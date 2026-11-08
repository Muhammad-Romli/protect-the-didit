"""Didit Wallstreet logic (no pygame): prices, headlines, one market move per finished run. Data: data/market.py.

Flow: the newspaper shows headlines for the NEXT move. `advance()` (called when a run ends) resolves them:
each headline is right with its source's probability (otherwise the price moves the other way, a bit), plus noise
and a pull back to the start price. Then a fresh batch of headlines is written. IUKXJ is the exception: its price
is simply the integer in kas.txt divided by KAS_DIVISOR. Everything round-trips through to_dict / from_dict.
"""
from __future__ import annotations

import os
import random
import re

from data import market as cfg

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KAS_PATHS = (os.path.join(_ROOT, cfg.KAS_FILE), cfg.KAS_FILE)


def read_kas() -> int:
    """The integer in kas.txt (dots / commas / spaces are tolerated). Falls back to KAS_DEFAULT."""
    for path in KAS_PATHS:
        try:
            with open(path, encoding="utf-8") as f:
                digits = re.sub(r"\D", "", f.read())
            if digits:
                return max(0, int(digits))
        except OSError:
            continue
    return cfg.KAS_DEFAULT


def kas_price(kas: int) -> float:
    return max(cfg.STOCKS["IUKXJ"]["floor"], kas / cfg.KAS_DIVISOR)


def fmt(n: int | float) -> str:
    return f"{int(round(n)):,}".replace(",", ".")


class Market:
    def __init__(self, rng: random.Random | None = None, kas: int | None = None) -> None:
        self.rng = rng or random.Random()
        self.tick = 0
        self.kas = read_kas() if kas is None else int(kas)
        self.prices = {s: float(cfg.STOCKS[s]["start"]) for s in cfg.ORDER}
        self.prices["IUKXJ"] = kas_price(self.kas)
        self.history = {s: [round(self.prices[s], 2)] for s in cfg.ORDER}
        self.change = {s: 0.0 for s in cfg.ORDER}      # last move, as a fraction
        self.headlines: list[dict] = []                # the news for the NEXT move
        self.report: list[dict] = []                   # what the last move did: {text, stock, effect}
        self._write_headlines(self.kas, self.kas, None)

    # ------------------------------------------------------------- queries
    def price(self, sym: str) -> int:
        """The price you actually pay (whole DR, at least 1)."""
        return max(1, round(self.prices[sym]))

    # ---------------------------------------------------------------- kas
    def sync_kas(self, kas: int) -> bool:
        """Re-read of kas.txt (menu opens): IUKXJ follows it at once. Returns True when the price changed."""
        new = kas_price(kas)
        changed = abs(new - self.prices["IUKXJ"]) > 1e-9
        self.kas = int(kas)
        self.prices["IUKXJ"] = new
        self.history["IUKXJ"][-1] = round(new, 2)
        return changed

    # ------------------------------------------------------------ the move
    def advance(self, kas: int | None = None, run: dict | None = None) -> list[dict]:
        """Resolve the pending headlines (one market move). `run` = {"won": bool, "wave": int} adds a front-page line."""
        kas = self.kas if kas is None else int(kas)
        old_kas = self.kas
        before = dict(self.prices)
        effects = {s: 0.0 for s in cfg.ORDER}
        self.report = []
        for h in self.headlines:
            applied = 0.0
            if h["stock"]:
                right = self.rng.random() < h["truth"]
                applied = h["effect"] if right else -h["effect"] * cfg.BACKFIRE
                effects[h["stock"]] += applied
            self.report.append({"text": h["text"], "stock": h["stock"], "effect": applied})
        for s in ("IHSD", "ROC"):
            info = cfg.STOCKS[s]
            p = self.prices[s] * (1 + effects[s] + self.rng.gauss(0, info["vol"]))
            p += (info["start"] - p) * cfg.MEAN_REVERSION
            self.prices[s] = min(info["cap"], max(info["floor"], p))
        self.kas = kas
        self.prices["IUKXJ"] = kas_price(kas)
        for s in cfg.ORDER:
            self.change[s] = self.prices[s] / before[s] - 1 if before[s] else 0.0
            self.history[s].append(round(self.prices[s], 2))
            self.history[s] = self.history[s][-cfg.HISTORY_LEN:]
        self.tick += 1
        self._write_headlines(old_kas, kas, run)
        return self.report

    def _write_headlines(self, old_kas: int, kas: int, run: dict | None) -> None:
        rng = self.rng
        last = {h["text"] for h in self.headlines}
        pool = [t for t in cfg.HEADLINES if t[2] not in last]
        picks: list[tuple] = []
        for stock in ("IHSD", "ROC"):   # at least one headline for each tradable stock
            picks.append(rng.choice([t for t in pool if t[0] == stock]))
        rest = [t for t in pool if t not in picks]
        picks += rng.sample(rest, 2)
        out: list[dict] = []
        for stock, mag, text in picks:
            domain = rng.choice(list(cfg.SOURCES))
            out.append({"text": text, "stock": stock, "effect": round(mag * rng.uniform(0.75, 1.25), 4),
                        "domain": domain, "truth": cfg.SOURCES[domain]})
        if kas > old_kas:
            kas_line = cfg.KAS_UP.format(kas=fmt(kas), diff=fmt(kas - old_kas))
        elif kas < old_kas:
            kas_line = cfg.KAS_DOWN.format(kas=fmt(kas), diff=fmt(old_kas - kas))
        else:
            kas_line = cfg.KAS_SAME.format(kas=fmt(kas))
        out.append({"text": kas_line, "stock": "", "effect": 0.0, "domain": "diditpost.id", "truth": 1.0})
        for text in rng.sample([t for t in cfg.NOISE if t not in last], 2):
            out.append({"text": text, "stock": "", "effect": 0.0, "domain": rng.choice(list(cfg.SOURCES)), "truth": 1.0})
        if run:
            line = (cfg.RUN_WON if run.get("won") else cfg.RUN_LOST).format(n=int(run.get("wave", 0)))
            out.append({"text": line, "stock": "", "effect": 0.0, "domain": "diditpost.id", "truth": 1.0})
        rng.shuffle(out)
        self.headlines = out

    # ------------------------------------------------------------- storage
    def to_dict(self) -> dict:
        return {"tick": self.tick, "kas": self.kas, "prices": {s: round(p, 4) for s, p in self.prices.items()},
                "history": self.history, "change": {s: round(c, 5) for s, c in self.change.items()},
                "headlines": self.headlines, "report": self.report}

    @classmethod
    def from_dict(cls, d: object, rng: random.Random | None = None) -> "Market":
        """Defensive load: anything unusable falls back to a fresh market."""
        m = cls(rng)
        try:
            if not isinstance(d, dict):
                return m
            m.tick = max(0, int(d.get("tick", 0)))
            for s in cfg.ORDER:
                info = cfg.STOCKS[s]
                m.prices[s] = min(info["cap"], max(info["floor"], float(d["prices"][s])))
                hist = [float(x) for x in d["history"][s]][-cfg.HISTORY_LEN:]
                m.history[s] = hist or [round(m.prices[s], 2)]
                m.change[s] = max(-1.0, min(5.0, float(d.get("change", {}).get(s, 0.0))))
            m.kas = max(0, int(d.get("kas", m.kas)))
            heads = []
            for h in d.get("headlines", []):
                stock = h["stock"] if h["stock"] in cfg.ORDER[:2] else ""
                heads.append({"text": str(h["text"])[:140], "stock": stock,
                              "effect": max(-0.3, min(0.3, float(h["effect"]))) if stock else 0.0,
                              "domain": str(h["domain"])[:30], "truth": max(0.0, min(1.0, float(h["truth"])))})
            if heads:
                m.headlines = heads
            m.report = [{"text": str(r["text"])[:140], "stock": str(r["stock"]), "effect": float(r["effect"])}
                        for r in d.get("report", [])][:10]
        except (KeyError, TypeError, ValueError, AttributeError):
            return cls(rng)
        return m
