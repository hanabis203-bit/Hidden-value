# Persistent profile, achievements, collection and cosmetic titles.
import json
import os
from textwrap import wrap
from settings import catalogue, history_limit
from interface import get_number, show, show_table, color_text, format_title, menu_color
from records import read_history
from rewards import (achievements, titles, earned_achievements, earned_titles,
                     legacy_titles, title_rules_version)

data_file = "player_data.json"
modes = [("normal", "NORMAL"), ("rage1", "RAGE D1"), ("rage2", "RAGE D2")]
pages = {
    "profile": ("PLAYER PROFILE", "VIEW PERSONAL DATA", "CLEAR PROFILE DATA"),
    "achievements": ("ACHIEVEMENTS", "VIEW ACHIEVEMENTS", "CLEAR ACHIEVEMENTS"),
    "collection": ("ITEM COLLECTION", "VIEW ITEM COLLECTION", "CLEAR COLLECTION"),
    "titles": ("TITLES", "VIEW TITLES", "CLEAR TITLES")
}


def new_stats():
    return {"played": 0, "wins": 0, "streak": 0, "best_streak": 0,
            "total_profit": 0, "best_profit": None, "recent": []}


def new_data():
    return {"profile": {key: new_stats() for key, _ in modes},
            "achievements": [], "collection": [], "titles": [],
            "title_rules": title_rules_version}


def valid_data(data):
    # Reject malformed files rather than overwrite an existing player record.
    if not isinstance(data, dict) or not all(key in data for key in pages):
        return False
    if not isinstance(data["profile"], dict):
        return False
    for key, _ in modes:
        stats = data["profile"].get(key)
        if not isinstance(stats, dict) or not all(field in stats for field in new_stats()):
            return False
        for field in ["played", "wins", "streak", "best_streak", "total_profit"]:
            if type(stats[field]) is not int:
                return False
        if not 0 <= stats["streak"] <= stats["best_streak"] <= stats["played"]:
            return False
        if not 0 <= stats["wins"] <= stats["played"]:
            return False
        if stats["best_profit"] is not None and type(stats["best_profit"]) is not int:
            return False
        recent = stats["recent"]
        if not isinstance(recent, list) or len(recent) > history_limit:
            return False
        if len(recent) > stats["played"] or any(type(win) is not bool for win in recent):
            return False
    if "title_rules" in data and data["title_rules"] != title_rules_version:
        return False
    allowed = {"achievements": [row[0] for row in achievements],
               "collection": [name for rows in catalogue.values() for name, _ in rows],
               "titles": legacy_titles if "title_rules" not in data else [row[0] for row in titles]}
    for section in allowed:
        values = data[section]
        if not isinstance(values, list) or any(value not in allowed[section] for value in values):
            return False
    return True


def save_data(data):
    try:
        # Replace only after writing succeeds, so an interrupted write is safe.
        with open(data_file + ".tmp", "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)
        os.replace(data_file + ".tmp", data_file)
        return True
    except (OSError, UnicodeError) as error:
        show("PLAYER DATA COULD NOT BE SAVED:", error)
        return False


def update_stats(stats, won, profits):
    stats["played"] += 1
    stats["wins"] += int(won)
    stats["streak"] = stats["streak"] + 1 if won else 0
    stats["best_streak"] = max(stats["best_streak"], stats["streak"])
    stats["recent"] = (stats["recent"] + [won])[-history_limit:]
    if profits:
        stats["total_profit"] += sum(profits)
        best = stats["best_profit"]
        stats["best_profit"] = max(profits + ([] if best is None else [best]))


def import_history(data):
    # Import available results once. Older deleted records cannot be recovered.
    for key, _ in modes:
        rage = key != "normal"
        records = read_history("rage_history.txt" if rage else "normal_history.txt",
                               int(key[-1]) if rage else None)
        if records is None:
            return False
        wins = ["MATCH RESULT: YOU WIN!"] if rage else [
            "You win!", "The computer loses money. You win!"]
        losses = ["MATCH RESULT: YOU LOSE!"] if rage else [
            "You lose!", "You did not win.", "The warehouse remains unsold. No win."]
        for record in records[-history_limit:]:
            lines = record.splitlines()
            result = lines[-1].strip()
            if result not in wins + losses:
                continue
            profits = []
            for line in lines:
                if line.startswith("NET PROFIT:"):
                    try:
                        profits.append(int(line.split()[2]))
                    except (ValueError, IndexError):
                        pass
            update_stats(data["profile"][key], result in wins, profits)
    return True


def load_data():
    """Load or initialise progress, preserving unreadable files and older stats."""
    try:
        with open(data_file, "r", encoding="utf-8") as file:
            data = json.load(file)
        if not valid_data(data):
            raise ValueError("invalid player data format")
        if "title_rules" not in data:
            # Old titles used different conditions. Keep all other progress.
            data["titles"] = []
            data["title_rules"] = title_rules_version
            if not save_data(data):
                return None
            show("TITLE RULES UPDATED. Titles are checked after your next result.")
        return data
    except FileNotFoundError:
        data = new_data()
        if import_history(data) and save_data(data):
            return data
    except (OSError, UnicodeError, ValueError) as error:
        show("PLAYER DATA COULD NOT BE READ:", error)
        show("The existing file was kept. Gameplay and history are available.")
    return None


def record_result(mode, won, games):
    """Save one Normal result or complete Rage match, then announce new titles."""
    # One Normal game or one complete Rage match counts as one result.
    data = load_data()
    if data is None:
        return
    profits = [game["profit"] for game in games]
    update_stats(data["profile"][mode], won, profits)
    before = len(data["collection"])
    for game in games:
        for name in game["items"]:
            if name not in data["collection"]:
                data["collection"].append(name)
    earned = earned_achievements(data["profile"], data["collection"], mode, won, games)
    notices = []
    for key, name, _, _, _ in achievements:
        if key in earned:
            if key not in data["achievements"]:
                data["achievements"].append(key)
                notices.append("ACHIEVEMENT UNLOCKED: " + name)
    new_titles = [name for name in earned_titles(data["profile"], data["achievements"], data["titles"])
                  if name not in data["titles"]]
    data["titles"].extend(new_titles)
    added = len(data["collection"]) - before
    if added:
        notices.append(f"NEW COLLECTION ENTRIES: {added}")
    if save_data(data):
        if notices:
            show_table("PLAYER PROGRESS", ["UPDATE"], [(notice,) for notice in notices], [62])
        # Keep new title announcements last, after all other game-end updates.
        for name in new_titles:
            show()
            show_table("NEW TITLE UNLOCKED", ["TITLE"], [(format_title(name),)], [62])


def get_player_title():
    data = load_data()
    unlocked = data["titles"] if data is not None else []
    return next((name for name, _ in reversed(titles) if name in unlocked), "UNRANKED")


def show_profile(data):
    show("\nCUMULATIVE RESULTS SINCE THE LAST PROFILE RESET.")
    show("Normal counts games; Rage counts complete matches.")
    rows = []
    for key, label in modes:
        stats = data["profile"][key]
        played, wins = stats["played"], stats["wins"]
        rate = f"{wins / played * 100:.2f}%" if played else "--"
        rows.append((label, played, wins, played - wins, rate))
    show_table("PLAYER PROFILE", ["MODE", "PLAYED", "WINS", "LOSSES", "WIN RATE"],
               rows, [15, 9, 9, 9, 8], right=(1, 2, 3, 4))
    rows = []
    for key, label in modes:
        stats = data["profile"][key]
        best = stats["best_profit"]
        rows.append((label, f"{stats['total_profit']:+d}",
                     "--" if best is None else f"{best:+d}", stats["best_streak"]))
    show_table("PROFIT AND WIN STREAKS", ["MODE", "TOTAL NET", "BEST GAME NET", "BEST STREAK"],
               rows, [14, 13, 14, 12], right=(1, 2, 3))
    show("Rage total net includes all games in completed matches.")
    show(f"RECENT RATE: UP TO {history_limit} RESULTS PER MODE SINCE RESET.")
    rows = []
    for key, label in modes:
        recent = data["profile"][key]["recent"]
        wins = sum(recent)
        rate = f"{wins / len(recent) * 100:.2f}%" if recent else "--"
        rows.append((label, len(recent), wins, rate))
    show_table("RECENT WIN RATES", ["MODE", "COUNTED", "WINS", "WIN RATE"],
               rows, [20, 11, 11, 11], right=(1, 2, 3))
    show("First use imports available history; older results are unknown.")
    show("Clearing game history does not clear this profile.")


def show_achievements(data):
    show(f"\nOBTAINED: {len(data['achievements'])} / {len(achievements)}")
    for index, (key, name, condition, _, _) in enumerate(achievements):
        obtained = key in data["achievements"]
        status = color_text("OBTAINED" if obtained else "NOT OBTAINED",
                            "\033[92m" if obtained else "\033[91m")
        rows = [("NAME", name)]
        rows += [("REQUIREMENT" if line == 0 else "", text)
                 for line, text in enumerate(wrap(condition, 45))]
        rows.append(("STATUS", status))
        show_table(f"ACHIEVEMENT {index + 1:02d} / {len(achievements)}",
                   ["FIELD", "DETAIL"], rows, [14, 45])
    show("Normal counts games; Rage counts completed matches.")
    show("Streaks require consecutive wins in the same mode.")
    show("Profit/card/round targets use individual settled games.")
    show("Clear achievements: profile and collection stay unchanged.")
    show("Their milestones may unlock again after your next result.")


def show_collection(data):
    total = sum(len(rows) for rows in catalogue.values())
    show_table("ITEM COLLECTION", ["DISCOVERED", "PROGRESS"],
               [(f"{len(data['collection'])} / {total}",
                 f"{len(data['collection']) / total * 100:.1f}%")], [43, 16], right=(1,))
    show("Revealed items count, regardless of who buys the warehouse.")
    for category, items in catalogue.items():
        rows = [(name, value, "YES" if name in data["collection"] else "--")
                for name, value in items]
        show_table(category.upper(), ["ITEM", "BASE PRICE", "FOUND"],
                   rows, [32, 15, 9], right=(1,))


def show_titles(data):
    active = next((name for name, _ in reversed(titles) if name in data["titles"]), "UNRANKED")
    for owned in [True, False]:
        rows = []
        for name, requirement in titles:
            if (name in data["titles"]) != owned:
                continue
            status = "ACTIVE" if owned and name == active else "OBTAINED" if owned else "NOT OBTAINED"
            rows.append((format_title(name), status))
            rows += [("  " + text, "") for text in wrap(requirement, 41)]
        show_table("OWNED TITLES" if owned else "UNOBTAINED TITLES",
                   ["TITLE / REQUIREMENT", "STATUS"], rows or [("None", "--")], [43, 16])
    show("Your highest unlocked title is shown on the home screen.")
    show("Normal counts games; Rage D1/D2 count full matches.")
    show("Master uses cumulative rates; exactly 50% does not qualify.")
    show("Legendary uses combined net profit, including losses.")
    show("Clearing titles restores UNRANKED; profile data is kept.")
    show("New titles are checked after your next completed result.")


def show_progress_menu(section):
    title, view_label, clear_label = pages[section]
    views = {"profile": show_profile, "achievements": show_achievements,
             "collection": show_collection, "titles": show_titles}
    while True:
        show()
        show_table(title, ["KEY", "ACTION"],
                   [(color_text(str(key), menu_color(key)), color_text(label, menu_color(key)))
                    for key, label in [(1, view_label), (2, clear_label), (0, "RETURN TO HOME")]], [5, 54])
        choice = get_number("\n  SELECT AN OPTION [0-2] > ", 0, 2)
        if choice == 0:
            return
        data = load_data()
        if data is None:
            return
        if choice == 1:
            views[section](data)
        else:
            data[section] = new_data()[section]
            if save_data(data):
                show(title + " DATA CLEARED. OTHER SECTIONS ARE UNCHANGED.")
