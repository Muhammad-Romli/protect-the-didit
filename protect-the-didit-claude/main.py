"""Entry point: window + game loop only.

The loop is async so the same file runs on desktop (`python main.py`) and in the browser (`pygbag .`).
Flow: title menu (CONTINUE / NEW GAME) -> loading screen (Game, sounds, sprite caches) -> game.
The menu comes first on purpose: browsers only start audio after a click.
"""
import asyncio
import time
import traceback

import pygame

from data.settings import FPS, MAX_DT, SCREEN_H, SCREEN_W, TITLE
from game import audio as audio_mod
from game import menu, savegame, title, web
from game.profile import Profile

SLOW_FRAME_MS = 40.0   # browser quality governor: frames slower than this (under 25 fps) ...
SLOW_SECONDS = 5.0     # ... for this long switch to light effects once. A smooth game never triggers it.
BUDGET = 0.012         # seconds of loading work per frame, so the loading screen keeps animating


async def _menu(screen: pygame.Surface, clock: pygame.time.Clock, profile: Profile, audio=None) -> str | None:
    """Main menu + UNITS / SHOP / DEVELOPERS screens. Returns "new", "continue" or None (EXIT / window closed)."""
    screens = {"main": menu.MainMenu(profile, savegame.summary()), "units": None, "shop": None, "developers": None}
    current, t = "main", 0.0
    while True:
        t += clock.tick(FPS) / 1000.0
        obj = screens[current]
        action = None
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                action = obj.click(event.pos)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    action = "fullscreen"
                elif event.key == pygame.K_ESCAPE and current != "main":
                    action = "back"
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE) and current == "main":
                    action = obj.primary
        if action == "fullscreen":
            title.toggle_fullscreen()
        elif action == "back":
            current, screens["main"] = "main", menu.MainMenu(profile, savegame.summary())
        elif action in ("units", "shop", "developers"):
            current = action
            screens[action] = {"units": menu.UnitsScreen, "developers": menu.DevelopersScreen}.get(action, lambda: menu.ShopScreen(profile, audio))()
        elif action == "exit":
            return None
        elif action in ("play", "continue"):
            return "continue" if action == "continue" else "new"
        obj = screens[current]
        obj.draw(screen, t, pygame.mouse.get_pos())
        pygame.display.flip()
        await asyncio.sleep(0)


async def _goodbye(screen: pygame.Surface, clock: pygame.time.Clock) -> bool:
    """EXIT. Desktop: a short farewell, then the window closes. Browser: a tab cannot close itself, so offer BACK."""
    t, back = 0.0, pygame.Rect(540, 440, 200, 60)
    while True:
        t += clock.tick(FPS) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if web.IS_WEB and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and back.collidepoint(event.pos):
                return True
        title.draw_backdrop(screen, t)
        from game.utils import draw_outlined
        draw_outlined(screen, "Thanks for playing!", (SCREEN_W // 2, 300), 72, (255, 214, 90), center=True, width=5)
        if web.IS_WEB:
            draw_outlined(screen, "You can close this tab now.", (SCREEN_W // 2, 380), 30, (255, 255, 255), center=True, width=3)
            menu.button(screen, back, (255, 160, 30), "BACK", pygame.mouse.get_pos(), 30)
        elif t > 0.9:
            return False
        pygame.display.flip()
        await asyncio.sleep(0)


async def _load(screen: pygame.Surface, clock: pygame.time.Clock, profile: Profile):
    """Build the Game, synthesize sounds and warm the sprite caches while the Didit walks along the path."""
    from game.game import Game
    from game.loading import warm_steps

    st = {"t": 0.0, "shown": 0.0}

    async def tick(target: float, status: str) -> None:
        st["t"] += clock.tick(FPS) / 1000.0
        st["shown"] += (target - st["shown"]) * 0.25  # ease toward the real progress
        pygame.event.pump()
        title.draw_loading(screen, st["t"], st["shown"], status)
        pygame.display.flip()
        await asyncio.sleep(0)

    audio_mod.LAZY = True  # Game() must not synthesize every sound in one long frame
    await tick(0.02, "Starting...")
    game = Game(screen, profile)
    await tick(0.10, "Building the map...")
    sounds = 0.0
    while sounds < 1.0:
        start = time.perf_counter()
        while sounds < 1.0 and time.perf_counter() - start < BUDGET:
            sounds = game.fx.audio.build_next()
        await tick(0.10 + 0.45 * sounds, "Tuning the squeaks...")
    warm, progress = warm_steps(), 0.0
    while progress < 1.0:
        start = time.perf_counter()
        while progress < 1.0 and time.perf_counter() - start < BUDGET:
            progress = next(warm, 1.0)
        await tick(0.55 + 0.43 * progress, "Feeding the Didits...")
    for _ in range(14):  # let the bar reach 100% and show it for a moment
        await tick(1.0, "Ready!")
    pygame.event.clear()
    return game


def _draw_crash(screen: pygame.Surface, text: str) -> None:
    """The game hit an unexpected error: show it instead of freezing, so the cause can be read and fixed."""
    from game.utils import draw_outlined
    panel = pygame.Rect(80, 120, 1120, 480)
    pygame.draw.rect(screen, (40, 16, 20), panel, border_radius=16)
    pygame.draw.rect(screen, (255, 110, 100), panel, 3, border_radius=16)
    draw_outlined(screen, "The game hit an error (send this screenshot)", (panel.x + 24, panel.y + 18), 30, (255, 214, 70))
    for i, line in enumerate(text.strip().splitlines()[-14:]):
        draw_outlined(screen, line[:110], (panel.x + 24, panel.y + 66 + i * 26), 17, (255, 255, 255), width=1)
    draw_outlined(screen, "Reload the page to start again (your save is kept).", (panel.x + 24, panel.bottom - 40), 20, (180, 230, 255), width=1)


async def main() -> None:
    pygame.init()
    web.setup_page()  # browser: fit the canvas, smooth scaling, no right-click menu (no-op on desktop)
    if web.IS_WEB:  # plain surface: the page scales the canvas (mouse stays in 1280x720 coordinates)
        screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    else:
        try:  # SCALED: fixed 1280x720 logic, stretched to the window/fullscreen, mouse mapped for us
            screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.SCALED | pygame.RESIZABLE)
        except pygame.error:
            screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()

    profile = Profile.load()   # Snack Coins, shop levels, item stock (kept between runs)
    game = None
    while True:
        choice = await _menu(screen, clock, profile, game.fx.audio if game else None)
        if choice is None:
            if await _goodbye(screen, clock):
                continue   # browser: BACK to the menu
            break
        if game is None:
            game = await _load(screen, clock, profile)
        game.reset()   # fresh run with the current shop perks (a new game; CONTINUE below loads the save over it)
        if choice == "continue" and not game.load_save():
            game.flash("Could not read the save: new game", 4.0)
        if not await _play(game, clock):
            break
    pygame.quit()


async def _play(game, clock: pygame.time.Clock) -> bool:
    """One run. Returns True when the player went back to the main menu, False when the window was closed."""
    slow_for, degraded, crash = 0.0, False, None
    while not game.exit_to_menu:
        frame_ms = clock.tick(FPS)
        dt = min(frame_ms / 1000.0, MAX_DT)
        game.fps = clock.get_fps()
        if web.IS_WEB and not degraded:  # safety net for very slow devices only
            slow_for = slow_for + frame_ms / 1000.0 if frame_ms > SLOW_FRAME_MS else max(0.0, slow_for - frame_ms / 1000.0)
            if slow_for > SLOW_SECONDS:
                degraded = True
                game.options["particles"], game.options["vignette"] = "Low", False  # runtime only, not saved
                game.apply_options()
                game.flash("Slow device: switched to light effects")
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            game.handle_event(event)
        try:
            if crash is None:
                game.update(dt)
                game.draw()
        except Exception:  # never die silently: show the real error on screen (and in the console) so it can be reported
            crash = traceback.format_exc()
            print(crash)
        if crash is not None:
            _draw_crash(game.screen, crash)
        pygame.display.flip()
        await asyncio.sleep(0)  # REQUIRED in the browser: hands control back to the page every frame
    return True

if __name__ == "__main__":
    asyncio.run(main())
