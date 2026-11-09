"""Procedural MODELS: character costumes + hair, held weapons, projectiles, floating props, Mark's runner.

Same style as game/sprites_proc.py (lit spheres from game/gfx.py, drawn at SS x supersampling, cached,
single light from the top-left). Models only: no gameplay logic, no sound, no particles.

Looks
-----
A tower's `look` is None (base) or (path, tier) from `look_of(kind, tiers)`: path 0 = A, 1 = B, tier 1..4.
  jalu   A = Mark (blue/yellow hero suit, mask, cape at 4)      B = Loki (green suit, gold horns, scepter, loom)
  romli  A = Business (shirt+tie -> suit -> gold -> crown)       B = Programmer (hoodie, headphones, code screens)
  zizi   A = Recitation (shawl, halo)                            B = Sloth (pajamas, sleepy eyes, pillow)
  bima   A = Graph (pencil, lab coat, hologram wave)             B = Geometry (orbiting shapes, laurel)
  fadhli A = Garp (white marine coat draped over the shoulders, iron gloves, gold trim)
         B = Johnny Joestar (feathered hat, wide-collar jacket, spiral belt) + the Tusk stand (Act 1 / 3 / 4)
  fused_jalu_romli  (fusion tower, not in the game yet): vest + headset.

Public API: look_of, costume, draw_hair, weapon_image, projectile, prop, draw_companion, mark_runner.
"""
from __future__ import annotations

import math

import pygame

from game import gfx

S = gfx.SS
_CACHE: dict[tuple, object] = {}


def look_of(kind: str, tiers) -> tuple[int, int] | None:
    """(path, tier) of the path the tower follows, or None for a base tower. Ties go to path A."""
    a, b = tiers
    if a > 0 and a >= b:
        return (0, a)
    if b > 0:
        return (1, b)
    return None


def _cut_below(img: pygame.Surface, y: int) -> pygame.Surface:
    img = img.copy()
    pygame.draw.rect(img, (0, 0, 0, 0), (0, y, img.get_width(), img.get_height() - y))
    return img


class Ctx:
    """Drawing context for a tower canvas. Coordinates are in tower-radius units, origin = pedestal centre,
    x right, y down. Heads sit at (0, -1.32) with radius 0.66, the body spans y -1.18..0.14."""

    def __init__(self, cv: pygame.Surface, radius: float, st: dict) -> None:
        self.cv, self.r, self.st = cv, radius, st
        self.u = radius * S
        self.ox, self.oy = cv.get_width() / 2, 3.45 * self.u

    def P(self, x: float, y: float) -> tuple[float, float]:
        return (self.ox + x * self.u, self.oy + y * self.u)

    def put(self, img: pygame.Surface, x: float, y: float) -> None:
        big = pygame.transform.smoothscale(img, (img.get_width() * S, img.get_height() * S))
        px, py = self.P(x, y)
        self.cv.blit(big, big.get_rect(center=(round(px), round(py))))

    def sph(self, rad: float, color, x: float, y: float, shine: float = 0.8) -> None:
        self.put(gfx.sphere(rad * self.r, color, shine=shine), x, y)

    def ell(self, w: float, h: float, color, x: float, y: float, **kw) -> None:
        self.put(gfx.ellipsoid(max(2, int(w * self.r)), max(2, int(h * self.r)), color, **kw), x, y)

    def poly(self, color, pts, outline=None, width: float = 0.05) -> None:
        gfx.poly(self.cv, color, [self.P(*p) for p in pts], outline, max(1, int(width * self.u)))

    def line(self, color, a, b, w: float = 0.05) -> None:
        pygame.draw.line(self.cv, color, self.P(*a), self.P(*b), max(1, int(w * self.u)))

    def lines(self, color, pts, w: float = 0.05) -> None:
        pygame.draw.lines(self.cv, color, False, [self.P(*p) for p in pts], max(1, int(w * self.u)))

    def circle(self, color, x, y, rad: float, width: float = 0.0) -> None:
        pygame.draw.circle(self.cv, color, self.P(x, y), rad * self.u, max(0, int(width * self.u)))

    def ellipse(self, color, x, y, w, h, width: float = 0.0) -> None:
        pygame.draw.ellipse(self.cv, color, (*self.P(x - w / 2, y - h / 2), w * self.u, h * self.u), max(0, int(width * self.u)))

    def glow(self, rad: float, color, alpha: int, x: float, y: float) -> None:
        g = gfx.glow(max(4, int(rad * self.u)), color, alpha)
        self.cv.blit(g, g.get_rect(center=self.P(x, y)))


# ====================================================================== costumes
GOLD, GOLD_D = (255, 206, 60), (150, 100, 20)


def costume(kind: str, look) -> dict:
    """Parts of a costume: `style` (colour overrides) and optional hooks back / body / behind_head / face / front
    (each takes a Ctx). `hair` may force a hairstyle. Base towers return {}."""
    if kind == "fused_jalu_romli":
        return {"style": {"shirt": (46, 168, 176), "shoes": (240, 240, 240)}, "body": _fused_vest, "front": _fused_headset}
    if look is None:
        return {}
    path, tier = look
    table = {("jalu", 0): _mark, ("jalu", 1): _loki, ("romli", 0): _business, ("romli", 1): _coder,
             ("zizi", 0): _recitation, ("zizi", 1): _sloth, ("bima", 0): _graph, ("bima", 1): _geometry, ("fadhli", 0): _garp, ("fadhli", 1): _johnny}
    fn = table.get((kind, path))
    return fn(tier) if fn else {}


def _cape(c: Ctx, col, edge, wide: float = 0.95) -> None:
    c.poly(gfx.shade(col, 0.75), [(-0.45, -1.1), (0.45, -1.1), (wide, 0.2), (0.35, 0.34), (-0.35, 0.28), (-wide, 0.2)], edge, 0.04)
    c.poly(col, [(-0.35, -1.05), (0.35, -1.05), (0.7, 0.1), (0, 0.22), (-0.7, 0.1)])


# ---- Jalu path A: Mark
def _mark(tier: int) -> dict:
    blue, yellow = (36, 84, 196), (244, 204, 52)

    def back(c: Ctx) -> None:
        if tier >= 4:
            _cape(c, (206, 48, 56), (90, 14, 24))

    def body(c: Ctx) -> None:
        c.poly(yellow, [(-0.1, -1.1), (0.1, -1.1), (0.1, 0.0), (-0.1, 0.0)])   # chest stripe
        c.poly(yellow, [(-0.18, -0.85), (0.04, -0.85), (-0.02, -0.65), (0.2, -0.65), (-0.14, -0.28), (-0.06, -0.55), (-0.24, -0.55)],
               (120, 80, 10), 0.02)                                          # bolt emblem
        c.line((30, 30, 40), (-0.6, -0.1), (0.6, -0.1), 0.12)                # belt
        c.circle(yellow, 0, -0.1, 0.09)
        if tier >= 2:
            for dx in (-0.64, 0.64):                                          # yellow shoulder guards
                c.sph(0.26, yellow, dx, -0.98)

    def face(c: Ctx) -> None:
        c.ellipse((18, 18, 28), 0, -1.28, 1.16, 0.36)                        # eye mask
        eye = (255, 70, 60) if tier >= 3 else (255, 255, 255)
        for dx in (-0.24, 0.24):
            c.ellipse(eye, dx, -1.28, 0.2, 0.12)
        if tier >= 3:                                                         # "Think, Mark!": angry brows
            for sx in (-1, 1):
                c.line((20, 14, 20), (sx * 0.08, -1.44), (sx * 0.42, -1.5 + 0.0), 0.08)
            c.glow(0.34, (255, 60, 50), 120, -0.24, -1.28)
            c.glow(0.34, (255, 60, 50), 120, 0.24, -1.28)

    return {"style": {"shirt": blue, "shoes": yellow, "glove": yellow}, "back": back, "body": body, "face": face}


# ---- Jalu path B: Loki
def _loki(tier: int) -> dict:
    green, gold = (28, 112, 72), (236, 190, 60)

    def back(c: Ctx) -> None:
        if tier >= 2:
            _cape(c, (22, 90, 60), (8, 40, 26), 0.9)

    def body(c: Ctx) -> None:
        c.lines(gold, [(-0.55, -1.0), (-0.1, -0.7), (0.1, -0.7), (0.55, -1.0)], 0.1)   # gold collar / straps
        c.line(gold, (0, -0.7), (0, 0.0), 0.08)
        c.line(gold, (-0.6, -0.08), (0.6, -0.08), 0.1)
        if tier >= 3:
            for dx in (-0.62, 0.62):
                c.sph(0.22, gold, dx, -0.98)

    def front(c: Ctx) -> None:
        big = 1.25 if tier >= 4 else 1.0
        for sx in (-1, 1):                                                    # curved gold horns
            c.poly(gold, [(sx * 0.42, -1.86), (sx * 0.74, -2.0 - 0.1 * big), (sx * (0.9 + 0.1 * big), -2.55 * big + 0.28),
                          (sx * 0.62, -2.08), (sx * 0.3, -1.98)], GOLD_D, 0.03)
            c.line(gfx.tint(gold, 0.6), (sx * 0.5, -1.95), (sx * 0.8, -2.12), 0.03)
        c.ellipse(gold, 0, -1.78, 1.1, 0.3)                                   # helmet band
        c.ellipse(gfx.tint(gold, 0.5), -0.2, -1.82, 0.4, 0.08)
        c.circle((120, 220, 255), 0, -1.78, 0.07)

    return {"style": {"shirt": green, "shoes": (36, 36, 40), "glove": (30, 60, 44)}, "back": back, "body": body,
            "front": front, "hair": "slick"}


# ---- Romli path A: business
def _business(tier: int) -> dict:
    suit = (44, 52, 70) if tier == 2 else (30, 34, 48) if tier >= 3 else (236, 236, 240)
    tie = (60, 190, 110) if tier <= 2 else GOLD

    def back(c: Ctx) -> None:
        if tier >= 4:
            _cape(c, (255, 206, 60), GOLD_D, 0.85)

    def body(c: Ctx) -> None:
        if tier >= 2:  # white shirt triangle under the jacket
            c.poly((246, 246, 250), [(-0.2, -1.12), (0.2, -1.12), (0.0, -0.55)])
            for sx in (-1, 1):  # lapels
                c.poly(gfx.shade(suit, 1.25), [(sx * 0.22, -1.12), (sx * 0.5, -1.0), (sx * 0.1, -0.35), (sx * 0.02, -0.6)], (10, 10, 16), 0.02)
        c.poly(tie, [(-0.07, -1.0), (0.07, -1.0), (0.12, -0.45), (0, -0.28), (-0.12, -0.45)], gfx.shade(tie, 0.6), 0.02)
        if tier >= 3:
            c.circle(GOLD, 0.63, -0.42, 0.1)                                  # gold watch on the wrist
            c.circle(GOLD_D, 0.63, -0.42, 0.1, 0.03)
        if tier >= 1 and tier < 3:  # little briefcase
            c.ell(0.5, 0.36, (140, 90, 50), -0.62, -0.22)
            c.line((60, 36, 20), (-0.84, -0.22), (-0.4, -0.22), 0.04)

    def front(c: Ctx) -> None:
        if tier >= 4:
            crown = [(-0.4, -1.98), (-0.4, -2.38), (-0.2, -2.16), (0, -2.46), (0.2, -2.16), (0.4, -2.38), (0.4, -1.98)]
            c.poly(GOLD, crown, GOLD_D, 0.04)
            for dx, col in ((-0.2, (230, 50, 50)), (0, (60, 160, 255)), (0.2, (230, 50, 50))):
                c.circle(col, dx, -2.1, 0.05)

    return {"style": {"shirt": suit, "shoes": (40, 34, 30) if tier >= 2 else (50, 42, 46)}, "back": back, "body": body, "front": front}


# ---- Romli path B: programmer
def _coder(tier: int) -> dict:
    hood = (52, 58, 78)

    def behind(c: Ctx) -> None:
        c.ell(1.35, 0.9, gfx.shade(hood, 0.8), 0, -0.98)                     # hood bunched at the neck

    def body(c: Ctx) -> None:
        c.line((20, 22, 30), (-0.12, -1.0), (-0.16, -0.5), 0.04)             # hoodie strings
        c.line((20, 22, 30), (0.12, -1.0), (0.16, -0.5), 0.04)
        c.ell(0.7, 0.3, gfx.shade(hood, 0.9), 0, -0.22)                      # kangaroo pocket
        if tier >= 2:
            c.lines((90, 255, 150), [(-0.22, -0.7), (-0.32, -0.6), (-0.22, -0.5)], 0.04)   # </> on the chest
            c.lines((90, 255, 150), [(0.22, -0.7), (0.32, -0.6), (0.22, -0.5)], 0.04)
            c.line((90, 255, 150), (0.05, -0.74), (-0.05, -0.46), 0.04)

    def front(c: Ctx) -> None:
        c.lines((24, 24, 30), [(-0.7, -1.3), (-0.62, -1.9), (0, -2.08), (0.62, -1.9), (0.7, -1.3)], 0.09)   # headphones band
        for sx in (-1, 1):
            c.sph(0.2, (36, 40, 52), sx * 0.7, -1.28)
            c.circle((90, 255, 150) if tier >= 2 else (120, 130, 150), sx * 0.7, -1.28, 0.07)

    return {"style": {"shirt": hood, "shoes": (230, 230, 236)}, "behind_head": behind, "body": body, "front": front}


# ---- Zizi path A: recitation
def _recitation(tier: int) -> dict:
    cream = (250, 240, 214)

    def back(c: Ctx) -> None:
        if tier >= 3:  # soft halo behind the head
            big = 0.5 if tier >= 4 else 0.0
            c.glow(1.2 + big, (255, 232, 140), 120, 0, -1.5)
            c.ellipse((255, 224, 120), 0, -2.12, 1.0 + big * 0.4, 0.26, 0.05)

    def body(c: Ctx) -> None:
        c.ell(1.5, 0.62, cream, 0, -1.02)                                     # shawl over the shoulders
        c.lines((236, 190, 70), [(-0.7, -0.92), (-0.3, -0.76), (0.3, -0.76), (0.7, -0.92)], 0.05)
        c.poly(cream, [(-0.1, -0.9), (0.14, -0.9), (0.2, -0.36), (-0.06, -0.3)], (210, 180, 120), 0.02)
        if tier >= 2:
            c.circle((236, 190, 70), 0, -0.78, 0.07)

    return {"style": {}, "back": back, "body": body}


# ---- Zizi path B: sloth
def _sloth(tier: int) -> dict:
    pj = (196, 186, 232)

    def body(c: Ctx) -> None:
        for x, y in ((-0.3, -0.9), (0.28, -0.6), (-0.1, -0.35), (0.36, -0.95)):   # moons/stars on the pajamas
            c.circle((255, 236, 150), x, y, 0.05)
        c.line((150, 140, 196), (-0.58, -0.2), (0.58, -0.2), 0.05)

    def face(c: Ctx) -> None:
        skin = c.st["skin"]
        for dx in (-0.24, 0.24):
            if tier >= 3:   # fast asleep: closed eyes
                c.circle(skin, dx, -1.28, 0.13)
                c.lines((40, 28, 50), [(dx - 0.12, -1.27), (dx, -1.2), (dx + 0.12, -1.27)], 0.04)
            else:           # half-lidded
                c.ellipse(skin, dx, -1.34, 0.3, 0.22)
                c.line((40, 28, 50), (dx - 0.13, -1.27), (dx + 0.13, -1.27), 0.04)
            if tier >= 2:   # eye bags
                c.lines((160, 110, 130), [(dx - 0.12, -1.13), (dx, -1.09), (dx + 0.12, -1.13)], 0.025)

    return {"style": {"shirt": pj}, "body": body, "face": face}


# ---- Bima path A: graph
def _graph(tier: int) -> dict:
    def body(c: Ctx) -> None:
        if tier >= 2:  # open white lab coat: the pi on the shirt stays visible
            coat = (244, 246, 250)
            for sx in (-1, 1):
                c.poly(coat, [(sx * 0.62, -1.1), (sx * 0.28, -1.1), (sx * 0.26, 0.1), (sx * 0.66, 0.1)], (170, 176, 190), 0.025)
                c.poly(gfx.shade(coat, 0.9), [(sx * 0.28, -1.1), (sx * 0.5, -0.98), (sx * 0.22, -0.7)], (170, 176, 190), 0.02)
            c.line((90, 140, 220), (0.46, -0.45), (0.54, -0.2), 0.05)         # pen in the pocket
        if tier >= 3:
            for sx in (-1, 1):
                c.lines((90, 160, 255), [(sx * 0.4, -0.3), (sx * 0.5, -0.4), (sx * 0.56, -0.3)], 0.02)

    def front(c: Ctx) -> None:
        c.line((255, 200, 60), (0.52, -1.52), (0.72, -1.2), 0.07)             # pencil behind the ear
        c.line((60, 40, 30), (0.7, -1.23), (0.74, -1.17), 0.07)
        c.line((240, 130, 150), (0.5, -1.55), (0.53, -1.5), 0.07)

    return {"style": {}, "body": body, "front": front}


# ---- Bima path B: geometry
def _geometry(tier: int) -> dict:
    def front(c: Ctx) -> None:
        if tier >= 4:  # Euclid's laurel wreath
            for sx in (-1, 1):
                for i in range(5):
                    a = 0.15 + i * 0.26
                    c.ell(0.2, 0.1, (90, 170, 80), sx * (0.5 + 0.18 * math.sin(a * 2.2)), -1.78 + i * 0.1 + 0.0)
            c.circle((255, 206, 60), 0, -1.99, 0.07)

    def body(c: Ctx) -> None:
        c.poly((255, 220, 70), [(0.34, -0.5), (0.6, -0.5), (0.47, -0.25)], (120, 80, 10), 0.02)   # triangle badge

    return {"style": {}, "body": body, "front": front}


# ---- Fadhli path A: Garp (clothes only: the marine coat worn draped over the shoulders)
def _garp(tier: int) -> dict:
    coat, coat_s, edge = (247, 248, 252), (190, 196, 212), (128, 136, 158)
    navy = (28, 40, 92)
    gold = (236, 190, 60)

    def back(c: Ctx) -> None:           # the long coat hanging down his back
        c.poly(coat_s, [(-0.56, -1.12), (0.56, -1.12), (1.04, 0.24), (0.4, 0.38), (-0.4, 0.38), (-1.04, 0.24)], edge, 0.03)
        c.poly(coat, [(-0.44, -1.08), (0.44, -1.08), (0.86, 0.14), (0, 0.28), (-0.86, 0.14)])
        if tier >= 3:
            c.lines(gold, [(-1.04, 0.24), (-0.4, 0.38), (0.4, 0.38), (1.04, 0.24)], 0.045)

    def body(c: Ctx) -> None:
        for sx in (-1, 1):              # open coat flaps with lapels, the navy shirt shows in the middle
            c.poly(coat, [(sx * 0.72, -1.14), (sx * 0.30, -1.12), (sx * 0.26, 0.12), (sx * 0.8, 0.14)], edge, 0.025)
            c.poly(coat_s, [(sx * 0.30, -1.12), (sx * 0.58, -1.0), (sx * 0.2, -0.66)], edge, 0.02)
            c.sph(0.3, coat, sx * 0.64, -1.0, 0.7)                                        # coat bulging over the shoulder
            if tier >= 3:
                c.line(gold, (sx * 0.27, -1.1), (sx * 0.24, 0.1), 0.04)                   # gold trim on the edges
        c.circle(navy, 0, -0.74, 0.17)                                                    # marine badge on the shirt
        c.circle((250, 250, 255), 0, -0.74, 0.1)
        c.line((190, 40, 50), (-0.07, -0.74), (0.07, -0.74), 0.05)
        c.line((30, 30, 40), (-0.2, -0.04), (0.2, -0.04), 0.09)                           # belt peeking out
        if tier >= 4:
            for sx in (-1, 1):
                c.sph(0.2, gold, sx * 0.7, -1.16, 0.8)                                   # gold epaulettes

    iron = (126, 134, 154)
    style = {"shirt": navy, "shoes": (36, 36, 44)}
    if tier >= 2:
        style["glove"] = iron                                                             # "Iron Fist" gauntlets
    return {"style": style, "back": back, "body": body}


# ---- Fadhli path B: Johnny Joestar (approximate: feathered hat, wide pointed collar, spiral belt buckle)
def _johnny(tier: int) -> dict:
    jacket, collar, edge = (34, 112, 108), (22, 78, 76), (10, 44, 42)
    hat, hat_d, gold = (36, 44, 76), (22, 26, 48), (240, 196, 70)

    def body(c: Ctx) -> None:
        for sx in (-1, 1):
            c.poly(jacket, [(sx * 0.66, -1.12), (sx * 0.26, -1.12), (sx * 0.24, 0.12), (sx * 0.7, 0.12)], edge, 0.025)
            c.poly(collar, [(sx * 0.28, -1.16), (sx * 0.86, -1.24), (sx * 0.54, -0.74)], edge, 0.02)   # big pointed collar
        c.line((22, 22, 30), (-0.66, -0.06), (0.66, -0.06), 0.13)                                      # belt
        c.circle(gold, 0, -0.06, 0.13)
        pts = [(0.0 + 0.012 * 1.618 ** (a / 1.2) * math.cos(a * 2.0), -0.06 + 0.012 * 1.618 ** (a / 1.2) * math.sin(a * 2.0)) for a in [i * 0.4 for i in range(9)]]
        c.lines((120, 80, 14), pts, 0.02)                                                              # spiral on the buckle
        if tier >= 3:
            for sx in (-1, 1):
                for k in range(3):
                    c.circle(gold, sx * (0.56 + 0.04 * k), -1.0 + 0.1 * k, 0.04)                       # studs on the collar
        if tier >= 4:                                                                                  # golden spiral glow on the chest
            sp = [(0.35 * 0.1 * 1.618 ** (a / 1.1) * math.cos(a * 2.0 + 1.0) - 0.0, -0.58 + 0.1 * 1.618 ** (a / 1.1) * math.sin(a * 2.0 + 1.0) * 0.9)
                  for a in [i * 0.3 for i in range(14)]]
            c.glow(0.5, (255, 214, 70), 90, 0, -0.58)
            c.lines((255, 226, 110), sp, 0.03)

    def front(c: Ctx) -> None:            # flat cap with a gold band and a feather
        c.ellipse(hat_d, 0, -1.84, 1.46, 0.34)                                                         # brim
        c.ell(1.12, 0.78, hat, 0, -2.0, shine=0.7)                                                     # crown
        c.line(gold, (-0.52, -1.9), (0.52, -1.9), 0.07)
        c.poly((255, 150, 176), [(0.38, -1.98), (0.62, -2.34), (0.82, -2.7), (0.68, -2.3), (0.52, -1.96)], (170, 70, 96), 0.02)
        c.line((255, 210, 220), (0.42, -2.0), (0.8, -2.66), 0.025)

    return {"style": {"shirt": (236, 236, 226), "shoes": (60, 44, 34), "glove": (60, 44, 34)}, "body": body, "front": front}


# ---- Fusion
def _fused_vest(c: Ctx) -> None:
    grey = (96, 104, 120)
    for sx in (-1, 1):
        c.poly(grey, [(sx * 0.62, -1.1), (sx * 0.2, -1.1), (sx * 0.22, 0.1), (sx * 0.62, 0.1)], (40, 44, 56), 0.025)
    c.line((170, 176, 190), (-0.4, -0.55), (0.4, -0.55), 0.03)
    c.lines(GOLD, [(-0.2, -1.05), (0, -0.78), (0.2, -1.05)], 0.05)            # gold chain


def _fused_headset(c: Ctx) -> None:
    c.lines((24, 24, 30), [(-0.68, -1.3), (-0.6, -1.9), (0, -2.04), (0.6, -1.9), (0.68, -1.3)], 0.08)
    for sx in (-1, 1):
        c.sph(0.18, (36, 40, 52), sx * 0.68, -1.28)
    c.lines((24, 24, 30), [(-0.68, -1.2), (-0.6, -0.95), (-0.25, -0.95)], 0.04)   # mic boom
    c.circle((255, 80, 80), -0.25, -0.95, 0.06)


# ========================================================================= hair
def draw_hair(c: Ctx, kind: str, cos: dict) -> None:
    """Hair, drawn after the head. Romli: short + messy. Zizi: short, no hat. Bima: buzz cut."""
    st, r = c.st, c.r
    hair = st["hair"]
    if kind == "romli":                                                       # short, messy (2026-11-02)
        cap = gfx.sphere(0.68 * r, hair, shine=0.6)
        c.put(_cut_below(cap, int(cap.get_height() * 0.45)), 0, -1.42)
        for x, h, lean in ((-0.52, 0.20, -0.10), (-0.30, 0.30, -0.06), (-0.06, 0.22, 0.04),
                           (0.18, 0.32, 0.10), (0.42, 0.24, 0.12), (0.58, 0.14, 0.14)):   # uneven tufts, different heights
            c.poly(hair, [(x - 0.12, -1.80), (x + lean, -1.80 - h - 0.04), (x + 0.12, -1.80)])
        for x, y in ((-0.34, -1.64), (0.02, -1.68), (0.36, -1.62)):           # a few loose strands over the forehead
            c.line(hair, (x, y), (x + 0.07, y + 0.12), 0.07)
        hi = gfx.tint(hair, 0.28)
        c.lines(hi, [(-0.4, -1.84), (-0.1, -1.92), (0.2, -1.9)], 0.03)
        return
    if kind == "bima":
        cap = gfx.sphere(0.68 * r, hair, shine=0.5)
        c.put(_cut_below(cap, int(cap.get_height() * 0.42)), 0, -1.38)
        for i in range(14):                                                   # buzz-cut stubble
            a = math.pi * (1.05 + 0.9 * i / 13)
            c.circle(gfx.tint(hair, 0.22), 0.6 * math.cos(a), -1.32 + 0.6 * math.sin(a) * 1.0, 0.04)
        return
    if kind == "zizi":                                                        # short hair, no hat (2026-11-02)
        cap = gfx.sphere(0.69 * r, hair, shine=0.8)
        c.put(_cut_below(cap, int(cap.get_height() * 0.46)), 0, -1.46)
        for x, y in ((-0.40, -1.74), (-0.12, -1.80), (0.16, -1.78), (0.42, -1.72)):   # short cropped top
            c.sph(0.15, hair, x, y, 0.8)
        c.poly(hair, [(-0.52, -1.66), (0.34, -1.54), (0.5, -1.66), (0.1, -1.78)])     # short side-swept fringe
        for sx in (-1, 1):                                                    # sideburns, above the ears
            c.ell(0.1, 0.2, hair, sx * 0.62, -1.36, shine=0.5)
        return
    if kind == "fadhli":                                                      # short dark hair with a side fringe
        cap = gfx.sphere(0.69 * r, hair, shine=0.7)
        c.put(_cut_below(cap, int(cap.get_height() * 0.46)), 0, -1.46)
        c.poly(hair, [(-0.54, -1.62), (0.4, -1.52), (0.52, -1.66), (0.12, -1.8), (-0.3, -1.78)])
        for sx in (-1, 1):
            c.ell(0.1, 0.2, hair, sx * 0.62, -1.36, shine=0.5)
        return
    hair_img = gfx.sphere(0.70 * r, hair, shine=0.9)
    if cos.get("hair") == "slick":                                            # Loki: slicked-back black hair
        c.put(_cut_below(hair_img, int(hair_img.get_height() * 0.5)), 0, -1.56)
        c.line(gfx.tint(hair, 0.4), (-0.35, -1.9), (0.3, -2.0), 0.03)
        return
    c.put(_cut_below(hair_img, int(hair_img.get_height() * 0.50)), 0, -1.56)
    if kind in ("jalu", "fused_jalu_romli"):
        for dx in (-0.36, 0.0, 0.36):                                         # spiky hair
            c.poly(hair, [(dx - 0.2, -1.82), (dx + 0.02, -2.28 + abs(dx) * 0.2), (dx + 0.2, -1.82)])


def hair_back(c: Ctx, kind: str) -> None:
    """Nothing hangs behind the head any more (Zizi's long hair was cut on 2026-11-02). Kept as a hook."""
    return


# =================================================================== weapons (held)
def _weapon_surface(kind: str, look) -> pygame.Surface | None:
    """Weapon pointing RIGHT, grip at the canvas centre. None = no weapon (Mark punches)."""
    L = 36
    cv = gfx.blank(2 * L * S, 2 * L * S)
    c = L * S

    def X(x, y=0.0):
        return (c + x * S, c + y * S)

    def poly(col, pts, outline=None, w=1.2):
        gfx.poly(cv, col, [X(*p) for p in pts], outline, max(1, int(w * S)))

    def ball(rad, col, x, y, shine=1.0):
        big = pygame.transform.smoothscale(gfx.sphere(rad, col, shine=shine), (int((2 * rad + 2) * S), int((2 * rad + 2) * S)))
        cv.blit(big, big.get_rect(center=X(x, y)))

    path = look[0] if look else None
    if kind == "jalu" and path == 0:
        return None
    if kind == "jalu" and path == 1:     # Loki's scepter
        poly(GOLD_D, [(-8, -1.8), (26, -1.8), (26, 1.8), (-8, 1.8)])
        poly(GOLD, [(-8, -1.3), (26, -1.3), (26, 0.4), (-8, 0.4)])
        for sx in (-1, 1):
            poly(GOLD, [(24, sx * 1.2), (30, sx * 6.5), (34, sx * 5.2), (29, sx * 1.8)], GOLD_D, 0.8)
        cv.blit(gfx.glow(11 * S // 2, (120, 220, 255), 200), gfx.glow(11 * S // 2, (120, 220, 255), 200).get_rect(center=X(30)))
        ball(4.2, (120, 210, 255), 30, 0)
        for x in (-4, 4, 12):
            ball(1.6, GOLD, x, 0, 0.6)
    elif kind == "jalu":                 # cardboard prop sword (he never watched the movie)
        poly((90, 56, 30), [(-6, -1.6), (3, -1.6), (3, 1.6), (-6, 1.6)], (40, 24, 14))
        poly(GOLD, [(3, -6), (6, -6), (6, 6), (3, 6)], GOLD_D, 0.8)
        poly((214, 222, 236), [(6, -3), (28, -3), (34, 0), (28, 3), (6, 3)], (70, 80, 104), 1.0)
        poly((250, 252, 255), [(6, -2.2), (28, -2.2), (31, -0.3), (6, -0.3)])
        for x in (10, 16, 22):  # blue tape
            pygame.draw.line(cv, (60, 120, 230), X(x, -3), X(x, 3), int(1.8 * S))
    elif kind == "romli" and path == 1:  # programmer: laptop (screen + keyboard base, shown edge-on to the aim)
        poly((150, 156, 170), [(-6, -2.4), (6, -2.4), (6, 2.4), (-6, 2.4)], (70, 76, 90), 0.8)        # keyboard base
        poly((110, 116, 132), [(-5, -1.4), (5, -1.4), (5, 1.4), (-5, 1.4)])
        poly((60, 66, 82), [(5, -8.5), (24, -8.5), (24, 8.5), (5, 8.5)], (30, 34, 44), 1.0)           # lid / screen bezel
        poly((14, 22, 20), [(7, -6.8), (22, -6.8), (22, 6.8), (7, 6.8)])
        for i, w in enumerate((10, 6, 9, 4, 8)):                                                       # lines of green code
            poly((90, 255, 150), [(9, -5.4 + i * 2.5), (9 + w, -5.4 + i * 2.5), (9 + w, -4.4 + i * 2.5), (9, -4.4 + i * 2.5)])
    elif kind == "romli":                # a fat stack of cash (base + business)
        for k, dy in enumerate((2.6, 0.0, -2.6)):                                                      # three stacked bundles
            poly((52, 120, 70), [(-6, dy - 3.4), (20, dy - 3.4), (20, dy + 3.4), (-6, dy + 3.4)], (24, 70, 40), 0.9)
            poly((98, 196, 118), [(-5, dy - 2.4), (19, dy - 2.4), (19, dy + 2.4), (-5, dy + 2.4)])
            ball(1.9, GOLD, 7, dy, 0.6)                                                                # coin on the note
        poly((236, 236, 240), [(2, -9.4), (6, -9.4), (6, 9.4), (2, 9.4)], (150, 150, 160), 0.6)      # paper band round the stack
    elif kind == "zizi" and path == 0:   # Recitation: a book (open it and read aloud)
        poly((120, 60, 40), [(-4, -9), (22, -9), (22, 9), (-4, 9)], (60, 28, 16), 1.0)                # cover
        poly((250, 240, 214), [(-2, -7.6), (21, -7.6), (21, 7.6), (-2, 7.6)], (200, 184, 150), 0.6)   # pages
        poly((236, 190, 70), [(-4, -9), (0, -9), (0, 9), (-4, 9)], GOLD_D, 0.8)                       # gilded spine
        for i in range(4):                                                                              # lines of text
            poly((120, 110, 100), [(4, -4.8 + i * 3.2), (4 + 14 - i * 2, -4.8 + i * 3.2), (4 + 14 - i * 2, -4.0 + i * 3.2), (4, -4.0 + i * 3.2)])
        ball(1.6, (230, 70, 70), 20, 6, 0.5)                                                            # ribbon bookmark
    elif kind == "zizi" and path == 1:   # Sloth: a fluffy pillow
        poly((176, 164, 224), [(-2, -10), (24, -10), (26, 0), (24, 10), (-2, 10), (0, 0)], (110, 98, 160), 1.0)
        poly((214, 206, 244), [(0, -8), (22, -8), (23.5, 0), (22, 8), (0, 8), (1.5, 0)])
        for cx, cy in ((-1, -9), (-1, 9), (25, -9), (25, 9)):                                           # corner tassels
            ball(1.6, (255, 236, 150), cx, cy, 0.6)
        for i in range(3):                                                                              # tiny moons/stars pattern
            ball(0.9, (255, 236, 150), 6 + i * 6, -3 + (i % 2) * 6, 0.4)
    elif kind == "zizi":                 # base Zizi: prayer beads on a string, with a tassel
        pts = [(2 + 3.7 * i, 4.5 * math.sin(i / 7 * math.pi)) for i in range(8)]
        pygame.draw.lines(cv, (150, 110, 60), False, [X(*p) for p in pts], max(1, int(0.9 * S)))
        for i, (x, y) in enumerate(pts):
            ball(2.5, (240, 214, 255) if i % 2 else (200, 120, 232), x, y)
        poly((236, 190, 70), [(29, 0), (34, -2.5), (38, 0), (34, 2.5)], GOLD_D, 0.7)
        for k in (-2, 0, 2):
            pygame.draw.line(cv, (236, 190, 70), X(36, 0), X(41, k * 1.4), int(1.2 * S))
    elif kind == "fadhli" and path == 0:   # Garp: a big iron cannonball
        ball(9.5, (74, 80, 98), 15, 0, 0.9)
        pygame.draw.line(cv, (200, 60, 60), X(15, -8.4), X(15, 8.4), int(1.6 * S))               # red band
        ball(2.0, (210, 216, 232), 11, -4, 0.4)
    elif kind == "fadhli" and path == 1:   # Johnny: a steel ball with a golden spiral
        ball(6.6, (206, 214, 228), 13, 0, 1.2)
        pts = [(13 + 0.7 * 1.618 ** (a / 1.1) * math.cos(a * 2.0), 0.7 * 1.618 ** (a / 1.1) * math.sin(a * 2.0)) for a in [i * 0.45 for i in range(12)]]
        pygame.draw.lines(cv, (240, 190, 50), False, [X(*q) for q in pts], max(1, int(1.1 * S)))
    elif kind == "fadhli":               # base Fadhli: a rock
        ball(6.0, (150, 140, 128), 12, 0, 0.7)
        ball(2.0, (180, 170, 156), 10, -2.4, 0.4)
        pygame.draw.line(cv, (98, 90, 80), X(10, 1.5), X(15, 3.5), int(1.0 * S))
    elif kind == "bima":                 # drawing compass
        pygame.draw.line(cv, (150, 156, 172), X(4, 0), X(30, -4.5), int(2.4 * S))
        pygame.draw.line(cv, (150, 156, 172), X(4, 0), X(27, 6), int(2.4 * S))
        pygame.draw.line(cv, (230, 236, 248), X(4, -0.6), X(30, -5), S)
        poly((210, 60, 60), [(25, 5), (30, 7.2), (28, 9.6), (24, 7)], (90, 20, 20), 0.6)   # pencil lead
        pygame.draw.line(cv, (60, 66, 82), X(30, -4.5), X(33, -6.5), int(1.4 * S))        # needle
        ball(3.0, (255, 160, 70), 4, 0)
        pygame.draw.line(cv, (90, 96, 112), X(-1, 0), X(-8, 0), int(2.2 * S))
        ball(1.8, (255, 214, 70), -9, 0, 0.6)
    else:
        return None
    return gfx.downscale(cv, S)


def weapon_image(kind: str, look, angle: float, flip: bool) -> pygame.Surface | None:
    """Held weapon rotated to `angle` degrees (counter-clockwise, screen up = 90). Centre of the image = the hand.
    `flip`: mirrored vertically so the weapon stays upright when aiming left."""
    base_key = ("weapon", kind, look)
    if base_key not in _CACHE:
        _CACHE[base_key] = _weapon_surface(kind, look)
    base = _CACHE[base_key]
    if base is None:
        return None
    a = round(angle / 6) * 6
    key = ("weapon_rot", kind, look, a, flip)
    if key not in _CACHE:
        img = pygame.transform.flip(base, False, True) if flip else base
        _CACHE[key] = pygame.transform.rotate(img, a)
    return _CACHE[key]


# ================================================================== projectiles
def projectile(kind: str, look) -> tuple[pygame.Surface, float] | None:
    """(sprite pointing RIGHT ~22 px, spin in degrees/second) or None when a tower has no projectile model
    (Mark punches; Bima's geometry shots use shape_sprite)."""
    key = ("proj", kind, look)
    if key in _CACHE:
        return _CACHE[key]
    n = 26
    cv = gfx.blank(n * S, n * S)
    h = n * S / 2

    def X(x, y=0.0):
        return (h + x * S, h + y * S)

    def ball(rad, col, x, y, shine=1.0):
        big = pygame.transform.smoothscale(gfx.sphere(rad, col, shine=shine), (int((2 * rad + 2) * S), int((2 * rad + 2) * S)))
        cv.blit(big, big.get_rect(center=X(x, y)))

    path = look[0] if look else None
    out: tuple[pygame.Surface, float] | None
    if kind == "jalu" and path == 0:
        out = None
    elif kind == "jalu" and path == 1:   # magic bolt: green energy diamond with a gold core and a tail
        cv.blit(gfx.glow(12 * S, (60, 230, 140), 200), gfx.glow(12 * S, (60, 230, 140), 200).get_rect(center=X(0)))
        gfx.poly(cv, (40, 190, 110), [X(-11, 0), X(-3, -4), X(9, 0), X(-3, 4)], (10, 80, 50), S)
        gfx.poly(cv, (140, 255, 190), [X(-6, 0), X(-1, -2), X(5, 0), X(-1, 2)])
        ball(2.2, (255, 236, 150), 1, 0, 0.8)
        out = (gfx.downscale(cv, S), 0.0)
    elif kind == "jalu":                  # a rolled-up movie poster, tumbling
        pygame.draw.rect(cv, (60, 40, 24), pygame.Rect(*X(-9, -3.6), 18 * S, 7.2 * S), border_radius=int(3.4 * S))
        pygame.draw.rect(cv, (244, 232, 200), pygame.Rect(*X(-8.4, -3.0), 16.8 * S, 6.0 * S), border_radius=int(3 * S))
        pygame.draw.rect(cv, (255, 250, 232), pygame.Rect(*X(-8, -2.8), 16 * S, 2.2 * S), border_radius=int(1 * S))
        pygame.draw.rect(cv, (214, 60, 70), pygame.Rect(*X(-2, -3.2), 3 * S, 6.4 * S))
        ball(3.0, (244, 232, 200), -9, 0, 0.5)
        ball(3.0, (200, 180, 140), 9, 0, 0.3)
        pygame.draw.circle(cv, (150, 120, 80), X(9, 0), int(1.4 * S))
        out = (gfx.downscale(cv, S), 540.0)
    elif kind == "romli":                 # the bug: green beetle with a glowing circuit back
        for sx in (-1, 1):
            for dx in (-4, 0, 4):
                pygame.draw.line(cv, (20, 50, 36), X(dx, 0), X(dx + 2, sx * 8.5), int(1.4 * S))
            pygame.draw.line(cv, (20, 50, 36), X(9, 0), X(13, sx * 4), int(1.1 * S))
        ball(5.2, (60, 190, 110), -2, 0)
        ball(3.4, (90, 220, 140), 6, 0)
        for sx in (-1, 1):
            ball(1.1, (255, 70, 70), 8, sx * 1.6, 0.5)
        pygame.draw.line(cv, (20, 50, 36), X(-2, -5), X(-2, 5), S)
        pygame.draw.lines(cv, (200, 255, 220), False, [X(-6, -2), X(-3, -2), X(-3, 1), X(0, 1), X(0, 3)], int(0.9 * S))
        out = (gfx.downscale(cv, S), 0.0)
    elif kind == "zizi":                  # a ring of prayer beads, softly glowing
        cv.blit(gfx.glow(12 * S, (210, 150, 255), 190), gfx.glow(12 * S, (210, 150, 255), 190).get_rect(center=X(0)))
        for i in range(9):
            a = i / 9 * math.tau
            ball(2.2, (244, 220, 255) if i % 2 else (200, 120, 232), 7 * math.cos(a), 7 * math.sin(a), 0.9)
        pygame.draw.circle(cv, (236, 190, 70), X(0, 0), int(1.6 * S))
        out = (gfx.downscale(cv, S), 200.0)
    elif kind == "fadhli" and path == 0:   # Garp: iron cannonball with a hot glow
        cv.blit(gfx.glow(12 * S, (255, 140, 60), 120), gfx.glow(12 * S, (255, 140, 60), 120).get_rect(center=X(0)))
        ball(9.5, (74, 80, 98), 0, 0, 0.9)
        pygame.draw.line(cv, (200, 60, 60), X(0, -8.4), X(0, 8.4), int(1.6 * S))
        ball(2.0, (210, 216, 232), -3.5, -3.5, 0.4)
        out = (gfx.downscale(cv, S), 160.0)
    elif kind == "fadhli" and path == 1:   # Johnny: steel ball, golden spiral, cold shine
        cv.blit(gfx.glow(10 * S, (190, 230, 255), 150), gfx.glow(10 * S, (190, 230, 255), 150).get_rect(center=X(0)))
        ball(6.6, (206, 214, 228), 0, 0, 1.3)
        pts = [(0.7 * 1.618 ** (a / 1.1) * math.cos(a * 2.0), 0.7 * 1.618 ** (a / 1.1) * math.sin(a * 2.0)) for a in [i * 0.45 for i in range(12)]]
        pygame.draw.lines(cv, (240, 190, 50), False, [X(*q) for q in pts], max(1, int(1.1 * S)))
        out = (gfx.downscale(cv, S), 900.0)
    elif kind == "fadhli":                # base Fadhli: a rock
        ball(6.4, (150, 140, 128), 0, 0, 0.7)
        ball(2.2, (184, 174, 160), -2, -2.4, 0.4)
        out = (gfx.downscale(cv, S), 220.0)
    elif kind == "bima":                  # equation spark: orange orb with a sine wave
        cv.blit(gfx.glow(11 * S, (255, 170, 80), 190), gfx.glow(11 * S, (255, 170, 80), 190).get_rect(center=X(0)))
        ball(7, (255, 160, 70), 0, 0)
        pygame.draw.lines(cv, (255, 255, 255), False, [X(-5 + i, 2.6 * math.sin(i * 0.9)) for i in range(11)], int(1.2 * S))
        out = (gfx.downscale(cv, S), 0.0)
    else:
        out = None
    _CACHE[key] = out
    return out


# ================================================================== Tusk (Johnny's stand)
def tusk(act: int, size: int) -> pygame.Surface:
    """Stylised Tusk, facing RIGHT. act 1: small critter with a pointed finger. act 3: crouching, tall horns + spiral tail.
    act 4: big muscular humanoid with golden spiral lines and a rotating halo. Cached, `size` = canvas px."""
    key = ("tusk", act, size)
    if key in _CACHE:
        return _CACHE[key]
    n = 48
    cv = gfx.blank(n * S, n * S)
    h = n * S / 2
    cream, cream_d, ink, gold, blue = (236, 232, 210), (190, 184, 160), (46, 50, 82), (255, 206, 60), (96, 176, 255)

    def X(x, y=0.0):
        return (h + x * S, h + y * S)

    def ball(rad, col, x, y, shine=0.9):
        big = pygame.transform.smoothscale(gfx.sphere(rad, col, shine=shine), (int((2 * rad + 2) * S), int((2 * rad + 2) * S)))
        cv.blit(big, big.get_rect(center=X(x, y)))

    def glow(rad, col, a, x=0.0, y=0.0):
        g = gfx.glow(int(rad * S), col, a)
        cv.blit(g, g.get_rect(center=X(x, y)))

    def spiral(cx, cy, scale, col, w, turns=11):
        pts = [(cx + scale * 1.618 ** (a / 1.1) * math.cos(a * 2.0), cy + scale * 1.618 ** (a / 1.1) * math.sin(a * 2.0)) for a in [i * 0.4 for i in range(turns)]]
        pygame.draw.lines(cv, col, False, [X(*q) for q in pts], max(1, int(w * S)))

    if act == 1:
        glow(18, blue, 70)
        ball(7.5, cream, -2, 9, 0.9)                                           # body
        ball(8.0, cream, -1, -5, 1.0)                                          # head
        for sx in (-1, 1):                                                     # small horns / ears
            gfx.poly(cv, ink, [X(-1 + sx * 5, -11), X(-1 + sx * 9.5, -19), X(-1 + sx * 8.5, -10)])
        ball(1.5, ink, 2, -6, 1.3); ball(1.5, ink, -5, -6, 1.3)                # eyes
        pygame.draw.line(cv, ink, X(-3, -1.5), X(1, -1.5), int(0.9 * S))      # mouth
        pygame.draw.line(cv, cream_d, X(3, 6), X(13, 3), int(3.2 * S))         # arm
        ball(3.2, cream, 14, 2.5, 0.9)                                         # hand
        gfx.poly(cv, gold, [X(16, 1), X(23, 2.2), X(16, 4.4)], (150, 100, 20), max(1, int(0.6 * S)))   # the nail
        glow(7, gold, 200, 22, 2.2)
        spiral(-2, 10, 0.5, ink, 0.8)
    elif act == 3:
        glow(22, blue, 80)
        for k in range(14):                                                    # spiral tail
            a = k * 0.5
            ball(2.4 - 0.12 * k, cream_d, -10 - 1.0 * k, 12 - 2.2 * math.sin(a), 0.7)
        spiral(-18, 10, 1.4, gold, 1.0, 9)
        ball(9, cream, -1, 6, 0.9)                                             # crouched body
        ball(8.4, cream, 1, -8, 1.0)                                           # head
        for sx in (-1, 1):                                                     # tall horns
            gfx.poly(cv, ink, [X(1 + sx * 4, -13), X(1 + sx * 8, -26), X(1 + sx * 10, -12)])
        for sx in (-1, 1):                                                     # shoulder spikes
            gfx.poly(cv, cream_d, [X(-1 + sx * 7, -1), X(-1 + sx * 13, -5), X(-1 + sx * 10, 3)], ink, max(1, int(0.5 * S)))
        ball(1.7, ink, 4, -9, 1.3); ball(1.7, ink, -3, -9, 1.3)
        pygame.draw.line(cv, cream_d, X(5, 4), X(16, 1), int(4 * S))
        ball(3.8, cream, 17, 0.5, 0.9)
        gfx.poly(cv, gold, [X(19, -1.8), X(28, 0.5), X(19, 2.8)], (150, 100, 20), max(1, int(0.6 * S)))
        glow(8, gold, 210, 27, 0.5)
        spiral(-1, 7, 0.6, ink, 0.9)
    else:  # act 4
        glow(23, gold, 90)
        pygame.draw.circle(cv, (*gold, 255), X(-2, -2), int(21 * S), max(1, int(1.2 * S)))        # the rotating halo (drawn static; Tower rotates the sprite)
        spiral(-2, -2, 1.2, gold, 1.1, 12)
        ball(11, cream, -2, 6, 0.9)                                            # broad torso
        ball(7.6, cream, -2, -10, 1.0)                                         # head
        for sx in (-1, 1):                                                     # horn crest
            gfx.poly(cv, ink, [X(-2 + sx * 3, -15), X(-2 + sx * 7, -28), X(-2 + sx * 9, -13)])
        gfx.poly(cv, gold, [X(-2 - 2, -17), X(-2, -31), X(-2 + 2, -17)])
        ball(1.7, gold, 1, -11, 1.3); ball(1.7, gold, -5, -11, 1.3)
        for sx in (-1, 1):
            pygame.draw.line(cv, cream_d, X(-2 + sx * 9, 0), X(-2 + sx * 17, 6), int(5 * S))      # big arms
            ball(4.6, cream, -2 + sx * 18, 7, 0.9)
            spiral(-2 + sx * 13, 3, 0.5, gold, 0.8, 8)
        spiral(-2, 5, 0.7, gold, 1.0, 12)
    img = gfx.downscale(cv, S)
    img = pygame.transform.smoothscale(img, (size, size))
    _CACHE[key] = img
    return img


# ================================================================ floating props
def prop(name: str, size: int) -> pygame.Surface:
    """Standalone models: 'fist' (Mark's punch, points RIGHT), 'loom' (Temporal Loom), 'screen' (code screen),
    'pillow' (Zizi's nap pillow). Used as tower companions and free for VFX to use."""
    key = ("prop", name, size)
    if key in _CACHE:
        return _CACHE[key]
    cv = gfx.blank(40 * S, 40 * S)
    h = 20 * S

    def X(x, y=0.0):
        return (h + x * S, h + y * S)

    def ball(rad, col, x, y, shine=1.0):
        big = pygame.transform.smoothscale(gfx.sphere(rad, col, shine=shine), (int((2 * rad + 2) * S), int((2 * rad + 2) * S)))
        cv.blit(big, big.get_rect(center=X(x, y)))

    if name == "fist":
        yellow = (244, 204, 52)
        gfx.poly(cv, (36, 84, 196), [X(-16, -6), X(-8, -7), X(-8, 7), X(-16, 6)], (14, 36, 100), S)
        ball(9, yellow, 1, 0)
        for i, y in enumerate((-6, -2, 2, 6)):                      # knuckles
            ball(3.4, gfx.tint(yellow, 0.1), 9, y, 0.8)
        ball(3.2, gfx.shade(yellow, 0.9), -1, 8, 0.6)               # thumb
        for y in (-3, 3):
            pygame.draw.line(cv, (255, 255, 255), X(-19, y), X(-12, y), int(1.2 * S))
    elif name == "loom":
        cv.blit(gfx.glow(18 * S, (120, 210, 255), 150), gfx.glow(18 * S, (120, 210, 255), 150).get_rect(center=X(0)))
        pygame.draw.circle(cv, GOLD_D, X(0), int(15 * S))
        pygame.draw.circle(cv, GOLD, X(0), int(13.5 * S))
        pygame.draw.circle(cv, (246, 240, 224), X(0), int(11 * S))
        for i in range(12):                                          # clock ticks
            a = i / 12 * math.tau
            pygame.draw.line(cv, (60, 50, 40), X(9 * math.cos(a), 9 * math.sin(a)), X(10.6 * math.cos(a), 10.6 * math.sin(a)), S)
        for x in (-7, -3.5, 0, 3.5, 7):                              # loom threads
            pygame.draw.line(cv, (70, 170, 230), X(x, -8), X(x, 8), int(1.0 * S))
        for y in (-5, 0, 5):
            pygame.draw.line(cv, (70, 200, 140), X(-9, y), X(9, y + 1), int(1.0 * S))
        pygame.draw.line(cv, (40, 30, 24), X(0), X(0, -8), int(1.6 * S))
        pygame.draw.line(cv, (40, 30, 24), X(0), X(5.5, 2), int(1.6 * S))
        ball(1.6, GOLD, 0, 0, 0.6)
    elif name == "screen":
        cv.blit(gfx.glow(17 * S, (90, 255, 150), 110), gfx.glow(17 * S, (90, 255, 150), 110).get_rect(center=X(0)))
        r = pygame.Rect(0, 0, 30 * S, 22 * S)
        r.center = X(0)
        pygame.draw.rect(cv, (30, 36, 52), r.inflate(int(3 * S), int(3 * S)), border_radius=int(3 * S))
        pygame.draw.rect(cv, (10, 18, 24), r, border_radius=int(2 * S))
        for i, (w, col) in enumerate(((16, (90, 255, 150)), (10, (120, 200, 255)), (20, (90, 255, 150)), (7, (255, 220, 100)), (13, (120, 200, 255)))):
            pygame.draw.line(cv, col, (r.x + 3 * S + (4 * S if i in (1, 3) else 0), r.y + (3 + 3.6 * i) * S),
                             (r.x + 3 * S + (4 * S if i in (1, 3) else 0) + w * S, r.y + (3 + 3.6 * i) * S), int(1.5 * S))
    elif name == "pillow":
        r = pygame.Rect(0, 0, 32 * S, 22 * S)
        r.center = X(0)
        pygame.draw.rect(cv, (90, 70, 140), r.inflate(int(3 * S), int(3 * S)), border_radius=int(9 * S))
        pygame.draw.rect(cv, (214, 200, 250), r, border_radius=int(8 * S))
        pygame.draw.rect(cv, (240, 232, 255), (r.x + 3 * S, r.y + 2 * S, r.w - 6 * S, 6 * S), border_radius=int(3 * S))
        for sx in (-1, 1):
            for sy in (-1, 1):
                ball(2.0, (236, 190, 70), sx * 16, sy * 11, 0.6)
        f = pygame.font.Font(None, int(14 * S))
        t = f.render("z", True, (120, 96, 180))
        cv.blit(t, t.get_rect(center=X(0, 2)))
    else:
        raise KeyError(name)
    img = gfx.downscale(cv, S)
    img = pygame.transform.smoothscale(img, (size, size))
    _CACHE[key] = img
    return img


def draw_companion(surface: pygame.Surface, kind: str, look, x: int, y: int, t: float) -> None:
    """Floating extras next to a tower (bobbing): Loom (Loki T3+), code screens (Programmer T3+), nap pillow
    (Sloth T4), orbiting shapes (Geometry), hologram sine wave (Graph T4). (x, y) = tower position."""
    if look is None:
        return
    path, tier = look
    bob = 3 * math.sin(t * 2.2)
    if kind == "jalu" and path == 1 and tier >= 3:
        img = prop("loom", 30 if tier >= 4 else 26)
        img = pygame.transform.rotozoom(img, 0, 1.0)
        surface.blit(img, img.get_rect(center=(x - 32, y - 50 + bob)))
    elif kind == "romli" and path == 1 and tier >= 3:
        spots = [(32, -54)] if tier == 3 else [(-32, -50), (32, -58)]
        for i, (dx, dy) in enumerate(spots):
            img = prop("screen", 28)
            surface.blit(img, img.get_rect(center=(x + dx, y + dy + 3 * math.sin(t * 2.2 + i * 2))))
    elif kind == "fadhli" and path == 1 and tier >= 2:     # Johnny's stand: Tusk Act 1 (T2) / Act 3 (T3) / Act 4 (T4)
        act = {2: 1, 3: 3, 4: 4}[tier]
        size = {1: 34, 3: 42, 4: 54}[act]
        img = tusk(act, size)
        surface.blit(img, img.get_rect(center=(x + 36, y - 40 + bob * (1.4 if act == 4 else 1.0))))
    elif kind == "zizi" and path == 1 and tier >= 4:
        img = prop("pillow", 28)
        surface.blit(img, img.get_rect(center=(x + 34, y - 30 + bob)))
    elif kind == "bima" and path == 1:
        solid = tier >= 3
        from game import sprites_proc  # lazy: sprites_proc imports this module
        for i in range(3):
            a = t * 1.4 + i * math.tau / 3
            img = sprites_proc.shape_sprite(i, solid, 14)
            px, py = x + 30 * math.cos(a), y - 46 + 9 * math.sin(a)
            surface.blit(img, img.get_rect(center=(round(px), round(py))))
    elif kind == "bima" and path == 0 and tier >= 4:
        pts = [(x + 24 + i * 2.2, y - 56 + 7 * math.sin(i * 0.7 + t * 3)) for i in range(11)]
        g = gfx.glow(18, (90, 220, 255), 90)
        surface.blit(g, g.get_rect(center=(x + 35, y - 56)))
        pygame.draw.lines(surface, (150, 235, 255), False, pts, 2)
        pygame.draw.line(surface, (90, 170, 220), (x + 22, y - 48), (x + 22, y - 64), 1)
        pygame.draw.line(surface, (90, 170, 220), (x + 22, y - 56), (x + 48, y - 56), 1)


# ============================================================ Mark (sweep runner)
def mark_runner(frame: int, facing_left: bool) -> pygame.Surface:
    """Mark in full costume (cape + mask) running flat out. 8 frames, ~60 px, centred. Used by the Sweep ability."""
    frame %= 8
    key = ("runner", frame, facing_left)
    if key in _CACHE:
        return _CACHE[key]
    n = 72
    cv = gfx.blank(n * S, n * S)
    h = n * S / 2
    phi = frame / 8 * math.tau
    blue, yellow = (36, 84, 196), (244, 204, 52)

    def X(x, y=0.0):
        return (h + x * S, h + y * S)

    def ball(rad, col, x, y, shine=0.9):
        big = pygame.transform.smoothscale(gfx.sphere(rad, col, shine=shine), (int((2 * rad + 2) * S), int((2 * rad + 2) * S)))
        cv.blit(big, big.get_rect(center=X(x, y)))

    flap = 3 * math.sin(phi * 2)
    gfx.poly(cv, (150, 30, 40), [X(-4, -8), X(-30, -14 + flap), X(-33, -2 - flap), X(-26, 8 + flap), X(-4, 6)], (70, 10, 20), S)
    gfx.poly(cv, (206, 48, 56), [X(-4, -7), X(-26, -12 + flap), X(-28, -3 - flap), X(-22, 6 + flap), X(-4, 4)])
    for sgn, ph in ((1, 0.0), (-1, math.pi)):                       # legs: far leg first
        a = math.sin(phi + ph) * 0.9
        hip = (-2.0, 8.0)
        foot = (hip[0] + math.sin(a) * 13 + 3, hip[1] + math.cos(a) * 11 - 1 - max(0.0, -math.cos(phi + ph)) * 4)
        pygame.draw.line(cv, blue if sgn > 0 else gfx.shade(blue, 0.7), X(*hip), X(*foot), int(6 * S))
        ball(3.8, yellow if sgn > 0 else gfx.shade(yellow, 0.8), foot[0] + 1.5, foot[1])
    torso = pygame.transform.rotozoom(gfx.ellipsoid(18, 22, blue, shine=0.9), -62, 1.0)
    torso = pygame.transform.smoothscale(torso, (torso.get_width() * S, torso.get_height() * S))
    cv.blit(torso, torso.get_rect(center=X(0, 0)))
    pygame.draw.line(cv, yellow, X(-6, -2), X(6, 2), int(2.4 * S))
    ball(3.5, yellow, -9, 5.5)                                       # back arm
    pygame.draw.line(cv, blue, X(-1, -4), X(-9, 3), int(4.6 * S))
    pygame.draw.line(cv, blue, X(4, -5), X(19, -7), int(5 * S))      # punching arm forward
    ball(5.2, yellow, 21, -7)
    ball(7.6, (176, 120, 82), 10, -11, 1.0)                          # head
    pygame.draw.ellipse(cv, (18, 18, 28), (*X(5, -14.5), 11 * S, 4.6 * S))
    pygame.draw.ellipse(cv, (255, 70, 60), (*X(11.2, -13.4), 3.4 * S, 1.8 * S))
    pygame.draw.ellipse(cv, (255, 70, 60), (*X(6.6, -13.4), 3.4 * S, 1.8 * S))
    for sx in (-2, 2, 6):                                            # spiky hair blown back
        gfx.poly(cv, (46, 34, 56), [X(5 + sx, -17), X(2 + sx, -24), X(8 + sx, -18)])
    for y in (-14, -2, 10):                                          # speed lines
        pygame.draw.line(cv, (255, 255, 255), X(-34, y), X(-26 - 4 * (y % 3), y), int(1.2 * S))
    img = gfx.downscale(cv, S)
    if facing_left:
        img = pygame.transform.flip(img, True, False)
    _CACHE[key] = img
    return img
