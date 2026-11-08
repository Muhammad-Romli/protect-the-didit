"""Bakes the whole static map into ONE surface (grass, raised stone path, trees, flowers, stash).

Baked once at start-up (and cached), so it costs a single blit per frame. The 3D-ish look comes from:
  * a lit grass base (bright top-left, darker bottom-right) with blotches and blades for texture
  * a path that is a raised slab: blurred ground shadow, dark south wall, light rim, cushion shading,
    individual cobblestones with bevels
  * every object (trees, bushes, rocks, flowers, stash) has a soft shadow cast to the bottom-right
"""
from __future__ import annotations

import math
import random

import pygame

from game import gfx
from game.utils import Vec, point_segment_distance

_BAKED: dict[tuple, pygame.Surface] = {}


def bake_map(points, size, path_width: int, stash_pos, seed: int = 11) -> pygame.Surface:
    key = (tuple((round(p.x), round(p.y)) for p in points), size, path_width, tuple(stash_pos))
    if key not in _BAKED:
        _BAKED[key] = _bake(points, size, path_width, stash_pos, seed)
    return _BAKED[key].copy()


def _dist_to_path(points, p) -> float:
    return min(point_segment_distance(Vec(p), a, b) for a, b in zip(points, points[1:]))


# -------------------------------------------------------------------- grass
def _grass(size, rnd: random.Random) -> pygame.Surface:
    w, h = size
    small = pygame.Surface((48, 27))
    tl, br = (132, 206, 64), (74, 152, 50)
    for y in range(27):
        for x in range(48):
            t = (x / 47 * 0.55 + y / 26 * 0.45)
            small.set_at((x, y), gfx.mix(tl, br, t))
    surf = pygame.transform.smoothscale(small, size).convert_alpha()
    blotch = gfx.blank(w // 4, h // 4)
    for _ in range(46):  # large soft light/dark patches
        col = rnd.choice([(200, 240, 90), (40, 110, 40), (170, 225, 80), (50, 130, 50)])
        pygame.draw.circle(blotch, (*col, rnd.randint(14, 30)), (rnd.randint(0, w // 4), rnd.randint(0, h // 4)),
                           rnd.randint(14, 46))
    surf.blit(pygame.transform.smoothscale(gfx.blur(blotch, 3), size), (0, 0))
    blades = gfx.blank(w, h)
    for _ in range(7500):  # grass blades
        x, y = rnd.randint(0, w), rnd.randint(0, h)
        light = rnd.random() < 0.45
        col = (190, 235, 90, 70) if light else (40, 120, 40, 80)
        pygame.draw.line(blades, col, (x, y), (x + rnd.randint(-2, 2), y - rnd.randint(3, 6)), 1)
    surf.blit(blades, (0, 0))
    return surf


# --------------------------------------------------------------------- path
def _stroke(surface, pts, color, width, dx=0, dy=0) -> None:
    shifted = [(p[0] + dx, p[1] + dy) for p in pts]
    pygame.draw.lines(surface, color, False, shifted, width)
    for p in shifted[::2] + shifted[-1:]:
        pygame.draw.circle(surface, color, p, width // 2)


def _path_layer(points, size, width: int, rnd: random.Random) -> pygame.Surface:
    """Raised stone path drawn at 2x then smoothed (anti-aliased)."""
    k = 2
    w, h = size
    pts = [(p.x * k, p.y * k) for p in points]
    W = width * k
    layer = gfx.blank(w * k, h * k)
    # ground shadow (blurred) cast down-right
    sh = gfx.blank(w * k, h * k)
    _stroke(sh, pts, (10, 40, 10, 120), W + 10, 9 * k, 11 * k)
    layer.blit(gfx.blur(sh, 6), (0, 0))
    _stroke(layer, pts, (78, 70, 64), W + 8, 0, 9 * k)      # south wall (the slab's side)
    _stroke(layer, pts, (88, 80, 72), W + 8, 0, 5 * k)
    _stroke(layer, pts, (212, 204, 188), W + 5)             # lit rim
    _stroke(layer, pts, (146, 138, 126), W - 2)             # cushion: dark edge -> bright centre
    _stroke(layer, pts, (162, 154, 142), W - 10)
    _stroke(layer, pts, (176, 168, 156), W - 22)
    # cobblestones along the path
    path = [Vec(p) for p in pts]
    total = sum(a.distance_to(b) for a, b in zip(path, path[1:]))
    d, i = 0.0, 0
    while d < total:
        acc = 0.0
        for a, b in zip(path, path[1:]):
            seg = a.distance_to(b)
            if acc + seg >= d:
                t = (d - acc) / seg if seg else 0
                pos, tan = a.lerp(b, t), (b - a).normalize()
                break
            acc += seg
        nrm = Vec(-tan.y, tan.x)
        for lane in (-1, 0, 1):
            off = lane * W * 0.29 + rnd.uniform(-3, 3) * k
            c = pos + nrm * off
            _cobble(layer, c, rnd, k, tan)
        d += rnd.uniform(24, 30) * k
        i += 1
    return gfx.downscale(layer, k)


def _cobble(layer, c: Vec, rnd: random.Random, k: int, tan: Vec) -> None:
    n = rnd.randint(5, 7)
    base = rnd.uniform(0.9, 1.12)
    rx, ry = rnd.uniform(9, 12) * k, rnd.uniform(7, 10) * k
    pts = []
    for j in range(n):
        a = j / n * math.tau + rnd.uniform(-0.2, 0.2)
        r = rnd.uniform(0.85, 1.05)
        pts.append((c.x + math.cos(a) * rx * r, c.y + math.sin(a) * ry * r))
    col = gfx.shade((184, 176, 164), base)
    pygame.draw.polygon(layer, (84, 76, 68, 210), [(x + 1.5 * k, y + 2 * k) for x, y in pts])      # gap shadow
    pygame.draw.polygon(layer, col, pts)
    inner = [(c.x + (x - c.x) * 0.7 - 1 * k, c.y + (y - c.y) * 0.7 - 1.5 * k) for x, y in pts]
    pygame.draw.polygon(layer, gfx.tint(col, 0.25), inner)                                          # lit top face
    pygame.draw.polygon(layer, gfx.shade(col, 0.7), pts, max(1, k // 2))                           # crisp edge


# ---------------------------------------------------------------- decoration
def _tree(surface, x, y, rnd: random.Random) -> None:
    gfx.blit_shadow(surface, (x + 30, y + 30), 120, 48, 85)
    trunk = pygame.Rect(x - 7, y - 4, 14, 38)
    pygame.draw.rect(surface, (92, 62, 38), trunk, border_radius=4)
    pygame.draw.rect(surface, (138, 98, 60), (trunk.x, trunk.y, 5, trunk.h), border_radius=3)
    greens = [(46, 138, 52), (58, 160, 56), (72, 176, 62)]
    blobs = [(-20, 4, 30), (22, 6, 28), (0, -20, 34), (-8, -34, 28), (16, -26, 26)]
    for dx, dy, r in blobs:
        surface.blit(gfx.sphere(r, rnd.choice(greens), bounce=(150, 200, 80)),
                     gfx.sphere(r, greens[1]).get_rect(center=(x + dx, y - 20 + dy)))


def _bush(surface, x, y, rnd: random.Random) -> None:
    gfx.blit_shadow(surface, (x + 8, y + 12), 46, 16, 80)
    for dx, dy, r in ((-9, 0, 11), (9, 1, 10), (0, -7, 12)):
        s = gfx.sphere(r, (54, 150, 54), bounce=(150, 200, 80))
        surface.blit(s, s.get_rect(center=(x + dx, y + dy)))


def _rock(surface, x, y, rnd: random.Random) -> None:
    w = rnd.randint(14, 22)
    gfx.blit_shadow(surface, (x + 4, y + 6), w + 6, 10, 90)
    s = gfx.ellipsoid(w, int(w * 0.72), (150, 150, 146), bounce=(120, 170, 110), shine=0.3)
    surface.blit(s, s.get_rect(center=(x, y)))


def _flower(surface, x, y, rnd: random.Random) -> None:
    col = rnd.choice([(255, 255, 255), (255, 236, 90), (255, 160, 200), (255, 255, 255), (170, 210, 255)])
    pygame.draw.ellipse(surface, (30, 90, 30, 90), (x - 3, y + 2, 9, 4))
    for i in range(5):
        a = i / 5 * math.tau
        pygame.draw.circle(surface, col, (x + math.cos(a) * 3.2, y + math.sin(a) * 3.2), 2.4)
    pygame.draw.circle(surface, (255, 190, 40), (x, y), 2)


def _tuft(surface, x, y, rnd: random.Random) -> None:
    for dx in (-3, 0, 3):
        pygame.draw.line(surface, (36, 110, 40), (x + dx, y), (x + dx * 1.8, y - rnd.randint(6, 10)), 2)
        pygame.draw.line(surface, (120, 200, 70), (x + dx + 1, y), (x + dx * 1.8 + 1, y - rnd.randint(5, 8)), 1)


def _stash(surface, pos) -> None:
    """Snack stash: a wooden crate piled with seeds and carrots."""
    x, y = int(pos[0]), int(pos[1]) + 6
    gfx.blit_shadow(surface, (x + 12, y + 20), 92, 28, 100)
    S = 3
    c = gfx.blank(80 * S, 70 * S)
    ox, oy = 40 * S, 38 * S
    front = [(ox - 30 * S, oy - 6 * S), (ox + 26 * S, oy - 6 * S), (ox + 26 * S, oy + 22 * S), (ox - 30 * S, oy + 22 * S)]
    top = [(ox - 30 * S, oy - 6 * S), (ox - 22 * S, oy - 18 * S), (ox + 34 * S, oy - 18 * S), (ox + 26 * S, oy - 6 * S)]
    side = [(ox + 26 * S, oy - 6 * S), (ox + 34 * S, oy - 18 * S), (ox + 34 * S, oy + 10 * S), (ox + 26 * S, oy + 22 * S)]
    gfx.poly(c, (176, 120, 62), front, (70, 44, 24), 3 * S)
    gfx.poly(c, (120, 78, 40), side, (70, 44, 24), 3 * S)
    gfx.poly(c, (206, 154, 90), top, (70, 44, 24), 3 * S)
    for yy in (oy + 3 * S, oy + 12 * S):
        pygame.draw.line(c, (100, 64, 32), (ox - 30 * S, yy), (ox + 26 * S, yy), 2 * S)
    pygame.draw.rect(c, (60, 60, 72), (ox - 24 * S, oy - 6 * S, 5 * S, 28 * S))
    pygame.draw.rect(c, (60, 60, 72), (ox + 16 * S, oy - 6 * S, 5 * S, 28 * S))
    rnd = random.Random(4)
    for _ in range(26):  # seeds on top
        sx, sy = ox + rnd.randint(-22, 26) * S, oy - 16 * S + rnd.randint(-2, 8) * S
        pygame.draw.ellipse(c, (84, 56, 34), (sx, sy - 3 * S, 6 * S, 4 * S))
        pygame.draw.ellipse(c, (150, 108, 70), (sx + S, sy - 3 * S, 3 * S, 2 * S))
    for cx, tilt in ((ox - 8 * S, -0.3), (ox + 10 * S, 0.35)):  # carrots
        tip = (cx + math.sin(tilt) * 16 * S, oy - 36 * S)
        pygame.draw.polygon(c, (240, 120, 30), [(cx - 5 * S, oy - 18 * S), (cx + 5 * S, oy - 18 * S), tip])
        for dx in (-3, 0, 3):
            pygame.draw.line(c, (70, 170, 60), tip, (tip[0] + dx * S, tip[1] - 8 * S), 2 * S)
    img = gfx.downscale(c, S)
    surface.blit(img, img.get_rect(center=(x, y - 6)))
    _original_didit(surface, x, y)


ORIGINAL_DIDIT_COLOR = (246, 244, 240)   # the real, white Didit: the one the player protects


def _original_didit(surface, x: int, y: int) -> None:
    """The original white Didit sits at the side of the stash (the enemies are the dark clones)."""
    from game import sprites_proc   # local import: sprites_proc needs a display-independent gfx only
    r = 15
    dx, dy = x - 58, y + 12
    gfx.blit_shadow(surface, (dx + 6, dy + 16), 40, 14, 100)
    img = sprites_proc._hamster_frame("normal", r, ORIGINAL_DIDIT_COLOR, 0)
    surface.blit(img, img.get_rect(center=(dx, dy)))
    for hx, hy, k in ((dx - 14, dy - 26, 1.0), (dx + 6, dy - 34, 0.7)):   # little hearts: it is loved
        pygame.draw.circle(surface, (236, 62, 52), (hx - 2, hy), int(3 * k))
        pygame.draw.circle(surface, (236, 62, 52), (hx + 2, hy), int(3 * k))
        pygame.draw.polygon(surface, (236, 62, 52), [(hx - 5 * k, hy + 1), (hx + 5 * k, hy + 1), (hx, hy + 7 * k)])


# ----------------------------------------------------------------- main bake
def _bake(points, size, path_width, stash_pos, seed) -> pygame.Surface:
    rnd = random.Random(seed)
    w, h = size
    surf = _grass(size, rnd)
    surf.blit(_path_layer(points, size, path_width, rnd), (0, 0))

    items: list[tuple[float, str, int, int]] = []  # (y, kind, x, y) drawn back-to-front
    taken: list[tuple[int, int, int]] = []

    def free(x, y, r) -> bool:
        return all(math.hypot(x - tx, y - ty) > r + tr for tx, ty, tr in taken)

    margin = path_width / 2 + 8
    for kind, count, clear, r, area in (
            ("tree", 22, path_width / 2 + 52, 38, (0, 0, w, 700)),
            ("bush", 22, path_width / 2 + 26, 16, (0, 0, w, 630)),
            ("rock", 24, margin + 6, 11, (0, 0, w, 630)),
            ("flower", 150, margin + 4, 5, (0, 0, w, 630)),
            ("tuft", 80, margin, 5, (0, 0, w, 630))):
        placed, tries = 0, 0
        while placed < count and tries < 4000:
            tries += 1
            x, y = rnd.randint(area[0] + 6, area[2] - 6), rnd.randint(area[1] + 6, area[3] - 6)
            if kind == "tree":  # trees only hug the screen edges / corners
                edge = min(x, w - x, y)
                if edge > 52:
                    continue
            if (kind == "bush" and min(x, w - x, y) > 120 and rnd.random() < 0.85):
                continue
            if _dist_to_path(points, (x, y)) < clear or not free(x, y, r):
                continue
            if math.hypot(x - stash_pos[0], y - stash_pos[1]) < 70:
                continue
            taken.append((x, y, r if kind in ("tree", "bush", "rock") else 2))
            items.append((y, kind, x, y))
            placed += 1
    draw = {"tree": _tree, "bush": _bush, "rock": _rock, "flower": _flower, "tuft": _tuft}
    for _, kind, x, y in sorted(items):
        draw[kind](surf, x, y, rnd)
    _stash(surf, stash_pos)

    # global light: soft vignette so the edges feel further away
    small = gfx.blank(64, 36)
    for yy in range(36):
        for xx in range(64):
            d = math.hypot((xx / 63 - 0.5) * 1.15, (yy / 35 - 0.5) * 1.0)
            small.set_at((xx, yy), (8, 30, 10, int(130 * max(0.0, d - 0.30) ** 1.6 * 2.2)))
    surf.blit(pygame.transform.smoothscale(small, size), (0, 0))
    return surf.convert()
