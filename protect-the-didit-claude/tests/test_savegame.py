"""Headless: autosave every 3rd cleared wave, snapshot -> restore round trip, bad data. Run: python tests/test_savegame.py"""
import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pygame; pygame.init(); screen = pygame.display.set_mode((1280, 720))
from game.game import Game, State
from game import savegame as S
S.PATH = "/tmp/_save_test.json"; S.clear()

g = Game(screen)
assert S.read() is None and S.summary() is None
g.money = 5000
for kind, pos in (("jalu", (500, 188)), ("bima", (700, 188))):
    g.placing = kind; g._try_place(pos)
jalu, bima = g.towers
jalu.upgrade(0); jalu.upgrade(0); jalu.targeting = "strong"
bima.upgrade(0); bima.formula = "2x+1"; bima.graph_dir = -1; bima.brain, bima.brain_init = 7.0, True

# waves 1 and 2: no save; wave 3: save
for n in (1, 2, 3):
    g.waves.number = n - 1; g._start_battle(); g.enemies.clear(); g.projectiles.clear(); g._finish_wave()
    assert (S.read() is not None) == (n >= 3), n
s = S.summary(); assert s["wave"] == 3 and s["towers"] == 2, s
print("autosave after wave 3 OK")

money, hp = int(g.money), g.stash_hp
g2 = Game(screen)
assert S.restore(g2, S.read())
assert g2.waves.number == 3 and int(g2.money) == money and g2.stash_hp == hp and len(g2.towers) == 2
j2, b2 = g2.towers
assert j2.kind == "jalu" and j2.tiers == [2, 0] and j2.targeting == "strong" and j2.spent == jalu.spent
assert b2.formula == "2x+1" and b2.graph_dir == -1 and abs(b2.brain - 7.0) < 0.01
assert j2.stats["damage"] == jalu.stats["damage"] and g2.state == State.PLAYING and not g2.waves.active
print("round trip OK")

assert not S.restore(g2, {"version": 1, "wave": 3, "money": 1, "stash_hp": 1, "towers": [{"kind": "nope"}]})
assert not S.restore(g2, {"version": 1, "wave": 999, "money": 1, "stash_hp": 1, "towers": []})
assert not S.restore(g2, {"version": 1})
assert g2.waves.number == 0 and not g2.towers  # failed restore leaves a fresh game
open(S.PATH, "w").write("{broken"); assert S.read() is None
print("bad data OK")

g.waves.number = g.waves.total - 1; S.autosave(g); g._start_battle(); g.enemies.clear(); g._finish_wave()
assert g.state == State.WON and S.read() is None
print("win clears save OK"); print("ALL OK")
