# CLAUDE.md — Protect The Didit

## Project overview
"Protect The Didit" is a 2D tower defense game inspired by Bloons TD 6, written in Python.
- **Towers ("characters")** are the makers: **Romli**, **Zizi**, **Jalu**.
- **Enemies** are hamsters, all variants of "Didit" (the dev's real hamster), walking along a path.
- **Goal of the player:** stop the hamsters before they reach the end of the path.
- **Deadline:** 2 weeks. This is a PROTOTYPE. Scope discipline matters more than polish.

> Open question (default below): the title says "Protect" but the enemies are Didit.
> Default: the hamsters are raiding the **Snack Stash** at the end of the path, and the player protects it.
> If this changes, only update text/art, not code structure.

## Tech stack
- Python 3.11+, `pygame-ce`. No other game engine. Standard library otherwise.
- Target: modest laptop (8 GB RAM), 60 FPS, 1280x720.
- Placeholder art first (colored circles + text labels). Real sprites only at the end, if time.

## Hard rules for Claude
1. **Do not add features outside the scope below.** Put ideas in `TODO.md` instead.
2. **Small steps.** One milestone item at a time. After each step the game must still run (`python main.py`).
3. **Data-driven.** Tower stats, upgrades, enemy stats, waves live in `data/`, not hardcoded in classes.
4. **Use delta time** (`dt` in seconds) for movement and cooldowns. Never frame-count.
5. **Separate logic from rendering.** Entities have `update(dt)` and `draw(surface)`.
6. **Upgrades are built from generic stat modifiers + named special effects.** See "Upgrade system". Do not write one hardcoded class per upgrade.
7. **No premature abstraction.** Simple classes, readable code, type hints, short docstrings.
8. After each step, state what changed and how to test it (what to click, what should happen).
9. If ambiguous, pick the simplest option, state the assumption in one line, and continue.

## Prototype scope
| Item | Count | Notes |
|---|---|---|
| Towers | 3 | Jalu (base, built first), Romli, Zizi |
| Upgrade paths | 2 per tower | **4 tiers per path** |
| Fusion | 1 | Combine 2 towers into 1 fused tower |
| Enemy types | 4 | normal, fast, tanky, boss |
| Maps | 1 | Fixed waypoint path |
| Waves | 10 | Boss on wave 10 |

**Out of scope:** multiplayer, save/load, multiple maps, difficulty modes, targeting-priority UI beyond "first",
menus beyond start/win/lose. Sound is optional and last.

## Core mechanics
- **Economy:** start with 650 money, 100 stash HP. Kills give money. Wave clear gives a bonus.
- **Placement:** click a tower in the shop bar, then the map. Invalid if on the path, off-map, or overlapping another tower. Show range circle while placing (green valid / red invalid).
- **Selecting a tower:** click it to open the upgrade panel (range circle, path A button, path B button, sell button, tower name + current tier).
- **Targeting:** "first" only (enemy furthest along the path within range).
- **Sell:** refunds 70% of total money spent on that tower.
- **Waves:** "Start wave" button. Optional x2 fast-forward toggle. Waves alternate with a preparation phase (see below).
- **Win:** survive wave 10 including the boss. **Lose:** stash HP reaches 0.

## Preparation phase (scope addition, 2026-10-24)
Game alternates **PREPARATION** and **BATTLE**. Preparation comes before wave 1 and after every cleared wave.
- **Time keeps moving** in preparation. Passive income (Romli `income_per_sec`) keeps flowing. This is a feature, not a bug.
- **Escalation:** the longer you wait, the stronger the next wave. Linear ramp from 20s (grace, x1) to 90s: enemy HP up to **x3**, speed up to **+30%**. At 1:30 the wave **starts by force**. Strength is locked in when the wave starts. Bounty and stash damage do not scale. All values live in `data/settings.py` (`PREP_*`).
- **Activities:** a tower can run one activity at a time, only during preparation; they stop automatically when the wave starts. **Max 3 simultaneous activities** (`MAX_ACTIVITIES`). Romli's activities do **not** count toward the cap (manual, they already take the player's attention). Defined in `data/activities.py`.
- **Activities** (build order was: prep mechanics -> Zizi -> Jalu -> Romli):
  - **Zizi** (built; each activity unlocks at **tier 2 of a path**: *Praying* at Recitation (A), *Slothing* at Sin of Sloth (B); because (2,2) is not allowed, one Zizi can only ever unlock one of them): *Slothing* gives **Laziness** stacks (+slow strength, +slow duration), *Praying* gives **Blessing** stacks (+damage, faster attacks). +1 stack every 5s, max 5 each; the activity auto-stops at max. Stacks last for the next battle only (`reset_on_wave_end` in `data/activities.py`). Switching Slothing <-> Praying on the same tower is allowed.
  - **Jalu** (built): *Larping* gives **+1 ball knowledge per second** (shared pool). Every Jalu upgrade tier costs money AND ball knowledge (10 / 25 / 60 / 120 per tier, `JALU_KNOWLEDGE_COSTS`).
  - **Romli (postponed until the rest of the game is ready):** farming; trading (read news, guess where prices move); solving code bugs (puzzles) for rewards.
- Debug: `F2` also gives +100 ball knowledge.

## VFX / SFX (approved 2026-10-24, goal: Bloons TD 6 feel)
Procedural, no downloads: `game/audio.py` synthesizes 25 sounds at startup (`assets/sfx/<name>.ogg|wav` overrides any of them, see `assets/sfx/README.txt`); `game/vfx.py` has particles, rings, floating text, comic words ("POW!"), screen shake/flash; `game/fx.py` maps game events to both. Game logic only calls `game.fx.<event>()`. `M` mutes. No music yet.

## Money feedback, display, sprites (approved 2026-10-24)
- All money changes go through `Game.add_money()`. The HUD total counts up/down to the real value and shows a merged `+$N` (green) / `-$N` (red) popup beside it (no flying coins). Wave-clear money (bonus + Romli per-wave income) is one combined popup.
- Romli's `income_per_sec` is paid as one lump every `INCOME_INTERVAL_SECONDS` (10s) with its own sound, coin burst and a progress bar over the tower. Without upgrades Romli only earns at wave end.
- Display: 1280x720 logical window, `pygame.SCALED | RESIZABLE`; `F11` / `Alt+Enter` toggles fullscreen; losing window focus pauses. Not verified on a real display yet.
- Sprites: any missing file falls back to the colored placeholder; names in `assets/sprites/README.txt`.
- Extra polish: hover/select sounds, danger vignette that grows with enemy strength, ambient motes, tower barrels that aim, shadows, boss aura, ice particles on slowed enemies, stash glow.

## QoL (approved 2026-10-24)
Pause (`P` or button), hotkeys (`1-3` place, `Space` start wave, `F` speed, `Q`/`W` upgrade path A/B, `X` sell), sell needs a second press within 3s, stats line for the selected tower, discounted prices shown in the upgrade panel.

## Upgrade system
- Each tower has **Path A** and **Path B**, each with **4 tiers**.
- **Rule (BTD6-style, but simplified):** a tower may go up to tier 4 on ONE path, and at most **tier 1 on the other path**.
  - Valid states `(a, b)`: `max(a, b) <= 4` and `min(a, b) <= 1`. Examples: `(4,1)` ok, `(1,1)` ok, `(2,2)` NOT ok.
  - The UI must grey out and show a reason ("Locked: other path is already deep") for blocked upgrades.
- Cost pattern (tunable): T1 = 100–150, T2 = 250–350, T3 = 500–550, T4 = 1100–1200 (T3/T4 lowered 2026-10-24 so tier 4 is reachable in a normal run).
- Each upgrade in `data/towers.py` is a dict with: `name`, `cost`, `description`, `stat_mods` (e.g. `{"damage": +1, "range": +20}`), optional `effects` (list of named special effects, e.g. `["chain_lightning"]`), and `voice_line` (see Jalu).
- Special effects are implemented as small handler functions registered by name (a dict `EFFECTS = {"chain_lightning": fn}`), so each tower asks "which effects do I have?" and calls them.

### Implementation priority for upgrades (IMPORTANT — scope control)
24 upgrades with unique mechanics is too much for 2 weeks if done all at once. Build in this order:
1. **Pass 1:** all tiers of all paths work with **stat modifiers only** (damage, range, cooldown, income, slow). Playable and balanced.
2. **Pass 2:** tier 2 special behaviors (new projectile types, income generation, AoE).
3. **Pass 3:** tier 3 special effects.
4. **Pass 4:** tier 4 active skills / random events. These are the riskiest; cut the weakest ones first if behind.

## Towers

All numbers are tunable starting values (in `data/towers.py`).

### Jalu — BASE TOWER (build and finish this one first)
- **Concept:** a larper who has never actually watched the movies but constantly talks about them. Sarcastic and funny.
- **Base:** single-target, reliable. Cost 200, damage 2, cooldown 0.8s, range 150. (Base damage doubled 2026-10-24: simulations showed the original 1 was unwinnable by wave 7.) He just throws things.
- **Path A — "God of Thunder" (Thor-style)**
  1. **Costume & hammer:** wears the costume and holds a hammer. More damage, slightly shorter cooldown.
  2. **Throw it:** throws the hammer / shoots lightning as a projectile. Longer range, pierces 1 enemy.
  3. **Real power:** chain lightning that jumps to nearby enemies. Strong damage boost.
  4. **Active skill + overall boost:** "Thunderstrike" active ability (button, ~30s cooldown): heavy AoE damage at a chosen point. Also stronger basic attacks.
- **Path B — "Time Loom Guy" (Loki-style)**
  1. **Costume & scepter:** wears the costume and holds a scepter. Small damage + range boost.
  2. **Magic bolts:** shoots magic bolts that apply a short slow.
  3. **Real power:** the Time Loom: hits have a chance to push the enemy backwards along the path (reduce its `distance_travelled` by a fixed amount). Does not work on bosses.
  4. **Active skill + overall boost:** "Loom Reset" active ability (~35s cooldown): all enemies in range are pushed back and frozen for 2s. Also stronger basic attacks.
- **Personality (voice lines):** a short speech bubble above Jalu appears on place, on each upgrade, and occasionally when shooting (max once per ~10s). He is sarcastic, overconfident, and gets movie references wrong. Keep lines in `data/dialogue.py`, 3–5 per upgrade/event, picked randomly. Example tone (rewrite freely):
  - Placed: "<plh>."
  - Thor T1: "<plh>."
  - Loki T1: "<plh>."
  - Hits an enemy: "<plh>!"
  - Tier 4: "<plh>."

### Romli — economy + programmer
- **Base:** earns a small passive income at the end of every wave (+25 money) and fires a weak "bug" projectile. Cost 250, damage 1, cooldown 1.2s, range 130.
- **Path A — Farm / Business (income)**
  1. Side hustle: more income per wave.
  2. Small business: income per wave increases again and adds a small income per second.
  3. Company: big income boost, and nearby towers get a small discount on upgrades (−5%).
  4. Empire: very large income per wave + extra bonus on boss kill.
- **Path B — Programmer (attack that converts to money)**
  1. Decoder: attacks give a small money bonus per hit.
  2. Better code: faster attacks, and more money per hit.
  3. **Random event every 20s** (equal 33% chance each): (a) +10% of current money, (b) all friendly towers in range get **attack speed x9.99 for 2s**, (c) "bug" — spawns a few enemies appropriate for the current wave.
  4. Same event system but stronger: boost lasts longer, money bonus larger, and the "bug" outcome spawns fewer enemies than before. Plus higher base damage.
- **Notes / balance guards (important):**
  - The "attack speed 999%" effect must be capped by a max fire rate (e.g., 20 shots/s per tower) and a short duration, or it will break the game performance and balance.
  - The "bug" outcome spawns enemies at the start of the path, count scaled by wave number (e.g., `1 + wave // 3`), capped at 6, and they give no money. Show a popup "BUG!" so it feels intentional.
  - Event timer shows a small progress bar over the tower.

### Zizi — support / crowd control
- **Base:** area damage + mild slow, low damage. Cost 300, damage 1 (radius 60), cooldown 1.4s, range 120, slows by 15%.
- **Path A — Recitation (buff + small AoE + slow)**
  1. Aura: small AoE damage, slow strength up.
  2. Nearby towers get a buff aura (+10% attack speed).
  3. Bigger AoE radius, stronger buff (+20%), slow lasts longer.
  4. Strongest aura: +30% attack speed for nearby towers, AoE damage up, slow applies to all enemies in a big radius.
- **Path B — Sin of Sloth (crowd control)** *(your design was undecided, so this is a proposal; change as you like)*
  1. Lazy hamsters: stronger slow (35%).
  2. Enemies inside the range take +15% damage from all towers ("debuff").
  3. Enemies hit have a chance to **stop for 1.5s** (fall asleep). Does not work on bosses.
  4. "Nap Time" active skill (~40s cooldown): all enemies in range stop for 3s (bosses for 1s). Also strengthens the damage debuff to +25%.
- **Tone note:** Keep Zizi's flavor respectful and affectionate. If you add jokes, make them about the game situation, not about the beliefs themselves. Also check the characters are okay with how they are portrayed.

### Fusion
- Default (placeholder, change if wanted): **Jalu + Romli** → "Marvel Startup Bro" (name TBD).
- Both towers must be placed within 200 px of each other and each at least tier 1 on any path.
- Action: select one, click "Fuse", pick the partner. Costs 500. Both originals are removed; the fused tower appears at the first one's position.
- Fused tower: strong single-target + income generation (small), long range, **no upgrades**. Distinct color + label.
- Implement as a data entry (`FUSIONS = {("jalu", "romli"): "fused_jalu_romli"}`) so more can be added without code changes.

## Enemies (all are Didit variants)
Tunable, in `data/enemies.py`.

| Type | HP | Speed (px/s) | Stash damage | Money | Notes |
|---|---|---|---|---|---|
| Normal Didit | 10 | 60 | 1 | 5 | baseline |
| Fast Didit | 6 | 120 | 1 | 6 | arrives quickly, low HP |
| Tanky Didit | 60 | 40 | 3 | 15 | soaks damage |
| Boss Didit | 600 | 30 | 25 | 150 | large sprite, big health bar, wave 10 only |

- Slow effects multiply speed (never below 20% of base). Bosses take half the slow effect and are immune to push-back and stop effects.
- Every enemy has a small health bar. The boss gets a large bar at the top of the screen.
- Spawned "bug" enemies (Romli) are flagged `gives_money = False`.

## Map
- 1 map, 1280x720. Path = list of waypoints in `data/map.py` (winding, ~6–8 turns).
- Enemies track `distance_travelled` (used for "first" targeting and push-back effects).
- Placement validity: distance from path segments must be at least 30 px.
- Draw the path as a thick tan polyline. End = Snack Stash.

## Waves (10 total, in `data/waves.py`)
Format: list of groups `(enemy_type, count, spawn_interval_seconds, start_delay_seconds)`.
- 1–3: normal only, increasing counts
- 4–5: introduce fast
- 6–7: introduce tanky
- 8–9: mixed, higher counts
- 10: mixed + boss

## Suggested project structure
```
protect-the-didit/
├── CLAUDE.md
├── TODO.md              # ideas that are out of scope
├── main.py              # entry point, game loop only
├── game/
│   ├── game.py          # Game state: money, lives, wave, entities, states
│   ├── tower.py         # Tower class (+ upgrade/sell/fuse logic)
│   ├── effects.py       # named special effects (chain_lightning, time_push, etc.)
│   ├── enemy.py         # Enemy (waypoint movement, slow, push-back, stop)
│   ├── projectile.py
│   ├── wave_manager.py
│   ├── ui.py            # shop bar, upgrade panel, buttons, HUD, speech bubbles
│   ├── utils.py
│   ├── audio.py         # procedural SFX (assets/sfx overrides)
│   ├── vfx.py           # particles, rings, floating/comic text, shake, flash
│   ├── fx.py            # game event -> sound + visuals (Game only calls this)
│   └── assets.py        # optional sprite loader (assets/sprites)
├── tests/               # headless checks (python tests/<file>.py)
├── tools/               # balance_bot.py
├── HANDOFF.md           # context for a fresh session
├── CHANGELOG.md
├── data/
│   ├── towers.py
│   ├── activities.py    # preparation-phase activities
│   ├── enemies.py
│   ├── waves.py
│   ├── map.py
│   └── dialogue.py      # Jalu voice lines
└── assets/              # optional
```

## Milestones (2 weeks)
Each milestone must be runnable before moving on. Jalu is built first and fully.

**Week 1 — core game**
- Day 1: project setup, window, game loop, draw map path, FPS cap
- Day 2: enemies walk the path (normal type), health bars, stash damage
- Day 3: Jalu base tower: placement (shop bar, range preview, validity), shoots projectiles
- Day 4: money/lives HUD, kill rewards, wave manager, "Start wave", win/lose screens
- Day 5: fast, tanky, boss enemies; generic upgrade system with the (4, 1) rule using stat mods only (Jalu both paths, Pass 1)
- Day 6: Romli and Zizi base towers + their Pass 1 upgrades
- Day 7: buffer, first balance pass, bug fixes

**Week 2 — depth and polish**
- Day 8: Pass 2 specials (Jalu hammer throw / magic bolts, Romli income, Zizi aura)
- Day 9: Pass 3 specials (chain lightning, time push, Romli random event system, Zizi sloth stop)
- Day 10: Pass 4 active skills (Jalu Thunderstrike / Loom Reset, Zizi Nap Time) and Romli tier 4
- Day 11: fusion
- Day 12: Jalu speech bubbles and voice lines, balance all 10 waves
- Day 13: polish (sprites if time, optional sound, start screen)
- Day 14: bug fixing only, README with run instructions. **No new features.**

**Cut order if behind schedule:** sound → sprites → fast-forward → Romli's "bug" outcome → tier 4 active skills (keep as stat boosts only) → fusion.

## Commands
- Install: `pip install pygame-ce`
- Run: `python main.py`
- Debug keys: `F1` debug overlay (FPS, entity counts), `F2` +1000 money, `F3` skip to next wave.

## Code style
- Python 3.11+, type hints on public functions, `dataclass` for plain data.
- Constants in UPPER_SNAKE_CASE; magic numbers go in `data/`.
- Short functions. Keep `main.py` under ~50 lines.
- No global mutable state outside the `Game` object.
