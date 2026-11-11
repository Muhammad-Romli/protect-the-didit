# Protect The Didit

2D tower defense (BTD6-style) in Python + pygame-ce. Hamsters ("Didit") raid the Snack Stash.

## Run
```
pip install pygame-ce
python main.py
```

## Menu, shop and Snack Coins
The game starts at a main menu: PLAY / CONTINUE, UNITS (characters and upgrade paths), SHOP (A'yun), DEVELOPERS (empty), EXIT.
Finishing a run (win or lose) pays Snack Coins. Spend them in the SHOP on permanent buffs or one-use items (used from the POWERS button in a run).
Your coins and purchases are saved in `profile.json` (browser: localStorage). Delete that file to reset them.

## Controls
- Hotkeys: `1-3` place, `Space` start wave, `P` pause, `F` speed, `Q`/`W` upgrade, `X` sell (press twice).
- Tower cards (bottom bar): click Jalu / Romli / Zizi, then click the map to place. RMB / Esc cancels.
- Click a tower: upgrade panel (Path A / Path B / Sell). Click empty ground to deselect.
- Green START button (Space), orange speed button (F), pause button top-right (P). `R` restarts.
- Debug: `F1` overlay, `F2` +$1000, `F3` skip to next wave, `F4` free next upgrade on the selected tower.

## Phone / tablet
Touch controls (tap-to-place with OK/cancel, formula keypad, ...), PWA and APK build: see `MOBILE.md`.

## Display
Resizable window; `F11` or `Alt+Enter` toggles fullscreen (the 1280x720 game is scaled to fit). Alt-tab pauses.

## Assets
Sprites: `assets/sprites/` (see its README). Sounds: `assets/sfx/` (see its README). Missing files fall back to generated sounds / colored shapes.

## Tests
`python tests/test_effects_and_qol.py`, `python tests/test_money_fx_assets.py`, `python tools/balance_bot.py` (all headless).

## Sound and effects
All generated in code (no asset files). `M` mutes. To use real sounds, put files in `assets/sfx/` (see the README there).

## Preparation phase
Before wave 1 and after each wave you are in PREPARATION: time moves (passive income still flows),
but enemies get stronger the longer you wait (up to x3 HP, +30% speed by 1:30, then the wave starts by
force). Select Jalu or Zizi and use the activity buttons (max 3 at once; they stop when the wave starts).
Zizi: Slothing -> Laziness / Praying -> Blessing stacks (+1 per 5s, max 5, last one battle).
Jalu: Larping -> +1 ball knowledge/s, required (with money) for every Jalu upgrade.
Tuning: `PREP_*` in `data/settings.py`.

- Bima (key 4): Graph path needs typing a formula (click the box, Enter fires, G repeats); Geometry path auto-attacks with shapes. Abilities E/C/V.
