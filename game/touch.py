"""Phone / tablet controls. The browser turns a tap into a mouse click, so the whole game already receives taps;
this module adds what a finger needs on top of that:

* tap or drag on the map moves a placement ghost, round OK / cancel buttons confirm (no accidental towers),
  the same for aimed abilities (Bima cube / sphere);
* a math keypad for Bima's formula box (there is no keyboard);
* "tap to resume" after pause, a PLAY AGAIN button on the end screen;
* mouse_pos is parked off-screen when no finger is down, so nothing stays "hovered".

Touch mode switches on by itself (first touch event, or a coarse pointer in the browser) and a real mouse click
switches it off again on hybrid laptops. All numbers: data/touch.py. Desktop behaviour is untouched.
"""
from __future__ import annotations

import math

import pygame

from data.bima import GRAPH
from data.settings import BAR_RECT, BUILD_RECT, COLORS, SCREEN_W
from data.touch import (AGAIN_RECT, CONFIRM_SIZE, KEY_FLASH_SECONDS, KEYPAD_COLS, KEYPAD_GAP, KEYPAD_PAD,
                        KEYPAD_RECT, TOUCH_DRAG_START, TOUCH_GHOST_LIFT, TOUCH_PICK_BONUS)
from data.towers import TOWERS
from game import bima, gfx, web
from game.formula import FUNCS
from game.utils import draw_outlined

OFFSCREEN = (-1000, -1000)
GOLD = COLORS["gold"]

# Keypad rows: (label, text, kind, columns). kind: ins | fn | back | clr | done
KEY_ROWS = [
    [("7", "7", "ins", 1), ("8", "8", "ins", 1), ("9", "9", "ins", 1), ("(", "(", "ins", 1), (")", ")", "ins", 1),
     ("^", "^", "ins", 1), ("sin", "sin(", "fn", 1), ("cos", "cos(", "fn", 1)],
    [("4", "4", "ins", 1), ("5", "5", "ins", 1), ("6", "6", "ins", 1), ("*", "*", "ins", 1), ("/", "/", "ins", 1),
     ("x", "x", "ins", 1), ("tan", "tan(", "fn", 1), ("ln", "ln(", "fn", 1)],
    [("1", "1", "ins", 1), ("2", "2", "ins", 1), ("3", "3", "ins", 1), ("+", "+", "ins", 1), ("-", "-", "ins", 1),
     ("pi", "pi", "ins", 1), ("abs", "abs(", "fn", 1), ("sqrt", "sqrt(", "fn", 1)],
    [("0", "0", "ins", 1), (".", ".", "ins", 1), ("exp", "exp(", "fn", 1), ("DEL", "", "back", 1),
     ("CLR", "", "clr", 1), ("DONE", "", "done", 3)],
]
MAX_FORMULA = 80   # same limit as typing (bima_ui.GraphConsole.key)


def key_layout(rect: pygame.Rect) -> list[tuple[pygame.Rect, str, str, str]]:
    """(rect, label, text, kind) for every keypad key inside `rect`."""
    inner = rect.inflate(-2 * KEYPAD_PAD, -2 * KEYPAD_PAD)
    cw = (inner.w - (KEYPAD_COLS - 1) * KEYPAD_GAP) / KEYPAD_COLS
    ch = (inner.h - (len(KEY_ROWS) - 1) * KEYPAD_GAP) / len(KEY_ROWS)
    out = []
    for r, row in enumerate(KEY_ROWS):
        c = 0
        for label, text, kind, span in row:
            x = inner.x + c * (cw + KEYPAD_GAP)
            w = span * cw + (span - 1) * KEYPAD_GAP
            out.append((pygame.Rect(round(x), round(inner.y + r * (ch + KEYPAD_GAP)), round(w), round(ch)), label, text, kind))
            c += span
    return out


def apply_key(formula: str, text: str, kind: str) -> str:
    """New formula text after pressing a key (pure function, easy to test)."""
    if kind == "back":
        return formula[:-1]
    if kind == "clr":
        return ""
    if kind in ("ins", "fn"):
        return formula if len(formula) + len(text) > MAX_FORMULA else formula + text
    return formula


def confirm_rects(ghost, size: int = CONFIRM_SIZE) -> tuple[pygame.Rect, pygame.Rect]:
    """(cancel, ok) buttons above the ghost (below it when the ghost is near the top), kept clear of the bar."""
    gx, gy = ghost
    top = gy - 62 - size
    y = top if top >= 90 else gy + 62
    y = min(y, BAR_RECT[1] - size - 10)
    x = max(size + 10, min(SCREEN_W - size - 10, gx))
    return pygame.Rect(x - size - 6, y, size, size), pygame.Rect(x + 6, y, size, size)


class Touch:
    def __init__(self, game) -> None:
        self.game = game
        self.coarse = web.is_coarse_pointer()
        self.enabled = self.coarse
        self.down = False
        self.finger = OFFSCREEN
        self.origin = OFFSCREEN
        self.dragging = False
        self.map_press = False      # this press started on the map while placing / aiming: it moves the ghost
        self.card_drag = False      # this press started on a tower card: dragging it onto the map moves the ghost
        self.ghost: tuple[int, int] | None = None
        self.flash_key: tuple[str, float] | None = None
        self.keypad = pygame.Rect(*KEYPAD_RECT)
        self.keys = key_layout(self.keypad)
        self.again = pygame.Rect(*AGAIN_RECT)
        self._set_layout()

    # ------------------------------------------------------------ mode
    def _set_layout(self) -> None:
        self.game.ui.set_touch(self.enabled)

    def set_enabled(self, on: bool) -> None:
        if on != self.enabled:
            self.enabled = on
            self.down = self.map_press = self.card_drag = False
            self.ghost = None
            self._set_layout()

    # ----------------------------------------------------------- queries
    @property
    def playing(self) -> bool:
        return self.game.state.value == "playing"

    def pending(self) -> bool:
        """A placement or an aimed ability is waiting for the OK button."""
        return self.game.placing is not None or self.game.aiming is not None

    def keypad_open(self) -> bool:
        g = self.game
        return self.enabled and self.playing and not g.options_open and g.ui.graph.focused and g.ui.graph.visible(g)

    def pick_bonus(self) -> int:
        return TOUCH_PICK_BONUS if self.enabled else 0

    def hint(self) -> str:
        g = self.game
        if g.aiming is not None:
            return "Drag / tap the map to aim, then press OK" if self.ghost else "Tap the map to aim"
        if g.placing is not None:
            d = TOWERS[g.placing]
            if self.ghost is None:
                return f"{d['name']} (${d['cost']}): tap the map to place"
            return "Drag to adjust, then press OK"
        return "Tap a tower to upgrade it"

    # ------------------------------------------------------------ events
    def handle_event(self, e) -> bool:
        """Called first for every event. Returns True when the event was fully handled here."""
        t = e.type
        if t in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
            self.set_enabled(True)
            return False
        if t not in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
            return False
        if getattr(e, "touch", False):
            self.set_enabled(True)
        elif self.enabled and not self.coarse and t == pygame.MOUSEBUTTONDOWN:
            self.set_enabled(False)   # a real mouse on a hybrid laptop: back to the normal controls
        if not self.enabled:
            return False
        if t == pygame.MOUSEMOTION:
            self._on_move(e.pos)
            return True
        if e.button != 1:
            return True
        if t == pygame.MOUSEBUTTONUP:
            self.down = self.map_press = self.card_drag = self.dragging = False
            return True
        self.down, self.finger, self.origin, self.dragging = True, e.pos, e.pos, False
        return self._on_down(e.pos)

    def _on_down(self, pos) -> bool:
        g = self.game
        if not self.playing:
            if self.again.collidepoint(pos):
                g.fx.click()
                g.reset()
            return True
        if g.paused:
            g.paused = False   # any tap resumes
            return True
        if self.keypad_open() and self.keypad.collidepoint(pos):
            self._press_key(pos)
            return True
        if self.pending() and self.ghost is not None and not g.options_open:
            cancel, ok = confirm_rects(self.ghost)
            if ok.collidepoint(pos):
                self._confirm()
                return True
            if cancel.collidepoint(pos):
                g.fx.click()
                g.placing = None
                g.aiming = None
                return True
        action = g.ui.hit_test(pos, g)
        self.card_drag = action is not None and action[0] == "shop"
        return False   # Game handles the rest (buttons, selecting towers, ghost via set_ghost)

    def _on_move(self, pos) -> None:
        self.finger = pos
        if not self.down:
            return
        g = self.game
        if self.card_drag and g.placing is not None and g.build_rect.collidepoint(pos):
            self.map_press = True   # dragged a card onto the map
        if not self.map_press:
            return
        if not self.dragging and math.hypot(pos[0] - self.origin[0], pos[1] - self.origin[1]) >= TOUCH_DRAG_START:
            self.dragging = True
        lift = TOUCH_GHOST_LIFT if self.dragging else 0
        self._put_ghost((pos[0], pos[1] - lift))

    def _put_ghost(self, pos) -> None:
        b = BUILD_RECT
        self.ghost = (max(b[0], min(b[0] + b[2], int(pos[0]))), max(b[1], min(b[1] + b[3], int(pos[1]))))

    def set_ghost(self, pos) -> None:
        """Called by Game when a tap on the empty map arrives while placing / aiming."""
        self.map_press = True
        self._put_ghost(pos)

    def _confirm(self) -> None:
        g = self.game
        if self.ghost is None:
            return
        if g.aiming is not None:
            from game import actives
            tower, aid = g.aiming
            if actives.use(g, tower, aid, self.ghost):
                g.aiming = None
        elif g.placing is not None:
            g._try_place(self.ghost)   # flashes the reason when the spot is invalid

    def _press_key(self, pos) -> None:
        g = self.game
        t = g.selected
        for rect, label, text, kind in self.keys:
            if not rect.collidepoint(pos):
                continue
            if kind == "fn":
                need = FUNCS[label][2]
                if need > GRAPH["func_level"][bima.graph_tier(t)]:
                    g.flash(f"{label} unlocks at Graph tier {need}", 1.6)
                    g.fx.invalid()
                    return
            g.fx.click()
            self.flash_key = (label, KEY_FLASH_SECONDS)
            if kind == "done":
                g.ui.graph.focused = False
            else:
                t.formula = apply_key(t.formula, text, kind)
            return

    # ------------------------------------------------------------ frame
    def update(self, dt: float) -> None:
        if not self.enabled:
            return
        g = self.game
        if not self.pending():
            self.ghost = None
        if self.flash_key:
            name, left = self.flash_key
            self.flash_key = (name, left - dt) if left - dt > 0 else None
        if self.ghost is not None:
            g.mouse_pos = self.ghost
        elif self.down:
            g.mouse_pos = self.finger
        else:
            g.mouse_pos = OFFSCREEN

    def draw(self, s: pygame.Surface) -> None:
        if not self.enabled:
            return
        g = self.game
        if not self.playing:
            self._draw_again(s)
            return
        if g.options_open or g.paused:
            return
        if self.pending() and self.ghost is not None:
            self._draw_confirm(s)
        if self.keypad_open():
            self._draw_keypad(s)

    # ----------------------------------------------------------- drawing
    def _draw_confirm(self, s: pygame.Surface) -> None:
        g = self.game
        cancel, ok = confirm_rects(self.ghost)
        if g.placing is not None:
            valid = g.placement_check(g.placing, self.ghost)[0]
        else:
            valid = True
        for rect, good, enabled in ((cancel, False, True), (ok, True, valid)):
            col = (92, 96, 108) if not enabled else COLORS["btn_green"] if good else COLORS["btn_red"]
            c = rect.center
            pygame.draw.circle(s, (20, 14, 12), c, rect.w // 2 + 4)
            pygame.draw.circle(s, col, c, rect.w // 2)
            pygame.draw.circle(s, (255, 255, 255), c, rect.w // 2, 4)
            pygame.draw.circle(s, gfx.tint(col, 0.35), (c[0], c[1] - rect.h // 6), rect.w // 3)
            if good:
                pts = [(c[0] - 18, c[1] + 1), (c[0] - 5, c[1] + 15), (c[0] + 20, c[1] - 14)]
                pygame.draw.lines(s, (255, 255, 255), False, pts, 9)
            else:
                pygame.draw.line(s, (255, 255, 255), (c[0] - 15, c[1] - 15), (c[0] + 15, c[1] + 15), 9)
                pygame.draw.line(s, (255, 255, 255), (c[0] - 15, c[1] + 15), (c[0] + 15, c[1] - 15), 9)

    def _draw_keypad(self, s: pygame.Surface) -> None:
        g = self.game
        t = g.selected
        level = GRAPH["func_level"][bima.graph_tier(t)]
        r = self.keypad
        s.blit(gfx.panel_surface(r.w, r.h, 14), (r.x - 2, r.y - 2))
        lit = self.flash_key[0] if self.flash_key else None
        for rect, label, text, kind in self.keys:
            locked = kind == "fn" and FUNCS[label][2] > level
            base = ((255, 160, 30) if kind == "done" else (225, 70, 60) if kind in ("back", "clr")
                    else (70, 150, 232) if kind == "fn" else (88, 98, 128) if label.isdigit() or label == "." else (112, 84, 170))
            state = "off" if locked else "pressed" if lit == label else "normal"
            s.blit(gfx.glossy(rect.w, rect.h, base, 10, (255, 255, 255), state), (rect.x - 1, rect.y - 1))
            size = 30 if len(label) == 1 else 24 if len(label) <= 3 else 21
            draw_outlined(s, label, rect.center, size, (255, 255, 255) if not locked else (190, 192, 200), center=True, width=2)

    def _draw_again(self, s: pygame.Surface) -> None:
        r = self.again
        s.blit(gfx.glossy(r.w, r.h, COLORS["btn_green"], 16, (255, 255, 255), "pressed" if self.down else "normal"), (r.x - 1, r.y - 1))
        draw_outlined(s, "PLAY AGAIN", r.center, 36, (255, 255, 255), center=True, width=3)
