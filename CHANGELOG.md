# Changelog

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
