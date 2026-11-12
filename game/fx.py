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
        src = getattr(proj, "source", None)
        if src is not None and src.kind == "fadhli":
            self._fadhli_trail(proj, src)
            return
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
        """Character-flavoured impact: Jalu thunder sparks (Mark: punch impact), Romli coins, Zizi ripples, Bima chalk dust."""
        kind = getattr(source, "kind", None)
        pos = enemy.pos
        if kind == "jalu" and "mark_melee" in source.effects:
            self.vfx.burst(pos, (255, 190, 90), 3, 120, 0.22, 3, 0)
            self.vfx.pop(pos, 24, (255, 170, 70), 0.1)
        elif kind == "jalu":
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
        elif kind == "fadhli":
            self._fadhli_hit(enemy, source)
        elif kind == "ayun":
            self.vfx.burst(pos, GOLD, 3, 100, 0.35, 3, 240)
            self.vfx.pop(pos, 20, (255, 214, 120), 0.1)

    def muzzle(self, tower, tip) -> None:
        self.vfx.pop(tip, 22 + 3 * (tower.tiers[0] + tower.tiers[1]), tower.color, 0.1)
        self.vfx.burst(tip, tower.color, 3, 120, 0.2, 2, 0)

    # ------------------------------------------------------- Mark (Jalu path A)
    def mark_punch(self, tower, target, stacks: int) -> None:
        """One melee punch: swoosh + impact at the target; rage stacks make it redder and louder."""
        self.audio.play("punch")
        self.vfx.ring(tower.pos, 6, 22, 0.1, (255, 255, 255), 2)
        self.vfx.pop(target.pos, 30 + 2 * stacks, (255, 190, 90) if stacks < 5 else (255, 110, 80), 0.12)
        self.vfx.burst(target.pos, (255, 220, 140), 3, 110, 0.18, 3, 0)
        if self._comic_cd <= 0 and random.random() < 0.12:
            self._comic_cd = COMIC_GAP
            self.vfx.comic(pygame.Vector2(target.pos) + pygame.Vector2(0, -22), random.choice(["PUNCH!", "WHAM!", "BAM!"]),
                           (255, 210, 90) if stacks < 5 else (255, 120, 90), 30)

    def knocked(self, enemy) -> None:
        self.vfx.burst(enemy.pos, (200, 190, 170), 2, 50, 0.25, 3, 0)

    def mark_vanish(self, tower) -> None:
        """Mark disappears in a puff of smoke."""
        self.audio.play("mark_vanish")
        self.vfx.burst(tower.pos, (235, 235, 245), 26, 190, 0.6, 6, -30)
        self.vfx.burst(tower.pos, (255, 214, 70), 14, 150, 0.5, 4, 0)
        self.vfx.ring(tower.pos, 8, 64, 0.35, (255, 214, 70), 4)
        self.vfx.pop(tower.pos, 80, (255, 230, 150), 0.3)
        self.vfx.comic(tower.pos + pygame.Vector2(0, -44), "SWEEP!", (255, 214, 70), 40, 1.0)

    def sweep_start(self, pos) -> None:
        """The sweeper appears at the exit of the path."""
        self.audio.play("mark_sweep")
        self.vfx.ring(pos, 10, 80, 0.3, (255, 214, 70), 4)
        self.vfx.pop(pos, 110, (255, 214, 70), 0.3)
        self.vfx.flash((255, 230, 150), 50, 0.2)
        self.vfx.shake(3, 0.2)

    def sweep_run(self, pos, behind) -> None:
        """Speed trail: sparks and streaks left behind the sweeper every simulation step."""
        self.vfx.trail(pos + pygame.Vector2(random.uniform(-26, 26), random.uniform(-26, 26)), (255, 214, 70))
        self.vfx.burst(behind + pygame.Vector2(random.uniform(-20, 20), random.uniform(-20, 20)), (255, 140, 60), 1, 60, 0.3, 4, 0)

    def sweep_hit(self, enemy) -> None:
        self.audio.play("sweep_hit")
        self.vfx.burst(enemy.pos, (255, 214, 70), 8, 220, 0.3, 4, 0)
        self.vfx.burst(enemy.pos, (255, 255, 255), 4, 140, 0.2, 3, 0)
        self.vfx.ring(enemy.pos, 4, 30, 0.2, (255, 160, 60), 3)
        self._hit_word(enemy.pos, 0.25)

    def mark_reappear(self, tower) -> None:
        """Mark is back at his spot."""
        self.audio.play("mark_reappear")
        self.vfx.ring(tower.pos, 6, 52, 0.4, (255, 255, 255), 4)
        self.vfx.ring(tower.pos, 6, 76, 0.5, (255, 214, 70), 3)
        self.vfx.pop(tower.pos, 70, (255, 240, 180), 0.35)
        self.vfx.sparkle(tower.pos, (255, 214, 70), 16)
        self.vfx.comic(tower.pos + pygame.Vector2(0, -44), "I'M BACK!", (255, 214, 70), 32, 0.9)

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
        """Bima fires a curve: muzzle flash, expanding rings, a shower of sparks and a small screen kick."""
        self.audio.play("graph_fire")
        self.vfx.pop(tower.pos, 34, (255, 190, 100), 0.18)
        self.vfx.ring(tower.pos, 8, 54, 0.3, (255, 210, 130), 4)
        self.vfx.ring(tower.pos, 4, 34, 0.22, (255, 255, 255), 2)
        self.vfx.burst(tower.pos, (255, 190, 90), 14, 220, 0.5, 4, 40)
        self.vfx.burst(tower.pos, (255, 255, 255), 6, 160, 0.35, 3, 0)
        self.vfx.shake(3 + min(4, cost / 8), 0.12)
        self.vfx.text(tower.pos + pygame.Vector2(0, -52), f"-{cost}", (130, 215, 255), 24, 0.8, 30)

    def graph_trail(self, pos) -> None:
        """Sparks shed by the head of a travelling curve."""
        self.vfx.burst(pos, (255, 200, 100), 2, 90, 0.35, 3, 0)
        self.vfx.trail(pos, (255, 255, 255))

    def graph_hit(self, enemy, damage: float, k: int, prev_pos=None, first: bool = False) -> None:
        """A curve hit: ring + sparks + a BIG damage number (bigger numbers for bigger hits) + chain lightning to the
        previous Didit the same curve hit. The first hit of a curve also gives a tiny hit-stop and a screen kick."""
        col = (255, 200, 90)
        big = min(1.0, damage / 60)
        self.vfx.ring(enemy.pos, 6, 40 + 24 * big, 0.32, col, 4)
        self.vfx.ring(enemy.pos, 3, 24, 0.2, (255, 255, 255), 2)
        self.vfx.burst(enemy.pos, col, 10 + int(8 * big), 210, 0.5, 4, 120)
        self.vfx.burst(enemy.pos, (255, 255, 255), 5, 150, 0.3, 3, 0)
        size = int(24 + 22 * big)
        self.vfx.text(enemy.pos + pygame.Vector2(random.uniform(-8, 8), -30), f"{int(damage)}", (255, 238, 150) if big < 0.6 else (255, 150, 70),
                      size, 0.9, 46)
        if prev_pos is not None:
            self.vfx.lightning(prev_pos, enemy.pos, (255, 225, 140), 0.28, 4, 12)
        if first:
            self.vfx.shake(2.5 + 3 * big, 0.14)

    def graph_done(self, tower, hits: int, total: float) -> None:
        """The curve is over: a combo banner when it hit several Didits."""
        if hits >= 3:
            self.audio.play("wave_money")
            words = ("COMBO", "f(x)!", "QED!", "SIGMA!")[min(3, hits // 3 - 1)] if hits >= 3 else "COMBO"
            self.vfx.comic(tower.pos + pygame.Vector2(0, -78), f"{words} x{hits}", (255, 214, 90), 40 + min(16, hits * 2), 0.9)
            self.vfx.text(tower.pos + pygame.Vector2(0, -108), f"{int(total)} total", (255, 240, 200), 24, 1.1, 30)
            self.vfx.flash((255, 220, 140), 40, 0.12)

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

    # ------------------------------------------------------------- Fadhli
    # Garp (path A): heavy and loud. Johnny (path B): metallic, with a tornado on every hit.
    def _fadhli_trail(self, proj, src) -> None:
        from game import fadhli
        if fadhli.is_johnny(src):          # cold sparks + a thin silver spiral behind the steel ball
            self.vfx.trail(proj.pos, (200, 235, 255))
            if random.random() < 0.6:
                a = pygame.time.get_ticks() / 40
                self.vfx.burst(proj.pos + pygame.Vector2(math.cos(a), math.sin(a)) * 6, (255, 220, 110), 1, 20, 0.25, 2, 0)
        elif fadhli.is_base(src):          # plain rock: the same little trail as every other tower
            if random.random() < 0.7:
                self.vfx.trail(proj.pos, proj.color)
        else:                              # smoke and embers behind the cannonball
            k = 2.0 if getattr(proj, "mega", False) else 1.0
            self.vfx.burst(proj.pos, (90, 84, 80), 1, 24 * k, 0.45 * k, 5 * k, -20)
            if random.random() < 0.8:
                self.vfx.burst(proj.pos, (255, 150, 60), 1, 40 * k, 0.3, 3 * k, 30)
            if k > 1:
                self.vfx.pop(proj.pos, 46, (255, 200, 90), 0.1)

    def fadhli_charge_start(self, t) -> None:
        from game import fadhli
        if fadhli.is_johnny(t):
            self.audio.play("steel_spin")
        elif fadhli.is_base(t):
            return                         # base Fadhli: a quiet, invisible wind-up
        else:
            self.audio.play("galaxy_charge" if t.charge_mega else "garp_charge")
            self.vfx.ring(t.pos, 6, 36, 0.25, (255, 255, 255), 2)

    def fadhli_charging(self, t, f: float) -> None:
        """Called every 0.05s while charging: particles are pulled into him, dust rises, the charge builds."""
        from game import fadhli
        if fadhli.is_base(t):
            return
        if fadhli.is_johnny(t):
            hand = t.pos + pygame.Vector2(14 if t.aim.x >= 0 else -14, -14)
            self.vfx.suck(hand, 20 + 10 * (1 - f), (190, 230, 255), 2, 0.12, 2)
            return
        big = 1.7 if t.charge_mega else 1.0
        col = (255, 236, 130) if t.charge_mega else (255, 150, 60)
        self.vfx.suck(t.pos + pygame.Vector2(0, -28), (74 - 40 * f) * big, col, 2 + int(4 * f), 0.32, 3 + 2 * f)
        self.vfx.burst(t.pos + pygame.Vector2(random.uniform(-22, 22), 10), (170, 140, 100), 1, 34, 0.55, 3, -90)   # dust lifting off
        if t.charge_mega and random.random() < 0.5:
            self.vfx.lightning(t.pos + pygame.Vector2(random.uniform(-40, 40), 8), t.pos + pygame.Vector2(random.uniform(-10, 10), -58),
                               (255, 255, 200), 0.12, 1, 10)

    def fadhli_cancel(self, t) -> None:
        self.vfx.burst(t.pos + pygame.Vector2(0, -20), (200, 200, 200), 8, 60, 0.4, 3, 0)

    def fadhli_throw(self, t, mega: bool) -> None:
        from game import fadhli
        tip = t.pos + pygame.Vector2(14 if t.aim.x >= 0 else -14, -14)
        if fadhli.is_johnny(t):
            self.audio.play("steel_throw")
            self.vfx.pop(tip, 24, (190, 230, 255), 0.1)
            self.vfx.ring(tip, 4, 18, 0.12, (255, 226, 120), 2)
            return
        if fadhli.is_base(t):              # regular throw: the same small puff and ring every tower has
            self.audio.play("shoot_jalu")
            self.vfx.ring(t.pos, 10, 26, 0.12, (255, 255, 255), 2)
            self.muzzle(t, tip)
            return
        self.audio.play("garp_throw")
        r = 120 if mega else 62
        self.vfx.ring(t.pos, 8, r, 0.35 if mega else 0.25, (255, 255, 255), 5 if mega else 4)
        self.vfx.ring(t.pos, 6, r * 0.7, 0.3, (255, 150, 60), 3)
        self.vfx.pop(tip, 56 if mega else 36, (150, 85, 30), 0.18)
        self.vfx.burst(t.pos + pygame.Vector2(0, 8), (170, 140, 100), 14 if mega else 8, 160, 0.5, 4, -20)
        self.vfx.shake(7 if mega else 2.5 + t.tiers[0] * 0.5, 0.25 if mega else 0.14)
        if mega:
            self.vfx.flash((255, 220, 150), 40, 0.2)
            self.vfx.comic(t.pos + pygame.Vector2(0, -76), "GALAXY IMPACT!", (255, 200, 90), 44, 1.0)
        elif t.tiers[0] >= 3 and random.random() < 0.35:
            self.vfx.comic(t.pos + pygame.Vector2(0, -70), random.choice(["FIST OF LOVE!", "HAAAH!"]), (255, 170, 80), 32, 0.8)

    def projectile_hit(self, p, victims) -> None:
        """Once per landing projectile (before the per-victim effects). Garp: a crater, a shockwave and a boom."""
        src = getattr(p, "source", None)
        if src is None or src.kind != "fadhli":
            return
        from game import fadhli
        if fadhli.is_johnny(src) or fadhli.is_base(src):
            return
        mega = getattr(p, "mega", False)
        big = 1.0 + 0.25 * src.tiers[0]
        self.audio.play("galaxy_impact" if mega else "garp_impact")
        r = max(p.aoe_radius, 30) * (1.0 if mega else 1.0)
        self.vfx.ring(p.pos, 6, r * 1.1, 0.28, (255, 255, 255), 6)
        self.vfx.ring(p.pos, 6, r * 0.8, 0.4, (255, 150, 60), 4)
        self.vfx.pop(p.pos, r * (0.9 if mega else 0.8), (80, 45, 12), 0.2)
        self.vfx.burst(p.pos, (150, 120, 90), int(10 * big) + (24 if mega else 0), 210, 0.6, 5, 240)   # flying rubble
        self.vfx.burst(p.pos, (255, 160, 70), int(6 * big), 180, 0.35, 4, 40)
        for i in range(5 if not mega else 7):                                                                 # cracks in the ground
            a = random.uniform(0, math.tau)
            ln = r * random.uniform(0.7, 1.4)
            self.vfx.lightning(p.pos, p.pos + pygame.Vector2(math.cos(a), math.sin(a) * 0.6) * ln, (255, 170, 80), 0.3, 2, 6)
        self.vfx.shake((5 + 1.2 * src.tiers[0]) * (1.8 if mega else 1.0), 0.3 if mega else 0.18)
        if mega:
            self.vfx.flash((255, 235, 190), 38, 0.25)
            self.vfx.comic(p.pos + pygame.Vector2(0, -50), "BOOOOM!", (255, 210, 100), 58, 1.2)
        elif self._comic_cd <= 0 and random.random() < 0.4:
            self._comic_cd = COMIC_GAP
            self.vfx.comic(p.pos + pygame.Vector2(0, -34), random.choice(["WHAM!", "KA-BOOM!", "CRUSH!"]), (255, 170, 80), 38)

    def _fadhli_hit(self, enemy, src) -> None:
        from game import fadhli
        pos = enemy.pos
        if fadhli.is_johnny(src):
            self.audio.play("steel_hit")
            self.audio.play("tornado")
            self.vfx.tornado(pos, 0.85, 1.15 + (0.6 if enemy.is_boss else 0.0), (170, 220, 255))
            self.vfx.burst(pos, (220, 240, 255), 5, 130, 0.3, 3, 0)
            self.vfx.burst(pos, (255, 214, 90), 3, 100, 0.3, 2, 0)
            self.vfx.pop(pos, 22, (90, 130, 170), 0.12)
            if self._comic_cd <= 0 and random.random() < 0.08:
                self._comic_cd = COMIC_GAP
                self.vfx.comic(pos + pygame.Vector2(0, -26), random.choice(["SPIN!", "WRYYY!", "TWIST!"]), (190, 230, 255), 30)
        elif fadhli.is_garp(src):
            self.vfx.burst(pos, (255, 170, 80), 6, 160, 0.3, 4, 60)
            self.vfx.burst(pos, (150, 120, 90), 4, 120, 0.4, 4, 160)
        else:
            self.vfx.burst(pos, (170, 150, 120), 4, 100, 0.3, 3, 60)

    def crater_born(self, pos, radius: float, mega: bool) -> None:
        """A hot crater opens where the throw landed: lava flash, a ring of heat, flying rocks."""
        self.vfx.ring(pos, radius * 0.3, radius * 1.05, 0.45, (255, 120, 40), 4)
        self.vfx.pop(pos, radius * 0.9, (255, 140, 50), 0.25)
        self.vfx.burst(pos, (255, 170, 60), 6 + int(radius / 10), 120 + radius, 0.55, 4, -30)
        if mega:
            self.vfx.comic(pos + pygame.Vector2(0, -radius * 0.7), "MAGMA!", (255, 150, 60), 34, 0.9)

    def burn(self, enemy) -> None:
        """One crater burn tick: a little flame on the Didit (quiet on purpose, it repeats every 0.5s)."""
        self.vfx.burst(enemy.pos + pygame.Vector2(0, -4), (255, 140, 50), 2, 50, 0.35, 3, -80)

    def fadhli_bounce(self, a, b, n: int) -> None:
        self.audio.play("bounce")
        self.vfx.lightning(a, b, (210, 240, 255), 0.16, 3, 5)
        self.vfx.ring(a, 4, 22, 0.18, (255, 226, 120), 3)
        self.vfx.text(pygame.Vector2(a) + pygame.Vector2(0, -22), f"x{n + 1}", (255, 226, 120), 20, 0.5, 26)

    def fadhli_ball_stops(self, pos) -> None:
        self.vfx.burst(pos, (200, 220, 240), 5, 70, 0.3, 3, 120)

    def fadhli_stun(self, enemy) -> None:
        self.audio.play("stun_ding")
        self.vfx.text(enemy.pos + pygame.Vector2(0, -28), "STUN!", (255, 236, 120), 24, 0.9, 26)
        for i in range(5):
            a = i / 5 * math.tau
            self.vfx.burst(enemy.pos + pygame.Vector2(math.cos(a) * 12, -12 + math.sin(a) * 4), (255, 236, 120), 1, 20, 0.6, 3, 0)

    def fadhli_slow(self, enemy) -> None:
        self.vfx.text(enemy.pos + pygame.Vector2(0, -28), "SLOW", (150, 210, 255), 22, 0.8, 24)
        self.vfx.ring(enemy.pos, 4, enemy.radius + 12, 0.3, (150, 210, 255), 3)

    def fadhli_barrage(self, t, victims) -> None:
        self.audio.play("barrage")
        stand = t.pos + pygame.Vector2(36, -40)
        self.vfx.burst(stand, (255, 226, 110), 5, 150, 0.2, 3, 0)
        for e in victims[:4]:
            self.vfx.burst(e.pos, (255, 235, 150), 4, 140, 0.2, 3, 0)
            self.vfx.pop(e.pos + pygame.Vector2(random.uniform(-8, 8), random.uniform(-8, 8)), 22, (255, 226, 110), 0.1)
        if self._comic_cd <= 0 and random.random() < 0.15:
            self._comic_cd = COMIC_GAP
            self.vfx.comic(t.pos + pygame.Vector2(random.uniform(-20, 20), -64), random.choice(["BARRAGE!", "TUSK!", "ACT 4!"]), (255, 226, 110), 30)

    def golden_on(self, t) -> None:
        self.audio.play("golden")
        for k in range(3):
            self.vfx.ring(t.pos, 8, 40 + 30 * k, 0.4 + 0.2 * k, (255, 214, 70), 4 - k)
        self.vfx.pop(t.pos, 90, (255, 226, 120), 0.4)
        self.vfx.flash((255, 220, 120), 50, 0.25)
        for i in range(26):                                      # a golden spiral of sparks
            a = i * 0.45
            r = 3 * 1.618 ** (a / 1.1)
            self.vfx.burst(t.pos + pygame.Vector2(math.cos(a * 2) * r, math.sin(a * 2) * r * 0.6), (255, 214, 70), 1, 18, 0.9, 3, -50)
        self.vfx.comic(t.pos + pygame.Vector2(0, -62), "GOLDEN RATIO!", (255, 214, 70), 38, 1.0)

    def golden_off(self, t) -> None:
        self.vfx.ring(t.pos, 6, 50, 0.3, (255, 214, 70), 3)

    def galaxy_on(self, t) -> None:
        self.audio.play("galaxy_on")
        self.vfx.ring(t.pos, 8, 80, 0.4, (255, 150, 70), 5)
        self.vfx.pop(t.pos, 80, (255, 190, 100), 0.35)
        self.vfx.comic(t.pos + pygame.Vector2(0, -62), "GALAXY!", (255, 190, 90), 38, 1.0)
        self.vfx.shake(3, 0.2)

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

    # -------------------------------------------------------------------- A'yun
    def ayun_roll(self, tower, item_id: str, auto: bool) -> None:
        """A gacha roll: a shower of sparkles in the rarity colour; rare and legendary get a louder reveal."""
        from data.ayun import ITEMS, RARITY_COLOR, RARITY_LABEL
        c = ITEMS[item_id]
        col = RARITY_COLOR[c["rarity"]]
        pos = tower.pos + pygame.Vector2(0, -34)
        self.audio.play("gacha_rare" if c["rarity"] in ("rare", "legendary") else "gacha_roll")
        self.vfx.sparkle(tower.pos, col, 10 + 8 * ("junk", "common", "rare", "legendary").index(c["rarity"]))
        self.vfx.ring(tower.pos, 8, 46, 0.35, col, 3)
        self.vfx.text(pos + pygame.Vector2(0, -22), ("AUTO: " if auto else "") + c["name"], col, 22, 1.4, 34)
        if c["rarity"] == "legendary":
            self.vfx.comic(tower.pos + pygame.Vector2(0, -60), "LEGENDARY!", col, 40, 1.2)
            self.vfx.flash(col, 50, 0.25)
            self.vfx.shake(3, 0.2)
        elif c["rarity"] == "rare":
            self.vfx.comic(tower.pos + pygame.Vector2(0, -60), "RARE!", col, 30, 0.9)

    def ayun_prompt(self, tower) -> None:
        self.audio.play("tick")
        self.vfx.text(tower.pos + pygame.Vector2(0, -50), "Stock full!", (255, 214, 70), 22, 1.2, 24)

    def ayun_replaced(self, tower, old_id: str, new_id: str) -> None:
        self.audio.play("place")
        self.vfx.burst(tower.pos + pygame.Vector2(0, -30), (180, 180, 190), 10, 90, 0.4, 3, 120)

    def ayun_item_sold(self, tower, item_id: str, value: int) -> None:
        self.audio.play("sell")
        self.vfx.burst(tower.pos + pygame.Vector2(0, -30), GOLD, 8, 110, 0.45, 3, 220)
        self.vfx.text(tower.pos + pygame.Vector2(0, -44), f"+${value}", GOLD, 22, 0.9, 30)

    def ayun_expired(self, tower, item_id: str) -> None:
        from data.ayun import ITEMS
        self.vfx.burst(tower.pos + pygame.Vector2(0, -50), (170, 170, 180), 8, 70, 0.5, 3, -30)
        self.vfx.text(tower.pos + pygame.Vector2(0, -56), f"{ITEMS[item_id]['name']} expired", (200, 200, 210), 18, 1.1, 22)

    def ayun_throw(self, tower, item_id: str) -> None:
        self.audio.play("shoot_ayun")
        self.vfx.ring(tower.pos, 8, 22, 0.12, (255, 255, 255), 2)

    def ayun_mark(self, enemy) -> None:
        self.vfx.text(enemy.pos + pygame.Vector2(0, -26), "$ +25%", (112, 178, 255), 18, 0.8, 20)

    def ayun_puddle(self, pos) -> None:
        self.vfx.burst(pos, (255, 120, 40), 12, 130, 0.5, 4, 80)
        self.vfx.ring(pos, 8, 52, 0.3, (255, 150, 60), 3)

    def ayun_sold_enemy(self, enemy, amount: int) -> None:
        """Passive: she sells the Didit she just killed (a small gold number, no extra sound spam)."""
        self.audio.play("coin")
        self.vfx.text(enemy.pos + pygame.Vector2(0, -22), f"SOLD +${amount}", GOLD, 18, 0.8, 26)
        self.vfx.burst(enemy.pos, GOLD, 3, 90, 0.4, 3, 240)
