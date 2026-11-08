"""Active skills: Romli DiditCode (preparation), Jalu Sweep (Mark) / Loom Reset, Zizi Nap Time, Bima Cube / Pyramid / Sphere.

A tower's actives are the effects it has that appear in ACTIVES. Aimed skills (aim=True) wait for a map click.
Cooldowns tick in simulation time (Tower.active_cd). Usable during battle only.
"""
from __future__ import annotations

from data import mark as mark_cfg
from data.bima import ABILITIES
from data.settings import DIDITCODE_COOLDOWN, DIDITCODE_MAX_PER_PREP
from game import bima, mark

ACTIVES = {
    "sweep_active": {"name": "Sweep", "cooldown": mark_cfg.SWEEP_COOLDOWN, "aim": False,
                     "color": (255, 214, 70), "icon": "sweep",
                     "desc": "Mark vanishes; a sweeper runs the path backwards, hitting every Didit."},
    "loom_reset_active": {"name": "Loom Reset", "cooldown": 35.0, "aim": False, "push": 160, "stun": 2.0,
                          "boss_slow": 0.5, "color": (130, 200, 255), "icon": "clock",
                          "desc": "Push back and freeze enemies in range (bosses are only slowed)."},
    "nap_time_active": {"name": "Nap Time", "cooldown": 40.0, "aim": False, "stun": 3.0, "boss_slow": 0.7,
                        "color": (200, 120, 255), "icon": "moon",
                        "desc": "Everything in range falls asleep (bosses are only slowed)."},
    # Romli's own ability (every Romli has it from the start). Preparation phase only: a code-bug puzzle for money.
    "diditcode": {"name": "DiditCode", "cooldown": DIDITCODE_COOLDOWN, "aim": False, "phase": "prep",
                  "color": (70, 200, 110), "icon": "code",
                  "desc": "Preparation only: find and fix the bug in a code snippet to earn money."},
    "cube_active": {"name": "Cube", "cooldown": ABILITIES["cube_active"]["cooldown"], "aim": True,
                    "color": (255, 160, 60), "icon": "cube", "desc": "Click the path: a cube blocks enemies and hurts them."},
    "pyramid_active": {"name": "Pyramid", "cooldown": ABILITIES["pyramid_active"]["cooldown"], "aim": False,
                       "color": (255, 220, 70), "icon": "pyramid", "desc": "Bima: +80% damage, +60% attack speed for 6s."},
    "sphere_active": {"name": "Sphere", "cooldown": ABILITIES["sphere_active"]["cooldown"], "aim": True,
                      "color": (90, 210, 255), "icon": "sphere", "desc": "Click the map: trap zone + a shield on the base."},
}


def actives_of(tower) -> list[str]:
    ids = [e for e in tower.effects if e in ACTIVES]
    if tower.kind == "romli":
        ids.insert(0, "diditcode")
    return ids


def phase_ok(game, aid: str) -> bool:
    """Most abilities work in battle only; DiditCode works in preparation only."""
    return game.phase.value == ACTIVES[aid].get("phase", "battle").replace("prep", "preparation")


def can_use(game, tower, aid: str) -> tuple[bool, str]:
    if not phase_ok(game, aid):
        return False, "DiditCode works during preparation" if aid == "diditcode" else "Abilities work during a battle"
    if aid == "diditcode" and (game.code_uses >= DIDITCODE_MAX_PER_PREP or game.code is not None):
        return False, "No more DiditCode this preparation"
    if tower.active_cd.get(aid, 0.0) > 0:
        return False, f"{ACTIVES[aid]['name']} is recharging"
    if tower.vanished:
        return False, f"{tower.name} is already sweeping"
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
    if aid == "diditcode":
        game.open_code(tower)   # the cooldown starts now (a free cancel refunds it)
        return True
    if aid == "sweep_active":
        fired = mark.start_sweep(game, tower)
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
