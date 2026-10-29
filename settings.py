# Shared game settings and public item catalogue.

starting_coins = 6000
round_percentages = [50, 40, 30, 20, 0]
player_names = ["You", "Computer A", "Computer B"]
history_limit = 15  # Per mode; each Rage difficulty has its own limit.
history_marker = "===== GAME RECORD =====\n"
bid_time_limit = 25
# Each row: (normal bid factor, risk factor, risk frequency, late probe step).
computer_settings = [
    (0.90, 1.15, 0.65, 1),   # Normal Mode.
    (0.75, 1.30, 0.48, 1),   # Rage Difficulty 1.
    (0.55, 1.10, 0.65, -3)   # Rage Difficulty 2.
]
rage2_round_factors = [1.10, 1.00, 1.00, 1.15, 1.25]
damaged_card_percent = 80  # Pay 80% of the usual card price in damaged games.
normal_event_chance = 30  # Normal Mode: 70% no event, 30% an event per game.
green = "\033[92m"
yellow = "\033[1;93m"
red = "\033[91m"
grey = "\033[90m"
cyan = "\033[1;96m"
table_width = 62

# Each card: (name, price, description).
clues = [
    ("Random Estimate", 50, "Random item: +/-20% estimate; identity hidden."),
    ("Category Scan", 80, "Chosen category: count items worth >=300."),
    ("Random Appraisal", 80, "Random item: reveal its number and exact value."),
    ("Rare Item Count", 220, "Warehouse: count items worth >=1000."),
    ("Second-Highest Scan", 220, "Second-highest value; item identity stays hidden."),
    ("Category Value Range", 120, "Chosen category total: 500-coin band (e.g. 500-999)."),
    ("Mid-Value Count", 60, "Count items worth 300-999; identities stay hidden."),
    ("Low-Value Total Range", 40, "Total of items below 300: a 100-coin band.")
]

catalogue = {
    "Electronics": [
        ("USB cable", 20), ("Mouse", 40), ("Headphones", 60),
        ("Keyboard", 90), ("Monitor", 140), ("Tablet", 300),
        ("Laptop", 500), ("Gaming computer", 1200)
    ],
    "Tools": [
        ("Screwdriver", 20), ("Wrench", 30), ("Hammer", 50),
        ("Toolbox", 80), ("Hand saw", 120), ("Drill", 250),
        ("Tool set", 450), ("Workshop machine", 1000)
    ],
    "Decorations": [
        ("Postcard", 10), ("Candle", 20), ("Picture frame", 40),
        ("Wall clock", 60), ("Lamp", 100), ("Sculpture", 200),
        ("Painting", 400), ("Antique vase", 1500)
    ],
    "Collectibles": [
        ("Trading card", 10), ("Badge", 30), ("Postage stamp", 50),
        ("Stamp album", 80), ("Figurine", 120), ("Signed book", 350),
        ("Rare coin", 650), ("Rare manuscript", 2000)
    ]
}
