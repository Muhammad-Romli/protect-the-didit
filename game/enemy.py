"""Enemy: walks the path by `distance`; supports slow. (push-back/stop come later.)"""
from __future__ import annotations

import pygame

from data.enemies import ENEMIES
from data.settings import BOSS_SLOW_FACTOR, COLORS, SLOW_FLOOR
from game.utils import Path, Vec


class Enemy:
    def __init__(self, kind: str, path: Path, gives_money: bool = True) -> None:
        d = ENEMIES[kind]
        self.kind = kind
        self.path = path
        self.max_hp = float(d["hp"])
        self.hp = self.max_hp
        self.base_speed = float(d["speed"])
        self.stash_damage: int = d["stash_damage"]
        self.bounty: int = d["money"]
        self.radius: int = d["radius"]
        self.color = d["color"]
        self.is_boss: bool = d["is_boss"]
        self.gives_money = gives_money
        self.distance = 0.0  # used for "first" targeting and push-back
        self.pos: Vec = path.position_at(0)
        self.slow_strength = 0.0
        self.slow_timer = 0.0
        self.reached_end = False

    @property
    def alive(self) -> bool:
        return self.hp > 0 and not self.reached_end

    @property
    def speed(self) -> float:
        return self.base_speed * max(SLOW_FLOOR, 1.0 - self.slow_strength)

    def apply_slow(self, strength: float, duration: float) -> None:
        """Strongest slow wins; bosses take half the effect."""
        if self.is_boss:
            strength *= BOSS_SLOW_FACTOR
        if self.slow_timer <= 0 or strength >= self.slow_strength:
            self.slow_strength = strength
            self.slow_timer = duration

    def take_damage(self, amount: float) -> None:
        self.hp -= amount

    def update(self, dt: float) -> None:
        if self.slow_timer > 0:
            self.slow_timer -= dt
            if self.slow_timer <= 0:
                self.slow_strength = 0.0
        self.distance += self.speed * dt
        if self.distance >= self.path.length:
            self.reached_end = True
        self.pos = self.path.position_at(self.distance)

    def draw(self, surface: pygame.Surface) -> None:
        x, y = int(self.pos.x), int(self.pos.y)
        r = self.radius
        # ears + body + eye = hamster-ish placeholder
        ear = max(3, r // 2)
        pygame.draw.circle(surface, self.color, (x - r // 2, y - r + 1), ear)
        pygame.draw.circle(surface, self.color, (x + r // 2, y - r + 1), ear)
        pygame.draw.circle(surface, self.color, (x, y), r)
        pygame.draw.circle(surface, (20, 20, 20), (x + r // 3, y - r // 4), max(2, r // 5))
        if self.slow_timer > 0:
            pygame.draw.circle(surface, (120, 180, 255), (x, y), r + 2, 2)
        if not self.is_boss:  # boss gets a big bar at the top of the screen instead
            w = r * 2 + 6
            top = y - r - ear - 8
            pygame.draw.rect(surface, COLORS["hp_bg"], (x - w // 2, top, w, 4))
            fill = int(w * max(0.0, self.hp) / self.max_hp)
            pygame.draw.rect(surface, COLORS["hp_fg"], (x - w // 2, top, fill, 4))
