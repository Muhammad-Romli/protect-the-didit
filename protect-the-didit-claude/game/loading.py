"""Cache pre-warming for the browser build: procedural sprites are normally built lazily on first use,
which would hitch the first time a new enemy kind shows up (much worse in WebAssembly)."""
from __future__ import annotations

from typing import Iterator


def warm_steps() -> Iterator[float]:
    """Generator: builds the enemy and tower sprite caches in small chunks, yielding progress 0..1."""
    from data.enemies import ENEMIES
    from data.settings import TOWER_RADIUS
    from data.towers import TOWERS
    from game import models, sprites_proc as sp

    total = len(ENEMIES) + len(TOWERS)
    done = 0
    for kind, d in ENEMIES.items():
        stages = (2, 1, 0) if d.get("armor") else (0,)  # Reinforced Didit: full / damaged / none
        for armored in stages:
            for frame in range(sp.FRAMES):
                for left in (False, True):
                    sp.enemy_sprite(kind, d["radius"], d["color"], frame, left, False, armored)
        done += 1
        yield done / total
    for kind, d in TOWERS.items():
        sp.tower_sprite(kind, TOWER_RADIUS, d["color"])
        for path in (0, 1):  # costumes of every upgrade path/tier
            for tier in range(1, 5):
                look = (path, tier)
                sp.tower_sprite(kind, TOWER_RADIUS, d["color"], look)
                models.weapon_image(kind, look, 0, False)
                models.projectile(kind, look)
        done += 1
        yield done / total
