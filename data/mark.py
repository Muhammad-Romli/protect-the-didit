"""Mark (Jalu path A, inspired by Mark from Invincible): ALL tuning numbers live in this file.

Mark is a melee brawler: short range, very fast punches that hit every Didit in a small radius around the
target. His weakness is placement: with so little range he only works well on the corners of the path.
Logic: game/mark.py.  Upgrade entries (names, prices): data/towers.py (prices are the same as the old path A).
All names below are placeholders the author can rename in data/towers.py.
"""

# --------------------------------------------------------------- Tier 1: "Flying Punch"
T1_COOLDOWN_CHANGE = -0.45   # seconds added to Jalu's 0.8s attack interval -> 0.35s ("large attack speed increase")
T1_RANGE_CHANGE = -75        # px added to Jalu's range 150 -> 75 (short range: the melee trade-off)
HIT_RADIUS = 28              # px: every Didit within this distance of the punched target is hit too

# ---------------------------------------------------------- Tier 2: "Viltrumite Strength"
T2_DAMAGE_BONUS = 0.5        # extra damage per punch (Jalu base damage is 2)
KNOCKBACK_DISTANCE = 8      # px pushed back ALONG THE PATH by every punch (many punches per second: keep it small)
KNOCKBACK_INTERVAL = 2.0     # seconds: one Didit can be knocked back at most once per this time (stops pin-in-place lock)
KNOCKBACK_BOSS_MULT = 0.25   # bosses are pushed only this fraction of KNOCKBACK_DISTANCE

# ------------------------------------------------------------- Tier 3: "Think, Mark!"
T3_HIT_RADIUS_BONUS = 6      # px added to HIT_RADIUS ("slightly bigger attack radius")
RAGE_BONUS_PER_STACK = 0.04  # +4% damage per stack (1 stack = 1 consecutive hit on the same target)
RAGE_MAX_STACKS = 10         # cap -> at most +40% damage

# ------------------------------------------------------------------ Tier 4: "Sweep"
SWEEP_COOLDOWN = 70.0        # seconds; starts when the ability is used
SWEEP_VANISH_TIME = 0.35     # seconds between Mark vanishing and the sweeper appearing at the exit
SWEEP_SPEED = 900.0          # px/s, constant. The path is ~3570 px long
SWEEP_DURATION = 4.0         # seconds the sweeper runs (it also stops if it reaches the path start)
SWEEP_RADIUS = 60            # px: every Didit this close to the sweeper is hit
SWEEP_HITS_PER_ENEMY = 2     # N: one Didit can be hit at most this many times per sweep
SWEEP_HIT_INTERVAL = 0.06    # seconds between two hits on the same Didit (so a fast sweeper can hit it twice)
SWEEP_DAMAGE_MULT = 25.0     # damage per hit = Mark's current damage x this
SWEEP_BOSS_DAMAGE_MULTIPLIER = 1.0   # bosses take this much of the sweep damage (1.0 = full; nerf here later, no hard cap)

# Stat changes the tiers give (read by data/towers.py; "aoe_radius" = the punch radius).
TIER_STATS = [
    {"cooldown": T1_COOLDOWN_CHANGE, "range": T1_RANGE_CHANGE, "aoe_radius": HIT_RADIUS},
    {"damage": T2_DAMAGE_BONUS},
    {"aoe_radius": T3_HIT_RADIUS_BONUS},
    {},
]
