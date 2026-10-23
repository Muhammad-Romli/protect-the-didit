"""10 waves. Each wave is a list of groups:
(enemy_type, count, spawn_interval_seconds, start_delay_seconds)."""

WAVES = [
    [("normal", 8, 1.2, 0)],                                                         # 1
    [("normal", 12, 1.0, 0)],                                                        # 2
    [("normal", 18, 0.8, 0)],                                                        # 3
    [("normal", 12, 0.9, 0), ("fast", 6, 0.8, 10)],                                  # 4
    [("normal", 15, 0.8, 0), ("fast", 12, 0.6, 8)],                                  # 5
    [("normal", 15, 0.8, 0), ("tanky", 4, 2.0, 6)],                                  # 6
    [("fast", 12, 0.6, 0), ("tanky", 8, 1.6, 4), ("normal", 15, 0.7, 12)],           # 7
    [("normal", 20, 0.6, 0), ("fast", 15, 0.5, 5), ("tanky", 8, 1.5, 8)],            # 8
    [("normal", 25, 0.5, 0), ("fast", 20, 0.5, 4), ("tanky", 12, 1.2, 6)],           # 9
    [("normal", 20, 0.6, 0), ("fast", 15, 0.5, 4), ("tanky", 12, 1.2, 6),
     ("boss", 1, 0, 15)],                                                            # 10
]
