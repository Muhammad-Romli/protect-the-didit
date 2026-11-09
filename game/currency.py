"""Didit Rupiah (DR): the meta currency. Drawn as a green paper banknote with the original Didit on it.

`note(width)` returns a cached banknote surface (aspect 5:3). Used in the menu pill, the shop prices,
the Wallstreet screen and the end screen. The in-run money stays "$".
"""
from __future__ import annotations

import pygame

from game import gfx, sprites_proc

NAME = "Didit Rupiah"
SHORT = "DR"
GREEN = (96, 224, 104)        # text colour of every DR amount
GREEN_DARK = (24, 92, 48)
PAPER = (86, 186, 100)
PAPER_LIGHT = (150, 224, 150)
INK = (38, 24, 18)
WHITE_DIDIT = (246, 244, 240)

_CACHE: dict[int, pygame.Surface] = {}


def fmt(n: int | float) -> str:
    """1500000 -> '1.500.000' (Indonesian grouping)."""
    return f"{int(round(n)):,}".replace(",", ".")


def note(width: int) -> pygame.Surface:
    if width in _CACHE:
        return _CACHE[width]
    S = 4
    W, H = width * S, round(width * 0.6) * S
    surf = gfx.blank(W, H)
    rad = H // 7
    pygame.draw.rect(surf, INK, (0, 0, W, H), border_radius=rad)
    body = gfx.vgradient(W - 6 * S, H - 6 * S, PAPER_LIGHT, PAPER)
    body.blit(gfx.rounded_mask(body.get_size(), rad - 2 * S), (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(body, (3 * S, 3 * S))
    cx, cy = W // 2, H // 2
    # guilloche: concentric rings behind the portrait + a thin inner frame
    for i in range(7):
        rr = (0.46 - i * 0.05) * H
        pygame.draw.ellipse(surf, (60, 150, 80), (cx - rr * 1.5, cy - rr, rr * 3, rr * 2), max(1, S // 2))
    pygame.draw.rect(surf, GREEN_DARK, (7 * S, 7 * S, W - 14 * S, H - 14 * S), max(1, S), border_radius=rad - 3 * S)
    # portrait medallion with the original (white) Didit
    pygame.draw.ellipse(surf, INK, (cx - 0.42 * H, cy - 0.40 * H, 0.84 * H, 0.80 * H))
    pygame.draw.ellipse(surf, (214, 244, 206), (cx - 0.39 * H, cy - 0.37 * H, 0.78 * H, 0.74 * H))
    face = sprites_proc._hamster_upper("normal", 0.26 * H, WHITE_DIDIT)
    surf.blit(face, face.get_rect(center=(cx, cy + 0.04 * H)))
    # corner values + "DR" marks
    font = pygame.font.Font(None, int(0.30 * H))
    for txt, pos in (("DR", (0.17 * W, 0.20 * H)), ("DR", (0.83 * W, 0.80 * H))):
        t = font.render(txt, True, GREEN_DARK)
        surf.blit(t, t.get_rect(center=(int(pos[0]), int(pos[1]))))
    for pos in ((0.10 * W, 0.80 * H), (0.90 * W, 0.20 * H)):
        pygame.draw.circle(surf, GREEN_DARK, (int(pos[0]), int(pos[1])), int(0.07 * H), max(1, S))
    _CACHE[width] = gfx.downscale(surf, S)
    return _CACHE[width]
