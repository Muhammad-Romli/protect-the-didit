"""Phone / tablet tunables (1280x720 game space). Logic: game/touch.py. Layout hooks: game/ui.py, game/bima_ui.py."""

TOUCH_PICK_BONUS = 16     # extra radius when tapping a tower (fingertips are fat)
TOUCH_GHOST_LIFT = 64     # while dragging, the placement ghost floats this far above the finger
TOUCH_DRAG_START = 12     # px of finger travel before a tap counts as a drag
TOUCH_SLOP = 8            # invisible extra hit area around small panel buttons
TOUCH_GEAR = (1196, 6, 72, 72)   # bigger options button (replaces the 58x58 one)
CONFIRM_SIZE = 84         # round OK / cancel buttons shown next to the ghost
AGAIN_RECT = (500, 440, 280, 76)  # PLAY AGAIN button on the win / lose screen

KEYPAD_RECT = (322, 322, 630, 304)   # Bima formula keypad, sits right above the wooden bar
KEYPAD_COLS = 8
KEYPAD_PAD = 10
KEYPAD_GAP = 8
KEY_FLASH_SECONDS = 0.12

# Bigger formula console for fingers (replaces the rects in game/bima_ui.py)
GRAPH_TOUCH = {
    "input": (330, 642, 330, 46),
    "fire_btn": (668, 642, 96, 46),
    "dir_btn": (772, 642, 80, 46),
    "pat_btn": (860, 642, 118, 46),
    "bar": (330, 694, 330, 16),
}
