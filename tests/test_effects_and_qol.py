"""Headless checks: Zizi unlocks, every effect hook, pause/hotkeys/sell confirm, random-bot fuzz.
Run from the project folder:  python tests/test_effects_and_qol.py
"""
import os, sys, random, tempfile
TMP = tempfile.gettempdir()
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pygame; pygame.init()
screen = pygame.display.set_mode((1280, 720))
from game.game import Game, State, Phase
from game.tower import Tower
from game.enemy import Enemy
from game.projectile import Projectile
from game.utils import Vec
from data.effects import EFFECT_PARAMS

def new():
    g = Game(screen); g.money = 99999; g.ball_knowledge = 9999; return g
def click(g, pos, b=1):
    g.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=pos))
    g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=b))
def key(g, k): g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=k))
def tower(g, kind, pos, tiers=(0,0)):
    t = Tower(kind, pos); t.tiers = list(tiers); t.recompute_stats(); g.towers.append(t); return t
def enemy_at(g, kind, dist, **kw):
    e = Enemy(kind, g.path, **kw); e.distance = dist; e.pos = g.path.position_at(dist); g.enemies.append(e); return e
def fire(g, t, target):
    s = t.stats
    p = Projectile(t.pos, target, 999, s["damage"], s["aoe_radius"], s["slow"], s["slow_duration"], s["money_per_hit"], t.color, t)
    p.pos = Vec(target.pos); g._resolve_hit(p)

# ---- A. Zizi unlocks by path tier 2
g = new(); z = tower(g, "zizi", (300, 160)); g.selected = z
rects = dict(g.ui.activity_rects("zizi"))
click(g, rects["zizi_sloth"].center); print("sloth at start:", z.activity, "|", g.message)
click(g, rects["zizi_pray"].center); print("pray at start :", z.activity, "|", g.message)
assert z.activity is None
for _ in range(2): click(g, g.ui.upgrade_btns[1].center)   # path B -> tier 2
assert z.tiers == [0, 2]
click(g, rects["zizi_sloth"].center); assert z.activity == "zizi_sloth"; print("sloth after B2: OK")
click(g, rects["zizi_pray"].center); print("pray after B2 :", z.activity, "|", g.message)
assert z.activity == "zizi_sloth"
# A2 and B2 can never both exist -> one Zizi unlocks only one activity
z2 = tower(g, "zizi", (500, 160), (1, 2)); print("A tier 2 on a (1,2) tower allowed?", z2.can_upgrade(0))
assert not z2.can_upgrade(0)[0]
z3 = tower(g, "zizi", (700, 160), (2, 0)); g.selected = z3
click(g, rects["zizi_pray"].center); assert z3.activity == "zizi_pray"; print("pray after A2: OK")

# ---- B. effects
random.seed(1)
# pierce: A2 hits 1 extra neighbour only
g = new(); j = tower(g, "jalu", (400, 160), (2, 0))
a = enemy_at(g, "tanky", 300); b = enemy_at(g, "tanky", 320); c = enemy_at(g, "tanky", 340)
fire(g, j, a); print("pierce hp:", a.hp, b.hp, c.hp, "(dmg", j.stats["damage"], ")")
hit = [e for e in (a, b, c) if e.hp < 60]; assert len(hit) == 2 and a.hp < 60

# chain lightning: A3, 3 jumps with falloff, bolts created
g = new(); j = tower(g, "jalu", (400, 160), (3, 0))
es = [enemy_at(g, "tanky", 300 + i * 25) for i in range(6)]
fire(g, j, es[0]); dmg = j.stats["damage"]
print("chain hp loss:", [round(60 - e.hp, 2) for e in es], "bolts:", len(g.bolts), "dmg", dmg)
assert sum(1 for e in es if e.hp < 60) >= 4 and len(g.bolts) == 3
assert abs((60 - es[0].hp) - dmg) < 1e-6
g.draw()  # bolts render

# time push + boss immune (force chance 1)
EFFECT_PARAMS["time_push"]["chance"] = 1.0
g = new(); j = tower(g, "jalu", (400, 160), (1, 3)); e = enemy_at(g, "normal", 500); boss = enemy_at(g, "boss", 500)
fire(g, j, e); fire(g, j, boss); print("push:", round(e.distance), "boss", round(boss.distance)); assert e.distance == 420 and boss.distance == 500
# sleep
EFFECT_PARAMS["sleep_chance"]["chance"] = 1.0
g = new(); z = tower(g, "zizi", (400, 160), (1, 3)); e = enemy_at(g, "tanky", 500); boss = enemy_at(g, "boss", 500)
fire(g, z, e); fire(g, z, boss); print("stun:", e.stun_timer, boss.stun_timer); assert e.stun_timer == 1.5 and boss.stun_timer == 0
d0 = e.distance; e.update(1.0); assert e.distance == d0  # stopped
# debuff
g = new(); z = tower(g, "zizi", (400, 160), (0, 2)); j = tower(g, "jalu", (450, 160)); e = enemy_at(g, "tanky", 300)
e.pos = Vec(420, 160); fire(g, j, e); print("debuffed dmg:", round(60 - e.hp, 3), "expected", round(j.stats["damage"] * 1.15, 3))
assert abs((60 - e.hp) - j.stats["damage"] * 1.15) < 1e-6
e2 = enemy_at(g, "tanky", 300); e2.pos = Vec(900, 600); fire(g, j, e2); assert abs((60 - e2.hp) - j.stats["damage"]) < 1e-6
# aura
g = new(); z = tower(g, "zizi", (400, 160), (2, 0)); near = tower(g, "jalu", (500, 160)); far = tower(g, "jalu", (900, 160))
print("aura rates:", g.attack_speed_mult(near), g.attack_speed_mult(far), g.attack_speed_mult(z))
assert abs(g.attack_speed_mult(near) - 1.1) < 1e-9 and g.attack_speed_mult(far) == 1 and g.attack_speed_mult(z) == 1
# discount + sale value
g = new(); r = tower(g, "romli", (400, 160), (3, 0)); j = tower(g, "jalu", (500, 160)); g.selected = j
up = j.next_upgrade(0); print("jalu A1 cost with Romli A3 nearby:", g.upgrade_cost(j, up), "base", up["cost"]); assert g.upgrade_cost(j, up) == 114
m = g.money; g._try_upgrade(0); assert m - g.money == 114 and j.spent == 200 + 114
# boss kill bonus
g = new(); r = tower(g, "romli", (400, 160), (4, 0)); b = enemy_at(g, "boss", 100); b.hp = 0; m = g.money; g._collect_enemies()
print("boss kill money:", g.money - m); assert g.money - m == 150 + 500

# ---- C. QoL
g = new(); e = enemy_at(g, "normal", 100); g.waves.active = True; g.waves._queue = [(99, "normal")]
key(g, pygame.K_p); assert g.paused; d0 = e.distance; [g.update(1/60) for _ in range(60)]; assert e.distance == d0
key(g, pygame.K_p); [g.update(1/60) for _ in range(60)]; assert e.distance > d0; print("pause OK")
g = new(); key(g, pygame.K_1); assert g.placing == "jalu"; key(g, pygame.K_3); assert g.placing == "zizi"; key(g, pygame.K_3); assert g.placing is None
key(g, pygame.K_SPACE); assert g.phase == Phase.BATTLE; print("hotkeys OK")
g = new(); j = tower(g, "jalu", (400, 160)); g.selected = j; key(g, pygame.K_q); assert j.tiers == [1, 0]; key(g, pygame.K_w); assert j.tiers == [1, 1]
key(g, pygame.K_x); assert j in g.towers and g.sell_pending is j; key(g, pygame.K_x); assert j not in g.towers; print("sell confirm OK")
g = new(); j = tower(g, "jalu", (400, 160)); g.selected = j; click(g, g.ui.sell_btn.center)
[g.update(1/60) for _ in range(60 * 4)]; click(g, g.ui.sell_btn.center); assert j in g.towers; print("sell confirm expires OK")
g.draw(); pygame.image.save(screen, TMP + "/qol.png")

# ---- D. fuzz: random bots through all 10 waves, check invariants
def fuzz(seed):
    rnd = random.Random(seed); random.seed(seed)
    g = Game(screen); g.money = 650
    for step in range(60 * 60 * 25):
        if step % 30 == 0:
            r = rnd.random()
            if r < 0.3: g.placing = rnd.choice(["jalu", "romli", "zizi"]); g._try_place((rnd.randint(30, 970), rnd.randint(30, 610)))
            elif r < 0.6 and g.towers: g.selected = rnd.choice(g.towers); g._try_upgrade(rnd.randint(0, 1))
            elif r < 0.75 and g.towers:
                g.selected = rnd.choice(g.towers); from data.activities import activities_for
                a = activities_for(g.selected.kind)
                if a: g._toggle_activity(rnd.choice(a)[0])
            elif r < 0.8 and g.towers: g.selected = rnd.choice(g.towers); g._request_sell(); g._request_sell()
            elif r < 0.9: key(g, pygame.K_SPACE)
        g.update(1/60)
        if step % 600 == 0: g.draw()
        assert g.money > -1e-6 and g.stash_hp >= 0 and g.activity_slots_used() <= 3, (seed, step)
        for t in g.towers:
            assert t.tiers[0] <= 4 and t.tiers[1] <= 4 and min(t.tiers) <= 1
        if g.state != State.PLAYING: break
    return g.state.name, g.waves.number
print("fuzz:", [fuzz(s) for s in range(6)])
print("ALL OK")
