"""Game state: money, lives, wave, entities, input actions. No global state elsewhere."""
from __future__ import annotations

import math
import random
from enum import Enum
from typing import Optional

import pygame

from data.activities import ACTIVITIES, STACKS
from data.map import MAP_CORNER_RADIUS, MAP_WAYPOINTS, STASH_POS
from data.settings import (BOUNTY_MULT, BOUNTY_WAVE_GROWTH, BUILD_RECT, COLORS, DEBUG_KNOWLEDGE, DEBUG_MONEY, SPEED_STEPS,
                           INCOME_INTERVAL_SECONDS, MAX_ACTIVITIES, PATH_MIN_DISTANCE, PATH_WIDTH, PLAYFIELD_RECT,
                           PREP_GRACE_SECONDS, PREP_MAX_HP_MULT, PREP_MAX_SECONDS,
                           PREP_MAX_SPEED_MULT, SELL_CONFIRM_SECONDS, START_MONEY,
                           SAVE_EVERY_WAVES, START_STASH_HP, TOWER_RADIUS, WAVE_CLEAR_BONUS_BASE,
                           WAVE_CLEAR_BONUS_PER_WAVE)
from data.towers import TOWER_ORDER, TOWERS
from data.waves import NEW_ENEMY_WAVES, SPECIAL_BONUS_MULT, SPECIAL_WAVES, WAVE_SCALING, WAVES
from data.enemies import ENEMIES
from data.effects import EFFECT_PARAMS
from game import actives, bima, mark, options as opts_mod, savegame, web
from game.effects import EFFECTS
from game import gfx
from game.assets import sprite
from game.scenery import bake_map
from game.enemy import Enemy
from game.fx import FX
from game.projectile import Projectile
from game import sprites_proc
from game.tower import Tower
from game.touch import Touch
from game.ui import UI
from game.utils import Path, Vec, draw_outlined, draw_range_circle, round_corners
from game.wave_manager import WaveManager

MESSAGE_SECONDS = 2.5


class State(Enum):
    PLAYING = "playing"
    WON = "won"
    LOST = "lost"


class Phase(Enum):
    PREP = "preparation"
    BATTLE = "battle"


class Game:
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.ui = UI()
        self.fx = FX()
        self.playfield = pygame.Rect(*PLAYFIELD_RECT)
        self.world = pygame.Surface(self.playfield.size)  # playfield drawn here, then shaken onto the screen
        self.build_rect = pygame.Rect(*BUILD_RECT)
        self.path = Path(round_corners(MAP_WAYPOINTS, MAP_CORNER_RADIUS))
        self.map_surface = self._render_map()
        self.vignette = self._make_vignette(self.playfield.size)
        self.show_debug = False
        self.options = opts_mod.load()
        self.options_open = False
        self.fps = 0.0
        self.mouse_pos = (0, 0)
        self.touch = Touch(self)  # phone controls; inactive on desktop until a finger touches the screen
        self.reset()
        self.apply_options()

    def apply_options(self) -> None:
        """Push the option values into audio / vfx (called at start and after every change)."""
        o = self.options
        self.fx.audio.master = o["volume"] / 10
        v = self.fx.vfx
        v.shake_enabled, v.comics_enabled = o["shake"], o["comics"]
        v.max_particles = 500 if o["particles"] == "High" else 120

    def reset(self) -> None:
        self.fx.reset()
        self._last_prep_sec = 0
        self._hover_key = None
        self.state = State.PLAYING
        self.money = float(START_MONEY)
        self.ball_knowledge = 0      # Jalu upgrade currency, earned by Larping
        self.stash_hp = START_STASH_HP
        self.towers: list[Tower] = []
        self.enemies: list[Enemy] = []
        self.projectiles: list[Projectile] = []
        self.waves = WaveManager()
        self.prep_time = 0.0         # seconds spent in the current preparation phase
        self.battle_hp_mult = 1.0    # strength locked in when the current wave started
        self.battle_speed_mult = 1.0
        self.selected: Optional[Tower] = None
        self.placing: Optional[str] = None
        self.sell_pending: Optional[Tower] = None
        self.sell_timer = 0.0
        self.paused = False
        self.larp_tip_shown = False
        self.speed = 1
        self.auto_timer = 0.0
        self.time = 0.0                 # simulation clock (seconds)
        self.delayed: list[list] = []   # [seconds left, callable] one-shot timers (ability wind-ups)
        self.shots: list = []           # Bima curve shots in flight
        self.cubes: list = []           # Bima cubes (block the path)
        self.sweeps: list = []          # Mark's running sweeps (see game/mark.py)
        self.zones: list = []           # Bima sphere trap zones
        self.shield, self.shield_t = 0.0, 0.0   # base shield (Bima sphere)
        self.hitstop, self.last_hitstop = 0.0, -9.0
        self.aiming = None              # (tower, ability id) while waiting for a map click
        self.message = ""
        self.message_timer = 0.0

    def flash(self, text: str, seconds: float = MESSAGE_SECONDS) -> None:
        self.message = text
        self.message_timer = seconds

    # ---------------------------------------------------------------- phases
    @property
    def phase(self) -> Phase:
        return Phase.BATTLE if self.waves.active else Phase.PREP

    def prep_ramp(self) -> float:
        """0.0 until the grace period ends, then rises linearly to 1.0 at PREP_MAX_SECONDS."""
        span = PREP_MAX_SECONDS - PREP_GRACE_SECONDS
        return max(0.0, min(1.0, (self.prep_time - PREP_GRACE_SECONDS) / span))

    def enemy_multipliers(self) -> tuple[float, float]:
        """(hp_mult, speed_mult): live preview in prep, locked-in value in battle."""
        if self.phase == Phase.BATTLE:
            return self.battle_hp_mult, self.battle_speed_mult
        r = self.prep_ramp()
        return 1 + (PREP_MAX_HP_MULT - 1) * r, 1 + (PREP_MAX_SPEED_MULT - 1) * r

    def _start_battle(self) -> None:
        """Lock in enemy strength from the prep time, stop activities, begin the wave."""
        if not self.waves.can_start:
            return
        self.battle_hp_mult, self.battle_speed_mult = self.enemy_multipliers()
        stopped = self._stop_all_activities()
        self.waves.start_next()
        boss = any(ENEMIES[kind]["is_boss"] for kind, *_ in WAVES[self.waves.number - 1])
        self.fx.wave_started(self.waves.number, boss, SPECIAL_WAVES.get(self.waves.number),
                             ENEMIES[NEW_ENEMY_WAVES[self.waves.number]]["name"] if self.waves.number in NEW_ENEMY_WAVES else None)
        if stopped:
            self.flash("Wave started: activities stopped")

    # ------------------------------------------------------------ activities
    def activity_slots_used(self) -> int:
        return sum(1 for t in self.towers
                   if t.activity and ACTIVITIES[t.activity]["counts_toward_limit"])

    def _stop_all_activities(self) -> bool:
        busy = [t for t in self.towers if t.activity]
        for t in busy:
            t.stop_activity()
        return bool(busy)

    def _toggle_activity(self, act_id: str) -> None:
        """Start `act_id` on the selected tower (switching from another one), or stop it."""
        t = self.selected
        data = ACTIVITIES.get(act_id)
        if data is None or data["tower"] != t.kind:
            return
        if t.activity == act_id:
            t.stop_activity()
            self.fx.click()
            return
        lock = t.activity_lock(data)
        if lock:
            self.flash(f"Locked: needs {lock}")
            self.fx.invalid()
            return
        if self.phase != Phase.PREP:
            self.flash("Activities only run during preparation")
            self.fx.invalid()
            return
        used = self.activity_slots_used()
        if t.activity and ACTIVITIES[t.activity]["counts_toward_limit"]:
            used -= 1  # switching frees this tower's own slot
        if data["counts_toward_limit"] and used >= MAX_ACTIVITIES:
            self.flash(f"All {MAX_ACTIVITIES} activity slots are busy")
            self.fx.invalid()
            return
        kind, arg = data["gives"]
        if kind == "stack" and t.stacks.get(arg, 0) >= STACKS[arg]["max"]:
            self.flash(f"{STACKS[arg]['label']} is already maxed")
            self.fx.invalid()
            return
        t.stop_activity()
        t.activity = act_id
        self.fx.click()

    def _tick_activities(self, dt: float) -> None:
        """Advance running activities; each completed interval grants its reward."""
        for t in self.towers:
            if not t.activity:
                continue
            data = ACTIVITIES[t.activity]
            t.activity_time += dt
            t.activity_acc += dt
            while t.activity and t.activity_acc >= data["interval"]:
                t.activity_acc -= data["interval"]
                kind, arg = data["gives"]
                if kind == "knowledge":
                    self.ball_knowledge += arg
                    self.fx.knowledge(t)
                elif kind == "stack":
                    t.add_stack(arg)
                    self.fx.stack(t, STACKS[arg]["color"])
                    if t.stacks[arg] >= STACKS[arg]["max"]:
                        self.flash(f"{STACKS[arg]['label']} maxed")
                        t.stop_activity()  # frees the slot

    # ---------------------------------------------------------------- input
    def handle_event(self, event: pygame.event.Event) -> None:
        if self.touch.handle_event(event):
            return
        if event.type == pygame.MOUSEMOTION:
            self.mouse_pos = event.pos
            self._update_hover(event.pos)
            if self.ui.graph.dragging:
                self.ui.graph.drag(event.pos, self)   # drag-select inside Bima's formula box
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.ui.graph.release()
        elif event.type == pygame.WINDOWFOCUSLOST and self.state == State.PLAYING and not web.IS_WEB:
            self.paused = True  # alt-tab pauses (desktop only: browsers fire focus-lost on a click outside the canvas, devtools, etc.)
        elif event.type == pygame.KEYDOWN:
            if self.state == State.PLAYING and self.ui.graph.focused and self.ui.graph.key(event, self):
                return  # typing a formula: no game hotkeys
            if event.key == pygame.K_RETURN and event.mod & pygame.KMOD_ALT:
                self._toggle_fullscreen()
            else:
                self._on_key(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN and self.state == State.PLAYING:
            if event.button == 1:
                self._on_left_click(event.pos)
            elif event.button == 3:
                self.placing = None
                self.aiming = None

    def _on_key(self, key: int) -> None:
        if key == pygame.K_r:
            self.reset()
        elif key == pygame.K_F11:
            self._toggle_fullscreen()
        elif key == pygame.K_m:
            self.fx.audio.muted = not self.fx.audio.muted
            self.flash("Sound off" if self.fx.audio.muted else "Sound on")
        elif key == pygame.K_F1:
            self.show_debug = not self.show_debug
        elif key == pygame.K_F2:
            self.add_money(DEBUG_MONEY)
            self.ball_knowledge += DEBUG_KNOWLEDGE
        elif self.state != State.PLAYING:
            return
        elif key == pygame.K_ESCAPE:
            if self.options_open:
                self.options_open = False
            elif self.aiming:
                self.aiming = None
            elif self.placing or self.selected:
                self.placing = None
                self.selected = None
            else:
                self.options_open = True
        elif key == pygame.K_o:
            self.options_open = not self.options_open
        elif key == pygame.K_t and self.selected:
            self._cycle_target(-1 if pygame.key.get_mods() & pygame.KMOD_SHIFT else 1)
        elif key == pygame.K_F3:
            self._skip_wave()
        elif key == pygame.K_F4 and self.selected:
            self._debug_free_upgrade()
        elif key == pygame.K_p:
            self.paused = not self.paused
        elif key == pygame.K_SPACE:
            self._start_battle()
        elif key == pygame.K_f:
            self._toggle_speed()
        elif key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
            self._choose_shop(TOWER_ORDER[key - pygame.K_1])
        elif key in (pygame.K_e, pygame.K_c, pygame.K_v) and self.selected:
            self.use_ability((pygame.K_e, pygame.K_c, pygame.K_v).index(key))
        elif key == pygame.K_g and self.selected and self.selected.kind == "bima":
            bima.fire_graph(self, self.selected)
        elif key in (pygame.K_q, pygame.K_w) and self.selected:
            self._try_upgrade(0 if key == pygame.K_q else 1)
        elif key == pygame.K_x and self.selected:
            self._request_sell()

    def _toggle_fullscreen(self) -> None:
        if web.IS_WEB:
            web.toggle_fullscreen()
            return
        try:
            pygame.display.toggle_fullscreen()
        except pygame.error:
            self.flash("Fullscreen is not supported on this display")

    def _update_hover(self, pos) -> None:
        """Soft tick when the mouse enters a different button."""
        action = self.ui.hit_test(pos, self)
        key = None if action in (None, ("noop",)) else action
        if key is not None and key != self._hover_key:
            self.fx.hover()
        self._hover_key = key

    def use_ability(self, index: int) -> None:
        """Hotkey / button for the selected tower's index-th ability. Aimed abilities wait for a map click."""
        t = self.selected
        ids = actives.actives_of(t) if t else []
        if index >= len(ids):
            return
        aid = ids[index]
        ok, why = actives.can_use(self, t, aid)
        if not ok:
            self.fx.invalid()
            self.flash(why, 1.5)
        elif actives.ACTIVES[aid]["aim"]:
            self.aiming = (t, aid)
            self.placing = None
            self.flash(f"{actives.ACTIVES[aid]['name']}: tap the map, then OK" if self.touch.enabled
                       else f"{actives.ACTIVES[aid]['name']}: click the map  (right-click cancels)", 2.5)
        else:
            actives.use(self, t, aid)

    def _on_left_click(self, pos) -> None:
        action = self.ui.hit_test(pos, self)
        if action is None or action[0] != "g_focus":
            self.ui.graph.focused = False
        if action is None and self.touch.enabled and (self.aiming is not None or self.placing):
            self.touch.set_ghost(pos)   # finger: tap moves the ghost, the OK button confirms
            return
        if action is None and self.aiming is not None:
            tower, aid = self.aiming
            if actives.use(self, tower, aid, pos):
                self.aiming = None
            return
        if action is not None:
            self._do_action(action)
        elif self.placing:
            self._try_place(pos)
        else:
            tower = self._tower_at(pos)
            if tower is not None and tower is not self.selected:
                self.fx.select(tower)
            self.selected = tower

    def _do_action(self, action: tuple) -> None:
        name = action[0]
        if name == "shop":
            self._choose_shop(action[1])
        elif name == "start_wave":
            self._start_battle()
        elif name == "speed":
            self.fx.click()
            self._toggle_speed()
        elif name == "ability":
            self.fx.click()
            self.use_ability(action[1])
        elif name.startswith("g_") and self.selected is not None:
            self.fx.click()
            self.ui.graph.do(action, self)
        elif name == "options":
            self.fx.click()
            self.options_open = not self.options_open
        elif name == "opt":
            self.fx.click()
            if action[1] == "fullscreen":
                self._toggle_fullscreen()
            elif action[1] == "restart":
                self.options_open = False
                self.reset()
            elif action[1] == "resume":
                self.options_open = False
            else:
                opts_mod.change(self.options, action[1], action[2])
                self.apply_options()
                opts_mod.save(self.options)
        elif name == "target" and self.selected:
            self.fx.click()
            self._cycle_target(action[1])
        elif name == "panel":
            self.fx.click()
            self.ui.collapsed = not self.ui.collapsed
        elif name == "pause":
            self.fx.click()
            self.paused = not self.paused
        elif name == "activity" and self.selected:
            self._toggle_activity(action[1])
        elif name == "upgrade" and self.selected:
            self._try_upgrade(action[1])
        elif name == "sell" and self.selected:
            self._request_sell()

    def _choose_shop(self, kind: str) -> None:
        if self.placing == kind:
            self.placing = None
            self.fx.click()
        elif self.money < TOWERS[kind]["cost"]:
            self.flash("Not enough money")
            self.fx.invalid()
        else:
            self.placing, self.selected = kind, None
            self.fx.click()

    def _toggle_speed(self) -> None:
        """Cycle x1 -> x2 -> x3 -> x1."""
        self.speed = SPEED_STEPS[(SPEED_STEPS.index(self.speed) + 1) % len(SPEED_STEPS)]

    def _cycle_target(self, direction: int) -> None:
        modes = opts_mod.TARGET_MODES
        t = self.selected
        t.targeting = modes[(modes.index(t.targeting) + direction) % len(modes)]
        self.flash(f"{t.name} targets: {opts_mod.TARGET_LABELS[t.targeting]}", 1.5)

    # -------------------------------------------------------------- upgrades
    def upgrade_cost(self, tower: Tower, up: dict) -> int:
        """Upgrade price after nearby discount auras (strongest aura wins)."""
        discount = max(self.effect_values("upgrade_discount", other=tower), default=0.0)
        return round(up["cost"] * (1 - discount))

    def _try_upgrade(self, path: int) -> None:
        t = self.selected
        ok, reason = t.can_upgrade(path)
        if not ok:
            self.flash(reason)
            self.fx.invalid()
            return
        up = t.next_upgrade(path)
        cost = self.upgrade_cost(t, up)
        if self.money < cost:
            self.flash("Not enough money")
            self.fx.invalid()
            return
        if self.ball_knowledge < up["knowledge"]:
            self.flash("Not enough ball knowledge (Jalu: Larp in preparation)")
            self.fx.invalid()
            return
        self.add_money(-cost)
        self.ball_knowledge -= up["knowledge"]
        t.upgrade(path, paid=cost)
        self.fx.upgraded(t, up["name"], t.tiers[path])

    def _debug_free_upgrade(self) -> None:
        """Debug (F4): the selected tower gets its next upgrade for free, on the path it already follows
        (path A for a fresh tower). Respects the path rules. Press up to 4 times for tier 4."""
        t = self.selected
        path = 0 if t.tiers[0] >= t.tiers[1] else 1
        up = t.next_upgrade(path)
        ok, reason = t.can_upgrade(path)
        if up is None or not ok:
            self.flash(reason or "Max tier")
            return
        t.upgrade(path, paid=0)
        self.fx.upgraded(t, up["name"], t.tiers[path])

    def _request_sell(self) -> None:
        """First press arms the sale, a second press within SELL_CONFIRM_SECONDS sells."""
        t = self.selected
        if t.vanished:  # Mark is away (Sweep): he has to come back first
            self.flash(f"{t.name} is sweeping: wait for him to come back", 1.5)
            self.fx.invalid()
            return
        if self.sell_pending is t and self.sell_timer > 0:
            self.add_money(t.sell_value)
            self.fx.sold(t, t.sell_value)
            self.towers.remove(t)
            self.selected = self.sell_pending = None
        else:
            self.sell_pending, self.sell_timer = t, SELL_CONFIRM_SECONDS
            self.fx.click()
            self.flash(f"Press Sell again to sell for ${t.sell_value}")

    # ------------------------------------------------------------ placement
    def placement_check(self, kind: str, pos) -> tuple[bool, str]:
        p = Vec(pos)
        margin = TOWER_RADIUS
        if not self.build_rect.inflate(-2 * margin, -2 * margin).collidepoint(pos):
            return False, "Off map"
        if self.path.distance_to(p) < PATH_MIN_DISTANCE:
            return False, "Too close to the path"
        if any(p.distance_to(t.pos) < 2 * TOWER_RADIUS for t in self.towers):
            return False, "Overlaps another tower"
        if self.money < TOWERS[kind]["cost"]:
            return False, "Not enough money"
        return True, ""

    def _try_place(self, pos) -> None:
        kind = self.placing
        ok, reason = self.placement_check(kind, pos)
        if not ok:
            self.flash(reason)
            self.fx.invalid()
            return
        self.add_money(-TOWERS[kind]["cost"])
        tower = Tower(kind, pos)
        tower.targeting = self.options["default_target"]
        self.towers.append(tower)
        self.fx.placed(tower)
        self.selected = tower
        self.placing = None
        if kind == "jalu" and not self.larp_tip_shown:
            self.larp_tip_shown = True
            self.flash("Tip: in preparation, use Larping to earn knowledge for Jalu upgrades", 6.0)

    def _tower_at(self, pos) -> Optional[Tower]:
        p = Vec(pos)
        reach = TOWER_RADIUS + 12 + self.touch.pick_bonus()  # fingers are fatter than a cursor
        best, best_d = None, reach + 1
        for t in reversed(self.towers):
            d = p.distance_to(t.pos + Vec(0, -12))
            if d <= reach and d < best_d:
                best, best_d = t, d
        return best

    # --------------------------------------------------------- effect hooks
    def effect_values(self, hook: str, **ctx) -> list[float]:
        """Ask every tower's effects for a value for `hook` (see game/effects.py)."""
        values: list[float] = []
        for t in self.towers:
            for name in t.effects:
                fn = EFFECTS.get(name)
                if fn is not None:
                    v = fn(t, self, hook, **ctx)
                    if v is not None:
                        values.append(v)
        return values

    def damage_multiplier(self, enemy: Enemy) -> float:
        mult = max(self.effect_values("damage_taken", enemy=enemy), default=1.0)
        if enemy.vuln_timer > 0:  # Bima's square mark
            mult *= 1.0 + enemy.vuln
        return min(mult, 1.6) if enemy.vuln_timer > 0 else mult

    def attack_speed_mult(self, tower: Tower) -> float:
        return 1.0 + max(self.effect_values("speed_bonus", other=tower), default=0.0)

    def hit_enemy(self, enemy: Enemy, damage: float, slow: float = 0.0,
                  slow_duration: float = 0.0, color=(255, 240, 180), source: Tower | None = None) -> None:
        """Single place where tower damage reaches an enemy (applies debuffs + slow).
        Armored enemies only lose armor: 1 per hit, 3 per hit from a tower with armor_breaker."""
        if slow > 0:
            enemy.apply_slow(slow, slow_duration)
        if enemy.armor > 0:
            hits = EFFECT_PARAMS["armor_breaker"]["hits"] if source is not None and "armor_breaker" in source.effects else 1
            self.fx.armor_hit(enemy, enemy.break_armor(hits), hits)
            return
        enemy.take_damage(damage * self.damage_multiplier(enemy))
        self.fx.hit(enemy, color, source)

    # --------------------------------------------------------------- update
    def update(self, dt: float) -> None:
        self.touch.update(dt)
        self.ui.update(dt, self.money, self)
        self.message_timer -= dt
        self.sell_timer -= dt
        if self.message_timer <= 0:
            self.message = ""
        if self.paused or self.options_open:
            return
        if self.state != State.PLAYING:
            self.fx.update(dt)
            return
        for _ in range(self.speed):  # x2 / x3 run the simulation several times per frame (stays accurate)
            self._step(dt)
            if self.state != State.PLAYING:
                break

    def _step(self, dt: float) -> None:
        self.fx.update(dt)
        if self.hitstop > 0:  # brief freeze on big impacts
            self.hitstop -= dt
            return
        self.time += dt
        for d in self.delayed:
            d[0] -= dt
        due = [d for d in self.delayed if d[0] <= 0]
        self.delayed = [d for d in self.delayed if d[0] > 0]
        for d in due:
            d[1]()
        bima.update_world(self, dt)
        mark.update_world(self, dt)
        if self.phase == Phase.PREP:
            self.prep_time += dt
            self._tick_activities(dt)
            self._prep_warnings()
            if self.options["auto_start"] and self.waves.can_start and self.prep_time >= self.options["auto_delay"]:
                self._start_battle()  # auto-start: skips the rest of the preparation
            elif self.prep_time >= PREP_MAX_SECONDS:
                self.flash("Time's up! The wave starts now")
                self._start_battle()
        for kind in self.waves.update(dt):
            if ENEMIES[kind]["is_boss"] or ENEMIES[kind].get("mini"):
                self.fx.boss_spawned()
            self.spawn_enemy(kind)
        for e in self.enemies:
            e.update(dt)
            if e.slow_timer > 0 and random.random() < dt * 5:
                self.fx.vfx.trail(e.pos + Vec(random.uniform(-6, 6), random.uniform(-6, 6)), (150, 200, 255))
        for t in self.towers:
            t.update(dt, self)
            self._tick_income(t, dt)
        for p in self.projectiles:
            p.update(dt)
            self.fx.trail(p)
            if p.arrived:
                self._resolve_hit(p)
        self.projectiles = [p for p in self.projectiles if not p.arrived]
        self._collect_enemies()

        if self.state == State.PLAYING and self.waves.active \
                and self.waves.all_spawned and not self.enemies:
            self._finish_wave()

    def spawn_enemy(self, kind: str, distance: float = 0.0, parent: Enemy | None = None) -> Enemy:
        """Create an enemy for the running wave (wave scaling x preparation penalty). Children of a
        Trojan inherit the parent's multipliers and money flag."""
        if parent is not None:
            e = Enemy(kind, self.path, parent.gives_money, parent.hp_mult, parent.speed_mult, parent.bounty_mult)
        else:
            n = max(1, min(self.waves.number, len(WAVE_SCALING)))
            wave_hp, wave_speed = WAVE_SCALING[n - 1]
            bounty = BOUNTY_MULT * (1 + BOUNTY_WAVE_GROWTH * (n - 1))
            e = Enemy(kind, self.path, True, self.battle_hp_mult * wave_hp, self.battle_speed_mult * wave_speed, bounty)
        e.distance = max(0.0, distance)
        e.pos = self.path.position_at(e.distance)
        self.enemies.append(e)
        return e

    def add_money(self, amount: float) -> None:
        """The only place money changes (so the HUD can show +$N / -$N)."""
        self.money += amount
        if amount:
            self.ui.money_change(amount)

    def _tick_income(self, t: Tower, dt: float) -> None:
        """Romli's income_per_sec is paid in one lump every INCOME_INTERVAL_SECONDS."""
        if t.stats["income_per_sec"] <= 0:
            return
        t.income_timer += dt
        if t.income_timer >= INCOME_INTERVAL_SECONDS:
            t.income_timer -= INCOME_INTERVAL_SECONDS
            amount = round(t.stats["income_per_sec"] * INCOME_INTERVAL_SECONDS)
            self.add_money(amount)
            self.fx.income(t, amount)

    def _prep_warnings(self) -> None:
        """Audio/visual cues: enemies start growing after the grace period; last 5s tick."""
        sec = int(self.prep_time)
        if sec == self._last_prep_sec:
            return
        if sec == PREP_GRACE_SECONDS:
            self.fx.warning()
            self.flash("Enemies are getting stronger!")
        elif PREP_MAX_SECONDS - 5 <= sec < PREP_MAX_SECONDS:
            self.fx.tick()
        self._last_prep_sec = sec

    def _resolve_hit(self, p: Projectile) -> None:
        if p.aoe_radius > 0:
            victims = [e for e in self.enemies
                       if e.alive and e.pos.distance_to(p.pos) <= p.aoe_radius + e.radius]
        else:
            victims = [p.target] if p.target.alive else []
        if not victims:
            return
        for e in victims:
            self.hit_enemy(e, p.damage, p.slow, p.slow_duration, p.color, p.source)
        if p.aoe_radius > 0:
            self.fx.aoe(p.pos, p.aoe_radius, p.color)
        self.add_money(p.money_on_hit)
        if p.source is not None:  # on-hit effects (time push, geometry stacks, knockback, ...) may add victims
            for name in p.source.effects:
                fn = EFFECTS.get(name)
                if fn is not None:
                    fn(p.source, self, "hit", proj=p, victims=victims)

    def _collect_enemies(self) -> None:
        """Pay bounties for dead enemies, apply stash damage for leakers."""
        remaining: list[Enemy] = []
        born: list[Enemy] = []
        for e in self.enemies:
            if e.hp <= 0:
                self.fx.killed(e)
                if e.spawns:  # Trojan: the hatch opens and its passengers climb out along the path
                    kind, count = e.spawns
                    self.fx.trojan_opened(e, count)
                    for i in range(count):
                        spread = (i - (count - 1) / 2) * 9
                        child = Enemy(kind, self.path, e.gives_money, e.hp_mult, e.speed_mult, e.bounty_mult)
                        child.distance = max(0.0, e.distance + spread)
                        child.pos = self.path.position_at(child.distance)
                        child.slow_strength, child.slow_timer = e.slow_strength * 0.5, e.slow_timer
                        born.append(child)
                if e.gives_money:
                    self.add_money(e.bounty)
                if e.is_boss:
                    self.add_money(sum(self.effect_values("boss_kill")))
            elif e.reached_end:
                dmg = e.stash_damage
                if self.shield > 0:  # Bima's sphere shield soaks stash damage first
                    soak = min(self.shield, dmg)
                    self.shield -= soak
                    dmg -= soak
                self.stash_hp -= dmg
                self.fx.leaked(e, STASH_POS)
                if e.steal and self.money > 0:  # Rich Didit runs off with your money
                    stolen = min(int(self.money), e.steal)
                    self.add_money(-stolen)
                    self.fx.stolen(e, stolen)
            else:
                remaining.append(e)
        self.enemies = remaining + born
        if self.stash_hp <= 0:
            self.stash_hp = 0
            self.state = State.LOST
            self.fx.lost()

    def _finish_wave(self) -> None:
        self.waves.finish()
        self.prep_time = 0.0
        self._last_prep_sec = 0
        self.battle_hp_mult = self.battle_speed_mult = 1.0
        for t in self.towers:
            t.clear_wave_stacks()
        bonus = WAVE_CLEAR_BONUS_BASE + WAVE_CLEAR_BONUS_PER_WAVE * self.waves.number
        if self.waves.number in SPECIAL_WAVES:
            bonus = round(bonus * SPECIAL_BONUS_MULT)  # special rounds pay double
        total = bonus
        for t in self.towers:  # Romli's per-wave income
            if t.stats["income_per_wave"] > 0:
                total += t.stats["income_per_wave"]
                self.fx.income(t, round(t.stats["income_per_wave"]), sound=False)
        self.add_money(total)  # one combined +$N popup on the HUD
        self.fx.wave_cleared()
        if self.waves.number >= self.waves.total:
            self.state = State.WON
            self.fx.won()
            savegame.clear()  # a finished run has nothing to continue
        elif self.waves.number % SAVE_EVERY_WAVES == 0:
            if savegame.autosave(self):  # background checkpoint, between waves (nothing in flight)
                self.flash(f"Game saved (wave {self.waves.number})", 3.5)

    def load_save(self) -> bool:
        """Continue from the last autosave (title screen). False if there is none or it is unusable."""
        data = savegame.read()
        if data is None or not savegame.restore(self, data):
            return False
        self.apply_options()
        self.flash(f"Continued from wave {self.waves.number}", 4.0)
        return True

    def _skip_wave(self) -> None:
        """Debug (F3): end the running wave without rewards drama, start the next."""
        if self.waves.active:
            self.enemies.clear()
            self.projectiles.clear()
            self._finish_wave()
        if self.state == State.PLAYING:
            self._start_battle()

    # ----------------------------------------------------------------- draw
    @staticmethod
    def _make_vignette(size) -> pygame.Surface:
        """Red screen-edge glow, built small and stretched (cheap), faded in by danger."""
        small = pygame.Surface((50, 32), pygame.SRCALPHA)
        for y in range(32):
            for x in range(50):
                d = max(0.0, (math.hypot((x / 49 - 0.5) * 2, (y / 31 - 0.5) * 2) - 0.5) / 0.9)
                small.set_at((x, y), (255, 20, 20, int(255 * min(1.0, d) ** 1.7)))
        return pygame.transform.smoothscale(small, size)

    def danger_level(self) -> float:
        """0..1: how threatening the next/current wave is (drives the red vignette)."""
        if self.phase == Phase.PREP:
            return self.prep_ramp()
        return 0.6 * (self.battle_hp_mult - 1) / (PREP_MAX_HP_MULT - 1)

    def _render_map(self) -> pygame.Surface:
        surf = bake_map(self.path.points, self.playfield.size, PATH_WIDTH, STASH_POS)
        return surf

    def draw(self) -> None:
        s, w = self.screen, self.world
        w.blit(self.map_surface, (0, 0))
        self._draw_stash_glow(w)
        self.fx.vfx.draw_ambient(w)
        if self.selected:
            draw_range_circle(w, self.selected.pos, self.selected.stats["range"], (255, 255, 255))
        # depth sorting: all shadows first, then towers + enemies back-to-front by y
        things = sorted([*self.towers, *self.enemies], key=lambda o: o.pos.y)
        for o in things:
            o.draw_shadow(w)
        for o in things:
            if isinstance(o, Tower):
                o.draw(w, o is self.selected)
            else:
                o.draw(w)
        for p in self.projectiles:
            p.draw(w)
        bima.draw_world(w, self)
        mark.draw_world(w, self)
        if self.selected is not None and self.selected.kind == "bima":
            bima.draw_preview(w, self.selected)
        self.fx.vfx.draw(w)
        self._draw_placement_preview(w)
        self._draw_aiming(w)
        s.fill(COLORS["grass"])
        s.blit(w, self.fx.vfx.shake_offset())  # whole playfield shakes, UI stays still
        self.fx.vfx.draw_overlay(s, self.playfield)
        self._draw_vignette(s)
        self.ui.draw(s, self)
        if self.show_debug:
            self._draw_debug()
        elif self.options["fps"]:
            draw_outlined(self.screen, f"FPS {self.fps:.0f}", (1270, 620), 18, (255, 255, 120), anchor="bottomright", width=1)
        if self.state == State.PLAYING:
            self.touch.draw(s)
        if self.paused and self.state == State.PLAYING:
            self._draw_banner_panel("PAUSED", "Tap to resume" if self.touch.enabled else "P or the pause button to resume", COLORS["gold"])
        if self.state != State.PLAYING:
            self._draw_end_screen()

    def _draw_stash_glow(self, surface: pygame.Surface) -> None:
        sx, sy = STASH_POS
        pulse = 1 + 0.08 * math.sin(pygame.time.get_ticks() / 300)
        g = gfx.glow(int(64 * pulse), (255, 214, 90), 120)
        surface.blit(g, g.get_rect(center=(sx, sy)))

    def _draw_vignette(self, screen: pygame.Surface) -> None:
        level = self.danger_level()
        if level <= 0 or not self.options["vignette"]:
            return
        pulse = 0.75 + 0.25 * math.sin(pygame.time.get_ticks() / 220)
        self.vignette.set_alpha(int(150 * level * pulse))
        screen.blit(self.vignette, self.playfield.topleft)

    def _draw_placement_preview(self, surface: pygame.Surface) -> None:
        if not self.placing or not self.build_rect.collidepoint(self.mouse_pos) or self.ui.hit_test(self.mouse_pos, self):
            return
        ok, _ = self.placement_check(self.placing, self.mouse_pos)
        color = COLORS["good"] if ok else COLORS["bad"]
        data = TOWERS[self.placing]
        x, y = self.mouse_pos
        draw_range_circle(surface, self.mouse_pos, data["stats"]["range"], color)
        ghost = Tower(self.placing, self.mouse_pos)
        ox, oy = sprites_proc.tower_origin(TOWER_RADIUS)
        img = sprites_proc.tower_sprite(self.placing, TOWER_RADIUS, data["color"]).copy()
        img.set_alpha(190 if ok else 120)
        surface.blit(img, (x - ox, y - oy))
        pygame.draw.ellipse(surface, color, (x - 30, y - 14, 60, 30), 3)

    def _draw_aiming(self, surface: pygame.Surface) -> None:
        """Preview while an aimed ability waits for a click."""
        if self.aiming is None:
            return
        tower, aid = self.aiming
        cfg = actives.ACTIVES[aid]
        pos = Vec(self.mouse_pos)
        if self.ui.hit_test(self.mouse_pos, self) is not None:
            return
        radius = {"sphere_active": 90}.get(aid, 28)
        if aid == "cube_active":
            d, off = bima.nearest_path_distance(self.path, pos)
            snapped = self.path.position_at(d)
            ok = off <= 48 and snapped.distance_to(tower.pos) <= 280
            draw_range_circle(surface, tower.pos, 280, (255, 255, 255))
            pygame.draw.circle(surface, COLORS["good"] if ok else COLORS["bad"], (int(snapped.x), int(snapped.y)), 26, 3)
            return
        draw_range_circle(surface, pos, radius, cfg["color"])

    def _draw_debug(self) -> None:
        lines = [f"FPS {self.fps:.0f}", f"enemies {len(self.enemies)}",
                 f"projectiles {len(self.projectiles)}", f"towers {len(self.towers)}",
                 f"speed x{self.speed}", f"particles {len(self.fx.vfx.particles)}", f"audio {'on' if self.fx.audio.enabled else 'off'}"]
        for i, line in enumerate(lines):
            draw_outlined(self.screen, line, (8, 110 + i * 18), 22, (255, 255, 0))

    def _draw_banner_panel(self, title: str, sub: str, color) -> None:
        dim = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        dim.fill((10, 8, 20, 150))
        self.screen.blit(dim, (0, 0))
        panel = gfx.panel_surface(560, 190)
        self.screen.blit(panel, panel.get_rect(center=(640, 320)))
        draw_outlined(self.screen, title, (640, 290), 64, color, center=True, width=4)
        draw_outlined(self.screen, sub, (640, 358), 28, (255, 255, 255), center=True)

    def _draw_end_screen(self) -> None:
        if self.state == State.WON:
            self._draw_banner_panel("YOU WIN!", "The stash is safe." if self.touch.enabled else "The stash is safe.  Press R to play again", COLORS["good"])
        else:
            self._draw_banner_panel("GAME OVER", "The stash is gone." if self.touch.enabled else "The stash is gone.  Press R to restart", COLORS["bad"])
        self.touch.draw(self.screen)
