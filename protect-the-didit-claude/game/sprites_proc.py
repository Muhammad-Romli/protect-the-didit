"""Procedural, shaded sprites for enemies and towers (used whenever assets/sprites has no PNG).

Everything is built from lit spheres/ellipsoids (game/gfx.py), assembled once and cached:
8 walk frames per enemy (squash + bob + tilt + alternating feet), mirrored for walking left.
Sprites are centred on the entity position; shadows are drawn separately by the entity.
"""
from __future__ import annotations

import math

import pygame

from game import gfx, models

FRAMES = 8
_CACHE: dict[tuple, pygame.Surface] = {}


def _put(layer: pygame.Surface, img: pygame.Surface, x: float, y: float) -> None:
    layer.blit(img, img.get_rect(center=(round(x), round(y))))


def _cut_below(img: pygame.Surface, y: int) -> pygame.Surface:
    img = img.copy()
    pygame.draw.rect(img, (0, 0, 0, 0), (0, y, img.get_width(), img.get_height() - y))
    return img


# ------------------------------------------------------------------ hamster
def is_dark(color) -> bool:
    """Enemy Didits are black / dark purple; the original (white) Didit and wooden statues use the light look."""
    return sum(color[:3]) < 330


def _hamster_upper(kind: str, r: float, color, armored: int = 0, wood: bool = False) -> pygame.Surface:
    pad = int(r * 1.15)
    size = int(2 * r + 2 * pad)
    L = gfx.blank(size, size)
    c = size / 2
    dark = is_dark(color) and not wood
    ear_in = (150, 70, 170) if dark else (255, 168, 170)
    belly = gfx.shade((70, 36, 96), 0.62) if dark else (250, 232, 200)
    for dx in (-0.52, 0.50):  # ears
        _put(L, gfx.sphere(0.38 * r, gfx.shade(color, 0.92)), c + dx * r, c - 0.80 * r)
        _put(L, gfx.sphere(0.22 * r, gfx.shade(color, 0.62) if wood else ear_in, shine=0.2), c + dx * r + 0.03 * r, c - 0.78 * r)
    _put(L, gfx.sphere(r, color), c, c)
    _put(L, gfx.ellipsoid(int(1.05 * r), int(0.9 * r), gfx.shade(color, 1.18) if wood else belly, shine=0.3), c + 0.18 * r, c + 0.30 * r)
    if not wood and not dark:  # a carved statue has no blush
        cheek = gfx.blank(size, size)
        pygame.draw.circle(cheek, (255, 120, 130, 90), (c + 0.50 * r, c + 0.16 * r), max(2, 0.16 * r))
        L.blit(cheek, (0, 0))
    for dx in (0.28, 0.68):  # eyes (glowing red on the dark Didits)
        if dark:
            _put(L, gfx.glow(max(3, int(0.42 * r)), (255, 60, 90), 160), c + dx * r, c - 0.16 * r)
        _put(L, gfx.sphere(max(2.0, 0.17 * r), (255, 70, 100) if dark else (24, 18, 26), shine=1.3), c + dx * r, c - 0.16 * r)
    nose = (200, 90, 220) if dark else ((70, 42, 22) if wood else (255, 150, 160))
    _put(L, gfx.sphere(max(1.6, 0.10 * r), nose, shine=0.4), c + 0.94 * r, c + 0.06 * r)  # nose
    if kind == "fast":
        band = gfx.blank(size, size)
        pygame.draw.ellipse(band, (230, 50, 50), (c - 0.95 * r, c - 0.74 * r, 2.0 * r, 0.34 * r))
        mask = gfx.blank(size, size)
        pygame.draw.circle(mask, (255, 255, 255, 255), (c, c), r)
        band.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        L.blit(band, (0, 0))
    elif kind == "tanky":  # big and scarred: a vertical scar over the front eye, torn ear, heavy brows
        pygame.draw.line(L, (200, 70, 80), (c + 0.50 * r, c - 0.62 * r), (c + 0.84 * r, c + 0.10 * r), max(2, int(0.09 * r)))
        pygame.draw.line(L, (255, 170, 170), (c + 0.50 * r - 1, c - 0.62 * r), (c + 0.84 * r - 1, c + 0.10 * r), max(1, int(0.03 * r)))
        for t in (0.2, 0.45, 0.7):  # stitches
            sx, sy = c + (0.50 + 0.34 * t) * r, c + (-0.62 + 0.72 * t) * r
            pygame.draw.line(L, (90, 30, 40), (sx - 0.11 * r, sy - 0.03 * r), (sx + 0.11 * r, sy + 0.05 * r), max(1, int(0.04 * r)))
        pygame.draw.polygon(L, (0, 0, 0, 0), [(c + 0.38 * r, c - 1.14 * r), (c + 0.62 * r, c - 1.1 * r), (c + 0.5 * r, c - 0.92 * r)])  # torn ear notch
        for dx in (0.28, 0.68):  # angry brows
            pygame.draw.line(L, (190, 130, 235) if dark else (60, 50, 50), (c + (dx - 0.18) * r, c - 0.44 * r), (c + (dx + 0.16) * r, c - 0.30 * r), max(3, int(0.11 * r)))
    elif kind == "boss":
        crown = [(c - 0.62 * r, c - 0.78 * r), (c - 0.62 * r, c - 1.42 * r), (c - 0.30 * r, c - 1.08 * r),
                 (c, c - 1.55 * r), (c + 0.30 * r, c - 1.08 * r), (c + 0.62 * r, c - 1.42 * r), (c + 0.62 * r, c - 0.78 * r)]
        gfx.poly(L, (255, 206, 60), crown, (120, 80, 10), max(2, int(0.07 * r)))
        pygame.draw.line(L, (255, 240, 150), (c - 0.55 * r, c - 0.95 * r), (c - 0.55 * r, c - 1.3 * r), max(1, int(0.05 * r)))
        for dx, col in ((-0.3, (230, 50, 50)), (0.0, (60, 160, 255)), (0.3, (230, 50, 50))):
            pygame.draw.circle(L, col, (c + dx * r, c - 0.9 * r), max(2, 0.08 * r))
        for dx in (0.28, 0.68):
            pygame.draw.line(L, (210, 110, 255) if dark else (40, 0, 0), (c + (dx - 0.20) * r, c - 0.42 * r), (c + (dx + 0.16) * r, c - 0.30 * r), max(2, int(0.1 * r)))
    elif kind == "rich":
        _rich_extras(L, r, c)
    elif kind == "speedster":
        _speedster_extras(L, r, c)
    elif kind == "reinforced":
        _reinforced_extras(L, r, c, armored)
    return L


def _rich_extras(L: pygame.Surface, r: float, c: float) -> None:
    """Top hat, monocle, handlebar mustache and a bag of money."""
    ink = (20, 20, 26)
    # mustache (under the nose, curled up at the ends)
    pygame.draw.ellipse(L, ink, (c + 0.40 * r, c + 0.16 * r, 0.40 * r, 0.17 * r))
    pygame.draw.ellipse(L, ink, (c + 0.78 * r, c + 0.18 * r, 0.30 * r, 0.15 * r))
    pygame.draw.circle(L, ink, (c + 0.40 * r, c + 0.13 * r), max(1.5, 0.07 * r))
    pygame.draw.circle(L, ink, (c + 1.06 * r, c + 0.15 * r), max(1.5, 0.06 * r))
    # monocle on the front eye + chain
    ring = (240, 190, 50)
    pygame.draw.circle(L, (210, 235, 255, 90), (c + 0.68 * r, c - 0.16 * r), 0.27 * r)
    pygame.draw.circle(L, ring, (c + 0.68 * r, c - 0.16 * r), 0.27 * r, max(2, int(0.07 * r)))
    pygame.draw.line(L, ring, (c + 0.88 * r, c + 0.02 * r), (c + 1.0 * r, c + 0.55 * r), max(1, int(0.04 * r)))
    # top hat
    pygame.draw.ellipse(L, ink, (c - 0.80 * r, c - 1.06 * r, 1.60 * r, 0.34 * r))
    pygame.draw.ellipse(L, (70, 70, 84), (c - 0.74 * r, c - 1.05 * r, 1.30 * r, 0.12 * r))
    crown = gfx.hgradient(int(0.98 * r), int(0.95 * r), [(0, (70, 70, 84)), (0.3, (36, 36, 44)), (1, (12, 12, 16))])
    L.blit(crown, (c - 0.49 * r, c - 1.92 * r))
    pygame.draw.ellipse(L, (60, 60, 72), (c - 0.49 * r, c - 2.02 * r, 0.98 * r, 0.22 * r))
    pygame.draw.ellipse(L, (28, 28, 34), (c - 0.43 * r, c - 2.0 * r, 0.86 * r, 0.16 * r))
    pygame.draw.rect(L, (200, 40, 50), (c - 0.49 * r, c - 1.22 * r, 0.98 * r, 0.20 * r))
    pygame.draw.rect(L, (250, 205, 70), (c - 0.12 * r, c - 1.24 * r, 0.24 * r, 0.24 * r), max(1, int(0.04 * r)))
    pygame.draw.line(L, (130, 130, 150), (c - 0.34 * r, c - 1.80 * r), (c - 0.34 * r, c - 1.3 * r), max(1, int(0.05 * r)))
    # bag of money held in front
    bag = gfx.ellipsoid(int(0.95 * r), int(1.0 * r), (196, 150, 82), bounce=(150, 190, 100), shine=0.3)
    bx, by = c + 0.62 * r, c + 0.70 * r
    L.blit(bag, bag.get_rect(center=(round(bx), round(by))))
    pygame.draw.polygon(L, (150, 106, 54), [(bx - 0.22 * r, by - 0.45 * r), (bx + 0.22 * r, by - 0.45 * r), (bx + 0.12 * r, by - 0.28 * r), (bx - 0.12 * r, by - 0.28 * r)])
    pygame.draw.line(L, (90, 56, 28), (bx - 0.2 * r, by - 0.3 * r), (bx + 0.2 * r, by - 0.3 * r), max(1, int(0.07 * r)))
    f = pygame.font.Font(None, max(10, int(0.95 * r)))
    t = f.render("$", True, (255, 236, 120))
    L.blit(t, t.get_rect(center=(round(bx), round(by + 0.1 * r))))
    for dx in (-0.45, 0.5):  # spilled coins
        pygame.draw.circle(L, (180, 120, 20), (bx + dx * r, by + 0.46 * r), max(2, 0.13 * r))
        pygame.draw.circle(L, (255, 215, 80), (bx + dx * r, by + 0.44 * r), max(2, 0.11 * r))


def _speedster_extras(L: pygame.Surface, r: float, c: float) -> None:
    """Goggles, a streaming scarf and a lightning mark: it is in a hurry."""
    gfx.poly(L, (230, 60, 70), [(c - 0.3 * r, c + 0.42 * r), (c + 0.25 * r, c + 0.52 * r), (c - 1.3 * r, c + 0.78 * r), (c - 1.2 * r, c + 0.52 * r)], (110, 20, 30), max(1, int(0.05 * r)))
    pygame.draw.line(L, (30, 40, 60), (c - 0.9 * r, c - 0.42 * r), (c + 0.35 * r, c - 0.3 * r), max(2, int(0.12 * r)))  # goggle strap
    for dx in (0.28, 0.68):
        pygame.draw.circle(L, (30, 40, 60), (c + dx * r, c - 0.16 * r), 0.30 * r)
        pygame.draw.circle(L, (90, 210, 255), (c + dx * r, c - 0.16 * r), 0.23 * r)
        pygame.draw.circle(L, (210, 245, 255), (c + (dx - 0.07) * r, c - 0.23 * r), 0.08 * r)
    bolt = [(c + 0.05 * r, c - 0.98 * r), (c - 0.18 * r, c - 0.62 * r), (c - 0.02 * r, c - 0.62 * r), (c - 0.14 * r, c - 0.34 * r),
            (c + 0.18 * r, c - 0.7 * r), (c + 0.02 * r, c - 0.7 * r)]
    gfx.poly(L, (255, 230, 70), bolt, (150, 100, 0), max(1, int(0.04 * r)))


def _reinforced_extras(L: pygame.Surface, r: float, c: float, stage: int) -> None:
    """stage 2 = full armor (shiny helmet, chest plate, shoulder pads);
    stage 1 = damaged (cracked helmet, holed plate, one pad missing); 0 = armor gone."""
    steel, dark = (158, 168, 186), (86, 94, 112)
    brow = lambda: [pygame.draw.line(L, (30, 20, 20), (c + (dx - 0.16) * r, c - 0.42 * r), (c + (dx + 0.14) * r, c - 0.30 * r), max(2, int(0.08 * r))) for dx in (0.28, 0.68)]
    if stage >= 1:
        full = stage == 2
        pads = (-0.85, 0.85) if full else (0.85,)
        for dx in pads:  # shoulder pads
            pad = gfx.sphere(0.32 * r, steel if full else (124, 132, 148), bounce=(180, 200, 220), shine=1.0)
            _put(L, pad, c + dx * r, c + 0.45 * r)
        plate = gfx.ellipsoid(int(1.3 * r), int(0.85 * r), steel if full else (128, 136, 152), bounce=(180, 200, 220), shine=1.1 if full else 0.4)
        _put(L, plate, c + 0.15 * r, c + 0.52 * r)
        pygame.draw.line(L, dark, (c + 0.15 * r, c + 0.2 * r), (c + 0.15 * r, c + 0.82 * r), max(1, int(0.05 * r)))
        dome = gfx.sphere(1.08 * r, steel if full else (130, 138, 154), bounce=(180, 200, 220), shine=1.2 if full else 0.4)
        d = _cut_below(dome, int(dome.get_height() * 0.5))
        _put(L, d, c, c - 0.08 * r - dome.get_height() * 0.04)
        pygame.draw.line(L, dark, (c - 1.02 * r, c - 0.18 * r), (c + 1.02 * r, c - 0.18 * r), max(2, int(0.1 * r)))
        for dx in (-0.6, 0.0, 0.6):
            pygame.draw.circle(L, (215, 220, 232), (c + dx * r, c - 0.18 * r), max(1, 0.06 * r))
        if full:  # shine + crest
            pygame.draw.line(L, (255, 255, 255), (c - 0.5 * r, c - 0.72 * r), (c - 0.1 * r, c - 0.92 * r), max(1, int(0.06 * r)))
            gfx.poly(L, (220, 50, 60), [(c - 0.1 * r, c - 1.0 * r), (c, c - 1.42 * r), (c + 0.1 * r, c - 1.0 * r)], (110, 20, 30), 1)
        else:  # cracks, a hole in the plate, a dent in the helmet
            for pts in (((-0.1, -0.92), (0.05, -0.62), (-0.12, -0.38)), ((0.3, -0.85), (0.42, -0.55))):
                pygame.draw.lines(L, (40, 44, 56), False, [(c + x * r, c + y * r) for x, y in pts], max(1, int(0.05 * r)))
            pygame.draw.polygon(L, (236, 232, 228), [(c + 0.35 * r, c + 0.42 * r), (c + 0.62 * r, c + 0.5 * r), (c + 0.5 * r, c + 0.72 * r), (c + 0.28 * r, c + 0.62 * r)])
            pygame.draw.lines(L, dark, True, [(c + 0.35 * r, c + 0.42 * r), (c + 0.62 * r, c + 0.5 * r), (c + 0.5 * r, c + 0.72 * r), (c + 0.28 * r, c + 0.62 * r)], max(1, int(0.04 * r)))
            pygame.draw.circle(L, (200, 70, 60), (c + 0.9 * r, c + 0.55 * r), max(2, 0.07 * r))  # a scratch of red paint
        if not full:
            brow()
    else:  # armor gone: scraps + angry brows
        for dx, dy in ((-0.7, 0.8), (0.9, 0.9)):
            pygame.draw.polygon(L, (110, 118, 134), [(c + dx * r, c + dy * r), (c + (dx + 0.3) * r, c + (dy - 0.05) * r), (c + (dx + 0.2) * r, c + (dy + 0.2) * r)])
        brow()


def _hamster_frame(kind: str, r: float, color, frame: int, armored: int = 0) -> pygame.Surface:
    phi = frame / FRAMES * math.tau
    upper = _hamster_upper(kind, r, color, armored)
    w, h = upper.get_size()
    sx = 1 + 0.05 * math.sin(2 * phi)
    img = pygame.transform.smoothscale(upper, (max(2, int(w * sx)), max(2, int(h * (2 - sx)))))
    img = pygame.transform.rotozoom(img, 5 * math.sin(phi), 1.0)
    canvas = gfx.blank(w + 8, h + 8)
    c = canvas.get_width() / 2
    lift = max(0.0, math.sin(phi)), max(0.0, -math.sin(phi))
    for side, dx in enumerate((-0.42, 0.42)):  # tiny pink feet, alternating
        pygame.draw.ellipse(canvas, (120, 60, 140) if is_dark(color) else (236, 150, 150), (c + dx * r - 0.22 * r, c + 0.78 * r - lift[side] * 0.22 * r, 0.46 * r, 0.30 * r))
    bob = abs(math.sin(phi)) * 0.10 * r
    _put(canvas, img, c, c - bob)
    if kind in ("fast", "speedster"):  # speed streaks behind (left)
        col = (255, 255, 255, 140) if kind == "fast" else (120, 210, 255, 190)
        for i, y in enumerate((-0.35, 0.05, 0.45)):
            pygame.draw.line(canvas, col, (c - 1.05 * r - 0.25 * r * (i % 2), c + y * r),
                             (c - (1.55 if kind == 'fast' else 1.95) * r, c + y * r), max(1, int(0.07 * r)))
    return canvas


# ------------------------------------------------------------------- trojan
WOOD = (184, 126, 66)  # bare wood: the Trojans are NOT painted any more
TROJAN_KINDS = ("trojan", "trojan_trojan")


def _wooden_didit(r: float, boss: bool) -> pygame.Surface:
    """A giant Didit statue carved from bare wood: barrel-stave seams, wood grain, iron (or gold)
    bands, and glowing windows with tiny Didits peeking out. Sits on a cart (see _trojan_frame)."""
    up = _hamster_upper("normal", r, WOOD, wood=True)
    c = up.get_width() / 2
    ov = gfx.blank(*up.get_size())
    seam = (86, 52, 24, 210)
    grain = (120, 76, 36, 90)
    for i in range(-5, 6):  # wood grain: faint wavy horizontal strokes
        gy = c + i * 0.17 * r
        pts = [(c + x * r, gy + 0.03 * r * math.sin(x * 5 + i)) for x in [j / 6 - 1 for j in range(13)]]
        pygame.draw.lines(ov, grain, False, pts, 1)
    for x0 in (-0.78, -0.52, -0.26, 0.0, 0.26, 0.52, 0.78):  # staves: meridians of the ball
        pts = [(c + x0 * math.sqrt(max(0.0, 1 - y * y)) * r, c + y * r) for y in [i / 8 - 1 for i in range(17)]]
        pygame.draw.lines(ov, seam, False, pts, max(1, int(0.035 * r)))
    band = (255, 206, 70, 255) if boss else (74, 74, 88, 255)
    for y0 in (-0.38, 0.46):  # bands around the belly
        pts = [(c + x * r, c + y0 * r + 0.14 * r * (1 - x * x)) for x in [i / 8 - 1 for i in range(17)]]
        pygame.draw.lines(ov, band, False, pts, max(3, int(0.13 * r)))
        for x in (-0.7, -0.35, 0.0, 0.35, 0.7):
            pygame.draw.circle(ov, (30, 30, 40, 255), (c + x * r, c + y0 * r + 0.14 * r * (1 - x * x)), max(1, 0.03 * r))
    mask = up.copy()
    mask.fill((255, 255, 255, 255), special_flags=pygame.BLEND_RGB_MAX)
    ov.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    up.blit(ov, (0, 0))
    wins = (-0.55, -0.05, 0.45) if boss else (-0.1,)
    for hx in wins:  # windows: warm light, tiny Didit heads inside
        hy, wr = c + 0.50 * r, 0.20 * r
        pygame.draw.circle(up, (96, 60, 30), (c + hx * r, hy), wr + max(2, 0.05 * r))
        pygame.draw.circle(up, (255, 226, 140), (c + hx * r, hy), wr)
        for ex in (-0.55, 0.55):
            pygame.draw.circle(up, (250, 250, 250), (c + hx * r + ex * wr, hy - 0.7 * wr), 0.28 * wr)  # tiny ears
        pygame.draw.circle(up, (250, 248, 244), (c + hx * r, hy + 0.1 * wr), 0.7 * wr)
        for ex in (-0.28, 0.28):
            pygame.draw.circle(up, (30, 24, 30), (c + hx * r + ex * wr, hy), max(1, 0.1 * wr))
    if boss:  # crown
        crown = [(c - 0.55 * r, c - 0.95 * r), (c - 0.55 * r, c - 1.5 * r), (c - 0.27 * r, c - 1.2 * r), (c, c - 1.6 * r),
                 (c + 0.27 * r, c - 1.2 * r), (c + 0.55 * r, c - 1.5 * r), (c + 0.55 * r, c - 0.95 * r)]
        gfx.poly(up, (255, 206, 60), crown, (120, 80, 10), max(2, int(0.06 * r)))
        for dx, col in ((-0.3, (230, 50, 50)), (0, (60, 160, 255)), (0.3, (230, 50, 50))):
            pygame.draw.circle(up, col, (c + dx * r, c - 1.12 * r), max(2, 0.06 * r))
    return up


def _cycle_px() -> float:
    """Road distance (px) covered by one walk cycle; imported lazily (game.enemy imports this module)."""
    from game.enemy import WALK_FRAMES_PER_PX
    return FRAMES / WALK_FRAMES_PER_PX


def trojan_lift(r: float, ground: float = 0.08) -> float:
    """How many px the Trojan sprite must be drawn ABOVE the enemy position so the wheels stand on the
    road: the lowest wheel pixel ends up `ground * r` below the path centre line. (Wheel bottom, measured
    from the sprite canvas centre, is 1.5 r + 2 - int(0.5 r) / 2, see _trojan_frame.)"""
    return 1.5 * r + 2 - int(0.5 * r) / 2 - ground * r


def _trojan_frame(r: float, frame: int, boss: bool) -> pygame.Surface:
    phi = frame / FRAMES * math.tau
    key = ("wooden", r, boss)
    if key not in _CACHE:
        _CACHE[key] = _wooden_didit(r, boss)
    up = _CACHE[key]
    w, h = up.get_size()
    canvas = gfx.blank(w + 8, h + int(0.5 * r) + 8)
    c = canvas.get_width() / 2
    cy = c  # body centre y
    ink = (52, 30, 16)
    base = pygame.Rect(0, 0, int(2.1 * r), int(0.28 * r))  # cart platform
    base.center = (round(c), round(cy + 0.98 * r))
    pygame.draw.rect(canvas, ink, base.inflate(3, 3), border_radius=4)
    pygame.draw.rect(canvas, (118, 78, 42), base, border_radius=4)
    pygame.draw.rect(canvas, (170, 124, 72), (base.x + 2, base.y + 1, base.w - 4, max(2, base.h // 3)), border_radius=3)
    wr = 0.36 * r
    # Roll without slipping: one 8-frame cycle = FRAMES / WALK_FRAMES_PER_PX px of road. The wheel has 6 spokes
    # (60 deg symmetry), so it turns a whole number of 60 deg steps per cycle (the loop stays seamless).
    k = max(1, round(_cycle_px() / (math.tau * wr) * 6))
    for wx in (-0.62, 0.62):  # wooden wheels, spokes roll
        cx2, cy2 = c + wx * r, cy + 1.14 * r
        pygame.draw.circle(canvas, ink, (cx2, cy2), wr + 2)
        pygame.draw.circle(canvas, (112, 72, 38), (cx2, cy2), wr)
        pygame.draw.circle(canvas, (70, 44, 22), (cx2, cy2), wr * 0.72, max(1, int(0.05 * r)))
        for j in range(6):
            a = phi * k / 6 + j * math.pi / 3
            pygame.draw.line(canvas, (70, 44, 22), (cx2, cy2), (cx2 + math.cos(a) * wr * 0.9, cy2 + math.sin(a) * wr * 0.9), max(1, int(0.06 * r)))
        pygame.draw.circle(canvas, (214, 170, 100), (cx2, cy2), max(2, 0.1 * r))
    body = pygame.transform.rotozoom(up, 2.5 * math.sin(phi), 1.0)
    canvas.blit(body, body.get_rect(center=(round(c), round(cy - abs(math.sin(phi)) * 0.04 * r))))
    return canvas


# --------------------------------------------------------------------- API
def enemy_sprite(kind: str, radius: float, color, frame: int, facing_left: bool, flash: bool = False,
                 armored: int = 0, ghost: bool = False) -> pygame.Surface:
    """`armored`: 2 = full armor, 1 = damaged armor, 0 = none (Reinforced Didit). `ghost`: cyan afterimage."""
    key = ("enemy", kind, radius, frame % FRAMES, facing_left, flash, armored, ghost)
    if key not in _CACHE:
        if kind in ("trojan", "trojan_trojan"):
            img = _trojan_frame(radius, frame % FRAMES, kind == "trojan_trojan")
        else:
            img = _hamster_frame(kind, radius, color, frame % FRAMES, armored)
        if facing_left:
            img = pygame.transform.flip(img, True, False)
        if flash:
            img = img.copy()
            img.fill((130, 130, 130, 0), special_flags=pygame.BLEND_RGB_ADD)
        if ghost:
            img = img.copy()
            img.fill((0, 110, 170, 0), special_flags=pygame.BLEND_RGB_ADD)
        _CACHE[key] = img
    return _CACHE[key]


TOWER_STYLE = {
    # skin: Jalu / Romli / Bima are brown (2026-10-28); Zizi keeps her light skin.
    "jalu": {"shirt": (70, 130, 240), "hair": (46, 34, 56), "skin": (184, 128, 88)},
    "romli": {"shirt": (70, 190, 110), "hair": (30, 28, 30), "skin": (168, 112, 74)},
    "zizi": {"shirt": (176, 100, 214), "hair": (70, 40, 120), "skin": (238, 196, 156)},
    "bima": {"shirt": (255, 160, 70), "hair": (60, 36, 24), "skin": (176, 120, 82)},
    "fused_jalu_romli": {"shirt": (46, 168, 176), "hair": (46, 34, 56), "skin": (176, 120, 82)},
}


def tower_sprite(kind: str, radius: float, color, look=None) -> pygame.Surface:
    """Little maker standing on a stone pedestal. Origin (the tower position) = centre of the pedestal top.
    `look` = (path, tier) from models.look_of: costume of the followed upgrade path (see game/models.py)."""
    key = ("tower", kind, radius, look)
    if key in _CACHE:
        return _CACHE[key]
    st = dict(TOWER_STYLE.get(kind, {"shirt": color, "hair": (40, 30, 30), "skin": (240, 200, 160)}))
    cos = models.costume(kind, look)
    st.update(cos.get("style", {}))
    S = gfx.SS
    u = radius * S
    cv = gfx.blank(int(3.4 * u), int(4.6 * u))
    c = models.Ctx(cv, radius, st)
    P = c.P

    # pedestal: dark base, shaded side band, lit plate
    pygame.draw.ellipse(cv, (96, 90, 84), (*P(-1.2, 0.18), 2.4 * u, 1.12 * u))
    band = gfx.hgradient(int(2.4 * u), int(0.5 * u), [(0, (200, 194, 182)), (0.35, (168, 162, 150)), (1, (96, 90, 84))])
    cv.blit(band, P(-1.2, 0.0))
    pygame.draw.ellipse(cv, (120, 114, 104), (*P(-1.2, -0.28), 2.4 * u, 1.12 * u))
    pygame.draw.ellipse(cv, (206, 200, 188), (*P(-1.2, -0.30), 2.4 * u, 1.10 * u))
    pygame.draw.ellipse(cv, (176, 170, 158), (*P(-1.0, -0.20), 2.0 * u, 0.90 * u))
    pygame.draw.ellipse(cv, (96, 90, 84), (*P(-1.2, -0.30), 2.4 * u, 1.10 * u), max(2, int(0.05 * u)))
    if cos.get("back"):  # cape, halo...
        cos["back"](c)
    # body (shirt) with shoes
    for dx in (-0.30, 0.30):
        c.sph(0.2, st.get("shoes", (50, 42, 46)), dx, 0.12, 0.5)
    c.put(gfx.ellipsoid(int(1.2 * radius), int(1.32 * radius), st["shirt"]), 0, -0.52)
    if cos.get("body"):
        cos["body"](c)
    for dx in (-0.66, 0.66):  # arms
        c.sph(0.24, st.get("glove", st["skin"]), dx, -0.48, 0.6)
    models.hair_back(c, kind)
    if cos.get("behind_head"):
        cos["behind_head"](c)
    # head
    c.sph(0.66, st["skin"], 0, -1.32)
    models.draw_hair(c, kind, cos)
    for dx in (-0.24, 0.24):  # eyes
        c.sph(0.085, (22, 18, 26), dx, -1.28, 1.3)
    if kind == "bima":  # round glasses and a pi on the shirt
        for dx in (-0.24, 0.24):
            pygame.draw.circle(cv, (50, 36, 30), P(dx, -1.28), 0.21 * u, max(2, int(0.05 * u)))
        pygame.draw.line(cv, (50, 36, 30), P(-0.03, -1.30), P(0.03, -1.30), max(2, int(0.04 * u)))
        f = pygame.font.Font(None, int(0.95 * u))
        t = f.render("\u03c0", True, (255, 255, 255))
        cv.blit(t, t.get_rect(center=P(0, -0.5)))
    # (Romli's glasses were removed on 2026-10-28)
    pygame.draw.arc(cv, (150, 70, 70), (*P(-0.2, -1.22), 0.4 * u, 0.26 * u), math.pi * 1.15, math.pi * 1.85, max(2, int(0.045 * u)))
    if cos.get("face"):  # mask, sleepy eyelids...
        cos["face"](c)
    if cos.get("front"):  # horns, crown, headphones...
        cos["front"](c)
    img = gfx.downscale(cv, S)
    _CACHE[key] = img
    return img


def tower_origin(radius: float) -> tuple[float, float]:
    """Pixel offset of the tower position (pedestal centre) inside tower_sprite()."""
    return 1.7 * radius, 3.70 * radius


SHAPE_COLORS = [(255, 160, 60), (255, 220, 70), (90, 210, 255)]  # square, triangle, circle


def shape_sprite(shape: int, solid: bool, size: int) -> pygame.Surface:
    """Bima's shapes. 2D: flat but shaded square / triangle / circle. Solid (Lv3): cube / pyramid / sphere
    drawn as shaded faces (fake 3D, light from the top-left)."""
    key = ("shape", shape, solid, size)
    if key in _CACHE:
        return _CACHE[key]
    S = gfx.SS
    n = size * S
    cv = gfx.blank(n, n)
    col = SHAPE_COLORS[shape]
    ink = (40, 24, 20)
    u = n / 40.0

    def P(x, y):
        return (x * u, y * u)
    if not solid:
        if shape == 0:
            r = pygame.Rect(*P(8, 8), 24 * u, 24 * u)
            pygame.draw.rect(cv, ink, r.inflate(4 * u, 4 * u), border_radius=int(4 * u))
            pygame.draw.rect(cv, gfx.shade(col, 0.8), r, border_radius=int(3 * u))
            pygame.draw.rect(cv, col, r.inflate(-6 * u, -6 * u), border_radius=int(2 * u))
            pygame.draw.rect(cv, gfx.tint(col, 0.5), (r.x + 3 * u, r.y + 3 * u, 18 * u, 4 * u), border_radius=int(2 * u))
        elif shape == 1:
            tri = [P(20, 5), P(35, 33), P(5, 33)]
            pygame.draw.polygon(cv, ink, [P(20, 1), P(39, 36), P(1, 36)])
            pygame.draw.polygon(cv, gfx.shade(col, 0.8), tri)
            pygame.draw.polygon(cv, col, [P(20, 12), P(29, 29), P(11, 29)])
            pygame.draw.line(cv, gfx.tint(col, 0.6), P(20, 8), P(10, 28), max(1, int(2 * u)))
        else:
            pygame.draw.circle(cv, ink, P(20, 20), 17 * u)
            pygame.draw.circle(cv, gfx.shade(col, 0.8), P(20, 20), 15 * u)
            pygame.draw.circle(cv, col, P(19, 19), 11 * u)
            pygame.draw.circle(cv, (255, 255, 255), P(14, 13), 3 * u)
    else:
        if shape == 0:   # cube
            gfx.poly(cv, gfx.tint(col, 0.45), [P(20, 4), P(35, 12), P(20, 20), P(5, 12)], ink, max(2, int(1.5 * u)))
            gfx.poly(cv, gfx.shade(col, 0.95), [P(5, 12), P(20, 20), P(20, 37), P(5, 29)], ink, max(2, int(1.5 * u)))
            gfx.poly(cv, gfx.shade(col, 0.6), [P(20, 20), P(35, 12), P(35, 29), P(20, 37)], ink, max(2, int(1.5 * u)))
        elif shape == 1:  # pyramid
            gfx.poly(cv, gfx.tint(col, 0.35), [P(20, 3), P(4, 30), P(21, 37)], ink, max(2, int(1.5 * u)))
            gfx.poly(cv, gfx.shade(col, 0.62), [P(20, 3), P(21, 37), P(37, 29)], ink, max(2, int(1.5 * u)))
        else:  # sphere
            b = gfx.sphere(15.5, col, shine=1.2)
            big = pygame.transform.smoothscale(b, (int(34 * u), int(34 * u)))
            cv.blit(big, big.get_rect(center=P(20, 20)))
    img = gfx.downscale(cv, S)
    _CACHE[key] = img
    return img


def stack_icons(mask: int) -> pygame.Surface:
    """Three tiny slots (square, triangle, circle): filled when the enemy carries that shape. Cached per mask."""
    key = ("stack", mask)
    if key not in _CACHE:
        surf = gfx.blank(3 * 14 + 2, 14)
        for i in range(3):
            slot = pygame.Rect(i * 14 + 1, 1, 12, 12)
            pygame.draw.rect(surf, (14, 10, 20, 210), slot, border_radius=4)
            if mask & (1 << i):
                ic = shape_sprite(i, False, 12)
                surf.blit(ic, ic.get_rect(center=slot.center))
            else:
                pygame.draw.rect(surf, (255, 255, 255, 70), slot, 1, border_radius=4)
        _CACHE[key] = surf
    return _CACHE[key]
