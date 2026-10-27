"""Active skills: Jalu Thunderstrike / Loom Reset, Zizi Nap Time, Bima Cube / Pyramid / Sphere.

A tower's actives are the effects it has that appear in ACTIVES. Aimed skills (aim=True) wait for a map click.
Cooldowns tick in simulation time (Tower.active_cd). Usable during battle only.
"""
from __future__ import annotations

from data.bima import ABILITIES
from game import bima
from game.utils import Vec

ACTIVES = {
    "thunderstrike_active": {"name": "Thunderstrike", "cooldown": 30.0, "aim": True, "radius": 95, "dmg_mult": 6.0,
                             "stun": 1.0, "color": (255, 240, 120), "icon": "bolt",
                             "desc": "Click the map: lightning hits everything in the circle."},
    "loom_reset_active": {"name": "Loom Reset", "cooldown": 35.0, "aim": False, "push": 160, "stun": 2.0,
                          "boss_slow": 0.5, "color": (130, 200, 255), "icon": "clock",
                          "desc": "Push back and freeze enemies in range (bosses are only slowed)."},
    "nap_time_active": {"name": "Nap Time", "cooldown": 40.0, "aim": False, "stun": 3.0, "boss_slow": 0.7,
                        "color": (200, 120, 255), "icon": "moon",
                        "desc": "Everything in range falls asleep (bosses are only slowed)."},
    "cube_active": {"name": "Cube", "cooldown": ABILITIES["cube_active"]["cooldown"], "aim": True,
                    "color": (255, 160, 60), "icon": "cube", "desc": "Click the path: a cube blocks enemies and hurts them."},
    "pyramid_active": {"name": "Pyramid", "cooldown": ABILITIES["pyramid_active"]["cooldown"], "aim": False,
                       "color": (255, 220, 70), "icon": "pyramid", "desc": "Bima: +80% damage, +60% attack speed for 6s."},
    "sphere_active": {"name": "Sphere", "cooldown": ABILITIES["sphere_active"]["cooldown"], "aim": True,
                      "color": (90, 210, 255), "icon": "sphere", "desc": "Click the map: trap zone + a shield on the base."},
}


def actives_of(tower) -> list[str]:
    return [e for e in tower.effects if e in ACTIVES]


def can_use(game, tower, aid: str) -> tuple[bool, str]:
    if game.phase.value != "battle":
        return False, "Abilities work during a battle"
    if tower.active_cd.get(aid, 0.0) > 0:
        return False, f"{ACTIVES[aid]['name']} is recharging"
    if tower.kind == "bima" and tower.lockout > 0:
        return False, "Bima needs a moment between abilities"
    return True, ""


def use(game, tower, aid: str, pos=None) -> bool:
    """Run the ability. Returns True if it fired (cooldown starts)."""
    ok, why = can_use(game, tower, aid)
    if not ok:
        game.fx.invalid()
        game.flash(why, 1.5)
        return False
    cfg = ACTIVES[aid]
    fired = False
    if aid == "thunderstrike_active":
        fired = _thunder(game, tower, Vec(pos), cfg)
    elif aid == "loom_reset_active":
        fired = _loom(game, tower, cfg)
    elif aid == "nap_time_active":
        fired = _nap(game, tower, cfg)
    elif aid == "cube_active":
        fired = bima.place_cube(game, tower, pos)
    elif aid == "pyramid_active":
        fired = bima.cast_pyramid(game, tower)
    elif aid == "sphere_active":
        fired = bima.cast_sphere(game, tower, pos)
    if fired:
        tower.active_cd[aid] = cfg["cooldown"]
        if tower.kind == "bima":
            tower.lockout = ABILITIES["global_lockout"]
    else:
        game.fx.invalid()
    return fired


def _thunder(game, tower, pos: Vec, cfg) -> bool:
    game.fx.thunder_warn(pos, cfg["radius"])
    dmg = tower.stats["damage"] * cfg["dmg_mult"]

    def strike():
        game.fx.thunder_strike(pos, cfg["radius"])
        for e in game.enemies:
            if e.alive and e.pos.distance_to(pos) <= cfg["radius"] + e.radius:
                game.hit_enemy(e, dmg, color=cfg["color"], source=tower)
                e.stun(cfg["stun"])
    game.delayed.append([0.45, strike])
    return True


def _in_range(game, tower):
    r = tower.stats["range"]
    return [e for e in game.enemies if e.alive and e.pos.distance_to(tower.pos) <= r + e.radius]


def _loom(game, tower, cfg) -> bool:
    game.fx.loom_reset(tower)
    for e in _in_range(game, tower):
        if e.is_boss:
            e.apply_slow(cfg["boss_slow"], cfg["stun"])
        else:
            e.push_back(cfg["push"])
            e.stun(cfg["stun"])
        game.fx.pushed(e)
    return True


def _nap(game, tower, cfg) -> bool:
    game.fx.nap_time(tower)
    for e in _in_range(game, tower):
        if e.is_boss:
            e.apply_slow(cfg["boss_slow"], cfg["stun"])
        else:
            e.stun(cfg["stun"])
        game.fx.slept(e)
    return True
