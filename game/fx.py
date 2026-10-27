"""FX: turns game events into sound + visuals. Game calls these; no game logic in here."""
from __future__ import annotations

import random

import pygame

from data.settings import WORLD_CENTER
from game.audio import Audio
from game.vfx import VFX

GOLD = (255, 215, 80)
CYAN = (120, 200, 230)
SPARK = (255, 240, 180)
COMIC_COLORS = [(255, 230, 60), (255, 130, 60), (120, 220, 255), (255, 100, 150), (160, 255, 120)]
HIT_WORDS = ["POW!", "BAM!", "WHAM!", "BONK!", "THWACK!"]
COMIC_GAP = 0.35  # seconds between random hit words so the screen stays readable


class FX:
    def __init__(self) -> None:
        self.audio = Audio()
        self.vfx = VFX()
        self._comic_cd = 0.0

    def reset(self) -> None:
        self.vfx.clear()

    def update(self, dt: float) -> None:
        self.vfx.update(dt)
        self._comic_cd -= dt

    def _hit_word(self, pos, chance: float) -> None:
        if self._comic_cd <= 0 and random.random() < chance:
            self._comic_cd = COMIC_GAP
            self.vfx.comic(pos + pygame.Vector2(0, -18), random.choice(HIT_WORDS),
                           random.choice(COMIC_COLORS), 30)

    # ----------------------------------------------------------------- UI
    def click(self) -> None:
        self.audio.play("click")

    def invalid(self) -> None:
        self.audio.play("error")

    def tick(self) -> None:
        self.audio.play("tick")

    def hover(self) -> None:
        self.audio.play("hover")

    def select(self, tower) -> None:
        self.audio.play("select")
        self.vfx.ring(tower.pos, 8, 30, 0.2, (255, 255, 255), 2)

    # ------------------------------------------------------------- towers
    def placed(self, tower) -> None:
        self.audio.play("place")
        self.vfx.ring(tower.pos, 6, 44, 0.3, tower.color, 4)
        self.vfx.burst(tower.pos, (170, 140, 90), 12, 90, 0.4, 4, 40)

    def upgraded(self, tower, name: str, tier: int) -> None:
        self.audio.play("upgrade")
        self.vfx.ring(tower.pos, 10, 56, 0.4, GOLD, 4)
        self.vfx.sparkle(tower.pos, GOLD, 16)
        self.vfx.text(tower.pos + pygame.Vector2(0, -34), name, (255, 255, 255), 22, 1.2, 30)
        if tier >= 4:
            self.vfx.comic(tower.pos + pygame.Vector2(0, -60), "ULTIMATE!", (255, 100, 150), 40, 1.0)
            self.vfx.shake(4, 0.25)

    def sold(self, tower, value: int) -> None:
        self.audio.play("sell")
        self.vfx.burst(tower.pos, GOLD, 14, 140, 0.5, 4, 200)
        self.vfx.text(tower.pos, f"+${value}", GOLD, 26, 1.0, 40)

    def fired(self, tower) -> None:
        self.audio.play(f"shoot_{tower.kind}")
        self.vfx.ring(tower.pos, 10, 26, 0.12, (255, 255, 255), 2)

    def trail(self, proj) -> None:
        if random.random() < 0.7:
            self.vfx.trail(proj.pos, proj.color)

    def knowledge(self, tower) -> None:
        self.audio.play("knowledge")
        self.vfx.text(tower.pos + pygame.Vector2(0, -28), "+1", CYAN, 22, 0.8, 35)

    def stack(self, tower, color) -> None:
        self.audio.play("stack")
        self.vfx.sparkle(tower.pos, color, 12)
        self.vfx.ring(tower.pos, 8, 36, 0.35, color, 3)

    # ------------------------------------------------------------ combat
    def hit(self, enemy, color) -> None:
        self.audio.play("hit")
        self.vfx.burst(enemy.pos, color, 4, 110, 0.25, 3, 0)
        self.vfx.burst(enemy.pos, SPARK, 2, 70, 0.18, 2, 0)
        self._hit_word(enemy.pos, 0.07)

    def aoe(self, pos, radius: float, color) -> None:
        self.vfx.ring(pos, radius * 0.3, radius, 0.3, color, 4)

    def zap(self, a, b) -> None:
        self.audio.play("zap")
        self.vfx.burst(b, (255, 245, 140), 6, 120, 0.2, 3, 0)
        if self._comic_cd <= 0:
            self._comic_cd = COMIC_GAP
            self.vfx.comic(pygame.Vector2(b) + pygame.Vector2(0, -20), "ZAP!", (255, 245, 100), 34)

    def pushed(self, enemy) -> None:
        self.audio.play("whoosh")
        self.vfx.burst(enemy.pos, (190, 130, 255), 10, 140, 0.35, 4, 0)
        self.vfx.ring(enemy.pos, 6, 34, 0.3, (190, 130, 255), 3)
        self.vfx.comic(enemy.pos + pygame.Vector2(0, -22), "SWOOSH!", (190, 130, 255), 28)

    def slept(self, enemy) -> None:
        self.audio.play("sleep")
        self.vfx.text(enemy.pos + pygame.Vector2(0, -26), "Zzz", (200, 220, 255), 26, 1.2, 25)

    def killed(self, enemy) -> None:
        if enemy.is_boss:
            self.audio.play("boss_die")
            self.vfx.burst(enemy.pos, enemy.color, 50, 260, 0.9, 7, 120)
            self.vfx.burst(enemy.pos, GOLD, 30, 200, 0.8, 5, 120)
            self.vfx.ring(enemy.pos, 10, 130, 0.6, (255, 255, 255), 6)
            self.vfx.comic(enemy.pos + pygame.Vector2(0, -40), "KABOOM!", (255, 120, 60), 64, 1.4)
            self.vfx.shake(9, 0.6)
        else:
            self.audio.play("pop")
            self.vfx.burst(enemy.pos, enemy.color, 10, 150, 0.45, 4, 220)
            self.vfx.ring(enemy.pos, 4, 24, 0.22, (255, 255, 255), 2)
        if enemy.gives_money:
            self.audio.play("coin")
            self.vfx.text(enemy.pos + pygame.Vector2(0, -16), f"+${enemy.bounty}", GOLD, 22, 0.9, 38)

    def trojan_opened(self, enemy, count: int) -> None:
        """Hatch bursts open: wood chips, dust ring and a comic word."""
        self.audio.play("crack")
        wood = (176, 120, 62)
        self.vfx.burst(enemy.pos, wood, 16, 190, 0.6, 5, 260)
        self.vfx.burst(enemy.pos, (120, 80, 40), 10, 140, 0.5, 4, 260)
        self.vfx.ring(enemy.pos, 6, 54 if enemy.is_boss else 38, 0.35, (240, 220, 180), 4)
        self.vfx.comic(enemy.pos + pygame.Vector2(0, -34), "CRACK!", (255, 190, 80), 44 if enemy.is_boss else 34, 0.9)
        self.vfx.text(enemy.pos + pygame.Vector2(0, -56), f"x{count}", (255, 255, 255), 26, 0.9, 30)
        if enemy.is_boss:
            self.vfx.shake(5, 0.35)

    def leaked(self, enemy, stash_pos) -> None:
        self.audio.play("leak")
        self.vfx.flash((255, 30, 30), 90, 0.4)
        self.vfx.shake(6, 0.3)
        self.vfx.burst(stash_pos, (255, 90, 90), 14, 160, 0.5, 5, 100)
        self.vfx.text(pygame.Vector2(stash_pos) + pygame.Vector2(0, -34), f"-{enemy.stash_damage}",
                      (255, 90, 90), 34, 1.1, 40)

    # ------------------------------------------------------------- waves
    def wave_started(self, number: int, boss: bool) -> None:
        self.audio.play("wave_start")
        center = pygame.Vector2(WORLD_CENTER)
        self.vfx.comic(center, "BOSS WAVE!" if boss else f"WAVE {number}!",
                       (255, 100, 100) if boss else (255, 230, 60), 72, 1.5)
        if boss:
            self.vfx.shake(5, 0.4)

    def boss_spawned(self) -> None:
        self.audio.play("boss")
        self.vfx.shake(7, 0.8)

    def wave_cleared(self) -> None:
        self.audio.play("wave_clear")
        self.audio.play("wave_money")
        self.vfx.comic(pygame.Vector2(WORLD_CENTER), "WAVE CLEARED!", (160, 255, 120), 60, 1.5)

    def income(self, tower, amount: int, sound: bool = True) -> None:
        """Romli paid out (every 10s, or his per-wave income)."""
        if sound:
            self.audio.play("income")
        self.vfx.burst(tower.pos, GOLD, 12, 120, 0.6, 4, 260)
        self.vfx.ring(tower.pos, 8, 40, 0.35, GOLD, 3)
        self.vfx.text(tower.pos + pygame.Vector2(0, -30), f"+${amount}", GOLD, 26, 1.0, 36)

    def warning(self) -> None:
        self.audio.play("warning")
        self.vfx.comic(pygame.Vector2(WORLD_CENTER), "HURRY UP!", (255, 140, 60), 56, 1.2)

    def won(self) -> None:
        self.audio.play("win")
        for x in (320, 640, 960):
            self.vfx.burst(pygame.Vector2(x, 250), random.choice(COMIC_COLORS), 30, 220, 1.0, 5, 150)

    def lost(self) -> None:
        self.audio.play("lose")
        self.vfx.shake(8, 0.6)
