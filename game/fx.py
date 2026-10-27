"""FX: turns game events into sound + visuals. Game calls these; no game logic in here."""
from __future__ import annotations

import math
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
        self.vfx.ring(tower.pos, 6, 90, 0.6, tower.color, 3)
        self.vfx.sparkle(tower.pos, GOLD, 16 + 6 * tier)
        self.vfx.pop(tower.pos, 60 + 14 * tier, tower.color, 0.45)
        for _ in range(8 + 3 * tier):  # rising light pillar
            self.vfx.burst(tower.pos + pygame.Vector2(random.uniform(-12, 12), random.uniform(-4, 8)), GOLD, 1, 30, 0.9, 3, -240)
        self.vfx.text(tower.pos + pygame.Vector2(0, -34), name, (255, 255, 255), 22, 1.2, 30)
        if tier >= 4:
            self.vfx.comic(tower.pos + pygame.Vector2(0, -60), "ULTIMATE!", (255, 100, 150), 40, 1.0)
            self.vfx.shake(4, 0.25)

    def sold(self, tower, value: int) -> None:
        self.audio.play("sell")
        self.vfx.burst(tower.pos, GOLD, 14, 140, 0.5, 4, 200)
        self.vfx.text(tower.pos, f"+${value}", GOLD, 26, 1.0, 40)

    def fired(self, tower) -> None:
        if tower.kind != "bima" or tower.tiers[1] == 0:
            self.audio.play(f"shoot_{tower.kind}")
        self.vfx.ring(tower.pos, 10, 26, 0.12, (255, 255, 255), 2)
        self.muzzle(tower, tower.pos + tower.aim * 22 + pygame.Vector2(14 if tower.aim.x >= 0 else -14, -12))

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
    def hit(self, enemy, color, source=None) -> None:
        self.audio.play("hit")
        if source is not None:
            self.tower_hit(enemy, source)
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

    # ---------------------------------------------- character vfx (all towers)
    def aura(self, tower) -> None:
        """Ambient sparkles around an upgraded tower: gold for path A, cyan for path B, more with every tier."""
        n = tower.tiers[0] + tower.tiers[1]
        if n <= 0:
            return
        col = GOLD if tower.tiers[0] >= tower.tiers[1] else CYAN
        for _ in range(1 + n // 3):
            a = random.uniform(0, 6.283)
            r = random.uniform(10, 24)
            p = tower.pos + pygame.Vector2(math.cos(a) * r, math.sin(a) * r * 0.6 + 6)
            self.vfx.burst(p, col, 1, 24, 0.7 + 0.1 * n, 2 + n // 3, -60)

    def tower_hit(self, enemy, source) -> None:
        """Character-flavoured impact: Jalu thunder sparks, Romli coins, Zizi ripples, Bima chalk dust."""
        kind = getattr(source, "kind", None)
        pos = enemy.pos
        if kind == "jalu":
            self.vfx.lightning(pos + pygame.Vector2(-16, -16), pos + pygame.Vector2(6, 8), (180, 210, 255), 0.12, 3, 8)
            self.vfx.pop(pos, 22, (120, 170, 255), 0.12)
        elif kind == "romli":
            self.vfx.burst(pos, GOLD, 3, 100, 0.4, 3, 260)
            self.vfx.pop(pos, 18, (110, 255, 160), 0.1)
        elif kind == "zizi":
            self.vfx.ring(pos, 4, 26, 0.25, (210, 140, 255), 2)
            self.vfx.pop(pos, 22, (200, 120, 255), 0.14)
        elif kind == "bima":
            self.vfx.burst(pos, (255, 190, 110), 4, 90, 0.35, 3, 40)
            self.vfx.pop(pos, 20, (255, 170, 80), 0.12)

    def muzzle(self, tower, tip) -> None:
        self.vfx.pop(tip, 22 + 3 * (tower.tiers[0] + tower.tiers[1]), tower.color, 0.1)
        self.vfx.burst(tip, tower.color, 3, 120, 0.2, 2, 0)

    def thunder_warn(self, pos, radius) -> None:
        self.vfx.ring(pos, radius, radius * 0.4, 0.45, (255, 240, 120), 3)

    def thunder_strike(self, pos, radius) -> None:
        self.audio.play("thunder")
        top = pygame.Vector2(pos.x + random.uniform(-30, 30), -10)
        for _ in range(3):
            self.vfx.lightning(top, pos, (255, 245, 150), 0.35, 6, 26)
        self.vfx.pop(pos, radius * 1.6, (255, 240, 150), 0.35)
        self.vfx.ring(pos, 10, radius, 0.35, (255, 255, 255), 5)
        self.vfx.ring(pos, 10, radius * 1.3, 0.5, (255, 220, 90), 3)
        self.vfx.burst(pos, (255, 240, 140), 26, 280, 0.6, 5, 150)
        self.vfx.comic(pos + pygame.Vector2(0, -radius), "THUNDERSTRIKE!", (255, 245, 100), 40, 1.0)
        self.vfx.flash((255, 255, 230), 90, 0.2)
        self.vfx.shake(7, 0.4)

    def loom_reset(self, tower) -> None:
        self.audio.play("loom")
        r = tower.stats["range"]
        for k in range(3):
            self.vfx.ring(tower.pos, 10, r * (0.5 + 0.25 * k), 0.4 + 0.15 * k, (130, 200, 255), 4 - k)
        self.vfx.pop(tower.pos, r * 0.7, (120, 190, 255), 0.4)
        self.vfx.comic(tower.pos + pygame.Vector2(0, -40), "TIME RESET!", (150, 210, 255), 36, 1.0)
        self.vfx.flash((120, 190, 255), 70, 0.25)

    def nap_time(self, tower) -> None:
        self.audio.play("nap")
        r = tower.stats["range"]
        self.vfx.ring(tower.pos, 10, r, 0.7, (200, 130, 255), 5)
        self.vfx.pop(tower.pos, r * 0.8, (170, 110, 255), 0.5)
        self.vfx.comic(tower.pos + pygame.Vector2(0, -40), "NAP TIME!", (210, 160, 255), 36, 1.0)
        self.vfx.flash((140, 90, 220), 80, 0.3)

    def graph_fire(self, tower, cost: int) -> None:
        self.audio.play("graph_fire")
        self.vfx.pop(tower.pos, 40, (255, 190, 90), 0.25)
        self.vfx.ring(tower.pos, 8, 34, 0.25, (255, 200, 120), 3)
        self.vfx.text(tower.pos + pygame.Vector2(0, -52), f"-{cost}", (130, 215, 255), 24, 0.8, 30)

    def shape_hit(self, enemy, shape: int, solid: bool) -> None:
        self.audio.play(("shape_sq", "shape_tri", "shape_circ")[shape])
        from game import sprites_proc
        col = sprites_proc.SHAPE_COLORS[shape]
        self.vfx.burst(enemy.pos, col, 5 + 4 * solid, 120, 0.3, 3, 0)
        self.vfx.ring(enemy.pos, 4, 22 + 6 * solid, 0.22, col, 2)

    def geo_converge(self, enemy, solid: bool) -> None:
        """Collision wind-up: the three shapes fly in from 120 degrees apart."""
        from game import sprites_proc
        self.audio.play("collide_wind")
        a0 = random.uniform(0, 6.283)
        for i in range(3):
            a = a0 + i * 2.094
            start = enemy.pos + pygame.Vector2(math.cos(a), math.sin(a)) * 56
            self.vfx.fly(start, enemy.pos, sprites_proc.shape_sprite(i, solid, 30), 0.1, 120 * (1 if i % 2 else -1))
            self.vfx.burst(start, sprites_proc.SHAPE_COLORS[i], 2, 40, 0.2, 2, 0)

    def geo_impact(self, enemy, damage: float, solid: bool) -> None:
        from game import sprites_proc
        self.audio.play("collide")
        self.vfx.pop(enemy.pos, 70 + 20 * solid, (255, 255, 255), 0.18)
        self.vfx.ring(enemy.pos, 8, 64 + 20 * solid, 0.22, (255, 255, 255), 6)
        self.vfx.ring(enemy.pos, 8, 48 + 14 * solid, 0.3, (255, 200, 90), 3)
        for i in range(3):
            self.vfx.burst(enemy.pos, sprites_proc.SHAPE_COLORS[i], 8 + 4 * solid, 300, 0.5, 4, 40)
        self.vfx.comic(enemy.pos + pygame.Vector2(0, -34), "COLLISION!", (255, 230, 90), 34, 0.9)
        self.vfx.text(enemy.pos + pygame.Vector2(0, -56), f"{int(damage)}", (255, 255, 255), 30, 0.9, 30)
        self.vfx.shake(3 + 2 * solid + (2 if enemy.is_boss else 0), 0.16)

    def cube_placed(self, pos) -> None:
        self.audio.play("cube")
        self.vfx.burst(pos, (190, 160, 110), 14, 140, 0.4, 4, 200)
        self.vfx.ring(pos, 6, 50, 0.25, (255, 190, 100), 3)
        self.vfx.pop(pos, 50, (255, 180, 90), 0.2)

    def cube_broke(self, pos) -> None:
        self.audio.play("crack")
        self.vfx.burst(pos, (255, 190, 100), 24, 240, 0.6, 5, 300)
        self.vfx.ring(pos, 8, 60, 0.3, (255, 200, 120), 4)

    def pyramid_on(self, tower) -> None:
        self.audio.play("pyramid")
        self.vfx.pop(tower.pos, 70, (255, 225, 90), 0.4)
        self.vfx.ring(tower.pos, 10, 70, 0.4, (255, 225, 90), 4)
        for i in range(10):
            self.vfx.burst(tower.pos + pygame.Vector2(random.uniform(-14, 14), 0), (255, 225, 110), 1, 60, 0.9, 3, -160)
        self.vfx.comic(tower.pos + pygame.Vector2(0, -46), "POWER UP!", (255, 225, 100), 34, 1.0)

    def sphere_cast(self, pos, radius, stash) -> None:
        self.audio.play("sphere")
        self.vfx.ring(pos, 10, radius, 0.4, (110, 220, 255), 5)
        self.vfx.pop(pos, radius, (100, 210, 255), 0.4)
        self.vfx.ring(stash, 10, 70, 0.5, (110, 220, 255), 4)
        self.vfx.comic(pos + pygame.Vector2(0, -radius), "SPHERE!", (130, 225, 255), 36, 1.0)

    def trapped(self, enemy) -> None:
        self.vfx.burst(enemy.pos, (130, 225, 255), 8, 100, 0.4, 3, 0)
        self.vfx.ring(enemy.pos, 4, enemy.radius + 12, 0.3, (130, 225, 255), 3)

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
            if enemy.kind == "rich":  # coin shower
                self.vfx.burst(enemy.pos, GOLD, 26, 210, 0.9, 5, 260)
        if enemy.gives_money:
            self.audio.play("coin")
            self.vfx.text(enemy.pos + pygame.Vector2(0, -16), f"+${enemy.bounty}", GOLD, 22, 0.9, 38)

    def armor_hit(self, enemy, broke: bool, hits: int) -> None:
        """A hit that only chipped armor: sparks + clang; bigger burst when the armor breaks."""
        self.audio.play("hit")
        self.vfx.burst(enemy.pos, (200, 210, 225), 5 if not broke else 22, 130 if not broke else 220, 0.3, 3, 0)
        if broke:
            self.vfx.ring(enemy.pos, 6, 40, 0.3, (200, 210, 225), 4)
            self.vfx.comic(enemy.pos + pygame.Vector2(0, -26), "CLANG!", (210, 220, 240), 36, 0.8)
        elif enemy.armor > 0:
            self.vfx.text(enemy.pos + pygame.Vector2(0, -22), f"{enemy.armor}", (210, 220, 240), 20, 0.5, 30)

    def normalized(self, enemy) -> None:
        """Jalu's Speed Against Time kicked in on a fast enemy."""
        self.vfx.ring(enemy.pos, 6, 36, 0.35, (150, 200, 255), 3)
        self.vfx.text(enemy.pos + pygame.Vector2(0, -26), "NORMAL", (170, 215, 255), 22, 0.9, 28)

    def stolen(self, enemy, amount: int) -> None:
        self.vfx.text(pygame.Vector2(enemy.pos) + pygame.Vector2(0, -50), f"-${amount} stolen!", (255, 120, 110), 30, 1.4, 34)
        self.vfx.burst(enemy.pos, GOLD, 18, 170, 0.8, 5, 200)

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
    def wave_started(self, number: int, boss: bool, special: str | None = None, new_enemy: str | None = None) -> None:
        self.audio.play("wave_start")
        center = pygame.Vector2(WORLD_CENTER)
        if special:
            self.vfx.comic(center, f"SPECIAL: {special}!", (120, 220, 255), 64, 1.7)
            self.vfx.text(center + pygame.Vector2(0, 52), f"WAVE {number}  -  double clear bonus", (255, 255, 255), 26, 1.7, 0)
        else:
            self.vfx.comic(center, "BOSS WAVE!" if boss else f"WAVE {number}!",
                           (255, 100, 100) if boss else (255, 230, 60), 72, 1.5)
        if new_enemy:
            self.vfx.text(center + pygame.Vector2(0, 92), f"NEW ENEMY: {new_enemy}", (255, 190, 90), 32, 2.2, 0)
        if boss or special:
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
