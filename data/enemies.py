"""Enemy stats. All enemies are Didit variants (placeholder: colored circles)."""

ENEMIES = {
    "normal": {"name": "Normal Didit", "hp": 10, "speed": 60, "stash_damage": 1,
               "money": 5, "radius": 11, "color": (214, 160, 90), "is_boss": False},
    "fast": {"name": "Fast Didit", "hp": 6, "speed": 120, "stash_damage": 1,
             "money": 6, "radius": 9, "color": (250, 220, 80), "is_boss": False},
    "tanky": {"name": "Tanky Didit", "hp": 60, "speed": 40, "stash_damage": 3,
              "money": 15, "radius": 16, "color": (120, 80, 50), "is_boss": False},
    "boss": {"name": "Boss Didit", "hp": 600, "speed": 30, "stash_damage": 25,
             "money": 150, "radius": 28, "color": (200, 40, 40), "is_boss": True},
}
