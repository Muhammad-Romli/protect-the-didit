"""30 waves. Each wave is a list of groups: (enemy_type, count, spawn_interval_seconds, start_delay_seconds).

Introductions:  6 Rich Didit | 8 Reinforced | 10 BOSS | 13 Trojan (miniboss) | 17 Speedster | 22 Trojan Trojan
Special rounds: 7 Stampede | 17 Speed Rush | 25 Iron Parade  (double wave-clear bonus, named banner)
Rich Didits show up in the round BEFORE each hard round (6, 9, 12, 16, 21, 24): kill them for a lot of
money, or they steal it. From wave ~18 minibosses/bosses appear as regular enemies.

WAVE_SCALING[i] = (hp_mult, speed_mult) for wave i+1; it stacks with the preparation-wait penalty."""

WAVES = [
    [("normal", 6, 1.3, 0)],                                                                      # 1
    [("normal", 10, 1.0, 0)],                                                                     # 2
    [("normal", 14, 0.8, 0)],                                                                     # 3
    [("normal", 10, 0.9, 0), ("fast", 6, 0.8, 8)],                                                # 4
    [("normal", 14, 0.7, 0), ("fast", 8, 0.7, 6)],                                                # 5
    [("normal", 12, 0.8, 0), ("tanky", 4, 2.0, 5), ("rich", 1, 0, 18)],                           # 6  Rich intro
    [("normal", 50, 0.22, 0), ("fast", 30, 0.2, 6)],                                              # 7  SPECIAL: Stampede
    [("normal", 16, 0.6, 0), ("reinforced", 4, 2.2, 4), ("tanky", 6, 1.6, 10)],                   # 8  Reinforced intro
    [("fast", 18, 0.5, 0), ("tanky", 8, 1.4, 4), ("reinforced", 5, 1.8, 8), ("rich", 2, 4, 14)],  # 9
    [("normal", 20, 0.55, 0), ("tanky", 8, 1.3, 4), ("reinforced", 6, 1.6, 8), ("boss", 1, 0, 16)],  # 10 BOSS intro
    [("normal", 24, 0.5, 0), ("fast", 20, 0.45, 3), ("tanky", 10, 1.2, 6), ("reinforced", 6, 1.5, 9)],  # 11
    [("normal", 20, 0.5, 0), ("fast", 16, 0.5, 4), ("reinforced", 8, 1.4, 6), ("tanky", 10, 1.2, 10),
     ("rich", 2, 3, 16)],                                                                         # 12
    [("normal", 24, 0.5, 0), ("tanky", 8, 1.2, 4), ("trojan", 1, 0, 12)],                         # 13 Trojan intro
    [("fast", 25, 0.4, 0), ("reinforced", 10, 1.2, 3), ("tanky", 10, 1.2, 8), ("trojan", 1, 0, 14)],  # 14
    [("normal", 30, 0.4, 0), ("reinforced", 10, 1.2, 4), ("trojan", 2, 6, 8), ("tanky", 12, 1.0, 10)],  # 15
    [("fast", 24, 0.4, 0), ("tanky", 12, 1.0, 3), ("reinforced", 10, 1.1, 6), ("trojan", 2, 5, 10),
     ("rich", 3, 2.5, 12)],                                                                       # 16
    [("fast", 40, 0.3, 0), ("speedster", 1, 0, 8), ("fast", 30, 0.25, 16), ("speedster", 1, 0, 24)],  # 17 Speedster + SPECIAL: Speed Rush
    [("normal", 30, 0.4, 0), ("tanky", 14, 0.9, 3), ("reinforced", 12, 1.0, 5), ("trojan", 2, 5, 9)],  # 18
    [("fast", 30, 0.35, 0), ("reinforced", 14, 0.9, 3), ("tanky", 14, 0.9, 6), ("trojan", 3, 4, 10)],  # 19
    [("normal", 30, 0.4, 0), ("tanky", 14, 0.9, 3), ("reinforced", 14, 0.9, 6), ("trojan", 2, 5, 12),
     ("boss", 1, 0, 10)],                                                                         # 20 (boss as a regular enemy)
    [("fast", 30, 0.35, 0), ("tanky", 16, 0.9, 3), ("reinforced", 16, 0.9, 6), ("trojan", 3, 4, 10),
     ("rich", 3, 2, 14)],                                                                         # 21
    [("normal", 30, 0.4, 0), ("tanky", 14, 0.9, 4), ("trojan", 2, 4, 8), ("trojan_trojan", 1, 0, 16)],  # 22 Trojan Trojan intro
    [("fast", 30, 0.3, 0), ("reinforced", 18, 0.8, 3), ("speedster", 1, 0, 10), ("tanky", 16, 0.8, 6),
     ("trojan", 3, 4, 12)],                                                                       # 23
    [("normal", 35, 0.35, 0), ("tanky", 18, 0.8, 3), ("reinforced", 18, 0.8, 5), ("trojan", 3, 4, 9),
     ("boss", 1, 0, 15), ("rich", 3, 2, 18)],                                                     # 24
    [("reinforced", 40, 0.6, 0), ("tanky", 20, 0.9, 5), ("trojan", 4, 3, 12), ("trojan_trojan", 1, 0, 22)],  # 25 SPECIAL: Iron Parade
    [("normal", 35, 0.35, 0), ("fast", 30, 0.3, 4), ("tanky", 20, 0.8, 5), ("reinforced", 20, 0.8, 8),
     ("trojan", 4, 3, 12), ("trojan_trojan", 1, 0, 20)],                                          # 26
    [("fast", 40, 0.25, 0), ("speedster", 2, 6, 8), ("reinforced", 24, 0.7, 4), ("trojan", 4, 3, 10),
     ("boss", 1, 0, 18)],                                                                         # 27
    [("normal", 40, 0.3, 0), ("tanky", 24, 0.7, 3), ("reinforced", 24, 0.7, 6), ("trojan", 5, 3, 10),
     ("trojan_trojan", 2, 8, 14)],                                                                # 28
    [("fast", 40, 0.25, 0), ("tanky", 24, 0.7, 3), ("reinforced", 24, 0.7, 4), ("trojan", 5, 3, 8),
     ("boss", 2, 10, 12), ("speedster", 2, 8, 16)],                                               # 29
    [("normal", 40, 0.3, 0), ("tanky", 24, 0.7, 3), ("reinforced", 24, 0.7, 5), ("trojan", 6, 2.5, 6),
     ("trojan_trojan", 2, 8, 12), ("boss", 2, 12, 16), ("speedster", 2, 10, 20)],                 # 30 finale
]

# (hp_mult, speed_mult): weak early waves (one Jalu holds 1-2), then steady growth.
_EARLY = [0.50, 0.60, 0.70, 0.80, 0.90, 1.00]
WAVE_SCALING = [
    (_EARLY[n - 1] if n <= 6 else 1.0 * 1.075 ** (n - 6),
     min(1.30, 0.85 + 0.03 * (n - 1) if n <= 6 else 1.0 + 0.008 * (n - 6)))
    for n in range(1, 31)
]

SPECIAL_WAVES = {7: "STAMPEDE", 17: "SPEED RUSH", 25: "IRON PARADE"}   # banner names, double clear bonus
SPECIAL_BONUS_MULT = 2.0
NEW_ENEMY_WAVES = {6: "rich", 8: "reinforced", 10: "boss", 13: "trojan", 17: "speedster", 22: "trojan_trojan"}
