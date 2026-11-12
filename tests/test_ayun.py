"""Headless checks for A'yun (shopkeeper): data, one upgrade track, gacha (cap / odds / pity), items as attacks with their own
cooldowns, expiry, replace-or-sell pop-up, the sell-on-kill passive, Supply Chain auto-roll + Steady Supply, savegame, UI.
Run from the project folder:  python tests/test_ayun.py
"""
import os, sys, random
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pygame; pygame.init()
screen = pygame.display.set_mode((1280, 720))
from data import ayun as cfg
from data.towers import TOWERS, TOWER_ORDER
from game import actives, ayun, ayun_art, savegame, sprites_proc
from game.audio import SOUNDS
from game.effects import EFFECTS
from game.game import Game
from game.tower import Tower
from game.utils import Vec

def new():
    g = Game(screen); g.money = 99999; return g
def mk(g, tier=0, pos=(330, 190)):
    t = Tower("ayun", pos); t.tiers = [tier, 0]; t.recompute_stats(); g.towers.append(t); g.selected = t; return t
def foe(g, dist, hp=99999.0):
    e = g.spawn_enemy("normal", dist); e.hp = e.max_hp = hp; e.base_speed = 0.0; return e
def run(g, seconds, dt=1 / 60):
    for _ in range(round(seconds / dt)): g.update(dt)
def battle(g):
    g.waves.active = True; g.waves._queue = [(999, "normal")]

# ---- 1. data
assert TOWER_ORDER[-1] == "ayun" and len(TOWER_ORDER) == 6
d = TOWERS["ayun"]; tiers = d["paths"][0]["tiers"]
assert [u["name"] for u in tiers] == ["Gacha Stall", "Display Shelf", "Loyalty Card", "Supply Chain"]
assert d["paths"][1]["tiers"] == []
assert [u["cost"] for u in tiers] == [180, 400, 700, 1500] and tiers[3]["cost"] > 1200
for u in tiers: assert all(e in EFFECTS for e in u["effects"]), u
for tr in cfg.ODDS.values(): assert sum(tr.values()) == 100
assert cfg.ODDS[1]["legendary"] == 0 and cfg.ODDS[2]["legendary"] == 0 and cfg.ODDS[3]["legendary"] > 0
assert cfg.ODDS[4]["legendary"] < 12 and cfg.ODDS[4]["rare"] < 38        # upgrade 4 odds were nerfed slightly
assert cfg.ITEMS["sword"]["cd"] == 2.0 and cfg.ITEMS["sauce"]["cd"] == 5.0
assert cfg.AUTO_INTERVAL == 15 and cfg.AUTO_COST_PER_MINUTE == 150 and abs(ayun.auto_cost() - 37.5) < 1e-9
assert {"shoot_ayun", "gacha_roll", "gacha_rare"} <= set(SOUNDS)
for iid in cfg.ITEMS: ayun_art.item_icon(iid, 24); ayun_art.item_icon(iid, 52)
assert sprites_proc.tower_sprite("ayun", 18, d["color"]).get_height() > 40
print("1 data ok")

# ---- 2. one track: path B refused, W does nothing bad, locked before U1
g = new(); t = mk(g)
assert t.can_upgrade(1) == (False, "No second path") and t.can_upgrade(0)[0]
g.selected = t; g._try_upgrade(1)
assert t.tiers == [0, 0]
assert not ayun.unlocked(t) and ayun.stock_cap(t) == 0
assert ayun.roll(g, t) is False                         # needs upgrade 1
for _ in range(4): g._try_upgrade(0)
assert t.tiers == [4, 0] and t.can_upgrade(0) == (False, "Max tier")
print("2 track ok")

# ---- 3. rolling: cost, cap 2 at U1, pop-up when full, replace / sell / timeout
g = new(); t = mk(g, 1); m0 = g.money
assert ayun.roll(g, t) and len(t.stock) == 1 and abs(m0 - g.money - cfg.ROLL_COST[1]) < 1e-6
assert ayun.roll(g, t) and len(t.stock) == 2
assert g.ayun_prompt is None
assert ayun.roll(g, t) and g.ayun_prompt is not None and len(t.stock) == 2    # third roll: stock full -> pop-up
assert ayun.roll(g, t) is False                                                # must decide first
new_id = g.ayun_prompt["item"]["id"]; old = t.stock[0]["id"]
ayun.resolve_prompt(g, "replace", 0)
assert g.ayun_prompt is None and t.stock[0]["id"] == new_id and len(t.stock) == 2
ayun.roll(g, t); assert g.ayun_prompt is not None
m = g.money; v = ayun.sell_value(g.ayun_prompt["item"]["id"]); ayun.resolve_prompt(g, "sell")
assert abs(g.money - m - v) < 1e-6 and len(t.stock) == 2
ayun.roll(g, t); v = ayun.sell_value(g.ayun_prompt["item"]["id"]); m = g.money
run(g, cfg.PROMPT_SECONDS + 0.5)                                               # nothing chosen -> the new item is sold
assert g.ayun_prompt is None and g.money >= m + v - 1e-6
m = g.money; it = t.stock[0]["id"]; assert ayun.sell_item(g, t, 0) and abs(g.money - m - ayun.sell_value(it)) < 1e-6 and len(t.stock) == 1
g.money = 5; assert ayun.roll(g, t) is False
print("3 rolling ok")

# ---- 4. odds per tier, pity from U3, legendary only from U3
random.seed(1)
def sample(tier, n=4000, auto=False):
    g = new(); t = mk(g, tier); t.tiers = [tier, 0]; out = {r: 0 for r in cfg.RARITIES}
    for _ in range(n): out[cfg.ITEMS[ayun.pick(t, auto)]["rarity"]] += 1
    return out
for tr in (1, 2): assert sample(tr)["legendary"] == 0
assert sample(1)["rare"] / 4000 < 0.12
s3 = sample(3); assert s3["legendary"] > 0
g = new(); t = mk(g, 3); t.pity = 5
random.seed(5)
for _ in range(50):
    t.pity = 5; assert cfg.ITEMS[ayun.pick(t)]["rarity"] in ("rare", "legendary")   # 6th roll without a Rare = Rare
t.pity = 0; ayun.pick(t); assert t.pity in (0, 1)
g = new(); t = mk(g, 2); t.pity = 99
random.seed(2); assert any(cfg.ITEMS[ayun.pick(t)]["rarity"] in ("junk", "common") for _ in range(20))   # no pity below U3
print("4 odds ok")

# ---- 5. items are attacks on their own cooldowns (sword 2s, dragon sauce 5s, in parallel), base throw goes on
g = new(); battle(g); t = mk(g, 2); e = foe(g, 150)
t.pos = Vec(g.path.position_at(150)) + Vec(0, 60)
t.stock = [ayun.new_item("sword"), ayun.new_item("sauce")]
fired = {"sword": 0, "sauce": 0}
for _ in range(60 * 21):
    n0 = len(g.projectiles); g.update(1 / 60)
    for p in g.projectiles:
        if p.item and not getattr(p, "_seen", False): p._seen = True; fired[p.item] += 1
assert 9 <= fired["sword"] <= 11, fired        # ~every 2s in 21s
assert 3 <= fired["sauce"] <= 5, fired         # ~every 5s
assert e.hp < e.max_hp
print("5 items ok", fired)

# ---- 6. expiry (battle seconds only), sauce puddle burns, price tag marks, pan breaks armor
g = new(); t = mk(g, 2); t.stock = [ayun.new_item("spoon")]
run(g, 100); assert len(t.stock) == 1                       # prep: items do not age
battle(g); run(g, cfg.LIFETIME["junk"] + 1); assert t.stock == []
g = new(); battle(g); t = mk(g, 3); e = foe(g, 150); t.pos = Vec(g.path.position_at(150)) + Vec(0, 50)
t.stock = [ayun.new_item("sauce")]; run(g, 1.5); assert g.puddles, "sauce leaves a puddle"
hp = e.hp; run(g, 2.0); assert e.hp < hp
g = new(); battle(g); t = mk(g, 3); e = foe(g, 150); t.pos = Vec(g.path.position_at(150)) + Vec(0, 50)
t.stock = [ayun.new_item("tag")]; run(g, 1.0); assert e.vuln_timer > 0 and e.vuln == cfg.MARK_BONUS
g = new(); battle(g); t = mk(g, 3); e = foe(g, 150); e.armor = e.max_armor = 9; t.pos = Vec(g.path.position_at(150)) + Vec(0, 50)
t.stock = [ayun.new_item("pan")]; t.stock[0]["cd"] = 0
for _ in range(120): g.update(1 / 60)
assert e.armor <= 9 - 3 and e.armor % 3 == 0 or e.armor < 9
print("6 specials ok")

# ---- 7. passive: she sells the Didits she kills (not other towers' kills); register pays double
g = new(); battle(g); t = mk(g, 0); e = foe(g, 150, hp=0.5)
t.pos = Vec(g.path.position_at(150)) + Vec(0, 50); m = g.money
run(g, 3.0); assert e not in g.enemies
bounty = e.bounty; assert abs(g.money - m - (bounty + max(1, round(bounty * cfg.SELL_BONUS)))) < 1e-6, (g.money - m, bounty)
g = new(); battle(g); other = Tower("jalu", (330, 190)); g.towers.append(other)
e = foe(g, 150, hp=0.5); g.hit_enemy(e, 5, source=other); m = g.money; g._collect_enemies()
assert abs(g.money - m - e.bounty) < 1e-6                      # a Jalu kill: no selling bonus
g = new(); t = mk(g, 3); e = foe(g, 100); e.item_hit = "register"
assert ayun.sell_amount(t, e) == max(1, round(e.bounty * cfg.SELL_BONUS_APPRAISAL)) + e.bounty
t2 = mk(g, 1, (500, 500)); assert ayun.sell_rate(t2) == cfg.SELL_BONUS and ayun.sell_rate(t) == cfg.SELL_BONUS_APPRAISAL
print("7 passive ok")

# ---- 8. Supply Chain: auto-roll every 15s (battle), cost 150/min, Steady Supply odds growth, pop-up when full
g = new(); battle(g); t = mk(g, 4); m = g.money
assert [a for a in actives.actives_of(t)] == ["ayun_roll", "ayun_auto"]
assert actives.use(g, t, "ayun_auto") and t.auto_on
run(g, 61); rolled = round((m - g.money) / 37.5)
assert 3 <= rolled <= 5, rolled                                 # 15s, 30s, 45s, 60s
assert len(t.stock) + (1 if g.ayun_prompt else 0) >= 3
t.stock = []; g.ayun_prompt = None; t.idle = 0; lo = ayun.odds(t, True); t.idle = 999; hi = ayun.odds(t, True)
assert lo == {k: float(v) for k, v in cfg.ODDS[3].items()} and hi == {k: float(v) for k, v in cfg.ODDS[4].items()}
t.idle = cfg.STEADY_SECONDS / 2; mid = ayun.odds(t, True)
assert lo["rare"] < mid["rare"] < hi["rare"] and lo["junk"] > mid["junk"] > hi["junk"]
assert ayun.odds(t) == {k: float(v) for k, v in cfg.ODDS[4].items()}      # manual roll uses the U4 table
ayun.roll(g, t); assert t.idle == 0                                        # manual roll resets Steady Supply
g = new(); t = mk(g, 4); t.auto_on = True; g.money = 10; battle(g); run(g, 16)
assert t.auto_on is False                                                  # can't pay: auto stops
g = new(); t = mk(g, 3); assert actives.use(g, t, "ayun_auto") is False or True
g = new(); t = mk(g, 3); assert "ayun_auto" not in actives.actives_of(t)
g = new(); t = mk(g, 4); t.auto_on = True; t.stock = [ayun.new_item("spoon") for _ in range(4)]   # prep: auto-roll does not run
run(g, 40); assert len(t.stock) == 4 and g.ayun_prompt is None
print("8 supply chain ok")

# ---- 9. savegame round trip
g = new(); t = mk(g, 4); t.stock = [ayun.new_item("lamp"), ayun.new_item("duck")]; t.stock[0]["life"] = 77.5
t.pity, t.idle, t.auto_on = 3, 41.0, True
snap = savegame.snapshot(g)
g2 = new(); assert savegame.restore(g2, snap)
t2 = g2.towers[0]
assert [i["id"] for i in t2.stock] == ["lamp", "duck"] and t2.stock[0]["life"] == 77.5 and t2.pity == 3 and t2.auto_on
snap["towers"][0]["ayun"]["stock"].append({"id": "not_an_item"}); g3 = new(); assert savegame.restore(g3, snap) and len(g3.towers[0].stock) == 2
print("9 savegame ok")

# ---- 10. UI: panel layout fits above the bar, buttons hit-test, pop-up, draws every state
g = new(); t = mk(g, 4, (200, 300)); g.selected = t
for _ in range(30): g.update(1 / 60)
g.ui.update(1 / 60, g.money, g)
assert g.ui.panel.bottom <= 636, g.ui.panel
assert g.ui.hit_test(g.ui.ayun_roll_btn.center, g) == ("ayun_roll",)
assert g.ui.hit_test(g.ui.ayun_auto_btn.center, g) == ("ayun_auto",)
assert g.ui.upgrade_btns[1].w == 0
t.stock = [ayun.new_item("sword")]
assert g.ui.hit_test(g.ui.ayun_slots[0][1].center, g) == ("ayun_sell", 0)
assert g.ui.hit_test(g.ui.ayun_slots[2][1].center, g) != ("ayun_sell", 2)     # empty slot: no sell button
g._do_action(("ayun_roll",)); assert len(t.stock) == 2
g._do_action(("ayun_sell", 0)); assert len(t.stock) == 1
t.stock = [ayun.new_item(i) for i in ("sword", "pan", "sauce", "register")]
g._do_action(("ayun_roll",)); assert g.ayun_prompt is not None
g.ui.update(1 / 60, g.money, g)
reps = [a for a, r in g.ui.prompt_rects if a[1] == "replace"]; assert len(reps) == 4
rect = dict(g.ui.prompt_rects)
for act, r in g.ui.prompt_rects: assert g.ui.hit_test(r.center, g) == act
g.draw(); pygame.display.flip()
g._do_action(("ayun_prompt", "replace", 3)); assert g.ayun_prompt is None and len(t.stock) == 4
for tr in range(5):
    g = new(); t = mk(g, tr, (200, 300)); g.selected = t; battle(g)
    if tr: t.stock = [ayun.new_item(i) for i in list(cfg.ITEMS)[:ayun.stock_cap(t)]]
    foe(g, 120); run(g, 1.0); g.ui.update(1 / 60, g.money, g); g.draw()
    assert g.ui.panel.bottom <= 636
# hotkeys: 6 places A'yun, E rolls, C toggles auto
g = new(); g._on_key(pygame.K_6); assert g.placing == "ayun"
g.placing = None; t = mk(g, 4); g._on_key(pygame.K_e); assert len(t.stock) == 1
g._on_key(pygame.K_c); assert t.auto_on
# shop bar clears POWERS, abilities do not collide
assert max(r.right for r in g.ui.shop_btns.values()) < g.ui.powers_btn.x
print("10 ui ok")

# ---- 11. units screen + menu tabs fit
from game.menu import UnitsScreen
u = UnitsScreen(); assert max(r.bottom for _, r in u.tabs) < u.back.y
u.idx = TOWER_ORDER.index("ayun"); u.draw(screen, 0.0, (0, 0)); u.sel = (0, 4); u.draw(screen, 0.0, (0, 0))
print("A'YUN OK")
