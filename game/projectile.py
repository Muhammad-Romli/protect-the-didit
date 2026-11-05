"""Projectile: flies to its target; Game resolves the hit when `arrived`."""
from __future__ import annotations

import math

import pygame

from data.fadhli import SKY_ARC_HEIGHT
from game import gfx, models, sprites_proc
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
        self.shape: int | None = None   # Bima's geometry shots: 0 square, 1 triangle, 2 circle
        self.solid = False              # Lv3: cube / pyramid / sphere
        self.color = color
        self.source = source  # firing Tower (its effects run on hit)
        self.arrived = False
        self.high_arc = False
        self.bounces = 0
        self.hit_ids: set[int] = set()
        self.power_crater = False
        self.make_crater = False
        self.gyro = False
        self.flight_time = 0.0

    def update(self, dt: float) -> None:
        self.flight_time += dt
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
        draw_pos = Vec(self.pos)
        if self.high_arc:
            total = max(1.0, Vec(self.target.pos).distance_to(Vec(self.source.pos)) if self.source else 1.0)
            progress = min(1.0, self.flight_time * self.speed / total)
            draw_pos.y -= math.sin(progress * math.pi) * SKY_ARC_HEIGHT
        x, y = int(draw_pos.x), int(draw_pos.y)
        kind = self.source.kind if self.source is not None else None
        img = sprite(f"projectiles/{kind}", 16) if kind else None
        if img is not None:
            d = self.dest - self.pos
            angle = -math.degrees(math.atan2(d.y, d.x)) if d.length() > 0 else 0
            img = pygame.transform.rotate(img, angle)
            surface.blit(img, img.get_rect(center=(x, y)))
            return
        if self.shape is not None:
            spr = sprites_proc.shape_sprite(self.shape, self.solid, 26)
            t = pygame.time.get_ticks() / 1000
            spr = pygame.transform.rotozoom(spr, (t * 240) % 360, 1.0)
            gfx.blit_shadow(surface, (x + 5, y + 14), 22, 9, 80)
            halo = gfx.glow(22, sprites_proc.SHAPE_COLORS[self.shape], 150)
            surface.blit(halo, halo.get_rect(center=(x, y)), special_flags=pygame.BLEND_RGB_ADD)
            surface.blit(spr, spr.get_rect(center=(x, y)))
            return
        if kind and self.shape is None:
            m = models.projectile(kind, models.look_of(kind, self.source.tiers))
            if m is not None:
                spr, spin = m
                d = self.dest - self.pos
                ang = -math.degrees(math.atan2(d.y, d.x)) if d.length() > 0 else 0
                ang += (pygame.time.get_ticks() / 1000 * spin) % 360
                gfx.blit_shadow(surface, (x + 5, y + 13), 20, 9, 80)
                img = pygame.transform.rotate(spr, ang)
                surface.blit(img, img.get_rect(center=(x, y)))
                if self.high_arc:
                    pygame.draw.ellipse(surface, (255, 225, 170), (x - 8, y - 14, 16, 4), 1)
                return
        r = 7 if self.aoe_radius > 0 else 5
        gfx.blit_shadow(surface, (x + 5, y + 13), r * 2.4, r * 1.1, 80)   # shadow stays on the ground: the shot floats
        halo = gfx.glow(r * 3, self.color, 170)
        surface.blit(halo, halo.get_rect(center=(x, y)))
        orb = gfx.sphere(r, gfx.tint(self.color, 0.15), bounce=self.color, shine=1.2)
        surface.blit(orb, orb.get_rect(center=(x, y)))
