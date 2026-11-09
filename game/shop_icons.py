"""Procedural icons for the shop items (data/shop.py `icon` names). Same look as gfx.icon: dark outline, flat bright fill,
drawn supersampled and cached. `icon(name, size)` returns a size x size surface; unknown names give a question mark.
"""
from __future__ import annotations

import math

import pygame

from game import gfx

INK = (38, 24, 18)
GOLD, GOLD_L, GOLD_D = (255, 190, 40), (255, 232, 110), (200, 120, 10)
_CACHE: dict[tuple, pygame.Surface] = {}


def _coin(s, x, y, r):
    pygame.draw.circle(s, INK, (x, y), r + 3)
    pygame.draw.circle(s, GOLD, (x, y), r)
    pygame.draw.circle(s, GOLD_L, (x - r * 0.1, y - r * 0.1), r * 0.72)
    pygame.draw.circle(s, GOLD_D, (x, y), r * 0.55, max(2, int(r * 0.12)))


def _heart(s, x, y, r, col=(236, 62, 52)):
    for dx in (-1, 1):
        pygame.draw.circle(s, INK, (x + dx * r * 0.95, y - r * 0.35), r + 4)
    pygame.draw.polygon(s, INK, [(x - r * 2.2, y - r * 0.1), (x + r * 2.2, y - r * 0.1), (x, y + r * 2.7)])
    for dx in (-1, 1):
        pygame.draw.circle(s, col, (x + dx * r * 0.95, y - r * 0.35), r)
    pygame.draw.polygon(s, col, [(x - r * 1.95, y - r * 0.05), (x + r * 1.95, y - r * 0.05), (x, y + r * 2.4)])
    pygame.draw.circle(s, (255, 170, 160), (x - r * 1.2, y - r * 0.75), r * 0.3)


def _box(s, rect, col, edge=INK, w=4, rad=10):
    pygame.draw.rect(s, edge, rect.inflate(w * 2, w * 2), border_radius=rad + 2)
    pygame.draw.rect(s, col, rect, border_radius=rad)


def _arrow_up(s, x, y, size, col=(120, 240, 110)):
    pts = [(x, y - size), (x + size * 0.8, y), (x + size * 0.3, y), (x + size * 0.3, y + size), (x - size * 0.3, y + size),
           (x - size * 0.3, y), (x - size * 0.8, y)]
    pygame.draw.polygon(s, INK, [(x + (px - x) * 1.25, y + (py - y) * 1.15) for px, py in pts])
    pygame.draw.polygon(s, col, pts)


def _draw(name: str, s: pygame.Surface, S: int) -> bool:
    c = S / 2
    R = pygame.Rect
    if name == "allowance":      # coin stack
        for i, dy in enumerate((0.20, 0.02, -0.16)):
            _coin(s, c + (i - 1) * S * 0.03, c + S * dy, S * 0.25)
        _arrow_up(s, c + S * 0.30, c - S * 0.28, S * 0.13)
    elif name == "crate":        # crate + heart
        _box(s, R(S * 0.14, S * 0.34, S * 0.72, S * 0.52), (178, 126, 68))
        for i in (1, 2):
            pygame.draw.line(s, (112, 74, 38), (S * 0.16, S * (0.34 + 0.17 * i)), (S * 0.84, S * (0.34 + 0.17 * i)), int(S * 0.04))
        pygame.draw.line(s, (112, 74, 38), (S * 0.2, S * 0.4), (S * 0.8, S * 0.8), int(S * 0.04))
        _heart(s, c, S * 0.26, S * 0.12)
    elif name == "discount":     # price tag with %
        pts = [(S * 0.14, S * 0.5), (S * 0.42, S * 0.16), (S * 0.86, S * 0.16), (S * 0.86, S * 0.84), (S * 0.42, S * 0.84)]
        pygame.draw.polygon(s, INK, [(c + (x - c) * 1.1, c + (y - c) * 1.1) for x, y in pts])
        pygame.draw.polygon(s, (90, 200, 120), pts)
        pygame.draw.circle(s, INK, (S * 0.34, S * 0.5), S * 0.06)
        pygame.draw.circle(s, (255, 255, 255), (S * 0.34, S * 0.5), S * 0.035)
        f = pygame.font.Font(None, int(S * 0.5))
        t = f.render("%", True, (255, 255, 255))
        s.blit(t, t.get_rect(center=(S * 0.62, S * 0.5)))
    elif name == "wallet":       # coin with sparkles
        _coin(s, c, c, S * 0.28)
        for a in (0.2, 1.5, 3.0, 4.4):
            x, y = c + math.cos(a) * S * 0.42, c + math.sin(a) * S * 0.42
            pygame.draw.polygon(s, INK, [(x, y - S * 0.1), (x + S * 0.04, y), (x, y + S * 0.1), (x - S * 0.04, y)])
            pygame.draw.polygon(s, (255, 255, 200), [(x, y - S * 0.08), (x + S * 0.03, y), (x, y + S * 0.08), (x - S * 0.03, y)])
    elif name == "tools":        # sword
        pygame.draw.line(s, INK, (S * 0.24, S * 0.76), (S * 0.74, S * 0.26), int(S * 0.2))
        pygame.draw.line(s, (220, 230, 245), (S * 0.24, S * 0.76), (S * 0.74, S * 0.26), int(S * 0.12))
        pygame.draw.line(s, INK, (S * 0.24, S * 0.5), (S * 0.5, S * 0.76), int(S * 0.15))
        pygame.draw.line(s, (255, 190, 40), (S * 0.26, S * 0.52), (S * 0.48, S * 0.74), int(S * 0.08))
        pygame.draw.circle(s, INK, (S * 0.82, S * 0.18), S * 0.1)
        pygame.draw.circle(s, (255, 90, 80), (S * 0.82, S * 0.18), S * 0.065)
    elif name == "haggler":      # glove / coin in hand
        _box(s, R(S * 0.2, S * 0.4, S * 0.6, S * 0.42), (236, 120, 70), rad=S // 6)
        for i in range(4):
            _box(s, R(S * (0.22 + i * 0.14), S * 0.2, S * 0.1, S * 0.28), (246, 150, 90), w=3, rad=6)
        _coin(s, S * 0.62, S * 0.62, S * 0.14)
    elif name == "notes":        # book
        _box(s, R(S * 0.18, S * 0.22, S * 0.64, S * 0.58), (110, 90, 200), rad=8)
        pygame.draw.rect(s, (245, 240, 220), R(S * 0.28, S * 0.28, S * 0.5, S * 0.46), border_radius=6)
        for i in range(3):
            pygame.draw.line(s, (150, 140, 120), (S * 0.34, S * (0.38 + i * 0.1)), (S * 0.7, S * (0.38 + i * 0.1)), int(S * 0.03))
        pygame.draw.circle(s, INK, (S * 0.78, S * 0.26), S * 0.11)
        pygame.draw.circle(s, (110, 200, 235), (S * 0.78, S * 0.26), S * 0.08)
    elif name == "booster":      # coin with plus
        _coin(s, c, c, S * 0.3)
        pygame.draw.circle(s, INK, (S * 0.76, S * 0.24), S * 0.17)
        pygame.draw.circle(s, (90, 210, 90), (S * 0.76, S * 0.24), S * 0.13)
        pygame.draw.line(s, (255, 255, 255), (S * 0.76, S * 0.17), (S * 0.76, S * 0.31), int(S * 0.045))
        pygame.draw.line(s, (255, 255, 255), (S * 0.69, S * 0.24), (S * 0.83, S * 0.24), int(S * 0.045))
    elif name == "cash_drop":    # banknote + coins
        for dy, col in ((0.12, (90, 170, 90)), (-0.02, (110, 200, 110))):
            _box(s, R(S * 0.12, c + S * dy - S * 0.16, S * 0.76, S * 0.34), col, rad=6)
        pygame.draw.circle(s, INK, (c, c - S * 0.02 - S * 0.0), S * 0.13)
        pygame.draw.circle(s, (230, 255, 200), (c, c - S * 0.02), S * 0.1)
        _coin(s, S * 0.72, S * 0.74, S * 0.13)
    elif name == "stash_patch":  # heart with plus
        _heart(s, c, c - S * 0.1, S * 0.2)
        pygame.draw.circle(s, INK, (S * 0.74, S * 0.74), S * 0.16)
        pygame.draw.circle(s, (255, 255, 255), (S * 0.74, S * 0.74), S * 0.12)
        pygame.draw.line(s, (60, 190, 80), (S * 0.74, S * 0.67), (S * 0.74, S * 0.81), int(S * 0.05))
        pygame.draw.line(s, (60, 190, 80), (S * 0.67, S * 0.74), (S * 0.81, S * 0.74), int(S * 0.05))
    elif name == "freeze_bomb":  # snowflake
        for k in range(3):
            a = k * math.pi / 3
            d = (math.cos(a) * S * 0.36, math.sin(a) * S * 0.36)
            pygame.draw.line(s, INK, (c - d[0], c - d[1]), (c + d[0], c + d[1]), int(S * 0.13))
        for k in range(3):
            a = k * math.pi / 3
            d = (math.cos(a) * S * 0.36, math.sin(a) * S * 0.36)
            pygame.draw.line(s, (180, 230, 255), (c - d[0], c - d[1]), (c + d[0], c + d[1]), int(S * 0.07))
        pygame.draw.circle(s, INK, (c, c), S * 0.1)
        pygame.draw.circle(s, (235, 248, 255), (c, c), S * 0.07)
    elif name == "espresso":     # cup
        _box(s, R(S * 0.2, S * 0.38, S * 0.46, S * 0.38), (245, 240, 230), rad=S // 8)
        pygame.draw.circle(s, INK, (S * 0.72, S * 0.52), S * 0.13, int(S * 0.07))
        pygame.draw.rect(s, (110, 70, 40), R(S * 0.24, S * 0.42, S * 0.38, S * 0.08), border_radius=4)
        pygame.draw.polygon(s, INK, [(S * 0.5, S * 0.06), (S * 0.34, S * 0.3), (S * 0.46, S * 0.3), (S * 0.4, S * 0.4), (S * 0.62, S * 0.2), (S * 0.5, S * 0.2)])
        pygame.draw.polygon(s, (255, 240, 120), [(S * 0.5, S * 0.1), (S * 0.38, S * 0.28), (S * 0.5, S * 0.28), (S * 0.43, S * 0.36), (S * 0.58, S * 0.2), (S * 0.5, S * 0.2)])
    elif name == "ball_scroll":  # scroll
        _box(s, R(S * 0.22, S * 0.2, S * 0.56, S * 0.6), (245, 232, 190), rad=6)
        for dy in (0.18, 0.78):
            pygame.draw.ellipse(s, INK, R(S * 0.16, S * (dy - 0.07), S * 0.68, S * 0.14))
            pygame.draw.ellipse(s, (206, 160, 100), R(S * 0.19, S * (dy - 0.05), S * 0.62, S * 0.1))
        pygame.draw.circle(s, INK, (c, c), S * 0.15)
        pygame.draw.circle(s, (110, 200, 235), (c, c), S * 0.11)
        pygame.draw.circle(s, (255, 255, 255), (c - S * 0.04, c - S * 0.04), S * 0.035)
    else:
        return False
    return True


def icon(name: str, size: int) -> pygame.Surface:
    key = (name, size)
    if key in _CACHE:
        return _CACHE[key]
    if name == "insta_jalu":   # Jalu's portrait
        from data.towers import TOWERS
        from game import sprites_proc
        spr = sprites_proc.tower_sprite("jalu", 14, TOWERS["jalu"]["color"])
        k = size / max(spr.get_width(), spr.get_height())
        img = pygame.transform.smoothscale(spr, (max(1, round(spr.get_width() * k)), max(1, round(spr.get_height() * k))))
        out = gfx.blank(size, size) if False else pygame.Surface((size, size), pygame.SRCALPHA)
        out.blit(img, img.get_rect(center=(size // 2, size // 2)))
        _CACHE[key] = out
        return out
    S = size * gfx.SS
    surf = gfx.blank(S, S)
    if not _draw(name, surf, S):
        f = pygame.font.Font(None, int(S * 0.9))
        t = f.render("?", True, (255, 255, 255))
        surf.blit(t, t.get_rect(center=(S // 2, S // 2)))
    out = gfx.downscale(surf)
    _CACHE[key] = out
    return out
