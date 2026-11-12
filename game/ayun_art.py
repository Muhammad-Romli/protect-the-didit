"""A'yun's gacha items: procedural icons (no files). Used by the tower panel, the replace-or-sell pop-up, the little
row above her head and the thrown projectiles. Icons are drawn on a 64x64 grid, supersampled, then scaled and cached.
Only pygame + game.gfx here, so any module can import it (no import cycles)."""
from __future__ import annotations

import math

import pygame

from data.ayun import ITEMS, RARITY_COLOR
from game import gfx

INK = (38, 24, 18)
_CACHE: dict[tuple, pygame.Surface] = {}


def _draw(item_id: str, S: int) -> pygame.Surface:
    n = 64 * S
    cv = gfx.blank(n, n)

    def P(x, y):
        return (x * S, y * S)

    def poly(col, pts, outline=INK, w=2.0):
        gfx.poly(cv, col, [P(*p) for p in pts], outline, max(1, int(w * S)))

    def circ(col, x, y, r, outline=INK, w=2.0):
        pygame.draw.circle(cv, col, P(x, y), r * S)
        if outline is not None:
            pygame.draw.circle(cv, outline, P(x, y), r * S, max(1, int(w * S)))

    def line(col, a, b, w=3.0):
        pygame.draw.line(cv, col, P(*a), P(*b), max(1, int(w * S)))

    if item_id == "spoon":
        line(INK, (14, 52), (38, 26), 7)
        line((176, 124, 70), (14, 52), (38, 26), 4.5)
        pygame.draw.ellipse(cv, INK, (*P(34, 8), 26 * S, 26 * S))
        pygame.draw.ellipse(cv, (196, 142, 84), (*P(36.5, 10.5), 21 * S, 21 * S))
        pygame.draw.ellipse(cv, (224, 176, 118), (*P(40, 13), 9 * S, 7 * S))
    elif item_id == "duck":
        circ((255, 214, 60), 30, 40, 18)
        circ((255, 222, 90), 40, 22, 12)
        poly((255, 140, 40), [(49, 20), (60, 24), (49, 28)], INK, 1.6)
        circ(INK, 43, 19, 2.2, None)
        pygame.draw.arc(cv, (226, 168, 30), (*P(18, 36), 20 * S, 16 * S), math.pi * 0.1, math.pi * 0.9, max(1, int(2 * S)))
    elif item_id == "sword":
        poly((222, 230, 244), [(40, 8), (52, 12), (56, 24), (22, 46), (18, 42)], INK, 2.0)
        poly((252, 254, 255), [(41, 12), (50, 15), (52, 22), (28, 40)], None)
        poly((255, 206, 60), [(12, 36), (26, 50), (22, 54), (8, 40)], INK, 2.0)     # guard
        line(INK, (14, 46), (6, 58), 7)
        line((130, 82, 44), (14, 46), (6, 58), 4.5)
        circ((255, 206, 60), 6, 58, 3.4)
    elif item_id == "pan":
        line(INK, (34, 36), (58, 56), 8)
        line((118, 90, 66), (34, 36), (58, 56), 5)
        circ((58, 62, 74), 26, 28, 20)
        circ((88, 94, 110), 26, 28, 15, None)
        circ((130, 138, 156), 20, 21, 4, None)
    elif item_id == "tomato":
        circ((226, 58, 52), 32, 36, 22)
        circ((246, 96, 86), 24, 28, 7, None)
        poly((86, 190, 70), [(32, 12), (38, 22), (50, 20), (42, 28), (46, 38), (32, 32), (18, 38), (22, 28), (14, 20), (26, 22)], INK, 1.6)
        circ((120, 160, 60), 52, 48, 4, None)                                     # a bit of splat
    elif item_id == "sauce":
        poly((214, 40, 36), [(24, 22), (40, 22), (44, 32), (46, 58), (18, 58), (20, 32)], INK, 2.0)    # bottle
        poly((240, 84, 70), [(24, 34), (30, 34), (28, 56), (22, 56)], None)
        poly((248, 236, 206), [(20, 38), (44, 38), (44, 52), (20, 52)], INK, 1.2)                      # label
        circ((220, 50, 40), 32, 45, 4.2, None)
        circ((70, 160, 70), 32, 14, 6, INK, 2.0)                                                       # cap
        poly((255, 170, 50), [(32, 2), (38, 10), (35, 14), (40, 18), (28, 18), (26, 12), (30, 8)], INK, 1.4)   # flame
    elif item_id == "tag":
        poly((250, 244, 224), [(10, 22), (34, 8), (58, 22), (58, 54), (10, 54)], INK, 2.0)
        circ((120, 100, 80), 34, 20, 3.4, INK, 1.4)
        pygame.draw.arc(cv, (220, 50, 50), (*P(20, 0), 28 * S, 28 * S), math.pi * 0.05, math.pi * 0.95, max(1, int(2.4 * S)))
        f = pygame.font.Font(None, 38 * S)
        t = f.render("$", True, (200, 40, 40))
        cv.blit(t, t.get_rect(center=P(34, 40)))
    elif item_id == "register":
        poly((255, 206, 60), [(8, 30), (56, 30), (60, 56), (4, 56)], INK, 2.2)
        poly((255, 232, 130), [(10, 32), (54, 32), (55, 38), (9, 38)], None)
        poly((196, 140, 30), [(14, 12), (50, 12), (56, 30), (8, 30)], INK, 2.0)
        poly((90, 220, 200), [(18, 15), (46, 15), (50, 26), (14, 26)], INK, 1.2)
        for x in (16, 26, 36, 46):
            circ((120, 80, 20), x, 46, 3.6, None)
        f = pygame.font.Font(None, 22 * S)
        t = f.render("$", True, (30, 70, 60))
        cv.blit(t, t.get_rect(center=P(32, 21)))
    elif item_id == "lamp":
        poly((255, 206, 60), [(10, 40), (22, 28), (44, 28), (54, 40), (46, 54), (20, 54)], INK, 2.2)
        poly((255, 236, 140), [(18, 38), (24, 32), (36, 31), (28, 40)], None)
        poly((255, 206, 60), [(50, 36), (62, 24), (60, 34), (54, 42)], INK, 1.8)       # spout
        pygame.draw.arc(cv, INK, (*P(2, 34), 16 * S, 16 * S), math.pi * 0.5, math.pi * 1.5, max(1, int(3 * S)))   # handle
        circ((255, 206, 60), 32, 24, 6, INK, 2.0)
        circ((120, 230, 255), 33, 10, 5, None)                                          # a wisp of magic
        circ((210, 250, 255), 35, 4, 3, None)
    else:                                   # unknown id: a question mark
        circ((200, 200, 210), 32, 32, 22)
        f = pygame.font.Font(None, 48 * S)
        t = f.render("?", True, INK)
        cv.blit(t, t.get_rect(center=P(32, 32)))
    return cv


def item_icon(item_id: str, size: int) -> pygame.Surface:
    """Icon of an item, `size` px square, cached."""
    key = ("icon", item_id, size)
    if key not in _CACHE:
        big = _draw(item_id, 3)
        _CACHE[key] = pygame.transform.smoothscale(big, (size, size))
    return _CACHE[key]


def rarity_color(item_id: str) -> tuple[int, int, int]:
    return RARITY_COLOR[ITEMS[item_id]["rarity"]]
