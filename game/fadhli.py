"""Fadhli: a thrower. Path A = Garp (heavy cannonballs), path B = Johnny + Tusk (bouncing steel balls).

All numbers live in data/fadhli.py. Hooks used by the rest of the game:
  Tower.__init__    -> init_tower()
  Tower.update      -> tick_tower()       (the whole attack cycle: charge -> release -> cooldown, barrage, ability timers)
  effects.py        -> bounce(), status(), shove(), crater()   ("fadhli_bounce", "fadhli_status", "garp_knockback", "garp_crater", on every hit)
  Game._step        -> update_world()     (hot craters: burn Didits, age, vanish)
  actives.py        -> start_galaxy(), start_golden()
  Tower.draw        -> draw_charge(), draw_barrage(), charge_shake()
  Game.draw         -> draw_world() (hot craters + the inner melee circle)

Base Fadhli (no upgrades) looks and sounds like a regular tower: a short invisible wind-up, a plain rock, the generic hit
effects. Only a Garp (path A) or Johnny (path B) gets the charge visuals, shaking, big impacts and the rest.

Attack cycle: when the cooldown is over and a Didit is in range, Fadhli CHARGES (wind-up: particles are pulled in, he
shakes, a ball grows above his head). When the charge is full the throw leaves his hand at the best target in range, and
the cooldown starts. Attack-speed buffs speed up both the charge and the cooldown.
"""
from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

import pygame

from data import fadhli as cfg
from game import gfx
from game.projectile import Projectile
from game.utils import Vec, draw_outlined

if TYPE_CHECKING:
    from game.enemy import Enemy
    from game.game import Game
    from game.tower import Tower

GARP_COL = (255, 150, 60)
MEGA_COL = (255, 236, 130)
JOHNNY_COL = (170, 225, 255)
GOLD = (255, 214, 70)


# ------------------------------------------------------------------ helpers
def is_garp(t: "Tower") -> bool:
    return t.kind == "fadhli" and t.tiers[0] > 0 and t.tiers[0] >= t.tiers[1]


def is_johnny(t: "Tower") -> bool:
    return t.kind == "fadhli" and t.tiers[1] > 0 and t.tiers[1] > t.tiers[0]


def is_base(t: "Tower") -> bool:
    """Fadhli without any upgrade: plain rock throws, no charge visuals, no impact show."""
    return t.kind == "fadhli" and t.tiers[0] == 0 and t.tiers[1] == 0


def boss_mult(p: Projectile, enemy: "Enemy") -> float:
    """Garp tier 3+: x3 damage against bosses (direct hits and the mega throw, not the crater burn)."""
    src = p.source
    if src is None or src.kind != "fadhli" or p.melee or not enemy.is_boss:
        return 1.0
    if is_garp(src) and src.tiers[0] >= cfg.GARP_BOSS_MULT_MIN_TIER:
        return cfg.GARP_BOSS_MULT
    return 1.0


def init_tower(t: "Tower") -> None:
    t.charging = False
    t.charge_t = 0.0
    t.charge_need = 1.0
    t.charge_mega = False
    t.charge_fx = 0.0        # timer between charge particles
    t.mega_t = 0.0           # seconds the Galaxy Impact mega throw stays ready
    t.golden_t = 0.0         # seconds of Golden Ratio left
    t.golden_mult = 1.0      # damage multiplier of the NEXT throw while Golden Ratio runs
    t.melee_cd = 0.0
    t.barraging = 0.0        # >0 while the barrage hit something recently (drawing)


def charge_time(t: "Tower") -> float:
    if is_johnny(t):
        return cfg.JOHNNY_CHARGE
    return cfg.GARP_CHARGE[min(t.tiers[0], len(cfg.GARP_CHARGE) - 1)]


def has_barrage(t: "Tower") -> bool:
    return "fadhli_barrage" in t.effects


def melee_radius(t: "Tower") -> float:
    return min(cfg.MELEE_RADIUS, t.stats["range"] - 20)


# ------------------------------------------------------------ the attack cycle
def tick_tower(t: "Tower", game: "Game", dt: float, rate: float) -> None:
    """Called every simulation step instead of the generic attack code."""
    if t.golden_t > 0:                                   # Golden Ratio also speeds him up (see GOLDEN_ATTACK_SPEED)
        rate *= cfg.GOLDEN_ATTACK_SPEED
    t.cooldown_left = max(0.0, t.cooldown_left - dt * rate)
    t.barraging = max(0.0, t.barraging - dt)
    if t.mega_t > 0:
        t.mega_t = max(0.0, t.mega_t - dt)
    if t.golden_t > 0:
        t.golden_t -= dt
        if t.golden_t <= 0:
            t.golden_t, t.golden_mult = 0.0, 1.0
            game.fx.golden_off(t)
    if has_barrage(t):
        _barrage(t, game, dt * (rate / cfg.GOLDEN_ATTACK_SPEED if t.golden_t > 0 else rate))   # the barrage keeps its own pace

    if t.charging:
        t.charge_t += dt * rate
        f = min(1.0, t.charge_t / t.charge_need)
        tgt = t.pick_target(game.enemies)
        if tgt is not None and tgt.pos != t.pos:
            t.aim = (tgt.pos - t.pos).normalize()
        t.charge_fx -= dt
        if t.charge_fx <= 0:
            t.charge_fx = 0.05
            game.fx.fadhli_charging(t, f)
        if t.charge_t >= t.charge_need:
            t.charging = False
            if tgt is None:                  # everyone left the range during the wind-up: the throw is lost
                t.charge_mega = False
                game.fx.fadhli_cancel(t)
            else:
                _release(t, game, tgt)
        return
    if t.cooldown_left > 0:
        return
    target = t.pick_target(game.enemies)
    if target is None:
        return
    _start_charge(t, game)


def _start_charge(t: "Tower", game: "Game") -> None:
    t.charging = True
    t.charge_t = 0.0
    t.charge_mega = t.mega_t > 0 and "galaxy_active" in t.effects
    if t.charge_mega:
        t.mega_t = 0.0
    t.charge_need = max(0.05, charge_time(t) * (cfg.GALAXY_CHARGE_MULT if t.charge_mega else 1.0))
    t.charge_fx = 0.0
    game.fx.fadhli_charge_start(t)


def _release(t: "Tower", game: "Game", target: "Enemy") -> None:
    s = t.stats
    mega = t.charge_mega
    t.charge_mega = False
    damage = s["damage"]
    if t.golden_t > 0:                                   # Golden Ratio: D/4, then x1.618 after every throw
        damage *= t.golden_mult
        t.golden_mult = min(cfg.GOLDEN_MAX_MULT, t.golden_mult * cfg.PHI)
    aoe = s["aoe_radius"]
    if mega:
        damage = s["damage"] * cfg.GALAXY_DAMAGE_MULT
        aoe = max(cfg.GALAXY_AOE_MIN, aoe * cfg.GALAXY_AOE_MULT)
    hand = t.pos + Vec(14 if t.aim.x >= 0 else -14, -14)
    p = Projectile(hand, target, s["proj_speed"], damage, aoe, s["slow"], s["slow_duration"], s["money_per_hit"], t.color, t)
    p.mega = mega
    p.scale = 2.0 if mega else cfg.GARP_PROJ_SCALE
    p.total = max(1.0, hand.distance_to(target.pos))
    if is_johnny(t):
        p.arc = 0.0
        if "fadhli_bounce" in t.effects:
            p.bounce_chance = cfg.BOUNCE_START_CHANCE
    elif is_base(t):
        p.arc = 0.0                                      # a plain straight throw, like every other tower
    else:
        p.arc = cfg.GALAXY_ARC if mega else cfg.GARP_ARC
    game.projectiles.append(p)
    t.cooldown_left = s["cooldown"]
    t.kick = 0.18
    if target.pos != t.pos:
        t.aim = (target.pos - t.pos).normalize()
    game.fx.fadhli_throw(t, mega)


# ----------------------------------------------------------------- on-hit effects
def bounce(game: "Game", tower: "Tower", p: Projectile, victims: list) -> None:
    """Johnny tier 2+: after a hit the steel ball keeps going with chance `p.bounce_chance` (50%, then -5 points per bounce)."""
    if p.melee or p.bounce_chance <= 0 or p.bounces >= cfg.BOUNCE_MAX:
        return
    if random.random() >= p.bounce_chance:
        game.fx.fadhli_ball_stops(p.pos)
        return
    cands = [e for e in game.enemies
             if e.alive and e is not p.target and p.pos.distance_to(e.pos) <= cfg.BOUNCE_RANGE + e.radius]
    if not cands:
        game.fx.fadhli_ball_stops(p.pos)
        return
    cands.sort(key=lambda e: (e in p.hit_list, p.pos.distance_to(e.pos)))   # prefer Didits this ball has not hit yet
    nxt = cands[0]
    q = Projectile(p.pos, nxt, tower.stats["proj_speed"] * cfg.BOUNCE_SPEED_MULT, p.damage, p.aoe_radius,
                   p.slow, p.slow_duration, p.money_on_hit, p.color, tower)
    q.bounces = p.bounces + 1
    q.bounce_chance = max(0.0, round(p.bounce_chance - cfg.BOUNCE_DECAY, 6))   # rounded: no float drift
    q.hit_list = [*p.hit_list, p.target]
    q.total = max(1.0, p.pos.distance_to(nxt.pos))
    game.projectiles.append(q)
    game.fx.fadhli_bounce(p.pos, nxt.pos, q.bounces)


def status(game: "Game", tower: "Tower", p: Projectile, victims: list) -> None:
    """Johnny tier 3+: every hit rolls once: 20% stun, 30% slow, 50% nothing."""
    if p.melee:
        return
    for e in victims:
        if not e.alive:
            continue
        r = random.random()
        if r < cfg.STATUS_STUN_CHANCE:
            if not e.is_boss:
                e.stun(cfg.STATUS_STUN_TIME)
                game.fx.fadhli_stun(e)
        elif r < cfg.STATUS_STUN_CHANCE + cfg.STATUS_SLOW_CHANCE:
            e.apply_slow(cfg.STATUS_SLOW, cfg.STATUS_SLOW_TIME)
            game.fx.fadhli_slow(e)


def shove(game: "Game", tower: "Tower", p: Projectile, victims: list) -> None:
    """Garp tier 3+: heavy hits knock Didits back along the path (bosses only a quarter as far)."""
    if p.melee:
        return
    for e in victims:
        if not e.alive or game.time < getattr(e, "garp_kb_ready", 0.0):
            continue
        e.garp_kb_ready = game.time + cfg.GARP_KNOCKBACK_INTERVAL
        dist = cfg.GARP_KNOCKBACK_DISTANCE * (cfg.GARP_KNOCKBACK_BOSS_MULT if e.is_boss else 1.0)
        e.distance = max(0.0, e.distance - dist)
        e.pos = e.path.position_at(e.distance)
        game.fx.knocked(e)


# ------------------------------------------------------------------ hot craters (Garp tier 2+)
def crater_stats(t: "Tower", mega: bool = False) -> dict | None:
    """Radius / burn damage per tick / lifetime of the crater this Garp leaves (None below tier 2)."""
    tier = t.tiers[0]
    if not is_garp(t) or tier < 2:
        return None
    c = dict(cfg.CRATER_TIERS[min(tier, max(cfg.CRATER_TIERS))])
    if mega:
        c["radius"] *= cfg.CRATER_MEGA_RADIUS_MULT
        c["damage"] *= cfg.CRATER_MEGA_DAMAGE_MULT
        c["seconds"] *= cfg.CRATER_MEGA_SECONDS_MULT
    return c


def crater(game: "Game", tower: "Tower", p: Projectile) -> None:
    """Garp tier 2+: the throw that just landed leaves a hot crater at the impact point."""
    if p.melee:
        return
    c = crater_stats(tower, p.mega)
    if c is None:
        return
    game.craters.append({"pos": Vec(p.pos), "radius": c["radius"], "damage": c["damage"], "t": c["seconds"],
                         "total": c["seconds"], "tick": cfg.CRATER_TICK, "mega": p.mega, "tier": tower.tiers[0],
                         "seed": random.randint(0, 9999), "born": game.time})
    while len(game.craters) > cfg.CRATER_MAX:
        game.craters.pop(0)
    game.fx.crater_born(p.pos, c["radius"], p.mega)


def update_world(game: "Game", dt: float) -> None:
    """Once per simulation step: burn every Didit standing in a crater (armored Didits are shielded), age the craters."""
    for c in list(game.craters):
        c["t"] -= dt
        c["tick"] -= dt
        if c["tick"] <= 0:
            c["tick"] += cfg.CRATER_TICK
            for e in list(game.enemies):
                if e.alive and e.armor <= 0 and c["pos"].distance_to(e.pos) <= c["radius"] + e.radius:
                    game.hit_enemy(e, c["damage"], color=(255, 120, 40), source=None, quiet=True)
        if c["t"] <= 0:
            game.craters.remove(c)


_CRATER_SPRITES: dict[tuple, pygame.Surface] = {}


def _crater_sprite(r: int, seed: int) -> pygame.Surface:
    """Scorched ground: dark soot disc, a raised rim and a few cracks (static, the glow is drawn on top)."""
    key = (r, seed % 6)
    if key in _CRATER_SPRITES:
        return _CRATER_SPRITES[key]
    w, h = 2 * r + 12, int(1.2 * r) + 12
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    cx, cy = w // 2, h // 2
    rx, ry = r, int(r * 0.58)
    pygame.draw.ellipse(surf, (22, 14, 10, 150), (cx - rx - 5, cy - ry - 3, 2 * rx + 10, 2 * ry + 7))   # soot halo
    pygame.draw.ellipse(surf, (70, 52, 40, 255), (cx - rx, cy - ry, 2 * rx, 2 * ry))                    # raised rim
    pygame.draw.ellipse(surf, (28, 18, 14, 255), (cx - rx + 4, cy - ry + 3, 2 * rx - 8, 2 * ry - 6))    # pit
    rnd = random.Random(seed % 6)
    for _ in range(7):                                                                                  # cracks
        a = rnd.uniform(0, math.tau)
        ln = rnd.uniform(0.7, 1.15)
        p0 = (cx + math.cos(a) * rx * 0.25, cy + math.sin(a) * ry * 0.25)
        p1 = (cx + math.cos(a) * rx * ln, cy + math.sin(a) * ry * ln)
        pygame.draw.line(surf, (12, 8, 6, 255), p0, p1, 3)
    _CRATER_SPRITES[key] = surf
    return surf


def _draw_craters(surface: pygame.Surface, game: "Game") -> None:
    now = pygame.time.get_ticks() / 1000
    for c in game.craters:
        r = int(c["radius"])
        x, y = int(c["pos"].x), int(c["pos"].y)
        frac = max(0.0, c["t"] / c["total"])
        fade = min(1.0, c["t"] / 0.9)                                    # dies out in the last 0.9 s
        base = _crater_sprite(r, c["seed"])
        base.set_alpha(int(255 * fade))
        surface.blit(base, base.get_rect(center=(x, y)))
        pulse = 0.8 + 0.2 * math.sin(now * 6 + c["seed"])
        heat = (0.35 + 0.65 * frac) * fade * pulse                       # the lava cools down with time
        ry = int(r * 0.58)
        lava = pygame.Surface((2 * r + 4, 2 * ry + 4), pygame.SRCALPHA)
        w1, h1 = int(1.0 * r), int(1.0 * ry)                            # glowing lava pool inside the dark pit
        pygame.draw.ellipse(lava, (230, 70, 16, int(190 * heat)), (r + 2 - w1 // 2, ry + 2 - h1 // 2, w1, h1))
        w2, h2 = int(0.5 * r), int(0.5 * ry)
        pygame.draw.ellipse(lava, (255, 170, 50, int(210 * heat)), (r + 2 - w2 // 2, ry + 2 - h2 // 2, w2, h2))
        surface.blit(lava, lava.get_rect(center=(x, y)))
        q = (int(90 * heat) // 20) * 20 + 20                             # quantised, gfx.glow caches per alpha
        g = gfx.glow(int(r * 0.9), (255, 90, 20), q)                      # soft orange heat haze (normal blend, not additive)
        surface.blit(g, g.get_rect(center=(x, y - 4)))
        if random.random() < 0.18 * fade:                                # embers rising
            game.fx.vfx.burst(c["pos"] + Vec(random.uniform(-r, r) * 0.6, random.uniform(-r, r) * 0.3), (255, 160, 60),
                              1, 22, 0.7, 3, -70)


# ------------------------------------------------------------------- the barrage
def _barrage(t: "Tower", game: "Game", dt: float) -> None:
    """Tusk Act 4: melee hits on every Didit inside the inner circle, at the same time as the throws."""
    t.melee_cd -= dt
    if t.melee_cd > 0:
        return
    r = melee_radius(t)
    inside = [e for e in game.enemies if e.alive and t.pos.distance_to(e.pos) <= r + e.radius]
    if not inside:
        t.melee_cd = 0.0
        return
    t.melee_cd = cfg.MELEE_INTERVAL
    inside.sort(key=lambda e: t.pos.distance_to(e.pos))
    dmg = t.stats["damage"] * cfg.MELEE_DAMAGE_MULT
    t.barraging = 0.3
    hit = inside[:cfg.MELEE_MAX_TARGETS]
    for e in hit:
        game.hit_enemy(e, dmg, color=(255, 226, 110), source=None)
    game.fx.fadhli_barrage(t, hit)


# ----------------------------------------------------------------------- abilities
def start_galaxy(game: "Game", t: "Tower") -> bool:
    """Garp tier 4: the next throw becomes a giant mega throw (charges longer, hits far harder, huge splash)."""
    if t.charge_mega or t.mega_t > 0:
        return False
    t.mega_t = cfg.GALAXY_WINDOW
    game.fx.galaxy_on(t)
    return True


def start_golden(game: "Game", t: "Tower") -> bool:
    """Johnny tier 4: Golden Ratio. For 5 s the damage is divided by 4, then x1.618 after every throw."""
    if t.golden_t > 0:
        return False
    t.golden_t = cfg.GOLDEN_DURATION
    t.golden_mult = 1.0 / cfg.GOLDEN_START_DIVISOR
    game.fx.golden_on(t)
    return True


# ---------------------------------------------------------------------------- drawing
def charge_frac(t: "Tower") -> float:
    return min(1.0, t.charge_t / t.charge_need) if getattr(t, "charging", False) else 0.0


def charge_shake(t: "Tower") -> tuple[int, int]:
    """Garp trembles while he charges (more with every bit of charge)."""
    if not getattr(t, "charging", False) or is_johnny(t) or is_base(t):
        return 0, 0
    a = 0.4 + 2.2 * charge_frac(t) * (1.6 if t.charge_mega else 1.0)
    return round(random.uniform(-a, a)), round(random.uniform(-a * 0.5, a * 0.5))


def draw_charge(surface: pygame.Surface, t: "Tower", x: int, y: int) -> None:
    """Charging visuals: a ball growing above Garp's head with a heat glow, ground cracks and a shrinking ring;
    Johnny: a small gold spin ring at his hand and a stand glow."""
    if not getattr(t, "charging", False) or is_base(t):
        return
    f = charge_frac(t)
    mega = t.charge_mega
    pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / (60 if f < 0.7 else 35))
    if is_johnny(t):
        hx = x + (14 if t.aim.x >= 0 else -14)
        g = gfx.glow(int(16 + 14 * f), JOHNNY_COL, int(90 + 110 * f))
        surface.blit(g, g.get_rect(center=(hx, y - 14)), special_flags=pygame.BLEND_RGB_ADD)
        for i in range(3):
            a = pygame.time.get_ticks() / 90 + i * math.tau / 3
            pygame.draw.circle(surface, GOLD, (int(hx + math.cos(a) * (10 + 4 * f)), int(y - 14 + math.sin(a) * 5)), 2)
        return
    col = MEGA_COL if mega else GARP_COL
    big = 1.7 if mega else 1.0
    g = gfx.glow(int((22 + 22 * f) * big), col, int(25 + 45 * f))                       # heat glow around him
    surface.blit(g, g.get_rect(center=(x, y - 24)), special_flags=pygame.BLEND_RGB_ADD)
    rad = (6 + 9 * f) * (1.8 if mega else 1.0)                                              # the ball above his head
    by = y - 58 - 8 * f * big
    halo = gfx.glow(int(rad * 1.9), col, int(50 + 50 * pulse))
    surface.blit(halo, halo.get_rect(center=(x, by)), special_flags=pygame.BLEND_RGB_ADD)
    ball = gfx.sphere(rad, (74, 80, 98), bounce=col, shine=1.0)
    ball = pygame.transform.smoothscale(ball, (max(4, int(rad * 2 + 2)), max(4, int(rad * 2 + 2))))
    surface.blit(ball, ball.get_rect(center=(x, by)))
    ring_r = (62 - 40 * f) * big                                                              # ring closing in on him
    pygame.draw.ellipse(surface, col, (x - ring_r, y + 4 - ring_r * 0.45, ring_r * 2, ring_r * 0.9), 2 if f < 0.8 else 3)
    random.seed(int(t.pos.x * 7 + t.pos.y))                                                    # stable crack pattern per tower
    for i in range(7):                                                                         # cracks spreading from the pedestal
        a = i / 7 * math.tau + 0.3
        ln = (16 + 34 * f) * big * random.uniform(0.7, 1.0)
        p0 = (x + math.cos(a) * 20, y + 8 + math.sin(a) * 8)
        p1 = (x + math.cos(a) * (20 + ln), y + 8 + math.sin(a) * (8 + ln * 0.4))
        pygame.draw.line(surface, (60, 40, 30), p0, p1, 2)
        pygame.draw.line(surface, col, p0, p1, 1)
    random.seed()
    if f > 0.85:                                                                               # about to release: white-hot flash
        w = gfx.glow(int(14 * big), (255, 255, 255), int(70 * (f - 0.85) / 0.15))
        surface.blit(w, w.get_rect(center=(x, by)), special_flags=pygame.BLEND_RGB_ADD)


def draw_barrage(surface: pygame.Surface, t: "Tower", x: int, y: int) -> None:
    """Tusk Act 4's fists: a flurry of ghost fists around the stand while the barrage hits something."""
    if t.barraging <= 0:
        return
    k = pygame.time.get_ticks()
    sx, sy = x + 36, y - 40
    for i in range(7):
        a = (k / 40 + i * 0.9) % math.tau
        px = sx + math.cos(a) * 22 + math.sin(k / 23 + i) * 6
        py = sy + math.sin(a * 1.3) * 14
        g = gfx.glow(9, GOLD if i % 2 else (255, 255, 255), 160)
        surface.blit(g, g.get_rect(center=(int(px), int(py))), special_flags=pygame.BLEND_RGB_ADD)


def draw_world(surface: pygame.Surface, game: "Game") -> None:
    """Hot craters on the ground + the inner circle of a Tusk Act 4 Fadhli (the range of the melee barrage)."""
    _draw_craters(surface, game)
    t0 = pygame.time.get_ticks() / 1000
    for t in game.towers:
        if t.kind != "fadhli" or not has_barrage(t):
            continue
        r = int(melee_radius(t))
        x, y = int(t.pos.x), int(t.pos.y)
        selected = t is game.selected
        alpha = 38 + (30 if t.barraging > 0 else 0) + (24 if selected else 0)
        disc = pygame.Surface((2 * r + 4, 2 * r + 4), pygame.SRCALPHA)
        pygame.draw.circle(disc, (*GOLD, alpha), (r + 2, r + 2), r)
        for i in range(24):                                                                   # dashed rotating rim
            a0 = t0 * 0.6 + i / 24 * math.tau
            pygame.draw.arc(disc, (*GOLD, 230 if selected or t.barraging > 0 else 130), (2, 2, 2 * r, 2 * r), a0, a0 + 0.17, 3)
        surface.blit(disc, (x - r - 2, y - r - 2))
        if selected:
            draw_outlined(surface, "BARRAGE", (x, y + r + 12), 15, GOLD, center=True, width=1)
