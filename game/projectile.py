"""Projectile: flies to its target; Game resolves the hit when `arrived`."""
from __future__ import annotations

import math

import pygame

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
        # Fadhli (game/fadhli.py): lobbed arc, size, bounce chain, melee marker
        self.arc = 0.0                  # px: peak height of the lob (visual only)
        self.scale = 1.0                # sprite scale (mega throw = 2.0)
        self.mega = False
        self.total = max(1.0, self.pos.distance_to(target.pos))   # distance at launch (for the arc)
        self.bounces = 0
        self.bounce_chance = 0.0        # chance that the ball goes on to another Didit after this hit
        self.hit_list: list = []        # Didits this ball already hit (bounce prefers new ones)
        self.melee = False

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
        x, y = int(self.pos.x), int(self.pos.y)
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
                lift = 0.0
                if self.arc > 0:   # lobbed throw: the ball flies up and comes down, the shadow stays on the ground
                    prog = max(0.0, min(1.0, 1 - (self.dest - self.pos).length() / self.total))
                    lift = self.arc * 4 * prog * (1 - prog)
                gfx.blit_shadow(surface, (x + 5, y + 13), (20 - 6 * lift / max(1, self.arc or 1)) * self.scale, 9 * self.scale, 80)
                img = pygame.transform.rotate(spr, ang)
                if self.scale != 1.0:
                    img = pygame.transform.rotozoom(img, 0, self.scale)
                if self.mega:      # blazing aura around the mega throw
                    halo = gfx.glow(int(24 * self.scale), (255, 170, 70), 120)
                    surface.blit(halo, halo.get_rect(center=(x, int(y - lift))), special_flags=pygame.BLEND_RGB_ADD)
                surface.blit(img, img.get_rect(center=(x, int(y - lift))))
                return
        r = 7 if self.aoe_radius > 0 else 5
        gfx.blit_shadow(surface, (x + 5, y + 13), r * 2.4, r * 1.1, 80)   # shadow stays on the ground: the shot floats
        halo = gfx.glow(r * 3, self.color, 170)
        surface.blit(halo, halo.get_rect(center=(x, y)))
        orb = gfx.sphere(r, gfx.tint(self.color, 0.15), bounce=self.color, shine=1.2)
        surface.blit(orb, orb.get_rect(center=(x, y)))
