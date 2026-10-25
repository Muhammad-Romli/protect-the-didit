"""Named special effects, registered by name: EFFECTS = {"chain_lightning": fn}.

Every handler has the signature  fn(tower, game, hook, **ctx)  and ignores hooks it does
not care about. Hooks (who calls them -> what the return value means):
  "hit"             Game._resolve_hit, only the firing tower's effects. ctx: proj, victims
                    (shared list: handlers may append extra victims). Returns None.
  "damage_taken"    Game.damage_multiplier, every tower. ctx: enemy. Returns a multiplier.
  "speed_bonus"     Game.attack_speed_mult, every tower. ctx: other. Returns a fraction.
  "upgrade_discount" Game.upgrade_cost, every tower. ctx: other. Returns a fraction.
  "boss_kill"       Game._collect_enemies, every tower. Returns bonus money.
Effects named in data/towers.py but missing here are shown as "not implemented yet".
Numbers live in data/effects.py.
"""
from __future__ import annotations

import random
from typing import Callable

from data.effects import EFFECT_PARAMS


def _nearest(enemies, point, exclude, max_dist):
    best, best_d = None, max_dist
    for e in enemies:
        if e.alive and e not in exclude:
            d = e.pos.distance_to(point)
            if d <= best_d:
                best, best_d = e, d
    return best


def _pierce(tower, game, hook, **ctx):
    """Hammer goes through: also hits the closest enemy(ies) next to the target."""
    if hook != "hit" or ctx["proj"].aoe_radius > 0 or not ctx["victims"]:
        return None
    p = EFFECT_PARAMS["pierce_1"]
    victims, primary = ctx["victims"], ctx["victims"][0]
    for _ in range(p["extra_targets"]):
        nxt = _nearest(game.enemies, primary.pos, victims, p["radius"])
        if nxt is None:
            break
        game.hit_enemy(nxt, ctx["proj"].damage)
        victims.append(nxt)
    return None


def _chain_lightning(tower, game, hook, **ctx):
    """Lightning jumps from the target to nearby enemies, losing damage each jump."""
    if hook != "hit" or ctx["proj"].aoe_radius > 0 or not ctx["victims"]:
        return None
    p = EFFECT_PARAMS["chain_lightning"]
    victims, current = ctx["victims"], ctx["victims"][0]
    damage = ctx["proj"].damage
    for _ in range(p["jumps"]):
        nxt = _nearest(game.enemies, current.pos, victims, p["range"])
        if nxt is None:
            break
        damage *= p["falloff"]
        game.add_bolt(current.pos, nxt.pos)
        game.hit_enemy(nxt, damage)
        victims.append(nxt)
        current = nxt
    return None


def _time_push(tower, game, hook, **ctx):
    """Hits may shove enemies back along the path (bosses are immune, see Enemy)."""
    if hook != "hit":
        return None
    p = EFFECT_PARAMS["time_push"]
    for e in ctx["victims"]:
        if random.random() < p["chance"]:
            e.push_back(p["distance"])
            game.fx.pushed(e)
    return None


def _sleep(tower, game, hook, **ctx):
    """Hits may stop enemies for a moment (bosses are immune, see Enemy)."""
    if hook != "hit":
        return None
    p = EFFECT_PARAMS["sleep_chance"]
    for e in ctx["victims"]:
        if random.random() < p["chance"]:
            if not e.is_boss:
                game.fx.slept(e)
            e.stun(p["duration"])
    return None


def _debuff(tower, game, hook, **ctx):
    """Enemies inside this tower's range take extra damage from every tower."""
    if hook != "damage_taken":
        return None
    e = ctx["enemy"]
    if tower.pos.distance_to(e.pos) <= tower.stats["range"] + e.radius:
        return EFFECT_PARAMS["damage_debuff_15"]["mult"]
    return None


def _aura(name: str) -> Callable:
    """Nearby towers (not the source itself) attack faster."""
    def fn(tower, game, hook, **ctx):
        if hook != "speed_bonus" or ctx["other"] is tower:
            return None
        p = EFFECT_PARAMS[name]
        return p["bonus"] if tower.pos.distance_to(ctx["other"].pos) <= p["radius"] else None
    return fn


def _discount(tower, game, hook, **ctx):
    if hook != "upgrade_discount" or ctx["other"] is tower:
        return None
    p = EFFECT_PARAMS["upgrade_discount_aura"]
    return p["discount"] if tower.pos.distance_to(ctx["other"].pos) <= p["radius"] else None


def _boss_bonus(tower, game, hook, **ctx):
    return EFFECT_PARAMS["boss_kill_bonus"]["bonus"] if hook == "boss_kill" else None


EFFECTS: dict[str, Callable] = {
    "pierce_1": _pierce,
    "chain_lightning": _chain_lightning,
    "time_push": _time_push,
    "sleep_chance": _sleep,
    "damage_debuff_15": _debuff,
    "aura_attack_speed_10": _aura("aura_attack_speed_10"),
    "aura_attack_speed_20": _aura("aura_attack_speed_20"),
    "aura_attack_speed_30": _aura("aura_attack_speed_30"),
    "upgrade_discount_aura": _discount,
    "boss_kill_bonus": _boss_bonus,
}
