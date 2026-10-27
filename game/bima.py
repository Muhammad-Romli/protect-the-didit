"""Bima (Mathematician): Graph path (formula curves + Brain Energy) and Geometry path (shape stacks, collision,
Cube / Pyramid / Sphere abilities). Numbers: data/bima.py. UI for typing: game/bima_ui.py.

Tower hooks: Tower.__init__ -> init_tower, Tower.update -> tick_tower + prepare_projectile,
EFFECTS["geo_effects"] -> geo_on_hit, Game._step -> update_world, Game.draw -> draw_world / draw_preview.
"""
from __future__ import annotations

import math

import pygame

from data.bima import ABILITIES, GEOMETRY, GRAPH, UNIT
from data.settings import BUILD_RECT, START_STASH_HP
from game import gfx, sprites_proc
from game.curves import CurveShot, sample_curve
from game.formula import FormulaError, compile_formula
from game.utils import Vec, draw_outlined

BOUNDS = pygame.Rect(*BUILD_RECT)
SHOT_COLOR = (255, 170, 70)


# ------------------------------------------------------------------ setup
def init_tower(t) -> None:
    t.brain, t.brain_init = 0.0, False
    t.shot_cd = 0.0
    t.formula, t.graph_dir = "x", 1
    t.preview, t._pkey, t._compiled = None, None, (None, None, None)
    t.shape_i = 0
    t.buff_timer = 0.0
    t.lockout = 0.0


def graph_tier(t) -> int:
    return t.tiers[0] if t.kind == "bima" else 0


def geo_tier(t) -> int:
    return t.tiers[1] if t.kind == "bima" else 0


def buff_active(t) -> bool:
    return t.kind == "bima" and t.buff_timer > 0


def brain_max(t) -> float:
    return GRAPH["brain_max"][graph_tier(t)]


def tick_tower(t, game, dt: float) -> None:
    t.shot_cd = max(0.0, t.shot_cd - dt)
    t.lockout = max(0.0, t.lockout - dt)
    t.buff_timer = max(0.0, t.buff_timer - dt)
    mx = brain_max(t)
    if mx:
        if not t.brain_init:
            t.brain, t.brain_init = mx, True
        t.brain = min(mx, t.brain + GRAPH["regen"][graph_tier(t)] * dt)  # preparation AND battle, no activity cost


# ------------------------------------------------------------------ graph
def compiled(t):
    level = GRAPH["func_level"][graph_tier(t)]
    key = (t.formula, level)
    if t._compiled[0] != key:
        try:
            f, pretty = compile_formula(t.formula, level)
            t._compiled = (key, (f, pretty), None)
        except FormulaError as e:
            t._compiled = (key, None, e)
    return t._compiled


def update_preview(t, force: bool = False) -> dict | None:
    """Re-sample the live curve when the formula / direction / tier / position changed."""
    gt = graph_tier(t)
    if gt < 2:
        t.preview = None
        return None
    key = (t.formula, t.graph_dir, gt, round(t.pos.x), round(t.pos.y))
    if key == t._pkey and not force:
        return t.preview
    t._pkey = key
    _, ok, err = compiled(t)
    if err is not None or ok is None:
        t.preview = {"error": err.msg if err else "?", "pos": err.pos if err else -1}
        return t.preview
    f, pretty = ok
    res = sample_curve(f, t.pos, t.graph_dir, GRAPH["range_units"][gt], BOUNDS)
    if "error" in res:
        t.preview = {"error": res["error"], "pos": -1}
        return t.preview
    cost = math.ceil(GRAPH["cost_base"][gt] + GRAPH["cost_per_unit"][gt] * res["length"])
    t.preview = {**res, "cost": cost, "pretty": pretty}
    return t.preview


def can_fire_now(game, t) -> bool:
    pv = t.preview
    return bool(pv and "cost" in pv and game.phase.value == "battle" and t.shot_cd <= 0 and pv["cost"] <= t.brain)


def fire_graph(game, t) -> bool:
    gt = graph_tier(t)
    if gt < 2:
        return False
    pv = update_preview(t)
    if pv is None or "error" in pv:
        game.fx.invalid()
        game.flash(pv["error"] if pv else "No formula", 1.6)
        return False
    if game.phase.value != "battle":
        game.fx.invalid()
        game.flash("Curves can be fired during a battle (preview them now)", 1.6)
        return False
    if t.shot_cd > 0:
        return False
    if pv["cost"] > brain_max(t):
        game.fx.invalid()
        game.flash(f"This curve costs {pv['cost']} - more than your max Brain Energy ({int(brain_max(t))})", 2.0)
        return False
    if pv["cost"] > t.brain:
        game.fx.invalid()
        wait = (pv["cost"] - t.brain) / GRAPH["regen"][gt]
        game.flash(f"Not enough Brain Energy: need {pv['cost']}, have {int(t.brain)} (ready in {wait:.1f}s)", 2.0)
        return False
    t.brain -= pv["cost"]
    t.shot_cd = GRAPH["shot_cooldown"][gt]
    shot = CurveShot(t, pv["pts"], pv["cum"], gt, t.stats["damage"] * GRAPH["dmg_mult"][gt])
    shot.cost = pv["cost"]
    shot.finalized = False
    game.shots.append(shot)
    t.kick = 0.1
    game.fx.graph_fire(t, pv["cost"])
    return True


def _build_grid(enemies) -> dict:
    grid: dict = {}
    for e in enemies:
        if e.alive:
            grid.setdefault((int(e.pos.x // 64), int(e.pos.y // 64)), []).append(e)
    return grid


# --------------------------------------------------------------- geometry
def prepare_projectile(t, game, target, proj) -> None:
    gt = geo_tier(t)
    if gt < 1:
        return
    mask = getattr(target, "shape_mask", 0)
    shape = None
    if gt >= 2:  # per-target assignment: first empty slot in the order square -> triangle -> circle
        shape = next((s for s in (0, 1, 2) if not mask & (1 << s)), None)
    if shape is None:
        shape = t.shape_i % 3
    t.shape_i += 1
    proj.shape, proj.solid = shape, gt >= 3
    if gt >= 2:
        if shape == 1:
            proj.damage *= GEOMETRY["triangle_mult"][gt]
        elif shape == 2:
            proj.slow = max(proj.slow, GEOMETRY["circle_slow"][gt])
            proj.slow_duration = max(proj.slow_duration, GEOMETRY["circle_slow_dur"][gt])
    if t.buff_timer > 0:
        proj.damage *= 1 + ABILITIES["pyramid_active"]["damage"]


def geo_on_hit(game, t, e, proj) -> None:
    shape = getattr(proj, "shape", None)
    gt = geo_tier(t)
    if shape is None or gt < 2 or not e.alive:
        return
    game.fx.shape_hit(e, shape, gt >= 3)
    if shape == 0:
        e.vuln, e.vuln_timer = GEOMETRY["vuln"][gt], GEOMETRY["vuln_dur"][gt]
    e.shape_mask |= 1 << shape        # same shape twice adds nothing
    if e.shape_mask == 7 and game.time >= e.collision_ready:
        trigger_collision(game, t, e)


def trigger_collision(game, t, e) -> None:
    gt = geo_tier(t)
    e.shape_mask = 0
    e.collision_ready = game.time + (GEOMETRY["collision_cd_boss"] if e.is_boss else GEOMETRY["collision_cd"])
    game.fx.geo_converge(e, gt >= 3)
    game.delayed.append([GEOMETRY["windup"], lambda: _collide(game, t, e)])


def collision_damage(t, e) -> float:
    gt = geo_tier(t)
    D = t.stats["damage"]
    pct = GEOMETRY["collision_pct"][gt] * e.max_hp * (GEOMETRY["boss_pct_mult"] if e.is_boss else 1.0)
    pct = min(pct, GEOMETRY["collision_pct_cap"][gt] * D)            # the percent part has its own cap
    return min(GEOMETRY["collision_flat"][gt] * D + pct, GEOMETRY["collision_total_cap"] * D)


def _collide(game, t, e) -> None:
    dmg = collision_damage(t, e)
    if e.alive:
        game.hit_enemy(e, dmg, color=(255, 240, 160), source=t)
    game.fx.geo_impact(e, dmg, geo_tier(t) >= 3)
    if e.is_boss or game.time - game.last_hitstop > 0.5:
        game.hitstop, game.last_hitstop = GEOMETRY["hitstop"], game.time


# -------------------------------------------------------------- abilities
class Cube:
    def __init__(self, tower, dist: float, pos: Vec, hp: float, duration: float) -> None:
        self.tower, self.dist, self.pos = tower, dist, pos
        self.hp = self.max_hp = hp
        self.t_left = self.max_t = duration
        self.attackers: list = []


def nearest_path_distance(path, pos: Vec) -> tuple[float, float]:
    """(distance along the path, distance from pos to the path) of the nearest path point."""
    best_d, best = 0.0, 1e9
    step = 8.0
    d = 0.0
    while d <= path.length:
        q = path.position_at(d).distance_to(pos)
        if q < best:
            best, best_d = q, d
        d += step
    return best_d, best


def place_cube(game, t, pos) -> bool:
    cfg = ABILITIES["cube_active"]
    pos = Vec(pos)
    if len(game.cubes) >= cfg["max_active"]:
        game.flash("Too many cubes at once", 1.5)
        return False
    d, off = nearest_path_distance(game.path, pos)
    if off > cfg["snap_px"]:
        game.flash("Place the cube on the path", 1.5)
        return False
    p = game.path.position_at(d)
    if p.distance_to(t.pos) > cfg["place_range"]:
        game.flash("Too far from Bima", 1.5)
        return False
    if d < cfg["min_from_spawn"] or game.path.length - d < cfg["min_from_base"]:
        game.flash("Too close to the spawn or the base", 1.5)
        return False
    hp = cfg["hp_mult_d"] * t.stats["damage"]
    game.cubes.append(Cube(t, d, p, hp, cfg["duration"]))
    game.fx.cube_placed(p)
    return True


def cast_sphere(game, t, pos) -> bool:
    cfg = ABILITIES["sphere_active"]
    pos = Vec(pos)
    if pos.distance_to(t.pos) > cfg["place_range"]:
        game.flash("Too far from Bima", 1.5)
        return False
    game.zones.append({"pos": pos, "r": cfg["zone_r"], "t": cfg["zone_time"], "n": 0})
    game.shield = max(game.shield, cfg["shield_pct"] * START_STASH_HP)
    game.shield_t = cfg["shield_time"]
    from data.map import STASH_POS
    game.fx.sphere_cast(pos, cfg["zone_r"], Vec(STASH_POS))
    return True


def cast_pyramid(game, t) -> bool:
    t.buff_timer = ABILITIES["pyramid_active"]["duration"]
    game.fx.pyramid_on(t)
    return True


def update_world(game, dt: float) -> None:
    """Curve shots, cubes (block + thorns), sphere zones and shield. Runs once per simulation step."""
    if game.shots:
        grid = _build_grid(game.enemies)
        for s in game.shots:
            def on_hit(e, k, s=s):
                dmg = s.damage * max(GRAPH["falloff_floor"], s.falloff ** k)
                game.hit_enemy(e, dmg, color=SHOT_COLOR, source=s.tower)
            s.advance(dt, grid, on_hit)
            if s.s >= s.total and not s.finalized:
                s.finalized = True
                if s.hits == 0:  # missed everything: part of the energy comes back
                    back = s.cost * GRAPH["miss_refund"]
                    s.tower.brain = min(brain_max(s.tower), s.tower.brain + back)
                    game.fx.vfx.text(s.tower.pos + Vec(0, -44), f"+{int(back)} refund", (130, 215, 255), 20, 0.8, 26)
        game.shots = [s for s in game.shots if not s.done]
    if game.cubes:
        _update_cubes(game, dt)
    if game.zones:
        _update_zones(game, dt)
    if game.shield_t > 0:
        game.shield_t -= dt
        if game.shield_t <= 0:
            game.shield = 0.0


def _update_cubes(game, dt: float) -> None:
    cfg = ABILITIES["cube_active"]
    for e in game.enemies:
        e.blocked = False
        e.cube_immune = max(0.0, e.cube_immune - dt)
    for cube in game.cubes:
        cube.t_left -= dt
        near = [e for e in game.enemies if e.alive and e.cube_immune <= 0 and e.distance < cube.dist
                and cube.dist - e.distance < 600]
        near.sort(key=lambda e: -e.distance)
        stop = cube.dist - 14
        cube.attackers = []
        for e in near:
            allowed = stop - e.radius
            if e.distance + e.speed * dt >= allowed:
                e.distance = min(e.distance, allowed)
                e.pos = game.path.position_at(e.distance)
                e.blocked = True
                stop = allowed - e.radius - 4
                if len(cube.attackers) < cfg["attackers"]:
                    cube.attackers.append(e)
        D = cube.tower.stats["damage"]
        for e in cube.attackers:
            cube.hp -= max(1.0, e.stash_damage * 2.0) * dt * (cfg["boss_dps_mult"] if e.is_boss else 1.0)
            e.thorn_t += dt
            if e.thorn_t >= cfg["thorns_every"]:   # thorns: no shape stacks from this damage
                e.thorn_t = 0.0
                e.take_damage(cfg["thorns_mult_d"] * D)
                game.fx.hit(e, (255, 190, 110), None)
        for e in near:
            if e.blocked:
                e.stall += dt
                if e.stall >= cfg["max_stall"]:   # never stall one enemy forever
                    e.stall, e.cube_immune = 0.0, cfg["max_stall"]
    gone = [c for c in game.cubes if c.hp <= 0 or c.t_left <= 0]
    for c in gone:
        game.fx.cube_broke(c.pos)
    game.cubes = [c for c in game.cubes if c not in gone]
    if not game.cubes:
        for e in game.enemies:
            e.blocked = False


def _update_zones(game, dt: float) -> None:
    cfg = ABILITIES["sphere_active"]
    for z in game.zones:
        z["t"] -= dt
        for e in game.enemies:
            e.trap_immune = max(0.0, e.trap_immune - dt) if z is game.zones[0] else e.trap_immune
            if not e.alive or e.trap_immune > 0 or z["n"] >= cfg["max_trapped"]:
                continue
            if e.pos.distance_to(z["pos"]) <= z["r"] + e.radius:
                z["n"] += 1
                if e.is_boss:
                    e.stun_timer = max(e.stun_timer, cfg["trap_boss"])
                    e.trap_immune = cfg["immune_boss"]
                    e.bubble = cfg["trap_boss"]
                else:
                    e.stun(cfg["trap"])
                    e.trap_immune = cfg["trap"] + cfg["immune"]
                    e.bubble = cfg["trap"]
                game.fx.trapped(e)
    game.zones = [z for z in game.zones if z["t"] > 0]


# ------------------------------------------------------------------ draw
_AXIS_CACHE: dict = {}


def axis_surface(origin: Vec, size, level: int) -> pygame.Surface:
    """Cartesian grid centred on Bima, baked once per (origin, level) and reused every frame."""
    key = (round(origin.x), round(origin.y), size, level)
    if key not in _AXIS_CACHE:
        if len(_AXIS_CACHE) > 8:
            _AXIS_CACHE.clear()
        surf = gfx.blank(*size)
        ox, oy = origin.x, origin.y
        rng = GRAPH["range_units"][level]
        x0, x1 = int(ox - rng * UNIT), int(ox + rng * UNIT)
        y0, y1 = int(oy - 10 * UNIT), int(oy + 10 * UNIT)
        for i in range(-int(rng), int(rng) + 1):
            x = ox + i * UNIT
            major = i % 5 == 0
            pygame.draw.line(surf, (255, 255, 255, 70 if major else 26), (x, max(0, y0)), (x, min(size[1], y1)), 2 if i == 0 else 1)
        for j in range(-10, 11):
            y = oy - j * UNIT
            pygame.draw.line(surf, (255, 255, 255, 70 if j % 5 == 0 else 26), (max(0, x0), y), (min(size[0], x1), y), 2 if j == 0 else 1)
        pygame.draw.line(surf, (255, 255, 255, 190), (max(0, x0), oy), (min(size[0], x1), oy), 2)
        pygame.draw.line(surf, (255, 255, 255, 190), (ox, max(0, y0)), (ox, min(size[1], y1)), 2)
        for i in range(-int(rng) // 5 * 5, int(rng) + 1, 5):
            if i:
                img = gfx.blank(1, 1)
                lab = sprites_proc  # noqa: F841 (keep import used)
                from game.utils import outlined_text
                t = outlined_text(str(i), 15, (255, 255, 255), (30, 20, 40), 1, False)
                surf.blit(t, t.get_rect(midtop=(ox + i * UNIT, oy + 4)))
        for j in (-10, -5, 5, 10):
            from game.utils import outlined_text
            t = outlined_text(str(j), 15, (255, 255, 255), (30, 20, 40), 1, False)
            surf.blit(t, t.get_rect(midright=(ox - 5, oy - j * UNIT)))
        _AXIS_CACHE[key] = surf
    return _AXIS_CACHE[key]


def draw_preview(surface: pygame.Surface, t) -> None:
    """Axis + live curve preview (dashed) for a selected Graph-path Bima."""
    gt = graph_tier(t)
    if gt < 2:
        return
    surface.blit(axis_surface(t.pos, surface.get_size(), gt), (0, 0))
    pv = update_preview(t)
    if not pv or "error" in pv:
        return
    pts = pv["pts"]
    for i in range(0, len(pts) - 1, 6):  # dashes
        seg = pts[i:i + 4]
        if len(seg) > 1:
            pygame.draw.lines(surface, (255, 200, 120), False, seg, 3)
    end = pts[-1]
    pygame.draw.circle(surface, (255, 255, 255), (int(end[0]), int(end[1])), 5, 2)
    draw_outlined(surface, f"{pv['cost']}", (end[0], end[1] - 16), 18, (130, 215, 255), center=True, width=1)


def draw_world(surface: pygame.Surface, game) -> None:
    """Curve shots, cubes, zones, shield dome."""
    for s in game.shots:
        s.draw(surface, SHOT_COLOR)
    for z in game.zones:
        a = min(1.0, z["t"] / 0.6)
        g = gfx.glow(int(z["r"] * 1.15), (110, 215, 255), int(120 * a))
        surface.blit(g, g.get_rect(center=(int(z["pos"].x), int(z["pos"].y))))
        pygame.draw.circle(surface, (150, 230, 255), (int(z["pos"].x), int(z["pos"].y)), int(z["r"]), 2)
        ph = pygame.time.get_ticks() / 400
        for k in range(6):
            a2 = ph + k * 1.047
            pygame.draw.circle(surface, (200, 240, 255), (int(z["pos"].x + math.cos(a2) * z["r"] * 0.8), int(z["pos"].y + math.sin(a2) * z["r"] * 0.8)), 3)
    for c in game.cubes:
        spr = sprites_proc.shape_sprite(0, True, 52)
        x, y = int(c.pos.x), int(c.pos.y)
        gfx.blit_shadow(surface, (x + 8, y + 18), 50, 18, 110)
        surface.blit(spr, spr.get_rect(center=(x, y - 6)))
        w = 44
        bar = pygame.Rect(0, 0, w, 6)
        bar.midbottom = (x, y - 36)
        gfx.hp_bar(surface, bar, c.hp / c.max_hp, None, gold=True)
        draw_outlined(surface, f"{max(0, c.t_left):.0f}s", (x, y + 22), 16, (255, 220, 150), center=True, width=1)
    if game.shield > 0:
        from data.map import STASH_POS
        a = min(1.0, game.shield_t / 1.0)
        r = 62 + 3 * math.sin(pygame.time.get_ticks() / 200)
        g = gfx.glow(int(r * 1.2), (110, 215, 255), int(110 * a))
        surface.blit(g, g.get_rect(center=STASH_POS))
        pygame.draw.circle(surface, (160, 235, 255), STASH_POS, int(r), 3)
        draw_outlined(surface, f"{int(game.shield)}", (STASH_POS[0], STASH_POS[1] - r - 10), 20, (160, 235, 255), center=True, width=2)
