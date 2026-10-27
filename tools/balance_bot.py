"""Crude bot that plays the whole game headless, to see where waves are lost.
Tweak prep_start / BUILD and run:  python tools/balance_bot.py   (a human plays better; use it for trends only)
"""
import os, sys, random, tempfile
TMP = tempfile.gettempdir()
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pygame; pygame.init(); screen = pygame.display.set_mode((1280, 720))
from game.game import Game, State, Phase
from data.towers import TOWERS
from data.activities import activities_for

BUILD = [("jalu",(500,188)),("jalu",(500,324)),("jalu",(800,324)),("zizi",(650,456)),("jalu",(800,188)),("romli",(350,324))]
SOLO = [("jalu",(500,188))]   # one Jalu only: wave 1-2 should still be holdable
def play(prep_start, dmg_mult=1.0, hp_mult=1.0, seed=0, build=None, max_waves=99):
    random.seed(seed)
    saved = {k: v["stats"]["damage"] for k, v in TOWERS.items()}
    for k, v in TOWERS.items(): v["stats"]["damage"] = saved[k] * dmg_mult
    g = Game(screen); dt = 1/30; queue = list(build or BUILD); log = []
    try:
        for step in range(30*60*45):
            if step % 15 == 0 and g.phase == Phase.PREP:
                if queue and g.money >= TOWERS[queue[0][0]]["cost"]:
                    k, pos = queue.pop(0); g.placing = k; g._try_place(pos)
                for t in g.towers:
                    for path in ([0, 1] if t.kind == "jalu" else [1, 0]):
                        up = t.next_upgrade(path)
                        if up and t.can_upgrade(path)[0] and g.money >= g.upgrade_cost(t, up) and g.ball_knowledge >= up["knowledge"]:
                            if not queue or g.money > 600:
                                g.selected = t; g._try_upgrade(path); break
                    if t.activity is None:
                        for aid, d in activities_for(t.kind):
                            if not t.activity_lock(d): g.selected = t; g._toggle_activity(aid); break
                if g.prep_time >= prep_start and g.waves.can_start: g._start_battle()
            g.update(dt)
            if g.phase == Phase.PREP and g.waves.number > len(log): log.append(100 - g.stash_hp)
            if g.state != State.PLAYING or g.waves.number > max_waves and g.phase == Phase.PREP: break
    finally:
        for k, v in TOWERS.items(): v["stats"]["damage"] = saved[k]
    top = sorted([(t.name[0], t.tiers) for t in g.towers])
    return g.state.name, g.waves.number, g.stash_hp, log, top

print("SOLO (1 Jalu) through wave 2:")
for start in (22, 40):
    r = play(start, build=SOLO, max_waves=2); print(f"  prep>={start}s: {r[0]:7} waves={r[1]:2} stash_lost={100-r[2]:3}")
print("FULL build:")
for start in (22, 30, 40, 55, 70):
    r = play(start); print(f"  prep>={start}s: {r[0]:7} waves={r[1]:2} hp={r[2]:3} lost/wave(cum)={r[3]}")
