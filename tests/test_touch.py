"""Headless checks for the phone controls (game/touch.py). Run from the project folder:  python tests/test_touch.py"""
import os, sys, tempfile
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pygame; pygame.init()
screen = pygame.display.set_mode((1280, 720))
from game.game import Game
from game import touch as T
from game.tower import Tower

def new():
    g = Game(screen); g.money = 99999; return g
def ev(t, **k): return pygame.event.Event(t, **k)
def tap(g, pos):
    g.handle_event(ev(pygame.MOUSEMOTION, pos=pos, rel=(0, 0), buttons=(0, 0, 0), touch=True))
    g.handle_event(ev(pygame.MOUSEBUTTONDOWN, pos=pos, button=1, touch=True))
    g.handle_event(ev(pygame.MOUSEBUTTONUP, pos=pos, button=1, touch=True))
    g.update(0.016)

g = new()
assert not g.touch.enabled                      # desktop stays in mouse mode
tap(g, (5, 5)); assert g.touch.enabled and g.ui.gear_btn.w == 72

# place a tower: card -> tap map (ghost only) -> OK
card = g.ui.shop_btns["jalu"].center
tap(g, card); assert g.placing == "jalu"
tap(g, (300, 200)); assert g.touch.ghost == (300, 200) and not g.towers
g.draw()
cancel, ok = T.confirm_rects(g.touch.ghost)
tap(g, ok.center); assert len(g.towers) == 1 and g.placing is None
g.update(0.016); assert g.touch.ghost is None

# invalid spot keeps the ghost and places nothing
tap(g, g.ui.shop_btns["jalu"].center); tap(g, (300, 200))   # on top of the first tower
cancel, ok = T.confirm_rects(g.touch.ghost); tap(g, ok.center)
assert len(g.towers) == 1 and g.placing == "jalu"
tap(g, cancel.center); assert g.placing is None

# fat finger: 40 px off the tower centre still selects it
tap(g, (300 + 38, 200)); assert g.selected is g.towers[0]

# Bima Graph keypad
g.selected = None
b = Tower("bima", (700, 250)); b.tiers = [2, 0]; b.recompute_stats(); g.towers.append(b); g.selected = b
g.update(0.016); tap(g, g.ui.graph.input.center); assert g.touch.keypad_open()
for label in ("2", "x", "+", "1"):
    k = [r for r, l, _, _ in g.touch.keys if l == label][0]; tap(g, k.center)
assert b.formula == "2x+1", b.formula
g.draw()
tap(g, [r for r, l, _, _ in g.touch.keys if l == "DEL"][0].center); assert b.formula == "2x+"
tap(g, [r for r, l, _, _ in g.touch.keys if l == "sin"][0].center); assert b.formula == "2x+"   # locked below tier 4
tap(g, [r for r, l, _, _ in g.touch.keys if l == "DONE"][0].center); assert not g.touch.keypad_open()

# pause overlay: tap resumes
g.paused = True; tap(g, (10, 300)); assert not g.paused
print("ALL OK")
