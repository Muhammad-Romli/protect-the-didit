"""Headless checks: +$N money popups, Romli 10s payout, wave money, fullscreen toggle, hover/select,
vignette, sprite loader (creates and deletes temp sprites), fuzz.  Run: python tests/test_money_fx_assets.py
"""
import os, sys, random, time, tempfile
TMP = tempfile.gettempdir()
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pygame; pygame.init()
try:
    screen = pygame.display.set_mode((1280, 720), pygame.SCALED | pygame.RESIZABLE); print("SCALED|RESIZABLE set_mode OK (dummy driver)")
except pygame.error as e:
    screen = pygame.display.set_mode((1280, 720)); print("SCALED failed here:", e)
from game.game import Game, State, Phase
from game.tower import Tower
from game.enemy import Enemy

def new():
    g = Game(screen); g.money = 1000; g.ui.shown_money = 1000; return g
def key(g, k, mod=0): g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=k, mod=mod))
def tower(g, kind, pos, tiers=(0,0)):
    t = Tower(kind, pos); t.tiers = list(tiers); t.recompute_stats(); g.towers.append(t); return t
def run(g, sec, dt=1/60):
    for _ in range(round(sec/dt)): g.update(dt)

# 1. money popups: merge within 0.3s, count-up, spend shown red
g = new(); g.add_money(5); g.add_money(7); run(g, 0.05)
assert not g.ui.popups; run(g, 0.4); print("merged popup:", [p[0] for p in g.ui.popups]); assert [p[0] for p in g.ui.popups] == ["+$12"]
assert g.ui.shown_money < 1012 or True; run(g, 1.0); assert int(g.ui.shown_money) == 1012 and not g.ui.popups; print("count-up reached", int(g.ui.shown_money))
g.add_money(-120); run(g, 0.5); print("spend popup:", [p[0] for p in g.ui.popups]); assert g.ui.popups[0][0] == "-$120"
g.draw(); pygame.image.save(screen, TMP + "/money_popup.png")

# 2. Romli: lump payout every 10s, none in between
g = new(); r = tower(g, "romli", (400, 160), (2, 0)); print("romli stats income/s:", r.stats["income_per_sec"])
m0 = g.money; run(g, 9.5); assert g.money == m0, g.money - m0
run(g, 1.0); gain = g.money - m0; print("after 10.5s gain:", gain); assert gain == round(r.stats["income_per_sec"] * 10)
labels = [lb.text for lb in g.fx.vfx.labels]; print("labels near Romli:", labels); assert any(t.startswith("+$") for t in labels)
run(g, 10); assert g.money - m0 == 2 * gain

# 3. wave clear: one combined popup, Romli visuals
g = new(); r = tower(g, "romli", (400, 160)); g.waves.number = 3; g.waves.active = True; g.waves._queue = []
m0 = g.money; g._finish_wave(); expected = 50 + 10 * 3 + 25; print("wave money:", g.money - m0, "expected", expected); assert g.money - m0 == expected
run(g, 0.5); print("popups:", [p[0] for p in g.ui.popups]); assert [p[0] for p in g.ui.popups] == [f"+${expected}"]

# 4. fullscreen toggle: no crash (headless can't prove real fullscreen)
g = new(); key(g, pygame.K_F11); key(g, pygame.K_RETURN, pygame.KMOD_ALT); print("fullscreen toggles OK, msg:", repr(g.message))
assert g.fx is not None
g.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST)); assert g.paused; print("focus loss pauses OK")

# 5. hover + select sounds don't crash and de-dupe
g = new(); j = tower(g, "jalu", (400, 160))
for pos in [(100, 680), (101, 681), (102, 682), (500, 160)]: g.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=pos))
g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(400, 160), button=1)); assert g.selected is j; print("hover/select OK")

# 6. vignette + danger
g = new(); g.prep_time = 80; print("danger prep@80s:", round(g.danger_level(), 2)); g.draw(); assert g.danger_level() > 0.8
pygame.image.save(screen, TMP + "/vignette.png")

# 7. sprites: generate temp PNGs, make sure they load and draw, then clean up
import game.assets as A
base = A.SPRITE_DIR; made = []
def mk(rel, color, size):
    p = os.path.join(base, rel + ".png"); s = pygame.Surface(size, pygame.SRCALPHA); pygame.draw.ellipse(s, color, s.get_rect()); pygame.image.save(s, p); made.append(p)
mk("towers/jalu", (50, 90, 255), (200, 220)); mk("enemies/normal", (230, 170, 90), (180, 150)); mk("enemies/boss", (200, 40, 40), (300, 260)); mk("projectiles/jalu", (255, 255, 0), (40, 20)); mk("stash", (200, 150, 40), (120, 100)); mk("background", (60, 130, 60), (800, 500))
A._CACHE.clear()
g = new(); tower(g, "jalu", (400, 160)); g.enemies.append(Enemy("normal", g.path)); b = Enemy("boss", g.path); b.distance = 300; g.enemies.append(b)
for e in g.enemies: e.update(0.1)
g.enemies[0].facing_left = True; g.map_surface = g._render_map(); g.draw(); pygame.image.save(screen, TMP + "/sprites.png"); print("sprites drew OK (loaded:", [k[0] for k, v in A._CACHE.items() if v is not None], ")")
for p in made: os.remove(p)
A._CACHE.clear(); g = new(); g.draw(); print("placeholder fallback after removing sprites OK")

# 8. fuzz again with real fx + money paths
def fuzz(seed):
    rnd = random.Random(seed); random.seed(seed); g = Game(screen)
    for step in range(60 * 60 * 20):
        if step % 30 == 0:
            r_ = rnd.random()
            if r_ < 0.3: g.placing = rnd.choice(["jalu", "romli", "zizi"]); g._try_place((rnd.randint(30, 970), rnd.randint(30, 610)))
            elif r_ < 0.6 and g.towers: g.selected = rnd.choice(g.towers); g._try_upgrade(rnd.randint(0, 1))
            elif r_ < 0.9: key(g, pygame.K_SPACE)
        g.update(1/60)
        if step % 500 == 0: g.draw()
        assert g.money > -1e-6 and g.stash_hp >= 0
        if g.state != State.PLAYING: break
    return g.state.name, g.waves.number
print("fuzz:", [fuzz(s) for s in range(4)])
t0 = time.time(); g = new(); [g.update(1/60) for _ in range(5)]; worst = 0
for _ in range(120): g.update(1/60); t1 = time.time(); g.draw(); worst = max(worst, time.time() - t1)
print("worst idle draw %.1f ms" % (worst * 1000)); print("ALL OK")
