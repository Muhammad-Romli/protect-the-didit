"""Turns data/waves.py into timed spawn events."""
from __future__ import annotations

from data.waves import WAVES


class WaveManager:
    def __init__(self) -> None:
        self.number = 0          # waves started so far (1-based once running)
        self.active = False
        self._queue: list[tuple[float, str]] = []
        self._time = 0.0

    @property
    def total(self) -> int:
        return len(WAVES)

    @property
    def can_start(self) -> bool:
        return not self.active and self.number < self.total

    @property
    def all_spawned(self) -> bool:
        return not self._queue

    def start_next(self) -> bool:
        if not self.can_start:
            return False
        groups = WAVES[self.number]
        self.number += 1
        self.active = True
        self._time = 0.0
        events = [(delay + i * interval, kind)
                  for kind, count, interval, delay in groups for i in range(count)]
        self._queue = sorted(events)
        return True

    def update(self, dt: float) -> list[str]:
        """Advance time; return enemy kinds that should spawn now."""
        if not self.active:
            return []
        self._time += dt
        spawned: list[str] = []
        while self._queue and self._queue[0][0] <= self._time:
            spawned.append(self._queue.pop(0)[1])
        return spawned

    def finish(self) -> None:
        self.active = False
        self._queue.clear()
