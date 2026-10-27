"""Curve sampling + the travelling curve shot for Bima's Graph path.

sample_curve(): evaluates y = f(x) - f(0) (so the curve passes through Bima) away from Bima in one direction.
  * 2 px base step + midpoint refinement (up to 4 levels) where the chord error is over 0.75 px, so fast
    wiggles are not aliased (aliasing would under-count arc length = under-priced curves)
  * the LIVE piece ends at: map edge (clipped), range limit, a hole (nan/inf: sqrt(-1), 1/0, ln(0)), or a jump
    (tan asymptote). Nothing after the first break is fired.
  * arc length is accumulated in WORLD units while sampling -> Brain Energy cost = base + per_unit * length
"""
from __future__ import annotations

import math

import pygame

from data.bima import GRAPH, UNIT
from game.utils import Vec

_SHOT_ID = [0]


def sample_curve(f, origin: Vec, direction: int, range_units: float, bounds: pygame.Rect, cfg=GRAPH, u: float = UNIT) -> dict:
    try:
        f0 = f(0.0)
    except Exception:  # a parser bug must never crash the game
        return {"error": "Could not evaluate the formula"}
    if not math.isfinite(f0):
        return {"error": "f(0) must be a real number (the curve starts at Bima)"}
    pts = [(origin.x, origin.y)]
    cum = [0.0]
    state = {"len": 0.0, "stop": False, "why": "range"}
    max_pts, max_depth, jump = cfg["max_points"], cfg["max_depth"], cfg["jump_px"]

    def g(t):
        try:
            return f(direction * t) - f0
        except Exception:
            return math.nan

    def push(t, y):
        X, Y = origin.x + direction * t * u, origin.y - y * u
        px, py = pts[-1]
        if not bounds.collidepoint(X, Y):  # clip at the map edge, then stop
            k = 1.0
            dx, dy = X - px, Y - py
            if dx > 0:
                k = min(k, (bounds.right - px) / dx)
            elif dx < 0:
                k = min(k, (bounds.left - px) / dx)
            if dy > 0:
                k = min(k, (bounds.bottom - py) / dy)
            elif dy < 0:
                k = min(k, (bounds.top - py) / dy)
            k = max(0.0, k)
            X, Y = px + dx * k, py + dy * k
            state["stop"], state["why"] = True, "map edge"
        state["len"] += math.hypot((X - px) / u, (Y - py) / u)
        pts.append((X, Y))
        cum.append(state["len"])

    def seg(ta, ya, tb, yb, d):
        if state["stop"]:
            return
        tm = (ta + tb) / 2
        ym = g(tm)
        ok = math.isfinite(ya) and math.isfinite(yb) and math.isfinite(ym)
        flat = ok and abs(ym - (ya + yb) / 2) * u <= 0.75
        if not flat and d < max_depth:
            if len(pts) >= max_pts - 16:
                state["stop"], state["why"] = True, "too detailed"
                return
            seg(ta, ya, tm, ym, d + 1)
            seg(tm, ym, tb, yb, d + 1)
            return
        if not (math.isfinite(ya) and math.isfinite(yb)):
            state["stop"], state["why"] = True, "undefined here"
            return
        if abs(yb - ya) * u > jump:
            state["stop"], state["why"] = True, "jump"
            return
        push(tb, yb)

    dt = cfg["px_step"] / u
    ta, ya, k = 0.0, 0.0, 1
    while not state["stop"] and ta < range_units - 1e-9:
        tb = min(range_units, k * dt)
        seg(ta, ya, tb, g(tb), 0)
        ta, ya, k = tb, g(tb), k + 1
    if state["why"] == "too detailed":
        return {"error": "Curve too detailed (too many wiggles)"}
    return {"pts": pts, "cum": cum, "length": state["len"], "ended": state["why"]}


def _dist_sq(px, py, ax, ay, bx, by) -> float:
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    t = ((px - ax) * dx + (py - ay) * dy) / l2 if l2 else 0.0
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    cx, cy = ax + t * dx - px, ay + t * dy - py
    return cx * cx + cy * cy


class CurveShot:
    """A fired curve. The head travels along the polyline; each frame the swept segments are tested against
    the enemies' CURRENT positions (they move while the curve is travelling). One hit per enemy per shot."""

    def __init__(self, tower, pts, cum, cfg_tier: int, damage: float) -> None:
        _SHOT_ID[0] += 1
        self.id = _SHOT_ID[0]
        self.tower, self.pts, self.cum = tower, pts, cum
        self.total = cum[-1]
        self.s = 0.0                       # head position, world units
        self.seg = 0
        self.hits = 0
        self.fade = 0.0                    # tail fade after the head arrives
        self.damage = damage
        self.max_targets = GRAPH["max_targets"][cfg_tier]
        self.falloff = GRAPH["falloff"][cfg_tier]
        self.speed = GRAPH["speed_px"] / UNIT

    @property
    def done(self) -> bool:
        return self.s >= self.total and self.fade <= 0

    def head_pos(self) -> Vec:
        i = max(1, min(len(self.pts) - 1, self.seg + 1))
        a, b = self.pts[i - 1], self.pts[i]
        span = max(1e-6, self.cum[i] - self.cum[i - 1])
        t = max(0.0, min(1.0, (self.s - self.cum[i - 1]) / span))
        return Vec(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)

    def advance(self, dt: float, grid: dict, on_hit) -> None:
        if self.s >= self.total:
            self.fade -= dt
            return
        s0 = self.s
        self.s = min(self.total, s0 + self.speed * dt)
        i = self.seg
        n = len(self.pts)
        while i < n - 2 and self.cum[i + 1] <= s0:
            i += 1
        while i < n - 1 and self.cum[i] < self.s:
            ax, ay = self.pts[i]
            bx, by = self.pts[i + 1]
            x0, x1 = (ax, bx) if ax < bx else (bx, ax)
            y0, y1 = (ay, by) if ay < by else (by, ay)
            for cx in range(int((x0 - 48) // 64), int((x1 + 48) // 64) + 1):
                for cy in range(int((y0 - 48) // 64), int((y1 + 48) // 64) + 1):
                    for e in grid.get((cx, cy), ()):
                        if e.last_shot == self.id or not e.alive:
                            continue
                        rr = e.radius + GRAPH["half_width"]
                        if _dist_sq(e.pos.x, e.pos.y, ax, ay, bx, by) <= rr * rr and self.hits < self.max_targets:
                            e.last_shot = self.id
                            on_hit(e, self.hits)
                            self.hits += 1
            i += 1
        self.seg = max(0, i - 1)
        if self.s >= self.total:
            self.fade = 0.3

    def draw(self, surface: pygame.Surface, color=(255, 170, 70)) -> None:
        if len(self.pts) < 2:
            return
        n = 0
        upto = [self.pts[0]]
        for i in range(1, len(self.pts)):
            if self.cum[i] <= self.s:
                upto.append(self.pts[i])
            else:
                upto.append((self.head_pos().x, self.head_pos().y))
                break
        if len(upto) < 2:
            return
        alpha = 1.0 if self.s < self.total else max(0.0, self.fade / 0.3)
        for width, col in ((9, tuple(int(c * 0.35 * alpha) for c in color)), (5, tuple(int(c * 0.8 * alpha) for c in color)),
                           (2, tuple(int(255 * alpha) for _ in range(3)))):
            if width > 2:
                s_ = pygame.Surface((0, 0))  # (placeholder to keep structure simple)
            pygame.draw.lines(surface, col, False, upto, width)
        if self.s < self.total:
            hp = self.head_pos()
            from game import gfx
            g = gfx.glow(20, color, 220)
            surface.blit(g, g.get_rect(center=(int(hp.x), int(hp.y))), special_flags=pygame.BLEND_RGB_ADD)
