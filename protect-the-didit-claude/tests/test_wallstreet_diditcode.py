"""Headless: Didit Rupiah banknote, dark enemy Didits, Didit Wallstreet (market, kas.txt, trading, screen) and
Romli's DiditCode ability. Run: python tests/test_wallstreet_diditcode.py"""
import os, sys, random, json
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pygame; pygame.init(); screen = pygame.display.set_mode((1280, 720))
from game.game import Game, State
from game import profile as P, market as M, menu, currency, diditcode, actives, savegame, sprites_proc
from game.profile import Profile
from data import market as cfg
from data.diditcode import PUZZLES
from data.enemies import ENEMIES
from data.settings import (DIDITCODE_COOLDOWN, DIDITCODE_MAX_PER_PREP, DIDITCODE_REWARD_BASE, DIDITCODE_REWARD_PER_WAVE,
                           DIDITCODE_STRIKES)

P.PATH = "/tmp/_profile_ws.json"; savegame.PATH = "/tmp/_save_ws.json"
for f in (P.PATH, savegame.PATH):
    if os.path.exists(f): os.remove(f)

# ---- enemies are black / dark purple, the original Didit is white
for k, d in ENEMIES.items():
    if k not in ("trojan", "trojan_trojan"):
        assert sum(d["color"]) < 330 and d["color"][2] >= d["color"][0], (k, d["color"])   # dark, purple-ish or black
        assert sprites_proc.is_dark(d["color"])
print("dark enemies OK")

# ---- banknote
assert currency.note(60).get_size()[0] == 60 and currency.fmt(1500000) == "1.500.000" and currency.GREEN[1] > currency.GREEN[0]
print("banknote OK")

# ---- kas.txt
assert M.read_kas() == 1_500_000, M.read_kas()
tmp = "/tmp/_kas_test.txt"
M.KAS_PATHS = (tmp,)
open(tmp, "w").write("2.250.000\n"); assert M.read_kas() == 2_250_000
open(tmp, "w").write("junk"); assert M.read_kas() == cfg.KAS_DEFAULT
os.remove(tmp); assert M.read_kas() == cfg.KAS_DEFAULT
open(tmp, "w").write("1500000")
m = M.Market(random.Random(3), kas=1_500_000)
assert m.prices["IUKXJ"] == 30.0 and m.price("IUKXJ") == 30
open(tmp, "w").write("1800000"); assert m.sync_kas(M.read_kas()) and m.price("IUKXJ") == 36
print("kas.txt OK")

# ---- market moves
assert set(m.prices) == set(cfg.ORDER) == {"IHSD", "ROC", "IUKXJ"}
assert any(h["stock"] == "IHSD" for h in m.headlines) and any(h["stock"] == "ROC" for h in m.headlines)
assert all(0 <= h["truth"] <= 1 for h in m.headlines)
rng = random.Random(7)
m = M.Market(rng, kas=1_500_000)
for i in range(300):
    kas = 1_500_000 if i < 100 else 1_650_000
    m.advance(kas, {"won": i % 2 == 0, "wave": i % 30})
    for s in ("IHSD", "ROC"):
        assert cfg.STOCKS[s]["floor"] <= m.prices[s] <= cfg.STOCKS[s]["cap"]
    assert len(m.history["ROC"]) <= cfg.HISTORY_LEN and len({h["text"] for h in m.headlines}) == len(m.headlines)
assert m.price("IUKXJ") == 33 and m.tick == 300
m2 = M.Market.from_dict(json.loads(json.dumps(m.to_dict())))
assert m2.tick == 300 and [h["text"] for h in m2.headlines] == [h["text"] for h in m.headlines] and abs(m2.prices["ROC"] - m.prices["ROC"]) < 1e-3
for bad in (None, "x", {}, {"prices": {"IHSD": "a"}}, {"tick": 2, "prices": {"IHSD": 1}}):
    assert M.Market.from_dict(bad).tick == 0
# a reliable "good news" headline raises the stock on average
ups = 0
for seed in range(200):
    mm = M.Market(random.Random(seed), kas=1_500_000)
    mm.headlines = [{"text": "t", "stock": "ROC", "effect": 0.10, "domain": "diditpost.id", "truth": 0.88}]
    before = mm.prices["ROC"]; mm.advance(); ups += mm.prices["ROC"] > before
assert ups > 140, ups
print("market OK")

# ---- profile: trading, fee, caps, persistence, record_run
M.KAS_PATHS = (tmp,); open(tmp, "w").write("1500000")
p = Profile.load(); p.coins = 1000
price = p.market.price("ROC")
assert p.buy_stock("ROC", 10) == "ok" and p.coins == 1000 - 10 * price and p.shares("ROC") == 10 and p.basis["ROC"] == 10 * price
assert p.buy_stock("ROC", 10 ** 6) in ("cap", "poor") and p.buy_stock("NOPE", 1) == "bad" and p.buy_stock("ROC", 0) == "bad"
p.coins = 0; assert p.buy_stock("IHSD", 1) == "poor"
got = p.sell_stock("ROC", 4); gross = 4 * price
assert got == gross - int(gross * cfg.SELL_FEE) and p.shares("ROC") == 6 and p.coins == got
assert p.sell_stock("IHSD", 5) == 0
p.sell_stock("ROC", 99); assert p.shares("ROC") == 0 and "ROC" not in p.basis
p.coins = 500; p.buy_stock("IUKXJ", 3); tick0 = p.market.tick
p.record_run(40, True, 12)
assert p.market.tick == tick0 + 1 and p.coins >= 40
assert any("Front page" in h["text"] for h in p.market.headlines)
q = Profile.load(); assert q.shares("IUKXJ") == 3 and q.market.tick == tick0 + 1 and q.coins == p.coins and q.net_worth() == p.net_worth()
open(P.PATH, "w").write(json.dumps({"version": 1, "coins": 5, "market": "broken", "holdings": {"ROC": 9999, "x": 1}, "basis": {"ROC": -3}}))
r = Profile.load(); assert r.coins == 5 and r.shares("ROC") == cfg.MAX_HOLD and "x" not in r.holdings and r.market.tick == 0 and r.basis["ROC"] == 0
open(P.PATH, "w").write(json.dumps({"version": 1, "coins": 7}))
assert Profile.load().coins == 7   # an old profile.json (before Wallstreet) still loads
print("profile trading OK")

# ---- the game pays through record_run and the market moves once
pr = Profile(); g = Game(screen, pr); g.waves.number = 4; g.stash_hp = 1
g.spawn_enemy("normal").reached_end = True; g._collect_enemies()
assert g.state == State.LOST and pr.market.tick == 1
print("market moves after a run OK")

# ---- Wallstreet screen
pr = Profile(); pr.coins = 500
ws = menu.WallstreetScreen(pr)
ws.draw(screen, 0.0, (0, 0))
assert len(ws.btns) == 12 and ws.click(ws.back.center) == "back"
buy1 = [b for b in ws.btns if b[1] == "ROC" and b[2] == "buy" and b[3] == 1][0][0]
ws.click(buy1.center); assert pr.shares("ROC") == 1
sell_all = [b for b in ws.btns if b[1] == "ROC" and b[2] == "sell" and b[3] == 0][0][0]
ws.click(sell_all.center); assert pr.shares("ROC") == 0
pr.coins = 0; ws.click(buy1.center); assert pr.shares("ROC") == 0   # poor
ws.draw(screen, 0.1, (10, 10))
mm = menu.MainMenu(pr, None); assert mm.click((495, 624)) == "wallstreet" and mm.click((640, 614)) == "play"
mm.draw(screen, 0.0, (0, 0))
print("wallstreet screen OK")

# ---- DiditCode puzzles are well formed
for pz in PUZZLES:
    assert 0 <= pz["bug"] < len(pz["code"]) and len(pz["options"]) == 3 and len(set(pz["options"])) == 3 and pz["why"], pz["title"]
    assert pz["options"][0].strip() != pz["code"][pz["bug"]].strip(), pz["title"]
# ---- DiditCode flow
dc = diditcode.DiditCode(5, random.Random(1), PUZZLES[0])
assert dc.reward == DIDITCODE_REWARD_BASE + 5 * DIDITCODE_REWARD_PER_WAVE and dc.stage == "find"
wrong_line = [i for i in range(len(dc.code)) if i != dc.bug][0]
assert dc.click(dc._row(wrong_line).center) == "wrong" and dc.strikes == 1 and dc.stage == "find"
assert dc.click(dc._row(wrong_line).center) is None   # already struck
assert dc.click(dc._row(dc.bug).center) is None and dc.stage == "fix"
good = dc.options.index(dc.fix); bad = [i for i in range(3) if i != good][0]
assert dc.click(diditcode.OPT_RECTS[bad].center) == "failed" and dc.stage == "lost"   # 2nd strike
assert dc.click(diditcode.DONE.center) == "close"
dc = diditcode.DiditCode(1, random.Random(2), PUZZLES[1])
dc.click(dc._row(dc.bug).center); assert dc.click(diditcode.OPT_RECTS[dc.options.index(dc.fix)].center) == "solved" and dc.stage == "won"
dc.draw(screen, (0, 0))
assert dc.key(pygame.K_ESCAPE) == "close" and diditcode.DiditCode(1).key(pygame.K_ESCAPE) == "cancel"
for pz in PUZZLES:   # every puzzle can be drawn in every stage
    d = diditcode.DiditCode(3, puzzle=pz); d.draw(screen, (0, 0)); d.click(d._row(d.bug).center); d.draw(screen, (500, 500))
print("diditcode flow OK")

# ---- Romli's ability inside the game
g = Game(screen, Profile()); g.money = 5000
g.placing = "romli"; g._try_place((300, 188)); romli = g.towers[-1]
g.placing = "jalu"; g._try_place((400, 188)); jalu = g.towers[-1]
assert "diditcode" in actives.actives_of(romli) and "diditcode" not in actives.actives_of(jalu)
g.selected = romli; g.ui.layout(g)
assert g.ui.ability_rects and g.ui.ability_rects[0][0] == "diditcode"
g.draw()
g.waves.number = 4
money0 = g.money
g.use_ability(0)
assert g.code is not None and romli.active_cd["diditcode"] == DIDITCODE_COOLDOWN and g.code_uses == 1
# NOT modal and NOT paused: the game keeps running; only clicks on the panel belong to DiditCode
t0 = g.time; g.update(0.016); g.draw(); assert g.time > t0
g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(900, 100), button=1)); assert g.selected is romli   # on the panel: not a map click
g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(200, 560), button=1)); assert g.selected is None    # left half: the map still works
g.selected = romli
g.code.click(diditcode.MINI.center); assert g.code.collapsed and g.code.wants(diditcode.TAB.center) and not g.code.wants(diditcode.PANEL.center)
g.draw(); g.code.click(diditcode.TAB.center); assert not g.code.collapsed
code = g.code
g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=code._row(code.bug).center, button=1))
g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=diditcode.OPT_RECTS[code.options.index(code.fix)].center, button=1))
assert g.money == money0 + diditcode.reward_for(5), (g.money, money0)
g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=diditcode.DONE.center, button=1)); assert g.code is None
ok, why = actives.can_use(g, romli, "diditcode"); assert not ok and "recharging" in why
romli.active_cd["diditcode"] = 0; g.use_ability(0)              # second attempt: cancel before clicking = free
g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode="", scancode=0))
assert g.code is None and g.code_uses == 1 and romli.active_cd["diditcode"] == 0
g.use_ability(0); c2 = g.code; c2.click(c2._row([i for i in range(len(c2.code)) if i != c2.bug][0]).center)   # a strike was made
g.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode="", scancode=0))
assert g.code is None and g.code_uses == 2 and romli.active_cd["diditcode"] > 0   # cancel after trying still costs
romli.active_cd["diditcode"] = 0
ok, why = actives.can_use(g, romli, "diditcode"); assert not ok and "No more" in why and DIDITCODE_MAX_PER_PREP == 2
# a wave start closes an open DiditCode (no reward); in battle the ability is not allowed; next preparation: allowed again
g.code_uses = 0; romli.active_cd["diditcode"] = 0; g.use_ability(0); assert g.code is not None
money_before = g.money; g._start_battle(); assert g.code is None and g.money == money_before
ok, why = actives.can_use(g, romli, "diditcode"); assert not ok and "preparation" in why
g.enemies.clear(); g._finish_wave()
romli.active_cd["diditcode"] = 0
assert g.code_uses == 0 and actives.can_use(g, romli, "diditcode")[0]
g.draw()
print("romli DiditCode OK")
# every puzzle: the buggy line and the correct fix start with the same token (the fix replaces THAT line)
for pz in PUZZLES:
    bug_line, fix = pz["code"][pz["bug"]].strip(), pz["options"][0].strip()
    if pz["title"] != "Hungry Didits":   # (WHERE -> HAVING is the one fix that changes the first word)
        assert bug_line.split()[0].rstrip("(") == fix.split()[0].rstrip("("), (pz["title"], bug_line, fix)
print("puzzle bug lines OK")

print("ALL OK")
