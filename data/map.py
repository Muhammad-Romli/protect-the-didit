"""The single map: a fixed corner list (rounded into a smooth path by game/utils.round_corners).
Enemies spawn at the first point (off-screen), the Snack Stash sits at the last.
Stays above the bottom bar (y < 636) and inside the 1280x720 playfield."""

MAP_WAYPOINTS = [
    (-40, 120),
    (1060, 120),
    (1060, 256),
    (230, 256),
    (230, 392),
    (1060, 392),
    (1060, 520),
    (600, 520),
    (600, 586),
]
MAP_CORNER_RADIUS = 46   # px; must stay below half of the shortest leg between two corners

STASH_POS = MAP_WAYPOINTS[-1]
