"""10 waves. Each wave is a list of groups:
(enemy_type, count, spawn_interval_seconds, start_delay_seconds).

WAVE_SCALING[i] = (hp_mult, speed_mult) for wave i+1: weak early waves (a single Jalu can hold
wave 1-2), steadily stronger late waves. It stacks with the preparation-phase ramp."""

WAVES = [
    [("normal", 6, 1.3, 0)],                                                         # 1
    [("normal", 10, 1.0, 0)],                                                        # 2
    [("normal", 14, 0.8, 0)],                                                        # 3
    [("normal", 10, 0.9, 0), ("fast", 6, 0.8, 8)],                                   # 4
    [("normal", 12, 0.8, 0), ("trojan", 2, 2.5, 6)],                                 # 5  Trojan intro
    [("normal", 12, 0.8, 0), ("tanky", 4, 2.0, 6), ("trojan", 3, 2.0, 14)],          # 6
    [("fast", 12, 0.6, 0), ("tanky", 8, 1.6, 4), ("trojan", 4, 1.8, 10)],            # 7
    [("normal", 20, 0.6, 0), ("fast", 15, 0.5, 5), ("tanky", 8, 1.5, 8),
     ("trojan", 5, 1.5, 12)],                                                        # 8
    [("normal", 20, 0.55, 0), ("fast", 18, 0.5, 4), ("tanky", 10, 1.3, 6),
     ("trojan", 6, 1.2, 10), ("trojan_trojan", 1, 0, 18)],                           # 9  mini-boss
    [("normal", 20, 0.6, 0), ("fast", 15, 0.5, 4), ("tanky", 12, 1.2, 6),
     ("trojan", 6, 1.2, 8), ("trojan_trojan", 2, 12, 10), ("boss", 1, 0, 15)],       # 10 boss
]

WAVE_SCALING = [
    (0.50, 0.85), (0.60, 0.88), (0.75, 0.92), (0.90, 0.96), (1.05, 1.00),
    (1.25, 1.03), (1.50, 1.06), (1.80, 1.09), (2.20, 1.12), (2.80, 1.15),
]
