"""DiditCode: Romli's preparation-phase ability. A short code snippet with ONE buggy line.

Step 1 (FIND): click the line with the bug. Step 2 (FIX): pick the right replacement line (3 options, shuffled).
A wrong line or a wrong fix is a strike; DIDITCODE_STRIKES strikes and the attempt fails. Solving it pays $ (the
in-run money). The overlay is modal: the game does not advance while it is open. Puzzles: data/diditcode.py.

DiditCode(wave, rng).click(pos) / .key(key) return one of: None | "solved" | "failed" | "close" | "cancel".
Game (game/game.py) reacts: pays the reward on "solved", closes the overlay on "close" / "cancel".
"""
from __future__ import annotations

import random

import pygame

from data.diditcode import PUZZLES
from data.settings import COLORS, DIDITCODE_REWARD_BASE, DIDITCODE_REWARD_PER_WAVE, DIDITCODE_STRIKES
from game import gfx
from game.utils import draw_outlined, get_font, wrap_text

PANEL = pygame.Rect(110, 56, 1060, 608)
EDITOR = pygame.Rect(140, 178, 1000, 290)
ROW_H = 30
CANCEL = pygame.Rect(PANEL.right - 170, PANEL.y + 14, 150, 44)
DONE = pygame.Rect(PANEL.centerx - 130, PANEL.bottom - 74, 260, 56)
OPT_RECTS = [pygame.Rect(140, 480 + i * 56, 1000, 48) for i in range(3)]
GOOD, BAD, WARN = (110, 235, 130), (255, 110, 100), (255, 190, 60)
_CODE_FONTS: dict[int, pygame.font.Font] = {}


def reward_for(wave_number: int) -> int:
    """$ for solving it before wave `wave_number`."""
    return DIDITCODE_REWARD_BASE + DIDITCODE_REWARD_PER_WAVE * max(1, wave_number)


def _code_font(size: int) -> pygame.font.Font:
    if size not in _CODE_FONTS:
        try:
            _CODE_FONTS[size] = pygame.font.SysFont("dejavusansmono,couriernew,consolas,menlo,monospace", size)
        except Exception:   # no system fonts (browser build): use the game font
            _CODE_FONTS[size] = get_font(size)
    return _CODE_FONTS[size]


class DiditCode:
    def __init__(self, wave_number: int, rng: random.Random | None = None, puzzle: dict | None = None) -> None:
        rng = rng or random.Random()
        src = puzzle or rng.choice(PUZZLES)
        self.title, self.lang, self.code, self.bug, self.why = src["title"], src["lang"], list(src["code"]), src["bug"], src["why"]
        self.options = list(src["options"])
        self.fix = self.options[0]                 # the first option is the correct one ...
        rng.shuffle(self.options)                  # ... then they are shuffled
        self.reward = reward_for(wave_number)
        self.stage = "find"                        # find | fix | won | lost
        self.strikes = 0
        self.bad_lines: set[int] = set()
        self.bad_options: set[int] = set()
        self.touched = False                       # any click made yet (a cancel before that is free)
        self.mouse = (0, 0)
        self.t = 0.0

    @property
    def finished(self) -> bool:
        return self.stage in ("won", "lost")

    @property
    def strikes_left(self) -> int:
        return DIDITCODE_STRIKES - self.strikes

    # ------------------------------------------------------------------ input
    def key(self, key: int) -> str | None:
        if key in (pygame.K_ESCAPE,):
            return "close" if self.finished else "cancel"
        if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE) and self.finished:
            return "close"
        return None

    def _strike(self) -> str | None:
        self.strikes += 1
        if self.strikes >= DIDITCODE_STRIKES:
            self.stage = "lost"
            return "failed"
        return None

    def click(self, pos) -> str | None:
        if self.finished:
            return "close" if DONE.collidepoint(pos) else None
        if CANCEL.collidepoint(pos):
            return "cancel"
        if self.stage == "find":
            for i in range(len(self.code)):
                if self._row(i).collidepoint(pos) and i not in self.bad_lines:
                    self.touched = True
                    if i == self.bug:
                        self.stage = "fix"
                        return None
                    self.bad_lines.add(i)
                    return self._strike() or "wrong"
        elif self.stage == "fix":
            for i, rect in enumerate(OPT_RECTS[:len(self.options)]):
                if rect.collidepoint(pos) and i not in self.bad_options:
                    self.touched = True
                    if self.options[i] == self.fix:
                        self.stage = "won"
                        return "solved"
                    self.bad_options.add(i)
                    return self._strike() or "wrong"
        return None

    @staticmethod
    def _row(i: int) -> pygame.Rect:
        return pygame.Rect(EDITOR.x + 6, EDITOR.y + 44 + i * ROW_H, EDITOR.w - 12, ROW_H - 2)

    # ------------------------------------------------------------------- draw
    def draw(self, screen: pygame.Surface, mouse) -> None:
        self.mouse = mouse
        self.t += 1 / 60
        dim = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        dim.fill((8, 8, 18, 190))
        screen.blit(dim, (0, 0))
        screen.blit(gfx.panel_surface(PANEL.w, PANEL.h), (PANEL.x - 2, PANEL.y - 2))
        screen.blit(gfx.icon("code", 52), (PANEL.x + 22, PANEL.y + 14))
        draw_outlined(screen, "DIDITCODE", (PANEL.x + 84, PANEL.y + 40), 40, (120, 255, 150), anchor="midleft", width=4)
        draw_outlined(screen, f"{self.lang}: {self.title}", (PANEL.x + 330, PANEL.y + 40), 26, (255, 255, 255), anchor="midleft", width=3)
        self._draw_hearts(screen)
        step = {"find": "Step 1: click the line that contains the bug",
                "fix": f"Step 2: pick the right fix for line {self.bug + 1}",
                "won": "Bug fixed!", "lost": "Out of strikes"}[self.stage]
        col = GOOD if self.stage == "won" else BAD if self.stage == "lost" else (255, 224, 150)
        draw_outlined(screen, step, (PANEL.x + 30, PANEL.y + 96), 28, col, anchor="midleft", width=3)
        self._draw_editor(screen)
        if self.stage == "fix":
            self._draw_options(screen)
        elif self.finished:
            self._draw_result(screen)
        else:
            draw_outlined(screen, "Wrong picks cost a strike. Cancel is free until you click something.",
                          (PANEL.centerx, 520), 20, (200, 215, 240), center=True, width=2)
        if not self.finished:
            hover = CANCEL.collidepoint(mouse)
            screen.blit(gfx.glossy(CANCEL.w, CANCEL.h, COLORS["btn_red"], 12, (255, 255, 255), "hover" if hover else "normal"), (CANCEL.x - 1, CANCEL.y - 1))
            draw_outlined(screen, "CANCEL", CANCEL.center, 24, (255, 255, 255), center=True, width=3)

    def _draw_hearts(self, screen: pygame.Surface) -> None:
        x = PANEL.right - 340
        for i in range(DIDITCODE_STRIKES):
            ic = gfx.icon("heart", 34)
            if i >= self.strikes_left:
                ic = ic.copy()
                ic.fill((70, 70, 70, 255), special_flags=pygame.BLEND_RGBA_MULT)
            screen.blit(ic, (x + i * 40, PANEL.y + 79))
        draw_outlined(screen, f"Reward: ${self.reward}", (PANEL.right - 36, PANEL.y + 96), 28, COLORS["gold"], anchor="midright", width=3)

    def _draw_editor(self, screen: pygame.Surface) -> None:
        pygame.draw.rect(screen, (14, 16, 26), EDITOR.inflate(8, 8), border_radius=12)
        pygame.draw.rect(screen, (24, 28, 42), EDITOR, border_radius=10)
        for i, c in enumerate(((255, 95, 90), (255, 200, 60), (90, 210, 100))):   # window dots
            pygame.draw.circle(screen, c, (EDITOR.x + 20 + i * 22, EDITOR.y + 20), 7)
        draw_outlined(screen, f"{self.lang.lower()} snippet", (EDITOR.right - 16, EDITOR.y + 20), 16, (150, 160, 190), anchor="midright", width=0)
        font = _code_font(20)
        for i, line in enumerate(self.code):
            r = self._row(i)
            hover = self.stage == "find" and r.collidepoint(self.mouse) and i not in self.bad_lines
            if i in self.bad_lines:
                pygame.draw.rect(screen, (110, 40, 44), r, border_radius=6)
            elif self.stage == "lost" and i == self.bug:
                pygame.draw.rect(screen, (40, 100, 56), r, border_radius=6)
            elif self.stage in ("fix", "won") and i == self.bug:
                pygame.draw.rect(screen, (120, 84, 24) if self.stage == "fix" else (40, 100, 56), r, border_radius=6)
                pygame.draw.rect(screen, WARN if self.stage == "fix" else GOOD, r, 2, border_radius=6)
            elif hover:
                pygame.draw.rect(screen, (50, 64, 104), r, border_radius=6)
            text = self.fix if (self.stage == "won" and i == self.bug) else line
            if self.stage == "won" and i == self.bug:   # keep the indent of the original line
                text = line[:len(line) - len(line.lstrip())] + self.fix
            comment = line.lstrip().startswith(("#", "//"))
            color = (130, 150, 130) if comment else (232, 236, 250)
            num = font.render(f"{i + 1:>2}", True, (110, 120, 150))
            screen.blit(num, num.get_rect(midleft=(r.x + 10, r.centery)))
            img = font.render(text.replace("\t", "    "), True, color)
            screen.blit(img, img.get_rect(midleft=(r.x + 56, r.centery)))

    def _draw_options(self, screen: pygame.Surface) -> None:
        font = _code_font(21)
        for i, (rect, text) in enumerate(zip(OPT_RECTS, self.options)):
            dead = i in self.bad_options
            hover = rect.collidepoint(self.mouse) and not dead
            base = (110, 60, 60) if dead else (70, 150, 230) if hover else (46, 88, 150)
            screen.blit(gfx.glossy(rect.w, rect.h, base, 12, (255, 255, 255), "off" if dead else "hover" if hover else "normal"), (rect.x - 1, rect.y - 1))
            draw_outlined(screen, "ABC"[i], (rect.x + 26, rect.centery), 26, (255, 255, 255), center=True, width=3)
            img = font.render(text, True, (255, 255, 255) if not dead else (200, 170, 170))
            screen.blit(img, img.get_rect(midleft=(rect.x + 60, rect.centery)))

    def _draw_result(self, screen: pygame.Surface) -> None:
        won = self.stage == "won"
        draw_outlined(screen, f"+${self.reward}" if won else "No reward this time", (PANEL.centerx, 500), 44,
                      GOOD if won else BAD, center=True, width=4)
        for k, line in enumerate(wrap_text(self.why, 22, PANEL.w - 120)[:2]):
            draw_outlined(screen, line, (PANEL.centerx, 548 + k * 26), 22, (255, 255, 255), center=True, width=2)
        hover = DONE.collidepoint(self.mouse)
        screen.blit(gfx.glossy(DONE.w, DONE.h, COLORS["btn_green"], 14, (255, 255, 255), "hover" if hover else "normal"), (DONE.x - 1, DONE.y - 1))
        draw_outlined(screen, "CONTINUE", DONE.center, 30, (255, 255, 255), center=True, width=3)
