"""Tunable parameters for the named special effects in game/effects.py."""

EFFECT_PARAMS = {
    # Jalu path A (Mark): all numbers are in data/mark.py
    # Jalu path B
    "time_push": {"chance": 0.20, "distance": 80},
    "speed_against_time": {"duration": 3.0},  # fast enemies walk at normal speed; refreshed by every hit
    # Zizi path A (auras: strongest source wins, they do not stack)
    "aura_attack_speed_10": {"bonus": 0.10, "radius": 150},
    "aura_attack_speed_20": {"bonus": 0.20, "radius": 150},
    "aura_attack_speed_30": {"bonus": 0.30, "radius": 150},
    # Zizi path B
    "damage_debuff_15": {"mult": 1.15},
    "sleep_chance": {"chance": 0.20, "duration": 1.5},
    # Romli path A
    "upgrade_discount_aura": {"discount": 0.05, "radius": 150},
    "boss_kill_bonus": {"bonus": 500},
    # Romli path B
    "armor_breaker": {"hits": 3},  # one hit counts as this many against armor
}
