"""In-game shop items ("powers", like BTD6 Powers): bought in the main-menu shop, used up one at a time during a run.

Data: data/shop.py (ITEMS). Stock lives in the Profile; per-run limits in Game.powers_used.
`status()` says whether an item can be used right now, `use()` does it. Insta towers only start the placement
(Game._try_place finishes it and calls `consume`), so cancelling a placement costs nothing.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from data.settings import WORLD_CENTER
from data.shop import ITEMS

if TYPE_CHECKING:
    from game.game import Game

GOLD = (255, 214, 70)


def left_this_run(game: "Game", pid: str) -> int:
    return max(0, ITEMS[pid]["max_per_run"] - game.powers_used.get(pid, 0))


def status(game: "Game", pid: str) -> tuple[bool, str]:
    """(usable, reason_if_not)."""
    if game.state.value != "playing":
        return False, "Run is over"
    if game.profile.owned(pid) <= 0:
        return False, "You have none: buy some in the SHOP"
    if left_this_run(game, pid) <= 0:
        return False, f"Limit reached ({ITEMS[pid]['max_per_run']} per run)"
    if pid == "stash_patch" and game.stash_hp >= game.stash_max:
        return False, "The Stash is already at full HP"
    if pid == "freeze_bomb" and not game.enemies:
        return False, "No Didits to freeze"
    if pid == "espresso" and not game.towers:
        return False, "Place a tower first"
    return True, ""


def consume(game: "Game", pid: str) -> None:
    game.profile.use_item(pid)
    game.powers_used[pid] = game.powers_used.get(pid, 0) + 1


def use(game: "Game", pid: str) -> bool:
    ok, why = status(game, pid)
    if not ok:
        game.flash(why, 1.8)
        game.fx.invalid()
        return False
    cfg, vfx = ITEMS[pid], game.fx.vfx
    centre = pygame.Vector2(WORLD_CENTER)
    if pid == "insta_jalu":   # placement mode: the item is spent when the tower is actually placed
        game.insta = {"id": pid, "kind": "jalu", "tiers": cfg["tiers"]}
        game.placing, game.selected, game.powers_open = "jalu", None, False
        game.flash("Insta-Jalu: pick a spot (right-click cancels)", 3.0)
        game.fx.click()
        return True
    consume(game, pid)
    game.fx.audio.play("upgrade")
    if pid == "cash_drop":
        game.add_money(cfg["amount"])
        vfx.burst(centre, GOLD, 30, 240, 0.9, 5, 260)
        vfx.comic(centre, "CASH DROP!", GOLD, 52, 1.2)
    elif pid == "stash_patch":
        game.stash_hp = min(game.stash_max, game.stash_hp + cfg["amount"])
        vfx.flash((120, 255, 140), 0.25, 0.3)
        vfx.comic(centre, f"+{cfg['amount']} HP", (140, 255, 150), 52, 1.2)
    elif pid == "freeze_bomb":
        for e in game.enemies:
            if e.is_boss:
                e.apply_slow(0.6, cfg["seconds"])
            else:
                e.stun(cfg["seconds"])
            vfx.burst(e.pos, (170, 225, 255), 6, 90, 0.5, 3, 0)
        vfx.flash((170, 225, 255), 0.35, 0.4)
        vfx.comic(centre, "FREEZE!", (170, 225, 255), 56, 1.2)
    elif pid == "espresso":
        for t in game.towers:
            t.haste = (max(t.haste[0], cfg["seconds"]), max(t.haste[1], cfg["bonus"]))
            vfx.ring(t.pos, 8, 40, 0.35, (255, 190, 90), 3)
        vfx.comic(centre, "ESPRESSO!", (255, 190, 90), 52, 1.2)
    elif pid == "ball_scroll":
        game.ball_knowledge += cfg["amount"]
        vfx.burst(centre, (130, 215, 255), 24, 200, 0.8, 4, 200)
        vfx.comic(centre, f"+{cfg['amount']} KNOWLEDGE", (130, 215, 255), 44, 1.2)
    return True
