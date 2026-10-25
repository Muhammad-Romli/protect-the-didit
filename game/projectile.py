"""Projectile: flies to its target; Game resolves the hit when `arrived`."""
from __future__ import annotations

import math

import pygame

from game.assets import sprite
from game.enemy import Enemy
from game.utils import Vec


class Projectile:
    def __init__(self, pos: Vec, target: Enemy, speed: float, damage: float,
                 aoe_radius: float, slow: float, slow_duration: float,
                 money_on_hit: float, color, source=None) -> None:
        self.pos = Vec(pos)
        self.target = target
        self.dest = Vec(target.pos)
        self.speed = speed
        self.damage = damage
        self.aoe_radius = aoe_radius
        self.slow = slow
        self.slow_duration = slow_duration
        self.money_on_hit = money_on_hit
        self.color = color
        self.source = source  # firing Tower (its effects run on hit)
        self.arrived = False

    def update(self, dt: float) -> None:
        if self.target.alive:
            self.dest = Vec(self.target.pos)  # homing while the target lives
        to_dest = self.dest - self.pos
        step = self.speed * dt
        if to_dest.length() <= step:
            self.pos = Vec(self.dest)
            self.arrived = True
        else:
            self.pos += to_dest.normalize() * step

    def draw(self, surface: pygame.Surface) -> None:
        kind = self.source.kind if self.source is not None else None
        img = sprite(f"projectiles/{kind}", 16) if kind else None
        if img is not None:
            d = self.dest - self.pos
            angle = -math.degrees(math.atan2(d.y, d.x)) if d.length() > 0 else 0
            img = pygame.transform.rotate(img, angle)
            surface.blit(img, img.get_rect(center=(int(self.pos.x), int(self.pos.y))))
            return
        r = 7 if self.aoe_radius > 0 else 5
        pygame.draw.circle(surface, tuple(min(255, c + 70) // 2 + 80 for c in self.color), (int(self.pos.x), int(self.pos.y)), r + 3, 1)  # soft halo
        pygame.draw.circle(surface, self.color, (int(self.pos.x), int(self.pos.y)), r)
        pygame.draw.circle(surface, (255, 255, 255), (int(self.pos.x), int(self.pos.y)), r, 1)
