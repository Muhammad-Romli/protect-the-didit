"""Didit Wallstreet data (main-menu minigame): stocks, news sources and headline templates.

Three stocks (prices are in Didit Rupiah, DR):
  IHSD   Indeks Harga Saham Didit   - volatile index, moved by Didit news
  ROC    Romli Corp.                - riskier company stock, moved by Romli news
  IUKXJ  Indeks Uang Kas X-J        - NOT random: price = total kas / KAS_DIVISOR. The total is the plain integer in
                                      kas.txt (project root). Edit that file when the real class cash changes.
The market only moves when a run ends ("after you finish the match"). The newspaper always shows the headlines
for the NEXT move. Each headline has a hidden size (`mag`) and a source: reliable sources are right far more often.
"""

KAS_FILE = "kas.txt"
KAS_DEFAULT = 1_500_000    # used when kas.txt is missing or unreadable
KAS_DIVISOR = 50_000       # IUKXJ price = kas / KAS_DIVISOR  (1.500.000 -> 30 DR)

ORDER = ["IHSD", "ROC", "IUKXJ"]
STOCKS = {
    "IHSD": {"name": "Indeks Harga Saham Didit", "start": 40.0, "floor": 5.0, "cap": 400.0, "vol": 0.035,
             "color": (150, 110, 255)},
    "ROC": {"name": "Romli Corp.", "start": 25.0, "floor": 2.0, "cap": 400.0, "vol": 0.06,
            "color": (80, 200, 120)},
    "IUKXJ": {"name": "Indeks Uang Kas X-J", "start": 30.0, "floor": 1.0, "cap": 2000.0, "vol": 0.0,
              "color": (255, 200, 70)},
}

MEAN_REVERSION = 0.04      # each move pulls the price a little back to its start (no runaway prices)
HISTORY_LEN = 24           # points kept for the chart
SELL_FEE = 0.01            # 1% fee when selling
MAX_HOLD = 500             # shares of one stock you can hold
BACKFIRE = 0.6             # when a headline is wrong the price moves the other way by this share of its size

# Source domain -> probability that its headline is right (shown like Hacker News' "(domain)")
SOURCES = {
    "diditpost.id": 0.88,
    "wallstreetdidit.id": 0.84,
    "hamsterwire.com": 0.70,
    "rumorhamster.net": 0.52,
    "trustmebro.biz": 0.45,
}

# (stock, mag, text): mag > 0 means the headline is good news for the stock; < 0 bad news. Size is hidden.
HEADLINES = [
    # ---- IHSD (Didit news)
    ("IHSD", +0.09, "Didits caught stockpiling seeds; analysts bullish"),
    ("IHSD", +0.05, "Hamster wheel output edges up in third quarter"),
    ("IHSD", +0.11, "Schrodinger's Cat sells robot suits to every Didit, index surges"),
    ("IHSD", +0.04, "Cure rumors lift Didit-Alpha related shares slightly"),
    ("IHSD", +0.07, "Didit spotted doing a double backflip on camera"),
    ("IHSD", -0.10, "Didit-Alpha escapes the lab again, investors panic"),
    ("IHSD", -0.06, "Seed shortage hits Didit markets"),
    ("IHSD", -0.04, "Cage inspection finds minor wheel squeaks"),
    ("IHSD", -0.09, "Hamster wheel recall announced after tiny explosion"),
    ("IHSD", -0.07, "Didit refuses to leave the burrow, trading volume falls"),
    # ---- ROC (Romli Corp.)
    ("ROC", +0.10, "Romli Corp. ships a bug-free release (allegedly)"),
    ("ROC", +0.06, "ROC lands a big school contract"),
    ("ROC", +0.04, "Romli's laptop survives a full day of coding"),
    ("ROC", +0.12, "ROC announces Go rewrite, developers thrilled"),
    ("ROC", +0.07, "Romli Corp. hires a very reliable intern"),
    ("ROC", -0.11, "Romli Corp. pushes to production on a Friday"),
    ("ROC", -0.07, "ROC server goes down: someone ran rm -rf in the wrong folder"),
    ("ROC", -0.05, "Romli Corp. CEO found sleeping through a deadline"),
    ("ROC", -0.09, "ROC's PostgreSQL migration goes sideways"),
    ("ROC", -0.04, "Romli Corp. stand-up meeting runs 40 minutes over"),
]

# Headlines that move nothing (filler, like the front page of any news site)
NOISE = [
    "Local hamster refuses to run on wheel, calls it \"cardio theatre\"",
    "Opinion: are Didits overvalued, or just fluffy?",
    "Show: I made a tiny spreadsheet for my seed budget",
    "Ask: how do you explain pointers to a hamster?",
    "Study finds 9 out of 10 Didits prefer sunflower seeds",
    "Why every class treasurer needs a notebook",
    "Weather: sunny with a chance of falling seeds",
    "Jalu insists he has seen that movie (he has not)",
]

KAS_UP = "Kas X-J rises to Rp {kas} (+Rp {diff}): the treasurer collected payments"
KAS_DOWN = "Kas X-J falls to Rp {kas} (-Rp {diff}): class spending approved"
KAS_SAME = "Kas X-J holds steady at Rp {kas}, treasurer says all is calm"

RUN_WON = "Front page: the Snack Stash was defended, wave {n} cleared"
RUN_LOST = "Front page: the Snack Stash was raided at wave {n}"
