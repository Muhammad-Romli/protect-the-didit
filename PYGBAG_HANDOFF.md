# Protect The Didit: handoff for the browser (pygbag) session

Read this first if you are the agent who has to make the game run in a web browser with **pygbag**.
Written 2026-10-25. **Nothing in this file about the browser has been tested**: the previous sessions had no
pygbag/browser available, only a headless Linux Python. Treat every "expected" below as a hypothesis to verify.

Other docs: `CLAUDE.md` (design rules, authoritative for gameplay), `README.md` (controls), `CHANGELOG.md`,
`HANDOFF.md` (older), `TODO.md`. This file only adds what the web port needs.

---

## 0. Status (2026-10-27): what is already done in code, all UNTESTED
Done (written without pygame or a browser, only `py_compile`d): 4.1 async loop, 4.2 plain `set_mode` + fullscreen hidden
on web, 4.3 click gate + loading bar + step-wise sound synthesis (`audio.LAZY`) + sprite pre-warm (`game/loading.py`),
4.4 localStorage for options (`game/web.py`), 4.5 a basic governor in `main.py`, right-click menu suppression via
`platform.window.eval` (guessed API, wrapped in try/except).
Not done: OGG pre-rendering, touch keypad for Bima's Graph, shape-sprite pre-warm, key/scroll suppression, half-resolution
rendering. Everything in section 5 is still unchecked. Also new: Trojans were recoloured to bare wood and their wheels
now stand on the road (`sprites_proc.trojan_lift`), see CHANGELOG.

Update 2026-10-27 (2): the stock pygbag page stretched the canvas and showed its own Python-logo splash before
`main.py` starts; the page CSS is now overridden at runtime (`game/web.py`) but pygbag's own pre-splash is not
restyled (would need a custom `--template`). Autosave + title/loading screens added (see CHANGELOG).

## 1. What the game is

2D tower defense in **Python + pygame-ce** (single map, 1280x720, 60 FPS). Enemies ("Didits", white hamsters) walk a
fixed winding path to a Snack Stash (100 HP). The player builds **four characters** as towers, upgrades two paths per
tower, and survives **30 waves**. A "preparation" phase before every wave lets you build, upgrade and run activities;
waiting too long makes the next wave stronger.

Look: BTD6-style UI, everything procedural (no art/audio files are required): shaded "3D-ish" sprites built from
gradients, a baked scenery surface, synthesised sound effects. The only external asset is the font
`assets/fonts/LilitaOne-Regular.ttf` (SIL OFL, license file next to it). PNG/WAV/OGG overrides are optional
(`assets/sprites/README.txt`, `assets/sfx/README.txt`).

### Characters (data/towers.py, numbers in data/)
| Tower | Cost | Path A | Path B |
|---|---|---|---|
| Jalu | 200 | Mark (melee brawler, `data/mark.py`; tier 4 **Sweep** active; each Jalu is locked to one path) | Temporal Loom Guy (slow/push; tier 3 **Speed Against Time**, tier 4 **Loom Reset** active). Upgrades also cost "ball knowledge" earned by the *Larping* activity. |
| Romli | 250 | Farm/Business (income) | Programmer (money per hit; tier 2 breaks armor 3x; tier 3-4 **random events** every 20 s) |
| Zizi | 300 | Recitation (AoE aura, slow, attack speed aura) | Sin of Sloth (stun; tier 4 **Nap Time** active) |
| **Bima** | 400 | **Graph**: type formulas, fire curves, Brain Energy | **Geometry**: shape stacks, collisions, Cube/Pyramid/Sphere actives |

Bima may use only ONE of his paths (`Tower.can_upgrade`). Everything about him is in `data/bima.py` (numbers) and
`game/bima.py`, `game/formula.py`, `game/curves.py`, `game/bima_ui.py`, `game/actives.py`.

### Enemies (data/enemies.py) and waves (data/waves.py)
normal, fast (headband), tanky (big, scar), **rich** (top hat, steals money if it leaks), **reinforced** (10 armor hits
before HP; visual stages: full / damaged / none), **speedster** (fast boss, decelerates, cyan afterimage trail),
**trojan** (miniboss, white painted wooden Didit on wheels, releases 5 normals), **trojan_trojan** (boss, releases 3
trojans), **boss**. 30 waves; specials at 7 (Stampede), 17 (Speed Rush), 25 (Iron Parade); intros at 6, 8, 10, 13, 17, 22.
Per-wave HP/speed scaling in `WAVE_SCALING`; bounties and wave bonuses in `data/settings.py`.

### Controls
Mouse + keyboard: `1-4` pick tower, click to place; click tower = upgrade panel; `Q/W` upgrade path A/B; `X` sell;
`Space` start wave / skip prep; `F` speed x1/x2/x3; `P` pause; `O`/Esc options; `T` target priority; `E/C/V` abilities;
`G` fire Bima's formula; Bima Graph needs **typing** into a text box (keyboard required).

---

## 2. File map

```
main.py                 window + loop only (synchronous, see section 4)
data/                   pure data: settings, towers, enemies, waves, map, effects, activities, bima
game/game.py            Game: state, rules, input, draw order (the big one)
game/ui.py              BTD6-style HUD, bar, upgrade panel, options overlay
game/bima.py bima_ui.py formula.py curves.py actives.py    Bima + active skills
game/tower.py enemy.py projectile.py effects.py wave_manager.py
game/gfx.py scenery.py sprites_proc.py    procedural rendering ("3D" look), all cached
game/vfx.py fx.py audio.py                particles/screen effects, game-level effects, synthesised SFX
game/options.py                          options menu rows + options.json persistence
game/utils.py assets.py                  helpers, optional PNG/WAV overrides
tests/*.py              headless tests (python tests/<name>.py)
tools/balance_bot.py    plays the game headless to check difficulty
```

## 3. Run and test on desktop

```
pip install -r requirements.txt        # pygame-ce
python main.py
# headless (no window/sound), used by all tests:
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python tests/test_bima.py
for t in test_bima test_new_enemies test_options_targeting test_trojan_economy test_effects_and_qol test_money_fx_assets; do python tests/$t.py | tail -1; done   # each must end with ALL OK
python tools/balance_bot.py 25 40       # ~20 s per run
```
Measured natively (headless, this container): 75 enemies + 6 towers = about 5 ms per frame (update + draw);
`Game()` construction about 0.7 s of which audio synthesis about 0.45 s and the map bake about 0.2 s.
**Browser numbers will be several times worse (WebAssembly); measure.**

---

## 4. The port: concrete to-do list (in priority order)

### 4.1 Async main loop (mandatory)
pygbag needs a cooperative loop. `main.py` is synchronous today. Replace with:
```python
import asyncio, pygame
from data.settings import FPS, MAX_DT, SCREEN_H, SCREEN_W, TITLE
from game.game import Game

async def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))   # see 4.2 about SCALED
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()
    game = Game(screen)
    running = True
    while running:
        dt = min(clock.tick(FPS) / 1000.0, MAX_DT)
        game.fps = clock.get_fps()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            else:
                game.handle_event(event)
        game.update(dt)
        game.draw()
        pygame.display.flip()
        await asyncio.sleep(0)          # REQUIRED: yields to the browser every frame
    pygame.quit()

asyncio.run(main())
```
Keep a desktop path working (`python main.py` must still run). No threads, no `time.sleep`, no blocking input anywhere
(grep found none in the game code). The app folder must contain `main.py` at its root.

### 4.2 Display
`pygame.SCALED | pygame.RESIZABLE` is used now (fixed 1280x720 logic stretched to the window). Verify it in the
browser; if not, use a plain `set_mode((1280, 720))` and let the pygbag canvas/CSS scale it. The mouse must stay in
1280x720 logical coordinates (all UI hit-testing assumes it). F11 / Alt+Enter fullscreen (`_toggle_fullscreen` in
game.py) and the "Fullscreen" button in Options probably do nothing useful in a browser: hide them when
`sys.platform == "emscripten"`.

### 4.3 Loading time and the "click to start" gate
- `game/audio.py` synthesises **42 sound effects at startup in pure Python** (22050 Hz, list/array math). Expect a
  multi-second stall in WASM. Options: (a) build lazily on first play; (b) lower variants/sample rate; (c) render once
  on desktop to `.ogg` files in `assets/sfx/` (the loader already prefers `assets/sfx/<name>.ogg|wav` over synthesis;
  see `assets/sfx/README.txt`) and ship those. pygbag recommends OGG.
- Browsers block audio until a user gesture: show a "Click to start" screen before creating `Game()` (or before
  `pygame.mixer.init`), then start. Also a loading text while the scenery bakes (`game/scenery.py`, about 0.2 s native)
  and sprites cache.
- Procedural sprites are generated lazily on first use (`sprites_proc.py`, `gfx.py`, cached in dicts). First appearance
  of a new enemy kind or shape can hitch. Pre-warm during loading: call `sprites_proc.enemy_sprite` for each kind and
  frame, `tower_sprite`, `shape_sprite`, `stack_icons(0..7)`.

### 4.4 Persistence
`game/options.py` writes `options.json` next to the code (`PATH`). In the browser the file system is in memory, so
settings vanish on reload. It is already wrapped in try/except. Implement browser storage for
`sys.platform == "emscripten"` via `platform.window.localStorage.setItem/getItem` (pygbag's `platform` module) and keep
the file for desktop.

### 4.5 Performance (the main risk)
Native cost is low, but WASM is typically 3 to 10x slower. Things most likely to hurt, and what to try:
1. Full-screen alpha surfaces blitted per frame: Cartesian axis overlay (`bima.axis_surface`, only while a Graph
   Bima is selected), danger vignette (`Game._draw_vignette`), pause/options dim overlays, fx flash.
   Try: skip or draw at half resolution; Options already has "Danger glow" and "Particles: Low" switches.
2. `BLEND_RGB_ADD` glow blits (`gfx.glow`, vfx `pop`, bolts) on many objects. Cap counts when slow.
3. Per-frame `Surface.copy()` calls (ghost trail in `enemy.py`, disabled-card tint in `ui.py`). Cache instead.
4. Baked scenery is one surface blit per frame (cheap). All sprites are cached (cheap).
5. Python-level loops: enemy/tower update, curve shot sweeps (`game/curves.py`, uses a 64 px dict grid), vfx particles
   (`MAX_PARTICLES` 500, Low = 120).
Suggested approach: add an automatic quality governor: if average frame time stays above about 25 ms for 2 s, switch to
Particles Low, disable vignette/ghost trail/axis overlay, and optionally render the world at 960x540 and scale up.
Measure first with the FPS option (Options > Show FPS) in the browser.

### 4.6 Input
- Bima's formula box uses `event.unicode` from `KEYDOWN` (`game/bima_ui.py`). Verify typing works in the browser
  (letters, digits, `^ * / ( )`, Backspace, Enter) and that keys like Space/F/arrow keys do not scroll the page
  or trigger browser shortcuts while typing.
- **Mobile/touch has no on-screen keyboard** in pygbag: the Graph path is unplayable on phones. A clickable math
  keypad (`x + - * / ^ ( ) pi sin cos tan` and digits) in `bima_ui.py` is the suggested fix; the formula pattern
  presets (Graph tier 3) already work with the mouse only.
- Right-click cancels placing/aiming; make sure the browser context menu is suppressed on the canvas.

### 4.7 Compatibility checks
Code targets Python 3.12 + pygame-ce 2.5 (`from __future__ import annotations`, `X | None` only in annotations).
pygbag ships its own Python/pygame-ce: if something fails to import, check these first: `pygame.Vector2.lerp`,
`BLEND_RGBA_MIN/MULT`, `Surface.fill(..., special_flags=...)`, `pygame.transform.smoothscale/rotozoom`,
`pygame.font.Font(path, size)`, `array`/`math` in audio synthesis, `pygame.mixer.Sound(buffer=...)`.
If `Sound(buffer=...)` fails in the browser, use the OGG route in 4.3.

### 4.8 Build and test
```
pip install pygbag
pygbag .                 # run from the folder that contains main.py, serves http://localhost:8000
pygbag --build .         # produces build/web (upload to itch.io as HTML5, or any static host)
```
(Commands as documented by pygbag at the time of writing; check its current docs.) Test in Chrome/Firefox, with
the console open. Use a fresh private window when testing storage.

---

## 5. Acceptance checklist for the port
- [ ] Game starts after a click, shows the HUD, plays sounds (or degrades gracefully with no audio).
- [ ] Place a tower with the mouse and with keys 1-4; upgrade panel opens; abilities E/C/V work.
- [ ] Bima Graph: type `2x`, see the preview cost, press Enter/FIRE during a wave; errors are friendly.
- [ ] Wave 1 to 3 playable at 60 FPS (or a stable 30 with the quality governor); wave 20+ still playable.
- [ ] x2/x3 speed do not freeze the page; pause and options work.
- [ ] Options persist across a page reload (localStorage).
- [ ] No exceptions in the browser console; `python tests/...` still pass on desktop.

## 6. Do not change without asking the owner
Game rules and numbers (data/), the BTD6-style layout, "all visuals/sounds are procedural", Bima's one-path rule,
per-enemy collision cooldown, and the rule that every tunable number stays in `data/`.
Owner prefers direct, unsentimental communication; no long praise.
