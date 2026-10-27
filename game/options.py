"""Player options (the gear button): defaults, row definitions, load/save to options.json.

Row kinds: toggle (bool), cycle (list of choices, any value), step (0..max int).
`apply()` in Game pushes the values into audio / vfx / rules.
"""
from __future__ import annotations

import json
import os

PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "options.json")

TARGET_MODES = ["first", "last", "strong", "weak", "close"]
TARGET_LABELS = {"first": "First", "last": "Last", "strong": "Strong", "weak": "Weak", "close": "Close"}

DEFAULTS = {"auto_start": False, "auto_delay": 3, "volume": 7, "shake": True, "comics": True,
            "particles": "High", "vignette": True, "fps": False, "default_target": "first"}

# (key, label, kind, choices)
ROWS = [
    ("auto_start", "Auto-start waves", "toggle", None),
    ("auto_delay", "Auto-start delay (s)", "cycle", [0, 3, 6, 10]),
    ("volume", "Sound volume", "step", 10),
    ("shake", "Screen shake", "toggle", None),
    ("comics", "Hit words (POW!)", "toggle", None),
    ("particles", "Particles", "cycle", ["Low", "High"]),
    ("vignette", "Danger glow", "toggle", None),
    ("fps", "Show FPS", "toggle", None),
    ("default_target", "New towers target", "cycle", TARGET_MODES),
]


def load() -> dict:
    opts = dict(DEFAULTS)
    try:
        with open(PATH, encoding="utf-8") as f:
            saved = json.load(f)
        for k, v in saved.items():
            if k in DEFAULTS and type(v) is type(DEFAULTS[k]):
                opts[k] = v
    except (OSError, ValueError):
        pass
    return opts


def save(opts: dict) -> None:
    try:
        with open(PATH, "w", encoding="utf-8") as f:
            json.dump(opts, f, indent=1)
    except OSError:
        pass


def value_text(key: str, value) -> str:
    if isinstance(value, bool):
        return "ON" if value else "OFF"
    if key == "default_target":
        return TARGET_LABELS[value]
    if key == "volume":
        return f"{value * 10}%"
    return str(value)


def change(opts: dict, key: str, direction: int = 1) -> None:
    for k, _label, kind, choices in ROWS:
        if k != key:
            continue
        if kind == "toggle":
            opts[k] = not opts[k]
        elif kind == "cycle":
            opts[k] = choices[(choices.index(opts[k]) + direction) % len(choices)]
        else:
            opts[k] = (opts[k] + direction) % (choices + 1)
        return
