"""Text for the UNITS screen (main menu). Upgrade names, prices and descriptions are read from data/towers.py,
so only the character blurbs live here. Keep them short; the screen wraps them into a small panel."""

UNITS_INFO = {
    "jalu": {"role": "Base fighter",
             "blurb": "A larper who has never actually watched the movies, but talks about them nonstop. "
                      "Reliable single-target damage. Pick Mark (brawler) or Temporal Loom (magic).",
             "rule": "Each Jalu follows ONE path (no cross-pathing)."},
    "romli": {"role": "Economy + coder",
              "blurb": "Earns money every wave and fires weak \"bug\" shots. Go business for income, "
                       "or programmer to turn attacks into money and random events. \
Ability DiditCode (preparation): fix a code bug for money.",
              "rule": "Tier 4 on one path, tier 1 on the other."},
    "zizi": {"role": "Support / control",
             "blurb": "Splash damage with a mild slow. Recitation buffs nearby towers, "
                      "Sin of Sloth weakens and stops Didits. Preparation activities build stacks.",
             "rule": "Tier 4 on one path, tier 1 on the other."},
    "bima": {"role": "Mathematician",
             "blurb": "Fires curves from formulas you type (Graph) or stacking shapes (Geometry). "
                      "Strong, but needs thinking. Uses ONE path only.",
             "rule": "Bima uses ONE path only."},
}
