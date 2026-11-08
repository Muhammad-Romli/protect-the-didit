"""Headless checks for Jalu's Mark path (replaces Thor), the per-unit path lock and the Sweep ability.
Run from the project folder:  python tests/test_mark.py
"""
import os, sys, tempfile
TMP = tempfile.gettempdir()
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pygame; pygame.init()
screen = pygame.display.set_mode((1280, 720))
from data import mark as cfg
from data.towers import TOWERS
from game import actives, mark
from game.effects import EFFECTS
from game.game import Game, Phase
from game.tower import Tower
from game.utils import Vec

def new():
    g = Game(screen); g.money = 99999; g.ball_knowledge = 9999; return g
def battle(g):
    g.waves.active = True; g.waves._queue = [(999, "normal")]   # keeps the wave running, nothing spawns
def mk(g, tiers, pos=(500, 188)):
    t = Tower("jalu", pos); t.tiers = list(tiers); t.recompute_stats(); g.towers.append(t); return t
def foe(g, kind, dist, hp=9999.0):
    e = g.spawn_enemy(kind, dist); e.hp = e.max_hp = hp; e.base_speed = 0.0; return e
def run(g, seconds, dt=1 / 60):
    for _ in range(round(seconds / dt)): g.update(dt)

# ---- 1. Thor is gone, Mark is there
names = [p["name"] for p in TOWERS["jalu"]["paths"]]
assert names[0] == "Mark" and names[1] == "Temporal Loom Guy", names
for gone in ("pierce_1", "chain_lightning", "thunderstrike_active"):
    assert gone not in EFFECTS and gone not in actives.ACTIVES, gone
    assert all(gone not in up["effects"] for p in TOWERS["jalu"]["paths"] for up in p["tiers"])
assert not hasattr(Game, "add_bolt") and not hasattr(Game(screen), "bolts")
assert "speed_against_time" in TOWERS["jalu"]["paths"][1]["tiers"][2]["effects"]   # Loki tier 3 untouched
print("Thor removed, Loki intact OK")

# ---- 2. per-unit lock (Jalu only)
g = new(); a = mk(g, (0, 0), (300, 160)); b = mk(g, (0, 0), (700, 160)); g.selected = a
assert a.can_upgrade(0)[0] and a.can_upgrade(1)[0]
g._try_upgrade(0); assert a.tiers == [1, 0]
ok, why = a.can_upgrade(1); assert not ok and "Locked" in why, why
g._try_upgrade(1); assert a.tiers == [1, 0]; print("lock message:", g.message)
g.selected = b; g._try_upgrade(1); assert b.tiers == [0, 1]       # a second Jalu picks the other path
assert not b.can_upgrade(0)[0] and a.can_upgrade(0)[0]
c = mk(g, (0, 0), (900, 160)); g.selected = c
for _ in range(4): g._try_upgrade(0)
assert c.tiers == [4, 0] and not c.can_upgrade(1)[0]
z = Tower("zizi", (300, 400)); g.towers.append(z); g.selected = z
g._try_upgrade(0); g._try_upgrade(1); assert z.tiers == [1, 1], "other towers keep the BTD6 one-upgrade rule"
g._try_upgrade(1); assert z.tiers == [1, 2] and not z.can_upgrade(0)[0]
g.ui.layout(g); g.selected = a; g.ui.layout(g); g.draw()
print("per-unit lock OK (Jalu), Zizi keeps cross-path OK")

# ---- 3. Mark stats per tier
j = mk(new(), (1, 0)); s = j.stats
assert abs(s["cooldown"] - 0.35) < 1e-9 and s["range"] == 75 and s["aoe_radius"] == cfg.HIT_RADIUS and s["damage"] == 2
j.tiers = [2, 0]; j.recompute_stats(); assert j.stats["damage"] == 2 + cfg.T2_DAMAGE_BONUS
j.tiers = [3, 0]; j.recompute_stats(); assert j.stats["aoe_radius"] == cfg.HIT_RADIUS + cfg.T3_HIT_RADIUS_BONUS
assert mark.is_mark(j) and not mark.is_mark(mk(new(), (0, 3)))
print("tier stats OK")

# ---- 4. punch: splash, knockback (boss reduced), rage
g = new(); battle(g); m = mk(g, (3, 0), (300, 188)); P = g.path
P = g.path
# deterministic splash test through the punch function itself
g = new(); battle(g); m = mk(g, (2, 0), (300, 188))
a = foe(g, "normal", 1500); b = foe(g, "normal", 1510); c2 = foe(g, "normal", 1700)
a.pos = Vec(330, 188); b.pos = Vec(330 + 20, 188); c2.pos = Vec(330 + 300, 188)
da, db, dc = a.distance, b.distance, c2.distance
mark.punch(m, g, a)
assert a.hp == 9999 - m.stats["damage"] and b.hp == 9999 - m.stats["damage"] and c2.hp == 9999
assert abs((da - a.distance) - cfg.KNOCKBACK_DISTANCE) < 1e-6 and abs((db - b.distance) - cfg.KNOCKBACK_DISTANCE) < 1e-6 and c2.distance == dc
print("splash + knockback OK:", round(da - a.distance, 2), "px")
boss = foe(g, "boss", 1500); boss.pos = Vec(330, 188); bd = boss.distance
mark.punch(m, g, boss); moved = bd - boss.distance
assert 0 < moved < cfg.KNOCKBACK_DISTANCE and abs(moved - cfg.KNOCKBACK_DISTANCE * cfg.KNOCKBACK_BOSS_MULT) < 1e-6
print("boss knockback reduced OK:", moved)
# rage: tier 3
g = new(); battle(g); m = mk(g, (3, 0), (300, 188)); t = foe(g, "boss", 1500); t.pos = Vec(330, 188)
dmgs = []
for _ in range(cfg.RAGE_MAX_STACKS + 4):
    h = t.hp; mark.punch(m, g, t); dmgs.append(h - t.hp); t.pos = Vec(330, 188)
base = m.stats["damage"]
assert abs(dmgs[0] - base) < 1e-9 and abs(dmgs[1] - base * (1 + cfg.RAGE_BONUS_PER_STACK)) < 1e-9
assert m.rage_stacks == cfg.RAGE_MAX_STACKS and abs(dmgs[-1] - base * (1 + cfg.RAGE_BONUS_PER_STACK * cfg.RAGE_MAX_STACKS)) < 1e-9
print("rage stacks + cap OK:", [round(x, 2) for x in dmgs[:4]], "...", round(dmgs[-1], 2))
other = foe(g, "normal", 1400); other.pos = Vec(335, 188); mark.punch(m, g, other); assert m.rage_target is other and m.rage_stacks == 1
t.pos = Vec(335, 190); mark.punch(m, g, t); assert m.rage_stacks == 1, "switching target starts over"
t.pos = Vec(900, 600); m.cooldown_left = 99; g.update(1 / 60); assert m.rage_stacks == 0, "target left the range"
m.cooldown_left = 0; k = foe(g, "normal", 1300, hp=1.0); k.pos = Vec(330, 188); mark.punch(m, g, k)
assert not k.alive and m.rage_stacks == 0, "target died"
print("rage reset on switch / out of range / death OK")
# tier 1 only: no knockback, no rage
g = new(); battle(g); m = mk(g, (1, 0), (300, 188)); t = foe(g, "normal", 1500); t.pos = Vec(330, 188); d = t.distance
mark.punch(m, g, t); assert t.distance == d and m.rage_stacks == 0
print("tier gating OK")

# ---- 5. Sweep
g = new(); m = mk(g, (4, 0), (300, 188)); g.selected = m; length = g.path.length
assert actives.actives_of(m) == ["sweep_active"]
assert not actives.can_use(g, m, "sweep_active")[0], "no sweep in preparation"
assert not actives.use(g, m, "sweep_active") and not m.vanished
battle(g)
e1 = foe(g, "tanky", 400); e2 = foe(g, "tanky", 1800); e3 = foe(g, "tanky", 3000); boss = foe(g, "boss", 3300)
for e in (e1, e2, e3, boss): e.hp = e.max_hp = 99999.0
dmg = m.stats["damage"] * cfg.SWEEP_DAMAGE_MULT
g.ui.layout(g); assert g.ui.ability_rects, "ability button exists"
pygame.event.clear(); g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))   # same activation path as other actives
assert m.vanished and m.active_cd["sweep_active"] == cfg.SWEEP_COOLDOWN
assert not actives.use(g, m, "sweep_active"), "cannot re-use while sweeping / on cooldown"
g.draw()                                   # hidden Mark + marker draws without errors
g._request_sell(); assert m in g.towers and g.sell_pending is None, "cannot sell while sweeping"
pre = m.cooldown_left; shots = len(g.projectiles); hp0 = [e.hp for e in (e1, e2, e3)]
dists = []
for step in range(round((cfg.SWEEP_VANISH_TIME + cfg.SWEEP_DURATION + 0.5) * 60)):
    g.update(1 / 60)
    if g.sweeps and g.sweeps[0]["pos"] is not None: dists.append(g.sweeps[0]["dist"])
    if step % 20 == 0: g.draw()
    if not m.vanished: break
assert dists and dists[0] > length - 100 and all(b <= a for a, b in zip(dists, dists[1:])), "runs against the Didit direction, from the exit"
assert not m.vanished and not g.sweeps, "Mark is back"
for e in (e1, e2, e3):
    hits = (99999.0 - e.hp) / dmg
    assert abs(hits - cfg.SWEEP_HITS_PER_ENEMY) < 1e-6, hits
bh = (99999.0 - boss.hp) / dmg
print("hits per enemy:", [round((99999.0 - e.hp) / dmg, 2) for e in (e1, e2, e3)], "boss:", round(bh, 2))
assert abs(bh - cfg.SWEEP_HITS_PER_ENEMY) < 1e-6
assert len(g.projectiles) == shots and m.vanished is False
assert m.active_cd["sweep_active"] > 0, "long cooldown still running"
print("sweep: vanish, run, N hits, reappear OK")
# boss multiplier constant
g = new(); battle(g); m = mk(g, (4, 0), (300, 188)); boss = foe(g, "boss", 1800); boss.hp = boss.max_hp = 99999.0
cfg.SWEEP_BOSS_DAMAGE_MULTIPLIER = 0.5
assert actives.use(g, m, "sweep_active"); run(g, cfg.SWEEP_VANISH_TIME + cfg.SWEEP_DURATION + 0.3)
cfg.SWEEP_BOSS_DAMAGE_MULTIPLIER = 1.0
assert abs((99999.0 - boss.hp) - 0.5 * cfg.SWEEP_HITS_PER_ENEMY * m.stats["damage"] * cfg.SWEEP_DAMAGE_MULT) < 1e-6
print("boss damage multiplier OK")
# Mark attacks again after the sweep; sold tower while sweeping via reset is safe
g = new(); battle(g); m = mk(g, (4, 0), (300, 188)); assert actives.use(g, m, "sweep_active"); g.towers.remove(m); run(g, 1.0); assert not g.sweeps
g = new(); battle(g); m = mk(g, (4, 0), (300, 188)); actives.use(g, m, "sweep_active"); g.reset(); assert not g.sweeps; g.update(1 / 60)
print("sold / reset during sweep OK")

# ---- 6. debug F4 + savegame
g = new(); m = mk(g, (0, 0)); g.selected = m
for _ in range(5): g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F4))
assert m.tiers == [4, 0]; print("F4 debug OK")
from game import savegame as S
S.PATH = TMP + "/mark_save_test.json"
g.waves.number = 3; assert S.autosave(g); g2 = Game(screen); assert g2.load_save(); assert g2.towers[0].tiers == [4, 0]
os.remove(S.PATH); print("savegame OK")
print("ALL OK")
