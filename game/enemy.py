"""Enemy: walks the path by `distance`; supports slow, stun, push-back and spawn-on-death."""
from __future__ import annotations

import random

import pygame

from data.enemies import ENEMIES
from data.settings import BOSS_SLOW_FACTOR, COLORS, SLOW_FLOOR
from game import gfx, sprites_proc
from game.assets import sprite
from game.utils import Path, Vec, draw_outlined

WALK_FRAMES_PER_PX = 0.11  # animation speed: frames advance with distance walked


class Enemy:
    def __init__(self, kind: str, path: Path, gives_money: bool = True,
                 hp_mult: float = 1.0, speed_mult: float = 1.0, bounty_mult: float = 1.0) -> None:
        d = ENEMIES[kind]
        self.kind = kind
        self.name: str = d["name"]
        self.path = path
        self.hp_mult, self.speed_mult, self.bounty_mult = hp_mult, speed_mult, bounty_mult  # children inherit these
        self.max_hp = float(d["hp"]) * hp_mult
        self.hp = self.max_hp
        self.base_speed = float(d["speed"]) * speed_mult
        self.stash_damage: int = d["stash_damage"]
        self.bounty: int = max(1, round(d["money"] * bounty_mult))
        self.radius: int = d["radius"]
        self.color = d["color"]
        self.is_boss: bool = d["is_boss"]
        self.spawns: tuple[str, int] | None = d.get("spawns")  # (kind, count) released on death
        self.gives_money = gives_money
        self.distance = 0.0  # used for "first" targeting and push-back
        self.pos: Vec = path.position_at(0)
        self.slow_strength = 0.0
        self.slow_timer = 0.0
        self.stun_timer = 0.0  # >0: stopped (sleep effect)
        self.hit_flash = 0.0   # visual: body flashes white when hit
        self.facing_left = False  # visual: sprites flip when walking left
        self.anim_offset = random.uniform(0, 8)
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

    # ----------------------------------------------------------------- draw
    def draw_shadow(self, surface: pygame.Surface) -> None:
        r = self.radius
        gfx.blit_shadow(surface, (self.pos.x + r * 0.35, self.pos.y + r * 0.78), r * 2.0, r * 0.85, 100)
        if self.is_boss:  # pulsing glow on the ground
            import math
            pulse = 1.0 + 0.12 * math.sin(pygame.time.get_ticks() / 150)
            g = gfx.glow(int(r * 2.1 * pulse), (255, 70, 60) if self.kind == "boss" else (255, 190, 60), 150)
            surface.blit(g, g.get_rect(center=(int(self.pos.x), int(self.pos.y + r * 0.2))))

    def draw(self, surface: pygame.Surface) -> None:
        r = self.radius
        x, y = int(self.pos.x), int(self.pos.y)
        if self.stun_timer > 0:
            frame = 0
        else:
            frame = int(self.distance * WALK_FRAMES_PER_PX + self.anim_offset)
        img = sprite(f"enemies/{self.kind}", 2 * r + 8)  # optional PNG override (faces right)
        if img is not None:
            if self.facing_left:
                img = pygame.transform.flip(img, True, False)
            if self.hit_flash > 0:
                img = img.copy()
                img.fill((120, 120, 120, 0), special_flags=pygame.BLEND_RGB_ADD)
        else:
            img = sprites_proc.enemy_sprite(self.kind, r, self.color, frame, self.facing_left, self.hit_flash > 0)
        surface.blit(img, img.get_rect(center=(x, y)))
        if self.slow_timer > 0:
            ring = gfx.glow(int(r * 1.5), (120, 190, 255), 140)
            surface.blit(ring, ring.get_rect(center=(x, y)))
        if self.stun_timer > 0:
            draw_outlined(surface, "z", (x + r, y - r - 12), 22, (255, 255, 255), center=True)
        if not self.is_boss and self.hp < self.max_hp:  # damaged: small health bar (bosses get the big one)
            w = max(22, r * 2 + 6)
            bar = pygame.Rect(x - w // 2, y - int(r * 1.5) - 8, w, 6)
            pygame.draw.rect(surface, (30, 14, 14), bar.inflate(2, 2), border_radius=3)
            pygame.draw.rect(surface, COLORS["hp_bg"], bar, border_radius=3)
            fill = bar.copy()
            fill.w = max(2, int(bar.w * max(0.0, self.hp) / self.max_hp))
            pygame.draw.rect(surface, COLORS["hp_fg"], fill, border_radius=3)
            pygame.draw.rect(surface, (200, 255, 190), (fill.x + 1, fill.y + 1, max(0, fill.w - 2), 1))
