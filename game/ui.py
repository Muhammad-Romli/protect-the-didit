"""UI: shop bar, HUD, upgrade panel. Draws and hit-tests only; Game executes actions.

hit_test() returns an action tuple:
  ("shop", kind) | ("start_wave",) | ("speed",) | ("upgrade", path) | ("sell",) | ("noop",)
or None when the click is not on any UI.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

from data.settings import COLORS, MAX_TIER, PANEL_RECT, SHOP_RECT
from data.towers import TOWER_ORDER, TOWERS
from game.utils import draw_text, get_font, wrap_text

if TYPE_CHECKING:
    from game.game import Game

PANEL_X = PANEL_RECT[0] + 10
PANEL_INNER_W = PANEL_RECT[2] - 20


class UI:
    def __init__(self) -> None:
        self.panel = pygame.Rect(*PANEL_RECT)
        self.shop = pygame.Rect(*SHOP_RECT)
        self.start_btn = pygame.Rect(PANEL_X, 140, 170, 48)
        self.speed_btn = pygame.Rect(PANEL_X + 180, 140, 80, 48)
        self.upgrade_btns = [pygame.Rect(PANEL_X, 245, PANEL_INNER_W, 140),
                             pygame.Rect(PANEL_X, 395, PANEL_INNER_W, 140)]
        self.sell_btn = pygame.Rect(PANEL_X, 545, PANEL_INNER_W, 40)
        self.shop_btns = {k: pygame.Rect(20 + i * 215, 650, 200, 62)
                          for i, k in enumerate(TOWER_ORDER)}

    # ------------------------------------------------------------- hit test
    def hit_test(self, pos, game: "Game"):
        for kind, rect in self.shop_btns.items():
            if rect.collidepoint(pos):
                return ("shop", kind)
        if self.start_btn.collidepoint(pos):
            return ("start_wave",)
        if self.speed_btn.collidepoint(pos):
            return ("speed",)
        if game.selected is not None:
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
            draw_text(surface, "Select a tower to upgrade", (PANEL_X, 260), 22, COLORS["text_dim"])
        if game.message:
            for i, line in enumerate(wrap_text(game.message, 22, PANEL_INNER_W)):
                draw_text(surface, line, (PANEL_X, 600 + i * 20), 22, COLORS["gold"])
        hint = "LMB place/select   RMB/Esc cancel   R restart"
        for i, line in enumerate(wrap_text(hint, 18, PANEL_INNER_W)):
            draw_text(surface, line, (PANEL_X, 668 + i * 16), 18, COLORS["text_dim"])

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
        draw_text(surface, f"Money: ${int(game.money)}", (PANEL_X, 14), 36, COLORS["gold"])
        hp_color = COLORS["good"] if game.stash_hp > 30 else COLORS["bad"]
        draw_text(surface, f"Stash HP: {game.stash_hp}", (PANEL_X, 52), 32, hp_color)
        draw_text(surface, f"Wave: {game.waves.number}/{game.waves.total}", (PANEL_X, 88), 32)

        can = game.waves.can_start
        self._button(surface, self.start_btn, can, game.mouse_pos)
        if game.waves.active:
            label = "Wave running..."
        elif can:
            label = f"Start wave {game.waves.number + 1}"
        else:
            label = "All waves done"
        draw_text(surface, label, self.start_btn.center, 24,
                  COLORS["text"] if can else COLORS["text_dim"], center=True)
        self._button(surface, self.speed_btn, True, game.mouse_pos)
        draw_text(surface, f"x{game.speed}", self.speed_btn.center, 28, center=True)

    def _draw_shop(self, surface, game: "Game") -> None:
        for kind, rect in self.shop_btns.items():
            d = TOWERS[kind]
            affordable = game.money >= d["cost"]
            self._button(surface, rect, affordable, game.mouse_pos)
            if game.placing == kind:
                pygame.draw.rect(surface, COLORS["good"], rect, 3, border_radius=6)
            pygame.draw.circle(surface, d["color"], (rect.x + 30, rect.centery), 18)
            draw_text(surface, d["name"][0], (rect.x + 30, rect.centery), 26, (15, 15, 25), center=True)
            draw_text(surface, d["name"], (rect.x + 58, rect.y + 10), 28,
                      COLORS["text"] if affordable else COLORS["text_dim"])
            draw_text(surface, f"${d['cost']}", (rect.x + 58, rect.y + 36), 26,
                      COLORS["gold"] if affordable else COLORS["bad"])

    def _draw_tower_panel(self, surface, game: "Game") -> None:
        t = game.selected
        draw_text(surface, f"{t.name}  (A:{t.tiers[0]}  B:{t.tiers[1]})", (PANEL_X, 210), 30)
        for i, rect in enumerate(self.upgrade_btns):
            self._draw_upgrade_button(surface, game, i, rect)
        self._button(surface, self.sell_btn, True, game.mouse_pos)
        draw_text(surface, f"Sell  +${t.sell_value}", self.sell_btn.center, 26, center=True)

    def _draw_upgrade_button(self, surface, game: "Game", path: int, rect: pygame.Rect) -> None:
        t = game.selected
        path_name = t.data["paths"][path]["name"]
        up = t.next_upgrade(path)
        ok, reason = t.can_upgrade(path)
        affordable = up is not None and game.money >= up["cost"]
        self._button(surface, rect, ok and affordable, game.mouse_pos)

        x, y = rect.x + 8, rect.y + 6
        draw_text(surface, f"{'AB'[path]}: {path_name}  {t.tiers[path]}/{MAX_TIER}", (x, y), 24)
        if up is None:
            draw_text(surface, "MAX TIER", (x, y + 26), 24, COLORS["good"])
            return
        draw_text(surface, up["name"], (x, y + 24), 24, COLORS["gold"])
        cost_color = COLORS["gold"] if affordable else COLORS["bad"]
        cost_img_x = rect.right - 8
        label = f"${up['cost']}"
        w = get_font(24).size(label)[0]
        draw_text(surface, label, (cost_img_x - w, y + 24), 24, cost_color)
        yy = y + 46
        for line in wrap_text(up["description"], 20, rect.w - 16)[:3]:
            draw_text(surface, line, (x, yy), 20, COLORS["text_dim"])
            yy += 16
        if not ok:
            status, color = reason, COLORS["bad"]
        elif not affordable:
            status, color = f"Need ${math.ceil(up['cost'] - game.money)} more", COLORS["bad"]
        elif t.pending_effects(up):
            status, color = "Special effect not implemented yet", COLORS["text_dim"]
        else:
            status, color = "", COLORS["text"]
        if status:
            draw_text(surface, status, (x, rect.bottom - 22), 20, color)
