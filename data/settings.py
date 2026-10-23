"""Global tunables: window, layout, economy, rules, colors."""

TITLE = "Protect The Didit"
SCREEN_W, SCREEN_H = 1280, 720
FPS = 60
MAX_DT = 0.05  # clamp so a lag spike never teleports enemies

# Layout as (x, y, w, h). Playfield + shop on the left, side panel on the right.
PLAYFIELD_RECT = (0, 0, 1000, 640)
SHOP_RECT = (0, 640, 1000, 80)
PANEL_RECT = (1000, 0, 280, 720)

# Economy
START_MONEY = 650
START_STASH_HP = 100
SELL_REFUND = 0.70
WAVE_CLEAR_BONUS_BASE = 50
WAVE_CLEAR_BONUS_PER_WAVE = 10

# Placement / map
TOWER_RADIUS = 16
PATH_MIN_DISTANCE = 30
PATH_WIDTH = 36

# Upgrade rule: one path up to MAX_TIER, the other at most MAX_OFF_PATH_TIER
MAX_TIER = 4
MAX_OFF_PATH_TIER = 1

# Stat limits
MIN_COOLDOWN = 0.1
MAX_SLOW = 0.9
SLOW_FLOOR = 0.2        # enemies never go below 20% of base speed
BOSS_SLOW_FACTOR = 0.5  # bosses take half the slow effect

FAST_FORWARD_SPEED = 2
DEBUG_MONEY = 1000

COLORS = {
    "grass": (84, 150, 84),
    "path": (214, 183, 130),
    "path_edge": (160, 130, 85),
    "ui_bg": (34, 36, 44),
    "ui_btn": (58, 62, 76),
    "ui_btn_hover": (78, 84, 104),
    "ui_btn_off": (44, 46, 54),
    "text": (235, 235, 240),
    "text_dim": (140, 142, 152),
    "bad": (235, 90, 90),
    "good": (110, 220, 120),
    "gold": (240, 200, 70),
    "hp_bg": (90, 20, 20),
    "hp_fg": (90, 220, 90),
}
