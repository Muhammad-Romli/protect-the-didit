"""Fadhli (thrower): ALL tuning numbers live in this file. Logic: game/fadhli.py. Upgrade names/prices: data/towers.py.

Fadhli throws a heavy object slowly. Every throw has a CHARGE (wind-up) before it leaves his hand; the charge
counts as part of his attack cycle (cycle = charge + cooldown) and is sped up by attack-speed buffs.
Each Fadhli unit follows ONE path (like Jalu).

  Path A = Garp (power): Garp's marine coat. Slow, heavy cannonball throws with a long charge, splash damage,
           armor breaking and knockback. From tier 2 every landing throw leaves a HOT CRATER that burns Didits inside
           (bigger + hotter with every tier). Tier 3 "Fist of Love" deals 300% damage to BOSSES.
           Tier 4 ability "Galaxy Impact" (next throw is a mega throw).
  Path B = Johnny (spin): Johnny Joestar + Tusk. Fast steel balls that bounce between Didits and spin them in a
           tornado. Tier 4: Tusk Act 4 barrage (melee) + ability "Golden Ratio".

Names of upgrades / moves are placeholders the author can rename in data/towers.py.
"""

# -------------------------------------------------------------------------------- charge (wind-up)
# Seconds of charging before the throw leaves his hand. Garp's grows with every tier (more power = longer charge).
# Index 0 = base Fadhli: a short, INVISIBLE wind-up (no glow, cracks or shaking; it throws like a regular tower).
GARP_CHARGE = [0.15, 0.45, 0.60, 0.80, 0.95]      # index = path A tier
JOHNNY_CHARGE = 0.12                               # Johnny barely winds up

# ------------------------------------------------------------------------------ path A: Garp (power)
GARP_KNOCKBACK_DISTANCE = 34      # px pushed back along the path by every heavy hit (tier 3+)
GARP_KNOCKBACK_BOSS_MULT = 0.25   # bosses are pushed only this fraction
GARP_KNOCKBACK_INTERVAL = 1.2     # seconds: one Didit can be knocked back at most once per this time
GARP_ARC = 34                     # px: how high the lobbed cannonball flies (visual only)
GARP_PROJ_SCALE = 1.0             # sprite scale of the cannonball

GALAXY_COOLDOWN = 45.0            # seconds, starts when the ability is used
GALAXY_WINDOW = 12.0              # seconds the mega throw stays ready (it is lost if nothing is thrown)
GALAXY_DAMAGE_MULT = 5.0          # x Fadhli's damage for the mega throw (T4 damage 36 -> 180, x3 more vs a boss)
GALAXY_AOE_MULT = 2.2             # x splash radius
GALAXY_AOE_MIN = 90               # px: minimum splash radius of the mega throw
GALAXY_CHARGE_MULT = 1.7          # the mega throw charges this much longer
GALAXY_ARC = 70

# ----------------------------------------------------------------------------- path B: Johnny (spin)
BOUNCE_START_CHANCE = 0.50        # tier 2+: chance that the steel ball keeps going after a hit (else it stops)
BOUNCE_DECAY = 0.05               # the chance drops by 5 percentage points with every bounce (50, 45, 40 ...)
BOUNCE_RANGE = 140                # px: how far the ball looks for the next Didit
BOUNCE_SPEED_MULT = 1.5           # the ball flies faster between bounces
BOUNCE_MAX = 12                   # hard cap (the chance reaches 0 after 10 bounces anyway)

STATUS_STUN_CHANCE = 0.20         # tier 3+: every hit rolls once: 20% stun, 30% slow, 50% nothing
STATUS_SLOW_CHANCE = 0.30
STATUS_STUN_TIME = 1.0            # seconds (bosses are immune to stun, see Enemy.stun)
STATUS_SLOW = 0.35                # 35% slower
STATUS_SLOW_TIME = 2.0            # (bosses take half the slow, see Enemy.apply_slow)

# Tier 4: Tusk Act 4 barrage = melee attacks at the same time as the throws. The inner circle shows its range.
MELEE_RADIUS = 70                 # px (must stay smaller than the throwing range)
MELEE_INTERVAL = 0.20             # seconds between barrage ticks
MELEE_DAMAGE_MULT = 0.20          # x Fadhli's damage per tick, on EVERY Didit inside the circle
MELEE_MAX_TARGETS = 6             # safety cap per tick

# Tier 4 ability "Golden Ratio": for GOLDEN_DURATION seconds his throw damage is divided by GOLDEN_START_DIVISOR,
# then multiplied by PHI after every projectile attack (not the barrage). Example: D/4, D/4*1.618, D/4*1.618^2 ...
GOLDEN_COOLDOWN = 45.0
GOLDEN_DURATION = 5.0
GOLDEN_START_DIVISOR = 4.0
PHI = 1.618
GOLDEN_ATTACK_SPEED = 2.0         # attack-speed multiplier while Golden Ratio runs. WHY: Johnny throws only ~5 times in 5 s, and
                                  # D/4 x 1.618^n summed over 5 throws (~4.1 D) is LESS than 5 normal throws (~5.2 D), so the literal
                                  # version would be a downgrade. At x2 he throws ~10 times: ~49 D in total (about 10x). Set 1.0 for the literal rule.
GOLDEN_MAX_MULT = 100.0           # safety cap on the multiplier (x Fadhli's damage); 5 s of throws stays far below it

# Stat changes the tiers give (read by data/towers.py).
# Garp's damage: base 5.5 -> T1 +3.0 (8.5) -> T2 +7.5 (16.0) -> T3 +8.0 (24.0) -> T4 +12.0 (36.0).
# Tier 3+ ("Fist of Love") ALSO deals 300% damage to BOSSES (GARP_BOSS_MULT), e.g. T3 24 -> 72, T4 36 -> 108.
FADHLI_BASE_DAMAGE = 5.5
GARP_BOSS_MULT = 3.0              # x damage against bosses, from Garp tier 3 (also applies to the Galaxy Impact mega throw)
GARP_BOSS_MULT_MIN_TIER = 3
GARP_STATS = [
    {"damage": 3.0, "range": 10},                                        # T1 Marine coat
    {"damage": 7.5, "cooldown": 0.2, "aoe_radius": 36},                  # T2 Iron Fist (+ crater)
    {"damage": 8.0, "cooldown": 0.1, "aoe_radius": 18},                  # T3 Fist of Love (x3 vs bosses)
    {"damage": 12.0, "aoe_radius": 12, "range": 15},                     # T4 Galaxy Impact
]

# ------------------------------------------------------------ hot crater (Garp tier 2+)
# Every Garp throw that lands leaves a crater at the impact point. Didits standing in it are burned every CRATER_TICK
# seconds. Radius, burn damage per tick and lifetime grow with the tier. Armored Didits are not burned (the armor shields them).
CRATER_TICK = 0.5
CRATER_TIERS = {                      # path A tier -> crater
    2: {"radius": 34, "damage": 1.2, "seconds": 3.0},
    3: {"radius": 50, "damage": 3.0, "seconds": 4.0},
    4: {"radius": 68, "damage": 5.5, "seconds": 5.0},
}
CRATER_MEGA_RADIUS_MULT = 1.8         # the Galaxy Impact mega throw leaves a much bigger crater
CRATER_MEGA_DAMAGE_MULT = 2.0
CRATER_MEGA_SECONDS_MULT = 1.5
CRATER_MAX = 14                       # oldest craters vanish first (performance + balance)

JOHNNY_STATS = [
    {"cooldown": -0.7},                                                  # T1 Spin practice (cheap, faster)
    {"damage": 1.0},                                                     # T2 Tusk Act 1 (+ bounce)
    {"damage": 1.5, "cooldown": -0.15, "range": 15},                     # T3 Tusk Act 3 (+ stun/slow)
    {"damage": 2.0, "cooldown": -0.1, "range": 10},                      # T4 Tusk Act 4 (+ barrage, Golden Ratio)
]
