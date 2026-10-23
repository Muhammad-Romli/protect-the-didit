"""Game state: money, lives, wave, entities, input actions. No global state elsewhere."""
from __future__ import annotations

from enum import Enum
from typing import Optional

import pygame

from data.map import MAP_WAYPOINTS, STASH_POS
from data.settings import (COLORS, DEBUG_MONEY, FAST_FORWARD_SPEED, PATH_MIN_DISTANCE,
                           PATH_WIDTH, PLAYFIELD_RECT, START_MONEY, START_STASH_HP,
                           TOWER_RADIUS, WAVE_CLEAR_BONUS_BASE, WAVE_CLEAR_BONUS_PER_WAVE)
from data.towers import TOWERS
from game.enemy import Enemy
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


class Game:
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.ui = UI()
        self.playfield = pygame.Rect(*PLAYFIELD_RECT)
        self.path = Path(MAP_WAYPOINTS)
        self.map_surface = self._render_map()
        self.show_debug = False
        self.fps = 0.0
        self.mouse_pos = (0, 0)
        self.reset()

    def reset(self) -> None:
        self.state = State.PLAYING
        self.money = float(START_MONEY)
        self.stash_hp = START_STASH_HP
        self.towers: list[Tower] = []
        self.enemies: list[Enemy] = []
        self.projectiles: list[Projectile] = []
        self.waves = WaveManager()
        self.selected: Optional[Tower] = None
        self.placing: Optional[str] = None
        self.speed = 1
        self.message = ""
        self.message_timer = 0.0

    def flash(self, text: str) -> None:
        self.message = text
        self.message_timer = MESSAGE_SECONDS

    # ---------------------------------------------------------------- input
    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self.mouse_pos = event.pos
        elif event.type == pygame.KEYDOWN:
            self._on_key(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN and self.state == State.PLAYING:
            if event.button == 1:
                self._on_left_click(event.pos)
            elif event.button == 3:
                self.placing = None

    def _on_key(self, key: int) -> None:
        if key == pygame.K_r:
            self.reset()
        elif key == pygame.K_ESCAPE:
            self.placing = None
            self.selected = None
        elif key == pygame.K_F1:
            self.show_debug = not self.show_debug
        elif key == pygame.K_F2:
            self.money += DEBUG_MONEY
        elif key == pygame.K_F3 and self.state == State.PLAYING:
            self._skip_wave()

    def _on_left_click(self, pos) -> None:
        action = self.ui.hit_test(pos, self)
        if action is not None:
            self._do_action(action)
        elif self.placing:
            self._try_place(pos)
        else:
            self.selected = self._tower_at(pos)

    def _do_action(self, action: tuple) -> None:
        name = action[0]
        if name == "shop":
            kind = action[1]
            if self.placing == kind:
                self.placing = None
            elif self.money < TOWERS[kind]["cost"]:
                self.flash("Not enough money")
            else:
                self.placing, self.selected = kind, None
        elif name == "start_wave":
            self.waves.start_next()
        elif name == "speed":
            self.speed = 1 if self.speed == FAST_FORWARD_SPEED else FAST_FORWARD_SPEED
        elif name == "upgrade" and self.selected:
            self._try_upgrade(action[1])
        elif name == "sell" and self.selected:
            self.money += self.selected.sell_value
            self.towers.remove(self.selected)
            self.selected = None

    def _try_upgrade(self, path: int) -> None:
        t = self.selected
        ok, reason = t.can_upgrade(path)
        if not ok:
            self.flash(reason)
            return
        cost = t.next_upgrade(path)["cost"]
        if self.money < cost:
            self.flash("Not enough money")
            return
        self.money -= cost
        t.upgrade(path)

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
            return
        self.money -= TOWERS[kind]["cost"]
        tower = Tower(kind, pos)
        self.towers.append(tower)
        self.selected = tower
        self.placing = None

    def _tower_at(self, pos) -> Optional[Tower]:
        p = Vec(pos)
        for t in reversed(self.towers):
            if p.distance_to(t.pos) <= TOWER_RADIUS + 4:
                return t
        return None

    # --------------------------------------------------------------- update
    def update(self, dt: float) -> None:
        self.message_timer -= dt
        if self.message_timer <= 0:
            self.message = ""
        if self.state != State.PLAYING:
            return
        dt *= self.speed

        for kind in self.waves.update(dt):
            self.enemies.append(Enemy(kind, self.path))
        for e in self.enemies:
            e.update(dt)
        for t in self.towers:
            t.update(dt, self)
            self.money += t.stats["income_per_sec"] * dt
        for p in self.projectiles:
            p.update(dt)
            if p.arrived:
                self._resolve_hit(p)
        self.projectiles = [p for p in self.projectiles if not p.arrived]
        self._collect_enemies()

        if self.state == State.PLAYING and self.waves.active \
                and self.waves.all_spawned and not self.enemies:
            self._finish_wave()

    def _resolve_hit(self, p: Projectile) -> None:
        if p.aoe_radius > 0:
            victims = [e for e in self.enemies
                       if e.alive and e.pos.distance_to(p.pos) <= p.aoe_radius + e.radius]
        else:
            victims = [p.target] if p.target.alive else []
        if not victims:
            return
        for e in victims:
            if p.slow > 0:
                e.apply_slow(p.slow, p.slow_duration)
            e.take_damage(p.damage)
        self.money += p.money_on_hit

    def _collect_enemies(self) -> None:
        """Pay bounties for dead enemies, apply stash damage for leakers."""
        remaining: list[Enemy] = []
        for e in self.enemies:
            if e.hp <= 0:
                if e.gives_money:
                    self.money += e.bounty
            elif e.reached_end:
                self.stash_hp -= e.stash_damage
            else:
                remaining.append(e)
        self.enemies = remaining
        if self.stash_hp <= 0:
            self.stash_hp = 0
            self.state = State.LOST

    def _finish_wave(self) -> None:
        self.waves.finish()
        self.money += WAVE_CLEAR_BONUS_BASE + WAVE_CLEAR_BONUS_PER_WAVE * self.waves.number
        self.money += sum(t.stats["income_per_wave"] for t in self.towers)
        if self.waves.number >= self.waves.total:
            self.state = State.WON

    def _skip_wave(self) -> None:
        """Debug (F3): end the running wave without rewards drama, start the next."""
        if self.waves.active:
            self.enemies.clear()
            self.projectiles.clear()
            self._finish_wave()
        if self.state == State.PLAYING:
            self.waves.start_next()

    # ----------------------------------------------------------------- draw
    def _render_map(self) -> pygame.Surface:
        surf = pygame.Surface(self.screen.get_size())
        surf.fill(COLORS["grass"])
        pts = [(int(p.x), int(p.y)) for p in self.path.points]
        for width, color in ((PATH_WIDTH + 8, COLORS["path_edge"]), (PATH_WIDTH, COLORS["path"])):
            pygame.draw.lines(surf, color, False, pts, width)
            for p in pts:  # round the joints so corners have no gaps
                pygame.draw.circle(surf, color, p, width // 2)
        sx, sy = STASH_POS
        stash = pygame.Rect(0, 0, 56, 40)
        stash.center = (sx, sy + 10)
        pygame.draw.rect(surf, (150, 100, 40), stash, border_radius=6)
        pygame.draw.rect(surf, COLORS["gold"], stash, 3, border_radius=6)
        draw_text(surf, "STASH", stash.center, 20, (255, 240, 200), center=True)
        return surf

    def draw(self) -> None:
        s = self.screen
        s.blit(self.map_surface, (0, 0))
        if self.selected:
            draw_range_circle(s, self.selected.pos, self.selected.stats["range"], (255, 255, 255))
        for t in self.towers:
            t.draw(s, t is self.selected)
        for e in self.enemies:
            e.draw(s)
        for p in self.projectiles:
            p.draw(s)
        self._draw_placement_preview()
        self._draw_boss_bar()
        self.ui.draw(s, self)
        if self.show_debug:
            self._draw_debug()
        if self.state != State.PLAYING:
            self._draw_end_screen()

    def _draw_placement_preview(self) -> None:
        if not self.placing or not self.playfield.collidepoint(self.mouse_pos):
            return
        ok, _ = self.placement_check(self.placing, self.mouse_pos)
        color = COLORS["good"] if ok else COLORS["bad"]
        data = TOWERS[self.placing]
        draw_range_circle(self.screen, self.mouse_pos, data["stats"]["range"], color)
        pygame.draw.circle(self.screen, data["color"], self.mouse_pos, TOWER_RADIUS)
        pygame.draw.circle(self.screen, color, self.mouse_pos, TOWER_RADIUS, 3)

    def _draw_boss_bar(self) -> None:
        boss = next((e for e in self.enemies if e.is_boss), None)
        if boss is None:
            return
        bar = pygame.Rect(200, 12, 600, 20)
        pygame.draw.rect(self.screen, COLORS["hp_bg"], bar)
        fill = bar.copy()
        fill.w = int(bar.w * max(0.0, boss.hp) / boss.max_hp)
        pygame.draw.rect(self.screen, (220, 60, 60), fill)
        pygame.draw.rect(self.screen, (255, 255, 255), bar, 2)
        draw_text(self.screen, "BOSS DIDIT", bar.center, 22, center=True)

    def _draw_debug(self) -> None:
        lines = [f"FPS {self.fps:.0f}", f"enemies {len(self.enemies)}",
                 f"projectiles {len(self.projectiles)}", f"towers {len(self.towers)}",
                 f"speed x{self.speed}"]
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
