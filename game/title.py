"""Title menu and loading screen. Everything is drawn procedurally (no art files), in the game's own style:
a Didit walks along a cobblestone path toward the Snack Stash; while loading, the walk IS the progress bar.
"""
from __future__ import annotations

import math
import random

import pygame

from data.enemies import ENEMIES
from data.settings import COLORS, SAVE_EVERY_WAVES, SCREEN_H, SCREEN_W
from data.waves import WAVES
from game import gfx, sprites_proc, web
from game.utils import draw_outlined

TIPS = [
    "Waiting too long in preparation makes the next wave stronger.",
    "Bima can only use ONE of his two upgrade paths.",
    "Jalu's upgrades also cost ball knowledge: send him Larping in preparation.",
    "Space starts a wave, F changes the speed, P pauses.",
    f"The game saves itself every {SAVE_EVERY_WAVES} rounds. Use CONTINUE next time.",
    "Trojan Didits break open and release a crowd of smaller Didits.",
    "Right-click cancels placing a tower.",
]
GOLD = (255, 214, 90)
TRACK = pygame.Rect(0, 0, 860, 58)
TRACK.center = (SCREEN_W // 2, 592)
_STATIC: pygame.Surface | None = None
_MOTES = [(random.Random(i).random(), random.Random(i + 99).random(), 1 + (i % 3)) for i in range(18)]


def toggle_fullscreen() -> None:
    if web.IS_WEB:
        web.toggle_fullscreen()
        return
    try:
        pygame.display.toggle_fullscreen()
    except pygame.error:
        pass


# ------------------------------------------------------------------- scene
def _crate(surf: pygame.Surface, center, s: int) -> None:
    r = pygame.Rect(0, 0, s, s)
    r.center = center
    for dx, dy in ((-12, -s // 2 - 6), (4, -s // 2 - 10), (18, -s // 2 - 4)):  # snacks piled on top
        pygame.draw.circle(surf, (38, 24, 18), (r.centerx + dx, r.y + dy), 9)
        pygame.draw.circle(surf, (255, 200, 70), (r.centerx + dx, r.y + dy), 7)
    pygame.draw.rect(surf, (38, 24, 18), r.inflate(6, 6), border_radius=8)
    pygame.draw.rect(surf, (178, 126, 68), r, border_radius=6)
    for i in (1, 2):
        pygame.draw.line(surf, (112, 74, 38), (r.x + 2, r.y + i * s // 3), (r.right - 3, r.y + i * s // 3), 3)
    pygame.draw.line(surf, (112, 74, 38), (r.x + 4, r.y + 4), (r.right - 5, r.bottom - 5), 3)
    pygame.draw.rect(surf, (214, 168, 104), (r.x + 3, r.y + 3, s - 6, 5), border_radius=3)


def _static() -> pygame.Surface:
    """Backdrop, title, path and crate: drawn once, blitted every frame."""
    global _STATIC
    if _STATIC is not None:
        return _STATIC
    surf = pygame.Surface((SCREEN_W, SCREEN_H))
    for y in range(SCREEN_H):  # deep forest green, lighter toward the middle
        d = abs(y / SCREEN_H - 0.45)
        k = 1.0 - 0.9 * d
        pygame.draw.line(surf, (int(26 * k + 8), int(66 * k + 10), int(34 * k + 8)), (0, y), (SCREEN_W, y))
    rng = random.Random(11)
    for _ in range(170):  # grass tufts and flowers, low contrast
        x, y, r = rng.randrange(SCREEN_W), rng.randrange(SCREEN_H), rng.randrange(2, 6)
        pygame.draw.circle(surf, rng.choice(((34, 84, 44), (22, 56, 30), (40, 92, 50))), (x, y), r)
    for _ in range(26):
        x, y = rng.randrange(SCREEN_W), rng.randrange(SCREEN_H)
        pygame.draw.circle(surf, rng.choice(((236, 120, 150), (250, 220, 110), (170, 150, 240))), (x, y), 3)
    for i in range(70):  # edge darkening (vignette)
        a = int(110 * (1 - i / 70) ** 2)
        band = pygame.Surface((SCREEN_W, 1), pygame.SRCALPHA)
        band.fill((0, 0, 0, a))
        surf.blit(band, (0, i))
        surf.blit(band, (0, SCREEN_H - 1 - i))
    # cobblestone track (its middle groove is the progress bar)
    gfx.blit_shadow(surf, (TRACK.centerx, TRACK.bottom + 6), TRACK.w + 40, 34, 120)
    pygame.draw.rect(surf, (38, 24, 18), TRACK.inflate(10, 10), border_radius=30)
    pygame.draw.rect(surf, (150, 146, 136), TRACK, border_radius=27)
    for row, y0 in enumerate((TRACK.y + 3, TRACK.bottom - 19)):
        for i, x in enumerate(range(TRACK.x + 12 + (row * 12), TRACK.right - 30, 28)):
            tone = 166 + (i * 7 + row * 11) % 28
            pygame.draw.ellipse(surf, (tone, tone - 4, tone - 14), (x, y0, 24, 16))
            pygame.draw.ellipse(surf, (110, 106, 98), (x, y0, 24, 16), 1)
    groove = pygame.Rect(TRACK.x + 12, TRACK.centery - 7, TRACK.w - 24, 14)
    pygame.draw.rect(surf, (52, 44, 38), groove, border_radius=7)
    _crate(surf, (TRACK.right + 52, TRACK.centery - 4), 66)
    # logo
    draw_outlined(surf, "PROTECT THE", (SCREEN_W // 2, 112), 60, (255, 255, 255), center=True, width=5)
    draw_outlined(surf, "DIDIT", (SCREEN_W // 2, 206), 138, GOLD, center=True, width=7)
    draw_outlined(surf, "Keep the Snack Stash safe from the hamsters", (SCREEN_W // 2, 296), 28,
                  (240, 232, 205), center=True, width=3)
    _STATIC = surf
    return surf


def _walker(surf: pygame.Surface, t: float, x: float) -> None:
    d = ENEMIES["normal"]
    frame = int(t * 9) % sprites_proc.FRAMES
    img = sprites_proc.enemy_sprite("normal", 22, d["color"], frame, False)
    gfx.blit_shadow(surf, (x + 5, TRACK.centery + 12), 46, 14, 120)
    surf.blit(img, img.get_rect(center=(int(x), TRACK.centery - 16)))


def _scene(screen: pygame.Surface, t: float, progress: float | None) -> None:
    screen.blit(_static(), (0, 0))
    for fx, fy, size in _MOTES:  # fireflies drifting up
        x = (fx * SCREEN_W + math.sin(t * 0.8 + fy * 9) * 24) % SCREEN_W
        y = (fy * SCREEN_H - t * (10 + 6 * size)) % SCREEN_H
        pygame.draw.circle(screen, (222, 244, 170), (int(x), int(y)), size)
    x0, x1 = TRACK.x + 22, TRACK.right - 22
    if progress is None:  # menu: the Didit strolls back and forth, forever hopeful
        span = x1 - x0
        u = (t * 70) % (2 * span)
        x = x0 + (u if u < span else 2 * span - u)
        _walker(screen, t, x)
        return
    x = x0 + (x1 - x0) * max(0.0, min(1.0, progress))
    groove = pygame.Rect(TRACK.x + 12, TRACK.centery - 7, int(x - TRACK.x - 12 + 6), 14)
    if groove.w > 8:
        pygame.draw.rect(screen, (255, 200, 70), groove, border_radius=7)
        pygame.draw.rect(screen, (255, 238, 150), (groove.x + 3, groove.y + 2, max(0, groove.w - 6), 4), border_radius=3)
    _walker(screen, t, x)


def draw_loading(screen: pygame.Surface, t: float, progress: float, status: str) -> None:
    _scene(screen, t, progress)
    draw_outlined(screen, f"{int(progress * 100)}%", (SCREEN_W // 2, TRACK.bottom + 44), 34, (255, 255, 255), center=True, width=3)
    draw_outlined(screen, status, (SCREEN_W // 2, TRACK.bottom + 80), 22, (205, 225, 200), center=True)
    tip = TIPS[int(t / 3.5) % len(TIPS)]
    draw_outlined(screen, "TIP: " + tip, (SCREEN_W // 2, SCREEN_H - 34), 22, (255, 232, 170), center=True)


# -------------------------------------------------------------------- menu
class TitleMenu:
    """CONTINUE (only with a save) / NEW GAME or PLAY / FULLSCREEN."""

    def __init__(self, save: dict | None) -> None:
        self.items: list[tuple[str, str, str, tuple, pygame.Rect]] = []
        entries = []
        if save:
            nxt = min(save["wave"] + 1, len(WAVES))
            entries.append(("continue", "CONTINUE", f"Wave {nxt}   ${save['money']}   {save['towers']} towers",
                            COLORS["btn_green"], 78))
        entries.append(("new", "NEW GAME" if save else "PLAY", "", COLORS["btn_orange"], 64))
        entries.append(("fullscreen", "FULLSCREEN", "", COLORS["btn_blue"], 56))
        y = 336
        for key, label, sub, color, h in entries:
            r = pygame.Rect(0, 0, 440, h)
            r.midtop = (SCREEN_W // 2, y)
            self.items.append((key, label, sub, color, r))
            y += h + 16
        self.primary = self.items[0][0]

    def hit(self, pos) -> str | None:
        for key, _l, _s, _c, rect in self.items:
            if rect.collidepoint(pos):
                return key
        return None

    def draw(self, screen: pygame.Surface, t: float, mouse) -> None:
        _scene(screen, t, None)
        for key, label, sub, color, rect in self.items:
            hover = rect.collidepoint(mouse)
            base = gfx.shade(color, 1.12) if hover else color
            body = rect.move(0, -2 if hover else 0)
            pygame.draw.rect(screen, COLORS["ink"], body.inflate(8, 8).move(0, 4), border_radius=18)
            pygame.draw.rect(screen, gfx.shade(base, 0.74), body, border_radius=15)
            top = body.copy()
            top.h -= 8
            pygame.draw.rect(screen, base, top, border_radius=15)
            pygame.draw.rect(screen, gfx.tint(base, 0.35), (top.x + 10, top.y + 4, top.w - 20, 4), border_radius=2)
            cy = body.centery - (4 if not sub else 12)
            draw_outlined(screen, label, (body.centerx, cy), 34, (255, 255, 255), center=True, width=3)
            if sub:
                draw_outlined(screen, sub, (body.centerx, body.centery + 17), 20, (255, 255, 255), center=True)
        draw_outlined(screen, f"Autosaves every {SAVE_EVERY_WAVES} rounds in this browser" if web.IS_WEB
                      else f"Autosaves every {SAVE_EVERY_WAVES} rounds", (SCREEN_W // 2, SCREEN_H - 34), 20,
                      (205, 225, 200), center=True)
