"""Tower: stats are base + sum of unlocked stat_mods (data-driven, no per-upgrade classes)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import pygame

from data.settings import (MAX_OFF_PATH_TIER, MAX_SLOW, MAX_TIER, MIN_COOLDOWN,
                           SELL_REFUND, TOWER_RADIUS)
from data.towers import DEFAULT_STATS, TOWERS
from game.effects import EFFECTS
from game.enemy import Enemy
from game.projectile import Projectile
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
        stats["cooldown"] = max(MIN_COOLDOWN, stats["cooldown"])
        stats["slow"] = min(MAX_SLOW, stats["slow"])
        self.stats = stats
        self.effects = effects

    @property
    def sell_value(self) -> int:
        return int(self.spent * SELL_REFUND)

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

    def upgrade(self, path: int) -> int:
        """Apply the next tier. Caller checks can_upgrade() and pays. Returns cost."""
        up = self.next_upgrade(path)
        assert up is not None
        self.tiers[path] += 1
        self.spent += up["cost"]
        self.recompute_stats()
        return up["cost"]

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
        self.cooldown_left = max(0.0, self.cooldown_left - dt)
        if self.cooldown_left > 0:
            return
        target = self.pick_target(game.enemies)
        if target is None:
            return
        s = self.stats
        game.projectiles.append(Projectile(
            self.pos, target, s["proj_speed"], s["damage"], s["aoe_radius"],
            s["slow"], s["slow_duration"], s["money_per_hit"], self.color))
        self.cooldown_left = s["cooldown"]

    # ----------------------------------------------------------------- draw
    def draw(self, surface: pygame.Surface, selected: bool = False) -> None:
        x, y = int(self.pos.x), int(self.pos.y)
        pygame.draw.circle(surface, self.color, (x, y), TOWER_RADIUS)
        pygame.draw.circle(surface, (255, 255, 255) if selected else (20, 20, 30),
                           (x, y), TOWER_RADIUS, 3 if selected else 2)
        draw_text(surface, self.name[0], (x, y), 26, (15, 15, 25), center=True)
        draw_text(surface, f"{self.tiers[0]}/{self.tiers[1]}", (x, y + TOWER_RADIUS + 8),
                  18, (255, 255, 255), center=True)
