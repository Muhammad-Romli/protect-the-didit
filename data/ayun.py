"""A'yun (shopkeeper, 6th tower): ALL tuning numbers live in this file. Logic: game/ayun.py. Art: game/ayun_art.py.
Upgrade names / prices: data/towers.py.

A'yun has NO upgrade paths (to be discussed later): she has one linear track of 4 upgrades.
  Passive (from the start): when she kills a Didit she SELLS it: extra money (SELL_BONUS x its bounty).
  Upgrade 1 "Gacha Stall": she can ROLL an item with in-match money (key E / the ROLL button).
  Every stored item IS an attack: it throws itself at the nearest-to-exit Didit on its OWN cooldown
  (sword every 2s, dragon sauce every 5s ...), all stored items in parallel. Items expire after a while
  (battle seconds only) or can be sold for a cheap price. She also keeps a weak plain throw (her base attack).
  Upgrade 4 "Supply Chain": active ability AUTO-ROLL (key C): one roll every 15s for 150 money per minute.
  Passive "Steady Supply": the longer since her last manual roll, the better the auto-roll odds
  (they start at the upgrade 3 odds and grow towards the upgrade 4 odds).
All names / numbers are placeholders the author can change.
"""

RARITIES = ("junk", "common", "rare", "legendary")
RARITY_LABEL = {"junk": "Junk", "common": "Common", "rare": "Rare", "legendary": "Legendary"}
RARITY_COLOR = {"junk": (176, 176, 188), "common": (130, 226, 130), "rare": (112, 178, 255), "legendary": (255, 208, 72)}

# ------------------------------------------------------------------------------ rolling (index = upgrade tier 1..4)
ROLL_COST = {1: 90, 2: 80, 3: 70, 4: 65}          # money per manual roll
STOCK_CAP = {1: 2, 2: 4, 3: 4, 4: 4}              # items she can hold at once
# Odds in percent (junk / common / rare / legendary). Upgrade 1 is deliberately bad. Upgrade 4 was nerfed slightly
# (it was 10 / 40 / 38 / 12 in the first proposal).
ODDS = {
    1: {"junk": 55, "common": 38, "rare": 7, "legendary": 0},
    2: {"junk": 40, "common": 45, "rare": 15, "legendary": 0},
    3: {"junk": 25, "common": 45, "rare": 25, "legendary": 5},
    4: {"junk": 14, "common": 44, "rare": 33, "legendary": 9},
}
PITY_MIN_TIER = 3        # from this upgrade on ...
PITY_AFTER = 6           # ... the 6th manual roll in a row without a Rare or better is a guaranteed Rare

# --------------------------------------------------------------- upgrade 4: Supply Chain + Steady Supply
AUTO_MIN_TIER = 4
AUTO_INTERVAL = 15.0            # seconds between automatic rolls (battle only)
AUTO_COST_PER_MINUTE = 150      # money per minute of auto-rolling -> 37.5 per roll
STEADY_SECONDS = 90.0           # seconds without a manual roll until the auto odds have fully grown (up3 odds -> up4 odds)
PROMPT_SECONDS = 8.0            # replace-or-sell pop-up: if you do nothing, the new item is sold

# ------------------------------------------------------------------------------------ passive: selling Didits
SELL_BONUS = 0.30               # extra money = this x the Didit's bounty, for every Didit she kills (any of her attacks)
SELL_BONUS_APPRAISAL = 0.50     # from upgrade 3 (Loyalty Card: she appraises everything better)
APPRAISAL_MIN_TIER = 3

# ---------------------------------------------------------------------------------------- selling / lifetime
SELL_VALUE = {"junk": 10, "common": 25, "rare": 50, "legendary": 120}     # cheap, by design (a roll costs 65-90)
LIFETIME = {"junk": 45.0, "common": 80.0, "rare": 110.0, "legendary": 150.0}   # BATTLE seconds until the item expires
FIRST_THROW_DELAY = 0.4         # a fresh item throws for the first time after this many seconds

# ------------------------------------------------------------------------------------------------- the items
# cd = seconds between throws. dmg = damage per hit. aoe = splash radius (px). slow = (strength, seconds).
# special: armor3 = counts as 3 hits on armor; mark = +25% damage taken for 5s; puddle = leaves a burning puddle;
#          double = a Didit killed by this item pays its bounty twice; triple = throws at up to 3 different Didits.
ITEMS = {
    "spoon":    {"name": "Wooden Spoon",      "rarity": "junk",      "cd": 1.6, "dmg": 1.5, "aoe": 0,  "slow": None, "speed": 420,
                 "desc": "A weak, quick whack."},
    "duck":     {"name": "Rubber Duck",       "rarity": "junk",      "cd": 2.2, "dmg": 1.0, "aoe": 0,  "slow": (0.25, 1.5), "speed": 380,
                 "desc": "Squeaks. Slows a little."},
    "sword":    {"name": "Sword",             "rarity": "common",    "cd": 2.0, "dmg": 7.0, "aoe": 0,  "slow": None, "speed": 460,
                 "desc": "One solid hit every 2s."},
    "pan":      {"name": "Frying Pan",        "rarity": "common",    "cd": 2.5, "dmg": 5.0, "aoe": 0,  "slow": None, "speed": 400,
                 "special": "armor3", "desc": "Breaks armor: 1 hit counts as 3."},
    "tomato":   {"name": "Rotten Tomato",     "rarity": "common",    "cd": 2.2, "dmg": 3.0, "aoe": 45, "slow": (0.30, 2.0), "speed": 360,
                 "desc": "Splash and a 30% slow."},
    "sauce":    {"name": "Dragon Sauce",      "rarity": "rare",      "cd": 5.0, "dmg": 14.0, "aoe": 75, "slow": None, "speed": 340,
                 "special": "puddle", "desc": "Big splash + a burning puddle."},
    "tag":      {"name": "Price Tag",         "rarity": "rare",      "cd": 3.0, "dmg": 4.0, "aoe": 0,  "slow": None, "speed": 480,
                 "special": "mark", "desc": "Marks a Didit: +25% damage for 5s."},
    "register": {"name": "Golden Register",   "rarity": "legendary", "cd": 6.0, "dmg": 40.0, "aoe": 90, "slow": None, "speed": 330,
                 "special": "double", "desc": "Huge splash. Kills pay double."},
    "lamp":     {"name": "Genie's Lamp",      "rarity": "legendary", "cd": 4.0, "dmg": 12.0, "aoe": 0,  "slow": None, "speed": 520,
                 "special": "triple", "desc": "Three bolts at three Didits."},
}
ITEMS_BY_RARITY = {r: [k for k, v in ITEMS.items() if v["rarity"] == r] for r in RARITIES}

# dragon sauce puddle (burns Didits standing in it; armored Didits are shielded, like Garp's craters)
PUDDLE_RADIUS = 50
PUDDLE_DAMAGE = 3.0             # per tick
PUDDLE_TICK = 0.5
PUDDLE_SECONDS = 4.0
PUDDLE_MAX = 10                 # oldest puddles vanish first (performance)

MARK_BONUS = 0.25               # Price Tag: +25% damage taken ...
MARK_SECONDS = 5.0              # ... for this long
