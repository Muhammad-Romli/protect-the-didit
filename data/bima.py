"""Bima (Mathematician) numbers. Everything tunable lives here; logic is in game/bima.py.
All values are placeholders to be tuned by playtest. D = Bima's current damage stat.

Index = tier of the chosen path (0..4). Path A = Graph, path B = Geometry. Bima may only use ONE path
(Tower.can_upgrade blocks the other one completely).
"""

UNIT = 20            # pixels per world unit on the Cartesian axis

GRAPH = {            # tier:        0     1     2     3     4
    "range_units":  [0,    0,    14,   16,   18],
    "brain_max":    [0,    0,    80,   100,  120],
    "regen":        [0,    0,    6,    7,    8],      # Brain Energy per second (preparation + battle)
    "cost_base":    [0,    0,    4,    4,    4],
    "cost_per_unit": [0,   0,    1.3,  1.2,  1.0],    # per world unit of arc length
    "dmg_mult":     [0,    0,    3.0,  3.0,  3.5],    # x D per target
    "falloff":      [1,    1,    0.90, 0.92, 0.94],   # damage multiplier per target already hit
    "falloff_floor": 0.4,
    "max_targets":  [0,    0,    5,    8,    10],
    "shot_cooldown": [0,   0,    1.2,  1.0,  0.8],
    "func_level":   [0,    0,    2,    3,    4],      # which functions the parser allows (abs/sqrt = 2, trig = 4)
    "speed_px": 900,                                  # how fast the curve is drawn / travels
    "half_width": 4,                                  # curve thickness for hit tests (px)
    "miss_refund": 0.5,                               # fraction of the cost returned if nothing was hit
    "max_points": 900, "px_step": 2.0, "max_depth": 4, "jump_px": 60,
}

GEOMETRY = {         # tier:        0     1     2     3     4
    "vuln":         [0,    0,    0.25, 0.40, 0.40],   # square: +damage taken
    "vuln_dur":     [0,    0,    2.0,  2.5,  2.5],
    "vuln_cap": 1.6,                                  # total damage-taken multiplier cap (all sources)
    "triangle_mult": [1,   1,    1.5,  2.0,  2.0],    # triangle: damage multiplier
    "circle_slow":  [0,    0,    0.30, 0.45, 0.45],
    "circle_slow_dur": [0, 0,    1.5,  2.0,  2.0],
    "collision_flat": [0,  0,    1.5,  2.0,  2.0],    # x D
    "collision_pct": [0,   0,    0.05, 0.07, 0.07],   # x enemy max HP
    "collision_pct_cap": [0, 0,  4,    6,    6],      # x D, caps the percent part only
    "collision_total_cap": 10,                        # x D, caps the whole collision
    "boss_pct_mult": 0.3,
    "collision_cd": 3.0, "collision_cd_boss": 5.0,    # per-enemy cooldown between collisions
    "windup": 0.10,                                   # seconds between trigger and damage (VFX converge)
    "hitstop": 0.05,
}

ABILITIES = {
    "cube_active": {"name": "Cube", "cooldown": 22.0, "aim": True, "hp_mult_d": 40, "duration": 8.0, "max_active": 2,
                    "attackers": 3, "thorns_mult_d": 0.5, "thorns_every": 0.5, "max_stall": 6.0, "snap_px": 48,
                    "place_range": 280, "min_from_spawn": 160, "min_from_base": 100, "boss_dps_mult": 2.0},
    "pyramid_active": {"name": "Pyramid", "cooldown": 24.0, "aim": False, "duration": 6.0,
                       "damage": 0.8, "attack_speed": 0.6},
    "sphere_active": {"name": "Sphere", "cooldown": 30.0, "aim": True, "shield_pct": 0.12, "shield_time": 10.0,
                      "zone_r": 90, "zone_time": 5.0, "trap": 2.0, "trap_boss": 0.6, "immune": 3.0,
                      "immune_boss": 6.0, "max_trapped": 15, "place_range": 320},
    "global_lockout": 3.0,   # after any Bima ability, the others wait this long
}

# Pattern presets (Graph Lv3). {a} is the player-adjustable parameter.
PATTERNS = [
    ("Line", "{a}*x", [0.5, 1, 1.5, 2, -0.5, -1, -2], 1),
    ("Parabola", "{a}*x^2", [0.05, 0.1, 0.2, -0.05, -0.1, -0.2], 0.1),
    ("Cubic", "{a}*x^3", [0.005, 0.01, 0.02, -0.01], 0.01),
    ("V shape", "{a}*abs(x)", [0.5, 1, 1.5, -0.5, -1], 1),
    ("Root", "{a}*sqrt(x)", [1, 2, 3, -1, -2], 2),
    ("Wave", "{a}*sin(x)", [1, 2, 3, 4], 2),       # needs Lv4 (sin)
    ("Fast wave", "2*sin({a}*x)", [1, 2, 3], 2),   # needs Lv4
]
