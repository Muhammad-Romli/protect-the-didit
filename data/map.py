"""The single map: fixed waypoint path. Enemies spawn at the first point,
the Snack Stash sits at the last. Stays inside the 1000x640 playfield."""

MAP_WAYPOINTS = [
    (-20, 90),
    (850, 90),
    (850, 230),
    (150, 230),
    (150, 370),
    (850, 370),
    (850, 510),
    (300, 510),
    (300, 600),
]

STASH_POS = MAP_WAYPOINTS[-1]
