# Protect The Didit

A 2D tower defense game in the style of Bloons TD 6, written in Python with
[pygame-ce](https://github.com/pygame-community/pygame-ce). Hamsters called
"Didit" march along a path to raid your **Snack Stash**. Place towers, upgrade
them, and stop the Didit before they empty the stash.

Playable on desktop and on phone / tablet.

## Table of contents
- [Quick start](#quick-start)
- [How to play](#how-to-play)
- [Controls](#controls)
- [Preparation phase](#preparation-phase)
- [Mobile support](#mobile-support)
- [Display](#display)
- [Assets](#assets)
- [Sound and effects](#sound-and-effects)
- [Tests](#tests)
- [Debug tools](#debug-tools)

## Quick start

```bash
pip install pygame-ce
python main.py
```

## How to play

1. Pick a tower from the cards in the bottom bar: **Jalu**, **Romli**, or **Zizi**.
2. Click the map to place it (you need enough money).
3. Start the wave with the green START button (or `Space`).
4. Didit walk the path toward the Snack Stash while your towers attack them.
5. Earn money, then place more towers or upgrade existing ones.
6. Click a placed tower to open its upgrade panel. Each tower has two upgrade
   paths (Path A and Path B), and you can also sell it.

**You lose when the Snack Stash's HP reaches zero.** Press `R` to restart.

## Controls

### Mouse
| Action | How |
|---|---|
| Place a tower | Click a tower card in the bottom bar, then click the map |
| Cancel placement | Right mouse button or `Esc` |
| Open upgrade panel | Click a placed tower (Path A / Path B / Sell) |
| Deselect | Click empty ground |
| Start wave | Green START button |
| Change game speed | Orange speed button |
| Pause | Pause button (top right) |

### Keyboard
| Key | Action |
|---|---|
| `1`-`3` | Select a tower to place |
| `Space` | Start the next wave |
| `P` | Pause / resume |
| `F` | Change game speed |
| `Q` / `W` | Upgrade Path A / Path B of the selected tower |
| `X` | Sell the selected tower (press twice to confirm) |
| `M` | Mute / unmute |
| `R` | Restart |
| `F11` or `Alt+Enter` | Toggle fullscreen |

## Preparation phase

Before wave 1 and after every wave, the game is in **PREPARATION**. Time keeps
moving and passive income still flows, so you can build and upgrade, but
waiting has a cost: **the longer you wait, the stronger the next wave gets.**

- Enemy HP scales up to **x3**.
- Enemy speed increases by **+30%**, reached at 1:30.
- At 1:30 the wave starts by force.

While preparing, select **Jalu** or **Zizi** and use their activity buttons.
At most 3 activities can run at once, and they stop when the wave starts.

| Tower | Activity | Effect |
|---|---|---|
| Zizi | Slothing | Builds **Laziness** stacks |
| Zizi | Praying | Builds **Blessing** stacks |
| Jalu | Larping | +1 **ball knowledge** per second |

- **Zizi:** stacks grow by +1 every 5 seconds, up to 5. The last one lasts for
  one battle.
- **Jalu:** ball knowledge is required, in addition to money, for every Jalu
  upgrade.

Timing and scaling values are tunable through the `PREP_*` constants in
`data/settings.py`.

## Mobile support

The game runs on phones and tablets with touch controls:

- Tap a tower card, then tap the map to place, and confirm with the **OK** or
  **cancel** buttons.
- An on-screen formula keypad for input.
- Can be installed as a **PWA** or built as an **APK**.

Full details, including build steps, are in [`MOBILE.md`](MOBILE.md).

## Display

The window is resizable. The game renders at a fixed 1280x720 and is scaled to
fit. Toggle fullscreen with `F11` or `Alt+Enter`. Alt-tabbing away pauses the
game.

## Assets

- Sprites: `assets/sprites/` (see the README in that folder)
- Sounds: `assets/sfx/` (see the README in that folder)

Missing files are not fatal: sounds fall back to generated ones and sprites
fall back to colored shapes, so the game runs even with empty asset folders.

## Sound and effects

All sound and effects are generated in code by default, so no asset files are
required. To use real sounds, put files in `assets/sfx/` (see the README
there). Press `M` to mute.

## Tests

All tests run headless (no window needed):

```bash
python tests/test_effects_and_qol.py
python tests/test_money_fx_assets.py
python tools/balance_bot.py
```

## Debug tools

| Key | Effect |
|---|---|
| `F1` | Toggle debug overlay |
| `F2` | +$1000 |
| `F3` | Skip to the next wave |
| `F4` | Free next upgrade on the selected tower |
