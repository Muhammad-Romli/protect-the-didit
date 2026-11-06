# Changelog

## 2026-11-06 - main menu, UNITS, SHOP, Snack Coins
- **Main menu (BTD6-style):** round buttons UNITS / SHOP / PLAY / DEVELOPERS / EXIT, CONTINUE button when a save exists, fullscreen button top-left, Snack Coins top-right. Code: `game/menu.py` (`MainMenu`, `UnitsScreen`, `ShopScreen`, `DevelopersScreen`), flow in `main.py` (`_menu` -> `_load` once -> `_play` -> back to the menu). The old `TitleMenu` is gone; the loading scene's track moved up (`title.TRACK`).
- **Snack Coins:** paid when a run ends (win or lose): `COINS_PER_WAVE` per wave cleared in that run + `COINS_WIN_BONUS` for a win (`data/settings.py`). A CONTINUEd run only pays for the waves it played. Quitting to the menu pays nothing. Stored in the profile (`game/profile.py`: `profile.json`, or localStorage in the browser), separate from the autosave.
- **UNITS:** portrait (hover/click a tier to see its costume), short description, base stats and both upgrade paths with prices. Names/prices/descriptions come from `data/towers.py`; blurbs in `data/units_info.py`.
- **SHOP (A'yun):** `data/shop.py`. PERMANENT (leveled): Bigger Allowance, Sturdy Crate, Friendly Discount, Lucky Wallet, Sharp Tools, Haggler's Gloves, Study Notes, Coin Booster. IN-GAME (one use, per-run limits): Cash Drop, Stash Patch, Freeze Bomb, Espresso Shot, Ball Knowledge Scroll, Insta-Jalu. Perk hooks are in `game/game.py` (`reset`, `upgrade_cost`, `damage_multiplier`, `spawn_enemy`, `sell_refund`, `_end_run`); item effects in `game/powers.py`; art in `game/shopkeeper.py` and `game/shop_icons.py`.
- **In game:** POWERS button above the bottom bar (opens the item list); options panel got a MENU button; the win/lose screen shows the coins earned with PLAY AGAIN / MAIN MENU buttons (mouse and touch).
- `Game(screen, profile=None)`: no profile = a blank, never-saved one, so tests are not affected by a real `profile.json`.
- DEVELOPERS is empty on purpose.
- Test: `tests/test_menu_shop.py`.

## 2026-11-02 - feedback pass
- **Look:** Romli: short messy hair (was wavy), now holds a stack of cash (base / Farm-Business path) or a laptop (Programmer path) instead of the fly swatter. Zizi: short hair, no beanie, no long back hair; she holds a book (Recitation path) or a pillow (Sloth path), the prayer beads stay for the base tower.
- **Bima formula box:** real caret and selection: arrows, Home/End, Shift+arrows, double-click = select all, drag to select, Ctrl+A/C/X/V, Delete, key repeat while typing. New **AUTO** button (Graph Lv2+): aims at the first Didit in reach and fires, no typing or maths.
- **Balance:** Mark T2 "Viltrumite Strength": knockback 12 -> 8 px, at most once per 2s per Didit (`KNOCKBACK_INTERVAL`), damage bonus +1 -> +0.5. Before, 3 punches/s pinned slow Didits in place and one Mark T2 alone cleared 40/40 tanky Didits.
- **Performance:** range circles are cached, Bima's axis overlay blits only its bounding box (about 20% less frame time in a headless heavy-battle profile).
- **Pause:** the browser build no longer auto-pauses on window focus loss (desktop still does). Unexpected errors now show on screen instead of freezing.
- Tests: `tests/test_editing_balance.py`; `tests/test_touch.py` fixed (Bima now starts with the formula "x").


## 2026-10-31: phone support (NOT run: no pygame / phone in the session)
- `game/touch.py` + `data/touch.py`: touch mode (auto-detected), ghost + OK / cancel placement, same for aimed abilities, drag a card onto the map, bigger tower pick radius, formula keypad for Bima Graph, tap to resume, PLAY AGAIN button, mouse_pos parked off-screen (no stuck hover).
- `ui.py`: `set_touch()` (72 px gear, invisible hit margins on small panel buttons, touch hint texts); `bima_ui.py`: taller console in touch mode.
- `web.py`: viewport meta, dvh sizing, "rotate your phone" overlay, first tap = fullscreen + landscape lock.
- Packaging: `tools/make_mobile_web.py` (PWA), `tools/make_icons.py`, `mobile/`, Android wrapper + `.github/workflows/android-apk.yml`. Test: `tests/test_touch.py`. Docs: `MOBILE.md`.

## 2026-10-28 (2): models pass (NOT run: no pygame in the session, only compiled)
- New `game/models.py`: costumes per upgrade path and tier (Jalu A Mark suit/mask/cape, Jalu B Loki suit/horns/cape + floating Temporal Loom, Romli A business shirt -> suit -> crown, Romli B hoodie/headphones/code screens, Zizi A shawl/halo, Zizi B pajamas/sleepy eyes/pillow, Bima A lab coat/pencil/hologram wave, Bima B orbiting shapes/laurel), held weapons (cardboard prop sword, scepter, fly swatter, prayer beads, compass), projectile models (rolled poster, magic bolt, bug, prayer-bead ring, equation spark), props (fist, loom, screen, pillow), Mark's running sprite for Sweep, fusion tower look.
- Look changes: Jalu, Romli and Bima have brown skin (Zizi unchanged). Romli's glasses removed, short wavy hair. Zizi: medium straight hair (framing the face and falling behind the shoulders, beanie kept). Bima: very short buzz cut.
- `tower_sprite(kind, radius, color, look=None)` got a `look`; Tower.draw, Projectile.draw, mark.draw_world and loading pre-warm use the models. PNG overrides in assets/sprites still win.
- Test: `tests/test_models.py`.

## 2026-10-28: Jalu path A is now Mark (Thor removed) + per-unit path lock
- Removed Thor: path, `pierce_1`, `chain_lightning`, Thunderstrike active, bolt rendering, `zap`/`thunder` sounds and their FX. (`vfx.lightning` stays: Jalu's hit sparks use it.)
- Jalu is locked to one path per unit (`Tower.is_path_locked`); locked card is greyed with "LOCKED" in the panel. Other towers unchanged.
- New Mark path (`data/mark.py` = all numbers, `game/mark.py` = logic): melee punches, knockback, rage stacks, tier 4 Sweep active with VFX/SFX. Debug `F4` = free next upgrade.
- Savegame VERSION 2 (old saves are ignored: Thor tiers would have loaded as Mark). Tests: `tests/test_mark.py`.

## 2026-10-27 (2): browser display fix, autosave, new title/loading screen (NOT run: no pygame/browser in the session)
- Browser: `web.setup_page()` injects CSS so the canvas fits the window at 16:9 WITHOUT stretching (the stock page squashed it), is scaled smoothly (`image-rendering: auto`), dark page background, no right-click menu, no arrow/space page scrolling. Fullscreen works in the browser (Options button, F11, title menu) via the Fullscreen API.
- Autosave: `game/savegame.py`. After every `SAVE_EVERY_WAVES` (3, data/settings.py) cleared wave a snapshot is written (browser: localStorage, desktop: `savegame.json`): money, knowledge, stash HP, wave number, towers incl. tiers/targeting/activity/Bima formula. A "Game saved" message shows. Winning clears the save; losing keeps the last checkpoint. Test: `tests/test_savegame.py`.
- New title menu (CONTINUE / NEW GAME / FULLSCREEN) and loading screen (a Didit walks along a cobblestone path to the Snack Stash; the path is the progress bar, rotating tips). Flow: title -> loading -> game, same on desktop and web (sounds are always built step by step now).
- Quality governor relaxed: only triggers below 25 fps for 5 s.


## 2026-10-27: Trojan look fix + first pygbag port pass (NOT run: no pygame/browser in the session)
- Trojan Didit / Trojan Trojan Didit are now **bare wood** (no white paint): wood body with grain and dark stave seams, wood-toned ears/belly/nose, darker cart and wheels. Tiny Didits in the windows stay white. `data/enemies.py` colour changed so death splinters are wood coloured too.
- Trojan wheels now **stand on the road**: the sprite is drawn raised by `sprites_proc.trojan_lift(r)` so the lowest wheel pixel sits on the path centre line (hit position unchanged). Shadow, HP bar, bubble, stun/vuln marks follow the body. Wheels roll without slipping (spin matches distance walked; before they spun 2-3x too fast).
- pygbag: `main.py` is async (desktop path unchanged), click-to-start gate + loading bar in the browser, sounds synthesized step by step (`audio.LAZY`, `Audio.build_next`), sprite pre-warm (`game/loading.py`), options saved to localStorage (`game/web.py`), fullscreen button/hints hidden in the browser, simple quality governor (Particles Low + no vignette after 2 s of frames above 25 ms).


## Checkpoint 8 (2026-10-25, third batch)
- **Bima** (Mathematician, cost 400, key 4). Graph path: Cartesian axis, typed formulas parsed by a safe custom parser (game/formula.py), curve sampling with adaptive refinement and discontinuity breaks (game/curves.py), Brain Energy cost by arc length, preview, FIRE, direction, patterns, miss refund. Geometry path: square/triangle/circle shots, per-target shape slots, collisions with per-enemy cooldown and capped percent damage, 3D shapes (Lv3), Cube / Pyramid / Sphere actives (Lv4). Numbers in data/bima.py. One path only.
- Active skills finished: Jalu Thunderstrike and Loom Reset, Zizi Nap Time (+ debuff 25%), Romli random events. Bottom-bar ability buttons (E/C/V), aimed abilities wait for a map click.
- Visuals: new Trojan (barrel-stave white wooden Didit with windows and wheels), Trojan / Trojan Trojan / Boss are bigger, Speedster afterimage trail, Reinforced Didit has 2 armor stages (full, damaged) instead of pips, new health bars (gradient, damage ghost, quarter ticks) and boss bars, more character VFX (tier glow + sparkles, muzzle flash, per-character hit effects, bigger upgrade bursts).
- PYGBAG_HANDOFF.md: everything a new session needs to run the game in the browser.
- Tests: tests/test_bima.py.

## Checkpoint 7 (2026-10-25, second batch)
1. Controls: speed x1/x2/x3 (F or the orange button; the simulation runs several steps per frame, so it stays accurate). START doubles as "skip prep". Options menu (gear button or O/Esc, saved to options.json): auto-start waves + delay, volume, screen shake, hit words, particles, danger glow, FPS, default target, fullscreen, restart. Per-tower target priority First/Last/Strong/Weak/Close (arrows in the panel or T / Shift+T).
2. New enemies: Rich Didit (top hat, mustache, money bag; big bounty, steals money if it leaks), Speedster Didit (fast boss, starts 4.2x speed and decelerates over 13s), Reinforced Didit (10 armor hits before HP). Jalu path B renamed "Temporal Loom Guy"; tier 3 "The Temporal Loom" adds Speed Against Time (hit fast Didits walk at normal speed for 3s, refreshed per hit). Romli Programmer tier 2 "Better code" counts 1 hit as 3 against armor.
3. 30 waves (data/waves.py). Intros: 6 Rich, 8 Reinforced, 10 Boss, 13 Trojan (now a miniboss), 17 Speedster, 22 Trojan Trojan. Special rounds (named banner, double clear bonus): 7 Stampede, 17 Speed Rush, 25 Iron Parade. Rich Didits come in the round before hard rounds. Bosses/minibosses appear as regular enemies from ~wave 18.
4. Look: every Didit is white; Tanky Didit is bigger with a scar; Trojan Didit / Trojan Trojan Didit are Didit-shaped wooden statues painted white (chipped paint, plank seams, wheels).
- Tests: test_new_enemies.py, test_options_targeting.py. Balance bot: 30 waves, 14 towers.

## Checkpoint 6 (2026-10-25): economy, Trojans, BTD6 UI, 3D-ish look
- Economy: bounties x2 and +8% per wave (`BOUNTY_*` in settings), wave-clear bonus 100 + 35/wave, start money 750.
- Wave scaling (`WAVE_SCALING` in data/waves.py): wave 1 = 0.5x HP / 0.85x speed ... wave 10 = 2.8x HP / 1.15x speed. Stacks with the prep-wait penalty. One Jalu holds waves 1-2 (bot).
- New enemies: **Trojan Didit** (wooden horse, releases 5 normal Didits) from wave 5; **Trojan Trojan Didit** (boss, releases 3 Trojans) in waves 9-10. Data field `spawns`; children inherit multipliers; a leaking Trojan spawns nothing.
- UI redone like BTD6: map fills the window, floating HUD (lives, money, round, pause), wooden bottom bar (UPGRADES, tower cards with prices, speed + start buttons), slide-in upgrade panel on the side away from the tower, boss bars, toasts, tooltips. Chunky font Lilita One (SIL OFL, assets/fonts).
- 3D-ish look (game/gfx.py, scenery.py, sprites_proc.py): baked scenery with a raised cobblestone path (wall, rim, bevels), lit grass, trees/bushes/rocks/flowers with soft shadows; shaded-sphere enemies with 8 walk frames; tower pedestals; glow projectiles with ground shadows; depth sorting by y.
- Map: new 1280x720 layout with rounded corners (`round_corners`). Placement uses BUILD_RECT (above the bar). `assets/sprites/background` override removed.
- Tests: `tests/test_trojan_economy.py`; balance bot has SOLO and FULL builds.

## Checkpoint 5
- Fullscreen: `pygame.SCALED | RESIZABLE` window, F11 / Alt+Enter toggle, focus loss pauses.
- Money: every change goes through `Game.add_money`; HUD total counts up/down with merged `+$N` / `-$N` popups.
- Romli: `income_per_sec` is now paid every 10s in one lump (sound, coin burst, "+$N", progress bar). Per-wave income gets coin visuals at wave end; wave-clear money has its own sound and one combined popup.
- More polish: hover/select sounds, red danger vignette, ambient motes, aiming tower barrels, shadows, boss aura, ice particles on slowed enemies, stash glow, enemies face their walking direction.
- Sprite loader (`game/assets.py`, `assets/sprites/README.txt`): drop PNGs in, placeholders remain as fallback.
- Tests moved into the project (`tests/`), balance bot in `tools/`.

## Checkpoint 4
- Difficulty: simulations showed the game unwinnable by wave 7 even with larping and upgrades. Base damage doubled (Jalu 2, Romli 1, Zizi 1); T3/T4 prices lowered (500-550 / 1100-1200). A crude bot now wins with prep waits up to ~30s and loses with 40s+.
- One-time tip about Larping when the first Jalu is placed (Jalu upgrades need knowledge).
- VFX/SFX layer (see CLAUDE.md): 25 procedural sounds with pitch variants and rate limiting, hit sparks, pop bursts, "+$" pop-ups, comic words, projectile trails, tower recoil, enemy hit flash and waddle, wave banners, screen shake/flash on leaks and bosses, prep warning and last-5s ticks. `M` mutes.

## Checkpoint 3 (autonomous pass)
- Zizi: Praying unlocks at Recitation (A) tier 2, Slothing at Sin of Sloth (B) tier 2; locked buttons say what is needed.
- Effect system (`game/effects.py`, numbers in `data/effects.py`, hooks documented in the module docstring).
  Implemented: pierce_1, chain_lightning (Thor), time_push (Loom), sleep_chance, damage_debuff_15,
  aura_attack_speed_10/20/30 (strongest aura wins), upgrade_discount_aura, boss_kill_bonus.
  Still pending (panel says "not implemented yet"): thunderstrike_active, loom_reset_active,
  nap_time_active, random_event, random_event_strong.
- Enemies: stun (sleep) and push-back; bosses are immune to both.
- QoL: pause, hotkeys, sell confirmation, tower stats line, hotkey labels on buttons, hotkey hints.
- Upgrade price now goes through `Game.upgrade_cost` (discounts); sell value counts the price actually paid.
- Tests run headless: all effects, unlocks, QoL, and 6 random-bot fuzz runs without errors.
