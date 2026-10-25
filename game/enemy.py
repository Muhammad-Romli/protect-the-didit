"""Enemy: walks the path by `distance`; supports slow. (push-back/stop come later.)"""
from __future__ import annotations

import math

import pygame

from data.enemies import ENEMIES
from data.settings import BOSS_SLOW_FACTOR, COLORS, SLOW_FLOOR
from game.assets import sprite
from game.utils import Path, Vec, draw_text


class Enemy:
    def __init__(self, kind: str, path: Path, gives_money: bool = True,
                 hp_mult: float = 1.0, speed_mult: float = 1.0) -> None:
        d = ENEMIES[kind]
        self.kind = kind
        self.path = path
        self.max_hp = float(d["hp"]) * hp_mult
        self.hp = self.max_hp
        self.base_speed = float(d["speed"]) * speed_mult
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
        self.stun_timer = 0.0  # >0: stopped (sleep effect)
        self.hit_flash = 0.0   # visual: body flashes white when hit
        self.facing_left = False  # visual: sprites flip when walking left
        self.reached_end = False

    @property
    def alive(self) -> bool:
        return self.hp > 0 and not self.reached_end

    @property
    def speed(self) -> float:
        if self.stun_timer > 0:
            return 0.0
        return self.base_speed * max(SLOW_FLOOR, 1.0 - self.slow_strength)

    def apply_slow(self, strength: float, duration: float) -> None:
        """Strongest slow wins; bosses take half the effect."""
        if self.is_boss:
            strength *= BOSS_SLOW_FACTOR
        if self.slow_timer <= 0 or strength >= self.slow_strength:
            self.slow_strength = strength
            self.slow_timer = duration

    def stun(self, duration: float) -> None:
        """Stop for `duration` seconds. Bosses are immune."""
        if not self.is_boss:
            self.stun_timer = max(self.stun_timer, duration)

    def push_back(self, distance: float) -> None:
        """Shove back along the path. Bosses are immune."""
        if not self.is_boss:
            self.distance = max(0.0, self.distance - distance)
            self.pos = self.path.position_at(self.distance)

    def take_damage(self, amount: float) -> None:
        self.hp -= amount
        self.hit_flash = 0.1

    def update(self, dt: float) -> None:
        if self.slow_timer > 0:
            self.slow_timer -= dt
            if self.slow_timer <= 0:
                self.slow_strength = 0.0
        self.hit_flash = max(0.0, self.hit_flash - dt)
        if self.stun_timer > 0:
            self.stun_timer -= dt
        self.distance += self.speed * dt
        if self.distance >= self.path.length:
            self.reached_end = True
        new_pos = self.path.position_at(self.distance)
        if abs(new_pos.x - self.pos.x) > 1e-6:
            self.facing_left = new_pos.x < self.pos.x
        self.pos = new_pos

    def draw(self, surface: pygame.Surface) -> None:
        bob = 0 if self.stun_timer > 0 else math.sin(self.distance * 0.12) * 1.6  # waddle
        x, y = int(self.pos.x), int(self.pos.y + bob)
        r = self.radius
        ear = max(3, r // 2)
        pygame.draw.ellipse(surface, (66, 120, 66), (x - r, int(self.pos.y) + r - 4, 2 * r, max(6, r // 2)))  # shadow
        if self.is_boss:  # pulsing red aura
            pulse = 6 + int(3 * math.sin(pygame.time.get_ticks() / 150))
            pygame.draw.circle(surface, (255, 70, 70), (x, y), r + pulse, 2)
        img = sprite(f"enemies/{self.kind}", 2 * r + 8)
        if img is not None:
            if self.facing_left:
                img = pygame.transform.flip(img, True, False)
            if self.hit_flash > 0:
                img = img.copy()
                img.fill((120, 120, 120, 0), special_flags=pygame.BLEND_RGB_ADD)  # brighten on hit
            surface.blit(img, img.get_rect(center=(x, y)))
        else:  # placeholder: ears + body + eye
            body = (255, 255, 255) if self.hit_flash > 0 else self.color
            pygame.draw.circle(surface, body, (x - r // 2, y - r + 1), ear)
            pygame.draw.circle(surface, body, (x + r // 2, y - r + 1), ear)
            pygame.draw.circle(surface, body, (x, y), r)
            eye = -1 if self.facing_left else 1
            pygame.draw.circle(surface, (20, 20, 20), (x + eye * (r // 3), y - r // 4), max(2, r // 5))
        if self.slow_timer > 0:
            pygame.draw.circle(surface, (120, 180, 255), (x, y), r + 2, 2)
        if self.stun_timer > 0:
            draw_text(surface, "z", (x + r, y - r - 12), 22, (255, 255, 255), center=True)
        if not self.is_boss:  # boss gets a big bar at the top of the screen instead
            w = r * 2 + 6
            top = y - r - ear - 8
            pygame.draw.rect(surface, COLORS["hp_bg"], (x - w // 2, top, w, 4))
            fill = int(w * max(0.0, self.hp) / self.max_hp)
            pygame.draw.rect(surface, COLORS["hp_fg"], (x - w // 2, top, fill, 4))
