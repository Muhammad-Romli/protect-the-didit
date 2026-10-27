"""Graph-path console (drawn inside the bottom bar while a Graph Bima is selected): formula input,
FIRE, direction, patterns, Brain Energy bar with the preview's cost. Pure UI, logic is in game/bima.py."""
from __future__ import annotations

import pygame

from data.bima import GRAPH, PATTERNS
from data.settings import COLORS
from game import bima, gfx
from game.utils import draw_outlined, wrap_text

CYAN = (130, 215, 255)


class GraphConsole:
    def __init__(self) -> None:
        self.focused = False
        self.pattern_open = False
        self.pattern_i = 0
        self.param_i = 0
        self.input = pygame.Rect(330, 648, 330, 34)
        self.fire_btn = pygame.Rect(668, 646, 96, 38)
        self.dir_btn = pygame.Rect(772, 646, 70, 38)
        self.pat_btn = pygame.Rect(850, 646, 118, 38)
        self.bar = pygame.Rect(330, 690, 330, 18)
        self.popup = pygame.Rect(330, 392, 440, 236)
        self.pat_rects = [pygame.Rect(self.popup.x + 14 + (i % 2) * 208, self.popup.y + 50 + (i // 2) * 40, 200, 34)
                          for i in range(len(PATTERNS))]
        self.param_minus = pygame.Rect(self.popup.x + 150, self.popup.bottom - 52, 40, 34)
        self.param_plus = pygame.Rect(self.popup.x + 300, self.popup.bottom - 52, 40, 34)

    def visible(self, game) -> bool:
        t = game.selected
        return t is not None and t.kind == "bima" and bima.graph_tier(t) >= 2 and not game.options_open

    # ---------------------------------------------------------------- input
    def hit_test(self, pos, game):
        if not self.visible(game):
            return None
        t = game.selected
        if self.pattern_open and self.popup.collidepoint(pos):
            for i, r in enumerate(self.pat_rects):
                if r.collidepoint(pos):
                    return ("g_pattern", i)
            if self.param_minus.collidepoint(pos):
                return ("g_param", -1)
            if self.param_plus.collidepoint(pos):
                return ("g_param", 1)
            return ("noop",)
        if self.input.collidepoint(pos):
            return ("g_focus",)
        if self.fire_btn.collidepoint(pos):
            return ("g_fire",)
        if self.dir_btn.collidepoint(pos):
            return ("g_dir", -1 if pos[0] < self.dir_btn.centerx else 1)
        if bima.graph_tier(t) >= 3 and self.pat_btn.collidepoint(pos):
            return ("g_patterns",)
        return None

    def do(self, action, game) -> None:
        t = game.selected
        name = action[0]
        if name == "g_focus":
            self.focused = True
        elif name == "g_fire":
            self.focused = False
            bima.fire_graph(game, t)
        elif name == "g_dir":
            t.graph_dir = action[1]
        elif name == "g_patterns":
            self.pattern_open = not self.pattern_open
        elif name == "g_pattern":
            self.pattern_i = action[1]
            self.param_i = 0
            self._apply_pattern(t)
        elif name == "g_param":
            vals = PATTERNS[self.pattern_i][2]
            self.param_i = (self.param_i + action[1]) % len(vals)
            self._apply_pattern(t)

    def _apply_pattern(self, t) -> None:
        name, tmpl, vals, _ = PATTERNS[self.pattern_i]
        t.formula = tmpl.replace("{a}", f"{vals[self.param_i]:g}")

    def key(self, event, game) -> bool:
        """Typing. Returns True when the key was consumed."""
        t = game.selected
        if t is None or not self.focused:
            return False
        k = event.key
        if k in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.focused = False
            bima.fire_graph(game, t)
        elif k == pygame.K_ESCAPE:
            self.focused = False
        elif k == pygame.K_BACKSPACE:
            t.formula = t.formula[:-1]
        elif k == pygame.K_DELETE:
            t.formula = ""
        elif event.unicode and event.unicode.isprintable() and len(t.formula) < 80:
            t.formula += event.unicode
        return True

    # ----------------------------------------------------------------- draw
    def draw(self, surface, game) -> None:
        t = game.selected
        gt = bima.graph_tier(t)
        pv = bima.update_preview(t)
        draw_outlined(surface, "y =", (self.input.x - 10, self.input.centery), 26, (255, 255, 255), anchor="midright", width=2)
        pygame.draw.rect(surface, (20, 14, 30), self.input.inflate(6, 6), border_radius=10)
        pygame.draw.rect(surface, (250, 246, 236) if self.focused else (214, 208, 196), self.input, border_radius=8)
        txt = t.formula
        blink = self.focused and (pygame.time.get_ticks() // 450) % 2 == 0
        show = txt + ("|" if blink else "")
        from game.utils import get_font
        font = get_font(24)
        while font.size(show)[0] > self.input.w - 16 and len(show) > 1:
            show = show[1:]
        img = font.render(show, True, (30, 24, 40))
        surface.blit(img, img.get_rect(midleft=(self.input.x + 10, self.input.centery)))
        if not txt and not self.focused:
            hint = get_font(20).render("click and type, e.g.  2x   or   x^2/10", True, (150, 144, 160))
            surface.blit(hint, hint.get_rect(midleft=(self.input.x + 10, self.input.centery)))
        # fire / direction / patterns
        ready = bima.can_fire_now(game, t)
        self._btn(surface, self.fire_btn, COLORS["btn_orange"], game, ready)
        draw_outlined(surface, "FIRE", self.fire_btn.center, 24, center=True, width=2)
        pygame.draw.rect(surface, (20, 14, 30), self.dir_btn.inflate(4, 4), border_radius=10)
        for i, d in enumerate((-1, 1)):
            half = pygame.Rect(self.dir_btn.x + i * 35, self.dir_btn.y, 35, 38)
            on = t.graph_dir == d
            pygame.draw.rect(surface, (255, 190, 80) if on else (70, 64, 90), half.inflate(-2, -2), border_radius=8)
            cx, cy = half.center
            pygame.draw.polygon(surface, (255, 255, 255) if on else (170, 166, 190),
                                [(cx - 6 * d, cy - 8), (cx - 6 * d, cy + 8), (cx + 7 * d, cy)])
        if gt >= 3:
            self._btn(surface, self.pat_btn, COLORS["btn_blue"], game, True, pressed=self.pattern_open)
            draw_outlined(surface, "PATTERNS", self.pat_btn.center, 20, center=True, width=2)
        # energy bar
        mx = bima.brain_max(t)
        pygame.draw.rect(surface, (14, 10, 26), self.bar.inflate(4, 4), border_radius=11)
        pygame.draw.rect(surface, (40, 34, 66), self.bar, border_radius=9)
        fill = self.bar.copy()
        fill.w = max(6, int(self.bar.w * t.brain / mx))
        pygame.draw.rect(surface, (90, 200, 255), fill, border_radius=9)
        pygame.draw.rect(surface, (190, 238, 255), (fill.x + 4, fill.y + 2, max(0, fill.w - 8), 5), border_radius=3)
        if pv and "cost" in pv:
            cx = self.bar.x + int(self.bar.w * min(1.0, pv["cost"] / mx))
            bad = pv["cost"] > t.brain
            pygame.draw.line(surface, (255, 110, 100) if bad else (255, 255, 255), (cx, self.bar.y - 3), (cx, self.bar.bottom + 3), 3)
        draw_outlined(surface, f"Brain Energy {int(t.brain)}/{int(mx)}   +{GRAPH['regen'][gt]}/s", self.bar.center, 15, center=True, width=1)
        # status line
        x, y = self.fire_btn.x, 700
        if pv is None:
            return
        if "error" in pv:
            msg = wrap_text(pv["error"], 16, 300)[0]
            draw_outlined(surface, msg, (x, y), 17, COLORS["bad"], anchor="midleft", width=1)
        else:
            cost = pv["cost"]
            col = COLORS["bad"] if cost > t.brain else (255, 255, 255)
            wait = ""
            if cost > t.brain and cost <= mx:
                wait = f"  (ready in {(cost - t.brain) / GRAPH['regen'][gt]:.1f}s)"
            elif cost > mx:
                wait = "  (more than max!)"
            draw_outlined(surface, f"Cost {cost}  length {pv['length']:.0f}{wait}", (x, y - 8), 17, col, anchor="midleft", width=1)
            draw_outlined(surface, f"reads as: {pv['pretty'][:34]}   [{pv['ended']}]", (x, y + 9), 14, (200, 205, 225), anchor="midleft", width=1)
        if self.pattern_open and gt >= 3:
            self._draw_popup(surface, game, gt)

    def _draw_popup(self, surface, game, gt: int) -> None:
        p = self.popup
        surface.blit(gfx.panel_surface(p.w, p.h, 12), (p.x - 2, p.y - 2))
        draw_outlined(surface, "PATTERNS", (p.x + 16, p.y + 14), 26, (255, 214, 70), width=2)
        for i, r in enumerate(self.pat_rects):
            name, tmpl, vals, _ = PATTERNS[i]
            locked = ("sin" in tmpl) and gt < 4
            self._btn(surface, r, COLORS["btn_blue"] if not locked else (90, 90, 100), game, not locked, 8, pressed=i == self.pattern_i)
            draw_outlined(surface, name + ("  (Lv4)" if locked else ""), r.center, 19, (255, 255, 255) if not locked else (190, 190, 200), center=True, width=1)
        name, tmpl, vals, _ = PATTERNS[self.pattern_i]
        draw_outlined(surface, f"a = {vals[self.param_i]:g}", (p.centerx + 0, self.param_minus.centery), 24, (255, 255, 255), center=True, width=2)
        for r, sym in ((self.param_minus, "-"), (self.param_plus, "+")):
            self._btn(surface, r, COLORS["btn_green"], game, True, 8)
            draw_outlined(surface, sym, r.center, 26, center=True, width=2)

    @staticmethod
    def _btn(surface, rect, base, game, enabled=True, radius=10, pressed=False) -> None:
        hover = enabled and rect.collidepoint(game.mouse_pos)
        state = "off" if not enabled else "pressed" if pressed else "hover" if hover else "normal"
        surface.blit(gfx.glossy(rect.w, rect.h, base, radius, (255, 255, 255), state), (rect.x - 1, rect.y - 1))
