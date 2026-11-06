"""Headless: every model builds. Run: python tests/test_models.py"""
import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pygame; pygame.init(); pygame.display.set_mode((1280, 720))
from game import models, sprites_proc as sp
from data.settings import TOWER_RADIUS as R
from data.towers import TOWERS

assert models.look_of("jalu", (0, 0)) is None and models.look_of("jalu", (4, 1)) == (0, 4) and models.look_of("zizi", (0, 2)) == (1, 2)
for kind, d in list(TOWERS.items()) + [("fused_jalu_romli", {"color": (50, 170, 170)})]:
    base = sp.tower_sprite(kind, R, d["color"])
    looks = [(p, t) for p in (0, 1) for t in range(1, 5)] if kind in TOWERS else []
    for look in looks:
        img = sp.tower_sprite(kind, R, d["color"], look)
        assert img.get_size() == base.get_size(), (kind, look)
        models.weapon_image(kind, look, 37, True); models.projectile(kind, look)
        surf = pygame.Surface((300, 300)); models.draw_companion(surf, kind, look, 150, 200, 1.0)
assert models.weapon_image("jalu", (0, 2), 0, False) is None      # Mark punches: no weapon
assert models.projectile("romli", None) is not None
for n in ("fist", "loom", "screen", "pillow"):
    assert models.prop(n, 40).get_size() == (40, 40)
assert all(models.mark_runner(f, lf).get_width() > 10 for f in range(8) for lf in (False, True))
assert sp.TOWER_STYLE["zizi"]["skin"] == (238, 196, 156)
assert sp.TOWER_STYLE["romli"]["skin"][0] < 200   # browner than before
print("models OK")
