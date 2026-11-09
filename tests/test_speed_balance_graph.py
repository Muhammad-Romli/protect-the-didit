"""Headless: x2/x3 speed does not speed up preparation by default; Romli / Bima balance; Bima Graph hits and VFX.
Run: python tests/test_speed_balance_graph.py"""
import os, sys, random
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pygame; pygame.init(); screen = pygame.display.set_mode((1280, 720))
from game import options as O; O.PATH = "/tmp/_o_speed.json"
if os.path.exists(O.PATH): os.remove(O.PATH)
from game.game import Game, Phase, State
from game import bima, curves
from data.bima import GRAPH, GEOMETRY
from data.towers import TOWERS
from data.settings import SPEED_STEPS

# ---- speed: prep stays x1 by default, battles run x3; option turns prep speed on
g = Game(screen); assert g.options["prep_speed"] is False
g.money = 5000; g.placing = "jalu"; g._try_place((300, 188)); j = g.towers[0]
g.selected = j; g.ui.layout(g)
g.speed = 3
t0, p0 = g.time, g.prep_time
for _ in range(60): g.update(1 / 60)
assert abs((g.time - t0) - 1.0) < 0.05 and abs((g.prep_time - p0) - 1.0) < 0.05, (g.time - t0, g.prep_time - p0)
# preparation activities (Jalu's larping) also run at x1
g.towers[0].activity = None
from data.activities import ACTIVITIES
act = next(a for a, d in ACTIVITIES.items() if a == "larp" or "larp" in a) if any("larp" in a for a in ACTIVITIES) else None
if act:
    g._toggle_activity(act); a0 = g.towers[0].activity_time
    for _ in range(60): g.update(1 / 60)
    assert abs(g.towers[0].activity_time - a0 - 1.0) < 0.06, g.towers[0].activity_time - a0
    g.towers[0].stop_activity()
g.options["prep_speed"] = True
t0, p0 = g.time, g.prep_time
for _ in range(60): g.update(1 / 60)
assert abs((g.prep_time - p0) - 3.0) < 0.1, g.prep_time - p0
g.options["prep_speed"] = False
g._start_battle(); assert g.phase == Phase.BATTLE
t0 = g.time
for _ in range(60): g.update(1 / 60)
assert abs((g.time - t0) - 3.0) < 0.1, g.time - t0   # battle: x3 as before
print("speed only in battle OK")

# ---- Romli: payback of every business upgrade (waves, 75 s per wave cycle) is reasonable and better than before
CYCLE = 75
r = TOWERS["romli"]
inc, per_s, cost = r["stats"]["income_per_wave"], 0.0, r["cost"]
pays = [inc / cost]
for up in r["paths"][0]["tiers"]:
    d_inc, d_s = up["stat_mods"].get("income_per_wave", 0), up["stat_mods"].get("income_per_sec", 0)
    pays.append((d_inc + d_s * CYCLE) / up["cost"])
    inc += d_inc; per_s += d_s
assert all(p >= 0.13 for p in pays), pays                       # every purchase pays itself back within ~8 waves
assert inc >= 600 and per_s >= 4.5                              # Empire: a real late-game economy
prog = r["paths"][1]["tiers"]; dmg = r["stats"]["damage"]; cd = r["stats"]["cooldown"]
for up in prog: dmg += up["stat_mods"].get("damage", 0); cd += up["stat_mods"].get("cooldown", 0)
assert dmg / cd >= 8, dmg / cd                                   # Programmer t4: at least ~8 dps (was 6.1)
print("romli balance OK: payback (waves)", [round(1 / p, 1) for p in pays], "programmer dps", round(dmg / cd, 1))

# ---- Bima Graph: a full curve is a big hit
def graph_stats(t):
    b = TOWERS["bima"]; D = b["stats"]["damage"]
    for up in b["paths"][0]["tiers"][:t]: D += up["stat_mods"].get("damage", 0)
    return D
for t, min_total in ((2, 50), (3, 120), (4, 280)):
    D = graph_stats(t); tot, m = 0, 1
    for _ in range(GRAPH["max_targets"][t]):
        tot += D * GRAPH["dmg_mult"][t] * max(GRAPH["falloff_floor"], m); m *= GRAPH["falloff"][t]
    assert tot >= min_total, (t, tot)
print("graph numbers OK")

# ---- Bima in the game: curve hits, armor breaks fast, VFX are spawned
g = Game(screen); g.money = 9999; g.placing = "bima"; g._try_place((300, 188)); b = g.towers[0]
b.tiers = [4, 0]; bima.init_tower(b); b.formula = "0"; b.graph_dir = 1; bima.update_preview(b, True)
g._start_battle(); g.waves.number = 12
es = []
for i in range(4):
    e = g.spawn_enemy("tanky", 1); e.speed_mult = 0; e.base_speed = 0; e.pos = pygame.Vector2(b.pos.x + 60 + 45 * i, b.pos.y); es.append(e)
ar = g.spawn_enemy("reinforced", 1); ar.base_speed = 0; ar.pos = pygame.Vector2(b.pos.x + 270, b.pos.y)
hp0 = [e.hp for e in es]; armor0 = ar.armor
b.brain = 150; b.shot_cd = 0
particles0 = len(g.fx.vfx.particles)
assert bima.fire_graph(g, b)
labels0 = len(g.fx.vfx.labels)
peak_p = peak_l = peak_r = 0
for _ in range(120):
    bima.update_world(g, 1 / 60); g.fx.update(1 / 60)   # enemies stay where they were put (as in test_bima)
    peak_p, peak_l, peak_r = max(peak_p, len(g.fx.vfx.particles)), max(peak_l, len(g.fx.vfx.labels)), max(peak_r, len(g.fx.vfx.rings))
for e in es: assert e.hp < hp0[es.index(e)] or not e.alive, "curve missed"
assert ar.armor <= armor0 - GRAPH["armor_hits"] or ar.armor == 0, (ar.armor, armor0)
assert peak_p > particles0 + 40 and peak_l >= 4 and peak_r >= 4, (peak_p, peak_l, peak_r)   # sparks, damage numbers + combo text, rings
g.draw()   # curve + vfx draw without errors, also mid-flight
b.brain = 150; b.shot_cd = 0; bima.fire_graph(g, b)
for _ in range(10): bima.update_world(g, 1 / 60); g.fx.update(1 / 60); g.draw()
print("graph hits + vfx OK")
print("ALL OK")
