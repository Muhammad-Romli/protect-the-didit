"""Shop data (main menu). Shopkeeper: A'yun. Currency: Snack Coins (earned at the end of every run).

PERMANENT items have levels: each level is bought once and the buff applies to EVERY later run.
  fields: name, desc, icon, per_level (value of one level), costs (price of level 1, 2, ...), unit (for the text)
IN-GAME items are consumables (like BTD6 Powers): bought in stacks, one is used up per use during a run.
  fields: name, desc, icon, cost, max_per_run (uses allowed in one run), plus the tunables read by game/powers.py
Logic: game/profile.py (ownership + saving), game/powers.py (in-game effects), game/game.py (perk hooks).
"""

SHOPKEEPER = "A'yun"
MAX_STOCK = 99   # most of one in-game item you can hold

PERM_ORDER = ["allowance", "crate", "discount", "wallet", "tools", "haggler", "notes", "booster"]
PERMANENT = {
    "allowance": {"name": "Bigger Allowance", "icon": "allowance", "per_level": 60, "unit": "$",
                  "desc": "Start every run with more money.", "costs": [80, 160, 260, 400, 600]},
    "crate": {"name": "Sturdy Crate", "icon": "crate", "per_level": 10, "unit": " HP",
              "desc": "The Snack Stash starts with more HP.", "costs": [100, 200, 320, 480, 700]},
    "discount": {"name": "Friendly Discount", "icon": "discount", "per_level": 0.03, "unit": "%",
                 "desc": "Tower upgrades cost less.", "costs": [120, 240, 380, 560, 800]},
    "wallet": {"name": "Lucky Wallet", "icon": "wallet", "per_level": 0.04, "unit": "%",
               "desc": "Every Didit pays a bigger bounty.", "costs": [120, 240, 380, 560, 800]},
    "tools": {"name": "Sharp Tools", "icon": "tools", "per_level": 0.03, "unit": "%",
              "desc": "All towers deal more damage.", "costs": [150, 300, 480, 700, 1000]},
    "haggler": {"name": "Haggler's Gloves", "icon": "haggler", "per_level": 0.04, "unit": "%",
                "desc": "Selling a tower refunds more.", "costs": [100, 220, 400]},
    "notes": {"name": "Study Notes", "icon": "notes", "per_level": 10, "unit": " KN",
              "desc": "Start with ball knowledge for Jalu's upgrades.", "costs": [80, 160, 260, 400, 600]},
    "booster": {"name": "Coin Booster", "icon": "booster", "per_level": 0.10, "unit": "%",
                "desc": "Earn more Snack Coins at the end of a run.", "costs": [200, 450, 800]},
}

ITEM_ORDER = ["cash_drop", "stash_patch", "freeze_bomb", "espresso", "ball_scroll", "insta_jalu"]
ITEMS = {
    "cash_drop": {"name": "Cash Drop", "icon": "cash_drop", "cost": 60, "max_per_run": 3, "amount": 400,
                  "desc": "Instantly gives $400."},
    "stash_patch": {"name": "Stash Patch", "icon": "stash_patch", "cost": 50, "max_per_run": 3, "amount": 25,
                    "desc": "Repairs 25 HP of the Snack Stash."},
    "freeze_bomb": {"name": "Freeze Bomb", "icon": "freeze_bomb", "cost": 80, "max_per_run": 3, "seconds": 4.0,
                    "desc": "Freezes every Didit for 4s (bosses are only slowed)."},
    "espresso": {"name": "Espresso Shot", "icon": "espresso", "cost": 70, "max_per_run": 3, "seconds": 12.0, "bonus": 0.5,
                 "desc": "All towers attack 50% faster for 12s."},
    "ball_scroll": {"name": "Ball Knowledge Scroll", "icon": "ball_scroll", "cost": 50, "max_per_run": 3, "amount": 30,
                    "desc": "Instantly gives 30 ball knowledge."},
    "insta_jalu": {"name": "Insta-Jalu", "icon": "insta_jalu", "cost": 120, "max_per_run": 2, "tiers": (2, 0),
                   "desc": "Place a free Jalu with Mark tier 2 already unlocked (sells for $0)."},
}

# Speech bubbles for A'yun (one is picked at random)
LINES = {
    "welcome": ["Welcome! Take a look around.", "Fresh stock today. Snack Coins only!", "Everything here helps the Stash."],
    "bought": ["Pleasure doing business!", "Good pick. Use it well.", "Sold! Thank you."],
    "poor": ["Not enough Snack Coins, sorry.", "Come back after another run!"],
    "maxed": ["You already own the best one.", "That one is fully upgraded!"],
    "full": ["Your bag is full of those."],
}
