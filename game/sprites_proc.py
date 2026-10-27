"""Procedural, shaded sprites for enemies and towers (used whenever assets/sprites has no PNG).

Everything is built from lit spheres/ellipsoids (game/gfx.py), assembled once and cached:
8 walk frames per enemy (squash + bob + tilt + alternating feet), mirrored for walking left.
Sprites are centred on the entity position; shadows are drawn separately by the entity.
"""
from __future__ import annotations

import math

import pygame

from game import gfx

FRAMES = 8
_CACHE: dict[tuple, pygame.Surface] = {}


def _put(layer: pygame.Surface, img: pygame.Surface, x: float, y: float) -> None:
    layer.blit(img, img.get_rect(center=(round(x), round(y))))


def _cut_below(img: pygame.Surface, y: int) -> pygame.Surface:
    img = img.copy()
    pygame.draw.rect(img, (0, 0, 0, 0), (0, y, img.get_width(), img.get_height() - y))
    return img


# ------------------------------------------------------------------ hamster
def _hamster_upper(kind: str, r: float, color) -> pygame.Surface:
    pad = int(r * 0.9)
    size = int(2 * r + 2 * pad)
    L = gfx.blank(size, size)
    c = size / 2
    for dx in (-0.52, 0.50):  # ears
        _put(L, gfx.sphere(0.38 * r, gfx.shade(color, 0.92)), c + dx * r, c - 0.80 * r)
        _put(L, gfx.sphere(0.22 * r, (255, 168, 170), shine=0.2), c + dx * r + 0.03 * r, c - 0.78 * r)
    _put(L, gfx.sphere(r, color), c, c)
    _put(L, gfx.ellipsoid(int(1.05 * r), int(0.9 * r), (250, 232, 200), shine=0.3), c + 0.18 * r, c + 0.30 * r)
    cheek = gfx.blank(size, size)
    pygame.draw.circle(cheek, (255, 120, 130, 90), (c + 0.50 * r, c + 0.16 * r), max(2, 0.16 * r))
    L.blit(cheek, (0, 0))
    for dx in (0.28, 0.68):  # eyes
        _put(L, gfx.sphere(max(2.0, 0.17 * r), (24, 18, 26), shine=1.3), c + dx * r, c - 0.16 * r)
    _put(L, gfx.sphere(max(1.6, 0.10 * r), (255, 150, 160), shine=0.4), c + 0.94 * r, c + 0.06 * r)  # nose
    if kind == "fast":
        band = gfx.blank(size, size)
        pygame.draw.ellipse(band, (230, 50, 50), (c - 0.95 * r, c - 0.74 * r, 2.0 * r, 0.34 * r))
        mask = gfx.blank(size, size)
        pygame.draw.circle(mask, (255, 255, 255, 255), (c, c), r)
        band.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        L.blit(band, (0, 0))
    elif kind == "tanky":
        dome = gfx.sphere(1.06 * r, (150, 160, 178), bounce=(180, 200, 220), shine=1.2)
        d = _cut_below(dome, int(dome.get_height() * 0.46))
        _put(L, d, c, c - 0.10 * r - (dome.get_height() * 0.04))
        pygame.draw.line(L, (90, 98, 116), (c - 1.0 * r, c - 0.20 * r), (c + 1.0 * r, c - 0.20 * r), max(2, int(0.1 * r)))
        for dx in (-0.55, 0, 0.55):
            pygame.draw.circle(L, (210, 216, 226), (c + dx * r, c - 0.20 * r), max(1, 0.06 * r))
        for dx in (0.28, 0.68):  # angry brows
            pygame.draw.line(L, (30, 20, 20), (c + (dx - 0.16) * r, c - 0.40 * r), (c + (dx + 0.14) * r, c - 0.30 * r), max(2, int(0.08 * r)))
    elif kind == "boss":
        crown = [(c - 0.62 * r, c - 0.78 * r), (c - 0.62 * r, c - 1.42 * r), (c - 0.30 * r, c - 1.08 * r),
                 (c, c - 1.55 * r), (c + 0.30 * r, c - 1.08 * r), (c + 0.62 * r, c - 1.42 * r), (c + 0.62 * r, c - 0.78 * r)]
        gfx.poly(L, (255, 206, 60), crown, (120, 80, 10), max(2, int(0.07 * r)))
        pygame.draw.line(L, (255, 240, 150), (c - 0.55 * r, c - 0.95 * r), (c - 0.55 * r, c - 1.3 * r), max(1, int(0.05 * r)))
        for dx, col in ((-0.3, (230, 50, 50)), (0.0, (60, 160, 255)), (0.3, (230, 50, 50))):
            pygame.draw.circle(L, col, (c + dx * r, c - 0.9 * r), max(2, 0.08 * r))
        for dx in (0.28, 0.68):
            pygame.draw.line(L, (40, 0, 0), (c + (dx - 0.20) * r, c - 0.42 * r), (c + (dx + 0.16) * r, c - 0.30 * r), max(2, int(0.1 * r)))
    return L


def _hamster_frame(kind: str, r: float, color, frame: int) -> pygame.Surface:
    phi = frame / FRAMES * math.tau
    upper = _hamster_upper(kind, r, color)
    w, h = upper.get_size()
    sx = 1 + 0.05 * math.sin(2 * phi)
    img = pygame.transform.smoothscale(upper, (max(2, int(w * sx)), max(2, int(h * (2 - sx)))))
    img = pygame.transform.rotozoom(img, 5 * math.sin(phi), 1.0)
    canvas = gfx.blank(w + 8, h + 8)
    c = canvas.get_width() / 2
    lift = max(0.0, math.sin(phi)), max(0.0, -math.sin(phi))
    for side, dx in enumerate((-0.42, 0.42)):  # tiny pink feet, alternating
        pygame.draw.ellipse(canvas, (236, 150, 150), (c + dx * r - 0.22 * r, c + 0.78 * r - lift[side] * 0.22 * r, 0.46 * r, 0.30 * r))
    bob = abs(math.sin(phi)) * 0.10 * r
    _put(canvas, img, c, c - bob)
    if kind == "fast":  # speed streaks behind (left)
        for i, y in enumerate((-0.35, 0.05, 0.45)):
            pygame.draw.line(canvas, (255, 255, 255, 140), (c - 1.05 * r - 0.25 * r * (i % 2), c + y * r),
                             (c - 1.55 * r, c + y * r), max(1, int(0.07 * r)))
    return canvas


# ------------------------------------------------------------------- trojan
def _trojan_frame(r: float, frame: int, boss: bool) -> pygame.Surface:
    """Wooden Trojan horse on wheels with hamster ears peeking out of a hatch."""
    S = gfx.SS
    u = r * S
    W, H = int(3.8 * u), int(3.3 * u)
    cv = gfx.blank(W, H)
    ox, oy = 1.75 * u, 1.9 * u  # sprite origin = body centre
    phi = frame / FRAMES * math.tau
    ink = (58, 34, 18)
    wood_base = (176, 120, 62) if not boss else (190, 128, 58)

    def P(x, y):
        return (ox + x * u, oy + y * u)

    bob = abs(math.sin(phi)) * 0.05
    trim = (255, 206, 70) if boss else (70, 70, 82)
    # body box
    front = [P(-1.1, -0.6 - bob), P(0.85, -0.6 - bob), P(0.85, 0.5 - bob), P(-1.1, 0.5 - bob)]
    gfx.poly(cv, wood_base, front, ink, max(2, int(0.07 * u)))
    for y in (-0.22, 0.14):
        pygame.draw.line(cv, gfx.shade(wood_base, 0.7), P(-1.1, y - bob), P(0.85, y - bob), max(2, int(0.05 * u)))
    for x in (-0.62, 0.35):
        pygame.draw.rect(cv, trim, (*P(x, -0.6 - bob), 0.14 * u, 1.1 * u))
        pygame.draw.rect(cv, gfx.shade(trim, 0.6), (*P(x, -0.6 - bob), 0.14 * u, 1.1 * u), max(1, int(0.03 * u)))
    pygame.draw.line(cv, gfx.tint(wood_base, 0.35), P(-1.07, -0.57 - bob), P(0.82, -0.57 - bob), max(2, int(0.05 * u)))  # lit edge
    # lid (top face, lit)
    top = [P(-1.0, -0.86 - bob), P(0.78, -0.86 - bob), P(0.85, -0.6 - bob), P(-1.1, -0.6 - bob)]
    gfx.poly(cv, gfx.tint(wood_base, 0.28), top, ink, max(2, int(0.06 * u)))
    hatch_xs = (-0.55, -0.15, 0.25) if boss else (-0.2,)
    for hx in hatch_xs:
        pygame.draw.ellipse(cv, (40, 22, 12), (*P(hx - 0.22, -0.84 - bob), 0.44 * u, 0.16 * u))
    # hamster ears peeking out of the hatch(es)
    for hx in hatch_xs:
        for dx in (-0.1, 0.1):
            ex, ey = P(hx + dx, -0.93 - bob)
            pygame.draw.circle(cv, (150, 100, 56), (ex, ey), 0.20 * u)
            pygame.draw.circle(cv, (222, 168, 100), (ex - 0.02 * u, ey - 0.03 * u), 0.16 * u)
            pygame.draw.circle(cv, (255, 176, 176), (ex, ey + 0.01 * u), 0.08 * u)
    # neck + head + mane
    neck = [P(0.5, -0.55 - bob), P(0.88, -0.55 - bob), P(1.12, -1.18 - bob), P(0.8, -1.22 - bob)]
    gfx.poly(cv, wood_base, neck, ink, max(2, int(0.06 * u)))
    head = [P(0.8, -1.32 - bob), P(1.2, -1.36 - bob), P(1.55, -1.1 - bob), P(1.5, -0.92 - bob), P(1.08, -0.98 - bob)]
    gfx.poly(cv, gfx.tint(wood_base, 0.1), head, ink, max(2, int(0.06 * u)))
    mane_col = (225, 40, 50) if not boss else (255, 70, 60)
    for i in range(5):
        t = i / 4
        bx, by = 0.52 + 0.28 * t, -0.58 - 0.64 * t
        gfx.poly(cv, mane_col, [P(bx, by - bob), P(bx - 0.26, by - 0.06 - bob), P(bx - 0.04, by - 0.26 - bob)], ink, max(1, int(0.04 * u)))
    pygame.draw.circle(cv, (255, 255, 255), P(1.16, -1.2 - bob), 0.07 * u)
    pygame.draw.circle(cv, (20, 12, 12), P(1.18, -1.2 - bob), 0.04 * u)
    gfx.poly(cv, wood_base, [P(0.92, -1.34 - bob), P(0.98, -1.58 - bob), P(1.08, -1.34 - bob)], ink, max(1, int(0.04 * u)))
    if boss:  # red plume + gold helm band
        for i, a in enumerate((-0.5, -0.1, 0.3)):
            gfx.poly(cv, (225, 40, 50), [P(0.98, -1.4 - bob), P(0.98 + 0.5 * math.sin(a) - 0.1, -1.4 - 0.5 - bob), P(1.1, -1.38 - bob)], ink, max(1, int(0.04 * u)))
        pygame.draw.line(cv, trim, P(0.84, -1.3 - bob), P(1.1, -1.34 - bob), max(2, int(0.08 * u)))
    # wheels
    for wx in (-0.62, 0.42):
        c = P(wx, 0.62)
        rr = 0.36 * u
        pygame.draw.circle(cv, ink, c, rr + 0.04 * u)
        pygame.draw.circle(cv, (150, 100, 55), c, rr)
        for k in range(4):
            a = phi * 2 + k * math.pi / 2
            pygame.draw.line(cv, (96, 60, 30), c, (c[0] + math.cos(a) * rr * 0.92, c[1] + math.sin(a) * rr * 0.92), max(2, int(0.06 * u)))
        pygame.draw.circle(cv, (214, 170, 100), c, 0.1 * u)
    return gfx.downscale(cv, S)


# --------------------------------------------------------------------- API
def enemy_sprite(kind: str, radius: float, color, frame: int, facing_left: bool, flash: bool = False) -> pygame.Surface:
    key = ("enemy", kind, radius, frame % FRAMES, facing_left, flash)
    if key not in _CACHE:
        if kind in ("trojan", "trojan_trojan"):
            img = _trojan_frame(radius, frame % FRAMES, kind == "trojan_trojan")
        else:
            img = _hamster_frame(kind, radius, color, frame % FRAMES)
        if facing_left:
            img = pygame.transform.flip(img, True, False)
        if flash:
            img = img.copy()
            img.fill((130, 130, 130, 0), special_flags=pygame.BLEND_RGB_ADD)
        _CACHE[key] = img
    return _CACHE[key]


TOWER_STYLE = {
    "jalu": {"shirt": (70, 130, 240), "hair": (46, 34, 56), "skin": (244, 206, 170)},
    "romli": {"shirt": (70, 190, 110), "hair": (30, 28, 30), "skin": (226, 184, 140)},
    "zizi": {"shirt": (176, 100, 214), "hair": (70, 40, 120), "skin": (238, 196, 156)},
}


def tower_sprite(kind: str, radius: float, color) -> pygame.Surface:
    """Little maker standing on a stone pedestal. Origin (the tower position) = centre of the pedestal top."""
    key = ("tower", kind, radius)
    if key in _CACHE:
        return _CACHE[key]
    st = TOWER_STYLE.get(kind, {"shirt": color, "hair": (40, 30, 30), "skin": (240, 200, 160)})
    S = gfx.SS
    u = radius * S
    W, H = int(3.4 * u), int(4.6 * u)
    cv = gfx.blank(W, H)
    ox, oy = W / 2, 3.45 * u

    def P(x, y):
        return (ox + x * u, oy + y * u)

    def put(img, x, y):  # blit a (1x) cached sprite scaled up to supersample space
        big = pygame.transform.smoothscale(img, (img.get_width() * S, img.get_height() * S))
        cv.blit(big, big.get_rect(center=(round(P(x, y)[0]), round(P(x, y)[1]))))

    # pedestal: dark base, shaded side band, lit plate
    pygame.draw.ellipse(cv, (96, 90, 84), (*P(-1.2, 0.18), 2.4 * u, 1.12 * u))
    band = gfx.hgradient(int(2.4 * u), int(0.5 * u), [(0, (200, 194, 182)), (0.35, (168, 162, 150)), (1, (96, 90, 84))])
    cv.blit(band, P(-1.2, 0.0))
    pygame.draw.ellipse(cv, (120, 114, 104), (*P(-1.2, -0.28), 2.4 * u, 1.12 * u))
    pygame.draw.ellipse(cv, (206, 200, 188), (*P(-1.2, -0.30), 2.4 * u, 1.10 * u))
    pygame.draw.ellipse(cv, (176, 170, 158), (*P(-1.0, -0.20), 2.0 * u, 0.90 * u))
    pygame.draw.ellipse(cv, (96, 90, 84), (*P(-1.2, -0.30), 2.4 * u, 1.10 * u), max(2, int(0.05 * u)))
    # body (shirt) with shoes
    for dx in (-0.30, 0.30):
        put(gfx.sphere(0.2 * radius, (50, 42, 46), shine=0.5), dx, 0.12)
    put(gfx.ellipsoid(int(1.2 * radius), int(1.32 * radius), st["shirt"]), 0, -0.52)
    for dx in (-0.66, 0.66):  # arms
        put(gfx.sphere(0.24 * radius, st["skin"], shine=0.6), dx, -0.48)
    # head
    put(gfx.sphere(0.66 * radius, st["skin"], shine=0.8), 0, -1.32)
    hair = gfx.sphere(0.70 * radius, st["hair"], shine=0.9)
    if kind == "zizi":  # beanie with a folded brim
        cap = _cut_below(gfx.sphere(0.74 * radius, (130, 70, 180), shine=0.9), int(hair.get_height() * 0.52))
        put(cap, 0, -1.58)
        pygame.draw.rect(cv, (190, 140, 230), (*P(-0.62, -1.50), 1.24 * u, 0.16 * u), border_radius=int(0.08 * u))
    else:
        put(_cut_below(hair, int(hair.get_height() * 0.50)), 0, -1.56)
        if kind == "jalu":
            for dx in (-0.36, 0.0, 0.36):  # spiky hair
                gfx.poly(cv, st["hair"], [P(dx - 0.2, -1.82), P(dx + 0.02, -2.28 + abs(dx) * 0.2), P(dx + 0.2, -1.82)])
    for dx in (-0.24, 0.24):  # eyes
        put(gfx.sphere(0.085 * radius, (22, 18, 26), shine=1.3), dx, -1.28)
    if kind == "romli":  # glasses
        for dx in (-0.24, 0.24):
            pygame.draw.circle(cv, (40, 40, 50), P(dx, -1.28), 0.2 * u, max(2, int(0.045 * u)))
        pygame.draw.line(cv, (40, 40, 50), P(-0.05, -1.30), P(0.05, -1.30), max(2, int(0.04 * u)))
    pygame.draw.arc(cv, (150, 70, 70), (*P(-0.2, -1.22), 0.4 * u, 0.26 * u), math.pi * 1.15, math.pi * 1.85, max(2, int(0.045 * u)))
    img = gfx.downscale(cv, S)
    _CACHE[key] = img
    return img


def tower_origin(radius: float) -> tuple[float, float]:
    """Pixel offset of the tower position (pedestal centre) inside tower_sprite()."""
    return 1.7 * radius, 3.70 * radius
