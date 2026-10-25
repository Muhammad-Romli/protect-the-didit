"""Optional sprites. Drop PNG/WEBP files into assets/sprites/ (names in assets/sprites/README.txt);
anything missing falls back to the colored-shape placeholder, so the game always runs."""
from __future__ import annotations

import os

import pygame

SPRITE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "sprites")
_CACHE: dict[tuple, pygame.Surface | None] = {}


def sprite(name: str, height: int | None = None, size: tuple[int, int] | None = None):
    """Load assets/sprites/<name>.png (or .webp), scaled to `height` (keeping the aspect
    ratio) or to an exact `size`. Returns None when the file is missing or unreadable."""
    key = (name, height, size)
    if key in _CACHE:
        return _CACHE[key]
    img = None
    for ext in (".png", ".webp"):
        path = os.path.join(SPRITE_DIR, name + ext)
        if os.path.isfile(path):
            try:
                img = pygame.image.load(path).convert_alpha()
            except pygame.error:
                img = None
            break
    if img is not None:
        if size is not None:
            img = pygame.transform.smoothscale(img, size)
        elif height is not None:
            w = max(1, round(img.get_width() * height / img.get_height()))
            img = pygame.transform.smoothscale(img, (w, height))
    _CACHE[key] = img
    return img
