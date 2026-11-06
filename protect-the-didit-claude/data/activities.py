"""Preparation-phase activities (one per tower at a time) and the stacks they build.

Activity fields: tower (kind), name, interval (seconds per tick), gives, counts_toward_limit,
implemented, unlock (optional: (path_index, tier) the tower must have). `gives` is ("stack", stack_name) -> +1 stack per tick (auto-stops at max),
or ("knowledge", amount) -> ball knowledge added to the player's pool per tick.
`counts_toward_limit=False` is reserved for Romli's future manual activities.
Activities only run during preparation and stop automatically when the wave starts.

Stacks: per-stack stat mods are multiplied by the stack count (see Tower.recompute_stats).
`reset_on_wave_end=True`: stacks last for the next battle only. Set False to keep them.
"""

STACKS = {
    "laziness": {"label": "Laziness", "max": 5, "color": (120, 170, 220),
                 "mods": {"slow": 0.04, "slow_duration": 0.2}, "reset_on_wave_end": True},
    "blessing": {"label": "Blessing", "max": 5, "color": (255, 235, 150),
                 "mods": {"damage": 0.15, "cooldown": -0.04}, "reset_on_wave_end": True},
}

ACTIVITIES = {
    "zizi_sloth": {"tower": "zizi", "name": "Slothing", "interval": 5.0,
                   "gives": ("stack", "laziness"), "counts_toward_limit": True, "implemented": True,
                   "unlock": (1, 2)},  # Sin of Sloth (B) tier 2
    "zizi_pray": {"tower": "zizi", "name": "Praying", "interval": 5.0,
                  "gives": ("stack", "blessing"), "counts_toward_limit": True, "implemented": True,
                  "unlock": (0, 2)},  # Recitation (A) tier 2
    "jalu_larp": {"tower": "jalu", "name": "Larping", "interval": 1.0,
                  "gives": ("knowledge", 1), "counts_toward_limit": True, "implemented": True},
}


def activities_for(tower_kind: str) -> list[tuple[str, dict]]:
    """All (activity_id, data) pairs a tower kind can run, in definition order."""
    return [(i, d) for i, d in ACTIVITIES.items() if d["tower"] == tower_kind]
