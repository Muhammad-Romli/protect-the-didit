# Merge and God Tier

> **Status: design only. Nothing in this file is implemented yet.** Written 2026-11-09 from the author's description.
> Marked **[author]** = the author said it. Marked **[proposal]** = my suggestion to fill a gap, change or delete freely.
> The only existing trace of merging in the code is the old Jalu + Romli "fusion" placeholder in `CLAUDE.md` and a
> `fused_jalu_romli` look in `game/models.py`. There is no fuse button, no `FUSIONS` table and no minigame yet.

## 1. The idea

**[author]** Two towers can be **merged** into one stronger tower. Most merges are "god tier": they need **both towers at
tier 4** and the merge is won in a minigame. One merge (Romli + Bima) is lighter and only needs tier 3, so it is not a real
god tier.

| Merge | Needs | Result | God tier? |
|---|---|---|---|
| Loki + Loki | two Jalu, path B (Loki), tier 4 each | **God Loki** | yes |
| Zizi good + Zizi bad | Zizi path A (Recitation) tier 4 + Zizi path B (Sloth) tier 4 | half demon / half angel, wings, 2 grimoires | yes |
| Romli Business + Bima | Romli path A (Business) tier 3 + Bima (either path) tier 3 + **100 ROC papers** | **Engineer Corp**, a summoner unit | no (tier 3 only) |

Notes on naming: "Zizi good / bad" is read as Recitation = good (halo, book) and Sloth = bad. "Romli business" is Romli path A.

## 2. Merge flow **[proposal]**

1. Select a tower that is eligible, press MERGE, pick a partner in range of it (distance rule is open, the old placeholder used 200 px).
2. Preparation phase only (the minigame must not run while Didits are walking).
3. The minigame starts (God Loki: section 3). **Success** replaces BOTH towers with the merged tower at the first one's position. **[author] Failure: you lose one of the two towers** (the other stays). **[proposal]** the player picks which one is at risk before starting, otherwise it is random.
4. Merged towers have **no further upgrades** (as in the old fusion placeholder) and cannot be merged again.
5. Cost: a price in money (old placeholder: 500). Needs a decision, god tier should probably cost much more.
6. Data-driven, per `CLAUDE.md` rule 3: a `MERGES` table in `data/merges.py` (inputs, minimum tiers, result id, minigame id, cost), logic in `game/merge.py`.

## 3. God Loki

### Minigame **[author]**
- Button smashing while the "larp edit" video plays.
- The video goes in **`assets/loki_larp.mp4`** (the author will add it; it does not exist in the project yet).
- If the player succeeds, they get God Loki.

### Minigame details **[proposal]**
- A bar fills a bit with every press and drains slowly; fill it before the video ends. Time limit = video length.
- Numbers to tune in `data/merges.py`: fill per press, drain per second, goal.
- Controls: SPACE or click/tap (touch build exists, `game/touch.py`).

### Look **[author]**
Looks like Loki when he forms the Yggdrasil tree. From the reference image you sent: a dark horned crown, a dark green
high-collar outfit, calm face, surrounded by glowing green strands. **[proposal]** for the sprite: the existing Loki costume
(`models._loki`) in darker green, bigger horns, and glowing green roots / threads growing up from his pedestal and branching
around him (animated sway, like the Temporal Loom threads). The existing `loom` prop can be the seed of the art.

### Abilities **[author: "powerful active and passive"; the specifics are not decided]**
**[proposal]**, built on what Loki already does (slow, push back, freeze, `time_push`, `speed_against_time`, Loom Reset):
- **Passive "Roots of Time":** every Didit in range is permanently slowed a bit (bosses half as much), and every hit has a higher time-push chance than Loki's 20%.
- **Active "Yggdrasil":** roots grow over the whole path for a few seconds: every Didit on the map is rooted in place and takes damage over time; bosses are only slowed.
- Stats: much more damage and range than a tier-4 Loki, since two tier-4 towers are spent.

## 4. Zizi good + Zizi bad **[author]**
- Becomes half demon and half angel, with wings and **2 grimoires**. Nothing more is attached to it (no drawback).
- Minigame: not specified. **[proposal]** the same button-smash minigame with a different clip, or a different one.
- Abilities: not specified. Zizi's tools today: aura (+attack speed, Recitation), slow, damage debuff, sleep/stun, Nap Time (Sloth). A natural fit is one grimoire per path (angel grimoire = buff aura, demon grimoire = debuff + sleep).

## 5. Engineer Corp (Romli Business + Bima) **[author]**
- Needs Romli path A (Business) tier 3 and Bima (either path) tier 3. **Not a god tier.**
- **[author]** Its condition is not a minigame: you need to own **100 ROC papers** (shares of ROC, "Romli Corp.", from Didit Wallstreet).
- How this fits the code (checked): shares live in the meta profile, `Profile.holdings["ROC"]` (`game/profile.py`), the cap is `MAX_HOLD = 500`, so 100 is allowed. They are bought in the main menu, and CLAUDE.md says Wallstreet is not available during a match: the player buys the papers before the run and the merge only *checks* the count. **[proposal]** the 100 papers are spent when the merge happens (sold to the "Corp" at no refund), otherwise it would be a free check. Decide which.
- A **summoner unit**: it spawns units. This is a new mechanic: no tower in the game summons anything today.
- **[proposal]** small "engineer" units placed or walking near the path with simple attacks, a cap on how many exist, and income from Romli's side. Everything else (what they do, cost, limits) is undecided.

## 6. Technical notes

### Playing the video: frames + audio **[author: acceptable]**
1. **Convert once, on your machine:** `python tools/convert_video.py assets/loki_larp.mp4` (script added in this change, needs
   `ffmpeg`; on WSL: `sudo apt install ffmpeg`). It writes `assets/loki_larp/frame_0001.jpg ...`, `audio.ogg` and `info.json`
   (fps, frame count, seconds). Defaults: 15 fps, 480 px wide. Tested here on a generated 3 s clip: 45 frames, about 0.6 MB.
2. **Commit the converted folder**, not necessarily the .mp4. The game never opens the .mp4.
3. **Player (not written yet), `game/clip.py`:** reads `info.json`, and each frame draws `frames[int(t * fps)]` where `t` comes from the
   game's own `dt`, so it stays in sync and works at any frame rate. Frames are loaded as JPGs *while playing* (a few ahead), not all at
   once, to save memory. Audio is played with `pygame.mixer` (OGG is supported in the browser build too).
4. **The minigame uses the clip as its timer:** it ends when the last frame is shown. If the player is too slow the clip ends and it is a fail.
5. **Size:** a 20 s clip at 15 fps and 480 px is roughly 300 frames, about 5 MB on disk. Raise `--fps` / `--width` only if it looks bad.
   Rough rule: memory and download size grow with fps x width squared x seconds.

### Other
- **Preparation only** for minigames, to match the DiditCode rule.
- **Balance:** merging removes two tier-4 towers (and a failure costs one), so the result has to beat both together.
- **Save game:** merged towers need their own save format (`game/savegame.py`).

## 7. Open questions
Answered by the author: failing the minigame loses one tower; Engineer Corp is gated by 100 ROC papers, not a minigame; Zizi has nothing after "but"; the clip may be converted to frames.

Still open:
1. Failure: does the player choose which tower is at risk, or is it random? (proposal in section 2)
2. Are the 100 ROC papers spent by the merge, or only checked?
3. The cost in money for each merge, and is a merge once per run or unlimited?
4. Zizi good + bad: which minigame (same smash with another clip, or something else)? And what are the two grimoires' abilities?
5. God Loki's passive and active: use the proposal in section 3 or write your own?
6. What does Engineer Corp summon and what does it do? (new mechanic, nothing like it exists yet)
7. Is the merge range (distance between the two towers) needed, and how far?

---

# Appendix A. Loki (Jalu path B) as it exists today

The base of God Loki. Everything below is checked against `data/towers.py`, `data/effects.py`, `game/effects.py`,
`game/actives.py`, `game/models.py` and `game/fx.py`. In the game the path is called **Temporal Loom Guy**, the look is **Loki**.

### A1. What it is

Jalu is the base tower (a larper who talks about movies he never watched). Path B turns him into a Loki-style
"god of mischief" who bends time: slows Didits, shoves them back along the path, and at tier 4 resets time around him.
It is the **control** path of Jalu (path A, Mark, is the brawler).

- **Role:** single-target magic damage + crowd control (slow, push back, freeze).
- **Rule:** each Jalu unit follows **ONE path**. The first upgrade bought in path B locks path A for that unit.
- **Currency:** every tier costs money **and** ball knowledge (10 / 25 / 60 / 120, `JALU_KNOWLEDGE_COSTS`). Ball knowledge comes from Jalu's Larping activity during preparation.

### A2. Upgrades

Base Jalu: damage 2, cooldown 0.8 s, range 150, projectile speed 450.

| Tier | Name | Money | Stat changes | Effects | What the player gets |
|---|---|---|---|---|---|
| 1 | Costume & scepter | 120 | damage +0.5, range +20 | none | Loki costume, scepter. |
| 2 | Magic bolts | 300 | damage +0.5, slow 20% for 1.0 s | none | Green magic bolts that slow what they hit. |
| 3 | The Temporal Loom | 500 | damage +1, slow +10 points | `time_push`, `speed_against_time` | Hits can shove Didits back; fast Didits that get hit walk at normal speed. |
| 4 | Loom Reset | 1100 | damage +3, range +20, cooldown -0.15 | `loom_reset_active` | Active skill + stronger basic attacks. |

Cumulative stats (computed from the game's own `Tower.recompute_stats`):

| Tier | Damage | Cooldown | Range | Slow |
|---|---|---|---|---|
| 0 (base) | 2.0 | 0.80 s | 150 | – |
| 1 | 2.5 | 0.80 s | 170 | – |
| 2 | 3.0 | 0.80 s | 170 | 20% for 1.0 s |
| 3 | 4.0 | 0.80 s | 170 | 30% for 1.0 s |
| 4 | 7.0 | 0.65 s | 190 | 30% for 1.0 s |

(Mixing in one tier of path A is not possible for Jalu: the unit is locked to one path, see section 1.)

### A3. Mechanics in detail

**Magic bolts (tier 2+).** Plain projectiles with a slow (`slow`, `slow_duration` in the stats above). Slow never takes a Didit below 20% of its base speed; bosses take half the slow.

**Time push (tier 3+).** `data/effects.py -> "time_push"`: every Didit a hit lands on has a **20% chance** to be pushed back **80 px** along the path (`Enemy.push_back`, reduces `distance`). Bosses are immune. Shows the "SWOOSH!" effect.

**Speed Against Time (tier 3+).** `"speed_against_time"`: a *fast* Didit (Fast, Speedster) that is hit walks at its normal speed for **3.0 s**; every new hit refreshes the 3 s. (`Enemy.normalize_timer`).

**Loom Reset (tier 4 active).** `game/actives.py -> "loom_reset_active"`:
- Cooldown **35 s**, no aiming, uses the tower's current range.
- Every Didit in range: pushed back **160 px** and **stunned 2.0 s**.
- Bosses are not pushed or stunned: they are slowed by 50% for 2.0 s instead.

### A4. Numbers you can change

| What | Where |
|---|---|
| Prices, damage/range/cooldown/slow per tier, descriptions | `data/towers.py` -> `TOWERS["jalu"]["paths"][1]` |
| Ball knowledge costs | `data/towers.py` -> `JALU_KNOWLEDGE_COSTS` |
| Push chance / distance, Speed Against Time duration | `data/effects.py` -> `EFFECT_PARAMS` |
| Loom Reset cooldown, push, stun, boss slow | `game/actives.py` -> `ACTIVES["loom_reset_active"]` |
| Voice lines | `data/dialogue.py` (`jalu_b1` ... `jalu_b4`, all still `<plh>` placeholders) |

### A5. Look (art)

All procedural, `game/models.py` (`_loki`, weapon, projectile, companion) and `game/sprites_proc.py`.

- Green suit with gold collar, straps and belt. Slicked-back black hair (`hair: "slick"`).
- Curved gold helmet horns with a cyan gem; the horns are **25% bigger at tier 4**.
- Tier 2+: green cape. Tier 3+: gold shoulder pads and the floating **Temporal Loom** (a clock with threads) next to him (a bit larger at tier 4).
- Weapon: a gold scepter with a glowing cyan orb. Projectile (tier 2+): green energy diamond with a gold core and a tail.
- Sounds: `loom` for Loom Reset. Bolts still reuse Jalu's `shoot_jalu` sound.

### A6. Tests that cover it

- `tests/test_mark.py`: path names, and that Loki's tier 3 effects are intact.
- `tests/test_new_enemies.py`: Temporal Loom passive normalises fast enemies for 3 s, refreshed per hit.
- `tests/test_bima.py` (line ~104): Loom Reset pushes back and stuns.
- `tests/test_models.py`: the `loom` prop renders.

Run from the project folder: `python tests/test_mark.py` (and the others the same way).

### A7. Known gaps (from `TODO.md`, still true)

- Bolts have no cast sound of their own and no green muzzle/impact colour (hit effects are still Jalu's blue).
- The Loom prop floating next to him is not used by the Loom Reset effect (no ring of threads / clock flash from the prop).
- Speed Against Time has `fx.normalized` but no clearly distinct sound/visual.
- All Jalu voice lines are placeholders (`<plh>`), the real sarcastic lines still need to be written.
- Per CLAUDE.md: check with Jalu that he is fine with how he is portrayed.

### A8. Not unlocked by the merge
Merging uses two **tier-4** Loki units (both Jalu, both path B). The merged tower is a new tower id, not a Jalu upgrade.
