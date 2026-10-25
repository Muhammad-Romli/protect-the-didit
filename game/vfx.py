"""Visual effects primitives: particles, expanding rings, floating text, comic-style
pop-up words ("POW!"), screen shake and screen flash. Pure visuals, no game logic."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pygame

from data.settings import PLAYFIELD_RECT
from game.utils import Vec, get_font

MAX_PARTICLES = 500
MAX_COMICS = 8
_TEXT_CACHE: dict[tuple, pygame.Surface] = {}


@dataclass
class Particle:
    pos: Vec
    vel: Vec
    life: float
    max_life: float
    color: tuple
    size: float
    gravity: float


@dataclass
class Ring:
    pos: Vec
    r0: float
    r1: float
    life: float
    max_life: float
    color: tuple
    width: int


@dataclass
class Label:
    """Floating text (rises + fades) or comic word (pops + wobbles)."""
    pos: Vec
    text: str
    color: tuple
    size: int
    life: float
    max_life: float
    rise: float = 0.0
    angle: float = 0.0
    comic: bool = False


def _text_surface(text: str, color: tuple, size: int, outline: int) -> pygame.Surface:
    """Text with a dark outline, cached."""
    key = (text, color, size, outline)
    if key not in _TEXT_CACHE:
        font = get_font(size)
        base = font.render(text, True, color)
        edge = font.render(text, True, (20, 16, 30))
        w, h = base.get_size()
        surf = pygame.Surface((w + 2 * outline, h + 2 * outline), pygame.SRCALPHA)
        for dx in range(-outline, outline + 1):
            for dy in range(-outline, outline + 1):
                if dx or dy:
                    surf.blit(edge, (outline + dx, outline + dy))
        surf.blit(base, (outline, outline))
        _TEXT_CACHE[key] = surf
    return _TEXT_CACHE[key]


class VFX:
    def __init__(self) -> None:
        self.clear()

    def clear(self) -> None:
        w, h = PLAYFIELD_RECT[2], PLAYFIELD_RECT[3]
        # slow drifting pollen/dust: [x, y, vx, vy, phase, size]
        self.motes = [[random.uniform(0, w), random.uniform(0, h), random.uniform(-6, 6),
                       random.uniform(-9, -2), random.uniform(0, 6.3), random.uniform(1.2, 2.4)]
                      for _ in range(22)]
        self.particles: list[Particle] = []
        self.rings: list[Ring] = []
        self.labels: list[Label] = []
        self.shake_time = 0.0
        self.shake_amp = 0.0
        self.flash_color = (255, 0, 0)
        self.flash_alpha = 0.0
        self.flash_time = 0.0
        self.flash_max = 1.0

    # ------------------------------------------------------------- spawners
    def burst(self, pos, color, n: int = 10, speed: float = 130, life: float = 0.45,
              size: float = 4, gravity: float = 180) -> None:
        for _ in range(n):
            if len(self.particles) >= MAX_PARTICLES:
                return
            ang = random.uniform(0, math.tau)
            spd = random.uniform(0.3, 1.0) * speed
            self.particles.append(Particle(Vec(pos), Vec(math.cos(ang), math.sin(ang)) * spd,
                                           life * random.uniform(0.7, 1.2), life, color,
                                           size * random.uniform(0.7, 1.3), gravity))

    def sparkle(self, pos, color, n: int = 10) -> None:
        """Slow rising glitter (upgrades, stacks)."""
        for _ in range(n):
            if len(self.particles) >= MAX_PARTICLES:
                return
            off = Vec(random.uniform(-16, 16), random.uniform(-10, 10))
            self.particles.append(Particle(Vec(pos) + off, Vec(random.uniform(-15, 15), random.uniform(-70, -30)),
                                           0.7, 0.7, color, random.uniform(2, 4), -20))

    def trail(self, pos, color) -> None:
        if len(self.particles) < MAX_PARTICLES:
            self.particles.append(Particle(Vec(pos), Vec(0, 0), 0.22, 0.22, color, 3.5, 0))

    def ring(self, pos, r0: float, r1: float, life: float, color, width: int = 3) -> None:
        self.rings.append(Ring(Vec(pos), r0, r1, life, life, color, width))

    def text(self, pos, text: str, color=(255, 255, 255), size: int = 24,
             life: float = 0.9, rise: float = 40) -> None:
        self.labels.append(Label(Vec(pos), text, color, size, life, life, rise))

    def comic(self, pos, text: str, color=(255, 230, 60), size: int = 34, life: float = 0.7) -> None:
        if sum(1 for lb in self.labels if lb.comic) >= MAX_COMICS:
            return
        self.labels.append(Label(Vec(pos), text, color, size, life, life, rise=20,
                                 angle=random.uniform(-12, 12), comic=True))

    def shake(self, amp: float, seconds: float) -> None:
        if amp >= self.shake_amp or self.shake_time <= 0:
            self.shake_amp, self.shake_time = amp, seconds

    def flash(self, color, alpha: float, seconds: float) -> None:
        self.flash_color, self.flash_alpha = color, alpha
        self.flash_time = self.flash_max = seconds

    # --------------------------------------------------------------- update
    def update(self, dt: float) -> None:
        w, h = PLAYFIELD_RECT[2], PLAYFIELD_RECT[3]
        for m in self.motes:
            m[4] += dt
            m[0] = (m[0] + (m[2] + math.sin(m[4]) * 8) * dt) % w
            m[1] = (m[1] + m[3] * dt) % h
        for p in self.particles:
            p.life -= dt
            p.vel.y += p.gravity * dt
            p.pos += p.vel * dt
        self.particles = [p for p in self.particles if p.life > 0]
        for r in self.rings:
            r.life -= dt
        self.rings = [r for r in self.rings if r.life > 0]
        for lb in self.labels:
            lb.life -= dt
            lb.pos.y -= lb.rise * dt
        self.labels = [lb for lb in self.labels if lb.life > 0]
        self.shake_time = max(0.0, self.shake_time - dt)
        self.flash_time = max(0.0, self.flash_time - dt)

    def shake_offset(self) -> tuple[int, int]:
        if self.shake_time <= 0:
            return 0, 0
        a = self.shake_amp * min(1.0, self.shake_time / 0.25)
        return int(random.uniform(-a, a)), int(random.uniform(-a, a))

    # ----------------------------------------------------------------- draw
    def draw_ambient(self, surface: pygame.Surface) -> None:
        for x, y, _vx, _vy, _ph, size in self.motes:
            pygame.draw.circle(surface, (235, 245, 185), (int(x), int(y)), int(size))

    def draw(self, surface: pygame.Surface) -> None:
        for r in self.rings:
            t = 1 - r.life / r.max_life
            radius = r.r0 + (r.r1 - r.r0) * (1 - (1 - t) ** 2)
            width = max(1, int(r.width * (1 - t)))
            pygame.draw.circle(surface, r.color, (int(r.pos.x), int(r.pos.y)), int(radius), width)
        for p in self.particles:
            size = max(1, int(p.size * p.life / p.max_life))
            pygame.draw.circle(surface, p.color, (int(p.pos.x), int(p.pos.y)), size)
        for lb in self.labels:
            self._draw_label(surface, lb)

    def _draw_label(self, surface: pygame.Surface, lb: Label) -> None:
        age = 1 - lb.life / lb.max_life
        alpha = 255 if age < 0.7 else int(255 * (1 - age) / 0.3)
        if lb.comic:
            base = _text_surface(lb.text, lb.color, lb.size, 3)
            if age < 0.2:
                scale = 0.4 + 0.8 * age / 0.2
            elif age < 0.35:
                scale = 1.2 - 0.2 * (age - 0.2) / 0.15
            else:
                scale = 1.0
            img = pygame.transform.rotozoom(base, lb.angle, scale)
        else:
            img = _text_surface(lb.text, lb.color, lb.size, 2).copy()
        if alpha < 255:
            img.set_alpha(alpha)
        surface.blit(img, img.get_rect(center=(int(lb.pos.x), int(lb.pos.y))))

    def draw_overlay(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Screen flash (e.g. red when the stash is hit), drawn over the playfield."""
        if self.flash_time <= 0:
            return
        a = int(self.flash_alpha * self.flash_time / self.flash_max)
        overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
        overlay.fill((*self.flash_color, a))
        surface.blit(overlay, rect.topleft)
