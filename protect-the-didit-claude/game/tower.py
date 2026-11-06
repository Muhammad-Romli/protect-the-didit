"""Tower: stats are base + sum of unlocked stat_mods (data-driven, no per-upgrade classes)."""
from __future__ import annotations

import math
from typing import TYPE_CHECKING, Optional

import pygame

from data.activities import STACKS
from data.settings import (INCOME_INTERVAL_SECONDS, MAX_OFF_PATH_TIER, MAX_SLOW, MAX_TIER, MIN_COOLDOWN,
                           SELL_REFUND, TOWER_RADIUS)
from data.towers import DEFAULT_STATS, TOWERS
from game.effects import EFFECTS
from game.enemy import Enemy
from game.projectile import Projectile
from game import bima, gfx, mark, models, sprites_proc
from game.assets import sprite
from game.utils import Vec, draw_outlined

if TYPE_CHECKING:
    from game.game import Game


class Tower:
    def __init__(self, kind: str, pos, refund: float = SELL_REFUND) -> None:
        self.kind = kind
        self.refund = refund                 # share of the money spent that selling gives back (shop perk raises it)
        self.data = TOWERS[kind]
        self.name: str = self.data["name"]
        self.color = self.data["color"]
        self.pos = Vec(pos)
        self.tiers = [0, 0]                  # (path A tier, path B tier)
        self.spent: int = self.data["cost"]  # total money spent (for sell value)
        self.cooldown_left = 0.0
        self.targeting = "first"  # priority: first | last | strong | weak | close
        self.kick = 0.0  # visual recoil timer after firing
        self.aim = Vec(0, -1)  # visual: where the barrel points
        self.income_timer = 0.0  # seconds toward the next income payout
        self.activity: Optional[str] = None  # key into data/activities.py
        self.activity_time = 0.0             # seconds spent in the current activity
        self.activity_acc = 0.0              # progress toward the next activity tick
        self.stacks: dict[str, int] = {}     # activity stacks (laziness, blessing, ...)
        self.stats: dict[str, float] = {}
        self.effects: list[str] = []
        self.active_cd: dict[str, float] = {}   # ability id -> seconds until ready
        self.haste = (0.0, 0.0)                 # (seconds left, attack speed bonus) from random events
        self.fx_t = 0.0                         # ambient sparkle timer
        self.vanished = False                   # Mark's Sweep: hidden, not attacking
        self.recompute_stats()
        if kind == "bima":
            bima.init_tower(self)
        elif kind == "jalu":
            mark.init_tower(self)

    # ---------------------------------------------------------------- stats
    def recompute_stats(self) -> None:
        stats = {**DEFAULT_STATS, **self.data["stats"]}
        effects: list[str] = []
        for path_idx, tier in enumerate(self.tiers):
            for up in self.data["paths"][path_idx]["tiers"][:tier]:
                for key, delta in up["stat_mods"].items():
                    stats[key] += delta
                effects.extend(up["effects"])
        for name, count in self.stacks.items():
            for key, delta in STACKS[name]["mods"].items():
                stats[key] += delta * count
        stats["cooldown"] = max(MIN_COOLDOWN, stats["cooldown"])
        stats["slow"] = min(MAX_SLOW, stats["slow"])
        self.stats = stats
        self.effects = effects

    @property
    def sell_value(self) -> int:
        return int(self.spent * self.refund)

    # --------------------------------------------------------------- stacks
    def add_stack(self, name: str) -> bool:
        """+1 stack up to its max. Returns False if already maxed."""
        if self.stacks.get(name, 0) >= STACKS[name]["max"]:
            return False
        self.stacks[name] = self.stacks.get(name, 0) + 1
        self.recompute_stats()
        return True

    def stop_activity(self) -> None:
        self.activity, self.activity_time, self.activity_acc = None, 0.0, 0.0

    def clear_wave_stacks(self) -> None:
        """Drop stacks that only last for one battle."""
        self.stacks = {n: c for n, c in self.stacks.items() if not STACKS[n]["reset_on_wave_end"]}
        self.recompute_stats()

    # ------------------------------------------------------------- upgrades
    def next_upgrade(self, path: int) -> Optional[dict]:
        tier = self.tiers[path]
        tiers = self.data["paths"][path]["tiers"]
        return tiers[tier] if tier < len(tiers) else None

    def is_path_locked(self, path: int) -> bool:
        """Jalu only: once this unit has bought ANY upgrade in one path, the other path is locked for it
        (no cross-pathing). Other towers keep the BTD6 rule in can_upgrade()."""
        return self.kind == "jalu" and self.tiers[1 - path] > 0

    def can_upgrade(self, path: int) -> tuple[bool, str]:
        """Rule: max(a, b) <= 4 and min(a, b) <= 1 (Jalu: one path only, Bima: one path only).
        Returns (ok, reason_if_blocked)."""
        if self.tiers[path] >= MAX_TIER:
            return False, "Max tier"
        if self.is_path_locked(path):
            return False, f"Locked: this Jalu follows path {'AB'[1 - path]}"
        new = list(self.tiers)
        new[path] += 1
        if min(new) > (0 if self.kind == "bima" else MAX_OFF_PATH_TIER):  # Bima: ONE path only
            return False, "Locked: Bima uses ONE path" if self.kind == "bima" else "Locked: other path is already deep"
        return True, ""

    def upgrade(self, path: int, paid: int | None = None) -> None:
        """Apply the next tier. Caller checks can_upgrade() and takes the payment (`paid`
        = money actually spent after discounts, counts toward the sell value)."""
        up = self.next_upgrade(path)
        assert up is not None
        self.tiers[path] += 1
        self.spent += up["cost"] if paid is None else paid
        self.recompute_stats()

    def activity_lock(self, act_data: dict) -> str:
        """'' if the activity is unlocked, else e.g. 'A tier 2' (what is still needed)."""
        unlock = act_data.get("unlock")
        if unlock is None or self.tiers[unlock[0]] >= unlock[1]:
            return ""
        return f"{'AB'[unlock[0]]} tier {unlock[1]}"

    def pending_effects(self, upgrade: dict) -> list[str]:
        """Effect names of an upgrade that have no handler registered yet."""
        return [e for e in upgrade["effects"] if e not in EFFECTS]

    # --------------------------------------------------------------- update
    def pick_target(self, enemies: list[Enemy]) -> Optional[Enemy]:
        """Best enemy in range for this tower's priority: first / last (path position),
        strong / weak (current HP), close (distance to the tower)."""
        rng = self.stats["range"]
        cands = [e for e in enemies if e.alive and self.pos.distance_to(e.pos) <= rng + e.radius]
        if not cands:
            return None
        mode = self.targeting
        if mode == "last":
            return min(cands, key=lambda e: e.distance)
        if mode == "strong":
            return max(cands, key=lambda e: (e.hp + e.armor * 1000, e.distance))
        if mode == "weak":
            return min(cands, key=lambda e: (e.hp + e.armor * 1000, -e.distance))
        if mode == "close":
            return min(cands, key=lambda e: self.pos.distance_to(e.pos))
        return max(cands, key=lambda e: e.distance)

    def update(self, dt: float, game: "Game") -> None:
        self.kick = max(0.0, self.kick - dt)
        for aid in list(self.active_cd):
            self.active_cd[aid] = max(0.0, self.active_cd[aid] - dt)
        if self.haste[0] > 0:
            self.haste = (self.haste[0] - dt, self.haste[1])
        for name in self.effects:  # per-frame effect hooks (e.g. Romli's random events)
            fn = EFFECTS.get(name)
            if fn is not None:
                fn(self, game, "tick", dt=dt)
        self.fx_t += dt
        if self.fx_t > 0.2:
            self.fx_t = 0.0
            game.fx.aura(self)
        if self.kind == "bima":
            bima.tick_tower(self, game, dt)
        elif self.kind == "jalu":
            mark.tick_tower(self)  # rage stacks end when the target dies / leaves the range
        rate = game.attack_speed_mult(self)  # Zizi auras
        if self.haste[0] > 0:
            rate += self.haste[1]
        if self.kind == "bima" and self.buff_timer > 0:
            rate += 0.6
        self.cooldown_left = max(0.0, self.cooldown_left - dt * rate)
        if self.cooldown_left > 0 or self.vanished:  # Mark does not attack while he is away (Sweep)
            return
        target = self.pick_target(game.enemies)
        if target is None:
            return
        s = self.stats
        if mark.is_mark(self):  # Mark: instant melee punch instead of a projectile
            mark.punch(self, game, target)
            self.cooldown_left = s["cooldown"]
            self.kick = 0.1
            self.aim = (target.pos - self.pos).normalize() if target.pos != self.pos else self.aim
            return
        proj = Projectile(self.pos, target, s["proj_speed"], s["damage"], s["aoe_radius"],
                          s["slow"], s["slow_duration"], s["money_per_hit"], self.color, self)
        if self.kind == "bima":
            bima.prepare_projectile(self, game, target, proj)
        game.projectiles.append(proj)
        self.cooldown_left = s["cooldown"]
        self.kick = 0.1
        game.fx.fired(self)
        self.aim = (target.pos - self.pos).normalize() if target.pos != self.pos else self.aim

    # ----------------------------------------------------------------- draw
    def draw_shadow(self, surface: pygame.Surface) -> None:
        if self.vanished:
            return
        gfx.blit_shadow(surface, (self.pos.x + 14, self.pos.y + 14), 66, 26, 105)

    def draw(self, surface: pygame.Surface, selected: bool = False) -> None:
        x, y = int(self.pos.x), int(self.pos.y)
        if self.vanished:  # Mark is sweeping: no sprite, just a marker where he will return
            mark.draw_vanished(surface, self, selected)
            return
        if selected:  # pulsing ring on the ground under the pedestal
            pulse = 2 * math.sin(pygame.time.get_ticks() / 160)
            pygame.draw.ellipse(surface, (255, 255, 255), (x - 28 - pulse, y - 12 - pulse / 2, 56 + 2 * pulse, 28 + pulse), 3)
        n_tiers = self.tiers[0] + self.tiers[1]
        if n_tiers:  # tier glow on the ground: bigger and brighter with every upgrade
            col = (255, 214, 70) if self.tiers[0] >= self.tiers[1] else (110, 215, 255)
            if self.kind == "bima" and bima.buff_active(self):
                col = (255, 225, 90)
            g = gfx.glow(30 + 5 * n_tiers, col, 60 + 14 * n_tiers)
            surface.blit(g, g.get_rect(center=(x, y + 4)))
        img = sprite(f"towers/{self.kind}", 2 * TOWER_RADIUS + 10)  # optional PNG override
        custom = img is not None
        if not custom:
            img = sprites_proc.tower_sprite(self.kind, TOWER_RADIUS, self.color, models.look_of(self.kind, self.tiers))
        recoil = self.kick / 0.1
        weapon_first = self.aim.y < 0  # aiming up: wand goes behind the body
        melee = mark.is_mark(self)  # Mark punches: no wand
        if not custom and weapon_first and not melee:
            self._draw_wand(surface, x, y, recoil)
        if custom:
            surface.blit(img, img.get_rect(center=(x, y)))
        else:
            ox, oy = sprites_proc.tower_origin(TOWER_RADIUS)
            surface.blit(img, (x - ox, y - oy - round(2 * recoil)))  # tiny hop when firing
        if not custom and not weapon_first and not melee:
            self._draw_wand(surface, x, y, recoil)
        if melee:
            mark.draw_rage(surface, self, x, y)
        pips = [(STACKS[n]["color"]) for n, c in self.stacks.items() for _ in range(c)]
        for i, color in enumerate(pips):  # one pip per active stack, above the tower
            px = x - (len(pips) - 1) * 4 + i * 8
            pygame.draw.circle(surface, color, (px, y - TOWER_RADIUS * 3 - 4), 3)
            pygame.draw.circle(surface, (20, 20, 30), (px, y - TOWER_RADIUS * 3 - 4), 3, 1)
        if self.stats["income_per_sec"] > 0:  # progress bar to the next income payout
            frac = min(1.0, self.income_timer / INCOME_INTERVAL_SECONDS)
            bar = pygame.Rect(x - 17, y - TOWER_RADIUS * 3 - 14, 34, 7)
            pygame.draw.rect(surface, (30, 20, 12), bar.inflate(2, 2), border_radius=4)
            pygame.draw.rect(surface, (80, 60, 30), bar, border_radius=3)
            if frac > 0:
                pygame.draw.rect(surface, (255, 215, 80), (bar.x, bar.y, max(3, int(bar.w * frac)), bar.h), border_radius=3)
        if self.activity:  # gold badge = busy with a preparation activity
            pygame.draw.circle(surface, (38, 24, 18), (x + 20, y - 40), 9)
            pygame.draw.circle(surface, (255, 214, 70), (x + 20, y - 40), 7)
            pygame.draw.circle(surface, (255, 246, 190), (x + 18, y - 42), 3)
        models.draw_companion(surface, self.kind, models.look_of(self.kind, self.tiers), x, y, pygame.time.get_ticks() / 1000)
        self._draw_tier_badge(surface, x, y)

    def _draw_wand(self, surface: pygame.Surface, x: int, y: int, recoil: float) -> None:
        """Held weapon model (game/models.py) that follows the aim direction (visual only)."""
        look = models.look_of(self.kind, self.tiers)
        angle = -math.degrees(math.atan2(self.aim.y, self.aim.x))
        img = models.weapon_image(self.kind, look, angle, self.aim.x < 0)
        hand = Vec(x + (14 if self.aim.x >= 0 else -14), y - 12)
        if img is None:
            return
        grip = hand - self.aim * (5 * recoil)
        surface.blit(img, img.get_rect(center=(round(grip.x), round(grip.y))))
        if recoil > 0:
            tip = hand + self.aim * 30
            glow = gfx.glow(16, (255, 240, 180), 200)
            surface.blit(glow, glow.get_rect(center=(int(tip.x), int(tip.y))))

    def _draw_tier_badge(self, surface: pygame.Surface, x: int, y: int) -> None:
        """Tiny plate under the pedestal: path A tier | path B tier (gold = A, cyan = B)."""
        a, b = self.tiers
        if a == 0 and b == 0:
            return
        plate = pygame.Rect(0, 0, 38, 16)
        plate.midtop = (x, y + 15)
        pygame.draw.rect(surface, (30, 20, 12), plate, border_radius=8)
        pygame.draw.rect(surface, (255, 255, 255), plate, 1, border_radius=8)
        draw_outlined(surface, str(a), (plate.x + 10, plate.centery), 14, (255, 214, 70), center=True, width=1)
        draw_outlined(surface, str(b), (plate.right - 10, plate.centery), 14, (120, 210, 255), center=True, width=1)
