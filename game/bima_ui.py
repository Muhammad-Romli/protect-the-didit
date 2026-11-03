"""Graph-path console (drawn inside the bottom bar while a Graph Bima is selected): formula input,
FIRE, direction, patterns, Brain Energy bar with the preview's cost. Pure UI, logic is in game/bima.py."""
from __future__ import annotations

import pygame

from data.bima import GRAPH, PATTERNS
from data.touch import GRAPH_TOUCH
from data.settings import COLORS
from game import bima, gfx
from game.utils import draw_outlined, wrap_text

CYAN = (130, 215, 255)


class GraphConsole:
    def __init__(self) -> None:
        self._focused = False
        self.cur = 0                 # caret position in the formula text
        self.anchor: int | None = None   # other end of the selection (None = no selection)
        self.dragging = False
        self._clip = ""              # fallback clipboard when the system one is unavailable (e.g. in the browser)
        self._last_click = 0
        self.touch = False
        self.pattern_open = False
        self.pattern_i = 0
        self.param_i = 0
        self.input = pygame.Rect(330, 648, 330, 34)
        self.fire_btn = pygame.Rect(668, 646, 96, 38)
        self.dir_btn = pygame.Rect(772, 646, 70, 38)
        self.pat_btn = pygame.Rect(850, 646, 118, 38)
        self.auto_btn = pygame.Rect(974, 646, 70, 38)
        self.bar = pygame.Rect(330, 690, 330, 18)
        self.popup = pygame.Rect(330, 392, 440, 236)
        self.pat_rects = [pygame.Rect(self.popup.x + 14 + (i % 2) * 208, self.popup.y + 50 + (i // 2) * 40, 200, 34)
                          for i in range(len(PATTERNS))]
        self.param_minus = pygame.Rect(self.popup.x + 150, self.popup.bottom - 52, 40, 34)
        self.param_plus = pygame.Rect(self.popup.x + 300, self.popup.bottom - 52, 40, 34)

    @property
    def focused(self) -> bool:
        return self._focused

    @focused.setter
    def focused(self, value: bool) -> None:
        if value == self._focused:
            return
        self._focused = value
        self.dragging = False
        if value:
            self.anchor = None
        try:  # held keys repeat only while typing (otherwise Space/P would auto-repeat as game hotkeys)
            pygame.key.set_repeat(350, 35) if value else pygame.key.set_repeat()
        except pygame.error:
            pass

    def set_touch(self, on: bool) -> None:
        """Taller buttons for fingers (rects from data/touch.py) or the original mouse sizes."""
        self.touch = on
        if on:
            c = GRAPH_TOUCH
            self.input, self.fire_btn, self.dir_btn = pygame.Rect(*c["input"]), pygame.Rect(*c["fire_btn"]), pygame.Rect(*c["dir_btn"])
            self.pat_btn, self.bar = pygame.Rect(*c["pat_btn"]), pygame.Rect(*c["bar"])
            self.auto_btn = pygame.Rect(*c["auto_btn"])
        else:
            self.input, self.fire_btn, self.dir_btn = pygame.Rect(330, 648, 330, 34), pygame.Rect(668, 646, 96, 38), pygame.Rect(772, 646, 70, 38)
            self.pat_btn, self.bar = pygame.Rect(850, 646, 118, 38), pygame.Rect(330, 690, 330, 18)
            self.auto_btn = pygame.Rect(974, 646, 70, 38)

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
            return ("g_focus", pos[0])
        if self.fire_btn.collidepoint(pos):
            return ("g_fire",)
        if self.dir_btn.collidepoint(pos):
            return ("g_dir", -1 if pos[0] < self.dir_btn.centerx else 1)
        if bima.graph_tier(t) >= 3 and self.pat_btn.collidepoint(pos):
            return ("g_patterns",)
        if self.auto_btn.collidepoint(pos):
            return ("g_auto",)
        return None

    def do(self, action, game) -> None:
        t = game.selected
        name = action[0]
        if name == "g_focus":
            self.focused = True
            if not self.touch and len(action) > 1:
                self._mouse_down(t, action[1])
        elif name == "g_fire":
            self.focused = False
            bima.fire_graph(game, t)
        elif name == "g_auto":                      # aim at the first Didit in reach and fire, no typing
            self.focused = False
            if not bima.auto_aim(game, t):
                game.fx.invalid()
                game.flash("No Didit inside the graph's reach to aim at", 1.6)
            else:
                self.cur, self.anchor = len(t.formula), None
                bima.fire_graph(game, t)
        elif name == "g_dir":
            t.graph_dir = action[1]
        elif name == "g_patterns":
            self.pattern_open = not self.pattern_open
        elif name == "g_pattern":
            self.cur, self.anchor = len(t.formula) + 99, None   # clamped to the new text on the next frame
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

    # ------------------------------------------------------------- editing
    MAX_LEN = 80

    def _norm(self, t) -> None:
        n = len(t.formula)
        self.cur = max(0, min(self.cur, n))
        if self.anchor is not None:
            self.anchor = max(0, min(self.anchor, n))
            if self.anchor == self.cur:
                self.anchor = None

    def _sel(self) -> tuple[int, int] | None:
        if self.anchor is None or self.anchor == self.cur:
            return None
        return (min(self.anchor, self.cur), max(self.anchor, self.cur))

    def _delete_sel(self, t) -> bool:
        sel = self._sel()
        if sel is None:
            return False
        t.formula = t.formula[:sel[0]] + t.formula[sel[1]:]
        self.cur, self.anchor = sel[0], None
        return True

    def _insert(self, t, text: str) -> None:
        self._delete_sel(t)
        text = "".join(ch for ch in text if ch.isprintable())[: max(0, self.MAX_LEN - len(t.formula))]
        t.formula = t.formula[:self.cur] + text + t.formula[self.cur:]
        self.cur += len(text)

    def _copy(self, t) -> None:
        sel = self._sel()
        txt = t.formula[sel[0]:sel[1]] if sel else t.formula
        self._clip = txt
        try:
            import pygame.scrap as scrap
            if not scrap.get_init():
                scrap.init()
            scrap.put_text(txt)
        except Exception:
            pass

    def _paste_text(self) -> str:
        try:
            import pygame.scrap as scrap
            if not scrap.get_init():
                scrap.init()
            got = scrap.get_text()
            if got:
                return got.replace("\n", " ").replace("\r", "")
        except Exception:
            pass
        return self._clip

    def _index_at(self, t, x: int) -> int:
        """Caret index nearest to screen x (the text may be scrolled)."""
        from game.utils import get_font
        font = get_font(24)
        rel = x - (self.input.x + 10) + self._scroll
        best, best_d = 0, 1e9
        for i in range(len(t.formula) + 1):
            d = abs(font.size(t.formula[:i])[0] - rel)
            if d < best_d:
                best, best_d = i, d
        return best

    _scroll = 0

    def _mouse_down(self, t, x: int) -> None:
        now = pygame.time.get_ticks()
        if now - self._last_click < 350:           # double click = select everything
            self.anchor, self.cur = 0, len(t.formula)
            self.dragging = False
        else:
            self.cur, self.anchor = self._index_at(t, x), None
            self.anchor = self.cur
            self.dragging = True
        self._last_click = now

    def drag(self, pos, game) -> None:
        """Mouse moved with the button down inside the box: extend the selection."""
        t = game.selected
        if self.dragging and t is not None:
            self.cur = self._index_at(t, pos[0])
            self._norm(t)

    def release(self) -> None:
        self.dragging = False

    def key(self, event, game) -> bool:
        """Typing with a real caret: arrows / Home / End, Shift+arrows select, Ctrl+A/C/X/V, Delete. True = consumed."""
        t = game.selected
        if t is None or not self.focused:
            return False
        self._norm(t)
        k, mod = event.key, event.mod
        ctrl, shift = bool(mod & pygame.KMOD_CTRL), bool(mod & pygame.KMOD_SHIFT)
        if k in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.focused = False
            bima.fire_graph(game, t)
        elif k == pygame.K_ESCAPE:
            self.focused = False
        elif ctrl and k == pygame.K_a:
            self.anchor, self.cur = 0, len(t.formula)
        elif ctrl and k in (pygame.K_c, pygame.K_x):
            self._copy(t)
            if k == pygame.K_x:
                if not self._delete_sel(t):
                    t.formula, self.cur = "", 0
        elif ctrl and k == pygame.K_v:
            self._insert(t, self._paste_text())
        elif k in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_HOME, pygame.K_END):
            if shift and self.anchor is None:
                self.anchor = self.cur
            sel = self._sel()
            if k == pygame.K_LEFT:
                self.cur = (sel[0] if sel and not shift else max(0, self.cur - 1))
            elif k == pygame.K_RIGHT:
                self.cur = (sel[1] if sel and not shift else min(len(t.formula), self.cur + 1))
            elif k == pygame.K_HOME:
                self.cur = 0
            else:
                self.cur = len(t.formula)
            if not shift:
                self.anchor = None
        elif k == pygame.K_BACKSPACE:
            if not self._delete_sel(t) and self.cur > 0:
                t.formula = t.formula[:self.cur - 1] + t.formula[self.cur:]
                self.cur -= 1
        elif k == pygame.K_DELETE:
            if not self._delete_sel(t):
                t.formula = t.formula[:self.cur] + t.formula[self.cur + 1:]
        elif event.unicode and event.unicode.isprintable() and not ctrl:
            self._insert(t, event.unicode)
        self._norm(t)
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
        self._norm(t)
        from game.utils import get_font
        font = get_font(24)
        inner = pygame.Rect(self.input.x + 10, self.input.y + 3, self.input.w - 20, self.input.h - 6)
        caret_x = font.size(txt[:self.cur])[0]
        if caret_x - self._scroll > inner.w:        # keep the caret inside the box
            self._scroll = caret_x - inner.w
        elif caret_x - self._scroll < 0:
            self._scroll = caret_x
        self._scroll = max(0, min(self._scroll, max(0, font.size(txt)[0] - inner.w + 4)))
        old_clip = surface.get_clip()
        surface.set_clip(inner)
        sel = self._sel()
        if sel and self.focused:
            x0 = inner.x + font.size(txt[:sel[0]])[0] - self._scroll
            x1 = inner.x + font.size(txt[:sel[1]])[0] - self._scroll
            pygame.draw.rect(surface, (120, 180, 255), (x0, inner.y + 1, x1 - x0, inner.h - 2), border_radius=3)
        if txt:
            img = font.render(txt, True, (30, 24, 40))
            surface.blit(img, img.get_rect(midleft=(inner.x - self._scroll, self.input.centery)))
        if self.focused and (pygame.time.get_ticks() // 450) % 2 == 0:
            cx = inner.x + caret_x - self._scroll
            pygame.draw.line(surface, (30, 24, 40), (cx, inner.y + 2), (cx, inner.bottom - 2), 2)
        surface.set_clip(old_clip)
        if not txt and not self.focused:
            hint = get_font(20).render(("tap to type, e.g.  2x   or   x^2/10" if self.touch else "click and type, e.g.  2x   or   x^2/10"), True, (150, 144, 160))
            surface.blit(hint, hint.get_rect(midleft=(self.input.x + 10, self.input.centery)))
        # fire / direction / patterns
        ready = bima.can_fire_now(game, t)
        self._btn(surface, self.fire_btn, COLORS["btn_orange"], game, ready)
        draw_outlined(surface, "FIRE", self.fire_btn.center, 24, center=True, width=2)
        pygame.draw.rect(surface, (20, 14, 30), self.dir_btn.inflate(4, 4), border_radius=10)
        for i, d in enumerate((-1, 1)):
            half = pygame.Rect(self.dir_btn.x + i * self.dir_btn.w // 2, self.dir_btn.y, self.dir_btn.w // 2, self.dir_btn.h)
            on = t.graph_dir == d
            pygame.draw.rect(surface, (255, 190, 80) if on else (70, 64, 90), half.inflate(-2, -2), border_radius=8)
            cx, cy = half.center
            pygame.draw.polygon(surface, (255, 255, 255) if on else (170, 166, 190),
                                [(cx - 6 * d, cy - 8), (cx - 6 * d, cy + 8), (cx + 7 * d, cy)])
        self._btn(surface, self.auto_btn, COLORS["btn_green"], game, True)
        draw_outlined(surface, "AUTO", self.auto_btn.center, 20, center=True, width=2)
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
