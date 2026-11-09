"""Visual effects primitives: particles, expanding rings, floating text, comic-style
pop-up words ("POW!"), screen shake and screen flash. Pure visuals, no game logic."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pygame

from data.settings import PLAYFIELD_RECT
from game.utils import Vec, get_font

MAX_PARTICLES = 500  # High; Low uses 1/4 of this (see VFX.max_particles)
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
        if len(_TEXT_CACHE) > 900:
            _TEXT_CACHE.clear()
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
        self.max_particles = getattr(self, "max_particles", MAX_PARTICLES)
        self.shake_enabled = getattr(self, "shake_enabled", True)
        self.comics_enabled = getattr(self, "comics_enabled", True)
        w, h = PLAYFIELD_RECT[2], PLAYFIELD_RECT[3]
        # slow drifting pollen/dust: [x, y, vx, vy, phase, size]
        self.motes = [[random.uniform(0, w), random.uniform(0, h), random.uniform(-6, 6),
                       random.uniform(-9, -2), random.uniform(0, 6.3), random.uniform(1.2, 2.4)]
                      for _ in range(22)]
        self.particles: list[Particle] = []
        self.rings: list[Ring] = []
        self.labels: list[Label] = []
        self.bolts: list[list] = []   # lightning: [points, life, max_life, color, width]
        self.flies: list[list] = []   # shapes flying to a point: [start, end, t, dur, sprite, spin]
        self.pops: list[list] = []    # additive glow flashes: [pos, radius, life, max_life, color]
        self.tornados: list[list] = []  # spinning funnels: [pos, life, max_life, scale, color, phase]
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
            if len(self.particles) >= self.max_particles:
                return
            ang = random.uniform(0, math.tau)
            spd = random.uniform(0.3, 1.0) * speed
            self.particles.append(Particle(Vec(pos), Vec(math.cos(ang), math.sin(ang)) * spd,
                                           life * random.uniform(0.7, 1.2), life, color,
                                           size * random.uniform(0.7, 1.3), gravity))

    def sparkle(self, pos, color, n: int = 10) -> None:
        """Slow rising glitter (upgrades, stacks)."""
        for _ in range(n):
            if len(self.particles) >= self.max_particles:
                return
            off = Vec(random.uniform(-16, 16), random.uniform(-10, 10))
            self.particles.append(Particle(Vec(pos) + off, Vec(random.uniform(-15, 15), random.uniform(-70, -30)),
                                           0.7, 0.7, color, random.uniform(2, 4), -20))

    def trail(self, pos, color) -> None:
        if len(self.particles) < self.max_particles:
            self.particles.append(Particle(Vec(pos), Vec(0, 0), 0.22, 0.22, color, 3.5, 0))

    def ring(self, pos, r0: float, r1: float, life: float, color, width: int = 3) -> None:
        self.rings.append(Ring(Vec(pos), r0, r1, life, life, color, width))

    def text(self, pos, text: str, color=(255, 255, 255), size: int = 24,
             life: float = 0.9, rise: float = 40) -> None:
        self.labels.append(Label(Vec(pos), text, color, size, life, life, rise))

    def comic(self, pos, text: str, color=(255, 230, 60), size: int = 34, life: float = 0.7) -> None:
        if not self.comics_enabled or sum(1 for lb in self.labels if lb.comic) >= MAX_COMICS:
            return
        self.labels.append(Label(Vec(pos), text, color, size, life, life, rise=20,
                                 angle=random.uniform(-12, 12), comic=True))

    def lightning(self, a, b, color=(255, 240, 140), life: float = 0.25, width: int = 4, jitter: float = 16) -> None:
        a, b = Vec(a), Vec(b)
        n = max(3, int(a.distance_to(b) / 22))
        d = (b - a)
        nrm = Vec(-d.y, d.x).normalize() if d.length() else Vec(1, 0)
        pts = [a]
        for i in range(1, n):
            pts.append(a + d * (i / n) + nrm * random.uniform(-jitter, jitter))
        pts.append(b)
        self.bolts.append([pts, life, life, color, width])

    def fly(self, start, end, sprite, dur: float = 0.1, spin: float = 360) -> None:
        self.flies.append([Vec(start), Vec(end), 0.0, dur, sprite, spin])

    def pop(self, pos, radius: float, color, life: float = 0.2) -> None:
        self.pops.append([Vec(pos), radius, life, life, color])

    def tornado(self, pos, life: float = 0.7, scale: float = 1.0, color=(190, 230, 255)) -> None:
        """A small whirlwind funnel on the ground at `pos` (Johnny's spin). At most 10 at once."""
        if len(self.tornados) >= 10:
            self.tornados.pop(0)
        self.tornados.append([Vec(pos), life, life, scale, color, random.uniform(0, math.tau)])

    def suck(self, pos, radius: float, color, n: int = 4, life: float = 0.3, size: float = 3) -> None:
        """Charging: particles start on a ring around `pos` and rush into its centre."""
        for _ in range(n):
            if len(self.particles) >= self.max_particles:
                return
            a = random.uniform(0, math.tau)
            r = radius * random.uniform(0.7, 1.1)
            start = Vec(pos) + Vec(math.cos(a), math.sin(a) * 0.8) * r
            vel = (Vec(pos) - start) / life
            self.particles.append(Particle(start, vel, life, life, color, size * random.uniform(0.7, 1.3), 0))

    def shake(self, amp: float, seconds: float) -> None:
        if self.shake_enabled and (amp >= self.shake_amp or self.shake_time <= 0):
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
        for b in self.bolts:
            b[1] -= dt
        self.bolts = [b for b in self.bolts if b[1] > 0]
        for f in self.flies:
            f[2] += dt
        self.flies = [f for f in self.flies if f[2] < f[3]]
        for pp in self.pops:
            pp[2] -= dt
        self.pops = [pp for pp in self.pops if pp[2] > 0]
        for tn in self.tornados:
            tn[1] -= dt
            tn[5] += dt * 14
        self.tornados = [tn for tn in self.tornados if tn[1] > 0]
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
        from game import gfx
        for pos, radius, life, max_life, color in self.pops:  # additive glow flashes
            g = gfx.glow(int(radius * (0.6 + 0.6 * (1 - life / max_life))), color, int(255 * life / max_life))
            surface.blit(g, g.get_rect(center=(int(pos.x), int(pos.y))), special_flags=pygame.BLEND_RGB_ADD)
        for tn in self.tornados:
            self._draw_tornado(surface, tn)
        for pts, life, max_life, color, width in self.bolts:
            a = life / max_life
            col = tuple(int(c * a) for c in color)
            pygame.draw.lines(surface, tuple(int(c * 0.35 * a) for c in color), False, pts, width + 6)
            pygame.draw.lines(surface, col, False, pts, width)
            pygame.draw.lines(surface, (int(255 * a),) * 3, False, pts, max(1, width // 2))
        for start, end, t, dur, spr, spin in self.flies:
            k = min(1.0, t / dur)
            k = k * k * k
            pos = start.lerp(end, k)
            img = pygame.transform.rotozoom(spr, spin * t, 1.0 - 0.3 * k)
            surface.blit(img, img.get_rect(center=(int(pos.x), int(pos.y))))
        for lb in self.labels:
            self._draw_label(surface, lb)

    @staticmethod
    def _draw_tornado(surface: pygame.Surface, tn: list) -> None:
        """Funnel made of stacked spinning rings that widen towards the top, with orbiting debris specks."""
        pos, life, max_life, scale, color, phase = tn
        age = max_life - life
        grow = min(1.0, age / 0.14) * min(1.0, life / 0.22)   # grows in fast, fades out
        if grow <= 0:
            return
        h = int(84 * scale)
        w = int(76 * scale)
        tmp = pygame.Surface((w * 2, h + 24), pygame.SRCALPHA)
        cx, base_y = w, h + 14
        levels = 9
        for i in range(levels):
            k = i / (levels - 1)
            ry = (3 + 5 * k) * scale
            rx = (6 + 24 * k ** 0.9) * scale * grow
            y = base_y - k * h * grow
            ang = phase + i * 0.8
            alpha = int(235 * grow * (1 - 0.35 * k))
            box = pygame.Rect(0, 0, rx * 2, ry * 2)
            box.center = (cx, y)
            wdt = max(2, int(3.5 * scale))
            pygame.draw.arc(tmp, (50, 90, 150, int(alpha * 0.8)), box.inflate(2, 2), ang, ang + 3.6, wdt + 2)   # dark underlay: readable on light grass
            pygame.draw.arc(tmp, (*color, alpha), box, ang, ang + 3.6, wdt)
            pygame.draw.arc(tmp, (255, 255, 255, int(alpha * 0.85)), box, ang + math.pi, ang + math.pi + 1.4, 2)
            sx = cx + math.cos(ang * 1.3) * rx
            sy = y + math.sin(ang * 1.3) * ry
            pygame.draw.circle(tmp, (255, 255, 255, int(alpha * 0.9)), (int(sx), int(sy)), max(1, int(2 * scale)))
        surface.blit(tmp, tmp.get_rect(midbottom=(int(pos.x), int(pos.y) + 12)))

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
