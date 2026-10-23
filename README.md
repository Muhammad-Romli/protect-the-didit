# Protect The Didit

2D tower defense (BTD6-style) in Python + pygame-ce. Hamsters ("Didit") raid the Snack Stash.

## Run
```
pip install pygame-ce
python main.py
```

## Controls
- Shop bar (bottom): click Jalu / Romli / Zizi, then click the map to place. RMB / Esc cancels.
- Click a tower: upgrade panel (Path A / Path B / Sell). Click empty ground to deselect.
- "Start wave" button, `x1/x2` speed toggle. `R` restarts.
- Debug: `F1` overlay, `F2` +$1000, `F3` skip to next wave.

## Status: foundation (≈ Day 1–6 of the CLAUDE.md plan, Pass 1)
Done: game loop, map, enemies (4 types), waves 1–10, placement, "first" targeting, projectiles
(single-target + AoE + slow), money/HUD, win/lose, 3 towers, generic upgrade system with the
(4,1) rule using stat modifiers only, sell (70%), per-second / per-wave income, money-per-hit.

Not done yet (data exists, behaviour doesn't): every named `effects` entry (pierce, chain lightning,
time push, auras, random events, sleep, debuff, active skills), fusion, Jalu speech bubbles
(`data/dialogue.py` is placeholders), sprites, sound, start screen. The upgrade panel marks tiers
whose special effect is not implemented yet..
