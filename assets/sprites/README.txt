Optional sprites. Missing files = the colored placeholder is used.
PNG or WEBP with transparency. Names (without extension) and what they replace:

  towers/jalu  towers/romli  towers/zizi  towers/bima  towers/fadhli     tower body (drawn ~42 px tall)
  enemies/normal fast tanky boss trojan trojan_trojan rich speedster reinforced             hamsters (drawn ~30/26/40/64 px tall)
                                              face RIGHT in the image; the game flips them when walking left
  projectiles/jalu  projectiles/romli  projectiles/zizi  projectiles/bima  projectiles/fadhli   shots (~16 px), pointing RIGHT
  stash                                       the Snack Stash (drawn ~48 px tall)
  (background override was removed: the map is baked by game/scenery.py)

Larger images are fine (they are scaled down smoothly); keep the aspect ratio you want.
Check the license of anything you download before using or sharing it.

Without PNGs the game draws its own shaded procedural sprites (game/sprites_proc.py).
Font: assets/fonts/LilitaOne-Regular.ttf, SIL Open Font License (OFL.txt).

Note: the built-in models (costumes per upgrade tier, weapons, projectiles) are in game/models.py.
A towers/<kind>.png override replaces the body for ALL tiers.
