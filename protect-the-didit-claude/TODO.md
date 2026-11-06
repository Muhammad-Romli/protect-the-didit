# TODO — ideas that are NOT in scope yet (CLAUDE.md rule 1: ask before building)

## Cool and cheap
- **Next-wave preview** on the HUD (enemy types and counts). Helps decide how long to prep vs the escalation timer.
- **First-run tutorial overlay**: prep phase, Larping, activities, the (4,1) upgrade rule. A playtest showed players miss that Jalu upgrades need knowledge.
- **Upgrade tooltips** on hover with the full description and the resulting stats.
- **Win/lose stats screen**: kills, money earned, time, towers built, best wave.
- **Particle/quality setting** (low/high) for weak laptops; volume sliders (SFX) and a small settings overlay.
- **Range ring on hover** over a tower or shop button before clicking.
- **Wave progress bar** (enemies left / spawned) during battle.

## Bigger
- **Music**: a loop for prep and a more intense one for battle (CC0 file or generated); separate music volume.
- **Targeting priority** (first / last / strong / close) — explicitly out of scope in CLAUDE.md, but very BTD6.
- **Sell-all / undo placement** within a few seconds.
- **Per-activity visuals** on the tower while Larping/Slothing/Praying (thought bubble, aura) instead of just the gold dot.
- **Difficulty presets** (prep time and enemy ramp) — out of scope per CLAUDE.md (no difficulty modes).
- **Bestiary / codex** page for Didit variants and tower lore.
- **Gamepad** input. (Touch: done, see MOBILE.md.)

## Dev tooling
- Turn `tools/balance_bot.py` into a small CLI that sweeps prep times / builds and prints a table, run after every balance change.
- Replace the placeholder `<plh>` lines in `data/dialogue.py` (Day 12 speech bubbles) — needs the author's jokes.
- Check with Jalu / Romli / Zizi that they are okay with their portrayal (CLAUDE.md tone note).

## VFX / SFX found unfinished or mismatched (2026-10-28, listed only, NOT built: models-only task)
- **Mark's punch** has no visible fist: `models.prop("fist", size)` now exists (points right) but `fx.mark_punch` only draws a ring/pop. Use it as a quick fly-in at the target.
- **Loki (Jalu B) magic bolts** (T2+) reuse `shoot_jalu` (the prop-sword throw sound) and the generic muzzle pop. Needs its own cast sound and a green muzzle/impact colour (the bolt model is green, the hit effects still use Jalu's blue).
- **Jalu base projectile** is now a tumbling rolled poster; the impact is still the generic spark. A paper-rip or "poof" would fit.
- **Temporal Loom** prop (`models.prop("loom")`) floats next to Loki at T3+, but `loom_reset` fx does not use it (no ring of threads / clock flash from the prop).
- **Speed Against Time** (Jalu B T3): no visual or sound when a fast Didit is normalised (`fx.normalized` exists; check it has a distinct look).
- **Zizi Nap Time** (`fx.nap_time`) and the Sloth pillow prop (`models.prop("pillow")`, shown at Sloth T4) are not connected; "Zzz" text is the only sleep visual.
- **Zizi Recitation aura** (the +attack-speed aura, T2-T4): `fx.aura` gives generic gold sparkles only; no ring showing the buff radius, no looping recitation sound.
- **Romli random events** (Programmer T3/T4): JACKPOT / OVERCLOCK / BUG have comic text and a burst but **no sound**; no screen-on-the-tower animation (the code screens are static).
- **Romli Farm/Business path**: no VFX or SFX tied to the tier look (suit/crown); the T3 upgrade-discount aura has no visual radius.
- **Romli armor_breaker** (Programmer T2): no distinct hit effect on armored Didits (`armor_hit` is generic).
- **Bima Graph T4 hologram wave** (companion model) is purely decorative; Bima's formula fire has a sound (`graph_fire`) but no sound for typing/invalid formula.
- **Fusion tower** (Jalu + Romli): model exists (`kind "fused_jalu_romli"`) but the feature, its sounds and its fuse VFX do not.
- **Boss Didit / Speedster / Trojan** entrance: `boss` sound only; no per-enemy intro sound (Speedster decel whoosh, Rich Didit jingle).
- **Music**: none (already listed above).
- **Jalu speech bubbles** + `data/dialogue.py` are all `<plh>` placeholders (already listed above).
