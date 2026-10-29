# Achievement definitions and cosmetic title requirements.
from settings import catalogue

# Each achievement: (ID, name, requirement, metric, target).
achievements = [
    ("first_win", "FIRST VICTORY", "Win a Normal game or a complete Rage match.", "won", 1),
    ("big_profit", "VALUE HUNTER", "Earn net profit of at least 1000 coins in one settled game.", "profit", 1000),
    ("rage_master", "RAGE MASTER", "Win a complete Rage Difficulty 2 match: first to two game wins.", "rage2_win", 1),
    ("first_game", "FIRST AUCTION", "Complete your first Normal game or Rage match.", "played", 1),
    ("played_5", "REGULAR BIDDER", "Complete 5 Normal games / Rage matches in total.", "played", 5),
    ("played_10", "AUCTION REGULAR", "Complete 10 Normal games / Rage matches in total.", "played", 10),
    ("played_25", "AUCTION VETERAN", "Complete 25 Normal games / Rage matches in total.", "played", 25),
    ("played_50", "AUCTION LEGEND", "Complete 50 Normal games / Rage matches in total.", "played", 50),
    ("wins_5", "FIVE VICTORIES", "Win 5 Normal games / Rage matches in total.", "wins", 5),
    ("wins_10", "TEN VICTORIES", "Win 10 Normal games / Rage matches in total.", "wins", 10),
    ("wins_25", "WINNING EXPERT", "Win 25 Normal games / Rage matches in total.", "wins", 25),
    ("normal_win", "NORMAL WINNER", "Win your first Normal Mode game.", "normal_wins", 1),
    ("normal_5", "NORMAL EXPERT", "Win 5 Normal Mode games.", "normal_wins", 5),
    ("rage1_win", "RAGE CHALLENGER", "Win your first complete Rage Difficulty 1 match.", "rage1_wins", 1),
    ("rage1_5", "RAGE CONQUEROR", "Win 5 complete Rage Difficulty 1 matches.", "rage1_wins", 5),
    ("rage2_5", "RAGE ELITE", "Win 5 complete Rage Difficulty 2 matches.", "rage2_wins", 5),
    ("streak_3", "THREE IN A ROW", "Win 3 consecutive completed results in the same mode.", "streak", 3),
    ("streak_5", "FIVE IN A ROW", "Win 5 consecutive completed results in the same mode.", "streak", 5),
    ("profit_1", "SMALL PROFIT", "Finish one settled game with net profit greater than zero.", "profit", 1),
    ("profit_500", "GREAT DEAL", "Earn net profit of at least 500 coins in one settled game.", "profit", 500),
    ("profit_2000", "JACKPOT", "Earn net profit of at least 2000 coins in one settled game.", "profit", 2000),
    ("no_clue_win", "NO CLUE WIN", "Buy the warehouse at positive net profit without buying any clue cards.", "no_clue", 1),
    ("informed_win", "INFORMED WIN", "Buy the warehouse at positive net profit after using at least one clue card.", "informed", 1),
    ("early_bird", "EARLY BIRD", "Buy the warehouse in Round 1 and finish at positive net profit.", "early", 1),
    ("last_chance", "LAST CHANCE", "Buy the warehouse in Round 5 and finish at positive net profit.", "late", 1),
    ("collect_8", "FIRST FINDS", "Discover 8 different catalogue items in completed games/matches.", "collected", 8),
    ("collect_16", "COLLECTOR", "Discover 16 different catalogue items in completed games/matches.", "collected", 16),
    ("collect_32", "FULL COLLECTION", "Discover all 32 different catalogue items.", "collected", 32),
    ("rare_find", "RARE DISCOVERY", "Discover an item with a catalogue base price of at least 1000 coins.", "rare", 1),
    ("category_all", "CATEGORY COMPLETE", "Discover all 8 different catalogue items in any one category.", "category", 1)
]

titles = [
    ("ROOKIE BIDDER", "Win at least once in each of Normal, Rage D1 and Rage D2."),
    ("SEASONED BIDDER", "Complete at least 15 results in EACH of the three modes."),
    ("MASTER BIDDER", "Reach a cumulative win rate strictly above 50% in EACH mode."),
    ("VALUE HUNTER", "Earn game net profit of at least 1500 coins in EACH mode."),
    ("LEGENDARY HUNTER", "Combined cumulative NET profit across all modes exceeds 300000 coins."),
    ("AUCTION KING", "Obtain all 30 achievements AND all five other titles.")
]
title_rules_version = 2
legacy_titles = ["ROOKIE BIDDER", "SMART BIDDER", "VALUE HUNTER", "RAGE CHAMPION"]
title_colors = {
    "ROOKIE BIDDER": "\033[92m", "SEASONED BIDDER": "\033[96m",
    "MASTER BIDDER": "\033[94m", "VALUE HUNTER": "\033[95m",
    "LEGENDARY HUNTER": "\033[93m", "AUCTION KING": "RAINBOW"
}
rainbow_colors = ["\033[1;91m", "\033[1;93m", "\033[1;92m",
                  "\033[1;96m", "\033[1;94m", "\033[1;95m"]


def earned_titles(profile, unlocked_achievements, owned_titles):
    """Check cumulative milestones; strict thresholds exclude exact boundaries."""
    stats = [profile[mode] for mode in ["normal", "rage1", "rage2"]]
    conditions = [
        all(row["wins"] >= 1 for row in stats),
        all(row["played"] >= 15 for row in stats),
        all(row["played"] > 0 and row["wins"] * 2 > row["played"] for row in stats),
        all(row["best_profit"] is not None and row["best_profit"] >= 1500 for row in stats),
        sum(row["total_profit"] for row in stats) > 300000
    ]
    qualified = [titles[index][0] for index in range(5) if conditions[index]]
    owned = set(owned_titles + qualified)
    if (all(key in unlocked_achievements for key, *_ in achievements)
            and all(name in owned for name, _ in titles[:-1])):
        qualified.append(titles[-1][0])
    return qualified


def earned_achievements(profile, collection, mode, won, games):
    """Evaluate completed results without affecting bidding or settlements."""
    profitable_buys = [game for game in games
                       if game.get("purchased") and game["profit"] > 0]
    metrics = {
        "won": int(won), "rage2_win": int(mode == "rage2" and won),
        "played": sum(stats["played"] for stats in profile.values()),
        "wins": sum(stats["wins"] for stats in profile.values()),
        "normal_wins": profile["normal"]["wins"],
        "rage1_wins": profile["rage1"]["wins"],
        "rage2_wins": profile["rage2"]["wins"],
        "streak": max(stats["best_streak"] for stats in profile.values()),
        "profit": max([game["profit"] for game in games], default=0),
        "no_clue": int(any(game.get("bought") == 0 for game in profitable_buys)),
        "informed": int(any(game.get("used", 0) >= 1 for game in profitable_buys)),
        "early": int(any(game.get("rounds") == 1 for game in profitable_buys)),
        "late": int(any(game.get("rounds") == 5 for game in profitable_buys)),
        "collected": len(set(collection)),
        "rare": int(any(name in collection and value >= 1000
                        for items in catalogue.values() for name, value in items)),
        "category": int(any(all(name in collection for name, _ in items)
                            for items in catalogue.values()))
    }
    return [key for key, _, _, metric, target in achievements if metrics[metric] >= target]
