"""Named special effects, registered by name: EFFECTS = {"chain_lightning": fn}.

Pass 1 (current): registry is empty, so every `effects` entry in data/towers.py is
ignored and the upgrade panel flags it as "pending". Passes 2-4 add handlers here.
Suggested handler shape (decide when Pass 2 starts):  fn(tower, game, **ctx) -> None
"""
from __future__ import annotations

from typing import Callable

EFFECTS: dict[str, Callable] = {}
