"""Enemy stats. Every enemy Didit is a black / dark purple hamster (the original white Didit sits next to the Snack Stash); kinds differ by size and accessories
(game/sprites_proc.py). Base `money` is multiplied by BOUNTY_MULT and the wave growth in data/settings.py.

Optional fields:
  spawns      (kind, count) released where the enemy dies (not when it leaks)
  fast        counts as a "fast" enemy (Jalu's Speed Against Time slows these to normal speed)
  mini        miniboss: always shows a health bar, but is not immune like a boss
  armor       hits needed to break its armor; while armored, hits only chip the armor (no HP damage)
  steal       base money stolen from the player when it leaks (scaled by the wave like bounties)
  decel       (boost, seconds): starts (1 + boost) x faster and slows down to normal speed over `seconds`
"""

ENEMIES = {
    "normal": {"name": "Normal Didit", "hp": 10, "speed": 60, "stash_damage": 1,
               "money": 5, "radius": 11, "color": (58, 30, 84), "is_boss": False},
    "fast": {"name": "Fast Didit", "hp": 6, "speed": 120, "stash_damage": 1,
             "money": 6, "radius": 9, "color": (26, 20, 34), "is_boss": False, "fast": True},
    "tanky": {"name": "Tanky Didit", "hp": 60, "speed": 40, "stash_damage": 3,
              "money": 15, "radius": 21, "color": (74, 40, 108), "is_boss": False},
    "boss": {"name": "Boss Didit", "hp": 700, "speed": 30, "stash_damage": 25,
             "money": 150, "radius": 36, "color": (34, 18, 52), "is_boss": True},
    # Rich Didit: top hat, mustache, bag of money. Pays a lot when killed, steals money when it leaks.
    "rich": {"name": "Rich Didit", "hp": 90, "speed": 52, "stash_damage": 2,
             "money": 45, "radius": 15, "color": (50, 28, 74), "is_boss": False, "steal": 40},
    # Speedster Didit: very fast boss that slows down the longer it runs.
    "speedster": {"name": "Speedster Didit", "hp": 320, "speed": 60, "stash_damage": 20,
                  "money": 120, "radius": 19, "color": (30, 24, 60), "is_boss": True,
                  "fast": True, "decel": (3.2, 13.0)},
    # Reinforced Didit: 10 hits to break the armor, then it can be damaged.
    "reinforced": {"name": "Reinforced Didit", "hp": 40, "speed": 48, "stash_damage": 2,
                   "money": 14, "radius": 14, "color": (44, 34, 64), "is_boss": False, "armor": 10},
    # Trojan Didit: a bare-wood Didit statue on wheels (not painted); a miniboss. 5 normal Didits climb out when it breaks.
    "trojan": {"name": "Trojan Didit", "hp": 150, "speed": 40, "stash_damage": 8,
               "money": 40, "radius": 30, "color": (184, 126, 66), "is_boss": False, "mini": True,
               "spawns": ("normal", 5)},
    # Trojan Trojan Didit: huge boss horse; 3 Trojan Didits come out.
    "trojan_trojan": {"name": "Trojan Trojan Didit", "hp": 600, "speed": 24, "stash_damage": 40,
                      "money": 150, "radius": 46, "color": (184, 126, 66), "is_boss": True,
                      "spawns": ("trojan", 3)},
}

NORMAL_SPEED = ENEMIES["normal"]["speed"]  # "walk like normal" (Jalu's Speed Against Time)
