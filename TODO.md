# TODO — remaining work only

Keep this file limited to work that is not already implemented. Check `CLAUDE.md` and the code before adding an item. Move completed items to `CHANGELOG.md` or remove them; do not keep historical status notes here.

## Gameplay and usability

- [ ] Next-wave preview showing upcoming enemy types/counts and the preparation escalation risk.
- [ ] First-run tutorial explaining preparation, activities, Jalu's ball-knowledge requirement, and crosspath restrictions.
- [ ] Win/lose summary with kills, money earned, time, towers built, and highest wave.
- [ ] Wave progress indicator showing spawned and remaining enemies during battle.
- [ ] Sell-all or short-window undo for accidental placement/selling, if scope allows.
- [ ] Gamepad support.
- [ ] Music for preparation and battle, with a separate music-volume setting.
- [ ] Bestiary/codex for Didit variants and character lore.

## Visual and audio polish still worth checking

- [ ] Mark's punch should visibly use the fist prop instead of relying only on ring/pop feedback.
- [ ] Give Loki magic bolts their own cast sound and green muzzle/impact feedback rather than reusing the base Jalu throw feedback.
- [ ] Give the rolled-poster projectile a paper-rip/poof impact treatment.
- [ ] Connect the Temporal Loom prop to Loom Reset with a visible thread/clock effect.
- [ ] Make Speed Against Time normalization visually and audibly distinct.
- [ ] Connect Zizi's pillow prop and Nap Time effect to a stronger sleep visual; the current Zzz feedback may be too subtle.
- [ ] Give Zizi's Recitation aura a visible radius indicator and, if appropriate, a quiet looping sound.
- [ ] Add distinct sound/animation feedback to Romli's random-event outcomes and business/programmer tiers.
- [ ] Give Romli's armor-breaker hits a distinct visual treatment.
- [ ] Add typing/invalid-formula feedback for Bima Graph if playtesting shows the current feedback is insufficient.
- [ ] Give boss and miniboss variants distinct entrance cues where useful.

## Character and content work

- [ ] Fadhli look: he still uses the default tower body and colors. Add a petanque-athlete outfit per path/tier and a held prop in `game/models.py`; ask the person he represents what he looks like first.
- [ ] Fadhli sounds: `shoot_fadhli` does not exist, so his throws are silent; add throw, impact, crater, Meteor, and Gyro sounds in `game/audio.py`.
- [ ] Spinned visual: the tornado is three wobbling ribbons drawn over the normal Didit. The design asks for three distinct tornado poses/models that make the enemy look like a tornado.
- [ ] Add Fadhli to `tools/balance_bot.py` and run a balance pass (his numbers are untested).
- [ ] Run `tests/test_fadhli.py` and the full suite on a machine with pygame; the Fadhli fixes and tests have only been compile-checked.
- [ ] Replace Jalu's `<plh>` dialogue placeholders in `data/dialogue.py` with approved lines.
- [ ] Review character portrayals with the people represented before adding more personal jokes or dialogue.

## Balance and developer tooling

- [ ] Expand `tools/balance_bot.py` into a CLI that can sweep preparation times/builds and print comparable results.
- [ ] Recheck balance after each new tower, major upgrade, or wave-scaling change.
