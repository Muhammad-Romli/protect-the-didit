"""Named special effects, registered by name: EFFECTS = {"time_push": fn}.

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

import pygame

from data.effects import EFFECT_PARAMS


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


def _speed_against_time(tower, game, hook, **ctx):
    """Fast enemies (Fast Didit, Speedster Didit) that get hit walk at normal speed for a few seconds."""
    if hook != "hit":
        return None
    for e in ctx["victims"]:
        if e.is_fast and e.alive:
            if e.normalize_timer <= 0:
                game.fx.normalized(e)
            e.normalize_timer = EFFECT_PARAMS["speed_against_time"]["duration"]
    return None


def _armor_breaker(tower, game, hook, **ctx):
    """Marker effect: Game.hit_enemy counts this tower's hits x3 against armor."""
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
    """Enemies inside this tower's range take extra damage from every tower (+25% once Nap Time is unlocked)."""
    if hook != "damage_taken":
        return None
    e = ctx["enemy"]
    if tower.pos.distance_to(e.pos) <= tower.stats["range"] + e.radius:
        return 1.25 if "nap_time_active" in tower.effects else EFFECT_PARAMS["damage_debuff_15"]["mult"]
    return None


def _marker(tower, game, hook, **ctx):
    """Effects that are handled elsewhere (actives, Bima paths, Mark's melee): registered so the UI knows they exist."""
    return None


def _mark_knockback(tower, game, hook, **ctx):
    """Mark tier 2: every punch pushes the victims back along the path (bosses much less). See game/mark.py."""
    if hook != "hit":
        return None
    from game import mark
    for e in ctx["victims"]:
        mark.knock_back(game, e)
    return None


def _fadhli_bounce(tower, game, hook, **ctx):
    """Johnny tier 2: the steel ball bounces on (50%, then -5 points per bounce). See game/fadhli.py."""
    if hook == "hit":
        from game import fadhli
        fadhli.bounce(game, tower, ctx["proj"], ctx["victims"])
    return None


def _fadhli_status(tower, game, hook, **ctx):
    """Johnny tier 3: every hit 20% stun / 30% slow / 50% nothing."""
    if hook == "hit":
        from game import fadhli
        fadhli.status(game, tower, ctx["proj"], ctx["victims"])
    return None


def _garp_knockback(tower, game, hook, **ctx):
    """Garp tier 3: heavy hits knock Didits back along the path."""
    if hook == "hit":
        from game import fadhli
        fadhli.shove(game, tower, ctx["proj"], ctx["victims"])
    return None


def _garp_crater(tower, game, hook, **ctx):
    """Garp tier 2+: the landing throw leaves a hot crater (see game/fadhli.py)."""
    if hook == "hit":
        from game import fadhli
        fadhli.crater(game, tower, ctx["proj"])


def _geo_effects(tower, game, hook, **ctx):
    """Bima Geometry Lv2+: shape stacks. The hit target gets its shape slot filled (see game/bima.py)."""
    if hook != "hit":
        return None
    from game import bima
    p = ctx["proj"]
    for e in ctx["victims"]:
        bima.geo_on_hit(game, tower, e, p)
    return None


def _random_event(strong: bool):
    """Romli Programmer: every 20s a random event: money gift, haste, or a bug (strong version: better odds)."""
    def fn(tower, game, hook, **ctx):
        if hook != "tick":
            return None
        if not strong and "random_event_strong" in tower.effects:
            return None  # the strong version replaces the basic one
        tower.event_timer = getattr(tower, "event_timer", 0.0) + ctx["dt"]
        if tower.event_timer < 20.0 or game.phase.value != "battle":
            return None
        tower.event_timer = 0.0
        r = random.random()
        pos = tower.pos + pygame.Vector2(0, -50)
        if r < (0.45 if strong else 0.4):
            gift = min(800 if strong else 300, game.money * (0.2 if strong else 0.1)) + (50 if strong else 20)
            game.add_money(gift)
            game.fx.vfx.comic(pos, "JACKPOT!", (255, 220, 70), 34, 1.0)
            game.fx.vfx.burst(tower.pos, (255, 220, 70), 24, 220, 0.8, 5, 260)
            game.fx.vfx.text(pos + pygame.Vector2(0, 30), f"+${int(gift)}", (255, 255, 255), 26, 1.0, 30)
        elif r < (0.9 if strong else 0.8):
            tower.haste = (8.0 if strong else 6.0, 0.8 if strong else 0.4)
            game.fx.vfx.comic(pos, "OVERCLOCK!", (110, 255, 160), 34, 1.0)
            game.fx.vfx.pop(tower.pos, 60, (110, 255, 160), 0.4)
        else:
            tower.cooldown_left += 1.5 if strong else 3.0
            game.fx.vfx.comic(pos, "BUG!", (255, 110, 100), 36, 1.0)
            game.fx.vfx.burst(tower.pos, (255, 110, 100), 12, 140, 0.5, 4, 100)
        return None
    return fn


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
    "geo_effects": _geo_effects,
    "random_event": _random_event(False),
    "random_event_strong": _random_event(True),
    **{n: _marker for n in ("graph_axis", "graph_patterns", "graph_advanced", "geo_shapes", "geo_3d",
                            "loom_reset_active", "nap_time_active", "mark_melee", "mark_rage", "sweep_active",
                            "cube_active", "pyramid_active", "sphere_active", "galaxy_active", "golden_active",
                            "fadhli_barrage")},
    "fadhli_bounce": _fadhli_bounce,
    "fadhli_status": _fadhli_status,
    "garp_knockback": _garp_knockback,
    "garp_crater": _garp_crater,
    "mark_knockback": _mark_knockback,
    "time_push": _time_push,
    "speed_against_time": _speed_against_time,
    "armor_breaker": _armor_breaker,
    "sleep_chance": _sleep,
    "damage_debuff_15": _debuff,
    "aura_attack_speed_10": _aura("aura_attack_speed_10"),
    "aura_attack_speed_20": _aura("aura_attack_speed_20"),
    "aura_attack_speed_30": _aura("aura_attack_speed_30"),
    "upgrade_discount_aura": _discount,
    "boss_kill_bonus": _boss_bonus,
}
