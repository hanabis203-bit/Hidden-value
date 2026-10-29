# Auction rules, clue cards, events and computer decision tree.
import random
import sys
import time
import interface as ui
import progress
from settings import (bid_time_limit, catalogue, clues, computer_settings,
                      cyan, damaged_card_percent, green, grey,
                      normal_event_chance, player_names, rage2_round_factors,
                      red, round_percentages, starting_coins, table_width, yellow)
from interface import (get_number, show, show_heading, show_panel, show_table,
                       table_lines, table_row, menu_option, menu_color)
from records import save_history


def get_bid(balance, rage=False, deadline=None):
    if rage and deadline is None:
        deadline = time.monotonic() + bid_time_limit
    number = get_number("Enter your bid (1 = pass this round): ", 1, balance, deadline)
    if number is None:
        show("TIME UP! Your bid is 0 for this round.")
        return 0
    return number


def create_warehouse():
    warehouse = []
    for category in catalogue:
        for name, value in random.sample(catalogue[category], 2):
            warehouse.append({"name": name, "category": category, "value": value})
    return warehouse


def apply_event(warehouse, rage=False):
    """Adjust base prices afresh so repeated events never stack their effects."""
    # Normal: a 30% event chance. Rage: always draw one of the four events.
    event = 0
    if rage or random.randint(1, 100) <= normal_event_chance:
        event = random.randint(1, 4)
    names = ["NO EVENT", "CATEGORY BOOM", "DAMAGED STOCK",
             "RARE MARKET", "COMMON MARKET"]
    category = random.choice(list(catalogue)) if event in [1, 2] else None
    percent = 100
    if event == 0:
        description = "No event. All items keep their base prices."
    elif event == 1:
        percent = 125
        description = f"{category.upper()}: all values +25%."
    elif event == 2:
        percent = 0
        count = sum([item["category"] == category for item in warehouse])
        description = f"{count} damaged items. Each is worth 0 coins."
    else:
        percent = random.choice([80, 120])
        target = ">=1000" if event == 3 else "<1000"
        description = f"Base price {target}: all values {percent - 100:+d}%."

    for item in warehouse:
        base = item.get("base_value", item["value"])
        item["base_value"] = base
        affected = (event in [1, 2] and item["category"] == category or
                    event == 3 and base >= 1000 or event == 4 and base < 1000)
        item["value"] = base * percent // 100 if affected else base
    return names[event], description


def show_event(event, rage=False, difficulty=1, compact=False):
    if compact:
        show("EVENT:", event[0], "|", event[1], color=yellow)
        return
    duration = "ROUND" if rage and difficulty == 2 else "GAME"
    show_panel("PUBLIC EVENT: " + event[0], [
        "  " + event[1],
        f"  FIXED THIS {duration} | CLUES AND PAYOUTS USE ADJUSTED VALUES."
    ], color=yellow)


def show_warehouse(warehouse, reveal=False):
    show("\nWAREHOUSE REVEAL" if reveal else "\nWAREHOUSE ITEMS")
    if reveal:
        show("Coins; event-adjusted items show base -> final.")
    previous_category = None
    for i in range(len(warehouse)):
        item = warehouse[i]
        if reveal:
            if item["category"] != previous_category:
                show("\n" + item["category"].upper())
                previous_category = item["category"]
            rare = item["value"] >= 1000
            damaged = item["value"] == 0
            label = " [DAMAGED]" if damaged else " [RARE]" if rare else ""
            base = item.get("base_value", item["value"])
            value = str(item["value"]) if base == item["value"] else f"{base} -> {item['value']}"
            show(f"  {i + 1}. {item['name']}: {value} coins{label}",
                 color=red if damaged else yellow if rare else None)
        else:
            show(i + 1, "-", item["category"], "- Hidden")


def create_players(rage=False):
    players = []
    names = player_names + ["Computer C"] if rage else player_names
    for name in names:
        players.append({
            "name": name, "balance": starting_coins,
            "cards": [], "cost": 0, "information": [],
            "prices": [clue[1] for clue in clues], "categories": {}
        })
    return players


def buy_clues(player, rage=False, damaged=False):
    percent = damaged_card_percent if damaged else 100
    player["prices"] = [clue[1] * percent // 100 for clue in clues]
    show_heading("INFORMATION CARD SHOP")
    show("Buy up to 3 different cards. Use at most one per round.")
    show("Pay now. Unused cards receive a 50% refund at the end.")
    if damaged:
        show(f"DAMAGED STOCK BONUS: {100-percent}% OFF ALL CLUE CARDS", color=yellow)
    if rage:
        show("Set categories for cards 2/6 here, before the round timer.")
    for line in table_lines(["ID", "CARD", "PRICE"], [], [3, 45, 8], right=(0, 2)):
        show(line)
    for i, (name, price, description) in enumerate(clues):
        show(table_row([i + 1, name, player["prices"][i]], [3, 45, 8], right=(0, 2)),
             color=menu_color(i + 1))
        show("      " + description, color=menu_color(i + 1))
    show("=" * table_width)
    show("0 - Finish shopping and start the auction.")
    while len(player["cards"]) < 3:
        show("\nYour balance:", player["balance"], "| Cards:", len(player["cards"]), "/ 3")
        selected = ", ".join([str(card + 1) for card in player["cards"]])
        show("[BOUGHT] Card IDs:", selected or "None")
        choice = get_number("Choose a card to buy (0 to start): ", 0, len(clues))
        if choice == 0:
            break
        card = choice - 1
        if card in player["cards"]:
            show("Already purchased. Choose a different card.")
            continue
        name = clues[card][0]
        price = player["prices"][card]
        if player["balance"] < price:
            show("Not enough coins. Choose another card or enter 0.")
            continue
        player["balance"] -= price
        player["cost"] += price
        player["cards"].append(card)
        show("[BOUGHT]", name, "| Price:", price, color=menu_color(card + 1))
        if rage and card in [1, 5]:
            show("Set category for", name, "(fixed this game):", color=menu_color(card + 1))
            player["categories"][card] = choose_category()
    if len(player["cards"]) == 3:
        show("3-card limit reached. Starting the auction.")
    show("Your clue cost:", player["cost"], "| Remaining coins:", player["balance"])


def calculate_clue_refund(player):
    """Refund half of the actual price paid for each unused card, rounded down."""
    refund = 0
    for card in player["cards"]:
        refund += player["prices"][card] // 2
    return refund


def show_bid_costs(player):
    # Preview only; refunds are credited during final settlement.
    refund = calculate_clue_refund(player)
    net_cost = player["cost"] - refund
    show(f"CLUE COST NOW: {player['cost']} paid - {refund} refund = {net_cost}")
    show(f"ESTIMATED PROFIT = YOUR VALUE ESTIMATE - BID - {net_cost}")


def show_round_status(player, round_index, percentage, rage, difficulty, match_score):
    mode = f"RAGE - DIFFICULTY {difficulty}" if rage else "NORMAL"
    refund = calculate_clue_refund(player)
    rows = [("BALANCE", player["balance"], "REQUIRED LEAD", f">{percentage}%"),
            ("CLUES PAID", player["cost"], "UNUSED REFUND", refund),
            ("NET CLUE COST", player["cost"] - refund, "CARDS LEFT", len(player["cards"]))]
    if rage and match_score is not None:
        yours, computers = match_score
        rows.append(("SCORE - YOU", yours, "COMPUTERS", computers))
    show_table(f"{mode} | ROUND {round_index + 1}/{len(round_percentages)}",
               ["STATUS", "VALUE", "STATUS", "VALUE"], rows, [19, 8, 19, 7], right=(1, 3))
    if rage and match_score is not None and yours == computers == 1:
        show("FINAL GAME - WIN THIS GAME TO WIN THE MATCH!", color=yellow)


def choose_category(deadline=None):
    categories = list(catalogue)
    for i in range(len(categories)):
        show(i + 1, "-", categories[i])
    return get_number("Choose category: ", 1, len(categories), deadline)


def get_clue(warehouse, card, deadline=None, category_number=None):
    values = [item["value"] for item in warehouse]

    if card == 0:
        estimate = random.choice(values) * random.randint(80, 120) // 100
        return f"One random item is estimated at about {estimate} coins."
    if card in [1, 5]:
        categories = list(catalogue)
        number = category_number if category_number is not None else choose_category(deadline)
        if number is None:
            return None
        category = categories[number - 1]
        count = 0
        total = 0
        for item in warehouse:
            if item["category"] == category:
                total += item["value"]
                if item["value"] >= 300:
                    count += 1
        if card == 5:
            lower = total // 500 * 500
            return f"{category}: category total range {lower}-{lower + 499} coins."
        return f"{category}: {count} item(s) worth at least 300."
    if card == 2:
        index = random.randint(0, len(warehouse) - 1)
        return f"Item {index + 1}: exactly {values[index]} coins."
    if card == 3:
        count = 0
        for value in values:
            if value >= 1000:
                count += 1
        return f"Warehouse: {count} item(s) worth at least 1000."
    if card == 4:
        return f"Second-highest item value: {sorted(values)[-2]} coins."
    if card == 6:
        count = 0
        for value in values:
            if 300 <= value < 1000:
                count += 1
        return f"Warehouse: {count} item(s) worth 300-999 coins."
    subtotal = 0
    for value in values:
        if value < 300:
            subtotal += value
    lower = subtotal // 100 * 100
    return f"Low-value subtotal range: {lower}-{lower + 99} coins."


def use_clue(warehouse, player, rage=False):
    show("\nKNOWN INFORMATION")
    for information in player["information"] or ["None"]:
        show(information, color=player.get("information_colors", {}).get(information))

    if player["cards"]:
        show("Available cards: 0 - Skip")
        for card in player["cards"]:
            show(card + 1, "-", clues[card][0], color=menu_color(card + 1))
    deadline = None
    if rage:
        show("Round time limit:", bid_time_limit, "seconds for card selection and bidding.")
        deadline = time.monotonic() + bid_time_limit
    if player["cards"] == []:
        return deadline
    while True:
        choice = get_number("Choose a card: ", 0, len(clues), deadline)
        if choice is None or choice == 0:
            return deadline
        card = choice - 1
        if card in player["cards"]:
            break
        show("Invalid input: that card is not available.")

    information = get_clue(warehouse, card, deadline, player["categories"].get(card))
    if information is not None:
        player["information"].append(information)
        player["cards"].remove(card)
        # Keep clue text plain; remember its card colour only for display.
        if "information_colors" not in player:
            player["information_colors"] = {}
        player["information_colors"][information] = menu_color(card + 1)
        show("[USED]", clues[card][0], color=menu_color(card + 1))
        show("[NEW]", information, color=menu_color(card + 1))
    return deadline


def get_computer_bid(total_value, balance, aggressive=False, volatile=False,
                     rage=False, round_index=0, previous_bids=None, difficulty=1):
    """Choose a legal AI quote from a noisy appraisal and prior public bids."""
    # Only the noisy valuation and completed rounds are available to the tree.
    estimate = total_value * random.randint(50 if volatile else 70, 130) / 100
    factor, risk_factor, risk_scale, probe_step = computer_settings[difficulty if rage else 0]
    if rage and difficulty == 2:
        factor *= rage2_round_factors[round_index]
    probe_chance = 20 if aggressive else 40
    if volatile:
        probe_chance = 30
    probe_chance += round_index * probe_step
    previous = previous_bids[-1] if previous_bids else None
    index = 3 if volatile else 2 if aggressive else 1
    mood = random.randint(1, 100)
    risk_chance = int((22 if volatile else 16 if aggressive else 8) * risk_scale)
    target = 0

    # Try risk or probe first, then follow public bids or use the round's range.
    if mood > 100 - risk_chance and (not rage or difficulty == 1 or round_index >= 3):
        # Two of eight items per category: one quarter of all listed prices.
        public_average = sum([v for rows in catalogue.values() for _, v in rows]) / 4
        estimate = max(estimate, public_average)  # An overconfident catalogue-price anchor.
        factor = risk_factor  # Overconfidence can cause a real loss.
        lower, upper = 0.80, 1.00
    elif mood <= probe_chance:
        lower, upper = 0.25, 0.50
    elif previous and not (rage and difficulty == 2) and previous[index] < max(previous):
        lower, upper = 0.70, 1.00
        target = min(balance, int(min(estimate, max(previous))))
    elif round_index >= 3:
        lower, upper = 0.65, 1.00
    else:
        lower, upper = 0.55, 0.90
    ceiling = max(1, min(balance, int(estimate * factor)))
    lowest = max(1, int(ceiling * lower), target * 90 // 100)
    highest = min(balance, max(1, int(ceiling * upper), target * 110 // 100))
    return random.randint(lowest, highest)


def check_sale(bids, percentage):
    """Return the winner only when the highest bid strictly exceeds the gap."""
    ordered = sorted(bids)
    if ordered[-1] * 100 > ordered[-2] * (100 + percentage):
        return bids.index(ordered[-1])
    return None


def show_bids(players, bids, percentage):
    second, highest = sorted(bids)[-2:]
    rows = []
    for i in range(len(players)):
        length = bids[i] * 20 // highest if highest else 0
        bar = "=" * length
        passed = i == 0 and bids[i] <= 1
        rows.append((players[i]["name"], "PASS" if passed else bids[i],
                     "NO BID THIS ROUND" if passed else f"[{bar:<20}]"))
    show_table("BID COMPARISON", ["BIDDER", "BID", "COMPARISON"], rows, [18, 10, 28], right=(1,))
    if second > 0:
        lead = (highest - second) * 100 / second
        show(f"Highest lead: {lead:.2f}% | Required: more than {percentage}%")
    else:
        show("Highest lead: no positive second bid.")
    winner = check_sale(bids, percentage)
    if winner is None:
        reason = "HIGHEST BIDS TIED" if highest == second else "REQUIRED LEAD NOT REACHED"
        show("NO SALE -", reason, color=yellow)
        minimum = second * (100 + percentage) // 100 + 1
        show("Minimum sale bid this round:", minimum)
    else:
        show("SOLD TO:", players[winner]["name"], "| PRICE:", bids[winner], color=green)
    return winner


def run_auction(warehouse, players, rage=False, match_score=None, event=None, difficulty=1):
    """Keep bids as a two-dimensional list: rows are rounds, columns are bidders."""
    bid_history = []
    winner = None
    for round_index in range(len(round_percentages)):
        percentage = round_percentages[round_index]
        show()
        show_round_status(players[0], round_index, percentage, rage, difficulty, match_score)
        if rage and (event is None or difficulty == 2 and round_index > 0):
            event = apply_event(warehouse, rage=True)
            if players[0]["information"]:
                show("[EXPIRED] Previous-round clues no longer apply.", color=yellow)
                players[0]["information"] = []
                players[0].get("information_colors", {}).clear()
        if event is not None:
            show_event(event, rage, difficulty, compact=(round_index > 0 and not (rage and difficulty == 2)))
        total_value = sum([item["value"] for item in warehouse])
        # Generate computer bids before receiving the player's current input.
        computer_bids = []
        for i in range(1, len(players)):
            computer_bids.append(get_computer_bid(
                total_value, players[i]["balance"],
                aggressive=(i == 2), volatile=(i == 3), rage=rage,
                round_index=round_index, previous_bids=bid_history, difficulty=difficulty))

        deadline = use_clue(warehouse, players[0], rage)
        show_bid_costs(players[0])
        player_bid = get_bid(players[0]["balance"], rage, deadline)
        bids = [player_bid] + computer_bids
        bid_history.append(bids)
        winner = show_bids(players, bids, percentage)
        if winner is not None:
            break
    return winner, bid_history


def show_result(warehouse, players, winner, bid_history, rage=False, difficulty=1):
    """Settle the purchase and refunds once, then apply the mode's win rule."""
    total_value = sum([item["value"] for item in warehouse])
    base_total = sum([item.get("base_value", item["value"]) for item in warehouse])
    price = bid_history[-1][winner] if winner is not None else 0
    if winner is not None:
        players[winner]["balance"] += total_value - price
    refunds = [calculate_clue_refund(player) for player in players]
    for i in range(len(players)):
        players[i]["balance"] += refunds[i]

    won = False
    if winner is None:
        result = "The warehouse remains unsold. No win."
    elif winner == 0 and players[0]["balance"] > starting_coins:
        won = True
        result = "You win!"
    elif ((not rage or difficulty == 1) and winner != 0
          and bid_history[-1][0] > 1 and players[winner]["balance"] < starting_coins):
        won = True
        result = "The computer loses money. You win!"
    else:
        result = "You lose!"

    player = players[0]
    profit = player["balance"] - starting_coins
    show_warehouse(warehouse, reveal=True)
    show()
    show_heading("SETTLEMENT")
    show(f"WAREHOUSE VALUE: {total_value} coins", color=yellow)
    if base_total != total_value:
        show(f"Base value: {base_total} (event change: {total_value - base_total:+d})", color=grey)
    buyer = players[winner]["name"] if winner is not None else "NONE"
    show("BUYER:", buyer, color=cyan)
    if winner is not None:
        show("Purchase price:", price, "coins")

    show("\nYOUR SUMMARY", color=cyan)
    profit_color = green if profit > 0 else red if profit < 0 else yellow
    show(f"NET PROFIT: {profit:+d} coins", color="\033[1m" + profit_color)
    show(f"Clue cost: {player['cost']}; refund: {refunds[0]}; actual cost: {player['cost'] - refunds[0]}")
    show("Final balance:", player["balance"], "coins")

    show("\nCOMPUTER RESULTS", color=grey)
    for computer in players[1:]:
        net = computer["balance"] - starting_coins
        show(f"{computer['name']}: net profit {net:+d} coins", color=red if net < 0 else green if net > 0 else grey)
    show("=" * table_width)
    # Display the outcome once; keep this final line for win-rate statistics.
    outcome_color = green if won else red if winner is not None else yellow
    show(result, color="\033[1m" + outcome_color)
    return won


def play_game(rage=False, match_score=None, difficulty=1, completed_games=None):
    """Run one auction; Rage game summaries are saved with the completed match."""
    ui.game_log = None
    progress.load_data()  # Import older history before recording this new game.
    show("Starting coins:", starting_coins)
    warehouse = create_warehouse()
    event = apply_event(warehouse, rage)
    show_event(event, rage, difficulty)
    players = create_players(rage)
    buy_clues(players[0], rage, event[0] == "DAMAGED STOCK")
    bought = len(players[0]["cards"])
    ui.game_log = []
    winner, bid_history = run_auction(warehouse, players, rage, match_score, event, difficulty)
    won = show_result(warehouse, players, winner, bid_history, rage, difficulty)
    summary = {"profit": players[0]["balance"] - starting_coins,
               "items": [item["name"] for item in warehouse],
               "purchased": winner == 0, "rounds": len(bid_history),
               "bought": bought, "used": bought - len(players[0]["cards"])}
    if completed_games is not None:
        completed_games.append(summary)
    if not rage:
        save_history(ui.game_log)
        ui.game_log = None
        progress.record_result("normal", won, [summary])
    return won


def choose_rage_difficulty():
    show_panel("RAGE MODE - SELECT DIFFICULTY", [
        menu_option(1, "DIFFICULTY 1 - FIXED EVENT PER GAME (DEFAULT)", True),
        menu_option(2, "DIFFICULTY 2 - NEW EVENT EACH ROUND", True),
        menu_option(0, "RETURN TO HOME")
    ])
    return get_number("\n  SELECT DIFFICULTY [0-2] > ", 0, 2)


def play_rage_match():
    """Count the first side to two game wins as one complete profile result."""
    difficulty = choose_rage_difficulty()
    if difficulty == 0:
        return False
    if not sys.stdin.isatty():
        show("RAGE MODE NEEDS AN INTERACTIVE TERMINAL. Please run it in a terminal.")
        return False

    your_wins = 0
    computer_wins = 0
    match_log = []
    completed_games = []
    for game_number in range(1, 4):
        show_panel(f"RAGE MODE - DIFFICULTY {difficulty}", [f"  GAME {game_number} OF 3",
                   f"  SCORE: YOU {your_wins} - COMPUTERS {computer_wins}"])
        if play_game(rage=True, match_score=(your_wins, computer_wins),
                     difficulty=difficulty, completed_games=completed_games):
            your_wins += 1
        else:
            computer_wins += 1
        show(f"SCORE: YOU {your_wins} - COMPUTERS {computer_wins}")
        if match_log:
            match_log.extend([""] * 5)
        match_log.append(f"GAME {game_number} OF 3")
        match_log.extend(ui.game_log)
        ui.game_log = None
        if your_wins == 2 or computer_wins == 2:
            break

    ui.game_log = [f"RAGE DIFFICULTY: {difficulty}"] + match_log
    show("MATCH RESULT: YOU WIN!" if your_wins == 2 else "MATCH RESULT: YOU LOSE!")
    save_history(ui.game_log, "rage_history.txt")
    ui.game_log = None
    progress.record_result("rage" + str(difficulty), your_wins == 2, completed_games)
