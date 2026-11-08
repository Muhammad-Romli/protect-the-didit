"""Rendering helpers for the "3D-ish" look. Pure pygame, no numpy, everything is cached.

Techniques used across the game (one consistent light from the top-left):
  * shaded spheres (radial gradient + bounce light + specular) instead of flat circles
  * soft blurred contact shadows, offset away from the light
  * extruded / beveled shapes (a darker copy shifted down = the visible side wall)
  * baked static scenery, depth sorting by y, glossy beveled UI
Supersampling (draw at 3x, smooth-scale down) gives anti-aliased edges.
"""
from __future__ import annotations

import math

import pygame

Vec = pygame.Vector2
LIGHT = Vec(-0.55, -0.83).normalize()   # direction pointing TOWARDS the light
SHADOW_DIR = Vec(0.55, 0.83).normalize()  # shadows fall the other way
SS = 3                                   # supersampling factor for sprites

_CACHE: dict[tuple, pygame.Surface] = {}


# ------------------------------------------------------------------ colours
def mix(a, b, t: float):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


def shade(c, f: float):
    return tuple(max(0, min(255, int(v * f))) for v in c[:3])


def tint(c, f: float):
    return mix(c[:3], (255, 255, 255), f)


# ----------------------------------------------------------------- surfaces
def blank(w: int, h: int) -> pygame.Surface:
    return pygame.Surface((max(1, int(w)), max(1, int(h))), pygame.SRCALPHA)


def blur(surf: pygame.Surface, k: int = 4, passes: int = 1) -> pygame.Surface:
    """Cheap blur: shrink then enlarge smoothly."""
    w, h = surf.get_size()
    for _ in range(passes):
        small = pygame.transform.smoothscale(surf, (max(1, w // k), max(1, h // k)))
        surf = pygame.transform.smoothscale(small, (w, h))
    return surf


def downscale(surf: pygame.Surface, factor: float = SS) -> pygame.Surface:
    w, h = surf.get_size()
    return pygame.transform.smoothscale(surf, (max(1, round(w / factor)), max(1, round(h / factor))))


def vgradient(w: int, h: int, top, bottom) -> pygame.Surface:
    surf = blank(w, h)
    for y in range(h):
        pygame.draw.line(surf, mix(top, bottom, y / max(1, h - 1)), (0, y), (w, y))
    return surf


def rounded_mask(size, radius: int) -> pygame.Surface:
    m = blank(*size)
    pygame.draw.rect(m, (255, 255, 255, 255), (0, 0, *size), border_radius=radius)
    return m


def soft_shadow(w: int, h: int, alpha: int = 95) -> pygame.Surface:
    """Blurred dark ellipse of size w x h (plus blur padding). Cached."""
    key = ("shadow", w, h, alpha)
    if key not in _CACHE:
        pad = max(6, min(w, h) // 2)
        surf = blank(w + 2 * pad, h + 2 * pad)
        pygame.draw.ellipse(surf, (10, 30, 10, alpha), (pad, pad, w, h))
        _CACHE[key] = blur(surf, 3, 2)
    return _CACHE[key]


def blit_shadow(surface: pygame.Surface, center, w: int, h: int, alpha: int = 95) -> None:
    sh = soft_shadow(int(w), int(h), alpha)
    surface.blit(sh, sh.get_rect(center=(int(center[0]), int(center[1]))))


def glow(radius: int, color, alpha: int = 150) -> pygame.Surface:
    """Soft radial glow (bright centre fading to transparent). Cached."""
    key = ("glow", radius, tuple(color), alpha)
    if key not in _CACHE:
        r = max(2, int(radius))
        surf = blank(2 * r, 2 * r)
        steps = max(8, r // 2)
        for i in range(steps):
            t = i / (steps - 1)
            pygame.draw.circle(surf, (*color[:3], int(alpha * t * t / steps * 3.2)), (r, r), r * (1 - t) + 1)
        _CACHE[key] = surf
    return _CACHE[key]


# ------------------------------------------------------------------ shapes
def sphere(radius: float, color, bounce=(110, 190, 90), shine: float = 1.0) -> pygame.Surface:
    """Lit ball: dark edge -> colour -> bright core shifted to the light, bounce light on the
    shadow side (light reflected from the grass) and a specular highlight. Cached."""
    key = ("sphere", round(radius, 1), tuple(color), tuple(bounce), shine)
    if key in _CACHE:
        return _CACHE[key]
    R = max(3, int(radius * SS))
    size = 2 * R + 4
    surf = blank(size, size)
    c = size / 2
    dark, light = shade(color, 0.50), tint(color, 0.55)
    steps = max(12, int(R / 2))
    for i in range(steps):
        t = i / (steps - 1)
        rr = R * (1 - 0.80 * t)
        off = LIGHT * (R * 0.40 * t)
        col = mix(dark, color, t * 2) if t < 0.5 else mix(color, light, (t - 0.5) * 2)
        pygame.draw.circle(surf, col, (c + off.x, c + off.y), rr)
    # bounce light: crescent on the side facing away from the light
    cres = blank(size, size)
    pygame.draw.circle(cres, (*bounce, 90), (c, c), R)
    pygame.draw.circle(cres, (0, 0, 0, 0), (c + LIGHT.x * R * 0.22, c + LIGHT.y * R * 0.22), R * 0.97)
    mask = blank(size, size)
    pygame.draw.circle(mask, (255, 255, 255, 255), (c, c), R)
    cres.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(cres, (0, 0))
    if shine > 0:  # specular
        spec = blank(size, size)
        hp = (c + LIGHT.x * R * 0.46, c + LIGHT.y * R * 0.46)
        pygame.draw.circle(spec, (255, 255, 255, min(255, int(110 * shine))), hp, R * 0.20)
        pygame.draw.circle(spec, (255, 255, 255, min(255, int(220 * shine))), hp, R * 0.10)
        surf.blit(spec, (0, 0))
    elif name == "clock":
        pygame.draw.circle(surf, ink, (c, c), S * 0.46)
        pygame.draw.circle(surf, (255, 255, 255), (c, c), S * 0.40)
        pygame.draw.line(surf, ink, (c, c), (c, c - S * 0.26), max(2, S // 16))
        pygame.draw.line(surf, ink, (c, c), (c + S * 0.18, c + S * 0.08), max(2, S // 16))
    elif name == "moon":
        pygame.draw.circle(surf, ink, (c, c), S * 0.46)
        pygame.draw.circle(surf, (255, 236, 150), (c, c), S * 0.40)
        pygame.draw.circle(surf, ink, (c + S * 0.18, c - S * 0.10), S * 0.34)
        pygame.draw.circle(surf, (120, 90, 200), (c + S * 0.18, c - S * 0.10), S * 0.30)
    out = downscale(surf)
    _CACHE[key] = out
    return out


def ellipsoid(w: int, h: int, color, **kw) -> pygame.Surface:
    """A sphere squashed into w x h (still lit like a ball)."""
    key = ("ell", w, h, tuple(color), tuple(sorted(kw.items())))
    if key not in _CACHE:
        s = sphere(max(w, h) / 2, color, **kw)
        _CACHE[key] = pygame.transform.smoothscale(s, (max(2, w), max(2, h)))
    return _CACHE[key]


def hgradient(w: int, h: int, stops) -> pygame.Surface:
    """Horizontal gradient through colour `stops` [(pos 0..1, colour), ...]."""
    surf = blank(w, h)
    for x in range(w):
        t = x / max(1, w - 1)
        for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
            if p0 <= t <= p1:
                pygame.draw.line(surf, mix(c0, c1, (t - p0) / max(1e-6, p1 - p0)), (x, 0), (x, h))
                break
    return surf


def poly(surf: pygame.Surface, color, pts, outline=None, width: int = 2) -> None:
    pygame.draw.polygon(surf, color, pts)
    if outline is not None:
        pygame.draw.polygon(surf, outline, pts, width)


# --------------------------------------------------------------------- UI
def wood(w: int, h: int, seed: int = 3) -> pygame.Surface:
    """Wooden plank texture with a beveled top edge. Cached."""
    key = ("wood", w, h, seed)
    if key in _CACHE:
        return _CACHE[key]
    import random
    rnd = random.Random(seed)
    base = (150, 104, 60)
    surf = vgradient(w, h, (176, 128, 78), (122, 82, 46))
    for _ in range(w // 3):  # grain
        x, y = rnd.randint(0, w), rnd.randint(0, h)
        pygame.draw.line(surf, (*shade(base, rnd.uniform(0.62, 0.85)), 70), (x, y), (x + rnd.randint(30, 140), y), 1)
    plank = max(26, h // 3)
    for y in range(plank, h, plank):
        pygame.draw.line(surf, (70, 44, 24, 150), (0, y), (w, y), 2)
        pygame.draw.line(surf, (214, 164, 104, 90), (0, y + 2), (w, y + 2), 1)
    pygame.draw.line(surf, (226, 180, 118), (0, 0), (w, 0), 3)       # lit top edge
    pygame.draw.line(surf, (60, 38, 20), (0, h - 1), (w, h - 1), 3)  # dark bottom edge
    _CACHE[key] = surf
    return surf


def panel_surface(w: int, h: int, radius: int = 14) -> pygame.Surface:
    """Wooden frame with a navy inset (upgrade panel). Cached."""
    key = ("panel", w, h, radius)
    if key in _CACHE:
        return _CACHE[key]
    surf = blank(w + 8, h + 10)
    pygame.draw.rect(surf, (0, 0, 0, 90), (4, 8, w, h), border_radius=radius)             # drop shadow
    frame = wood(w, h)
    framed = blank(w, h)
    framed.blit(frame, (0, 0))
    framed.blit(rounded_mask((w, h), radius), (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(framed, (2, 2))
    pygame.draw.rect(surf, (60, 38, 20), (2, 2, w, h), 3, border_radius=radius)
    inner = pygame.Rect(2 + 9, 2 + 9, w - 18, h - 18)
    pygame.draw.rect(surf, (20, 30, 66), inner.move(0, 2), border_radius=radius - 4)
    body = vgradient(inner.w, inner.h, (52, 76, 138), (30, 46, 96))
    body.blit(rounded_mask(inner.size, radius - 4), (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(body, inner.topleft)
    pygame.draw.rect(surf, (18, 26, 56), inner, 2, border_radius=radius - 4)
    _CACHE[key] = surf
    return surf


def glossy(w: int, h: int, base, radius: int = 12, border=(255, 255, 255), state: str = "normal") -> pygame.Surface:
    """Glossy beveled button (white border, dark outer edge, top highlight). `state`:
    normal | hover | pressed | off. Cached."""
    key = ("glossy", w, h, tuple(base), radius, tuple(border), state)
    if key in _CACHE:
        return _CACHE[key]
    if state == "off":
        base, border = (92, 96, 108), (170, 172, 182)
    elif state == "hover":
        base = tint(base, 0.22)
    elif state == "pressed":
        base = shade(base, 0.82)
    surf = blank(w + 6, h + 8)
    drop = 2 if state == "pressed" else 5
    pygame.draw.rect(surf, (0, 0, 0, 100), (3, 1 + drop, w, h), border_radius=radius)
    pygame.draw.rect(surf, (38, 24, 18), (1, 1 + (drop - 3 if state != "pressed" else 0), w + 2, h + 2), border_radius=radius + 1)
    body = pygame.Rect(3, 3 + (drop - 3 if state != "pressed" else 0), w - 2, h - 2)
    pygame.draw.rect(surf, border, body, border_radius=radius)
    inner = body.inflate(-8, -8)
    grad = vgradient(inner.w, inner.h, tint(base, 0.35), shade(base, 0.78))
    grad.blit(rounded_mask(inner.size, max(2, radius - 4)), (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(grad, inner.topleft)
    gloss = blank(inner.w, inner.h // 2)
    pygame.draw.rect(gloss, (255, 255, 255, 62), (3, 2, inner.w - 6, inner.h // 2 - 2), border_radius=max(2, radius - 6))
    surf.blit(gloss, inner.topleft)
    pygame.draw.rect(surf, shade(base, 0.45), inner, 2, border_radius=max(2, radius - 4))
    _CACHE[key] = surf
    return surf


def pill(w: int, h: int, fill=(32, 20, 14), alpha: int = 170) -> pygame.Surface:
    """Dark rounded plate behind HUD numbers."""
    key = ("pill", w, h, tuple(fill), alpha)
    if key not in _CACHE:
        surf = blank(w, h)
        pygame.draw.rect(surf, (*fill, alpha), (0, 0, w, h), border_radius=h // 2)
        pygame.draw.rect(surf, (255, 255, 255, 60), (0, 0, w, h), 2, border_radius=h // 2)
        _CACHE[key] = surf
    return _CACHE[key]


# ------------------------------------------------------------------ icons
def icon(name: str, size: int) -> pygame.Surface:
    """Procedural HUD icons (supersampled): heart, coin, gear, play, ff, pause, book, bolt, sweep."""
    key = ("icon", name, size)
    if key in _CACHE:
        return _CACHE[key]
    S = size * SS
    surf = blank(S, S)
    c = S / 2
    ink = (38, 24, 18)
    if name == "heart":
        r = S * 0.25
        for dx in (-1, 1):
            pygame.draw.circle(surf, ink, (c + dx * r * 0.95, c - r * 0.35), r + S * 0.05)
        pygame.draw.polygon(surf, ink, [(c - r * 2.2, c - r * 0.1), (c + r * 2.2, c - r * 0.1), (c, c + r * 2.6)])
        for dx in (-1, 1):
            pygame.draw.circle(surf, (236, 62, 52), (c + dx * r * 0.95, c - r * 0.35), r)
        pygame.draw.polygon(surf, (236, 62, 52), [(c - r * 1.95, c - r * 0.05), (c + r * 1.95, c - r * 0.05), (c, c + r * 2.3)])
        pygame.draw.circle(surf, (255, 150, 140), (c - r * 1.2, c - r * 0.75), r * 0.34)
    elif name == "coin":
        pygame.draw.circle(surf, ink, (c, c), S * 0.46)
        pygame.draw.circle(surf, (255, 190, 40), (c, c), S * 0.42)
        pygame.draw.circle(surf, (255, 232, 110), (c - S * 0.03, c - S * 0.03), S * 0.34)
        pygame.draw.circle(surf, (240, 170, 30), (c, c), S * 0.27, max(2, S // 22))
        f = pygame.font.Font(None, int(S * 0.62))
        t = f.render("$", True, (200, 120, 10))
        surf.blit(t, t.get_rect(center=(c, c + S * 0.02)))
    elif name == "gear":
        pts = []
        for i in range(16):
            a = i / 16 * math.tau
            rr = S * (0.44 if i % 2 == 0 else 0.34)
            pts += [(c + math.cos(a - 0.12) * rr, c + math.sin(a - 0.12) * rr),
                    (c + math.cos(a + 0.12) * rr, c + math.sin(a + 0.12) * rr)]
        pygame.draw.polygon(surf, ink, [(c + (x - c) * 1.1, c + (y - c) * 1.1) for x, y in pts])
        pygame.draw.polygon(surf, (255, 255, 255), pts)
        pygame.draw.circle(surf, ink, (c, c), S * 0.17)
        pygame.draw.circle(surf, (70, 160, 235), (c, c), S * 0.12)
    elif name in ("play", "ff"):
        n = 1 if name == "play" else 2
        w = S * (0.52 if n == 1 else 0.36)
        for k in range(n):
            x0 = c - (w * n) / 2 + k * w * 0.95 + (S * 0.03 if n == 1 else 0)
            tri = [(x0, c - S * 0.30), (x0 + w, c), (x0, c + S * 0.30)]
            pygame.draw.polygon(surf, ink, [(x0 - 4, c - S * 0.36), (x0 + w + 8, c), (x0 - 4, c + S * 0.36)])
            pygame.draw.polygon(surf, (255, 255, 255), tri)
    elif name == "pause":
        for dx in (-0.16, 0.16):
            pygame.draw.rect(surf, ink, (c + S * dx - S * 0.13, c - S * 0.34, S * 0.26, S * 0.68), border_radius=S // 14)
            pygame.draw.rect(surf, (255, 255, 255), (c + S * dx - S * 0.09, c - S * 0.30, S * 0.18, S * 0.60), border_radius=S // 18)
    elif name == "bolt":
        pts = [(c + S * 0.08, c - S * 0.42), (c - S * 0.26, c + S * 0.06), (c - S * 0.02, c + S * 0.06),
               (c - S * 0.12, c + S * 0.42), (c + S * 0.28, c - S * 0.10), (c + S * 0.04, c - S * 0.10)]
        pygame.draw.polygon(surf, ink, [(c + (x - c) * 1.18, c + (y - c) * 1.12) for x, y in pts])
        pygame.draw.polygon(surf, (255, 240, 120), pts)
    elif name == "brain":  # ball knowledge
        pygame.draw.circle(surf, ink, (c, c), S * 0.42)
        pygame.draw.circle(surf, (110, 200, 235), (c, c), S * 0.37)
        pygame.draw.circle(surf, (190, 235, 255), (c - S * 0.08, c - S * 0.08), S * 0.22)
        pygame.draw.circle(surf, (255, 255, 255), (c - S * 0.14, c - S * 0.14), S * 0.07)
    elif name == "sweep":  # Mark's Sweep: speed lines + arrowhead
        for dy, ln in ((-0.26, 0.5), (0.0, 0.62), (0.26, 0.5)):
            y = c + S * dy
            pygame.draw.line(surf, ink, (c - S * 0.44, y), (c - S * 0.44 + S * ln, y), int(S * 0.15))
            pygame.draw.line(surf, (255, 214, 70), (c - S * 0.44, y), (c - S * 0.44 + S * ln, y), int(S * 0.09))
        head = [(c + S * 0.16, c - S * 0.36), (c + S * 0.46, c), (c + S * 0.16, c + S * 0.36)]
        pygame.draw.polygon(surf, ink, [(c + (x - c) * 1.15 - S * 0.02, c + (y - c) * 1.15) for x, y in head])
        pygame.draw.polygon(surf, (255, 255, 255), head)
    elif name == "code":  # DiditCode: </> in a terminal window
        win = (S * 0.06, S * 0.14, S * 0.88, S * 0.72)
        pygame.draw.rect(surf, ink, win, border_radius=int(S * 0.1))
        pygame.draw.rect(surf, (24, 40, 36), (win[0] + S * 0.04, win[1] + S * 0.04, win[2] - S * 0.08, win[3] - S * 0.08), border_radius=int(S * 0.07))
        g = (120, 255, 150)
        w = max(2, int(S * 0.07))
        pygame.draw.lines(surf, g, False, [(c - S * 0.12, c - S * 0.14), (c - S * 0.30, c), (c - S * 0.12, c + S * 0.14)], w)
        pygame.draw.lines(surf, g, False, [(c + S * 0.12, c - S * 0.14), (c + S * 0.30, c), (c + S * 0.12, c + S * 0.14)], w)
        pygame.draw.line(surf, g, (c + S * 0.05, c - S * 0.2), (c - S * 0.05, c + S * 0.2), w)
    elif name == "meteor":  # Galaxy Impact: a fiery cannonball with a tail
        for k, (dx, dy) in enumerate(((-0.34, -0.34), (-0.22, -0.46), (-0.46, -0.2))):
            pygame.draw.line(surf, ink, (c + S * dx, c + S * dy), (c - S * 0.08, c - S * 0.08), int(S * 0.2))
            pygame.draw.line(surf, (255, 150, 60), (c + S * dx, c + S * dy), (c - S * 0.08, c - S * 0.08), int(S * 0.12))
        pygame.draw.circle(surf, ink, (c + S * 0.12, c + S * 0.12), S * 0.34)
        pygame.draw.circle(surf, (70, 74, 90), (c + S * 0.12, c + S * 0.12), S * 0.30)
        pygame.draw.circle(surf, (150, 156, 176), (c + S * 0.04, c + S * 0.04), S * 0.16)
        pygame.draw.circle(surf, (255, 255, 255), (c - S * 0.01, c - S * 0.01), S * 0.06)
    elif name == "spiral":  # Golden Ratio: a golden spiral
        pts = []
        for i in range(0, 64):
            a = i / 63 * 3.1 * math.pi
            r = S * 0.04 * (1.618 ** (a / (math.pi / 2)))
            pts.append((c + S * 0.08 + r * math.cos(a + 3.5) * 0.9, c + S * 0.08 + r * math.sin(a + 3.5) * 0.9))
        pygame.draw.lines(surf, ink, False, pts, int(S * 0.15))
        pygame.draw.lines(surf, (255, 214, 70), False, pts, int(S * 0.09))
        pygame.draw.circle(surf, (255, 255, 255), pts[0], int(S * 0.05))
    out = downscale(surf)
    _CACHE[key] = out
    return out


def hp_bar(surface: pygame.Surface, rect: pygame.Rect, frac: float, ghost: float | None = None, gold: bool = False) -> None:
    """Health bar: dark rim, colour that shifts green -> yellow -> red, a white 'ghost' segment that
    shows the damage just taken, glossy highlight and quarter ticks."""
    frac = max(0.0, min(1.0, frac))
    r = rect.h // 2
    pygame.draw.rect(surface, (14, 10, 20), rect.inflate(4, 4), border_radius=r + 2)
    pygame.draw.rect(surface, (52, 36, 48), rect, border_radius=r)
    if ghost is not None and ghost > frac:
        g = rect.copy()
        g.w = max(rect.h, int(rect.w * min(1.0, ghost)))
        pygame.draw.rect(surface, (255, 246, 230), g, border_radius=r)
    if frac > 0:
        f = rect.copy()
        f.w = max(rect.h, int(rect.w * frac))
        col = (255, 190, 70) if gold else (mix((240, 70, 60), (250, 214, 60), frac * 2) if frac < 0.5 else mix((250, 214, 60), (96, 226, 84), (frac - 0.5) * 2))
        pygame.draw.rect(surface, col, f, border_radius=r)
        pygame.draw.rect(surface, tint(col, 0.55), (f.x + r // 2, f.y + 1, max(0, f.w - r), max(1, rect.h // 3)), border_radius=max(1, r // 2))
        pygame.draw.rect(surface, shade(col, 0.6), (f.x + r // 2, f.bottom - max(1, rect.h // 4), max(0, f.w - r), max(1, rect.h // 4)), border_radius=1)
    for q in (0.25, 0.5, 0.75):
        x = rect.x + int(rect.w * q)
        pygame.draw.line(surface, (20, 14, 26), (x, rect.y + 1), (x, rect.bottom - 2), 1)
