"""Headless: Rich / Speedster / Reinforced Didit, Temporal Loom passive, armor breaker, 30 waves.
Run: python tests/test_new_enemies.py"""
import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pygame; pygame.init(); screen = pygame.display.set_mode((1280, 720))
from game.game import Game
from game.tower import Tower
from data.waves import WAVES, NEW_ENEMY_WAVES, SPECIAL_WAVES
from data.enemies import ENEMIES, NORMAL_SPEED
from data.towers import TOWERS

g = Game(screen); g.waves.number = 4; g.waves.active = True; g.money = 5000
def tower(kind, pos, tiers):
    t = Tower(kind, pos); t.tiers = list(tiers); t.recompute_stats(); g.towers.append(t); return t

# --- 30 waves, introductions and specials
assert len(WAVES) == 30 and g.waves.total == 30
for wave, kind in NEW_ENEMY_WAVES.items():
    first = next(i for i, w in enumerate(WAVES, 1) if any(k == kind for k, *_ in w)); assert first == wave, (kind, first, wave)
assert set(SPECIAL_WAVES) == {7, 17, 25}
print("30 waves, intro waves 6/8/10/13/17/22, specials 7/17/25 OK")

# --- Reinforced: 10 hits to break armor, then HP damage; Romli Better code counts 1 hit as 3
r = g.spawn_enemy("reinforced", 300); plain = tower("jalu", (500, 188), (0, 0)); hp0 = r.hp
for i in range(9): g.hit_enemy(r, 5, source=plain)
assert r.armor == 1 and r.hp == hp0; g.hit_enemy(r, 5, source=plain); assert r.armor == 0 and r.hp == hp0
g.hit_enemy(r, 5, source=plain); assert r.hp < hp0; print("armor: 10 hits then damage OK")
r2 = g.spawn_enemy("reinforced", 300); rom = tower("romli", (350, 324), (0, 2)); assert "armor_breaker" in rom.effects
for i in range(3): g.hit_enemy(r2, 5, source=rom)
assert r2.armor == 1, r2.armor; g.hit_enemy(r2, 5, source=rom); assert r2.armor == 0
rom0 = tower("romli", (400, 324), (0, 1)); assert "armor_breaker" not in rom0.effects; print("Romli Better code: 1 hit = 3 OK")

# --- Speedster: very fast, decelerates; Temporal Loom passive normalizes fast enemies for 3s, refreshed per hit
sp = g.spawn_enemy("speedster", 100); s0 = sp.speed; assert sp.is_boss and sp.is_fast
for _ in range(60 * 14): sp.age += 1 / 60
assert s0 > 3.5 * sp.speed and abs(sp.speed - sp.base_speed) < 1; print(f"speedster {s0:.0f} -> {sp.speed:.0f} px/s OK")
loom = tower("jalu", (500, 324), (0, 3)); assert "speed_against_time" in loom.effects and "time_push" in loom.effects
assert TOWERS["jalu"]["paths"][1]["name"] == "Temporal Loom Guy"
f = g.spawn_enemy("fast", 100); sp2 = g.spawn_enemy("speedster", 100); n = g.spawn_enemy("normal", 100)
class P: aoe_radius = 0; damage = 1
for e in (f, sp2, n):
    import game.effects as fx; fx.EFFECTS["speed_against_time"](loom, g, "hit", proj=P, victims=[e])
assert abs(f.speed - NORMAL_SPEED * f.speed_mult) < 1e-6 and sp2.speed <= NORMAL_SPEED * sp2.speed_mult + 1e-6 and n.normalize_timer == 0
f.update(2.0); assert f.normalize_timer > 0.9; f.update(1.5); assert f.speed > NORMAL_SPEED * f.speed_mult * 1.5; print("Speed Against Time: 3s normal speed OK")

# --- Rich: big bounty, steals money on leak
g.enemies.clear(); rich = g.spawn_enemy("rich", 100); rich.reached_end = True; m = g.money; g._collect_enemies()
assert g.money == m - rich.steal and not g.enemies; print(f"rich leak stole ${m - g.money:.0f} OK")
rich = g.spawn_enemy("rich", 200); rich.hp = 0; m = g.money; g._collect_enemies(); assert g.money - m >= ENEMIES["rich"]["money"]; print("rich bounty OK")
g.draw(); print("ALL OK")
