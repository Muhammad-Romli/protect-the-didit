"""A'yun, the shopkeeper: a procedural character in the same style as the towers (game/models.py Ctx), plus the little
wooden stall she/he stands behind. Art only: no logic. Change the colours in STYLE to restyle A'yun.
"""
from __future__ import annotations

import math

import pygame

from game import gfx, models

STYLE = {"shirt": (250, 236, 200), "apron": (40, 150, 150), "hair": (44, 30, 28), "skin": (190, 134, 92),
         "cap": (214, 90, 70), "cap_edge": (150, 50, 40)}
_CACHE: dict[tuple, pygame.Surface] = {}


def ayun_sprite(radius: float) -> pygame.Surface:
    """A'yun standing (no pedestal). Origin = feet centre; same proportions as the towers."""
    key = ("ayun", radius)
    if key in _CACHE:
        return _CACHE[key]
    S = gfx.SS
    u = radius * S
    cv = gfx.blank(int(3.0 * u), int(4.4 * u))
    st = dict(STYLE)
    c = models.Ctx(cv, radius, st)
    P = c.P
    for dx in (-0.30, 0.30):                                      # shoes
        c.sph(0.2, (60, 44, 40), dx, 0.12, 0.5)
    c.put(gfx.ellipsoid(int(1.2 * radius), int(1.32 * radius), st["shirt"]), 0, -0.52)      # shirt
    c.put(gfx.ellipsoid(int(0.98 * radius), int(1.12 * radius), st["apron"]), 0, -0.44)     # apron
    c.poly(st["apron"], [(-0.26, -0.98), (0.26, -0.98), (0.2, -0.7), (-0.2, -0.7)])          # apron bib
    c.line(gfx.shade(st["apron"], 0.7), (-0.26, -1.0), (-0.5, -1.12), 0.06)                  # straps
    c.line(gfx.shade(st["apron"], 0.7), (0.26, -1.0), (0.5, -1.12), 0.06)
    for dx in (-0.66, 0.66):                                       # arms (hands)
        c.sph(0.24, st["skin"], dx, -0.48, 0.6)
    c.sph(0.17, (255, 190, 40), 0.66, -0.44, 0.9)                  # coin in the right hand
    c.circle((200, 120, 10), 0.66, -0.44, 0.1, 0.03)
    c.sph(0.66, st["skin"], 0, -1.32)                             # head
    hair = gfx.sphere(0.68 * r_(radius), st["hair"], shine=0.7)
    c.put(models._cut_below(hair, int(hair.get_height() * 0.5)), 0, -1.46)
    for dx in (-0.24, 0.24):                                      # eyes + brows
        c.sph(0.085, (22, 18, 26), dx, -1.28, 1.3)
        c.line((50, 34, 30), (dx - 0.1, -1.46), (dx + 0.1, -1.5), 0.04)
    for dx in (-0.4, 0.4):                                        # cheeks
        c.circle((226, 120, 110), dx, -1.14, 0.1)
    pygame.draw.arc(cv, (150, 60, 60), (*P(-0.22, -1.2), 0.44 * u, 0.3 * u), math.pi * 1.1, math.pi * 1.9, max(2, int(0.05 * u)))
    # flat merchant cap with a coin badge
    cap = gfx.sphere(0.7 * r_(radius), st["cap"], shine=0.8)
    c.put(models._cut_below(cap, int(cap.get_height() * 0.44)), 0, -1.7)
    c.ell(1.5, 0.22, st["cap_edge"], 0, -1.7, shine=0.4)
    c.sph(0.13, (255, 200, 60), 0, -1.86, 0.9)
    img = gfx.downscale(cv, S)
    _CACHE[key] = img
    return img


def r_(radius: float) -> float:
    return radius


def origin(radius: float) -> tuple[float, float]:
    """Feet position inside ayun_sprite()."""
    return 1.5 * radius, 3.45 * radius


def draw_stall(surface: pygame.Surface, rect: pygame.Rect) -> None:
    """Counter with an awning behind A'yun: rect = the area the stall may use."""
    awning = pygame.Rect(rect.x, rect.y, rect.w, 54)
    pygame.draw.rect(surface, (38, 24, 18), awning.inflate(8, 8), border_radius=14)
    n = 6
    sw = awning.w / n
    for i in range(n):
        col = (232, 84, 70) if i % 2 == 0 else (250, 240, 220)
        r = pygame.Rect(round(awning.x + i * sw), awning.y, math.ceil(sw), awning.h)
        pygame.draw.rect(surface, col, r, border_radius=10 if i in (0, n - 1) else 0)
        pygame.draw.circle(surface, col, (round(r.centerx), awning.bottom), round(sw / 2))
    back = pygame.Rect(rect.x + 10, awning.bottom + 4, rect.w - 20, rect.h - 54)
    pygame.draw.rect(surface, (110, 74, 44), back, border_radius=10)      # back wall
    for y in (back.y + 60, back.y + 130):                                    # two shelves, jars only at the sides
        pygame.draw.rect(surface, (74, 48, 28), (back.x + 10, y, back.w - 20, 8), border_radius=4)
        for k, x in enumerate((back.x + 36, back.x + 84, back.right - 84, back.right - 36)):
            col = ((255, 190, 40), (110, 200, 235), (140, 220, 120), (240, 130, 150))[(k + y // 10) % 4]
            pygame.draw.circle(surface, (38, 24, 18), (x, y - 12), 14)
            pygame.draw.circle(surface, col, (x, y - 12), 11)


def draw_counter(surface: pygame.Surface, rect: pygame.Rect) -> None:
    """The front of the counter, drawn OVER A'yun's lower body."""
    wood = gfx.wood(rect.w, rect.h)
    surface.blit(wood, rect.topleft)
    pygame.draw.rect(surface, (38, 24, 18), rect, 3, border_radius=8)
    pygame.draw.rect(surface, (214, 168, 104), (rect.x + 4, rect.y + 3, rect.w - 8, 6), border_radius=3)
