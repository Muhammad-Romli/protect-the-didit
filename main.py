"""Entry point: window + game loop only."""
import pygame

from data.settings import FPS, MAX_DT, SCREEN_H, SCREEN_W, TITLE
from game.game import Game


def main() -> None:
    pygame.init()
    try:  # SCALED: fixed 1280x720 logic, stretched to the window/fullscreen, mouse mapped for us
        screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.SCALED | pygame.RESIZABLE)
    except pygame.error:
        screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
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
    pygame.quit()


if __name__ == "__main__":
    main()
