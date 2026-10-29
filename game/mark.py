"""Mark (Jalu path A): melee punches, rage stacks, knockback and the tier 4 ability "Sweep".

All numbers live in data/mark.py. Hooks used by the rest of the game:
  Tower.update      -> punch()           (instead of firing a projectile, when the tower has "mark_melee")
  effects.py        -> knock_back()      ("mark_knockback", runs on every hit)
  actives.py        -> start_sweep()     ("sweep_active")
  Game._step        -> update_world()    (moves the sweepers, hits Didits, ends sweeps)
  Game.draw         -> draw_world()      (sweepers) ; Tower.draw -> draw_vanished() / draw_rage()

Sweep, step by step: Mark vanishes (hidden, does not attack) -> after SWEEP_VANISH_TIME a sweeper appears at the
path EXIT and runs back toward the path start (against the Didit movement) at SWEEP_SPEED for SWEEP_DURATION
seconds, hitting every Didit inside SWEEP_RADIUS at most SWEEP_HITS_PER_ENEMY times -> Mark reappears.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

from data import mark as cfg
from data.settings import TOWER_RADIUS
from game import gfx, models, sprites_proc
from game.projectile import Projectile
from game.utils import Vec, draw_outlined

if TYPE_CHECKING:
    from game.enemy import Enemy
    from game.game import Game
    from game.tower import Tower

SWEEP_COLOR = (255, 214, 70)       # gold: the sweeper
SWEEP_EDGE = (255, 120, 60)        # orange: its trail edge
RAGE_COLOR = (255, 110, 90)


def is_mark(tower: "Tower") -> bool:
    """True for a Jalu that has bought Mark's first upgrade (he punches instead of shooting)."""
    return "mark_melee" in tower.effects


def init_tower(tower: "Tower") -> None:
    tower.rage_target = None
    tower.rage_stacks = 0


# ------------------------------------------------------------------- punch
def _in_reach(tower: "Tower", e: "Enemy") -> bool:
    return e.alive and tower.pos.distance_to(e.pos) <= tower.stats["range"] + e.radius


def reset_rage(tower: "Tower") -> None:
    tower.rage_target, tower.rage_stacks = None, 0


def tick_tower(tower: "Tower") -> None:
    """Every frame: rage stacks vanish when the target dies or leaves Mark's range."""
    t = tower.rage_target
    if t is not None and not _in_reach(tower, t):
        reset_rage(tower)


def punch(tower: "Tower", game: "Game", target: "Enemy") -> None:
    """One instant melee hit: damages the target and everything within the punch radius of it.
    Goes through Game._resolve_hit, so money-per-hit, armor, debuffs and on-hit effects (knockback) all apply."""
    if tower.rage_target is not target:  # a new target starts from zero stacks
        tower.rage_target, tower.rage_stacks = target, 0
    s = tower.stats
    bonus = 1.0 + cfg.RAGE_BONUS_PER_STACK * tower.rage_stacks if "mark_rage" in tower.effects else 1.0
    p = Projectile(tower.pos, target, 0.0, s["damage"] * bonus, s["aoe_radius"], s["slow"], s["slow_duration"],
                   s["money_per_hit"], tower.color, tower)
    p.pos = Vec(target.pos)
    game.fx.mark_punch(tower, target, tower.rage_stacks)
    game._resolve_hit(p)
    if "mark_rage" in tower.effects and target.alive:
        tower.rage_stacks = min(cfg.RAGE_MAX_STACKS, tower.rage_stacks + 1)  # +1 per consecutive hit on the same target
    elif not target.alive:
        reset_rage(tower)


def knock_back(game: "Game", enemy: "Enemy") -> None:
    """Push along the path. Bosses are not immune (unlike Enemy.push_back) but only move KNOCKBACK_BOSS_MULT as far."""
    if not enemy.alive:
        return
    dist = cfg.KNOCKBACK_DISTANCE * (cfg.KNOCKBACK_BOSS_MULT if enemy.is_boss else 1.0)
    enemy.distance = max(0.0, enemy.distance - dist)
    enemy.pos = enemy.path.position_at(enemy.distance)
    game.fx.knocked(enemy)


# ------------------------------------------------------------------- sweep
def start_sweep(game: "Game", tower: "Tower") -> bool:
    """Tier 4 ability. Mark vanishes; the sweeper is created after SWEEP_VANISH_TIME."""
    if tower.vanished:
        return False
    tower.vanished = True
    reset_rage(tower)
    game.sweeps.append({"tower": tower, "delay": cfg.SWEEP_VANISH_TIME, "t": cfg.SWEEP_DURATION,
                        "dist": game.path.length, "pos": None, "hits": {}, "trail": []})
    game.fx.mark_vanish(tower)
    return True


def _end_sweep(game: "Game", sweep: dict) -> None:
    tower = sweep["tower"]
    tower.vanished = False
    tower.cooldown_left = max(tower.cooldown_left, 0.3)  # a beat before the first punch after coming back
    if tower in game.towers:
        game.fx.mark_reappear(tower)


def _hit_enemies(game: "Game", sweep: dict) -> None:
    tower = sweep["tower"]
    pos: Vec = sweep["pos"]
    for e in game.enemies:
        if not e.alive or pos.distance_to(e.pos) > cfg.SWEEP_RADIUS + e.radius:
            continue
        n, last = sweep["hits"].get(e, (0, -9.0))
        if n >= cfg.SWEEP_HITS_PER_ENEMY or game.time - last < cfg.SWEEP_HIT_INTERVAL:
            continue
        sweep["hits"][e] = (n + 1, game.time)
        dmg = tower.stats["damage"] * cfg.SWEEP_DAMAGE_MULT
        if e.is_boss:
            dmg *= cfg.SWEEP_BOSS_DAMAGE_MULTIPLIER
        game.hit_enemy(e, dmg, color=SWEEP_COLOR)
        game.fx.sweep_hit(e)


def update_world(game: "Game", dt: float) -> None:
    """Runs once per simulation step (Game._step)."""
    for sweep in list(game.sweeps):
        tower = sweep["tower"]
        if tower not in game.towers:  # sold / reset meanwhile: nothing to bring back
            tower.vanished = False
            game.sweeps.remove(sweep)
            continue
        if sweep["pos"] is None:  # Mark has vanished, the sweeper is about to appear at the exit
            sweep["delay"] -= dt
            if sweep["delay"] > 0:
                continue
            dt = -sweep["delay"]  # carry the overshoot into the run
            sweep["pos"] = game.path.position_at(sweep["dist"])
            game.fx.sweep_start(sweep["pos"])
        move = min(cfg.SWEEP_SPEED * dt, sweep["dist"], cfg.SWEEP_SPEED * sweep["t"])
        steps = max(1, math.ceil(move / (cfg.SWEEP_RADIUS * 0.5)))  # sub-steps: a fast sweeper must not skip Didits
        for _ in range(steps):
            sweep["dist"] -= move / steps
            sweep["pos"] = game.path.position_at(sweep["dist"])
            _hit_enemies(game, sweep)
        sweep["t"] -= dt
        sweep["trail"].append(Vec(sweep["pos"]))
        del sweep["trail"][:-14]
        game.fx.sweep_run(sweep["pos"], game.path.position_at(min(game.path.length, sweep["dist"] + 40)))
        if sweep["t"] <= 0 or sweep["dist"] <= 0:
            _end_sweep(game, sweep)
            game.sweeps.remove(sweep)


# -------------------------------------------------------------------- draw
def draw_world(surface: pygame.Surface, game: "Game") -> None:
    """The sweepers: a speed trail, the damage radius as a soft glow and Mark running along the path."""
    for sweep in game.sweeps:
        pos = sweep["pos"]
        if pos is None:
            continue
        trail = sweep["trail"]
        for i, p in enumerate(trail):  # speed trail: additive glow blobs that fade with age
            k = (i + 1) / max(1, len(trail))
            g = gfx.glow(int(cfg.SWEEP_RADIUS * (0.4 + 0.5 * k)), SWEEP_EDGE, int(150 * k))
            surface.blit(g, g.get_rect(center=(int(p.x), int(p.y))))
        if len(trail) >= 2:
            for width, col in ((12, SWEEP_EDGE), (6, SWEEP_COLOR), (2, (255, 255, 255))):
                pygame.draw.lines(surface, col, False, [(p.x, p.y) for p in trail], width)
        halo = gfx.glow(int(cfg.SWEEP_RADIUS * 1.5), SWEEP_COLOR, 150)  # the damage radius
        surface.blit(halo, halo.get_rect(center=(int(pos.x), int(pos.y))))
        t = sweep["tower"]
        prev = trail[-2] if len(trail) >= 2 else pos
        if abs(pos.x - prev.x) > 0.5:
            sweep["face_left"] = pos.x < prev.x
        img = models.mark_runner(int(game.time * 20), sweep.get("face_left", False))
        surface.blit(img, img.get_rect(center=(int(pos.x), int(pos.y) - 12)))
        gfx.blit_shadow(surface, (pos.x + 10, pos.y + 14), 50, 20, 90)


def draw_vanished(surface: pygame.Surface, tower: "Tower", selected: bool) -> None:
    """While Mark is away: his sprite is hidden, only a faint marker shows where he will come back."""
    x, y = int(tower.pos.x), int(tower.pos.y)
    if selected:
        pulse = 2 * math.sin(pygame.time.get_ticks() / 160)
        pygame.draw.ellipse(surface, (255, 255, 255), (x - 28 - pulse, y - 12 - pulse / 2, 56 + 2 * pulse, 28 + pulse), 3)
    ring = gfx.glow(30, SWEEP_COLOR, 110)
    surface.blit(ring, ring.get_rect(center=(x, y + 4)))
    pygame.draw.ellipse(surface, (255, 235, 150), (x - 22, y - 8, 44, 22), 2)
    draw_outlined(surface, "SWEEPING", (x, y - 22), 16, SWEEP_COLOR, center=True, width=1)


def draw_rage(surface: pygame.Surface, tower: "Tower", x: int, y: int) -> None:
    """Rage stacks: a red glow and an 'x7' tag above Mark."""
    n = tower.rage_stacks
    if n <= 0:
        return
    g = gfx.glow(26 + 3 * n, RAGE_COLOR, 40 + 9 * n)
    surface.blit(g, g.get_rect(center=(x, y - 6)))
    draw_outlined(surface, f"x{n}", (x, y - TOWER_RADIUS * 3 - 6), 18, RAGE_COLOR, center=True, width=2)
