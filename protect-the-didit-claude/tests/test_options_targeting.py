"""Headless: speed x1-x3, auto-start, target priority, options UI. Run: python tests/test_options_targeting.py"""
import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pygame; pygame.init(); screen = pygame.display.set_mode((1280, 720))
from game.game import Game, Phase
from game import options as O
O.PATH = "/tmp/_opts_test.json"; os.path.exists(O.PATH) and os.remove(O.PATH)  # options persist; start clean

g = Game(screen)
def click(pos):
    a = g.ui.hit_test(pos, g)
    if a and a[0] != "noop": g._do_action(a)
    return a

g.speed = 1
for want in (2, 3, 1): g._toggle_speed(); assert g.speed == want
print("speed cycle 1->2->3->1 OK")

g.speed = 3; g.money = 5000; g.placing = "jalu"; g._try_place((500, 188)); t = g.towers[0]
g.waves.number = 1; g._start_battle(); e1 = g.spawn_enemy("normal", 900); e2 = g.spawn_enemy("tanky", 700); e3 = g.spawn_enemy("normal", 800)
t.pos = pygame.Vector2(560, 188); t.stats["range"] = 9999
for mode, want in (("first", e1), ("last", e2), ("strong", e2), ("weak", e3 if e3.hp <= e1.hp and e3.distance > e1.distance else e1), ("close", None)):
    t.targeting = mode; got = t.pick_target(g.enemies)
    if want is not None: assert got is want, (mode, got.kind, want.kind)
print("target priorities OK")
g.selected = t; g.ui.layout(g)
before = t.targeting; click(g.ui.target_rects[1].center); assert t.targeting != before
pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_t, mod=0, unicode="t")); g.handle_event(pygame.event.get()[-1]) if hasattr(g, "handle_event") else None
print("target buttons OK ->", t.targeting)

g2 = Game(screen); g2.options["auto_start"] = True; g2.options["auto_delay"] = 0
g2.update(0.05); assert g2.phase != Phase.PREP, "auto start should begin wave 1"
g2.options["auto_delay"] = 3; g3 = Game(screen); g3.options.update(auto_start=True, auto_delay=3)
for _ in range(100): g3.update(1 / 60)
assert g3.phase == Phase.PREP; [g3.update(1 / 60) for _ in range(120)]; assert g3.phase != Phase.PREP
print("auto-start (0s and 3s delay) OK")

g.options_open = True; g.ui.layout(g); g.ui._build_options_layout()
row = dict(g.ui.opt_rows)["auto_start"]; click(row.center); assert g.options["auto_start"] is True
row = dict(g.ui.opt_rows)["volume"]; v = g.options["volume"]; click((row.right - 20, row.centery)); assert g.options["volume"] != v
assert g.fx.audio.master == g.options["volume"] / 10; click(dict(g.ui.opt_rows)["resume"].center); assert not g.options_open
g.options_open = True; g.draw(); pygame.image.save(screen, "/tmp/options.png")
print("options UI OK"); print("ALL OK")
