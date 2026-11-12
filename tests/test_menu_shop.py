"""Headless: profile storage, shop purchases, permanent perks, Didit Rupiah rewards, in-game items, menu screens.
Run: python tests/test_menu_shop.py"""
import os, sys, json
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pygame; pygame.init(); screen = pygame.display.set_mode((1280, 720))
from game.game import Game, State
from game import profile as P, powers, menu, savegame
from game.profile import Profile
from data.settings import START_MONEY, START_STASH_HP, COINS_PER_WAVE, COINS_WIN_BONUS
from data.shop import PERMANENT, ITEMS, PERM_ORDER, ITEM_ORDER
from data.towers import TOWERS

P.PATH = "/tmp/_profile_test.json"
savegame.PATH = "/tmp/_save_test2.json"
for f in (P.PATH, savegame.PATH):
    if os.path.exists(f): os.remove(f)

# ---- profile: purchases, save / load, bad data
p = Profile.load(); assert p.coins == 0 and p.perm == {} and p.persist
p.coins = 500
assert p.buy_perm("allowance") == "ok" and p.coins == 420 and p.level("allowance") == 1
assert p.bonus("allowance") == 60
p.coins = 0; assert p.buy_perm("crate") == "poor" and p.buy_item("cash_drop") == "poor"
p.coins = 99999
for _ in range(10): p.buy_perm("haggler")
assert p.level("haggler") == 3 and p.buy_perm("haggler") == "maxed" and p.next_cost("haggler") is None
assert p.buy_item("cash_drop") == "ok" and p.owned("cash_drop") == 1
p.stock["cash_drop"] = 99; assert p.buy_item("cash_drop") == "full"
p.stock["cash_drop"] = 1; p.record_run(40, True, 12); p.save()
q = Profile.load()
assert (q.coins, q.perm, q.stock, q.runs, q.wins, q.best_wave) == (p.coins, p.perm, p.stock, 1, 1, 12)
open(P.PATH, "w").write(json.dumps({"version": 1, "coins": -5, "perm": {"nope": 3, "crate": 99}, "stock": {"x": 1, "cash_drop": 5000}}))
r = Profile.load(); assert r.coins == 0 and r.perm == {"crate": 5} and r.stock == {"cash_drop": 99}
open(P.PATH, "w").write("{broken"); assert Profile.load().coins == 0
assert not Profile().save()   # blank profile never touches the disk
print("profile OK")

# ---- a default Game has no perks and behaves as before
g = Game(screen)
assert g.money == START_MONEY and g.stash_hp == g.stash_max == START_STASH_HP and g.ball_knowledge == 0
print("no perks = old behaviour OK")

# ---- perks
pr = Profile(); pr.perm = {"allowance": 2, "crate": 3, "notes": 1, "discount": 5, "wallet": 5, "tools": 5, "haggler": 3, "booster": 2}
g = Game(screen, pr)
assert g.money == START_MONEY + 120 and g.stash_hp == g.stash_max == START_STASH_HP + 30 and g.ball_knowledge == 10
g.money = 5000; g.placing = "zizi"; g._try_place((300, 188)); t = g.towers[0]
assert t.sell_value == int(t.spent * 0.82)
up = t.next_upgrade(0); assert g.upgrade_cost(t, up) == round(up["cost"] * 0.85)
g.waves.number = 1; e = g.spawn_enemy("normal")
g2 = Game(screen); g2.waves.number = 1; e2 = g2.spawn_enemy("normal")
assert e.bounty >= round(e2.bounty * 1.15), (e.bounty, e2.bounty)
assert abs(g.damage_multiplier(e) - 1.15) < 1e-9 and abs(g2.damage_multiplier(e2) - 1.0) < 1e-9
g.reset(); assert g.money == START_MONEY + 120   # perks re-applied on every new run
print("perks OK")

# ---- run rewards
g = Game(screen, Profile()); g.waves.number = 6; g.stash_hp = 1
g.spawn_enemy("normal").reached_end = True; g._collect_enemies()
assert g.state == State.LOST and g.run_reward["coins"] == 5 * COINS_PER_WAVE and g.profile.coins == 5 * COINS_PER_WAVE
g._end_run(False); assert g.profile.coins == 5 * COINS_PER_WAVE   # paid once
assert g.profile.runs == 1 and g.profile.best_wave == 5
g.reset(); assert g.run_reward is None and g.state == State.PLAYING
g.waves.number = g.waves.total - 1; g._start_battle(); g.enemies.clear(); g._finish_wave()
assert g.state == State.WON and g.run_reward["coins"] == g.waves.total * COINS_PER_WAVE + COINS_WIN_BONUS and g.run_reward["win"]
pr = Profile(); pr.perm = {"booster": 3}; g = Game(screen, pr); g.waves.number = 11; g.stash_hp = 1
g.spawn_enemy("normal").reached_end = True; g._collect_enemies()
assert g.run_reward["coins"] == round(10 * COINS_PER_WAVE * 1.3), g.run_reward
# continued run only pays for the waves it played
g = Game(screen, Profile()); g.money = 3000; g.placing = "jalu"; g._try_place((500, 188))
g.waves.number = 3; g._start_battle(); g.enemies.clear(); g._finish_wave()   # wave 4 cleared -> autosave? (every 3rd)
g.waves.number = 5; g._start_battle(); g.enemies.clear(); g._finish_wave()
g.waves.number = 8; g._start_battle(); g.enemies.clear(); g._finish_wave()   # wave 9 cleared -> saved
assert savegame.read()["wave"] == 9
g2 = Game(screen, Profile()); assert g2.load_save() and g2.run_start_wave == 9
g2.waves.number = 12; g2.stash_hp = 1; g2.spawn_enemy("normal").reached_end = True; g2._collect_enemies()
assert g2.run_reward["waves"] == 2 and g2.run_reward["coins"] == 2 * COINS_PER_WAVE, g2.run_reward
print("rewards OK")

# ---- in-game items
pr = Profile(); pr.stock = {k: 5 for k in ITEM_ORDER}; g = Game(screen, pr)
ok, why = powers.status(g, "stash_patch"); assert not ok and "full" in why
ok, why = powers.status(g, "freeze_bomb"); assert not ok
ok, why = powers.status(g, "espresso"); assert not ok
m0 = g.money; assert powers.use(g, "cash_drop") and g.money == m0 + 400 and pr.owned("cash_drop") == 4
for _ in range(5): powers.use(g, "cash_drop")
assert g.powers_used["cash_drop"] == 3 and pr.owned("cash_drop") == 2, "per-run limit"
g.stash_hp = 50; assert powers.use(g, "stash_patch") and g.stash_hp == 75
g.stash_hp = 90; powers.use(g, "stash_patch"); assert g.stash_hp == g.stash_max
k0 = g.ball_knowledge; powers.use(g, "ball_scroll"); assert g.ball_knowledge == k0 + 30
g.money = 3000; g.placing = "jalu"; g._try_place((500, 188)); jalu = g.towers[0]
assert powers.use(g, "espresso") and jalu.haste[0] > 11 and jalu.haste[1] == 0.5
g.waves.number = 1; g._start_battle(); a = g.spawn_enemy("normal"); b = g.spawn_enemy("boss")
assert powers.use(g, "freeze_bomb") and a.stun_timer > 3 and b.stun_timer == 0 and b.slow_timer > 0
# insta jalu: placement only consumes the item when the tower is really placed
pr.stock["insta_jalu"] = 2; g.enemies.clear(); g.waves.finish(); money = g.money
assert powers.use(g, "insta_jalu") and g.placing == "jalu" and g.insta and pr.owned("insta_jalu") == 2
ok, reason = g.placement_check("jalu", (500, 188)); assert not ok   # overlaps the first Jalu
g.money = 0; ok, _ = g.placement_check("jalu", (700, 188)); assert ok, "free even with $0"
g._try_place((700, 188)); ins = g.towers[-1]
assert ins.tiers == [2, 0] and ins.spent == 0 and ins.sell_value == 0 and g.money == 0
assert pr.owned("insta_jalu") == 1 and g.insta is None and g.powers_used["insta_jalu"] == 1
powers.use(g, "insta_jalu"); g._choose_shop("jalu"); assert g.insta is None   # a normal card cancels it
pr.stock["insta_jalu"] = 1; g.insta = None
print("items OK")

# ---- leaving to the menu: options button, end-screen buttons
g = Game(screen, Profile()); g.options_open = True
g.ui.layout(g); g.ui._build_options_layout()
rect = dict(g.ui.opt_rows)["menu"]; act = g.ui.hit_test(rect.center, g); assert act == ("opt", "menu", 0), act
g._do_action(act); assert g.exit_to_menu and not g.options_open
g = Game(screen, Profile()); g.waves.number = 3; g.stash_hp = 1; g.spawn_enemy("normal").reached_end = True; g._collect_enemies()
g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(800, 550), button=1)); assert g.exit_to_menu
g.exit_to_menu = False; g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(400, 550), button=1))
assert g.state == State.PLAYING and not g.exit_to_menu   # PLAY AGAIN
g.draw(); g.options_open = True; g.draw()
print("menu exits OK")

# ---- the menu screens
pr = Profile(); pr.coins = 700
mm = menu.MainMenu(pr, None)
assert mm.primary == "play"
for key, label, r, x, y in mm.circles: assert mm.click((x, y)) == key
assert mm.click((640, 358)) is None and mm.click((30, 30)) == "fullscreen"
mm = menu.MainMenu(pr, {"wave": 5, "money": 100, "towers": 3}); assert mm.primary == "continue" and mm.click((640, 358)) == "continue"
mm.draw(screen, 0.5, (0, 0))
un = menu.UnitsScreen()
for i, (k, rect) in enumerate(un.tabs):
    assert un.click(rect.center) is None and un.kind == k
    un.draw(screen, 0.5, (0, 0))
    for (path, tier), card in un._live_cards().items():
        un.draw(screen, 0.5, card.center)             # hover preview of every tier's costume
        un.click(card.center); assert un.sel == (path, tier + 1)
        un.click(card.center); assert un.sel is None
assert un.click(un.back.center) == "back"
dv = menu.DevelopersScreen(); dv.draw(screen, 0.5, (0, 0)); assert dv.click(dv.back.center) == "back"
sh = menu.ShopScreen(pr)
sh.draw(screen, 0.5, (0, 0))
card = sh._card_rect(0); sh.click(card.center)       # Bigger Allowance, 80 coins
assert pr.coins == 620 and pr.level("allowance") == 1
pr.coins = 5; sh.click(card.center); assert pr.coins == 5 and pr.level("allowance") == 1
sh.click(sh.tabs["items"].center); assert sh.tab == "items"
pr.coins = 1000; sh.click(sh._card_rect(1).center); assert pr.owned("stash_patch") == 1 and pr.coins == 950
sh.draw(screen, 0.5, sh._card_rect(2).center)
assert sh.click(sh.back.center) == "back"
for pid in PERM_ORDER: assert len(PERMANENT[pid]["costs"]) >= 3
print("menu screens OK")
print("ALL OK")
