"""Entry point: window + game loop only.

The loop is async so the same file runs on desktop (`python main.py`) and in the browser (`pygbag .`).
In the browser it first waits for a click (browsers block audio until a user gesture), then shows a loading bar
while sounds are synthesized and sprite caches are warmed.
"""
import asyncio

import pygame

from data.settings import FPS, MAX_DT, SCREEN_H, SCREEN_W, TITLE
from game import audio as audio_mod
from game import web
from game.utils import draw_outlined

SLOW_FRAME_MS = 25.0   # browser quality governor: average frame time above this ...
SLOW_SECONDS = 2.0     # ... for this long switches to the light visual settings (once)


def _splash(screen: pygame.Surface, title: str, subtitle: str, progress: float | None = None) -> None:
    screen.fill((28, 44, 30))
    draw_outlined(screen, title, (SCREEN_W // 2, SCREEN_H // 2 - 50), 64, (255, 214, 90), center=True, width=4)
    draw_outlined(screen, subtitle, (SCREEN_W // 2, SCREEN_H // 2 + 30), 30, (255, 255, 255), center=True)
    if progress is not None:
        bar = pygame.Rect(0, 0, 420, 22)
        bar.center = (SCREEN_W // 2, SCREEN_H // 2 + 90)
        pygame.draw.rect(screen, (20, 28, 22), bar, border_radius=8)
        fill = bar.copy()
        fill.w = int(bar.w * max(0.0, min(1.0, progress)))
        if fill.w > 0:
            pygame.draw.rect(screen, (110, 220, 110), fill, border_radius=8)
        pygame.draw.rect(screen, (255, 255, 255), bar, 2, border_radius=8)
    pygame.display.flip()


async def _wait_for_click(screen: pygame.Surface) -> bool:
    """Browser only. Returns False if the window was closed."""
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                return True
        _splash(screen, TITLE, "Click to start")
        await asyncio.sleep(0)


async def _load_web(screen: pygame.Surface):
    """Browser only: build the Game, then synthesize sounds and warm sprite caches with a progress bar."""
    from game.game import Game
    from game.loading import warm_steps

    audio_mod.LAZY = True  # Game() must not synthesize all sounds in one long frame
    _splash(screen, TITLE, "Loading...", 0.0)
    await asyncio.sleep(0)
    game = Game(screen)
    sounds = 0.0
    while sounds < 1.0:
        sounds = game.fx.audio.build_next()
        _splash(screen, TITLE, "Loading sounds...", 0.5 * sounds)
        await asyncio.sleep(0)
    for progress in warm_steps():
        _splash(screen, TITLE, "Loading sprites...", 0.5 + 0.5 * progress)
        await asyncio.sleep(0)
    return game


async def main() -> None:
    pygame.init()
    if web.IS_WEB:  # plain surface: the pygbag canvas does the scaling (mouse stays in 1280x720 coordinates)
        screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    else:
        try:  # SCALED: fixed 1280x720 logic, stretched to the window/fullscreen, mouse mapped for us
            screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.SCALED | pygame.RESIZABLE)
        except pygame.error:
            screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()

    if web.IS_WEB:
        web.suppress_context_menu()
        if not await _wait_for_click(screen):
            return
        game = await _load_web(screen)
    else:
        from game.game import Game
        game = Game(screen)

    slow_for, degraded = 0.0, False
    running = True
    while running:
        frame_ms = clock.tick(FPS)
        dt = min(frame_ms / 1000.0, MAX_DT)
        game.fps = clock.get_fps()
        if web.IS_WEB and not degraded:  # quality governor: stay playable on slow machines
            slow_for = slow_for + frame_ms / 1000.0 if frame_ms > SLOW_FRAME_MS else max(0.0, slow_for - frame_ms / 1000.0)
            if slow_for > SLOW_SECONDS:
                degraded = True
                game.options["particles"], game.options["vignette"] = "Low", False  # not saved: runtime only
                game.apply_options()
                game.flash("Slow device: switched to light effects")
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            else:
                game.handle_event(event)
        game.update(dt)
        game.draw()
        pygame.display.flip()
        await asyncio.sleep(0)  # REQUIRED in the browser: hands control back to the page every frame
    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
