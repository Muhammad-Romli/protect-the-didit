"""Headless: Trojan chains, wave scaling, bounty growth. Run: python tests/test_trojan_economy.py"""
import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pygame; pygame.init(); screen = pygame.display.set_mode((1280, 720))
from game.game import Game
from data.waves import WAVE_SCALING

g = Game(screen); g.waves.number = 3; g.waves.active = True
t = g.spawn_enemy("trojan", 500); t.hp = 0; g._collect_enemies()
print("trojan ->", [e.kind for e in g.enemies]); assert [e.kind for e in g.enemies].count("normal") == 5
g.enemies.clear()
tt = g.spawn_enemy("trojan_trojan", 500); assert tt.is_boss; tt.hp = 0; g._collect_enemies()
assert [e.kind for e in g.enemies] == ["trojan"] * 3
for e in g.enemies: e.hp = 0
g._collect_enemies(); kinds = [e.kind for e in g.enemies]; print("TT chain ->", len(kinds), "normals"); assert kinds == ["normal"] * 15
assert all(e.hp_mult == tt.hp_mult and e.bounty == tt.bounty * 0 + e.bounty for e in g.enemies)
g.enemies.clear(); g.waves.number = 1; a = g.spawn_enemy("normal"); g.waves.number = 10; b = g.spawn_enemy("normal")
print("wave1 hp", a.max_hp, "bounty", a.bounty, "| wave10 hp", b.max_hp, "bounty", b.bounty)
assert a.max_hp == 10 * WAVE_SCALING[0][0] and b.max_hp == 10 * WAVE_SCALING[9][0] and b.bounty > a.bounty >= 10
g.enemies.clear(); g.waves.number = 2; leak = g.spawn_enemy("trojan", g.path.length - 1); g.update(0.1)
assert not any(e.kind == "normal" for e in g.enemies); print("leaking Trojan spawns nothing OK")
print("ALL OK")
