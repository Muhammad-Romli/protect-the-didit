# Changelog

## Checkpoint 5
- Fullscreen: `pygame.SCALED | RESIZABLE` window, F11 / Alt+Enter toggle, focus loss pauses.
- Money: every change goes through `Game.add_money`; HUD total counts up/down with merged `+$N` / `-$N` popups.
- Romli: `income_per_sec` is now paid every 10s in one lump (sound, coin burst, "+$N", progress bar). Per-wave income gets coin visuals at wave end; wave-clear money has its own sound and one combined popup.
- More polish: hover/select sounds, red danger vignette, ambient motes, aiming tower barrels, shadows, boss aura, ice particles on slowed enemies, stash glow, enemies face their walking direction.
- Sprite loader (`game/assets.py`, `assets/sprites/README.txt`): drop PNGs in, placeholders remain as fallback.
- Tests moved into the project (`tests/`), balance bot in `tools/`.

## Checkpoint 4
- Difficulty: simulations showed the game unwinnable by wave 7 even with larping and upgrades. Base damage doubled (Jalu 2, Romli 1, Zizi 1); T3/T4 prices lowered (500-550 / 1100-1200). A crude bot now wins with prep waits up to ~30s and loses with 40s+.
- One-time tip about Larping when the first Jalu is placed (Jalu upgrades need knowledge).
- VFX/SFX layer (see CLAUDE.md): 25 procedural sounds with pitch variants and rate limiting, hit sparks, pop bursts, "+$" pop-ups, comic words, projectile trails, tower recoil, enemy hit flash and waddle, wave banners, screen shake/flash on leaks and bosses, prep warning and last-5s ticks. `M` mutes.

## Checkpoint 3 (autonomous pass)
- Zizi: Praying unlocks at Recitation (A) tier 2, Slothing at Sin of Sloth (B) tier 2; locked buttons say what is needed.
- Effect system (`game/effects.py`, numbers in `data/effects.py`, hooks documented in the module docstring).
  Implemented: pierce_1, chain_lightning (Thor), time_push (Loom), sleep_chance, damage_debuff_15,
  aura_attack_speed_10/20/30 (strongest aura wins), upgrade_discount_aura, boss_kill_bonus.
  Still pending (panel says "not implemented yet"): thunderstrike_active, loom_reset_active,
  nap_time_active, random_event, random_event_strong.
- Enemies: stun (sleep) and push-back; bosses are immune to both.
- QoL: pause, hotkeys, sell confirmation, tower stats line, hotkey labels on buttons, hotkey hints.
- Upgrade price now goes through `Game.upgrade_cost` (discounts); sell value counts the price actually paid.
- Tests run headless: all effects, unlocks, QoL, and 6 random-bot fuzz runs without errors.
