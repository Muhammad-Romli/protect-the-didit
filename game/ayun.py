"""A'yun (shopkeeper tower): item gacha, items as attacks, Supply Chain auto-roll, selling Didits. Numbers: data/ayun.py.

Hooks (who calls what):
  Tower.__init__            -> init_tower()        (stock, pity, idle timer, auto-roll state)
  Tower.update              -> tick_tower()        (item expiry, every item's own throw cooldown, auto-roll)
  Game._resolve_hit         -> on_item_hit()       (Price Tag mark, Dragon Sauce puddle) for projectiles that carry an item
  Game._collect_enemies     -> sell_amount()       (passive: she sells every Didit she kills)
  Game._step / Game.draw    -> update_world() / draw_world()   (puddles, pop-up timer)
  game/actives.py           -> roll() and toggle_auto()        (abilities E = Roll, C = Auto)
  game/ui.py                -> panel buttons call Game actions that end up in roll / sell_item / resolve_prompt

State on the tower: stock = [{"id", "cd", "life"}], pity, idle (seconds since her last manual roll), auto_on, auto_timer.
State on the game: game.ayun_prompt = {"tower", "item", "timer"} while a replace-or-sell pop-up is open; game.puddles.
"""
from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

import pygame

from data import ayun as cfg
from game import ayun_art
from game.utils import Vec

if TYPE_CHECKING:
    from game.game import Game
    from game.tower import Tower


# ------------------------------------------------------------------------------------------------ basics
def is_ayun(t: "Tower") -> bool:
    return t.kind == "ayun"


def tier(t: "Tower") -> int:
    return t.tiers[0]


def unlocked(t: "Tower") -> bool:
    """Upgrade 1 (Gacha Stall) unlocks rolling."""
    return tier(t) >= 1


def stock_cap(t: "Tower") -> int:
    return cfg.STOCK_CAP.get(tier(t), 0)


def roll_cost(t: "Tower") -> int:
    return cfg.ROLL_COST.get(tier(t), cfg.ROLL_COST[1])


def auto_cost() -> float:
    """Money per automatic roll (150 per minute at one roll per 15 s = 37.5)."""
    return cfg.AUTO_COST_PER_MINUTE * cfg.AUTO_INTERVAL / 60.0


def has_auto(t: "Tower") -> bool:
    return tier(t) >= cfg.AUTO_MIN_TIER


def sell_rate(t: "Tower") -> float:
    return cfg.SELL_BONUS_APPRAISAL if tier(t) >= cfg.APPRAISAL_MIN_TIER else cfg.SELL_BONUS


def steady(t: "Tower") -> float:
    """0..1: how far Steady Supply has grown (time since her last manual roll)."""
    if not has_auto(t):
        return 0.0
    return max(0.0, min(1.0, t.idle / cfg.STEADY_SECONDS))


def odds(t: "Tower", auto: bool = False) -> dict[str, float]:
    """Rarity weights in percent for her next roll. Auto-roll odds start at the upgrade 3 table and grow towards the
    upgrade 4 table with Steady Supply."""
    tr = max(1, min(4, tier(t)))
    if not auto:
        return {k: float(v) for k, v in cfg.ODDS[tr].items()}
    a, b, f = cfg.ODDS[3], cfg.ODDS[4], steady(t)
    return {k: a[k] + (b[k] - a[k]) * f for k in cfg.RARITIES}


def odds_text(t: "Tower", auto: bool = False) -> str:
    o = odds(t, auto)
    return "  ".join(f"{cfg.RARITY_LABEL[k][:3]} {o[k]:.0f}%" for k in cfg.RARITIES if o[k] > 0)


def pity_left(t: "Tower") -> int | None:
    """Manual rolls until a guaranteed Rare (None before upgrade 3)."""
    if tier(t) < cfg.PITY_MIN_TIER:
        return None
    return max(0, cfg.PITY_AFTER - t.pity)


def sell_value(item_id: str) -> int:
    return cfg.SELL_VALUE[cfg.ITEMS[item_id]["rarity"]]


def init_tower(t: "Tower") -> None:
    t.stock = []
    t.pity = 0
    t.idle = 0.0
    t.auto_on = False
    t.auto_timer = cfg.AUTO_INTERVAL


def new_item(item_id: str) -> dict:
    r = cfg.ITEMS[item_id]["rarity"]
    return {"id": item_id, "cd": cfg.FIRST_THROW_DELAY, "life": cfg.LIFETIME[r]}


def pick(t: "Tower", auto: bool = False) -> str:
    """Draw an item id. Manual rolls from upgrade 3 have pity: the 6th roll in a row without a Rare is a Rare."""
    o = odds(t, auto)
    rarity = random.choices(cfg.RARITIES, weights=[o[r] for r in cfg.RARITIES])[0]
    if not auto and tier(t) >= cfg.PITY_MIN_TIER and t.pity >= cfg.PITY_AFTER - 1 and rarity in ("junk", "common"):
        rarity = "rare"
    if not auto:
        t.pity = 0 if rarity in ("rare", "legendary") else t.pity + 1
    return random.choice(cfg.ITEMS_BY_RARITY[rarity])


# ---------------------------------------------------------------------------------------------- rolling
def roll(game: "Game", t: "Tower", auto: bool = False) -> bool:
    """Spend money and roll one item. A full stock opens the replace-or-sell pop-up (the new item waits there)."""
    if not unlocked(t):
        game.flash("A'yun needs upgrade 1 to roll items", 1.8)
        game.fx.invalid()
        return False
    if game.ayun_prompt is not None:
        game.flash("Decide about the new item first (replace or sell)", 1.8)
        game.fx.invalid()
        return False
    cost = auto_cost() if auto else roll_cost(t)
    if game.money < cost:
        game.flash("Not enough money to roll", 1.5)
        game.fx.invalid()
        return False
    game.add_money(-cost)
    item_id = pick(t, auto)
    if not auto:
        t.idle = 0.0   # a manual roll resets Steady Supply
    game.fx.ayun_roll(t, item_id, auto)
    item = new_item(item_id)
    if len(t.stock) < stock_cap(t):
        t.stock.append(item)
    else:
        game.ayun_prompt = {"tower": t, "item": item, "timer": cfg.PROMPT_SECONDS}
        game.fx.ayun_prompt(t)
    return True


def toggle_auto(game: "Game", t: "Tower") -> bool:
    if not has_auto(t):
        game.flash("Supply Chain (upgrade 4) unlocks auto-roll", 1.8)
        game.fx.invalid()
        return False
    t.auto_on = not t.auto_on
    if t.auto_on:
        t.auto_timer = cfg.AUTO_INTERVAL
        game.flash(f"Auto-roll ON: a roll every {cfg.AUTO_INTERVAL:g}s (battle), ${cfg.AUTO_COST_PER_MINUTE}/min", 2.2)
    else:
        game.flash("Auto-roll OFF", 1.2)
    game.fx.click()
    return True


def sell_item(game: "Game", t: "Tower", slot: int) -> bool:
    """Sell a stored item for its (cheap) price."""
    if not 0 <= slot < len(t.stock):
        return False
    it = t.stock.pop(slot)
    value = sell_value(it["id"])
    game.add_money(value)
    game.fx.ayun_item_sold(t, it["id"], value)
    return True


def resolve_prompt(game: "Game", choice: str, slot: int | None = None) -> None:
    """Pop-up answer: 'replace' (the item in `slot` is thrown away) or 'sell' (the NEW item is sold). Doing nothing for
    PROMPT_SECONDS sells the new item."""
    p = game.ayun_prompt
    if p is None:
        return
    game.ayun_prompt = None
    t, item = p["tower"], p["item"]
    if choice == "replace" and t in game.towers and slot is not None and 0 <= slot < len(t.stock):
        old = t.stock[slot]
        t.stock[slot] = item
        game.fx.ayun_replaced(t, old["id"], item["id"])
        return
    value = sell_value(item["id"])
    game.add_money(value)
    game.fx.ayun_item_sold(t, item["id"], value)


# -------------------------------------------------------------------------------------------- per frame
def tick_tower(t: "Tower", game: "Game", dt: float, rate: float) -> None:
    """Called from Tower.update every step: lifetimes, every item's own throw cooldown, auto-roll."""
    t.idle += dt
    if not unlocked(t):
        return
    battle = game.waves.active
    if battle:
        for it in list(t.stock):
            it["life"] -= dt   # items only age during battles
            if it["life"] <= 0:
                t.stock.remove(it)
                game.fx.ayun_expired(t, it["id"])
        for it in t.stock:
            it["cd"] = max(0.0, it["cd"] - dt * rate)
            if it["cd"] <= 0 and fire(game, t, it):
                it["cd"] = cfg.ITEMS[it["id"]]["cd"]
        if has_auto(t) and t.auto_on:
            t.auto_timer -= dt
            if t.auto_timer <= 0:
                if game.ayun_prompt is not None:
                    t.auto_timer = 1.0            # wait for the decision, then roll
                elif game.money < auto_cost():
                    t.auto_on = False
                    game.flash("Auto-roll stopped: not enough money", 2.2)
                    game.fx.invalid()
                else:
                    t.auto_timer = cfg.AUTO_INTERVAL
                    roll(game, t, auto=True)


def _in_range(t: "Tower", game: "Game") -> list:
    r = t.stats["range"]
    return [e for e in game.enemies if e.alive and t.pos.distance_to(e.pos) <= r + e.radius]


def fire(game: "Game", t: "Tower", it: dict) -> bool:
    """Throw one stored item at a Didit in range. False (nothing thrown, the item stays ready) when none is in range."""
    from game.projectile import Projectile
    c = cfg.ITEMS[it["id"]]
    cands = _in_range(t, game)
    if not cands:
        return False
    first = t.pick_target(game.enemies)
    targets = [first] if first is not None else cands[:1]
    if c.get("special") == "triple":
        others = sorted((e for e in cands if e is not first), key=lambda e: -e.distance)
        targets = ([first] if first is not None else []) + others
        targets = targets[:3]
    color = ayun_art.rarity_color(it["id"])
    slow, slow_t = c["slow"] if c["slow"] else (0.0, 0.0)
    origin = Vec(t.pos) + Vec(0, -12)
    for target in targets:
        p = Projectile(origin, target, c["speed"], c["dmg"], c["aoe"], slow, slow_t, 0.0, color, t)
        p.item = it["id"]
        p.armor_hits = 3 if c.get("special") == "armor3" else None
        game.projectiles.append(p)
    t.kick = 0.1
    t.aim = (targets[0].pos - t.pos).normalize() if targets[0].pos != t.pos else t.aim
    game.fx.ayun_throw(t, it["id"])
    return True


def on_item_hit(game: "Game", p, victims: list) -> None:
    """Item specials that happen on impact (called by Game._resolve_hit for projectiles that carry an item)."""
    c = cfg.ITEMS[p.item]
    special = c.get("special")
    if special == "mark":
        for e in victims:
            if e.alive:
                e.vuln = max(e.vuln, cfg.MARK_BONUS)
                e.vuln_timer = max(e.vuln_timer, cfg.MARK_SECONDS)
                game.fx.ayun_mark(e)
    elif special == "puddle" and p.source is not None:
        game.puddles.append({"pos": Vec(p.pos), "t": cfg.PUDDLE_SECONDS, "total": cfg.PUDDLE_SECONDS, "tick": cfg.PUDDLE_TICK,
                             "owner": p.source, "seed": random.randint(0, 9999)})
        while len(game.puddles) > cfg.PUDDLE_MAX:
            game.puddles.pop(0)
        game.fx.ayun_puddle(p.pos)


def sell_amount(t: "Tower", enemy) -> int:
    """Passive: extra money for a Didit she killed (she sells it). Golden Register kills pay their bounty twice."""
    amount = enemy.bounty * sell_rate(t)
    if getattr(enemy, "item_hit", None) and cfg.ITEMS[enemy.item_hit].get("special") == "double":
        amount += enemy.bounty
    return max(1, round(amount))


# ------------------------------------------------------------------------------------------------- world
def update_world(game: "Game", dt: float) -> None:
    """Once per simulation step: burn Didits in dragon sauce puddles, age puddles, run the pop-up timer."""
    for pd in list(game.puddles):
        pd["t"] -= dt
        pd["tick"] -= dt
        if pd["tick"] <= 0:
            pd["tick"] += cfg.PUDDLE_TICK
            for e in list(game.enemies):
                if e.alive and e.armor <= 0 and pd["pos"].distance_to(e.pos) <= cfg.PUDDLE_RADIUS + e.radius:
                    e.item_hit = None
                    game.hit_enemy(e, cfg.PUDDLE_DAMAGE, color=(255, 120, 40), source=pd["owner"], quiet=True)
        if pd["t"] <= 0:
            game.puddles.remove(pd)
    p = game.ayun_prompt
    if p is not None:
        p["timer"] -= dt
        if p["timer"] <= 0 or p["tower"] not in game.towers:
            resolve_prompt(game, "sell")


def draw_world(surface: pygame.Surface, game: "Game") -> None:
    """Burning dragon-sauce puddles on the ground."""
    now = pygame.time.get_ticks() / 1000
    for pd in game.puddles:
        life = max(0.0, pd["t"] / pd["total"])
        r = cfg.PUDDLE_RADIUS
        w, h = 2 * r, int(1.1 * r)
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        flick = 0.85 + 0.15 * math.sin(now * 9 + pd["seed"])
        a = int(150 * min(1.0, life * 2.5) * flick)
        pygame.draw.ellipse(s, (120, 20, 14, a), (0, 0, w, h))
        pygame.draw.ellipse(s, (236, 70, 36, a), (6, 4, w - 12, h - 8))
        pygame.draw.ellipse(s, (255, 170, 60, a), (w // 4, h // 4, w // 2, h // 2))
        surface.blit(s, s.get_rect(center=(int(pd["pos"].x), int(pd["pos"].y))))


def draw_tower(surface: pygame.Surface, t: "Tower", x: int, y: int) -> None:
    """Little row of icons above her head (one per stored item, a thin bar = remaining life) + the auto-roll timer."""
    n = len(t.stock)
    if n:
        step = 19
        x0 = x - (n - 1) * step // 2
        for i, it in enumerate(t.stock):
            cx, cy = x0 + i * step, y - 76
            ic = ayun_art.item_icon(it["id"], 18)
            pygame.draw.circle(surface, (28, 18, 12), (cx, cy), 11)
            pygame.draw.circle(surface, ayun_art.rarity_color(it["id"]), (cx, cy), 11, 2)
            surface.blit(ic, ic.get_rect(center=(cx, cy)))
            frac = max(0.0, min(1.0, it["life"] / cfg.LIFETIME[cfg.ITEMS[it["id"]]["rarity"]]))
            pygame.draw.rect(surface, (30, 20, 12), (cx - 9, cy + 12, 18, 4), border_radius=2)
            pygame.draw.rect(surface, (255, 120, 90) if frac < 0.25 else (120, 230, 130), (cx - 8, cy + 13, max(1, int(16 * frac)), 2))
    if has_auto(t) and t.auto_on:
        frac = 1.0 - max(0.0, min(1.0, t.auto_timer / cfg.AUTO_INTERVAL))
        pygame.draw.rect(surface, (30, 20, 12), (x - 17, y - 98, 34, 6), border_radius=3)
        pygame.draw.rect(surface, (120, 215, 255), (x - 16, y - 97, max(2, int(32 * frac)), 4), border_radius=2)
