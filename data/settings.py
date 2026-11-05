"""Global tunables: window, layout, economy, rules, colors."""

TITLE = "Protect The Didit"
SCREEN_W, SCREEN_H = 1280, 720
FPS = 60
MAX_DT = 0.05  # clamp so a lag spike never teleports enemies

# Damage popups appear only for large hits; fonts and colors escalate by stage.
DAMAGE_STAGES = ((8, 20, (255, 210, 70)), (18, 25, (255, 115, 35)),
                 (40, 31, (230, 35, 45)), (80, 39, (110, 20, 70)))

# Layout as (x, y, w, h). BTD6-style: the map fills the whole window, the HUD floats on top,
# a wooden bar sits at the bottom. Towers can only be placed above the bar (BUILD_RECT).
PLAYFIELD_RECT = (0, 0, 1280, 720)
BAR_RECT = (0, 636, 1280, 84)
BUILD_RECT = (0, 0, 1280, 636)
WORLD_CENTER = (640, 300)  # where big banners ("WAVE 3!") pop up

# Economy (faster progression, 2026-10-25): kills pay BOUNTY_MULT x the base bounty in data/enemies.py,
# and the payout grows by BOUNTY_WAVE_GROWTH per wave so income keeps up with the stronger late waves.
START_MONEY = 750
START_STASH_HP = 100
SELL_REFUND = 0.70
BOUNTY_MULT = 2.0
BOUNTY_WAVE_GROWTH = 0.08
WAVE_CLEAR_BONUS_BASE = 100
WAVE_CLEAR_BONUS_PER_WAVE = 35

# Placement / map
TOWER_RADIUS = 18
PATH_MIN_DISTANCE = 42   # tower centre to path centre line (path half width 24 + tower radius 18)
PATH_WIDTH = 48

# Upgrade rule: one path up to MAX_TIER, the other at most MAX_OFF_PATH_TIER
MAX_TIER = 4
MAX_OFF_PATH_TIER = 1

# Stat limits
MIN_COOLDOWN = 0.1
MAX_SLOW = 0.9
SLOW_FLOOR = 0.2        # enemies never go below 20% of base speed
BOSS_SLOW_FACTOR = 0.5  # bosses take half the slow effect

SPEED_STEPS = (1, 2, 3)  # game speed button / F key cycles through these

# Preparation phase: time keeps moving; the longer you wait, the stronger the next wave.
# Ramp is linear from GRACE (x1) to MAX (full multipliers), then the wave starts by force.
PREP_GRACE_SECONDS = 20
PREP_MAX_SECONDS = 90
PREP_MAX_HP_MULT = 3.0
PREP_MAX_SPEED_MULT = 1.3
SELL_CONFIRM_SECONDS = 3.0  # second click on Sell must come within this time
INCOME_INTERVAL_SECONDS = 10  # Romli's per-second income is paid out in one lump every 10s
MAX_ACTIVITIES = 3  # simultaneous tower activities (those with counts_toward_limit)
DEBUG_MONEY = 1000
DEBUG_KNOWLEDGE = 100  # F2 also gives this much ball knowledge

COLORS = {
    "grass": (104, 178, 56),
    "path": (170, 162, 150),
    "path_edge": (96, 88, 80),
    "ui_bg": (34, 36, 44),
    "ui_btn": (58, 62, 76),
    "ui_btn_hover": (78, 84, 104),
    "ui_btn_off": (44, 46, 54),
    "text": (255, 255, 255),
    "text_dim": (200, 205, 220),
    "bad": (255, 110, 100),
    "good": (130, 240, 110),
    "gold": (255, 214, 70),
    "hp_bg": (60, 14, 14),
    "hp_fg": (110, 230, 80),
    # BTD6-style UI palette
    "wood": (150, 104, 60),
    "wood_light": (190, 140, 84),
    "wood_dark": (96, 64, 36),
    "ink": (38, 24, 18),          # text outline
    "btn_green": (70, 200, 50),
    "btn_blue": (60, 160, 235),
    "btn_orange": (255, 160, 30),
    "btn_red": (225, 70, 60),
    "navy": (34, 52, 104),
}

# Autosave: a snapshot is stored (browser localStorage / savegame.json) after every Nth cleared wave
SAVE_EVERY_WAVES = 3
