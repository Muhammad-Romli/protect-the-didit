"""Small helpers: path geometry, text drawing, range circles."""
from __future__ import annotations

import bisect

import pygame

Vec = pygame.Vector2

_FONTS: dict[int, pygame.font.Font] = {}


def get_font(size: int) -> pygame.font.Font:
    """Cached default pygame font (no system font dependency)."""
    if size not in _FONTS:
        _FONTS[size] = pygame.font.Font(None, size)
    return _FONTS[size]


def draw_text(surface: pygame.Surface, text: str, pos, size: int = 24,
              color=(235, 235, 240), center: bool = False) -> pygame.Rect:
    img = get_font(size).render(text, True, color)
    rect = img.get_rect(center=pos) if center else img.get_rect(topleft=pos)
    surface.blit(img, rect)
    return rect


def wrap_text(text: str, size: int, max_width: int) -> list[str]:
    """Greedy word wrap using the cached font."""
    font = get_font(size)
    lines: list[str] = []
    line = ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if font.size(trial)[0] <= max_width:
            line = trial
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def draw_range_circle(surface: pygame.Surface, center, radius: float, color) -> None:
    """Translucent filled circle with outline (for ranges / placement preview)."""
    r = int(radius)
    tmp = pygame.Surface((2 * r + 4, 2 * r + 4), pygame.SRCALPHA)
    pygame.draw.circle(tmp, (*color, 55), (r + 2, r + 2), r)
    pygame.draw.circle(tmp, (*color, 170), (r + 2, r + 2), r, 2)
    surface.blit(tmp, (center[0] - r - 2, center[1] - r - 2))


def point_segment_distance(p: Vec, a: Vec, b: Vec) -> float:
    ab = b - a
    denom = ab.length_squared()
    if denom == 0:
        return p.distance_to(a)
    t = max(0.0, min(1.0, (p - a).dot(ab) / denom))
    return p.distance_to(a + ab * t)


class Path:
    """Polyline path. Enemies only store `distance`; position is derived here."""

    def __init__(self, waypoints) -> None:
        self.points = [Vec(p) for p in waypoints]
        self._cum = [0.0]
        for a, b in zip(self.points, self.points[1:]):
            self._cum.append(self._cum[-1] + a.distance_to(b))
        self.length = self._cum[-1]

    def position_at(self, distance: float) -> Vec:
        d = max(0.0, min(distance, self.length))
        i = min(bisect.bisect_right(self._cum, d) - 1, len(self.points) - 2)
        seg = self._cum[i + 1] - self._cum[i]
        t = (d - self._cum[i]) / seg if seg else 0.0
        return self.points[i].lerp(self.points[i + 1], t)

    def distance_to(self, p) -> float:
        """Shortest distance from point p to the path centre line."""
        p = Vec(p)
        return min(point_segment_distance(p, a, b)
                   for a, b in zip(self.points, self.points[1:]))
