"""Enemy stats. All enemies are Didit variants (procedural sprites in game/sprites_proc.py).

`spawns`: optional (kind, count) released where the enemy dies (not when it leaks).
Base `money` is multiplied by BOUNTY_MULT and the wave growth in data/settings.py.
"""

ENEMIES = {
    "normal": {"name": "Normal Didit", "hp": 10, "speed": 60, "stash_damage": 1,
               "money": 5, "radius": 11, "color": (214, 160, 90), "is_boss": False},
    "fast": {"name": "Fast Didit", "hp": 6, "speed": 120, "stash_damage": 1,
             "money": 6, "radius": 9, "color": (250, 220, 80), "is_boss": False},
    "tanky": {"name": "Tanky Didit", "hp": 60, "speed": 40, "stash_damage": 3,
              "money": 15, "radius": 16, "color": (120, 80, 50), "is_boss": False},
    "boss": {"name": "Boss Didit", "hp": 600, "speed": 30, "stash_damage": 25,
             "money": 150, "radius": 28, "color": (200, 40, 40), "is_boss": True},
    # Trojan Didit: a wooden horse; when destroyed 5 normal Didits climb out.
    "trojan": {"name": "Trojan Didit", "hp": 28, "speed": 48, "stash_damage": 3,
               "money": 8, "radius": 17, "color": (176, 120, 62), "is_boss": False,
               "spawns": ("normal", 5)},
    # Trojan Trojan Didit: a huge boss horse; when destroyed 3 Trojan Didits come out.
    "trojan_trojan": {"name": "Trojan Trojan Didit", "hp": 350, "speed": 26, "stash_damage": 30,
                      "money": 80, "radius": 30, "color": (196, 140, 60), "is_boss": True,
                      "spawns": ("trojan", 3)},
}
