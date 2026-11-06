"""Tower + upgrade data. Pass 1: every tier works through `stat_mods` alone.
`effects` names special behaviours that arrive in later passes (see game/effects.py);
until they are registered there, they are ignored and the UI says so.
`voice_line` is a key into data/dialogue.py (Jalu only)."""

DEFAULT_STATS = {
    "damage": 0.0,
    "cooldown": 1.0,
    "range": 100.0,
    "proj_speed": 400.0,
    "aoe_radius": 0.0,       # >0: projectile explodes and hits everything in radius
    "slow": 0.0,             # 0.15 = -15% speed
    "slow_duration": 0.0,
    "income_per_wave": 0.0,
    "income_per_sec": 0.0,
    "money_per_hit": 0.0,
}

from data.mark import TIER_STATS as MARK_STATS

TOWER_ORDER = ["jalu", "romli", "zizi", "bima"]


def _up(name, cost, description, stat_mods=None, effects=None, voice_line=None):
    return {"name": name, "cost": cost, "knowledge": 0, "description": description,
            "stat_mods": stat_mods or {}, "effects": effects or [], "voice_line": voice_line}


TOWERS = {
    # Bima the Mathematician: path A = Graph (formula curves), path B = Geometry (shape stacks).
    # Only ONE path can be used (Tower.can_upgrade). Numbers: data/bima.py, logic: game/bima.py.
    "bima": {
        "name": "Bima", "color": (255, 160, 70), "cost": 400,
        "stats": {"damage": 1.5, "cooldown": 1.0, "range": 140, "proj_speed": 420},
        "paths": [
            {"name": "Graph", "tiers": [
                _up("Math gets easier", 150, "Graphs click: more damage and attack speed.",
                    {"damage": 0.5, "cooldown": -0.1}),
                _up("Cartesian plane", 350, "Axis with Bima at (0,0). Type formulas to fire curves (Brain Energy).",
                    {}, ["graph_axis"]),
                _up("Pattern book", 600, "Preset formulas with adjustable parameters. Typing still works.",
                    {"damage": 0.5}, ["graph_patterns"]),
                _up("Calculus", 1300, "Unlocks sin, cos, tan, ln, exp. Longer, cheaper curves.",
                    {"damage": 1}, ["graph_advanced"]),
            ]},
            {"name": "Geometry", "tiers": [
                _up("Shapes", 150, "Shots become squares, triangles, circles. More damage.",
                    {"damage": 0.5}, ["geo_shapes"]),
                _up("Shape effects", 350, "Square: +25% dmg taken. Triangle: x1.5. Circle: slow. All 3 = collision!",
                    {}, ["geo_effects"]),
                _up("Solid geometry", 600, "Cube, pyramid, sphere: stronger effects and collision.",
                    {"damage": 0.5}, ["geo_3d"]),
                _up("Euclid's mastery", 1300, "Actives: Cube wall, Pyramid buff, Sphere shield + trap.",
                    {"damage": 1}, ["cube_active", "pyramid_active", "sphere_active"]),
            ]},
        ],
    },
    # ------------------------------------------------------------------ Jalu
    # Path A = Mark, path B = Temporal Loom. Each Jalu UNIT is locked to one path (Tower.can_upgrade):
    # the first upgrade bought in a path locks the other one for that unit.
    "jalu": {
        "name": "Jalu", "color": (80, 140, 255), "cost": 200,
        "stats": {"damage": 2, "cooldown": 0.8, "range": 150, "proj_speed": 450},
        "paths": [
            {"name": "Mark", "tiers": [   # numbers: data/mark.py, logic: game/mark.py
                _up("Flying Punch", 120, "Short-range brawler. Much faster punches that hit a small area.",
                    MARK_STATS[0], ["mark_melee"], "jalu_a1"),
                _up("Viltrumite Strength", 300, "More damage. Hits knock Didits back (bosses barely move).",
                    MARK_STATS[1], ["mark_knockback"], "jalu_a2"),
                _up("Think, Mark!", 500, "Rage: more damage per consecutive hit on one target. Bigger radius.",
                    MARK_STATS[2], ["mark_rage"], "jalu_a3"),
                _up("Sweep", 1100, "Active: Mark vanishes, a sweeper runs the path backwards.",
                    MARK_STATS[3], ["sweep_active"], "jalu_a4"),
            ]},
            {"name": "Temporal Loom Guy", "tiers": [
                _up("Costume & scepter", 120, "Small damage and range boost.",
                    {"damage": 0.5, "range": 20}, voice_line="jalu_b1"),
                _up("Magic bolts", 300, "Bolts apply a short slow.",
                    {"damage": 0.5, "slow": 0.2, "slow_duration": 1.0}, voice_line="jalu_b2"),
                _up("The Temporal Loom", 500, "Hits push enemies back (not bosses). Speed Against Time: hit fast Didits walk at normal speed 3s.",
                    {"damage": 1, "slow": 0.1}, ["time_push", "speed_against_time"], "jalu_b3"),
                _up("Loom Reset", 1100, "Active: push back + freeze enemies in range 2s. Stronger attacks.",
                    {"damage": 3, "range": 20, "cooldown": -0.15}, ["loom_reset_active"], "jalu_b4"),
            ]},
        ],
    },
    # ----------------------------------------------------------------- Romli
    "romli": {
        "name": "Romli", "color": (80, 200, 120), "cost": 250,
        "stats": {"damage": 1, "cooldown": 1.2, "range": 130, "proj_speed": 380,
                  "income_per_wave": 25},
        "paths": [
            {"name": "Farm / Business", "tiers": [
                _up("Side hustle", 130, "More income per wave.", {"income_per_wave": 25}),
                _up("Small business", 300, "More income per wave, plus a little per second.",
                    {"income_per_wave": 35, "income_per_sec": 0.5}),
                _up("Company", 550, "Big income boost. Nearby towers: -5% upgrade cost.",
                    {"income_per_wave": 100, "income_per_sec": 1.0}, ["upgrade_discount_aura"]),
                _up("Empire", 1200, "Huge income per wave + bonus on boss kill.",
                    {"income_per_wave": 300, "income_per_sec": 2.0}, ["boss_kill_bonus"]),
            ]},
            {"name": "Programmer", "tiers": [
                _up("Decoder", 130, "Attacks give a small money bonus per hit.",
                    {"money_per_hit": 1}),
                _up("Better code", 320, "Faster attacks, more money per hit. Breaks armor: 1 hit counts as 3.",
                    {"cooldown": -0.3, "money_per_hit": 1, "damage": 0.5}, ["armor_breaker"]),
                _up("Random event", 550, "Every 20s: +10% money / attack-speed boost / bug.",
                    {"damage": 1, "money_per_hit": 1}, ["random_event"]),
                _up("Stronger events", 1200, "Stronger event outcomes. Higher base damage.",
                    {"damage": 3}, ["random_event_strong"]),
            ]},
        ],
    },
    # ------------------------------------------------------------------ Zizi
    "zizi": {
        "name": "Zizi", "color": (200, 110, 220), "cost": 300,
        "stats": {"damage": 1, "cooldown": 1.4, "range": 120, "proj_speed": 300,
                  "aoe_radius": 60, "slow": 0.15, "slow_duration": 1.5},
        "paths": [
            {"name": "Recitation", "tiers": [
                _up("Aura", 130, "Small AoE damage up, stronger slow.",
                    {"damage": 0.5, "slow": 0.1}),
                _up("Buff aura", 300, "Nearby towers get +10% attack speed.",
                    {"cooldown": -0.2}, ["aura_attack_speed_10"]),
                _up("Wide recitation", 500, "Bigger AoE, buff +20%, longer slow.",
                    {"aoe_radius": 25, "slow_duration": 1.0}, ["aura_attack_speed_20"]),
                _up("Strongest aura", 1100, "Buff +30%, big AoE, slow hits all in a big radius.",
                    {"damage": 2, "aoe_radius": 40}, ["aura_attack_speed_30"]),
            ]},
            {"name": "Sin of Sloth", "tiers": [
                _up("Lazy hamsters", 130, "Much stronger slow (35%).", {"slow": 0.2}),
                _up("Weakness", 300, "Enemies in range take +15% damage from all towers.",
                    {"range": 15, "damage": 0.5}, ["damage_debuff_15"]),
                _up("Fall asleep", 550, "Hits can stop enemies for 1.5s (not bosses).",
                    {"slow_duration": 1.0}, ["sleep_chance"]),
                _up("Nap Time", 1200, "Active: stop all enemies in range 3s. Debuff +25%.",
                    {"range": 20, "damage": 1}, ["nap_time_active"]),
            ]},
        ],
    },
}


# Jalu upgrades also cost "ball knowledge" (earned by Larping in preparation). Per tier, both paths.
JALU_KNOWLEDGE_COSTS = [10, 25, 60, 120]
for _path in TOWERS["jalu"]["paths"]:
    for _tier, _k in zip(_path["tiers"], JALU_KNOWLEDGE_COSTS):
        _tier["knowledge"] = _k
