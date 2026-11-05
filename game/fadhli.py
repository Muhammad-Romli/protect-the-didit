"""Fadhli, the petanque athlete: shot damage (empowered shots, Golden Ratio ramp), steel-boule status rolls,
the three-target bounce, craters, and the state indicators drawn on the tower.

Numbers: data/fadhli.py. Tiers and prices: data/towers.py. Hooks:
Tower.update -> tick / next_shot / prepare_projectile, Game._resolve_hit -> apply_status / after_hit / on_miss,
Game._step -> tick_craters, Tower.draw -> draw_state / draw_stand_gag, actives.use -> start_gyro.
pygame is imported lazily so the rules can be unit-tested without a display.
"""
from __future__ import annotations

import math
import random

from data import fadhli as cfg


# ------------------------------------------------------------------ shots
def tick(tower, dt: float) -> None:
    """Count the Gyro active down; when it ends the Golden Ratio sequence is dropped."""
    if tower.gyro_timer > 0:
        tower.gyro_timer = max(0.0, tower.gyro_timer - dt)
        if tower.gyro_timer == 0:
            tower.golden_damage = 0.0


def start_gyro(tower) -> None:
    """Arigatou, Gyro: 5 s window; the first shot deals 1/4 of normal damage (the ramp lives in golden_damage only)."""
    tower.gyro_timer = cfg.GYRO_DURATION
    tower.golden_damage = max(0.1, tower.stats["damage"] * cfg.GOLDEN_START_FRACTION)


def next_shot(tower) -> tuple[float, bool]:
    """(damage, empowered) of the next boule. During Gyro the damage ramps x1.618 per shot (never touches the
    tower's base damage); each Meteor shot uses up one empowered charge and hits harder."""
    damage = tower.stats["damage"]
    if tower.gyro_timer > 0:
        damage = tower.golden_damage
        tower.golden_damage *= cfg.GOLDEN_RATIO
    empowered = tower.power_shots > 0
    if empowered:
        tower.power_shots -= 1
        damage *= cfg.POWER_SHOT_MULT
    return damage, empowered


def prepare_projectile(tower, proj, empowered: bool) -> None:
    proj.high_arc = "fadhli_sky" in tower.effects
    proj.bounces = cfg.BOUNCE_TARGETS if "fadhli_bounce" in tower.effects else 0
    proj.power_crater = empowered
    proj.make_crater = "fadhli_crater" in tower.effects
    proj.gyro = tower.gyro_timer > 0


# ------------------------------------------------------------------ hits
def roll_status(rng=random) -> str:
    """One roll per hit gives exactly one outcome: 'stun', 'slow' or 'none' (STUN_CHANCE / SLOW_CHANCE / rest)."""
    roll = rng.random()
    if roll < cfg.STUN_CHANCE:
        return "stun"
    if roll < cfg.STUN_CHANCE + cfg.SLOW_CHANCE:
        return "slow"
    return "none"


def spin(enemy) -> None:
    """Spinned: tornado look and a short stun. Bosses only get a short look; Enemy.stun ignores bosses."""
    enemy.spinned_timer = cfg.SPIN_BOSS_DURATION if enemy.is_boss else cfg.SPIN_DURATION
    enemy.stun(cfg.SPIN_STUN)


def apply_status(enemy, tower, gyro: bool) -> None:
    """Status of one boule hit: Spinned during the Gyro active (replaces the roll), else the steel-ball roll."""
    if gyro:
        spin(enemy)
    elif "fadhli_spin" in tower.effects:
        outcome = roll_status()
        if outcome == "stun":
            enemy.stun(cfg.STUN_DURATION)
        elif outcome == "slow":
            enemy.apply_slow(cfg.SLOW_STRENGTH, cfg.SLOW_DURATION)


def after_hit(game, p, victims) -> None:
    """Landing effects of a boule that hit: hot crater, then the bounce."""
    if p.make_crater:
        add_crater(game, p)
    if p.bounces:
        bounce(game, p, victims)


def on_miss(p) -> None:
    """The target died before the boule landed: an empowered shot is not used up."""
    if p.power_crater and p.source is not None:
        p.source.power_shots = min(cfg.POWER_SHOTS, p.source.power_shots + 1)


def bounce(game, p, victims) -> list:
    """Jump to up to `p.bounces` more enemies, each within BOUNCE_RADIUS of the last one hit. One shot never
    hits the same enemy twice. Returns the enemies hit by the bounce."""
    hit_ids = p.hit_ids
    hit_ids.update(id(e) for e in victims)
    at = p.pos.copy()
    hits = []
    for _ in range(p.bounces):
        cands = [e for e in game.enemies
                 if e.alive and id(e) not in hit_ids and e.pos.distance_to(at) <= cfg.BOUNCE_RADIUS]
        if not cands:
            break
        e = min(cands, key=lambda c: c.pos.distance_to(at))
        hit_ids.add(id(e))
        game.fx.vfx.lightning(at, e.pos, (235, 235, 215), 0.12, 3, 3)
        apply_status(e, p.source, p.gyro)
        game.hit_enemy(e, p.damage, color=p.color, source=p.source)
        hits.append(e)
        at = e.pos.copy()
    return hits


# ------------------------------------------------------------------ craters
def add_crater(game, p) -> None:
    """Crater record: [position, radius, dps, seconds left, source tower, seconds since the last hit]."""
    radius, dps = ((cfg.POWER_CRATER_RADIUS, cfg.POWER_CRATER_DPS) if p.power_crater
                   else (cfg.CRATER_RADIUS, cfg.CRATER_DPS))
    game.craters.append([p.pos.copy(), radius, dps, cfg.CRATER_DURATION, p.source, 0.0])
    game.fx.vfx.ring(p.pos, 8, radius, 0.5, (255, 100, 30), 4)


def tick_craters(game, dt: float) -> None:
    """Every CRATER_TICK seconds a crater hits each enemy inside it for DPS * tick, through Game.hit_enemy
    (armor loses one hit per tick; a hit every frame would strip armor at once and spam particles and sound)."""
    for crater in game.craters:
        pos, radius, dps, _left, source, _since = crater
        crater[3] -= dt
        crater[5] += dt
        if crater[5] < cfg.CRATER_TICK:
            continue
        crater[5] -= cfg.CRATER_TICK
        for enemy in game.enemies:
            if enemy.alive and enemy.pos.distance_to(pos) <= radius + enemy.radius:
                game.hit_enemy(enemy, dps * cfg.CRATER_TICK, color=(255, 105, 35), source=source)
    game.craters = [c for c in game.craters if c[3] > 0]


# ------------------------------------------------------------------ drawing
def draw_state(surface, tower, x: int, y: int) -> None:
    """Orange pips = empowered Meteor shots left; cyan bar = time left of Arigatou, Gyro."""
    import pygame
    from data.settings import TOWER_RADIUS
    top = y - TOWER_RADIUS * 3 - 4
    for i in range(tower.power_shots):
        px = x - (tower.power_shots - 1) * 5 + i * 10
        pygame.draw.circle(surface, (36, 20, 14), (px, top), 5)
        pygame.draw.circle(surface, (255, 120, 45), (px, top), 4)
    if tower.gyro_timer > 0:
        bar = pygame.Rect(x - 17, top - 9, 34, 6)
        pygame.draw.rect(surface, (20, 40, 50), bar.inflate(2, 2), border_radius=3)
        frac = tower.gyro_timer / cfg.GYRO_DURATION
        pygame.draw.rect(surface, (100, 220, 230), (bar.x, bar.y, max(2, int(bar.w * frac)), bar.h), border_radius=3)


def draw_stand_gag(surface, tower, x: int, y: int) -> None:
    """Original, deliberately childlike stand gag beside him: wonky crayon strokes and mismatched eyes
    (Accuracy tier 3; tier 4 adds more doodles)."""
    import pygame
    wiggle = int(math.sin(pygame.time.get_ticks() / 110) * 2)
    cx, cy = x + 29, y - 39
    pygame.draw.circle(surface, (255, 240, 150), (cx, cy), 15, 2)
    pygame.draw.line(surface, (80, 65, 170), (cx - 10, cy - 8), (cx + 8, cy - 12 + wiggle), 4)
    pygame.draw.line(surface, (230, 70, 90), (cx - 8, cy + 9), (cx + 12, cy + 5), 3)
    pygame.draw.circle(surface, (25, 25, 40), (cx - 4, cy - 2), 2)
    pygame.draw.circle(surface, (25, 25, 40), (cx + 6, cy + 1), 3)
    pygame.draw.line(surface, (255, 220, 80), (cx + 2, cy + 13), (cx + 20, cy + 17), 3)
    if tower.tiers[1] >= 4:
        pygame.draw.line(surface, (80, 190, 230), (cx - 14, cy - 13), (cx - 21, cy - 22 + wiggle), 2)
        pygame.draw.line(surface, (245, 90, 160), (cx + 13, cy - 7), (cx + 23, cy - 2), 2)
        pygame.draw.circle(surface, (255, 255, 255), (cx + 17, cy - 15), 2)
        pygame.draw.line(surface, (70, 45, 120), (cx - 6, cy + 5), (cx + 5, cy + 3), 2)
