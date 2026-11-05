"""Balance knobs for Fadhli, the petanque athlete. Logic: game/fadhli.py. Tier stats and prices: data/towers.py."""

# --- Power path ---------------------------------------------------------------------------------
INFINITE_RANGE = 10000        # Power T4 adds this much range: anything >= this counts as infinite (no range ring)
SKY_ARC_HEIGHT = 95           # px: peak height of the Sky shot's visual arc
CRATER_RADIUS = 58
CRATER_DURATION = 3.2
CRATER_DPS = 5.0
CRATER_TICK = 0.5             # seconds between crater hits; each hit deals DPS * tick (armor loses 1 per hit)
POWER_SHOTS = 3               # empowered shots per Meteor activation
POWER_SHOT_MULT = 3.5         # damage multiplier of an empowered shot
POWER_CRATER_RADIUS = 105
POWER_CRATER_DPS = 14.0
POWER_COOLDOWN = 36.0

# --- Accuracy path ------------------------------------------------------------------------------
BOUNCE_TARGETS = 2            # extra targets after the first (3 enemies per shot in total)
BOUNCE_RADIUS = 140           # px: how far the boule can jump from the last enemy it hit
STUN_CHANCE = 0.20            # steel boule: one roll per hit -> 20% stun, 30% slow, 50% nothing
SLOW_CHANCE = 0.30
STUN_DURATION = 0.65
SLOW_STRENGTH = 0.35
SLOW_DURATION = 2.2
SPIN_DURATION = 2.5           # Spinned look (Arigatou, Gyro)
SPIN_BOSS_DURATION = 0.8      # bosses: shorter look, never stunned
SPIN_STUN = 0.6
GOLDEN_RATIO = 1.618
GOLDEN_START_FRACTION = 0.25  # first shot of the active = 1/4 of normal damage, each next shot x GOLDEN_RATIO
GYRO_DURATION = 5.0
GYRO_COOLDOWN = 32.0
