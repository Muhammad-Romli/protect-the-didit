"""Autosave: a snapshot after every SAVE_EVERY_WAVES-th cleared wave (data/settings.py).

Snapshots are only taken between waves, so there are no enemies / projectiles / cubes to store: money, knowledge,
stash HP, the wave number and the towers (position, tiers, targeting, activity, Bima's formula). Storage is browser
localStorage on the web build and `savegame.json` next to the code on desktop. Loading is defensive: a damaged or
outdated save is ignored (the title screen then simply offers NEW GAME).
"""
from __future__ import annotations

import json
import os

from data.activities import ACTIVITIES, STACKS
from data.settings import MAX_TIER
from data.towers import TOWERS
from game import web

VERSION = 2  # 2: Jalu path A became Mark (old Thor tiers would load as Mark) and Jalu is locked to one path
KEY = "protect_the_didit_save"
PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "savegame.json")


# ------------------------------------------------------------------ storage
def read() -> dict | None:
    try:
        if web.IS_WEB:
            raw = web.storage_get(KEY)
        else:
            with open(PATH, encoding="utf-8") as f:
                raw = f.read()
        data = json.loads(raw) if raw else None
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get("version") == VERSION else None


def write(data: dict) -> bool:
    text = json.dumps(data, separators=(",", ":"))
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


def clear() -> None:
    if web.IS_WEB:
        web.storage_remove(KEY)
        return
    try:
        os.remove(PATH)
    except OSError:
        pass


def summary() -> dict | None:
    """What the title screen shows for CONTINUE: {'wave': N, 'money': M, 'towers': K} or None."""
    d = read()
    if d is None:
        return None
    try:
        return {"wave": int(d["wave"]), "money": int(d["money"]), "towers": len(d["towers"])}
    except (KeyError, TypeError, ValueError):
        return None


# ----------------------------------------------------------------- snapshot
def snapshot(game) -> dict:
    towers = []
    for t in game.towers:
        d = {"kind": t.kind, "x": round(t.pos.x, 1), "y": round(t.pos.y, 1), "tiers": list(t.tiers),
             "spent": int(t.spent), "targeting": t.targeting, "stacks": dict(t.stacks),
             "income_timer": round(t.income_timer, 2), "activity": t.activity,
             "activity_time": round(t.activity_time, 2), "activity_acc": round(t.activity_acc, 2),
             "active_cd": {k: round(v, 2) for k, v in t.active_cd.items()}}
        if t.kind == "bima":
            d["bima"] = {"formula": t.formula, "dir": t.graph_dir, "shape": t.shape_i,
                         "brain": round(t.brain, 2), "brain_init": bool(t.brain_init)}
        towers.append(d)
    return {"version": VERSION, "wave": game.waves.number, "money": int(game.money),
            "knowledge": int(game.ball_knowledge), "stash_hp": int(game.stash_hp),
            "larp_tip_shown": bool(game.larp_tip_shown), "towers": towers}


def autosave(game) -> bool:
    return write(snapshot(game))


# ------------------------------------------------------------------ restore
def restore(game, data: dict) -> bool:
    """Rebuild the game from a snapshot. Returns False (and leaves a fresh game) if the data is not usable."""
    from game.tower import Tower
    from game.utils import Vec
    try:
        wave = int(data["wave"])
        if not 0 <= wave < game.waves.total:  # a finished game has nothing to continue
            return False
        built = []
        for d in data["towers"]:
            kind = d["kind"]
            if kind not in TOWERS:
                return False
            t = Tower(kind, Vec(float(d["x"]), float(d["y"])), game.sell_refund())
            t.tiers = [max(0, min(MAX_TIER, int(v))) for v in d["tiers"]][:2]
            if len(t.tiers) != 2:
                return False
            t.spent = int(d["spent"])
            t.targeting = d["targeting"] if d.get("targeting") in ("first", "last", "strong", "weak", "close") else "first"
            t.stacks = {n: int(c) for n, c in d.get("stacks", {}).items() if n in STACKS}
            t.income_timer = float(d.get("income_timer", 0.0))
            act = d.get("activity")
            if act in ACTIVITIES and ACTIVITIES[act]["tower"] == kind:
                t.activity = act
                t.activity_time = float(d.get("activity_time", 0.0))
                t.activity_acc = float(d.get("activity_acc", 0.0))
            t.active_cd = {str(k): float(v) for k, v in d.get("active_cd", {}).items()}
            t.recompute_stats()
            b = d.get("bima")
            if kind == "bima" and isinstance(b, dict):
                t.formula = str(b.get("formula", "x"))[:60]
                t.graph_dir = 1 if int(b.get("dir", 1)) >= 0 else -1
                t.shape_i = int(b.get("shape", 0)) % 3
                t.brain = float(b.get("brain", 0.0))
                t.brain_init = bool(b.get("brain_init", False))
            built.append(t)
        game.reset()
        game.waves.number = wave
        game.run_start_wave = wave   # only waves played from here on pay Snack Coins
        game.money = float(data["money"])
        game.ball_knowledge = int(data.get("knowledge", 0))
        game.stash_hp = max(1, int(data["stash_hp"]))
        game.stash_max = max(game.stash_max, game.stash_hp)
        game.larp_tip_shown = bool(data.get("larp_tip_shown", False))
        game.towers = built
        game.ui.shown_money = game.money  # HUD starts at the real value (no count-up animation)
        return True
    except (KeyError, TypeError, ValueError, AttributeError):
        game.reset()
        return False
