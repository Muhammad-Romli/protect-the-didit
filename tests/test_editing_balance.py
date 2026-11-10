"""Headless: Bima formula box editing, AUTO aim, Mark knockback cooldown, Romli/Zizi models. Run: python tests/test_editing_balance.py"""
import math, os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pygame; pygame.init(); screen = pygame.display.set_mode((1280, 720))
from game import options as O; O.PATH = "/tmp/_o_edit.json"
from game import bima, models, sprites_proc as sp
from game.game import Game
from game.tower import Tower
from data import mark as cfg
from data.settings import TOWER_RADIUS

g = Game(screen); g.money = 99999
b = Tower("bima", (600, 188)); b.tiers = [4, 0]; b.recompute_stats(); g.towers.append(b); g.selected = b
g.update(0.016); c = g.ui.graph

def key(k, uni="", mod=0): g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=k, unicode=uni, mod=mod))

# --- formula box: caret, selection, replace, copy/paste, delete
c.focused = True; b.formula = ""; c.cur = 0
for ch in "2x+1": key(ord(ch), ch)
assert b.formula == "2x+1" and c.cur == 4
for _ in range(3): key(pygame.K_LEFT)
key(ord("3"), "3"); assert b.formula == "23x+1", b.formula
key(pygame.K_a, "a", pygame.KMOD_CTRL); assert c._sel() == (0, 5)
key(ord("x"), "x"); assert b.formula == "x" and c.cur == 1
key(pygame.K_HOME); key(pygame.K_RIGHT, mod=pygame.KMOD_SHIFT); assert c._sel() == (0, 1)
key(pygame.K_c, "c", pygame.KMOD_CTRL); key(pygame.K_END); key(pygame.K_v, "v", pygame.KMOD_CTRL); assert b.formula == "xx", b.formula
key(pygame.K_BACKSPACE); key(pygame.K_BACKSPACE); assert b.formula == ""
g.draw(); c.focused = False
print("formula box editing OK")

# --- AUTO aim: the typed line passes through the target, on both sides of Bima
g.waves.active = True; g.waves._queue = [(999, "normal")]
for ex, ey in [(800, 120), (420, 256), (700, 256), (500, 120)]:
    g.enemies.clear(); e = g.spawn_enemy("tanky", 1); e.pos = pygame.Vector2(ex, ey)
    assert bima.auto_aim(g, b); pv = bima.update_preview(b, force=True)
    assert min(math.hypot(px - ex, py - ey) for px, py in pv["pts"]) < 6, (ex, ey, b.formula)
g.enemies.clear(); assert not bima.auto_aim(g, b)
print("AUTO aim OK")

# --- Mark: a Didit can only be knocked back once per KNOCKBACK_INTERVAL
g2 = Game(screen); e = g2.spawn_enemy("tanky", 300); g2.waves.active = True
from game import mark
d0 = e.distance; mark.knock_back(g2, e); d1 = e.distance; mark.knock_back(g2, e)
assert d1 == d0 - cfg.KNOCKBACK_DISTANCE and e.distance == d1, (d0, d1, e.distance)
g2.time += cfg.KNOCKBACK_INTERVAL + 0.01; mark.knock_back(g2, e); assert e.distance == d1 - cfg.KNOCKBACK_DISTANCE
print("Mark knockback cooldown OK")

# --- every Romli / Zizi look builds (new hair, cash, laptop, book, pillow)
for kind in ("romli", "zizi"):
    for look in (None, (0, 1), (0, 4), (1, 1), (1, 4)):
        assert sp.tower_sprite(kind, TOWER_RADIUS, (80, 200, 120), look) is not None
        w = models.weapon_image(kind, look, 30, False)
        if (kind, look) == ("zizi", None):
            assert w is None, "base Zizi holds no weapon (removed 2026-11-09)"
        else:
            assert w is not None, (kind, look)
print("models OK")
print("ALL OK")
