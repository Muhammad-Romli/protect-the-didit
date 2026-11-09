"""UI (BTD6-style): floating HUD on top of the map, wooden bottom bar with tower cards,
slide-in upgrade panel. Draws and hit-tests only; Game executes the actions.

hit_test() returns an action tuple:
  ("shop", kind) | ("start_wave",) | ("speed",) | ("pause",) | ("panel",) | ("activity", act_id)
  | ("upgrade", path) | ("sell",) | ("noop",)
or None when the click is not on any UI.

Layout (1280x720):  top-left lives + money, top-centre phase banner, top-right round + pause,
bottom bar: [UPGRADES + progress slot] [tower cards] [speed + start-wave buttons].
The upgrade panel opens on the side of the screen away from the selected tower.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

from data.activities import ACTIVITIES, STACKS, activities_for
from data.settings import (BAR_RECT, COLORS, INCOME_INTERVAL_SECONDS, MAX_ACTIVITIES, MAX_TIER, PREP_GRACE_SECONDS,
                           PREP_MAX_SECONDS, TOWER_RADIUS)
from data.shop import ITEM_ORDER, ITEMS
from data.touch import TOUCH_GEAR, TOUCH_SLOP
from data.towers import DEFAULT_STATS, TOWER_ORDER, TOWERS
from data.waves import SPECIAL_WAVES, WAVES
from game import gfx, options as opts_mod, powers, shop_icons, sprites_proc
from data.settings import DIDITCODE_MAX_PER_PREP
from game.actives import ACTIVES, actives_of, phase_ok as actives_phase_ok
from game.bima_ui import GraphConsole
from game.utils import draw_outlined, draw_outlined_digits, outlined_text, wrap_text

if TYPE_CHECKING:
    from game.game import Game

KNOWLEDGE_COLOR = (130, 215, 255)
GAIN_COLOR = (140, 255, 150)
SPEND_COLOR = (255, 130, 120)
GOLD = COLORS["gold"]
POPUP_SECONDS = 1.1
POPUP_MERGE_SECONDS = 0.3   # gains inside this window become one "+$N"
COUNT_UP_SPEED = 9.0        # how fast the shown total catches up with the real one
PANEL_W = 300
CARD_W, CARD_H = 94, 78
CARD_UP_H = 132             # upgrade card height in the tower panel
SLIDE_SPEED = 7.0           # panel slide-in, 1/seconds


class UI:
    def __init__(self) -> None:
        self.bar = pygame.Rect(*BAR_RECT)
        self.upgrades_btn = pygame.Rect(18, 640, 214, 44)
        self.slot = pygame.Rect(18, 690, 214, 22)
        n = len(TOWER_ORDER)
        cw, gap = (CARD_W, 14) if n <= 4 else (78, 9)   # 5+ towers: narrower cards so the bar clears the abilities and POWERS
        x0 = 640 - (n * cw + (n - 1) * gap) // 2 if n <= 4 else 432
        self.shop_btns = {k: pygame.Rect(x0 + i * (cw + gap), 641, cw, CARD_H)
                          for i, k in enumerate(TOWER_ORDER)}
        self.powers_btn = pygame.Rect(866, 644, 166, 66)   # opens the in-game shop items (POWERS) list
        self.power_rows: list[tuple[str, pygame.Rect]] = []
        self.powers_panel = pygame.Rect(700, 272, 332, 356)
        self.speed_btn = pygame.Rect(1048, 644, 84, 66)
        self.start_btn = pygame.Rect(1142, 644, 126, 66)
        self.gear_btn = pygame.Rect(1214, 10, 58, 58)
        # upgrade panel (geometry is rebuilt by layout() for the selected tower)
        self.graph = GraphConsole()
        self.touch = False           # phone layout (bigger gear button, finger-sized hit areas); see set_touch()
        self.ability_rects: list[tuple[str, pygame.Rect]] = []
        self.panel = pygame.Rect(0, 0, 0, 0)
        self.upgrade_btns = [pygame.Rect(0, 0, 0, 0), pygame.Rect(0, 0, 0, 0)]
        self.sell_btn = pygame.Rect(0, 0, 0, 0)
        self._act_rects: list[tuple[str, pygame.Rect]] = []
        self.target_rects = (pygame.Rect(0, 0, 0, 0), pygame.Rect(0, 0, 0, 0))  # prev / next priority
        self.opt_panel = pygame.Rect(380, 70, 520, 556)
        self.opt_rows: list[tuple[str, pygame.Rect]] = []
        self.panel_open = False      # target of the slide animation (tower selected and not collapsed)
        self.collapsed = False       # the UPGRADES button hides the panel
        self.slide = 0.0             # 0 = off-screen, 1 = fully in
        self.panel_side = "right"
        self._last_selected = None
        # money display: counts up/down to the real total, with +$N / -$N popups beside it
        self.shown_money: float | None = None
        self.pulse = 0.0
        self.popups: list[list] = []  # [text, color, age]
        self._pending = {"gain": 0.0, "spend": 0.0}
        self._pending_timer = {"gain": 0.0, "spend": 0.0}

    def set_touch(self, on: bool) -> None:
        """Switch between the mouse layout and the finger layout (called by game/touch.py)."""
        self.touch = on
        self.gear_btn = pygame.Rect(*(TOUCH_GEAR if on else (1214, 10, 58, 58)))
        self.graph.set_touch(on)

    def _hit(self, rect: pygame.Rect, pos, slop: int = TOUCH_SLOP) -> bool:
        """collidepoint, with an invisible extra margin around small buttons when a finger is used."""
        return (rect.inflate(2 * slop, 2 * slop) if self.touch else rect).collidepoint(pos)

    # ------------------------------------------------------------- money fx
    def money_change(self, amount: float) -> None:
        """Called by Game for every earning (+) or spending (-)."""
        kind = "gain" if amount > 0 else "spend"
        if self._pending[kind] == 0:
            self._pending_timer[kind] = POPUP_MERGE_SECONDS
        self._pending[kind] += abs(amount)

    def update(self, dt: float, money: float, game: "Game | None" = None) -> None:
        if self.shown_money is None:
            self.shown_money = money
        diff = money - self.shown_money
        self.shown_money = money if abs(diff) < 0.6 else self.shown_money + diff * min(1.0, dt * COUNT_UP_SPEED)
        self.pulse = max(0.0, self.pulse - dt * 3)
        for kind in ("gain", "spend"):
            if self._pending[kind] > 0:
                self._pending_timer[kind] -= dt
                if self._pending_timer[kind] <= 0:
                    value = round(self._pending[kind])
                    if value > 0:
                        sign, color = ("+", GAIN_COLOR) if kind == "gain" else ("-", SPEND_COLOR)
                        self.popups.append([f"{sign}${value}", color, 0.0])
                        if kind == "gain":
                            self.pulse = 1.0
                    self._pending[kind] = 0.0
        for p in self.popups:
            p[2] += dt
        self.popups = [p for p in self.popups if p[2] < POPUP_SECONDS]
        if game is not None:
            self.layout(game)
            step = SLIDE_SPEED * dt
            self.slide = min(1.0, self.slide + step) if self.panel_open else max(0.0, self.slide - step)
            self.layout(game)

    # --------------------------------------------------------------- layout
    def layout(self, game: "Game") -> None:
        """Rebuild the panel rectangles for the selected tower (every frame and before hit tests)."""
        t = game.selected
        pp = self.powers_panel
        self.power_rows = [(pid, pygame.Rect(pp.x + 14, pp.y + 52 + i * 50, pp.w - 28, 46)) for i, pid in enumerate(ITEM_ORDER)]
        self.ability_rects = [] if t is None else [(a, pygame.Rect(244 + i * 60, 642, 56, 68)) for i, a in enumerate(actives_of(t)[:3])]
        if t is not self._last_selected:
            self.graph.focused = False
            self.graph.pattern_open = False
            self._last_selected = t
            self.collapsed = False
            if t is not None:
                self.panel_side = "left" if t.pos.x > 640 else "right"
                if self.slide > 0.5:
                    self.slide = 0.35  # switching towers: quick re-slide
        self.panel_open = t is not None and not self.collapsed
        if t is None:
            return
        acts = activities_for(t.kind)
        h = 18 + 52 + 6 + 36 + 4 + 34 + 8 + (54 if acts else 0) + 2 * CARD_UP_H + 8 + 10 + 38 + 18
        ease = 1 - (1 - self.slide) ** 3
        home = 14 if self.panel_side == "left" else 1280 - PANEL_W - 14
        off = -(PANEL_W + 40) if self.panel_side == "left" else (PANEL_W + 40)
        self.panel = pygame.Rect(round(home + off * (1 - ease)), 76, PANEL_W, h)
        x, w = self.panel.x + 20, PANEL_W - 40
        ty = self.panel.y + 18 + 52 + 6 + 36 + 4
        self.target_rects = (pygame.Rect(x, ty, 34, 30), pygame.Rect(x + w - 34, ty, 34, 30))
        y = ty + 34 + 8
        self._act_rects = []
        if acts:
            gap = 6
            aw = (w - gap * (len(acts) - 1)) // len(acts)
            self._act_rects = [(a, pygame.Rect(x + i * (aw + gap), y, aw, 46)) for i, (a, _) in enumerate(acts)]
            y += 54
        self.upgrade_btns = [pygame.Rect(x, y, w, CARD_UP_H), pygame.Rect(x, y + CARD_UP_H + 8, w, CARD_UP_H)]
        self.sell_btn = pygame.Rect(x, y + 2 * CARD_UP_H + 18, w, 38)

    def _build_options_layout(self) -> None:
        p = self.opt_panel
        self.opt_rows = []
        y = p.y + 76
        for key, *_ in opts_mod.ROWS:
            self.opt_rows.append((key, pygame.Rect(p.x + 24, y, p.w - 48, 34)))
            y += 38
        y += 6
        bw = (p.w - 48 - 30) // 4
        for i, key in enumerate(("fullscreen", "restart", "menu", "resume")):
            self.opt_rows.append((key, pygame.Rect(p.x + 24 + i * (bw + 10), y, bw, 44)))

    def activity_rects(self, tower_kind: str) -> list[tuple[str, pygame.Rect]]:
        """One button per activity the selected tower can run (valid after layout())."""
        return self._act_rects

    # ------------------------------------------------------------- hit test
    def hit_test(self, pos, game: "Game"):
        self.layout(game)
        if self.gear_btn.collidepoint(pos):
            return ("options",)
        if game.options_open:
            self._build_options_layout()
            for key, rect in self.opt_rows:
                if rect.collidepoint(pos):
                    if key in ("fullscreen", "restart", "menu", "resume"):
                        return ("opt", key, 0)
                    return ("opt", key, -1 if pos[0] < rect.centerx - 10 and key != "auto_start" else 1)
            return ("noop",)
        g = self.graph.hit_test(pos, game)
        if g is not None:
            return g
        if not self.graph.visible(game):
            if game.powers_open:
                for pid, rect in self.power_rows:
                    if rect.collidepoint(pos):
                        return ("power", pid)
            if self.powers_btn.collidepoint(pos):
                return ("powers",)
            if game.powers_open and self.powers_panel.collidepoint(pos):
                return ("noop",)
        for i, (aid, rect) in enumerate(self.ability_rects):
            if rect.collidepoint(pos):
                return ("ability", i)
        for kind, rect in (() if self.graph.visible(game) else self.shop_btns.items()):
            if rect.collidepoint(pos):
                return ("shop", kind)
        if self.start_btn.collidepoint(pos):
            return ("start_wave",)
        if self.speed_btn.collidepoint(pos):
            return ("speed",)
        if self.upgrades_btn.collidepoint(pos):
            return ("panel",)
        if game.selected is not None and (self.panel_open or self.slide > 0.02):
            for i, rect in enumerate(self.target_rects):
                if self._hit(rect, pos):
                    return ("target", -1 if i == 0 else 1)
            for act_id, rect in self._act_rects:
                if self._hit(rect, pos, 5):
                    return ("activity", act_id)
            for i, rect in enumerate(self.upgrade_btns):
                if rect.collidepoint(pos):
                    return ("upgrade", i)
            if self._hit(self.sell_btn, pos):
                return ("sell",)
            if self.panel.collidepoint(pos):
                return ("noop",)
        if self.bar.collidepoint(pos):
            return ("noop",)
        return None

    # ----------------------------------------------------------------- draw
    def draw(self, surface: pygame.Surface, game: "Game") -> None:
        self.layout(game)
        self._draw_hud(surface, game)
        self._draw_banner(surface, game)
        self._draw_boss_bars(surface, game)
        if game.selected is not None and self.slide > 0.01:
            self._draw_tower_panel(surface, game)
        self._draw_bar(surface, game)
        self._draw_toast(surface, game)
        if game.powers_open and not self.graph.visible(game):
            self._draw_powers(surface, game)
        self._draw_tooltip(surface, game)
        if game.options_open:
            self._draw_options(surface, game)

    def _btn(self, surface, rect, base, game, enabled=True, radius=12, border=(255, 255, 255), pressed=False):
        hover = enabled and rect.collidepoint(game.mouse_pos)
        state = "off" if not enabled else "pressed" if pressed else "hover" if hover else "normal"
        surface.blit(gfx.glossy(rect.w, rect.h, base, radius, border, state), (rect.x - 1, rect.y - 1))
        return hover

    @staticmethod
    def _portrait(kind: str, color) -> pygame.Surface:
        key = ("portrait", kind)
        if key not in gfx._CACHE:
            spr = sprites_proc.tower_sprite(kind, TOWER_RADIUS, color)
            gfx._CACHE[key] = pygame.transform.smoothscale(spr, (round(spr.get_width() * 50 / spr.get_height()), 50))
        return gfx._CACHE[key]

    # --------------------------------------------------------------- top HUD
    def _draw_hud(self, surface, game: "Game") -> None:
        surface.blit(gfx.icon("heart", 46), (10, 8))  # lives
        low = game.stash_hp <= 30
        draw_outlined(surface, str(game.stash_hp), (62, 30), 38, COLORS["bad"] if low else (255, 255, 255),
                      anchor="midleft", width=3)
        surface.blit(gfx.icon("coin", 46), (172, 8))  # money (+ popups)
        shown = int(self.shown_money if self.shown_money is not None else game.money)
        size = 38 + int(7 * self.pulse)
        r = draw_outlined_digits(surface, f"${shown}", (226, 30), size, GOLD if self.pulse < 0.01 else (255, 255, 255),
                                width=3)
        for text, col, age in self.popups:
            f = age / POPUP_SECONDS
            img = outlined_text(text, 28 + int(6 * max(0.0, 1 - f * 5)), col, COLORS["ink"], 2).copy()
            if f > 0.6:
                img.set_alpha(int(255 * (1 - f) / 0.4))
            surface.blit(img, (r.right + 10, 14 - int(10 * f)))
        surface.blit(gfx.icon("brain", 28), (14, 58))  # ball knowledge + activity slots
        draw_outlined(surface, str(game.ball_knowledge), (48, 72), 24, KNOWLEDGE_COLOR, anchor="midleft")
        used = game.activity_slots_used()
        draw_outlined(surface, f"Activities {used}/{MAX_ACTIVITIES}", (112, 72), 20,
                      GOLD if used else COLORS["text_dim"], anchor="midleft")
        total = game.waves.total  # round + pause (top-right)
        n = min(total, game.waves.number if game.waves.active else game.waves.number + 1)
        rx = self.gear_btn.x - 10
        draw_outlined(surface, "ROUND", (rx, 8), 20, (255, 255, 255), anchor="topright")
        draw_outlined(surface, f"{n}/{total}", (rx, 24), 40, (255, 255, 255), anchor="topright", width=3)
        self._btn(surface, self.gear_btn, COLORS["btn_blue"], game, pressed=game.options_open)
        gi = gfx.icon("gear", 38)
        surface.blit(gi, gi.get_rect(center=(self.gear_btn.centerx, self.gear_btn.centery - 1)))

    def _draw_banner(self, surface, game: "Game") -> None:
        """Top-centre: phase, timer and how strong the wave is."""
        hp_mult, speed_mult = game.enemy_multipliers()
        w, h = 330, 58
        rect = pygame.Rect(640 - w // 2, 8, w, h)
        surface.blit(gfx.pill(w, h), rect)
        strength = f"x{hp_mult:.1f} HP  +{round((speed_mult - 1) * 100)}% speed"
        if game.phase.value == "battle":
            left = len(game.enemies) + len(game.waves._queue)
            special = SPECIAL_WAVES.get(game.waves.number)
            head = f"WAVE {game.waves.number}  {special}  -  {left} left" if special else f"WAVE {game.waves.number}  -  {left} left"
            draw_outlined(surface, head, (rect.centerx, rect.y + 17), 24 if special else 26,
                          (120, 220, 255) if special else COLORS["bad"], center=True)
            draw_outlined(surface, f"Wait penalty: {strength}", (rect.centerx, rect.y + 42), 17,
                          COLORS["text_dim"], center=True, width=1)
        else:
            t = int(game.prep_time)
            mx = PREP_MAX_SECONDS
            nxt = SPECIAL_WAVES.get(game.waves.number + 1)
            title = f"PREP  {t // 60}:{t % 60:02d} / {mx // 60}:{mx % 60:02d}" + (f"  -  next: {nxt}!" if nxt else "")
            draw_outlined(surface, title, (rect.centerx, rect.y + 17), 24 if not nxt else 21, GOLD, center=True)
            draw_outlined(surface, f"Next wave: {strength}", (rect.centerx, rect.y + 42), 17,
                          COLORS["bad"] if game.prep_ramp() > 0 else COLORS["text_dim"], center=True, width=1)

    def _draw_boss_bars(self, surface, game: "Game") -> None:
        """Top-centre boss bars: name plate, segmented health bar with a damage 'ghost', percentage."""
        y = 78
        for boss in sorted([e for e in game.enemies if e.is_boss], key=lambda e: -e.max_hp)[:2]:
            bar = pygame.Rect(640 - 230, y + 20, 460, 18)
            gfx.hp_bar(surface, bar, boss.hp / boss.max_hp, boss.hp_ghost / boss.max_hp)
            plate = pygame.Rect(0, 0, 250, 26)
            plate.midbottom = (bar.centerx, bar.y + 2)
            pygame.draw.rect(surface, (20, 12, 28), plate, border_radius=13)
            pygame.draw.rect(surface, (255, 120, 100), plate, 2, border_radius=13)
            draw_outlined(surface, boss.name.upper(), plate.center, 18, (255, 235, 220), center=True, width=2)
            draw_outlined(surface, f"{max(0, round(100 * boss.hp / boss.max_hp))}%", (bar.right + 10, bar.centery), 18,
                          (255, 255, 255), anchor="midleft", width=2)
            for sx in (bar.x - 8, bar.right + 8 - 0):
                pygame.draw.circle(surface, (255, 120, 100), (sx, bar.centery), 5)
            y += 52

    # ------------------------------------------------------------ bottom bar
    def _draw_bar(self, surface, game: "Game") -> None:
        surface.blit(gfx.wood(self.bar.w, self.bar.h), self.bar.topleft)
        pygame.draw.line(surface, (255, 222, 160), (0, self.bar.y + 3), (self.bar.w, self.bar.y + 3), 1)
        sel = game.selected is not None  # UPGRADES button: shows / hides the panel
        shown = sel and self.panel_open
        self._btn(surface, self.upgrades_btn, COLORS["btn_green"], game, enabled=sel, pressed=shown)
        col = (255, 255, 255) if sel else (205, 208, 218)
        draw_outlined(surface, "UPGRADES", (self.upgrades_btn.centerx + 12, self.upgrades_btn.centery - 1), 27, col, center=True)
        cx, cy = self.upgrades_btn.x + 30, self.upgrades_btn.centery
        d = 1 if shown else -1  # arrow points down while the panel is open
        pygame.draw.polygon(surface, col, [(cx - 9, cy - 4 * d), (cx + 9, cy - 4 * d), (cx, cy + 5 * d)])
        self._draw_slot(surface, game)
        if self.graph.visible(game):
            self.graph.draw(surface, game)
        else:
            for i, (kind, rect) in enumerate(self.shop_btns.items()):
                self._draw_card(surface, game, kind, rect, i + 1)
        self._draw_abilities(surface, game)
        if not self.graph.visible(game):
            self._draw_powers_button(surface, game)
        fast = game.speed > 1  # orange: speed (x1/x2/x3), green: start / skip the preparation
        self._btn(surface, self.speed_btn, COLORS["btn_orange"], game, pressed=fast)
        surface.blit(gfx.icon("ff", 34), (self.speed_btn.x + 25, self.speed_btn.y + 5))
        draw_outlined(surface, f"x{game.speed}", (self.speed_btn.centerx, self.speed_btn.bottom - 15), 22, center=True)
        can = game.waves.can_start and not game.waves.active
        self._btn(surface, self.start_btn, COLORS["btn_green"], game, enabled=can)
        surface.blit(gfx.icon("play", 40), (self.start_btn.x + 8, self.start_btn.y + 12))
        if game.waves.active:
            label, sub = "RUNNING", None
        elif can:
            label, sub = "START", f"skip prep"
        else:
            label, sub = "DONE", None
        cx = self.start_btn.x + 82
        draw_outlined(surface, label, (cx, self.start_btn.centery - (8 if sub else 0)), 23,
                      (255, 255, 255) if can else (205, 208, 218), center=True)
        if sub:
            draw_outlined(surface, sub, (cx, self.start_btn.centery + 14), 17, (255, 255, 255), center=True, width=1)

    def _draw_powers_button(self, surface, game: "Game") -> None:
        r = self.powers_btn
        total = sum(game.profile.owned(i) for i in ITEM_ORDER)
        self._btn(surface, r, (150, 90, 210), game, pressed=game.powers_open)
        draw_outlined(surface, "POWERS", (r.centerx, r.centery - 8), 26, center=True)
        draw_outlined(surface, f"{total} owned", (r.centerx, r.centery + 17), 17, (235, 220, 255) if total else (190, 180, 210),
                      center=True, width=1)

    def _draw_powers(self, surface, game: "Game") -> None:
        """List of the in-game shop items: icon, name, how many you own / how many uses are left this run."""
        p = self.powers_panel
        surface.blit(gfx.panel_surface(p.w, p.h), (p.x - 2, p.y - 2))
        draw_outlined(surface, "POWERS", (p.centerx, p.y + 26), 32, (255, 255, 255), center=True, width=3)
        for pid, rect in self.power_rows:
            ok, _why = powers.status(game, pid)
            owned = game.profile.owned(pid)
            self._btn(surface, rect, (96, 120, 190) if ok else (70, 74, 90), game, enabled=ok, radius=10)
            icon = shop_icons.icon(ITEMS[pid]["icon"], 38)
            surface.blit(icon, icon.get_rect(midleft=(rect.x + 8, rect.centery)))
            draw_outlined(surface, ITEMS[pid]["name"], (rect.x + 54, rect.centery - 8), 19,
                          (255, 255, 255) if ok else (200, 204, 216), anchor="midleft", width=2)
            sub = f"{powers.left_this_run(game, pid)} uses left this run"
            draw_outlined(surface, sub, (rect.x + 54, rect.centery + 11), 14, (225, 230, 245), anchor="midleft", width=1)
            draw_outlined(surface, f"x{owned}", (rect.right - 12, rect.centery), 26, GOLD if owned else COLORS["bad"],
                          anchor="midright", width=2)
        draw_outlined(surface, "Buy more in the main-menu SHOP", (p.centerx, p.bottom - 14), 14, COLORS["text_dim"],
                      center=True, width=1)

    def _draw_abilities(self, surface, game: "Game") -> None:
        t = game.selected
        for i, (aid, rect) in enumerate(self.ability_rects):
            cfg = ACTIVES[aid]
            cd = t.active_cd.get(aid, 0.0)
            live = actives_phase_ok(game, aid) and cd <= 0 and not (aid == "diditcode" and game.code_uses >= DIDITCODE_MAX_PER_PREP)
            self._btn(surface, rect, cfg["color"], game, live, 10, pressed=game.aiming is not None and game.aiming[1] == aid)
            icon = cfg["icon"]
            if icon in ("cube", "pyramid", "sphere"):
                img = sprites_proc.shape_sprite(("cube", "pyramid", "sphere").index(icon) if icon != "cube" else 0, True, 34)
                if icon == "pyramid":
                    img = sprites_proc.shape_sprite(1, True, 34)
                elif icon == "sphere":
                    img = sprites_proc.shape_sprite(2, True, 34)
            else:
                img = gfx.icon(icon, 30)
            surface.blit(img, img.get_rect(center=(rect.centerx, rect.y + 24)))
            draw_outlined(surface, cfg["name"], (rect.centerx, rect.bottom - 14), 13, (255, 255, 255), center=True, width=1)
            if cd > 0:
                h = int(rect.h * cd / cfg["cooldown"])
                shade_ = pygame.Surface((rect.w - 4, h), pygame.SRCALPHA)
                shade_.fill((10, 8, 20, 150))
                surface.blit(shade_, (rect.x + 2, rect.y + 2))
                draw_outlined(surface, f"{cd:.0f}", (rect.centerx, rect.y + 24), 24, center=True, width=2)
            pygame.draw.circle(surface, (28, 18, 12), (rect.x + 9, rect.y + 9), 9)
            draw_outlined(surface, "ECV"[i], (rect.x + 9, rect.y + 9), 14, (255, 255, 255), center=True, width=1)
            if rect.collidepoint(game.mouse_pos):  # tooltip
                tip = outlined_text(cfg["desc"], 17, (255, 255, 255), COLORS["ink"], 2)
                box = tip.get_rect(midbottom=(min(1100, max(tip.get_width() // 2 + 10, rect.centerx)), self.bar.y - 52)).inflate(24, 12)
                surface.blit(gfx.pill(box.w, box.h, alpha=200), box)
                surface.blit(tip, tip.get_rect(center=box.center))

    def _draw_slot(self, surface, game: "Game") -> None:
        """Recessed wooden slot: escalation timer in preparation, spawn progress in battle."""
        r = self.slot
        pygame.draw.rect(surface, (52, 32, 18), r.inflate(4, 4), border_radius=9)
        pygame.draw.rect(surface, (34, 20, 12), r, border_radius=8)
        grace_x = None
        if game.phase.value == "preparation":
            frac = min(1.0, game.prep_time / PREP_MAX_SECONDS)
            ramp = game.prep_ramp()
            color = (int(110 + 125 * ramp), int(220 - 130 * ramp), 80)
            label = "Prepare" if ramp <= 0 else "Enemies growing!"
            grace_x = r.x + int(r.w * PREP_GRACE_SECONDS / PREP_MAX_SECONDS)
        else:
            total = max(1, sum(g[1] for g in WAVES[game.waves.number - 1]))
            frac = 1.0 - len(game.waves._queue) / total
            color, label = (240, 150, 60), "Spawning"
        if frac > 0:
            fill = pygame.Rect(r.x + 2, r.y + 2, max(10, int((r.w - 4) * frac)), r.h - 4)
            pygame.draw.rect(surface, color, fill, border_radius=6)
            pygame.draw.rect(surface, gfx.tint(color, 0.5), (fill.x + 3, fill.y + 2, max(0, fill.w - 6), 4), border_radius=3)
        if grace_x is not None:
            pygame.draw.line(surface, (255, 255, 255), (grace_x, r.y + 1), (grace_x, r.bottom - 2), 2)
        draw_outlined(surface, label, r.center, 16, center=True, width=1)

    def _draw_card(self, surface, game: "Game", kind: str, rect: pygame.Rect, number: int) -> None:
        d = TOWERS[kind]
        affordable = game.money >= d["cost"]
        placing = game.placing == kind
        hover = rect.collidepoint(game.mouse_pos)
        state = "off" if not affordable else "pressed" if placing else "hover" if hover else "normal"
        lift = 3 if hover and affordable and not placing else 0
        surface.blit(gfx.glossy(rect.w, rect.h, (70, 150, 232), 12, (255, 255, 255), state), (rect.x - 1, rect.y - 1 - lift))
        port = self._portrait(kind, d["color"])
        if not affordable:
            port = port.copy()
            port.fill((130, 130, 130, 255), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(port, port.get_rect(midtop=(rect.centerx, rect.y + 6 - lift)))
        plate = pygame.Rect(0, 0, rect.w - 14, 20)  # price plate
        plate.midbottom = (rect.centerx, rect.bottom - 6 - lift)
        pygame.draw.rect(surface, (28, 18, 12), plate, border_radius=10)
        draw_outlined(surface, f"${d['cost']}", plate.center, 19, GOLD if affordable else COLORS["bad"],
                      center=True, width=1)
        pygame.draw.circle(surface, (28, 18, 12), (rect.x + 14, rect.y + 14 - lift), 10)  # hotkey badge
        draw_outlined(surface, str(number), (rect.x + 14, rect.y + 14 - lift), 17, (255, 255, 255), center=True, width=1)
        if placing:
            pulse = 3 + 2 * math.sin(pygame.time.get_ticks() / 140)
            pygame.draw.rect(surface, GOLD, rect.inflate(pulse, pulse), 3, border_radius=14)

    def _draw_toast(self, surface, game: "Game") -> None:
        text, dim = game.message, False
        if not text and self.touch and (game.placing or game.aiming):
            text = game.touch.hint()
        if not text and game.placing:
            d = TOWERS[game.placing]
            text = f"Placing {d['name']} (${d['cost']}) - click the map, right-click to cancel"
        if not text and game.selected is None and self.touch:
            text, dim = "Tap a card, then the map, to build.  Tap a tower to upgrade it.", True
        if not text and game.selected is None:
            text, dim = "1-3 place   Space start   P pause   F speed   Q/W upgrade   X sell   M mute   F11 fullscreen", True
        if not text:
            return
        img = outlined_text(text, 20 if dim else 24, COLORS["text_dim"] if dim else GOLD, COLORS["ink"], 2)
        plate = img.get_rect(midbottom=(640, self.bar.y - 8)).inflate(30, 10)
        surface.blit(gfx.pill(plate.w, plate.h, alpha=110 if dim else 190), plate)
        surface.blit(img, img.get_rect(center=plate.center))

    def _draw_tooltip(self, surface, game: "Game") -> None:
        if game.placing is not None:
            return
        for kind, rect in self.shop_btns.items():
            if rect.collidepoint(game.mouse_pos):
                d = TOWERS[kind]
                w = 300
                body = wrap_text(self._base_stats(d["stats"]), 18, w - 28)
                tip = pygame.Rect(0, 0, w, 56 + 20 * len(body))
                tip.midbottom = (min(1280 - w // 2 - 8, max(w // 2 + 8, rect.centerx)), self.bar.y - 52)
                surface.blit(gfx.panel_surface(w, tip.h, 12), (tip.x - 2, tip.y - 2))
                draw_outlined(surface, d["name"], (tip.x + 16, tip.y + 14), 24, GOLD)
                for i, line in enumerate(body):
                    draw_outlined(surface, line, (tip.x + 16, tip.y + 44 + i * 20), 18, (255, 255, 255), width=1)
                return

    @staticmethod
    def _base_stats(stats: dict) -> str:
        s = {**DEFAULT_STATS, **stats}
        parts = [f"Dmg {s['damage']:g}", f"CD {s['cooldown']:.1f}s", f"Range {s['range']:g}"]
        if s["aoe_radius"]:
            parts.append(f"AoE {s['aoe_radius']:g}")
        if s["slow"]:
            parts.append(f"Slow {round(s['slow'] * 100)}%")
        if s["income_per_wave"]:
            parts.append(f"+${s['income_per_wave']:g}/wave")
        return "  ".join(parts)

    # ----------------------------------------------------------- tower panel
    @staticmethod
    def _stats_text(t) -> str:
        s = t.stats
        parts = [f"Dmg {s['damage']:g}", f"CD {s['cooldown']:.2f}s", f"Range {s['range']:g}"]
        if s["aoe_radius"] > 0:
            parts.append(f"AoE {s['aoe_radius']:g}")
        if s["slow"] > 0:
            parts.append(f"Slow {round(s['slow'] * 100)}% / {s['slow_duration']:.1f}s")
        if s["income_per_wave"]:
            parts.append(f"+${s['income_per_wave']:g}/wave")
        if s["income_per_sec"]:
            parts.append(f"+${round(s['income_per_sec'] * INCOME_INTERVAL_SECONDS)}/{INCOME_INTERVAL_SECONDS}s")
        if s["money_per_hit"]:
            parts.append(f"+${s['money_per_hit']:g}/hit")
        return "  ".join(parts)

    def _draw_tower_panel(self, surface, game: "Game") -> None:
        t = game.selected
        p = self.panel
        surface.blit(gfx.panel_surface(p.w, p.h), (p.x - 2, p.y - 2))
        x = p.x + 20
        surface.blit(self._portrait(t.kind, t.color), (x - 4, p.y + 18))
        draw_outlined(surface, t.name, (x + 50, p.y + 22), 32, (255, 255, 255), width=3)
        draw_outlined(surface, f"Path A tier {t.tiers[0]}   Path B tier {t.tiers[1]}", (x + 50, p.y + 54), 16,
                      COLORS["text_dim"], width=1)
        for i, line in enumerate(wrap_text(self._stats_text(t), 16, PANEL_W - 40)[:2]):
            draw_outlined(surface, line, (x, p.y + 18 + 52 + 6 + i * 17), 16, (225, 235, 255), width=1)
        self._draw_target_row(surface, game)
        self._draw_activity_buttons(surface, game)
        for i, rect in enumerate(self.upgrade_btns):
            self._draw_upgrade_card(surface, game, i, rect)
        confirming = game.sell_pending is t and game.sell_timer > 0
        self._btn(surface, self.sell_btn, COLORS["btn_red"], game, pressed=confirming)
        draw_outlined(surface, f"SURE?  +${t.sell_value}" if confirming else f"SELL  +${t.sell_value}",
                      self.sell_btn.center, 24, center=True)

    def _draw_target_row(self, surface, game: "Game") -> None:
        t = game.selected
        for i, rect in enumerate(self.target_rects):
            self._btn(surface, rect, COLORS["btn_blue"], game, True, 8)
            cx, cy, d = rect.centerx, rect.centery, (1 if i == 0 else -1)
            pygame.draw.polygon(surface, (255, 255, 255), [(cx + 5 * d, cy - 7), (cx + 5 * d, cy + 7), (cx - 5 * d, cy)])
        mid = pygame.Rect(self.target_rects[0].right + 6, self.target_rects[0].y, self.target_rects[1].x - self.target_rects[0].right - 12, 30)
        pygame.draw.rect(surface, (18, 26, 56), mid, border_radius=8)
        draw_outlined(surface, f"Target: {opts_mod.TARGET_LABELS[t.targeting]}  [T]", mid.center, 19, GOLD, center=True, width=1)

    def _draw_options(self, surface, game: "Game") -> None:
        dim = pygame.Surface((1280, 720), pygame.SRCALPHA)
        dim.fill((8, 6, 18, 170))
        surface.blit(dim, (0, 0))
        p = self.opt_panel
        self._build_options_layout()
        surface.blit(gfx.panel_surface(p.w, p.h), (p.x - 2, p.y - 2))
        draw_outlined(surface, "OPTIONS", (p.centerx, p.y + 40), 44, (255, 255, 255), center=True, width=3)
        for key, rect in self.opt_rows:
            if key in ("fullscreen", "restart", "menu", "resume"):
                base = {"fullscreen": COLORS["btn_blue"], "restart": COLORS["btn_red"], "menu": COLORS["btn_orange"],
                        "resume": COLORS["btn_green"]}[key]
                self._btn(surface, rect, base, game, True, 10)
                draw_outlined(surface, key.upper(), rect.center, 20, center=True)
                continue
            label = next(r[1] for r in opts_mod.ROWS if r[0] == key)
            val = game.options[key]
            surface.blit(gfx.pill(rect.w, rect.h, (14, 22, 52), 150), rect)
            draw_outlined(surface, label, (rect.x + 12, rect.centery), 21, (255, 255, 255), anchor="midleft", width=2)
            vb = pygame.Rect(0, 0, 150, 28)
            vb.midright = (rect.right - 6, rect.centery)
            on = val is True
            self._btn(surface, vb, COLORS["btn_green"] if on else (70, 120, 200) if not isinstance(val, bool) else (110, 114, 130), game, True, 8)
            draw_outlined(surface, opts_mod.value_text(key, val), vb.center, 19, center=True, width=1)
            if not isinstance(val, bool):
                for d, px in ((-1, vb.x + 10), (1, vb.right - 10)):
                    pygame.draw.polygon(surface, (255, 255, 255), [(px + 4 * d, vb.centery - 6), (px + 4 * d, vb.centery + 6), (px - 4 * d, vb.centery)])
        draw_outlined(surface, "Esc / O closes   -   changes save automatically", (p.centerx, p.bottom - 14), 15, COLORS["text_dim"], center=True, width=1)

    def _draw_activity_buttons(self, surface, game: "Game") -> None:
        t = game.selected
        prep = game.phase.value == "preparation"
        for act_id, rect in self._act_rects:
            data = ACTIVITIES[act_id]
            running = t.activity == act_id
            kind, arg = data["gives"]
            lock = t.activity_lock(data)
            maxed = kind == "stack" and t.stacks.get(arg, 0) >= STACKS[arg]["max"]
            used = game.activity_slots_used()
            if t.activity and ACTIVITIES[t.activity]["counts_toward_limit"]:
                used -= 1
            slot_free = (not data["counts_toward_limit"]) or used < MAX_ACTIVITIES
            usable = running or (not lock and prep and slot_free and not maxed)
            self._btn(surface, rect, COLORS["btn_orange"] if running else (70, 150, 232), game, usable, 10, pressed=running)
            draw_outlined(surface, f"{'Stop' if running else 'Start'} {data['name']}", (rect.centerx, rect.y + 14), 19,
                          (255, 255, 255) if usable else (205, 208, 218), center=True, width=1)
            if kind == "stack":
                info = f"{STACKS[arg]['label']} {t.stacks.get(arg, 0)}/{STACKS[arg]['max']}"
                color = STACKS[arg]["color"]
            else:
                info, color = f"+{arg} knowledge / {data['interval']:g}s", KNOWLEDGE_COLOR
            if not running and not usable:
                color = (205, 208, 218)
                info = (f"Needs {lock}" if lock else "Maxed" if maxed else
                        "Preparation only" if not prep else "No free slot")
            draw_outlined(surface, info, (rect.centerx, rect.y + 32), 15, color, center=True, width=1)
            if running:
                frac = min(1.0, t.activity_acc / data["interval"])
                pygame.draw.rect(surface, (60, 30, 10), (rect.x + 10, rect.bottom - 8, rect.w - 20, 4), border_radius=2)
                pygame.draw.rect(surface, (255, 240, 160), (rect.x + 10, rect.bottom - 8, int((rect.w - 20) * frac), 4), border_radius=2)

    def _draw_locked_card(self, surface, game: "Game", path: int, rect: pygame.Rect) -> None:
        """Greyed-out upgrade card for a path this Jalu can no longer take."""
        t = game.selected
        grey, dim = (150, 154, 168), (110, 114, 128)
        plate = gfx.blank(rect.w, rect.h)
        pygame.draw.rect(plate, (20, 22, 30, 150), (0, 0, rect.w, rect.h), border_radius=12)
        pygame.draw.rect(plate, (255, 255, 255, 40), (0, 0, rect.w, rect.h), 2, border_radius=12)
        surface.blit(plate, rect.topleft)
        x, y = rect.x + 12, rect.y + 8
        draw_outlined(surface, f"{'AB'[path]}  {t.data['paths'][path]['name']}", (x, y), 18, dim, width=2)
        for i in range(MAX_TIER):  # empty tier pips
            c = (rect.right - 18 - (MAX_TIER - 1 - i) * 16, y + 11)
            pygame.draw.circle(surface, (20, 14, 30), c, 7)
            pygame.draw.circle(surface, (60, 64, 80), c, 5)
        cx, cy = rect.centerx, rect.centery + 2
        pygame.draw.arc(surface, (20, 14, 30), (cx - 12, cy - 30, 24, 30), 0, math.pi, 7)  # padlock shackle
        pygame.draw.arc(surface, grey, (cx - 12, cy - 30, 24, 30), 0, math.pi, 4)
        body = pygame.Rect(cx - 17, cy - 10, 34, 26)
        pygame.draw.rect(surface, (20, 14, 30), body.inflate(4, 4), border_radius=6)
        pygame.draw.rect(surface, grey, body, border_radius=5)
        pygame.draw.circle(surface, (50, 54, 66), (cx, cy + 1), 4)
        draw_outlined(surface, "LOCKED", (cx, rect.bottom - 22), 20, grey, center=True, width=2)

    def _draw_upgrade_card(self, surface, game: "Game", path: int, rect: pygame.Rect) -> None:
        t = game.selected
        up = t.next_upgrade(path)
        ok, reason = t.can_upgrade(path)
        cost = game.upgrade_cost(t, up) if up else 0
        afford_money = up is not None and game.money >= cost
        afford_know = up is not None and game.ball_knowledge >= up["knowledge"]
        buyable = up is not None and ok and afford_money and afford_know
        if up is not None and t.is_path_locked(path):  # Jalu: the other path was chosen -> this one is locked
            self._draw_locked_card(surface, game, path, rect)
            return
        plate = gfx.blank(rect.w, rect.h)
        pygame.draw.rect(plate, (255, 255, 255, 26), (0, 0, rect.w, rect.h), border_radius=12)
        pygame.draw.rect(plate, (130, 240, 110, 190) if buyable else (255, 255, 255, 60), (0, 0, rect.w, rect.h), 2, border_radius=12)
        surface.blit(plate, rect.topleft)
        x, y = rect.x + 12, rect.y + 8
        draw_outlined(surface, f"{'AB'[path]}  {t.data['paths'][path]['name']}", (x, y), 18, (255, 255, 255), width=2)
        for i in range(MAX_TIER):  # tier pips
            c = (rect.right - 18 - (MAX_TIER - 1 - i) * 16, y + 11)
            pygame.draw.circle(surface, (20, 14, 30), c, 7)
            pygame.draw.circle(surface, GOLD if i < t.tiers[path] else (70, 80, 120), c, 5)
            if i < t.tiers[path]:
                pygame.draw.circle(surface, (255, 248, 190), (c[0] - 1, c[1] - 1), 2)
        if up is None:
            draw_outlined(surface, "MAX TIER", (rect.centerx, rect.centery + 8), 28, COLORS["good"], center=True, width=3)
            return
        pending = bool(t.pending_effects(up))
        draw_outlined(surface, up["name"] + ("  (effect soon)" if pending else ""), (x, y + 26), 22, GOLD, width=2)
        for i, line in enumerate(wrap_text(up["description"], 15, rect.w - 24)[:2]):
            draw_outlined(surface, line, (x, y + 50 + i * 16), 15, (225, 235, 255), width=1)
        btn = pygame.Rect(rect.x + 10, rect.bottom - 42, rect.w - 20, 32)
        self._btn(surface, btn, COLORS["btn_green"], game, buyable, 9)
        if not ok:
            draw_outlined(surface, reason.upper(), btn.center, 17, (215, 218, 228), center=True, width=1)
            return
        surface.blit(gfx.icon("coin", 24), (btn.x + 10, btn.y + 4))
        draw_outlined(surface, f"${cost}", (btn.x + 38, btn.centery), 22,
                      (255, 255, 255) if afford_money else COLORS["bad"], anchor="midleft", width=2)
        if cost != up["cost"]:
            draw_outlined(surface, f"-{round((1 - cost / up['cost']) * 100)}%", (btn.x + 108, btn.centery), 15,
                          COLORS["good"], anchor="midleft", width=1)
        if up["knowledge"]:
            surface.blit(gfx.icon("brain", 24), (btn.right - 74, btn.y + 4))
            draw_outlined(surface, str(up["knowledge"]), (btn.right - 46, btn.centery), 22,
                          KNOWLEDGE_COLOR if afford_know else COLORS["bad"], anchor="midleft", width=2)
