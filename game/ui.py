"""UI: shop bar, HUD, upgrade panel. Draws and hit-tests only; Game executes actions.

hit_test() returns an action tuple:
  ("shop", kind) | ("start_wave",) | ("speed",) | ("pause",) | ("activity", act_id)
  | ("upgrade", path) | ("sell",) | ("noop",)
or None when the click is not on any UI.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

from data.activities import ACTIVITIES, STACKS, activities_for
from data.settings import (COLORS, INCOME_INTERVAL_SECONDS, MAX_ACTIVITIES, MAX_TIER, PANEL_RECT, PREP_GRACE_SECONDS,
                           PREP_MAX_SECONDS, SHOP_RECT)
from data.towers import TOWER_ORDER, TOWERS
from game.utils import draw_text, get_font, wrap_text

if TYPE_CHECKING:
    from game.game import Game

PANEL_X = PANEL_RECT[0] + 10
PANEL_INNER_W = PANEL_RECT[2] - 20
KNOWLEDGE_COLOR = (120, 200, 230)
GAIN_COLOR = (130, 255, 150)
SPEND_COLOR = (255, 120, 120)
POPUP_SECONDS = 1.1
POPUP_MERGE_SECONDS = 0.3   # gains inside this window become one "+$N"
COUNT_UP_SPEED = 9.0        # how fast the shown total catches up with the real one


class UI:
    def __init__(self) -> None:
        self.panel = pygame.Rect(*PANEL_RECT)
        self.shop = pygame.Rect(*SHOP_RECT)
        self.start_btn = pygame.Rect(PANEL_X, 184, 150, 44)
        self.speed_btn = pygame.Rect(PANEL_X + 156, 184, 52, 44)
        self.pause_btn = pygame.Rect(PANEL_X + 214, 184, 46, 44)
        self.upgrade_btns = [pygame.Rect(PANEL_X, 332, PANEL_INNER_W, 134),
                             pygame.Rect(PANEL_X, 472, PANEL_INNER_W, 134)]
        self.sell_btn = pygame.Rect(PANEL_X, 612, PANEL_INNER_W, 28)
        self.shop_btns = {k: pygame.Rect(20 + i * 215, 650, 200, 62)
                          for i, k in enumerate(TOWER_ORDER)}
        # money display: counts up/down to the real total, with +$N / -$N popups beside it
        self.shown_money: float | None = None
        self.pulse = 0.0
        self.popups: list[list] = []  # [text, color, age]
        self._pending = {"gain": 0.0, "spend": 0.0}
        self._pending_timer = {"gain": 0.0, "spend": 0.0}

    def money_change(self, amount: float) -> None:
        """Called by Game for every earning (+) or spending (-)."""
        kind = "gain" if amount > 0 else "spend"
        if self._pending[kind] == 0:
            self._pending_timer[kind] = POPUP_MERGE_SECONDS
        self._pending[kind] += abs(amount)

    def update(self, dt: float, money: float) -> None:
        if self.shown_money is None:
            self.shown_money = money
        diff = money - self.shown_money
        self.shown_money = money if abs(diff) < 0.6 else self.shown_money + diff * min(1.0, dt * COUNT_UP_SPEED)
        self.pulse = max(0.0, self.pulse - dt * 3)
        for kind, color in ("gain", GAIN_COLOR), ("spend", SPEND_COLOR):
            if self._pending[kind] > 0:
                self._pending_timer[kind] -= dt
                if self._pending_timer[kind] <= 0:
                    value = round(self._pending[kind])
                    if value > 0:
                        self.popups.append([f"{'+' if kind == 'gain' else '-'}${value}", color, 0.0])
                        if kind == "gain":
                            self.pulse = 1.0
                    self._pending[kind] = 0.0
        for p in self.popups:
            p[2] += dt
        self.popups = [p for p in self.popups if p[2] < POPUP_SECONDS]

    def activity_rects(self, tower_kind: str) -> list[tuple[str, pygame.Rect]]:
        """One button per activity the tower can run, splitting the panel width."""
        acts = activities_for(tower_kind)
        n = max(1, len(acts))
        gap = 6
        w = (PANEL_INNER_W - gap * (n - 1)) // n
        return [(act_id, pygame.Rect(PANEL_X + i * (w + gap), 282, w, 44))
                for i, (act_id, _) in enumerate(acts)]

    # ------------------------------------------------------------- hit test
    def hit_test(self, pos, game: "Game"):
        for kind, rect in self.shop_btns.items():
            if rect.collidepoint(pos):
                return ("shop", kind)
        if self.start_btn.collidepoint(pos):
            return ("start_wave",)
        if self.speed_btn.collidepoint(pos):
            return ("speed",)
        if self.pause_btn.collidepoint(pos):
            return ("pause",)
        if game.selected is not None:
            for act_id, rect in self.activity_rects(game.selected.kind):
                if rect.collidepoint(pos):
                    return ("activity", act_id)
            for i, rect in enumerate(self.upgrade_btns):
                if rect.collidepoint(pos):
                    return ("upgrade", i)
            if self.sell_btn.collidepoint(pos):
                return ("sell",)
        if self.panel.collidepoint(pos) or self.shop.collidepoint(pos):
            return ("noop",)
        return None

    # ----------------------------------------------------------------- draw
    def draw(self, surface: pygame.Surface, game: "Game") -> None:
        pygame.draw.rect(surface, COLORS["ui_bg"], self.panel)
        pygame.draw.rect(surface, COLORS["ui_bg"], self.shop)
        pygame.draw.line(surface, (70, 74, 90), self.shop.topleft, self.shop.topright, 2)
        pygame.draw.line(surface, (70, 74, 90), self.panel.topleft, self.panel.bottomleft, 2)
        self._draw_hud(surface, game)
        self._draw_shop(surface, game)
        if game.selected is not None:
            self._draw_tower_panel(surface, game)
        else:
            draw_text(surface, "Select a tower to upgrade", (PANEL_X, 290), 22, COLORS["text_dim"])
        if game.message:
            for i, line in enumerate(wrap_text(game.message, 20, PANEL_INNER_W)[:2]):
                draw_text(surface, line, (PANEL_X, 646 + i * 18), 20, COLORS["gold"])
        for i, line in enumerate(("1-3 place  Space wave  P pause", "F speed  Q/W upgrade  X sell", "M mute  F11 fullscreen  R restart")):
            draw_text(surface, line, (PANEL_X, 684 + i * 13), 15, COLORS["text_dim"])

    def _button(self, surface, rect, enabled=True, hover_pos=None) -> None:
        if not enabled:
            color = COLORS["ui_btn_off"]
        elif hover_pos is not None and rect.collidepoint(hover_pos):
            color = COLORS["ui_btn_hover"]
        else:
            color = COLORS["ui_btn"]
        pygame.draw.rect(surface, color, rect, border_radius=6)
        pygame.draw.rect(surface, (90, 94, 110), rect, 1, border_radius=6)

    def _draw_hud(self, surface, game: "Game") -> None:
        self._draw_money(surface, game)
        hp_color = COLORS["good"] if game.stash_hp > 30 else COLORS["bad"]
        draw_text(surface, f"Stash HP: {game.stash_hp}", (PANEL_X, 42), 28, hp_color)
        draw_text(surface, f"Wave: {game.waves.number}/{game.waves.total}", (PANEL_X, 68), 28)
        self._draw_phase(surface, game)

        can = game.waves.can_start
        self._button(surface, self.start_btn, can, game.mouse_pos)
        if game.waves.active:
            label = "Wave running..."
        elif can:
            label = f"Start wave {game.waves.number + 1}"
        else:
            label = "All waves done"
        draw_text(surface, label, self.start_btn.center, 22,
                  COLORS["text"] if can else COLORS["text_dim"], center=True)
        self._button(surface, self.speed_btn, True, game.mouse_pos)
        draw_text(surface, f"x{game.speed}", self.speed_btn.center, 28, center=True)
        self._button(surface, self.pause_btn, True, game.mouse_pos)
        draw_text(surface, ">" if game.paused else "II", self.pause_btn.center, 28,
                  COLORS["gold"] if game.paused else COLORS["text"], center=True)

    def _draw_money(self, surface, game: "Game") -> None:
        shown = int(self.shown_money if self.shown_money is not None else game.money)
        size = 34 + int(6 * self.pulse)  # little bump while a gain is being absorbed
        t = self.pulse
        color = tuple(int(g + (w - g) * t) for g, w in zip(COLORS["gold"], (255, 255, 255)))
        label = f"Money: ${shown}"
        draw_text(surface, label, (PANEL_X, 10 - (size - 34) // 2), size, color)
        x = PANEL_X + get_font(34).size(f"Money: ${shown}")[0] + 14
        for text, col, age in self.popups:
            f = age / POPUP_SECONDS
            img = get_font(26 + int(6 * max(0.0, 1 - f * 5))).render(text, True, col)
            if f > 0.6:
                img.set_alpha(int(255 * (1 - f) / 0.4))
            surface.blit(img, (min(x, PANEL_X + PANEL_INNER_W - img.get_width()), 14 - int(10 * f)))

    def _draw_phase(self, surface, game: "Game") -> None:
        hp_mult, speed_mult = game.enemy_multipliers()
        strength = f"x{hp_mult:.1f} HP, +{round((speed_mult - 1) * 100)}% speed"
        if game.phase.value == "battle":
            draw_text(surface, "BATTLE", (PANEL_X, 98), 28, COLORS["bad"])
            draw_text(surface, f"This wave: {strength}", (PANEL_X, 128), 20, COLORS["text_dim"])
        else:
            t = int(game.prep_time)
            mx = PREP_MAX_SECONDS
            draw_text(surface, f"PREPARATION  {t // 60}:{t % 60:02d} / {mx // 60}:{mx % 60:02d}",
                      (PANEL_X, 98), 26, COLORS["gold"])
            bar = pygame.Rect(PANEL_X, 124, PANEL_INNER_W, 8)
            pygame.draw.rect(surface, (60, 62, 74), bar)
            fill = bar.copy()
            fill.w = int(bar.w * min(1.0, game.prep_time / mx))
            r = game.prep_ramp()
            color = (int(110 + 125 * r), int(220 - 130 * r), 90)  # green -> red as it escalates
            pygame.draw.rect(surface, color, fill)
            grace_x = bar.x + int(bar.w * PREP_GRACE_SECONDS / mx)
            pygame.draw.line(surface, (255, 255, 255), (grace_x, bar.y - 2), (grace_x, bar.bottom + 1), 1)
            draw_text(surface, f"Next wave: {strength}", (PANEL_X, 136), 20,
                      COLORS["bad"] if r > 0 else COLORS["text_dim"])
        used = game.activity_slots_used()
        draw_text(surface, f"Activities: {used}/{MAX_ACTIVITIES}", (PANEL_X, 158), 22,
                  COLORS["gold"] if used else COLORS["text_dim"])
        know = f"Knowledge: {game.ball_knowledge}"
        w = get_font(22).size(know)[0]
        draw_text(surface, know, (PANEL_X + PANEL_INNER_W - w, 158), 22, KNOWLEDGE_COLOR)

    def _draw_shop(self, surface, game: "Game") -> None:
        for i, (kind, rect) in enumerate(self.shop_btns.items()):
            d = TOWERS[kind]
            affordable = game.money >= d["cost"]
            self._button(surface, rect, affordable, game.mouse_pos)
            if game.placing == kind:
                pygame.draw.rect(surface, COLORS["good"], rect, 3, border_radius=6)
            pygame.draw.circle(surface, d["color"], (rect.x + 30, rect.centery), 18)
            draw_text(surface, d["name"][0], (rect.x + 30, rect.centery), 26, (15, 15, 25), center=True)
            draw_text(surface, f"{d['name']}  [{i + 1}]", (rect.x + 58, rect.y + 10), 28,
                      COLORS["text"] if affordable else COLORS["text_dim"])
            draw_text(surface, f"${d['cost']}", (rect.x + 58, rect.y + 36), 26,
                      COLORS["gold"] if affordable else COLORS["bad"])

    # ---------------------------------------------------------- tower panel
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
        draw_text(surface, f"{t.name}  (A:{t.tiers[0]}  B:{t.tiers[1]})", (PANEL_X, 232), 26)
        for i, line in enumerate(wrap_text(self._stats_text(t), 18, PANEL_INNER_W)[:2]):
            draw_text(surface, line, (PANEL_X, 254 + i * 14), 18, COLORS["text_dim"])
        self._draw_activity_buttons(surface, game)
        for i, rect in enumerate(self.upgrade_btns):
            self._draw_upgrade_button(surface, game, i, rect)
        confirming = game.sell_pending is t and game.sell_timer > 0
        self._button(surface, self.sell_btn, True, game.mouse_pos)
        if confirming:
            pygame.draw.rect(surface, COLORS["bad"], self.sell_btn, 2, border_radius=6)
        draw_text(surface, f"Confirm sell?  +${t.sell_value}" if confirming else f"Sell  +${t.sell_value}",
                  self.sell_btn.center, 24, COLORS["bad"] if confirming else COLORS["text"], center=True)

    def _draw_activity_buttons(self, surface, game: "Game") -> None:
        t = game.selected
        prep = game.phase.value == "preparation"
        for act_id, rect in self.activity_rects(t.kind):
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
            self._button(surface, rect, usable, game.mouse_pos)
            if running:
                draw_text(surface, f"Stop {data['name']}", (rect.x + 6, rect.y + 5), 20, COLORS["gold"])
                frac = min(1.0, t.activity_acc / data["interval"])
                pygame.draw.rect(surface, (30, 32, 40), (rect.x + 6, rect.bottom - 8, rect.w - 12, 4))
                pygame.draw.rect(surface, COLORS["gold"],
                                 (rect.x + 6, rect.bottom - 8, int((rect.w - 12) * frac), 4))
            else:
                draw_text(surface, f"Start {data['name']}", (rect.x + 6, rect.y + 5), 20,
                          COLORS["text"] if usable else COLORS["text_dim"])
            if kind == "stack":
                info = f"{STACKS[arg]['label']} {t.stacks.get(arg, 0)}/{STACKS[arg]['max']}"
                color = STACKS[arg]["color"]
            else:
                info, color = f"+{arg} knowledge / {data['interval']:g}s", KNOWLEDGE_COLOR
            if not running and not usable:
                color = COLORS["text_dim"]
                info = (f"Needs {lock}" if lock else "Maxed" if maxed else
                        "Preparation only" if not prep else "No free slot")
            draw_text(surface, info, (rect.x + 6, rect.y + 23), 18, color)

    def _draw_upgrade_button(self, surface, game: "Game", path: int, rect: pygame.Rect) -> None:
        t = game.selected
        path_name = t.data["paths"][path]["name"]
        up = t.next_upgrade(path)
        ok, reason = t.can_upgrade(path)
        cost = game.upgrade_cost(t, up) if up else 0
        afford_money = up is not None and game.money >= cost
        afford_know = up is not None and game.ball_knowledge >= up["knowledge"]
        self._button(surface, rect, ok and afford_money and afford_know, game.mouse_pos)

        x, y = rect.x + 8, rect.y + 6
        key = "QW"[path]
        draw_text(surface, f"{'AB'[path]}: {path_name}  {t.tiers[path]}/{MAX_TIER}  [{key}]", (x, y), 24)
        if up is None:
            draw_text(surface, "MAX TIER", (x, y + 26), 24, COLORS["good"])
            return
        draw_text(surface, up["name"], (x, y + 22), 24, COLORS["gold"])
        money_lbl = f"${cost}"
        draw_text(surface, money_lbl, (x, y + 42), 22, COLORS["gold"] if afford_money else COLORS["bad"])
        if cost != up["cost"]:
            draw_text(surface, f"(-{round((1 - cost / up['cost']) * 100)}%)",
                      (x + get_font(22).size(money_lbl)[0] + 6, y + 44), 18, COLORS["good"])
        if up["knowledge"]:
            kx = x + 100
            draw_text(surface, f"{up['knowledge']} knowledge", (kx, y + 42), 22,
                      KNOWLEDGE_COLOR if afford_know else COLORS["bad"])
        yy = y + 62
        for line in wrap_text(up["description"], 20, rect.w - 16)[:3]:
            draw_text(surface, line, (x, yy), 20, COLORS["text_dim"])
            yy += 16
        if not ok:
            status, color = reason, COLORS["bad"]
        elif not afford_money:
            status, color = f"Need ${math.ceil(cost - game.money)} more", COLORS["bad"]
        elif not afford_know:
            status, color = f"Need {up['knowledge'] - game.ball_knowledge} more knowledge (Jalu: Larp)", COLORS["bad"]
        elif t.pending_effects(up):
            status, color = "Special effect not implemented yet", COLORS["text_dim"]
        else:
            status, color = "", COLORS["text"]
        if status:
            draw_text(surface, status, (x, rect.bottom - 20), 19, color)
