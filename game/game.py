"""Game state: money, lives, wave, entities, input actions. No global state elsewhere."""
from __future__ import annotations

import math
import random
from enum import Enum
from typing import Optional

import pygame

from data.activities import ACTIVITIES, STACKS
from data.effects import BOLT_SECONDS
from data.map import MAP_WAYPOINTS, STASH_POS
from data.settings import (COLORS, DEBUG_KNOWLEDGE, DEBUG_MONEY, FAST_FORWARD_SPEED,
                           INCOME_INTERVAL_SECONDS, MAX_ACTIVITIES, PATH_MIN_DISTANCE, PATH_WIDTH, PLAYFIELD_RECT,
                           PREP_GRACE_SECONDS, PREP_MAX_HP_MULT, PREP_MAX_SECONDS,
                           PREP_MAX_SPEED_MULT, SELL_CONFIRM_SECONDS, START_MONEY,
                           START_STASH_HP, TOWER_RADIUS, WAVE_CLEAR_BONUS_BASE,
                           WAVE_CLEAR_BONUS_PER_WAVE)
from data.towers import TOWER_ORDER, TOWERS
from data.waves import WAVES
from game.effects import EFFECTS
from game.assets import sprite
from game.enemy import Enemy
from game.fx import FX
from game.projectile import Projectile
from game.tower import Tower
from game.ui import UI
from game.utils import Path, Vec, draw_range_circle, draw_text
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
        self.path = Path(MAP_WAYPOINTS)
        self.map_surface = self._render_map()
        self.vignette = self._make_vignette(self.playfield.size)
        self.show_debug = False
        self.fps = 0.0
        self.mouse_pos = (0, 0)
        self.reset()

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
        self.bolts: list[list] = []  # [start, end, seconds_left] chain-lightning lines
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
        boss = any(kind == "boss" for kind, *_ in WAVES[self.waves.number - 1])
        self.fx.wave_started(self.waves.number, boss)
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
        if event.type == pygame.MOUSEMOTION:
            self.mouse_pos = event.pos
            self._update_hover(event.pos)
        elif event.type == pygame.WINDOWFOCUSLOST and self.state == State.PLAYING:
            self.paused = True  # alt-tab pauses
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN and event.mod & pygame.KMOD_ALT:
                self._toggle_fullscreen()
            else:
                self._on_key(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN and self.state == State.PLAYING:
            if event.button == 1:
                self._on_left_click(event.pos)
            elif event.button == 3:
                self.placing = None

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
            self.placing = None
            self.selected = None
        elif key == pygame.K_F3:
            self._skip_wave()
        elif key == pygame.K_p:
            self.paused = not self.paused
        elif key == pygame.K_SPACE:
            self._start_battle()
        elif key == pygame.K_f:
            self._toggle_speed()
        elif key in (pygame.K_1, pygame.K_2, pygame.K_3):
            self._choose_shop(TOWER_ORDER[key - pygame.K_1])
        elif key in (pygame.K_q, pygame.K_w) and self.selected:
            self._try_upgrade(0 if key == pygame.K_q else 1)
        elif key == pygame.K_x and self.selected:
            self._request_sell()

    def _toggle_fullscreen(self) -> None:
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

    def _on_left_click(self, pos) -> None:
        action = self.ui.hit_test(pos, self)
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
        self.speed = 1 if self.speed == FAST_FORWARD_SPEED else FAST_FORWARD_SPEED

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

    def _request_sell(self) -> None:
        """First press arms the sale, a second press within SELL_CONFIRM_SECONDS sells."""
        t = self.selected
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
        if not self.playfield.inflate(-2 * margin, -2 * margin).collidepoint(pos):
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
        self.towers.append(tower)
        self.fx.placed(tower)
        self.selected = tower
        self.placing = None
        if kind == "jalu" and not self.larp_tip_shown:
            self.larp_tip_shown = True
            self.flash("Tip: in preparation, use Larping to earn knowledge for Jalu upgrades", 6.0)

    def _tower_at(self, pos) -> Optional[Tower]:
        p = Vec(pos)
        for t in reversed(self.towers):
            if p.distance_to(t.pos) <= TOWER_RADIUS + 4:
                return t
        return None

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
        return max(self.effect_values("damage_taken", enemy=enemy), default=1.0)

    def attack_speed_mult(self, tower: Tower) -> float:
        return 1.0 + max(self.effect_values("speed_bonus", other=tower), default=0.0)

    def hit_enemy(self, enemy: Enemy, damage: float, slow: float = 0.0,
                  slow_duration: float = 0.0, color=(255, 240, 180)) -> None:
        """Single place where tower damage reaches an enemy (applies debuffs + slow)."""
        if slow > 0:
            enemy.apply_slow(slow, slow_duration)
        enemy.take_damage(damage * self.damage_multiplier(enemy))
        self.fx.hit(enemy, color)

    def add_bolt(self, a, b) -> None:
        self.bolts.append([Vec(a), Vec(b), BOLT_SECONDS])
        self.fx.zap(a, b)

    # --------------------------------------------------------------- update
    def update(self, dt: float) -> None:
        self.ui.update(dt, self.money)
        self.message_timer -= dt
        self.sell_timer -= dt
        if self.message_timer <= 0:
            self.message = ""
        if self.paused:
            return
        self.fx.update(dt * self.speed)
        if self.state != State.PLAYING:
            return
        dt *= self.speed

        if self.phase == Phase.PREP:
            self.prep_time += dt
            self._tick_activities(dt)
            self._prep_warnings()
            if self.prep_time >= PREP_MAX_SECONDS:
                self.flash("Time's up! The wave starts now")
                self._start_battle()
        for kind in self.waves.update(dt):
            if kind == "boss":
                self.fx.boss_spawned()
            self.enemies.append(Enemy(kind, self.path, hp_mult=self.battle_hp_mult,
                                      speed_mult=self.battle_speed_mult))
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
        for b in self.bolts:
            b[2] -= dt
        self.bolts = [b for b in self.bolts if b[2] > 0]
        self._collect_enemies()

        if self.state == State.PLAYING and self.waves.active \
                and self.waves.all_spawned and not self.enemies:
            self._finish_wave()

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
            self.hit_enemy(e, p.damage, p.slow, p.slow_duration, p.color)
        if p.aoe_radius > 0:
            self.fx.aoe(p.pos, p.aoe_radius, p.color)
        self.add_money(p.money_on_hit)
        if p.source is not None:  # on-hit effects (pierce, chain lightning, ...) may add victims
            for name in p.source.effects:
                fn = EFFECTS.get(name)
                if fn is not None:
                    fn(p.source, self, "hit", proj=p, victims=victims)

    def _collect_enemies(self) -> None:
        """Pay bounties for dead enemies, apply stash damage for leakers."""
        remaining: list[Enemy] = []
        for e in self.enemies:
            if e.hp <= 0:
                self.fx.killed(e)
                if e.gives_money:
                    self.add_money(e.bounty)
                if e.is_boss:
                    self.add_money(sum(self.effect_values("boss_kill")))
            elif e.reached_end:
                self.stash_hp -= e.stash_damage
                self.fx.leaked(e, STASH_POS)
            else:
                remaining.append(e)
        self.enemies = remaining
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
        surf = pygame.Surface(self.screen.get_size())
        surf.fill(COLORS["grass"])
        bg = sprite("background", size=self.playfield.size)
        if bg is not None:
            surf.blit(bg, (0, 0))
        pts = [(int(p.x), int(p.y)) for p in self.path.points]
        for width, color in ((PATH_WIDTH + 8, COLORS["path_edge"]), (PATH_WIDTH, COLORS["path"])):
            pygame.draw.lines(surf, color, False, pts, width)
            for p in pts:  # round the joints so corners have no gaps
                pygame.draw.circle(surf, color, p, width // 2)
        sx, sy = STASH_POS
        stash = pygame.Rect(0, 0, 56, 40)
        stash.center = (sx, sy + 10)
        img = sprite("stash", 48)
        if img is not None:
            surf.blit(img, img.get_rect(center=stash.center))
        else:
            pygame.draw.rect(surf, (150, 100, 40), stash, border_radius=6)
            pygame.draw.rect(surf, COLORS["gold"], stash, 3, border_radius=6)
            draw_text(surf, "STASH", stash.center, 20, (255, 240, 200), center=True)
        return surf

    def draw(self) -> None:
        s, w = self.screen, self.world
        w.blit(self.map_surface, (0, 0))
        self._draw_stash_glow(w)
        self.fx.vfx.draw_ambient(w)
        if self.selected:
            draw_range_circle(w, self.selected.pos, self.selected.stats["range"], (255, 255, 255))
        for t in self.towers:
            t.draw(w, t is self.selected)
        for e in self.enemies:
            e.draw(w)
        for p in self.projectiles:
            p.draw(w)
        self._draw_bolts(w)
        self.fx.vfx.draw(w)
        self._draw_placement_preview(w)
        self._draw_boss_bar(w)
        s.fill(COLORS["grass"])
        s.blit(w, self.fx.vfx.shake_offset())  # whole playfield shakes, UI stays still
        self.fx.vfx.draw_overlay(s, self.playfield)
        self._draw_vignette(s)
        self.ui.draw(s, self)
        if self.show_debug:
            self._draw_debug()
        if self.paused and self.state == State.PLAYING:
            draw_text(s, "PAUSED", (500, 300), 72, COLORS["gold"], center=True)
            draw_text(s, "P to resume", (500, 350), 30, center=True)
        if self.state != State.PLAYING:
            self._draw_end_screen()

    def _draw_stash_glow(self, surface: pygame.Surface) -> None:
        sx, sy = STASH_POS
        pulse = 3 * math.sin(pygame.time.get_ticks() / 300)
        pygame.draw.circle(surface, (240, 200, 70), (sx, sy + 10), int(36 + pulse), 2)

    def _draw_vignette(self, screen: pygame.Surface) -> None:
        level = self.danger_level()
        if level <= 0:
            return
        pulse = 0.75 + 0.25 * math.sin(pygame.time.get_ticks() / 220)
        self.vignette.set_alpha(int(150 * level * pulse))
        screen.blit(self.vignette, self.playfield.topleft)

    def _draw_bolts(self, surface: pygame.Surface) -> None:
        for a, b, ttl in self.bolts:
            mid = a.lerp(b, 0.5) + Vec(random.uniform(-6, 6), random.uniform(-6, 6))
            pts = [(a.x, a.y), (mid.x, mid.y), (b.x, b.y)]
            pygame.draw.lines(surface, (255, 245, 140), False, pts, 4)
            pygame.draw.lines(surface, (255, 255, 255), False, pts, 2)

    def _draw_placement_preview(self, surface: pygame.Surface) -> None:
        if not self.placing or not self.playfield.collidepoint(self.mouse_pos):
            return
        ok, _ = self.placement_check(self.placing, self.mouse_pos)
        color = COLORS["good"] if ok else COLORS["bad"]
        data = TOWERS[self.placing]
        draw_range_circle(surface, self.mouse_pos, data["stats"]["range"], color)
        pygame.draw.circle(surface, data["color"], self.mouse_pos, TOWER_RADIUS)
        pygame.draw.circle(surface, color, self.mouse_pos, TOWER_RADIUS, 3)

    def _draw_boss_bar(self, surface: pygame.Surface) -> None:
        boss = next((e for e in self.enemies if e.is_boss), None)
        if boss is None:
            return
        bar = pygame.Rect(200, 12, 600, 20)
        pygame.draw.rect(surface, COLORS["hp_bg"], bar)
        fill = bar.copy()
        fill.w = int(bar.w * max(0.0, boss.hp) / boss.max_hp)
        pygame.draw.rect(surface, (220, 60, 60), fill)
        pygame.draw.rect(surface, (255, 255, 255), bar, 2)
        draw_text(surface, "BOSS DIDIT", bar.center, 22, center=True)

    def _draw_debug(self) -> None:
        lines = [f"FPS {self.fps:.0f}", f"enemies {len(self.enemies)}",
                 f"projectiles {len(self.projectiles)}", f"towers {len(self.towers)}",
                 f"speed x{self.speed}", f"particles {len(self.fx.vfx.particles)}", f"audio {'on' if self.fx.audio.enabled else 'off'}"]
        for i, line in enumerate(lines):
            draw_text(self.screen, line, (8, 40 + i * 18), 22, (255, 255, 0))

    def _draw_end_screen(self) -> None:
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))
        won = self.state == State.WON
        cx = self.screen.get_width() // 2
        draw_text(self.screen, "YOU WIN! The stash is safe." if won else "GAME OVER - the stash is gone",
                  (cx, 300), 64, COLORS["good"] if won else COLORS["bad"], center=True)
        draw_text(self.screen, "Press R to restart", (cx, 370), 36, center=True)
