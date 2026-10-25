# HANDOFF — context for a fresh session

Read this, then CLAUDE.md (the spec; some numbers there were changed on purpose, marked with dates), CHANGELOG.md and TODO.md.

## What this is
"Protect The Didit": a 2-week-prototype tower defense (Bloons TD 6 style) in Python 3.11+ / pygame-ce.
Towers = the author's friends: **Jalu** (base tower, larper), **Romli** (economy, the author himself), **Zizi** (support/CC).
Enemies = hamsters ("Didit", the author's real hamster) walking one fixed path to the Snack Stash.
Run: `pip install pygame-ce && python main.py`. Tests: see README (all headless).

## Decisions the author made (chronological)
1. Build the framework from CLAUDE.md, placeholder shapes for art.
2. **Preparation phase** between waves: time keeps moving (Romli income keeps flowing on purpose); enemies get stronger the longer you wait (x3 HP, +30% speed, ramp from 20s to 1:30, then the wave is forced). Max 3 simultaneous tower activities (Romli's future ones do not count).
3. Activities: **Zizi** Slothing -> Laziness stacks / Praying -> Blessing stacks (+1 per 5s, max 5, last one battle only; Praying unlocks at Recitation A tier 2, Slothing at Sin of Sloth B tier 2); **Jalu** Larping -> +1 "ball knowledge"/s, needed with money for every Jalu upgrade. **Romli's activities (farming, news-based trading, code-bug puzzles) are postponed** until the game is ready.
4. Autonomy granted: gameplay (effects, bug fixes, balance) + QoL; ask the author through Q&A for important decisions. VFX/SFX then approved explicitly (Bloons feel).
5. Economy: lowered T3/T4 prices so tier 4 is reachable. Base damage doubled after simulations showed the game unwinnable by wave 7.
6. Money feedback: HUD "+$N" popups, no flying coins; Romli income in 10s lumps; fullscreen; he will add free 2D assets himself (sprites/sounds).

## Architecture in one minute
- `data/` holds every number: towers (+ upgrades with stat_mods/effects/knowledge cost), enemies, waves, map, settings, effects params, activities/stacks, dialogue (placeholders).
- `game/game.py` = all state + input + rules. Only place money changes: `add_money`. Effects use hooks (`game/effects.py` docstring): hit / damage_taken / speed_bonus / upgrade_discount / boss_kill.
- Game never draws sound/particles directly: it calls `game.fx.<event>()` (`game/fx.py`) -> `audio.py` (synth SFX, `assets/sfx` overrides) + `vfx.py` (particles, comic words, shake).
- `game/ui.py` draws/hit-tests only and returns action tuples; Game executes them.
- Optional sprites via `game/assets.py` (names in `assets/sprites/README.txt`).

## Status
Done: loop, map, 4 enemy types, 10 waves, 3 towers x 2 paths x 4 tiers (stat mods), prep phase, activities, effects (pierce, chain lightning, time push, sleep, damage debuff, attack-speed auras, upgrade discount, boss-kill bonus), pause/hotkeys/sell confirm, VFX/SFX, fullscreen, sprite loader.
Pending (data exists, panel says "not implemented yet"): active skills (Thunderstrike, Loom Reset, Nap Time), Romli random events (path B tiers 3-4), Zizi tier-4 "slow all in a big radius", fusion tower, Jalu speech bubbles (needs the author's lines), music, Romli's activities.

## Honest caveats
- Everything was tested headless only. Never seen in a real window: real FPS on his laptop (AMD, 8 GB), real fullscreen behaviour (he develops under WSL; check WSLg), and how the synthesized sounds actually sound.
- Balance comes from a crude bot (wins with prep waits <= ~30s, loses at 40s+); human play is untested. Blessing at 5 stacks looks strong.
- Base Romli earns only at wave end; his 10s lump payout starts at Small business (path A tier 2). Ask if he wants base Romli to pay every 10s too.
- One Zizi can unlock only one activity (A2 and B2 cannot coexist under the (4,1) rule).

## Working agreements
- The author is a backend programmer (learning Go on boot.dev, uses Python here); wants direct, unsentimental honesty, no yes-man behaviour, verified claims. English unless he writes Indonesian. "Teach me" = explain, don't just fix.
- Follow CLAUDE.md rules: small steps, runnable after each step, data-driven, no out-of-scope features (put ideas in TODO.md), state assumptions in one line, say how to test.

## Good next steps
1. Author playtests on his machine and reports FPS, feel, sound quality, wave 7 difficulty.
2. Active skills (Pass 4) or fusion, whichever he picks.
3. Plug in his sprites/sounds and fix scale/offset issues.
4. Jalu dialogue + speech bubbles once he writes the lines.
