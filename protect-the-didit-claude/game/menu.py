"""Main menu and its sub-screens (BTD6-style): MainMenu, UnitsScreen, ShopScreen, DevelopersScreen.

All screens share one tiny interface used by main.py:
    draw(screen, t, mouse)     draw one frame
    click(pos) -> str | None   a left click; returns a navigation word (see each class) or None
Nothing here needs a running Game: the screens only read data/ and the Profile (Snack Coins, shop levels, stock),
so they work before the (slow) Game is built and again every time a run ends.
Sounds: pass `audio` (game.fx.audio) once a Game exists; before that the menu is silent (browsers need a click first).
"""
from __future__ import annotations

import math
import random

import pygame

from data.settings import COLORS, SAVE_EVERY_WAVES, SCREEN_H, SCREEN_W
from data.shop import (ITEM_ORDER, ITEMS, LINES, MAX_STOCK, PERM_ORDER, PERMANENT, SHOPKEEPER)
from data.towers import DEFAULT_STATS, TOWER_ORDER, TOWERS
from data.units_info import UNITS_INFO
from data.waves import WAVES
from game import gfx, shop_icons, shopkeeper, sprites_proc, title, web
from game.profile import Profile
from game.utils import draw_outlined, wrap_text

GOLD = COLORS["gold"]
WHITE = (255, 255, 255)
DIM = (205, 215, 235)
NAVY = (28, 40, 84)
PATH_COLORS = ((90, 170, 240), (240, 170, 70))   # path A / path B borders in the UNITS screen


# ================================================================== shared bits
def _play(audio, name: str) -> None:
    if audio is not None and getattr(audio, "enabled", False):
        audio.play(name)


def button(surface, rect: pygame.Rect, base, label: str, mouse, size: int = 28, enabled: bool = True,
           pressed: bool = False, color=WHITE) -> bool:
    """Glossy button with an outlined label. Returns True when hovered."""
    hover = enabled and rect.collidepoint(mouse)
    state = "off" if not enabled else "pressed" if pressed else "hover" if hover else "normal"
    surface.blit(gfx.glossy(rect.w, rect.h, base, 14, WHITE, state), (rect.x - 1, rect.y - 1))
    draw_outlined(surface, label, rect.center, size, color if enabled else (200, 204, 214), center=True, width=3)
    return hover


def coin_pill(surface: pygame.Surface, coins: int, pulse: float = 0.0) -> None:
    """Snack Coins total, top right (like the cash counter in the BTD6 menu)."""
    r = pygame.Rect(0, 0, 250, 54)
    r.topright = (SCREEN_W - 16, 14)
    surface.blit(gfx.pill(r.w, r.h, (20, 14, 10), 200), r)
    surface.blit(gfx.icon("coin", 46), (r.x + 4, r.y + 4))
    size = 34 + int(6 * pulse)
    draw_outlined(surface, f"{coins}", (r.right - 16, r.centery - 2), size, GOLD if pulse < 0.05 else WHITE,
                  anchor="midright", width=3)
    draw_outlined(surface, "SNACK COINS", (r.right - 8, r.bottom + 12), 14, DIM, anchor="midright", width=1)


def title_text(surface: pygame.Surface, text: str, y: int = 54) -> None:
    draw_outlined(surface, text, (SCREEN_W // 2, y), 62, GOLD, center=True, width=5)


def wood_panel(surface: pygame.Surface, rect: pygame.Rect) -> None:
    surface.blit(gfx.panel_surface(rect.w, rect.h), (rect.x - 2, rect.y - 2))


def _fullscreen_icon(surface: pygame.Surface, rect: pygame.Rect) -> None:
    c, s = rect.center, 12
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = c[0] + sx * s, c[1] + sy * s
            pygame.draw.lines(surface, WHITE, False, [(x - sx * 9, y), (x, y), (x, y - sy * 9)], 5)


# ======================================================================= main menu
class MainMenu:
    """Bottom row like BTD6: UNITS, SHOP, PLAY (big), DEVELOPERS, EXIT; Snack Coins top right.
    click() returns: play | continue | units | shop | developers | exit | fullscreen | None."""

    def __init__(self, profile: Profile, save: dict | None) -> None:
        self.profile, self.save = profile, save
        self.circles = [("units", "UNITS", 44, 340, 624), ("shop", "SHOP", 44, 490, 624),
                        ("play", "PLAY", 62, 640, 614), ("developers", "DEVELOPERS", 44, 790, 624),
                        ("exit", "EXIT", 44, 940, 624)]
        self.continue_btn = pygame.Rect(0, 0, 420, 66)
        self.continue_btn.center = (SCREEN_W // 2, 358)
        self.fullscreen_btn = pygame.Rect(16, 14, 58, 58)
        self.primary = "continue" if save else "play"
        self._mouse = (0, 0)

    def _circle_at(self, pos) -> str | None:
        for key, _label, r, x, y in self.circles:
            if math.hypot(pos[0] - x, pos[1] - y) <= r + 4:
                return key
        return None

    def click(self, pos) -> str | None:
        if self.save and self.continue_btn.collidepoint(pos):
            return "continue"
        if self.fullscreen_btn.collidepoint(pos):
            return "fullscreen"
        return self._circle_at(pos)

    def _icon(self, surface, key: str, x: int, y: int, r: int) -> None:
        if key == "play":
            img = gfx.icon("play", 84)
        elif key == "units":
            spr = sprites_proc.tower_sprite("jalu", 14, TOWERS["jalu"]["color"])
            k = 84 / spr.get_height()
            img = pygame.transform.smoothscale(spr, (round(spr.get_width() * k), 84))
        elif key == "shop":
            img = shop_icons.icon("allowance", 64)
        else:
            img = None
        if img is not None:
            surface.blit(img, img.get_rect(center=(x, y)))
        elif key == "developers":
            draw_outlined(surface, "</>", (x, y - 2), 34, WHITE, center=True, width=3)
        elif key == "exit":   # power symbol
            pts = [(x + 22 * math.cos(math.radians(a)), y + 4 + 22 * math.sin(math.radians(a))) for a in range(-50, 231, 10)]
            pygame.draw.lines(surface, (38, 24, 18), False, pts, 11)
            pygame.draw.lines(surface, WHITE, False, pts, 6)
            pygame.draw.line(surface, (38, 24, 18), (x, y - 30), (x, y - 2), 11)
            pygame.draw.line(surface, WHITE, (x, y - 30), (x, y - 2), 6)

    def draw(self, screen: pygame.Surface, t: float, mouse) -> None:
        title._scene(screen, t, None)
        hovered = self._circle_at(mouse)
        colors = {"units": COLORS["btn_blue"], "shop": COLORS["btn_orange"], "play": COLORS["btn_green"],
                  "developers": (150, 90, 210), "exit": COLORS["btn_red"]}
        for key, label, r, x, y in self.circles:
            hov = hovered == key
            rr = r + (4 if hov else 0)
            pygame.draw.circle(screen, (0, 0, 0, 0) if False else (20, 14, 10), (x, y + 6), rr + 5)
            pygame.draw.circle(screen, (38, 24, 18), (x, y), rr + 4)
            pygame.draw.circle(screen, WHITE, (x, y), rr)
            base = colors[key]
            pygame.draw.circle(screen, gfx.shade(base, 0.78), (x, y), rr - 5)
            pygame.draw.circle(screen, gfx.tint(base, 0.18) if hov else base, (x, y - 2), rr - 8)
            pygame.draw.ellipse(screen, gfx.tint(base, 0.5), (x - rr * 0.6, y - rr * 0.82, rr * 1.2, rr * 0.7))
            self._icon(screen, key, x, y, r)
            draw_outlined(screen, label, (x, y + rr + 20), 30 if key == "play" else 22, WHITE, center=True, width=3)
        if self.save:
            nxt = min(self.save["wave"] + 1, len(WAVES))
            sub = f"Wave {nxt}   ${self.save['money']}   {self.save['towers']} towers"
            hov = button(screen, self.continue_btn, COLORS["btn_green"], "", mouse)
            lift = -2 if hov else 0
            draw_outlined(screen, "CONTINUE", (self.continue_btn.centerx, self.continue_btn.centery - 11 + lift), 32, WHITE, center=True, width=3)
            draw_outlined(screen, sub, (self.continue_btn.centerx, self.continue_btn.centery + 17 + lift), 18, WHITE, center=True, width=1)
        hov = self.fullscreen_btn.collidepoint(mouse)
        screen.blit(gfx.glossy(58, 58, COLORS["btn_blue"], 14, WHITE, "hover" if hov else "normal"),
                    (self.fullscreen_btn.x - 1, self.fullscreen_btn.y - 1))
        _fullscreen_icon(screen, self.fullscreen_btn)
        coin_pill(screen, self.profile.coins)
        p = self.profile
        draw_outlined(screen, f"Runs {p.runs}   Wins {p.wins}   Best wave {p.best_wave}", (SCREEN_W // 2, 514), 20, DIM,
                      center=True, width=2)
        draw_outlined(screen, ("Autosaves every %d rounds in this browser" if web.IS_WEB else "Autosaves every %d rounds") % SAVE_EVERY_WAVES,
                      (SCREEN_W // 2, 538), 17, (170, 195, 170), center=True, width=1)


# ====================================================================== developers
class DevelopersScreen:
    """Empty for now (on purpose). click() returns 'back'."""

    def __init__(self) -> None:
        self.back = pygame.Rect(30, 646, 200, 58)
        self.panel = pygame.Rect(150, 110, SCREEN_W - 300, 510)

    def click(self, pos) -> str | None:
        return "back" if self.back.collidepoint(pos) else None

    def draw(self, screen: pygame.Surface, t: float, mouse) -> None:
        title.draw_backdrop(screen, t)
        title_text(screen, "DEVELOPERS")
        wood_panel(screen, self.panel)
        button(screen, self.back, COLORS["btn_orange"], "BACK", mouse, 30)


# ========================================================================== units
class UnitsScreen:
    """Left: the four characters. Middle: portrait, short description, base stats. Right: both upgrade paths
    (name, price, description). Hover or click a tier to see the portrait wear that tier's costume.
    click() returns 'back' or None."""

    TAB_W, TAB_H = 232, 98
    CARD_W, CARD_H = 313, 114

    def __init__(self) -> None:
        self.idx = 0
        self.sel: tuple[int, int] | None = None   # (path, tier) chosen by a click; None = base look
        self.back = pygame.Rect(30, 646, 200, 58)
        self.tabs = [(k, pygame.Rect(30, 104 + i * (self.TAB_H + 8), self.TAB_W, self.TAB_H)) for i, k in enumerate(TOWER_ORDER)]
        self.char_panel = pygame.Rect(278, 104, 322, 540)
        self.cards = {(p, i): pygame.Rect(616 + p * (self.CARD_W + 12), 156 + i * (self.CARD_H + 6), self.CARD_W, self.CARD_H)
                      for p in (0, 1) for i in range(4)}

    @property
    def kind(self) -> str:
        return TOWER_ORDER[self.idx]

    def click(self, pos) -> str | None:
        if self.back.collidepoint(pos):
            return "back"
        for i, (_k, rect) in enumerate(self.tabs):
            if rect.collidepoint(pos):
                self.idx, self.sel = i, None
                return None
        for key, rect in self.cards.items():
            if rect.collidepoint(pos):
                self.sel = None if self.sel == (key[0], key[1] + 1) else (key[0], key[1] + 1)
                return None
        return None

    def _look(self, mouse) -> tuple[int, int] | None:
        for (p, i), rect in self.cards.items():
            if rect.collidepoint(mouse):
                return (p, i + 1)
        return self.sel

    def draw(self, screen: pygame.Surface, t: float, mouse) -> None:
        title.draw_backdrop(screen, t)
        title_text(screen, "UNITS")
        kind, data = self.kind, TOWERS[self.kind]
        info = UNITS_INFO[kind]
        for k, rect in self.tabs:   # character tabs
            on, hov = k == kind, rect.collidepoint(mouse)
            screen.blit(gfx.glossy(rect.w, rect.h, COLORS["btn_blue"] if on else (84, 92, 120), 14, WHITE if on else (190, 196, 214),
                                   "pressed" if on else "hover" if hov else "normal"), (rect.x - 1, rect.y - 1))
            spr = sprites_proc.tower_sprite(k, 14, TOWERS[k]["color"])
            sc = pygame.transform.smoothscale(spr, (round(spr.get_width() * 66 / spr.get_height()), 66))
            screen.blit(sc, sc.get_rect(midleft=(rect.x + 14, rect.centery)))
            draw_outlined(screen, TOWERS[k]["name"], (rect.x + 88, rect.centery - 14), 32, WHITE, anchor="midleft", width=3)
            draw_outlined(screen, UNITS_INFO[k]["role"], (rect.x + 88, rect.centery + 16), 15, (225, 235, 255), anchor="midleft", width=1)
        # character panel
        cp = self.char_panel
        wood_panel(screen, cp)
        look = self._look(mouse)
        spr = sprites_proc.tower_sprite(kind, 44, data["color"], look)
        gfx.blit_shadow(screen, (cp.centerx, cp.y + 30 + spr.get_height() - 40), 150, 34, 120)
        screen.blit(spr, spr.get_rect(midtop=(cp.centerx, cp.y + 22)))
        y = cp.y + 22 + spr.get_height() + 6
        draw_outlined(screen, data["name"], (cp.centerx, y), 40, GOLD, center=True, width=4)
        if look is None:
            sub = info["role"]
        else:
            up = data["paths"][look[0]]["tiers"][look[1] - 1]
            sub = f"{'AB'[look[0]]}{look[1]}: {up['name']}"
        draw_outlined(screen, sub, (cp.centerx, y + 30), 19, (210, 235, 255), center=True, width=2)
        y += 52
        for line in wrap_text(info["blurb"], 17, cp.w - 40):
            draw_outlined(screen, line, (cp.x + 20, y), 17, WHITE, width=1)
            y += 21
        y += 4
        for line in wrap_text(info["rule"], 15, cp.w - 40):
            draw_outlined(screen, line, (cp.x + 20, y), 15, (255, 224, 150), width=1)
            y += 18
        st = {**DEFAULT_STATS, **data["stats"]}
        stats = [("Cost", f"${data['cost']}"), ("Damage", f"{st['damage']:g}"), ("Range", f"{st['range']:g}"),
                 ("Speed", f"{1 / st['cooldown']:.1f}/s")]
        for i, (lab, val) in enumerate(stats):
            bx = pygame.Rect(cp.x + 16 + (i % 2) * 146, cp.bottom - 78 + (i // 2) * 34, 138, 28)
            screen.blit(gfx.pill(bx.w, bx.h, (14, 22, 52), 170), bx)
            draw_outlined(screen, lab, (bx.x + 12, bx.centery), 15, DIM, anchor="midleft", width=1)
            draw_outlined(screen, val, (bx.right - 12, bx.centery), 18, WHITE, anchor="midright", width=2)
        # upgrade paths
        for p, path in enumerate(data["paths"]):
            head = pygame.Rect(616 + p * (self.CARD_W + 12), 104, self.CARD_W, 44)
            screen.blit(gfx.glossy(head.w, head.h, PATH_COLORS[p], 12, WHITE, "normal"), (head.x - 1, head.y - 1))
            draw_outlined(screen, f"PATH {'AB'[p]}:  {path['name']}", head.center, 24, WHITE, center=True, width=3)
            for i, up in enumerate(path["tiers"]):
                self._card(screen, self.cards[(p, i)], p, i, up, mouse)
        button(screen, self.back, COLORS["btn_orange"], "BACK", mouse, 30)

    def _card(self, screen, rect: pygame.Rect, p: int, i: int, up: dict, mouse) -> None:
        on = self.sel == (p, i + 1)
        hov = rect.collidepoint(mouse)
        pygame.draw.rect(screen, (20, 14, 10), rect.move(0, 3), border_radius=12)
        pygame.draw.rect(screen, (46, 62, 118) if hov or on else NAVY, rect, border_radius=12)
        pygame.draw.rect(screen, WHITE if on else PATH_COLORS[p], rect, 4 if on else 3, border_radius=12)
        badge = (rect.x + 24, rect.y + 24)
        pygame.draw.circle(screen, (38, 24, 18), badge, 17)
        pygame.draw.circle(screen, PATH_COLORS[p], badge, 14)
        draw_outlined(screen, str(i + 1), badge, 20, WHITE, center=True, width=2)
        draw_outlined(screen, up["name"], (rect.x + 48, rect.y + 24), 20, WHITE, anchor="midleft", width=2)
        cost = f"${up['cost']}" + (f" + {up['knowledge']} KN" if up.get("knowledge") else "")
        draw_outlined(screen, cost, (rect.right - 10, rect.y + 24), 16, GOLD, anchor="midright", width=1)
        y = rect.y + 50
        for line in wrap_text(up["description"], 15, rect.w - 26)[:3]:
            draw_outlined(screen, line, (rect.x + 14, y), 15, (222, 230, 250), width=1)
            y += 19


# ========================================================================== shop
def bonus_text(pid: str, value: float) -> str:
    unit = PERMANENT[pid]["unit"]
    if unit == "%":
        return f"+{round(value * 100)}%"
    if unit == "$":
        return f"+${int(value)}"
    return f"+{int(value)}{unit}"


class ShopScreen:
    """A'yun's stall. Tabs: PERMANENT (levels, buff every run) / IN-GAME (one-use items). A click on a card buys.
    click() returns 'back' or None; purchases go straight to the Profile (which saves itself)."""

    CARD_W, CARD_H = 196, 236

    def __init__(self, profile: Profile, audio=None) -> None:
        self.profile, self.audio = profile, audio
        self.tab = "perm"
        self.back = pygame.Rect(30, 652, 190, 54)
        self.stall = pygame.Rect(30, 92, 372, 548)
        self.tabs = {"perm": pygame.Rect(426, 96, 250, 52), "items": pygame.Rect(690, 96, 250, 52)}
        self.say_text, self.say_left = random.choice(LINES["welcome"]), 99.0
        self.pulse = 0.0
        self.sparks: list[list] = []   # [x, y, vx, vy, life]
        self.bounce: dict[str, float] = {}

    def _ids(self) -> list[str]:
        return PERM_ORDER if self.tab == "perm" else ITEM_ORDER

    def _card_rect(self, i: int) -> pygame.Rect:
        return pygame.Rect(426 + (i % 4) * (self.CARD_W + 14), 162 + (i // 4) * (self.CARD_H + 12), self.CARD_W, self.CARD_H)

    def say(self, kind: str) -> None:
        self.say_text, self.say_left = random.choice(LINES[kind]), 3.2

    def click(self, pos) -> str | None:
        if self.back.collidepoint(pos):
            return "back"
        for key, rect in self.tabs.items():
            if rect.collidepoint(pos):
                if key != self.tab:
                    self.tab = key
                    _play(self.audio, "click")
                return None
        for i, pid in enumerate(self._ids()):
            rect = self._card_rect(i)
            if rect.collidepoint(pos):
                self._buy(pid, rect)
                return None
        return None

    def _buy(self, pid: str, rect: pygame.Rect) -> None:
        res = self.profile.buy_perm(pid) if self.tab == "perm" else self.profile.buy_item(pid)
        if res == "ok":
            _play(self.audio, "upgrade")
            self.say("bought")
            self.pulse = 1.0
            self.bounce[pid] = 0.25
            for _ in range(14):
                a = random.uniform(0, math.tau)
                v = random.uniform(80, 220)
                self.sparks.append([rect.centerx, rect.centery, math.cos(a) * v, math.sin(a) * v - 60, 0.6])
        else:
            _play(self.audio, "error")
            self.say({"maxed": "maxed", "full": "full"}.get(res, "poor"))

    # ------------------------------------------------------------------ draw
    def draw(self, screen: pygame.Surface, t: float, mouse) -> None:
        dt = 1 / 60
        self.say_left -= dt
        self.pulse = max(0.0, self.pulse - dt * 3)
        self.sparks = [[x + vx * dt, y + vy * dt, vx, vy + 400 * dt, life - dt] for x, y, vx, vy, life in self.sparks if life > dt]
        self.bounce = {k: v - dt for k, v in self.bounce.items() if v > dt}
        if self.say_left <= 0:
            self.say("welcome")
        title.draw_backdrop(screen, t)
        title_text(screen, "SHOP", 44)
        self._draw_stall(screen, t)
        for key, rect in self.tabs.items():
            on = key == self.tab
            label = "PERMANENT" if key == "perm" else "IN-GAME"
            button(screen, rect, COLORS["btn_blue"] if key == "perm" else COLORS["btn_orange"], label, mouse, 26, pressed=on)
            if on:
                pygame.draw.polygon(screen, WHITE, [(rect.centerx - 10, rect.bottom + 6), (rect.centerx + 10, rect.bottom + 6),
                                                    (rect.centerx, rect.bottom + 14)])
        sub = ("Bought once, applies to every run." if self.tab == "perm"
               else "Use them during a run from the POWERS button. They are used up.")
        draw_outlined(screen, sub, (960, 122), 17, DIM, anchor="midleft", width=1)
        for i, pid in enumerate(self._ids()):
            self._card(screen, self._card_rect(i), pid, mouse)
        for x, y, _vx, _vy, life in self.sparks:
            pygame.draw.circle(screen, GOLD, (int(x), int(y)), max(1, int(5 * life / 0.6) + 1))
        coin_pill(screen, self.profile.coins, self.pulse)
        button(screen, self.back, COLORS["btn_orange"], "BACK", mouse, 30)

    def _draw_stall(self, screen: pygame.Surface, t: float) -> None:
        st = self.stall
        shopkeeper.draw_stall(screen, st)
        radius = 108
        img = shopkeeper.ayun_sprite(radius)
        fx, fy = shopkeeper.origin(radius)
        bob = math.sin(t * 2.2) * 3
        feet = (st.centerx + 6, st.y + 480 + bob)
        gfx.blit_shadow(screen, (feet[0], st.y + 484), 170, 34, 110)
        screen.blit(img, (feet[0] - fx, feet[1] - fy))
        shopkeeper.draw_counter(screen, pygame.Rect(st.x - 4, st.y + 452, st.w + 8, 100))
        draw_outlined(screen, SHOPKEEPER, (st.centerx, st.y + 508), 36, GOLD, center=True, width=4)
        bubble = pygame.Rect(st.x + 22, st.y + 70, st.w - 44, 92)   # speech bubble
        pygame.draw.rect(screen, (38, 24, 18), bubble.inflate(6, 6), border_radius=16)
        pygame.draw.rect(screen, (255, 250, 236), bubble, border_radius=14)
        pygame.draw.polygon(screen, (38, 24, 18), [(bubble.centerx - 14, bubble.bottom + 1), (bubble.centerx + 14, bubble.bottom + 1),
                                                   (bubble.centerx + 4, bubble.bottom + 22)])
        pygame.draw.polygon(screen, (255, 250, 236), [(bubble.centerx - 10, bubble.bottom - 2), (bubble.centerx + 10, bubble.bottom - 2),
                                                      (bubble.centerx + 3, bubble.bottom + 16)])
        lines = wrap_text(self.say_text, 20, bubble.w - 28)[:3]
        top = bubble.centery - len(lines) * 12
        for k, line in enumerate(lines):
            draw_outlined(screen, line, (bubble.centerx, top + k * 24 + 12), 20, (60, 40, 30), center=True, width=0, outline=(255, 250, 236))

    def _card(self, screen: pygame.Surface, rect: pygame.Rect, pid: str, mouse) -> None:
        perm = self.tab == "perm"
        d = PERMANENT[pid] if perm else ITEMS[pid]
        hov = rect.collidepoint(mouse)
        lift = -4 if hov else 0
        bump = self.bounce.get(pid, 0.0)
        rect = rect.move(0, lift - int(8 * bump))
        pygame.draw.rect(screen, (20, 14, 10), rect.move(0, 4), border_radius=14)
        pygame.draw.rect(screen, (46, 62, 118) if hov else NAVY, rect, border_radius=14)
        pygame.draw.rect(screen, (240, 200, 110) if hov else (120, 140, 200), rect, 3, border_radius=14)
        ic = shop_icons.icon(d["icon"], 66)
        screen.blit(ic, ic.get_rect(midtop=(rect.centerx, rect.y + 8)))
        y = rect.y + 80
        for line in wrap_text(d["name"], 20, rect.w - 16)[:2]:
            draw_outlined(screen, line, (rect.centerx, y + 10), 20, WHITE, center=True, width=2)
            y += 22
        y += 6
        for line in wrap_text(d["desc"], 14, rect.w - 20)[:3]:
            draw_outlined(screen, line, (rect.centerx, y + 7), 14, (222, 230, 250), center=True, width=1)
            y += 16
        btn = pygame.Rect(rect.x + 10, rect.bottom - 40, rect.w - 20, 32)
        if perm:
            lvl, top = self.profile.level(pid), len(d["costs"])
            for k in range(top):   # level pips
                px = rect.centerx + (k - (top - 1) / 2) * 18
                pygame.draw.circle(screen, (38, 24, 18), (px, rect.bottom - 58), 7)
                pygame.draw.circle(screen, GOLD if k < lvl else (70, 76, 100), (px, rect.bottom - 58), 5)
            cost = self.profile.next_cost(pid)
            now = bonus_text(pid, self.profile.bonus(pid)) if lvl else "none yet"
            draw_outlined(screen, f"Now: {now}", (rect.centerx, rect.bottom - 76), 14, (190, 235, 190), center=True, width=1)
            self._price(screen, btn, cost, "MAX", self.profile.coins, mouse)
        else:
            owned = self.profile.owned(pid)
            draw_outlined(screen, f"Owned: {owned}   (max {d['max_per_run']} per run)", (rect.centerx, rect.bottom - 58), 14,
                          (190, 235, 190) if owned else DIM, center=True, width=1)
            self._price(screen, btn, d["cost"] if owned < MAX_STOCK else None, "FULL", self.profile.coins, mouse)

    @staticmethod
    def _price(screen, btn: pygame.Rect, cost: int | None, done_label: str, coins: int, mouse) -> None:
        if cost is None:
            button(screen, btn, (110, 114, 130), done_label, mouse, 20, enabled=False)
            return
        ok = coins >= cost
        button(screen, btn, COLORS["btn_green"] if ok else (150, 70, 66), "", mouse, 20, enabled=True)
        screen.blit(gfx.icon("coin", 24), (btn.centerx - 44, btn.centery - 12))
        draw_outlined(screen, f"{cost}", (btn.centerx - 14, btn.centery), 22, WHITE if ok else (255, 200, 190), anchor="midleft", width=2)
