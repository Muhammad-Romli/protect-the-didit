# Protect The Didit

2D tower defense built with Python and `pygame-ce`. Didit hamsters raid the Snack Stash; place and upgrade character towers to stop them.

## Run

```bash
pip install -r requirements.txt
python main.py
```

## Controls
- Hotkeys: `1-3` place, `Space` start wave, `P` pause, `F` speed, `Q`/`W` upgrade, `X` sell (press twice).
- Tower cards (bottom bar): click Jalu / Romli / Zizi, then click the map to place. RMB / Esc cancels.
- Click a tower: upgrade panel (Path A / Path B / Sell). Click empty ground to deselect.
- Green START button (Space), orange speed button (F), pause button top-right (P). `R` restarts.
- Debug: `F1` overlay, `F2` +$1000, `F3` skip to next wave, `F4` free next upgrade on the selected tower.

- `1`-`5`: select/place Jalu, Romli, Zizi, Bima, or Fadhli.
- `Space`: start the next wave / skip preparation.
- `P`: pause. `F`: cycle game speed. `Q` / `W`: upgrade path A / B. `X`: sell (press twice to confirm).
- Click a tower to open its upgrade panel. Click empty ground to deselect.
- `T` / `Shift+T`: change target priority. `O` or `Esc`: open Options.
- `R`: restart. `F11` / `Alt+Enter`: fullscreen. `M`: mute.
- Debug: `F1` overlay, `F2` add money and ball knowledge, `F3` skip to next wave, `F4` free next upgrade for the selected tower.
- Active abilities: `E` / `C` / `V` (the selected tower's ability buttons, in panel order). Bima's Graph path uses the formula editor (`G` fires) and his Geometry path uses shape attacks.

## Current content

- Five towers: Jalu, Romli, Zizi, Bima, and Fadhli. Bima has Graph and Geometry paths but can choose only one. Jalu's first path choice locks the other path; Romli, Zizi, and Fadhli use the standard crosspath rule (one path to tier 4, the other to tier 1).
- Fadhli is a petanque athlete who throws boules. Power path: high-arc shots, hot craters, and the Meteor active (three empowered shots, infinite range). Accuracy path: faster throws, a three-target bounce, steel-ball stun/slow, and the Arigatou, Gyro active (Spinned enemies and Golden Ratio damage).
- 30 waves, multiple Didit variants, preparation-phase escalation, Jalu/Zizi preparation activities, active abilities, options, and save checkpoints.
- Large hits show floating damage numbers that get bigger and redder with the damage.

## Phone / tablet

Touch controls, PWA and Android build instructions: see `MOBILE.md`.

## Assets

Optional sprite overrides live in `assets/sprites/`; optional sound overrides live in `assets/sfx/`. Missing files use generated visuals/sounds. See the README files inside those folders.

## Tests and balance

```bash
python -m pytest tests -q
python tools/balance_bot.py
```

Each test file also runs on its own, for example `python tests/test_fadhli.py`. The balance bot does not use Fadhli yet.

## Documentation

- `TODO.md`: remaining ideas and known polish gaps; completed features should not be left here.
- `CHANGELOG.md`: chronological implementation history.
- `MOBILE.md`: phone, PWA, and Android notes.
- `CLAUDE.md`: project rules and system reference for AI coding assistants. It is listed in `.gitignore`, so it only exists in local copies.
