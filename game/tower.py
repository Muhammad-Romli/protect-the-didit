"""Tower: stats are base + sum of unlocked stat_mods (data-driven, no per-upgrade classes)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import pygame

from data.activities import STACKS
from data.settings import (INCOME_INTERVAL_SECONDS, MAX_OFF_PATH_TIER, MAX_SLOW, MAX_TIER, MIN_COOLDOWN,
                           SELL_REFUND, TOWER_RADIUS)
from data.towers import DEFAULT_STATS, TOWERS
from game.effects import EFFECTS
from game.enemy import Enemy
from game.projectile import Projectile
from game.assets import sprite
from game.utils import Vec, draw_text

if TYPE_CHECKING:
    from game.game import Game


class Tower:
    def __init__(self, kind: str, pos) -> None:
        self.kind = kind
        self.data = TOWERS[kind]
        self.name: str = self.data["name"]
        self.color = self.data["color"]
        self.pos = Vec(pos)
        self.tiers = [0, 0]                  # (path A tier, path B tier)
        self.spent: int = self.data["cost"]  # total money spent (for sell value)
        self.cooldown_left = 0.0
        self.kick = 0.0  # visual recoil timer after firing
        self.aim = Vec(0, -1)  # visual: where the barrel points
        self.income_timer = 0.0  # seconds toward the next income payout
        self.activity: Optional[str] = None  # key into data/activities.py
        self.activity_time = 0.0             # seconds spent in the current activity
        self.activity_acc = 0.0              # progress toward the next activity tick
        self.stacks: dict[str, int] = {}     # activity stacks (laziness, blessing, ...)
        self.stats: dict[str, float] = {}
        self.effects: list[str] = []
        self.recompute_stats()

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
        return int(self.spent * SELL_REFUND)

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

    def can_upgrade(self, path: int) -> tuple[bool, str]:
        """Rule: max(a, b) <= 4 and min(a, b) <= 1. Returns (ok, reason_if_blocked)."""
        if self.tiers[path] >= MAX_TIER:
            return False, "Max tier"
        new = list(self.tiers)
        new[path] += 1
        if min(new) > MAX_OFF_PATH_TIER:
            return False, "Locked: other path is already deep"
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
        """'First' targeting: enemy furthest along the path within range."""
        best: Optional[Enemy] = None
        rng = self.stats["range"]
        for e in enemies:
            if e.alive and self.pos.distance_to(e.pos) <= rng + e.radius:
                if best is None or e.distance > best.distance:
                    best = e
        return best

    def update(self, dt: float, game: "Game") -> None:
        self.kick = max(0.0, self.kick - dt)
        rate = game.attack_speed_mult(self)  # Zizi auras
        self.cooldown_left = max(0.0, self.cooldown_left - dt * rate)
        if self.cooldown_left > 0:
            return
        target = self.pick_target(game.enemies)
        if target is None:
            return
        s = self.stats
        game.projectiles.append(Projectile(
            self.pos, target, s["proj_speed"], s["damage"], s["aoe_radius"],
            s["slow"], s["slow_duration"], s["money_per_hit"], self.color, self))
        self.cooldown_left = s["cooldown"]
        self.kick = 0.1
        game.fx.fired(self)
        self.aim = (target.pos - self.pos).normalize() if target.pos != self.pos else self.aim

    # ----------------------------------------------------------------- draw
    def draw(self, surface: pygame.Surface, selected: bool = False) -> None:
        x, y = int(self.pos.x), int(self.pos.y)
        r = TOWER_RADIUS + int(4 * self.kick / 0.1)  # squash-and-stretch when firing
        pygame.draw.ellipse(surface, (66, 120, 66), (x - r, y + r - 7, 2 * r, 12))  # ground shadow
        img = sprite(f"towers/{self.kind}", 2 * TOWER_RADIUS + 10)
        if img is not None:
            if r != TOWER_RADIUS:
                img = pygame.transform.smoothscale(img, (img.get_width() * r // TOWER_RADIUS, img.get_height() * r // TOWER_RADIUS))
            surface.blit(img, img.get_rect(center=(x, y)))
            if selected:
                pygame.draw.circle(surface, (255, 255, 255), (x, y), r + 2, 2)
        else:
            dark = tuple(c // 2 for c in self.color)
            tip = self.pos + self.aim * (TOWER_RADIUS + 8)
            pygame.draw.line(surface, dark, (x, y), (int(tip.x), int(tip.y)), 7)  # barrel
            pygame.draw.circle(surface, self.color, (x, y), r)
            pygame.draw.circle(surface, (255, 255, 255) if selected else (20, 20, 30),
                               (x, y), r, 3 if selected else 2)
            draw_text(surface, self.name[0], (x, y), 26, (15, 15, 25), center=True)
        pips = [(STACKS[n]["color"]) for n, c in self.stacks.items() for _ in range(c)]
        for i, color in enumerate(pips):  # one pip per active stack, above the tower
            px = x - (len(pips) - 1) * 4 + i * 8
            pygame.draw.circle(surface, color, (px, y - TOWER_RADIUS - 7), 3)
            pygame.draw.circle(surface, (20, 20, 30), (px, y - TOWER_RADIUS - 7), 3, 1)
        if self.stats["income_per_sec"] > 0:  # progress bar to the next income payout
            frac = min(1.0, self.income_timer / INCOME_INTERVAL_SECONDS)
            pygame.draw.rect(surface, (30, 32, 40), (x - 15, y - TOWER_RADIUS - 11, 30, 5))
            pygame.draw.rect(surface, (255, 215, 80), (x - 15, y - TOWER_RADIUS - 11, int(30 * frac), 5))
        if self.activity:  # gold badge = busy with a preparation activity
            pygame.draw.circle(surface, (240, 200, 70), (x + 13, y - 13), 6)
            pygame.draw.circle(surface, (20, 20, 30), (x + 13, y - 13), 6, 1)
        draw_text(surface, f"{self.tiers[0]}/{self.tiers[1]}", (x, y + TOWER_RADIUS + 8),
                  18, (255, 255, 255), center=True)
