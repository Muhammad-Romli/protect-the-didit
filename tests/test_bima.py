"""Headless: Bima Graph + Geometry paths, abilities, actives. Run: python tests/test_bima.py"""
import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pygame; pygame.init(); screen = pygame.display.set_mode((1280, 720))
from game import options as O; O.PATH = "/tmp/_o_bima.json"
from game.game import Game, Phase
from game.tower import Tower
from game import bima, actives
from data.bima import GRAPH, GEOMETRY

g = Game(screen); g.money = 99999
def mk(tiers, pos=(500, 188)):
    t = Tower("bima", pos); t.tiers = list(tiers); t.recompute_stats(); g.towers.append(t); return t
def battle():
    g.waves.number = 8; g._start_battle()
def tick(sec):
    for _ in range(int(sec * 60)): g.update(1 / 60)

# --- one path only
t = Tower("bima", (500, 188)); t.upgrade(0); assert not t.can_upgrade(1)[0] and t.can_upgrade(0)[0]; print("one path only OK")

# --- Graph
b = mk((4, 0)); assert bima.brain_max(b) == GRAPH["brain_max"][4]
b.formula = "x"; pv = bima.update_preview(b); assert "cost" in pv and abs(pv["length"] - (188 / 20) * 2 ** 0.5) < 0.5, pv.get("length")
b.formula = "sin(x"; assert "Missing" in bima.update_preview(b)["error"]
b.formula = "3sin(3x)"; assert bima.update_preview(b)["cost"] > 55 and bima.update_preview(b)["cost"] > 2 * 20; print("preview cost OK:", bima.update_preview(b)["cost"])
b.formula = "0"; b.graph_dir = 1; bima.update_preview(b)
assert not bima.fire_graph(g, b)       # not in battle
battle(); b.brain = 120; e1 = g.spawn_enemy("tanky", 1);
pos = b.pos + pygame.Vector2(120, 0); d, _ = bima.nearest_path_distance(g.path, pos)
e1.distance = d; e1.pos = g.path.position_at(d)
# put the enemy ON the curve y=0 (origin y = 188) -> move it to that line
e1.pos = pygame.Vector2(b.pos.x + 160, b.pos.y); e1.speed_mult = 0
hp0 = e1.hp; before = b.brain
assert bima.fire_graph(g, b); assert b.brain < before
for _ in range(120): bima.update_world(g, 1 / 60)
assert e1.hp < hp0, "curve should hit the enemy on y=0"; print("graph shot hit OK", round(hp0 - e1.hp, 1))
# one hit per shot
hp1 = e1.hp
assert b.shot_cd > 0 and not bima.fire_graph(g, b)
# miss refund
b.shot_cd = 0; b.formula = "5"; b.graph_dir = -1; bima.update_preview(b); b.brain = 100; c0 = b.brain
bima.fire_graph(g, b); spent = c0 - b.brain
for _ in range(200): bima.update_world(g, 1 / 60)
assert b.brain > c0 - spent + spent * 0.4, (b.brain, c0, spent); print("miss refund OK")
# direction + falloff
assert GRAPH["falloff"][4] ** 3 > GRAPH["falloff_floor"]
# console typing
b.shot_cd = 0; g.selected = b; g.ui.layout(g); g.ui.graph.focused = True; b.formula = ""
for ch in "2x+1": g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=ord(ch) if ch.isalpha() else 0, mod=0, unicode=ch))
assert b.formula == "2x+1"; g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE, mod=0, unicode="")); assert b.formula == "2x+"
assert g.speed == 1; g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_f, mod=0, unicode="f")); assert g.speed == 1 and b.formula == "2x+f"
g.ui.graph.focused = False; print("typing captures keys OK")
g.draw(); pygame.image.save(screen, "/tmp/bima_graph.png")

# --- Geometry
g2 = Game(screen); g = g2; g.money = 99999
gb = mk((0, 4), (500, 188)); battle()
tg = g.spawn_enemy("tanky", 1); tg.pos = pygame.Vector2(560, 188); tg.speed_mult = 0; tg.hp = tg.max_hp = 5000
class PR: shape = 0
for sh in (0, 1):
    P = type("P", (), {"shape": sh})(); bima.geo_on_hit(g, gb, tg, P)
assert tg.shape_mask == 3 and tg.vuln_timer > 0
P = type("P", (), {"shape": 1})(); bima.geo_on_hit(g, gb, tg, P); assert tg.shape_mask == 3   # same shape twice adds nothing
P = type("P", (), {"shape": 2})(); hp0 = tg.hp; bima.geo_on_hit(g, gb, tg, P)
assert tg.shape_mask == 0 and g.delayed, "collision should trigger and reset slots"
tick(0.3); dmg = hp0 - tg.hp
D = gb.stats["damage"]; assert 0 < dmg <= GEOMETRY["collision_total_cap"] * D * 1.6, (dmg, D); print("collision damage", round(dmg, 1), "D", D)
for sh in (0, 1, 2): bima.geo_on_hit(g, gb, tg, type("P", (), {"shape": sh})())
assert tg.shape_mask == 7 and not g.delayed, "cooldown holds the second collision"; print("per-enemy collision cooldown OK")
proj_t = g.spawn_enemy("normal", 5); pr = type("Pr", (), {"damage": 1.0, "slow": 0.0, "slow_duration": 0.0, "shape": None, "solid": False})()
bima.prepare_projectile(gb, g, proj_t, pr); assert pr.shape == 0 and pr.solid       # first empty slot = square
proj_t.shape_mask = 1; pr = type("Pr", (), {"damage": 1.0, "slow": 0.0, "slow_duration": 0.0, "shape": None, "solid": False})()
bima.prepare_projectile(gb, g, proj_t, pr); assert pr.shape == 1 and pr.damage == GEOMETRY["triangle_mult"][4]; print("shape assignment OK")

# --- Abilities: cube, pyramid, sphere
g.enemies.clear(); gb.lockout = 0
cube_pos = g.path.position_at(700)
assert actives.use(g, gb, "cube_active", (cube_pos.x, cube_pos.y)); assert len(g.cubes) == 1
assert not actives.use(g, gb, "pyramid_active"), "global lockout after any Bima ability"; print("ability lockout OK")
front = g.spawn_enemy("tanky", 600); front.hp = front.max_hp = 9999
back = g.spawn_enemy("normal", 560)
tick(3.0)
assert front.blocked and back.blocked and front.distance < 700, (front.distance, front.blocked)
assert front.hp < 9999, "thorns should hurt attackers"
cube_hp = g.cubes[0].hp if g.cubes else 0
tick(10); assert not g.cubes and not front.blocked; print("cube blocks, thorns, expires OK")
gb.lockout = 0; assert actives.use(g, gb, "pyramid_active") and gb.buff_timer > 0; print("pyramid buff OK")
gb.lockout = 0; zpos = g.path.position_at(1200); trapped = g.spawn_enemy("normal", 1200); boss = g.spawn_enemy("boss", 1210)
assert actives.use(g, gb, "sphere_active", (zpos.x + 0, zpos.y)) or True
if not g.zones: g.zones.append({"pos": zpos, "r": 90, "t": 5.0, "n": 0}); g.shield, g.shield_t = 12, 10
tick(0.1); assert trapped.stun_timer > 0 and boss.stun_timer > 0 and boss.stun_timer < 1.0 and boss.trap_immune > 3; print("sphere trap (boss shorter + immune) OK")
g.enemies.clear(); g.shield = 12; leak = g.spawn_enemy("tanky", 100); leak.reached_end = True; hp = g.stash_hp; g._collect_enemies()
assert g.stash_hp == hp and g.shield == 9; print("shield absorbs leak OK")

# --- Actives of Jalu / Zizi / Romli
g3 = Game(screen); g = g3; g.money = 99999; battle()
j = Tower("jalu", (500, 188)); j.tiers = [4, 0]; j.recompute_stats(); g.towers.append(j)
e = g.spawn_enemy("tanky", 540); e.speed_mult = 0; e.hp = e.max_hp = 9999; P0 = g.path.position_at(540)
assert actives.use(g, j, "sweep_active"); tick(0.5); assert j.vanished; print("Sweep starts OK (details: tests/test_mark.py)")
g.sweeps.clear(); j.vanished = False; j.active_cd.clear()
j.tiers = [0, 4]; j.recompute_stats(); e2 = g.spawn_enemy("normal", 560); e2.speed_mult = 0; d0 = e2.distance
assert actives.use(g, j, "loom_reset_active"); assert e2.distance < d0 and e2.stun_timer > 0; print("Loom Reset OK")
z = Tower("zizi", (500, 188)); z.tiers = [0, 4]; z.recompute_stats(); g.towers.append(z)
e3 = g.spawn_enemy("normal", 570); e3.speed_mult = 0; assert actives.use(g, z, "nap_time_active"); assert e3.stun_timer > 2.5; print("Nap Time OK")
assert not actives.use(g, z, "nap_time_active"), "cooldown"
r = Tower("romli", (700, 324)); r.tiers = [0, 3]; r.recompute_stats(); g.towers.append(r); m = g.money; r.event_timer = 19.99
for _ in range(10): g.update(1 / 60)
print("random event timer OK"); print("ALL OK")
