"""Player profile: Snack Coins, permanent shop levels, in-game item stock and run stats.

Separate from the autosave on purpose (a run's save is deleted when the run ends; the profile never is).
Storage: browser localStorage on the web build, `profile.json` next to the code on desktop.
`Profile()` is a blank in-memory profile (tests, and Game's default); `Profile.load()` is the real, saving one.
Loading is defensive: unknown ids are dropped, numbers are clamped, a damaged file gives a fresh profile.
"""
from __future__ import annotations

import json
import os

from data.shop import ITEMS, MAX_STOCK, PERMANENT
from game import web

VERSION = 1
KEY = "protect_the_didit_profile"
PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "profile.json")
MAX_COINS = 999_999


class Profile:
    def __init__(self, persist: bool = False) -> None:
        self.persist = persist
        self.coins = 0
        self.perm: dict[str, int] = {}     # permanent item id -> level bought
        self.stock: dict[str, int] = {}    # in-game item id -> how many you hold
        self.runs = self.wins = self.best_wave = 0

    # ------------------------------------------------------------- storage
    @classmethod
    def load(cls) -> "Profile":
        p = cls(persist=True)
        try:
            if web.IS_WEB:
                raw = web.storage_get(KEY)
            else:
                with open(PATH, encoding="utf-8") as f:
                    raw = f.read()
            data = json.loads(raw) if raw else None
            if isinstance(data, dict) and data.get("version") == VERSION:
                p._apply(data)
        except (OSError, ValueError, TypeError):
            pass
        return p

    def _apply(self, d: dict) -> None:
        self.coins = max(0, min(MAX_COINS, int(d.get("coins", 0))))
        self.perm = {k: max(0, min(len(PERMANENT[k]["costs"]), int(v)))
                     for k, v in dict(d.get("perm", {})).items() if k in PERMANENT}
        self.stock = {k: max(0, min(MAX_STOCK, int(v))) for k, v in dict(d.get("stock", {})).items() if k in ITEMS}
        self.runs, self.wins, self.best_wave = (max(0, int(d.get(k, 0))) for k in ("runs", "wins", "best_wave"))

    def save(self) -> bool:
        if not self.persist:
            return False
        text = json.dumps({"version": VERSION, "coins": self.coins, "perm": self.perm, "stock": self.stock,
                           "runs": self.runs, "wins": self.wins, "best_wave": self.best_wave}, separators=(",", ":"))
        if web.IS_WEB:
            return web.storage_set(KEY, text)
        try:
            tmp = PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(text)
            os.replace(tmp, PATH)  # atomic: a crash while saving never leaves a half-written file
            return True
        except OSError:
            return False

    # ----------------------------------------------------------- permanent
    def level(self, pid: str) -> int:
        return self.perm.get(pid, 0)

    def bonus(self, pid: str) -> float:
        """Total value of a permanent item right now (levels x per-level value); 0 when not bought."""
        return self.level(pid) * PERMANENT[pid]["per_level"]

    def next_cost(self, pid: str) -> int | None:
        costs = PERMANENT[pid]["costs"]
        lvl = self.level(pid)
        return costs[lvl] if lvl < len(costs) else None

    def buy_perm(self, pid: str) -> str:
        """'ok' | 'maxed' | 'poor'."""
        cost = self.next_cost(pid)
        if cost is None:
            return "maxed"
        if self.coins < cost:
            return "poor"
        self.coins -= cost
        self.perm[pid] = self.level(pid) + 1
        self.save()
        return "ok"

    # ------------------------------------------------------------ in-game
    def owned(self, iid: str) -> int:
        return self.stock.get(iid, 0)

    def buy_item(self, iid: str) -> str:
        """'ok' | 'full' | 'poor'."""
        if self.owned(iid) >= MAX_STOCK:
            return "full"
        if self.coins < ITEMS[iid]["cost"]:
            return "poor"
        self.coins -= ITEMS[iid]["cost"]
        self.stock[iid] = self.owned(iid) + 1
        self.save()
        return "ok"

    def use_item(self, iid: str) -> bool:
        if self.owned(iid) <= 0:
            return False
        self.stock[iid] -= 1
        self.save()
        return True

    # ---------------------------------------------------------------- runs
    def record_run(self, coins: int, won: bool, waves_cleared: int) -> None:
        self.coins = min(MAX_COINS, self.coins + coins)
        self.runs += 1
        self.wins += 1 if won else 0
        self.best_wave = max(self.best_wave, waves_cleared)
        self.save()
