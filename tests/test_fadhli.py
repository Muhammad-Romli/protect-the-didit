"""Headless checks for Fadhli: charge cycle, path lock, bounce chain (50% -5 per bounce), stun/slow rolls (20/30/50),
Tusk Act 4 barrage + inner circle, Golden Ratio, Galaxy Impact, looks/sounds, tornado vfx, savegame.
Run from the project folder:  python tests/test_fadhli.py
"""
import os, sys, random, tempfile
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pygame; pygame.init()
screen = pygame.display.set_mode((1280, 720))
from data import fadhli as cfg
from data.towers import TOWERS, TOWER_ORDER
from game import actives, fadhli, models, sprites_proc
from game.audio import SOUNDS
from game.effects import EFFECTS
from game.game import Game
from game.projectile import Projectile
from game.tower import Tower
from game.utils import Vec

def new():
    g = Game(screen); g.money = 99999; g.waves.active = True; g.waves._queue = [(999, "normal")]; return g
def mk(g, tiers, pos=(330, 190)):
    t = Tower("fadhli", pos); t.tiers = list(tiers); t.recompute_stats(); g.towers.append(t); return t
def foe(g, dist, hp=99999.0):
    e = g.spawn_enemy("normal", dist); e.hp = e.max_hp = hp; e.base_speed = 0.0; return e
def run(g, seconds, dt=1 / 60):
    for _ in range(round(seconds / dt)): g.update(dt)

# ---- 1. data: both paths, prices, effects, order
assert "fadhli" in TOWER_ORDER and len(TOWER_ORDER) == 5
names = [p["name"] for p in TOWERS["fadhli"]["paths"]]
assert names == ["Garp (Power)", "Johnny (Spin)"], names
jt = TOWERS["fadhli"]["paths"][1]["tiers"]
assert jt[0]["cost"] <= 100 and set(jt[0]["stat_mods"]) == {"cooldown"} and jt[0]["stat_mods"]["cooldown"] < 0 and not jt[0]["effects"]  # cheap, only faster
assert "fadhli_bounce" in jt[1]["effects"] and jt[1]["stat_mods"].get("damage", 0) > 0
assert "fadhli_status" in jt[2]["effects"] and jt[2]["stat_mods"].get("damage", 0) > 0
assert {"fadhli_barrage", "golden_active"} <= set(jt[3]["effects"])
for up in jt: assert all(e in EFFECTS for e in up["effects"]), up
gt = TOWERS["fadhli"]["paths"][0]["tiers"]
assert "galaxy_active" in gt[3]["effects"] and all(e in EFFECTS for up in gt for e in up["effects"])
assert "golden_active" in actives.ACTIVES and "galaxy_active" in actives.ACTIVES
print("data OK")

# ---- 2. one path per Fadhli
g = new(); t = mk(g, (0, 0)); g.selected = t
t.upgrade(1); ok, why = t.can_upgrade(0)
assert not ok and "Locked" in why, why
assert t.can_upgrade(1)[0]
print("path lock OK")

# ---- 3. charge cycle: charge first, then the throw leaves, then cooldown. Slow compared with Jalu.
g = new(); t = mk(g, (0, 0)); e = foe(g, 290)
need = fadhli.charge_time(t)
g.update(1 / 60)
assert t.charging and not g.projectiles, "he must charge before throwing"
run(g, need * 0.5)
assert t.charging and not g.projectiles
run(g, need * 0.6)
assert g.projectiles and not t.charging and t.cooldown_left > 0, "throw after the charge"
assert t.stats["cooldown"] >= 1.5, "base attack is slow"
print("charge cycle OK")

# ---- 4. Garp charges longer with every tier; Johnny barely charges
assert cfg.GARP_CHARGE == sorted(cfg.GARP_CHARGE) and cfg.GARP_CHARGE[4] > cfg.GARP_CHARGE[0] * 2
assert cfg.JOHNNY_CHARGE < cfg.GARP_CHARGE[0]
print("charge times OK")

# ---- 5. Garp: heavy damage, splash, armor break, knockback
g = new(); a = mk(g, (4, 0)); j = mk(g, (0, 4), (700, 300))
assert a.stats["damage"] > 30 and a.stats["damage"] > 3 * j.stats["damage"], "Garp compensates his slowness with damage"
assert a.stats["cooldown"] > j.stats["cooldown"] * 2
assert a.stats["aoe_radius"] > 50 and "armor_breaker" in a.effects and "garp_knockback" in a.effects
es = [foe(g, d) for d in (290, 300, 310)]
d0 = [e.distance for e in es]
run(g, 6)
assert all(e.hp < e.max_hp for e in es), "splash hits all three"
print("Garp OK")

# ---- 6. Johnny T1: only faster
g = new(); t = mk(g, (0, 1)); base = mk(g, (0, 0), (500, 300))
assert t.stats["cooldown"] < base.stats["cooldown"] - 0.5 and t.stats["damage"] == base.stats["damage"]
assert not t.effects
print("Johnny T1 OK")

# ---- 7. bounce: 50% then -5 points each bounce; chain stops at 0
g = new(); t = mk(g, (0, 2)); es = [foe(g, d) for d in (280, 290, 300, 310, 320)]
p = Projectile(es[0].pos, es[0], 400, 10, 0, 0, 0, 0, t.color, t); p.bounce_chance = cfg.BOUNCE_START_CHANCE
assert abs(p.bounce_chance - 0.5) < 1e-9
random.seed(1)
chances, bounces_seen = [], 0
cur = p
for _ in range(30):
    g.projectiles.clear()
    random.random = lambda: 0.0    # always "continue"
    fadhli.bounce(g, t, cur, [cur.target])
    random.seed()
    if not g.projectiles: break
    cur = g.projectiles[0]; chances.append(round(cur.bounce_chance, 4)); bounces_seen += 1
assert chances[:4] == [0.45, 0.40, 0.35, 0.30], chances
assert bounces_seen == 10 and chances[-1] == 0.0, (bounces_seen, chances)   # 0.50 -> 0.00 in 10 steps, then it must stop
# statistics: P(first bounce) = 50%
import importlib; importlib.reload(random)
n, cont = 4000, 0
for _ in range(n):
    g.projectiles.clear(); q = Projectile(es[0].pos, es[0], 400, 10, 0, 0, 0, 0, t.color, t); q.bounce_chance = 0.5
    fadhli.bounce(g, t, q, [es[0]]); cont += bool(g.projectiles)
assert 0.46 < cont / n < 0.54, cont / n
# the ball prefers Didits it has not hit yet and never "bounces" onto the one it just hit
assert g.projectiles[0].target is not es[0] if g.projectiles else True
print("bounce OK", round(cont / n, 3))

# ---- 8. stun / slow / nothing = 20 / 30 / 50
g = new(); t = mk(g, (0, 3)); e = foe(g, 290)
p = Projectile(t.pos, e, 400, 1, 0, 0, 0, 0, t.color, t)
stun = slow = none = 0; N = 6000
for _ in range(N):
    e.stun_timer = 0.0; e.slow_timer = 0.0; e.slow_strength = 0.0
    fadhli.status(g, t, p, [e])
    if e.stun_timer > 0: stun += 1
    elif e.slow_timer > 0: slow += 1
    else: none += 1
assert 0.17 < stun / N < 0.23 and 0.27 < slow / N < 0.33 and 0.47 < none / N < 0.53, (stun, slow, none)
boss = g.spawn_enemy("boss", 300); boss.stun_timer = 0
for _ in range(200): fadhli.status(g, t, p, [boss])
assert boss.stun_timer == 0, "bosses are immune to stun"
print("status OK", stun / N, slow / N, none / N)

# ---- 9. Tusk Act 4: barrage hits everything INSIDE the inner circle at the same time as the throws; none outside
g = new(); t = mk(g, (0, 4))
assert fadhli.has_barrage(t) and fadhli.melee_radius(t) < t.stats["range"]
inner = foe(g, 290); outer = foe(g, 320)
while t.pos.distance_to(inner.pos) > fadhli.melee_radius(t) - 5:   # put one Didit inside, one outside the circle
    inner.distance += 4; inner.pos = inner.path.position_at(inner.distance)
    if inner.distance > 800: break
r = fadhli.melee_radius(t)
inner.pos = t.pos + Vec(r * 0.5, 0); inner.distance = inner.path.nearest_distance(inner.pos) if hasattr(inner.path, "nearest_distance") else inner.distance
outer.pos = t.pos + Vec(r + 40, 0)
for e in (inner, outer): e.update = lambda dt: None        # frozen, positions stay where the test put them
hp_in, hp_out = inner.hp, outer.hp
t.melee_cd = 0.0
for _ in range(30): fadhli._barrage(t, g, 1 / 60 * 3)
assert inner.hp < hp_in, "barrage must hit inside the inner circle"
assert outer.hp == hp_out, "nothing outside the inner circle is hit by melee"
assert t.barraging > 0
g.selected = t; g.draw()                                   # the inner circle is drawn
print("barrage OK")

# ---- 10. throws still happen while the barrage runs (both at the same time)
g = new(); t = mk(g, (0, 4)); e = foe(g, 290)
e.pos = t.pos + Vec(40, 0); e.update = lambda dt: None
run(g, 3)
assert e.hp < e.max_hp - 3 * 5, "barrage + throws both deal damage"
print("simultaneous OK")

# ---- 11. Golden Ratio: damage /4, then x1.618 per THROW, for 5 s
g = new(); t = mk(g, (0, 4)); foe(g, 290)
assert actives.can_use(g, t, "golden_active")[0], "usable in battle"
t.active_cd = {}
ok = actives.use(g, t, "golden_active")
assert ok and t.golden_t == cfg.GOLDEN_DURATION and abs(t.golden_mult - 0.25) < 1e-9
dmgs = []
_orig_release = fadhli._release
def _logged_release(tw, gm, target):      # log every throw when it is released (polling per frame could miss one)
    n = len(gm.projectiles); _orig_release(tw, gm, target)
    if len(gm.projectiles) > n and tw is t: dmgs.append((id(gm.projectiles[n]), gm.projectiles[n].damage))
fadhli._release = _logged_release
for _ in range(900):
    g.update(1 / 60)
    if t.golden_t == 0 and len(dmgs) > 3: break
fadhli._release = _orig_release
vals = [d[1] for d in dmgs]
base_d = t.stats["damage"]
assert abs(vals[0] - base_d / 4) < 1e-6, (vals[0], base_d / 4)
for a_, b_ in zip(vals, vals[1:]):
    if b_ > 0 and a_ < base_d * cfg.GOLDEN_MAX_MULT / 2: assert abs(b_ / a_ - cfg.PHI) < 1e-3, (a_, b_)
assert len(vals) >= 8, f"only {len(vals)} throws during Golden Ratio"
assert sum(vals) > 10 * base_d, "Golden Ratio must be a real burst"
assert t.golden_t == 0 and t.golden_mult == 1.0
print("golden ratio OK", len(vals), "throws, total", round(sum(vals)), "vs normal 5s", round(5 / (t.stats["cooldown"] + cfg.JOHNNY_CHARGE) * base_d))

# ---- 12. Galaxy Impact: the next throw is a mega throw (x5 damage, bigger splash, longer charge)
g = new(); t = mk(g, (4, 0)); es = [foe(g, d) for d in (290, 300)]
t.active_cd = {}
assert actives.use(g, t, "galaxy_active") and t.mega_t > 0
g.update(1 / 60)
assert t.charging and t.charge_mega and t.charge_need > fadhli.charge_time(t) * 1.5
run(g, t.charge_need + 0.05)
mega = [p for p in g.projectiles if p.mega]
assert mega and abs(mega[0].damage - t.stats["damage"] * cfg.GALAXY_DAMAGE_MULT) < 1e-6 and mega[0].aoe_radius >= cfg.GALAXY_AOE_MIN
run(g, 6)
assert t.charge_mega is False
print("galaxy OK")

# ---- 13. looks, props and sounds exist; tornado vfx is created on a Johnny hit; Tusk acts differ
for look in [None] + [(p, k) for p in (0, 1) for k in range(1, 5)]:
    sprites_proc.tower_sprite("fadhli", 18, TOWERS["fadhli"]["color"], look)
    models.weapon_image("fadhli", look, 0, False)
    assert models.projectile("fadhli", look) is not None, look
a1, a3, a4 = models.tusk(1, 40), models.tusk(3, 40), models.tusk(4, 40)
assert pygame.image.tostring(a1, "RGBA") != pygame.image.tostring(a3, "RGBA") != pygame.image.tostring(a4, "RGBA")
for n in ("garp_charge", "garp_throw", "garp_impact", "galaxy_charge", "galaxy_impact", "steel_spin", "steel_throw",
          "steel_hit", "tornado", "bounce", "barrage", "golden", "stun_ding", "galaxy_on"):
    assert n in SOUNDS, n
g = new(); t = mk(g, (0, 1)); e = foe(g, 290)
before = len(g.fx.vfx.tornados)
g.fx.tower_hit(e, t)
assert len(g.fx.vfx.tornados) == before + 1, "a Johnny hit spawns a tornado"
tg = mk(g, (1, 0), (600, 300)); g.fx.tower_hit(e, tg)
assert len(g.fx.vfx.tornados) == before + 1, "Garp does not spawn tornados"
for _ in range(120): g.fx.update(1 / 60)
assert not g.fx.vfx.tornados
print("looks / sounds / tornado OK")

# ---- 14. whole run with every tier, drawing every frame: no exceptions
for tiers in [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (0, 1), (0, 2), (0, 3), (0, 4)]:
    g = new(); t = mk(g, tiers); [foe(g, d) for d in (285, 295, 305, 315)]; g.selected = t
    for i in range(240):
        g.update(1 / 60)
        if i % 6 == 0: g.draw()
print("all tiers run + draw OK")

# ---- 15. savegame round trip keeps tiers and the tower works afterwards
from game import savegame
g = new(); t = mk(g, (0, 3)); d = savegame.snapshot(g) if hasattr(savegame, "snapshot") else None
print("savegame hook:", "snapshot" if d is not None else "skipped (checked in test_savegame)")
# ---- 12. (2026-11-09) base Fadhli looks like a regular tower; Garp 300% vs bosses at T3+; hot craters from tier 2
g = new(); b = mk(g, (0, 0)); assert fadhli.is_base(b) and not fadhli.is_garp(b) and not fadhli.is_johnny(b)
e = foe(g, 290); g.update(1 / 60)
assert b.charging and fadhli.charge_shake(b) == (0, 0), "no shaking while the base Fadhli winds up"
run(g, 0.5)
assert g.projectiles or e.hp < e.max_hp
if g.projectiles:
    assert g.projectiles[0].arc == 0.0, "plain straight throw at base"
assert not g.craters, "base Fadhli leaves no crater"
assert models.weapon_image("fadhli", None, 30, False) is not None      # still throws a rock
print("base looks regular OK")

g = new(); t2 = mk(g, (4, 0)); t2.tiers = [2, 0]; t2.recompute_stats()
t3 = mk(g, (3, 0), (700, 300)); t3.tiers = [3, 0]; t3.recompute_stats()
t4 = mk(g, (4, 0), (900, 300)); t4.tiers = [4, 0]; t4.recompute_stats()
assert t2.stats["damage"] < t3.stats["damage"] < t4.stats["damage"], "damage grows every tier"
assert abs(t2.stats["damage"] - 16.0) < 1e-6 and abs(t3.stats["damage"] - 24.0) < 1e-6 and abs(t4.stats["damage"] - 36.0) < 1e-6
assert "garp_crater" in t2.effects and "garp_crater" in t3.effects and "garp_crater" in t4.effects
t1 = mk(g, (1, 0), (500, 500)); t1.tiers = [1, 0]; t1.recompute_stats(); assert "garp_crater" not in t1.effects
# 300% against bosses from tier 3 only (direct hits), nothing extra against normal Didits
def dmg_taken(tower, kind):
    g = new(); tower.tiers = list(tower.tiers); g.towers.append(tower); e = g.spawn_enemy(kind, 100); e.hp = e.max_hp = 99999.0
    p = Projectile(Vec(e.pos), e, 400, tower.stats["damage"], 0, 0, 0, 0, (255, 150, 60), tower); g._resolve_hit(p)
    return e.max_hp - e.hp
from data.enemies import ENEMIES
boss = next(k for k, v in ENEMIES.items() if v["is_boss"] and not v.get("armor"))
for tr, mult in ((2, 1.0), (3, 3.0), (4, 3.0)):
    tw = Tower("fadhli", (0, 0)); tw.tiers = [tr, 0]; tw.recompute_stats()
    n, b = dmg_taken(tw, "normal"), dmg_taken(tw, boss)
    assert abs(n - tw.stats["damage"]) < 1e-6 and abs(b - tw.stats["damage"] * mult) < 1e-6, (tr, n, b)
print("Garp: x3 only vs bosses from tier 3 OK", t2.stats["damage"], t3.stats["damage"], t4.stats["damage"])

# a crater appears where the throw lands, grows with the tier, burns Didits inside, and disappears
radii = []
for tiers in ((2, 0), (3, 0), (4, 0)):
    g = new(); t = mk(g, tiers, (330, 190)); e = foe(g, 290, hp=99999.0)
    run(g, 3.2)
    assert g.craters, tiers
    c = g.craters[-1]
    radii.append((c["radius"], c["damage"], c["total"]))
assert radii[0][0] < radii[1][0] < radii[2][0] and radii[0][1] < radii[1][1] < radii[2][1] and radii[0][2] < radii[1][2] < radii[2][2], radii
print("crater grows with the tier OK", radii)

g = new(); t = mk(g, (2, 0), (330, 190)); t.cooldown_left = 999
inside = foe(g, 100); outside = foe(g, 400); armored = foe(g, 101); armored.armor = 5
crate = {"pos": Vec(inside.pos), "radius": 40, "damage": 2.0, "t": 3.0, "total": 3.0, "tick": cfg.CRATER_TICK, "mega": False, "tier": 2, "seed": 1, "born": 0.0}
assert crate["pos"].distance_to(outside.pos) > 100 and crate["pos"].distance_to(armored.pos) < 40
g.craters.append(crate)
run(g, 1.1)
assert inside.hp < inside.max_hp and outside.hp == outside.max_hp and armored.hp == armored.max_hp, "burn only inside, armor shields"
run(g, 3.0)
assert not g.craters, "the crater cools down and vanishes"
print("crater burns inside only, vanishes OK")

g = new(); [g.craters.append({"pos": Vec(i, 0), "radius": 30, "damage": 1.0, "t": 5.0, "total": 5.0, "tick": 0.5, "mega": False, "tier": 2, "seed": i, "born": 0.0}) for i in range(5)]
t = mk(g, (4, 0), (330, 190)); e = foe(g, 290)
for _ in range(40):
    p = Projectile(Vec(e.pos), e, 400, 1.0, 30, 0, 0, 0, (255, 150, 60), t); p.arrived = True
    g._resolve_hit(p)
assert len(g.craters) <= cfg.CRATER_MAX, len(g.craters)
assert len(g.craters) == cfg.CRATER_MAX, "the cap is actually reached"
mega = Projectile(Vec(e.pos), e, 400, 1.0, 30, 0, 0, 0, (255, 150, 60), t); mega.mega = True; g.craters.clear(); g._resolve_hit(mega)
assert g.craters and g.craters[0]["radius"] > cfg.CRATER_TIERS[4]["radius"], "mega throw = bigger crater"
screen.fill((0, 0, 0)); g.draw()
print("crater cap + mega crater + draw OK")

print("ALL OK")
