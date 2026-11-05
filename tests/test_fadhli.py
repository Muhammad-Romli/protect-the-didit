"""Headless checks for Fadhli (petanque athlete) and the large-damage numbers.
Run from the project folder:  python tests/test_fadhli.py
"""
import os, sys, random
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pygame; pygame.init()
screen = pygame.display.set_mode((1280, 720))
from data import fadhli as cfg
from data.settings import DAMAGE_STAGES
from data.towers import TOWERS
from game import actives, fadhli
from game.game import Game
from game.projectile import Projectile
from game.tower import Tower
from game.ui import _range_text
from game.utils import Vec

def new():
    g = Game(screen); g.money = 99999; return g
def battle(g):
    g.waves.active = True; g.waves._queue = [(999, "normal")]   # keeps the wave running, nothing spawns
def mk(g, tiers, pos=(500, 188)):
    t = Tower("fadhli", pos); t.tiers = list(tiers); t.recompute_stats(); g.towers.append(t); return t
def foe(g, kind, dist, hp=9999.0):
    e = g.spawn_enemy(kind, dist); e.hp = e.max_hp = hp; e.base_speed = 0.0; return e
def near(g, dist, off=80):
    """A tower position `off` px beside the path at `dist` (so a boule always flies for a few frames)."""
    c = g.path.position_at(dist); return (c.x, c.y - off)
def run(g, seconds, dt=1 / 60):
    for _ in range(round(seconds / dt)): g.update(dt)
def fired(g, seconds, dt=1 / 60):
    """Run and return the projectiles Fadhli fired, in order, as (damage, power_crater, gyro)."""
    seen, out = set(), []
    for _ in range(round(seconds / dt)):
        g.update(dt)
        for p in g.projectiles:
            if id(p) not in seen:
                seen.add(id(p)); out.append((p.damage, p.power_crater, p.gyro))
    return out

# ---- 1. data: every tier has a measurable stat gain (rule 7); odds are valid
for path in TOWERS["fadhli"]["paths"]:
    for up in path["tiers"]:
        m = up["stat_mods"]
        assert m.get("damage", 0) > 0 or m.get("cooldown", 0) < 0 or m.get("range", 0) > 0, up["name"]
assert cfg.STUN_CHANCE + cfg.SLOW_CHANCE <= 1.0
print("tier stats OK")

# ---- 2. steel boule: one roll per hit, 20% stun / 30% slow / 50% nothing
random.seed(7); n = 40000; c = {"stun": 0, "slow": 0, "none": 0}
for _ in range(n): c[fadhli.roll_status()] += 1
assert abs(c["stun"] / n - 0.20) < 0.01 and abs(c["slow"] / n - 0.30) < 0.01 and abs(c["none"] / n - 0.50) < 0.01, c
g = new(); steel = mk(g, (0, 3)); both = stun = slow = 0
for i in range(300):
    e = g.spawn_enemy("normal", 100 + i); fadhli.apply_status(e, steel, False)
    s_, l_ = e.stun_timer > 0, e.slow_timer > 0
    both += s_ and l_; stun += s_; slow += l_
assert both == 0 and 0 < stun < 150 and 0 < slow < 200, (both, stun, slow)
plain = mk(g, (0, 2)); e = g.spawn_enemy("normal", 50); fadhli.apply_status(e, plain, False)
assert e.stun_timer == 0 and e.slow_timer == 0          # no steel before Accuracy tier 3
print("20/30/50 OK")

# ---- 3. three-target bounce: initial target + 2, nobody hit twice
g = new(); battle(g); t = mk(g, (0, 2), near(g, 420))
es = [foe(g, "normal", d) for d in (380, 400, 420, 440, 460)]
for _ in range(600):
    g.update(1 / 60)
    if t.cooldown_left > 0 and not g.projectiles: break
lost = [round(9999.0 - e.hp, 6) for e in es]
assert sorted(lost) == [0, 0, round(t.stats["damage"], 6), round(t.stats["damage"], 6), round(t.stats["damage"], 6)], lost
assert lost[4] > 0                                       # the first enemy is the initial target
print("bounce OK")

# ---- 4. crater: AoE damage over time in ticks, not every frame; armor loses one hit per tick
g = new(); e = foe(g, "normal", 400); spot = Vec(e.pos)
g.craters.append([Vec(spot), cfg.CRATER_RADIUS, cfg.CRATER_DPS, cfg.CRATER_DURATION, None, 0.0])
g.craters.append([Vec(spot.x + 400, spot.y), cfg.CRATER_RADIUS, cfg.CRATER_DPS, cfg.CRATER_DURATION, None, 0.0])  # nobody inside
run(g, 2.0)
dealt = 9999.0 - e.hp
assert abs(dealt - cfg.CRATER_DPS * 2.0) <= cfg.CRATER_DPS * cfg.CRATER_TICK + 1e-6, dealt
run(g, cfg.CRATER_DURATION)
assert not g.craters, "crater expires"
g = new(); r = foe(g, "reinforced", 400); armor0 = r.armor
g.craters.append([Vec(r.pos), cfg.POWER_CRATER_RADIUS, cfg.POWER_CRATER_DPS, cfg.CRATER_DURATION, None, 0.0])
run(g, 2.0)
assert armor0 - r.armor <= round(2.0 / cfg.CRATER_TICK) + 1, (armor0, r.armor)   # a hit every frame would strip all of it
print("crater OK")

# ---- 5. Power T4: infinite range is permanent (no activation needed); T3 is not
g = new(); t3 = mk(g, (3, 0), (60, 690)); t4 = mk(g, (4, 0), (60, 690))
cands = [foe(g, "normal", d) for d in range(100, 2000, 150)]
far = max(cands, key=lambda e: t4.pos.distance_to(e.pos))
assert t4.pos.distance_to(far.pos) > t3.stats["range"], "test map has no enemy beyond Power T3's range"
assert t3.stats["range"] < cfg.INFINITE_RANGE <= t4.stats["range"]
assert t3.pick_target([far]) is None and t4.pick_target([far]) is far
assert _range_text(t4.stats["range"]) == "infinite" and _range_text(175.0) == "175"
print("infinite range OK")

# ---- 6. Meteor: exactly three empowered shots; a shot whose target died is not used up
g = new(); battle(g); t = mk(g, (4, 0), near(g, 300)); foe(g, "normal", 300, 1e9)
assert actives.use(g, t, "fadhli_power_active") and t.power_shots == cfg.POWER_SHOTS
assert not actives.use(g, t, "fadhli_power_active"), "on cooldown"
shots = fired(g, 9.0)[:4]
assert [s[1] for s in shots] == [True, True, True, False], shots
assert abs(shots[0][0] - t.stats["damage"] * cfg.POWER_SHOT_MULT) < 1e-9 and abs(shots[3][0] - t.stats["damage"]) < 1e-9
g = new(); battle(g); t = mk(g, (4, 0)); e = foe(g, "normal", 300)
p = Projectile(t.pos, e, 500, 10, 0, 0, 0, 0, t.color, t); fadhli.prepare_projectile(t, p, True)
t.power_shots = 2; e.hp = 0; g._resolve_hit(p)
assert t.power_shots == 3 and not g.craters, "missed empowered shot is refunded"
e2 = foe(g, "normal", 310); p = Projectile(t.pos, e2, 500, 10, 0, 0, 0, 0, t.color, t); fadhli.prepare_projectile(t, p, True)
t.power_shots = 2; g._resolve_hit(p)
assert t.power_shots == 2 and g.craters and g.craters[0][1] == cfg.POWER_CRATER_RADIUS and g.craters[0][2] == cfg.POWER_CRATER_DPS
print("empowered shots OK")

# ---- 7. Arigatou, Gyro: 5 s, first shot = 1/4 damage, each next x1.618, reset afterwards, base damage untouched
g = new(); battle(g); t = mk(g, (0, 4), near(g, 300)); foe(g, "normal", 300, 1e9)
base = t.stats["damage"]
assert actives.use(g, t, "fadhli_gyro_active") and t.gyro_timer == cfg.GYRO_DURATION
assert abs(t.golden_damage - base * cfg.GOLDEN_START_FRACTION) < 1e-9
shots = fired(g, cfg.GYRO_DURATION + 1.5)
inside = [s for s in shots if s[2]]
assert len(inside) >= 8 and abs(inside[0][0] - base / 4) < 1e-9, inside[:2]
for a, b in zip(inside, inside[1:]): assert abs(b[0] / a[0] - cfg.GOLDEN_RATIO) < 1e-6, (a, b)
assert not shots[-1][2] and abs(shots[-1][0] - base) < 1e-9, shots[-1]      # after the window: normal damage again
assert t.stats["damage"] == base and t.golden_damage == 0.0
print("golden ratio OK")

# ---- 8. Spinned: tornado look + short stun; bosses only get a short look, never stunned
g = new(); n_ = g.spawn_enemy("normal", 100); b_ = g.spawn_enemy("boss", 100)
fadhli.spin(n_); fadhli.spin(b_)
assert n_.spinned_timer == cfg.SPIN_DURATION and n_.stun_timer == cfg.SPIN_STUN
assert b_.spinned_timer == cfg.SPIN_BOSS_DURATION and b_.stun_timer == 0
print("spinned OK")

# ---- 9. drawing: tower with Meteor pips + Gyro bar + stand gag
g = new(); t = mk(g, (0, 4), (150, 200)); t.power_shots = 2; t.gyro_timer = 3.0
t.draw(pygame.Surface((300, 300), pygame.SRCALPHA))
print("draw OK")

# ---- 10. large-damage numbers: only big hits, bigger font + color at every stage
th = [s[0] for s in DAMAGE_STAGES]; sizes = [s[1] for s in DAMAGE_STAGES]
assert th == sorted(th) and sizes == sorted(sizes) and len(set(sizes)) == len(sizes) and len({s[2] for s in DAMAGE_STAGES}) == len(sizes)
g = new(); e = foe(g, "normal", 300, 1e9); g.fx._comic_cd = 1e9      # no random hit words in the label list
n0 = len(g.fx.vfx.labels); g.hit_enemy(e, th[0] - 0.5)
assert len(g.fx.vfx.labels) == n0, "routine hits get no number"
for thr, size, color in DAMAGE_STAGES:
    g.hit_enemy(e, thr); lab = g.fx.vfx.labels[-1]
    assert lab.size == size and lab.color == color and lab.text == str(round(thr)), (thr, lab)
print("damage numbers OK")
print("ALL FADHLI TESTS PASSED")
