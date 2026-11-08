"""Small helpers: path geometry, text drawing, range circles."""
from __future__ import annotations

import bisect
import os

import pygame

Vec = pygame.Vector2

FONT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "assets", "fonts", "LilitaOne-Regular.ttf")  # SIL OFL, see assets/fonts/OFL.txt
FONT_SCALE = 0.86  # sizes were tuned for pygame's default font; the chunky font renders larger
_FONTS: dict[int, pygame.font.Font] = {}
_TEXT_CACHE: dict[tuple, pygame.Surface] = {}


def get_font(size: int) -> pygame.font.Font:
    """Cached chunky UI font (falls back to pygame's default font if the file is missing)."""
    if size not in _FONTS:
        try:
            _FONTS[size] = pygame.font.Font(FONT_PATH, max(8, round(size * FONT_SCALE)))
        except (FileNotFoundError, pygame.error):
            _FONTS[size] = pygame.font.Font(None, size)
    return _FONTS[size]


def draw_text(surface: pygame.Surface, text: str, pos, size: int = 24,
              color=(235, 235, 240), center: bool = False) -> pygame.Rect:
    img = get_font(size).render(text, True, color)
    rect = img.get_rect(center=pos) if center else img.get_rect(topleft=pos)
    surface.blit(img, rect)
    return rect


def outlined_text(text: str, size: int, color=(255, 255, 255), outline=(38, 24, 18),
                  width: int = 2, shadow: bool = True) -> pygame.Surface:
    """BTD6-style text: fill + dark outline (+ small drop shadow), cached."""
    key = (text, size, color, outline, width, shadow)
    img = _TEXT_CACHE.get(key)
    if img is None:
        if len(_TEXT_CACHE) > 900:
            _TEXT_CACHE.clear()
        font = get_font(size)
        base, edge = font.render(text, True, color), font.render(text, True, outline)
        w, h = base.get_size()
        pad = width + (2 if shadow else 0)
        img = pygame.Surface((w + 2 * pad, h + 2 * pad), pygame.SRCALPHA)
        if shadow:
            img.blit(edge, (pad, pad + 2))
        for dx in range(-width, width + 1):
            for dy in range(-width, width + 1):
                if (dx or dy) and dx * dx + dy * dy <= width * width + 1:
                    img.blit(edge, (pad + dx, pad + dy))
        img.blit(base, (pad, pad))
        _TEXT_CACHE[key] = img
    return img


def draw_outlined(surface: pygame.Surface, text: str, pos, size: int = 24, color=(255, 255, 255),
                  center: bool = False, anchor: str = "topleft", width: int = 2,
                  outline=(38, 24, 18)) -> pygame.Rect:
    """Draw outlined text. `anchor` is any pygame.Rect attribute (midtop, midright, ...)."""
    img = outlined_text(text, size, color, outline, width)
    rect = img.get_rect(center=pos) if center else img.get_rect(**{anchor: pos})
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


_RANGE_CACHE: dict = {}


def draw_range_circle(surface: pygame.Surface, center, radius: float, color) -> None:
    """Translucent filled circle with outline (for ranges / placement preview). Cached per (radius, color)."""
    r = int(radius)
    key = (r, tuple(color))
    tmp = _RANGE_CACHE.get(key)
    if tmp is None:
        if len(_RANGE_CACHE) > 64:
            _RANGE_CACHE.clear()
        tmp = pygame.Surface((2 * r + 4, 2 * r + 4), pygame.SRCALPHA)
        pygame.draw.circle(tmp, (*color, 55), (r + 2, r + 2), r)
        pygame.draw.circle(tmp, (*color, 170), (r + 2, r + 2), r, 2)
        _RANGE_CACHE[key] = tmp
    surface.blit(tmp, (center[0] - r - 2, center[1] - r - 2))


def point_segment_distance(p: Vec, a: Vec, b: Vec) -> float:
    ab = b - a
    denom = ab.length_squared()
    if denom == 0:
        return p.distance_to(a)
    t = max(0.0, min(1.0, (p - a).dot(ab) / denom))
    return p.distance_to(a + ab * t)


def round_corners(points, radius: float, steps: int = 9) -> list[Vec]:
    """Replace every sharp corner of a polyline by a smooth quadratic curve."""
    pts = [Vec(p) for p in points]
    out = [pts[0]]
    for a, p, b in zip(pts, pts[1:], pts[2:]):
        r = min(radius, a.distance_to(p) / 2, b.distance_to(p) / 2)
        start = p + (a - p).normalize() * r
        end = p + (b - p).normalize() * r
        for i in range(steps + 1):
            t = i / steps
            out.append(start * (1 - t) ** 2 + p * (2 * t * (1 - t)) + end * t * t)
    out.append(pts[-1])
    return out


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
