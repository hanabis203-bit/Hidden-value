# Terminal input, tables, menus and game rules.
import sys
import time
import re
import unicodedata
from rewards import title_colors, rainbow_colors
from settings import (bid_time_limit, catalogue, damaged_card_percent,
                      history_limit, normal_event_chance, starting_coins,
                      round_percentages, table_width)

# None disables logging; a list records the current game from Round 1.
game_log = None

# A single colour covers each navigation label; ANSI codes never enter saves.
home_title_color = "\033[1;38;5;220m"
menu_colors = {
    0: "\033[38;5;250m", 1: "\033[38;5;82m", 2: "\033[38;5;203m",
    3: "\033[38;5;45m", 4: "\033[38;5;75m", 5: "\033[38;5;141m",
    6: "\033[38;5;214m", 7: "\033[38;5;121m", 8: "\033[38;5;207m"
}
difficulty_colors = {1: "\033[38;5;51m", 2: "\033[38;5;196m"}


def show(*values, color=None):
    text = " ".join([str(value) for value in values])
    if color and sys.stdout.isatty():
        print(color + text + "\033[0m")
    else:
        print(text)
    if game_log is not None:
        game_log.append(plain_text(text))


def plain_text(text):
    return re.sub(r"\033\[[0-9;]*m", "", str(text))


def display_width(text):
    # Ignore colour codes and count wide Unicode characters as two columns.
    return sum(0 if unicodedata.combining(char) else
               2 if unicodedata.east_asian_width(char) in ["W", "F"] else 1
               for char in plain_text(text))


def color_text(text, color):
    return color + text + "\033[0m" if sys.stdout.isatty() else text


def menu_color(number, difficulty=False):
    return difficulty_colors[number] if difficulty and number in difficulty_colors else menu_colors[number]


def menu_option(number, label, difficulty=False):
    return color_text(f"  [{number}] {label}", menu_color(number, difficulty))


def format_title(name):
    label = name
    color = title_colors.get(name)
    if not color or not sys.stdout.isatty():
        return label
    if color == "RAINBOW":
        return "".join(rainbow_colors[index % len(rainbow_colors)] + char
                       for index, char in enumerate(label)) + "\033[0m"
    return color_text(label, color)


def ask(prompt):
    answer = input(prompt)
    if game_log is not None:
        game_log.append(prompt + answer)
    return answer


def get_number(prompt, minimum, maximum, deadline=None):
    """Retry invalid numbers while keeping the same optional round deadline."""
    while True:
        if deadline is None:
            answer = ask(prompt)
        else:
            if time.monotonic() >= deadline:
                return None
            answer = timed_input(prompt, deadline)
            if game_log is not None:
                game_log.append(prompt + ("[TIMEOUT]" if answer is None else answer))
            if answer is None:
                return None
        try:
            number = int(answer)
            if minimum <= number <= maximum:
                return number
        except ValueError:
            pass
        show("Invalid input: enter a whole number from", minimum, "to", maximum)


def update_countdown(deadline, previous):
    seconds = max(0, int(deadline - time.monotonic() + 0.999))
    if seconds != previous:
        filled = min(20, int(seconds * 20 / bid_time_limit))
        bar = "=" * filled + " " * (20 - filled)
        color = "\033[31m" if seconds <= 5 else ""
        print(f"\0337\033[1A\r\033[2K{color}TIME LEFT: {seconds:02d}s [{bar}]\033[0m\0338",
              end="", flush=True)
    return seconds


def timed_input(prompt, deadline):
    """Read until the shared deadline without leaving a background input task."""
    print("\n" + prompt, end="", flush=True)
    previous = update_countdown(deadline, None)
    if sys.platform == "win32":
        import msvcrt
        answer = ""
        special_key = False
        while time.monotonic() < deadline:
            previous = update_countdown(deadline, previous)
            if not msvcrt.kbhit():
                time.sleep(0.01)
                continue
            key = msvcrt.getwch()
            if special_key:
                special_key = False
            elif key in ["\x00", "\xe0"]:
                special_key = True
            elif key == "\x03":
                raise KeyboardInterrupt
            elif key == "\x1a":
                raise EOFError
            elif key in ["\r", "\n"]:
                print()
                return answer
            elif key == "\b":
                if answer:
                    answer = answer[:-1]
                    print("\b \b", end="", flush=True)
            elif key.isprintable():
                answer += key
                print(key, end="", flush=True)
    else:
        import select
        import termios
        while time.monotonic() < deadline:
            previous = update_countdown(deadline, previous)
            remaining = max(0, deadline - time.monotonic())
            ready, _, _ = select.select([sys.stdin], [], [], min(0.1, remaining))
            if ready:
                answer = sys.stdin.readline()
                if answer == "":
                    raise EOFError
                if time.monotonic() < deadline:
                    return answer.rstrip("\n")
        if sys.stdin.isatty():
            termios.tcflush(sys.stdin, termios.TCIFLUSH)
    update_countdown(deadline, previous)
    print()
    return None


def show_heading(title, color=None):
    border = "=" * table_width
    show(border, color=color)
    show("|" + title.center(table_width - 2) + "|", color=color)
    show(border, color=color)


def show_panel(title, rows, color=None, title_color=None):
    show_heading(title, title_color or color)
    for text in rows:
        show(text, color=color)
    show("=" * table_width, color=color)


def table_row(values, widths, right=()):
    cells = []
    for i, value in enumerate(values):
        text = str(value)
        padding = " " * max(0, widths[i] - display_width(text))
        cells.append(padding + text if i in right else text + padding)
    return " | ".join(cells)


def table_lines(headers, rows, widths, right=()):
    return [table_row(headers, widths, right), "=" * table_width] + [
        table_row(row, widths, right) for row in rows]


def show_table(title, headers, rows, widths, right=()):
    show_panel(title, table_lines(headers, rows, widths, right))


def show_home(title="UNRANKED"):
    show_panel("WELCOME TO HIDDEN VALUE^V^", [
        "  REVEAL THE HIDDEN VALUE, THEN BID WITHOUT HESITATION 😋",
        "  TITLE: " + format_title(title),
        " MAIN MENU ".center(table_width, "="),
        "",
        menu_option(1, "NORMAL MODE"),
        menu_option(2, "RAGE MODE"),
        menu_option(3, "VIEW GAME HISTORY"),
        menu_option(4, "PLAYER PROFILE"),
        menu_option(5, "GAME RULES"),
        menu_option(6, "ACHIEVEMENTS"),
        menu_option(7, "ITEM COLLECTION"),
        menu_option(8, "TITLES"),
        "",
        menu_option(0, "EXIT"),
        "",
        "  Enter a number and press Enter.",
        ""
    ], title_color=home_title_color)
    return get_number("\n  Select an option [0-8] > ", 0, 8)


def show_mode_rules(rage=False):
    rows = [
        "  1. SETUP",
        f"  You + {3 if rage else 2} computers; {starting_coins} coins each.",
        "  Eight hidden items: two from each category."
    ]
    if rage:
        rows += ["  First side to two wins takes the match.",
                 "  Funds, warehouse, cards and event reset each game."]
    rows += ["", "  2. PUBLIC EVENTS"]
    if rage:
        rows += ["  Choose Difficulty 1 or 2 before starting a match.",
                 "  DIFFICULTY 1 (DEFAULT): one fixed event per game.",
                 "  DIFFICULTY 2: redraw an event every auction round.",
                 "  Both difficulties guarantee an event (100% chance).",
                 "  The opening event is announced before shopping.",
                 "  Difficulty 1: clues stay valid throughout the game.",
                 "  Difficulty 2: each round resets to base prices;",
                 "  effects do not stack and previous clues expire."]
    else:
        rows += [f"  Per game: {100-normal_event_chance}% NO EVENT; {normal_event_chance}% with an event.",
                 "  Announced before shopping, then fixed for all rounds.",
                 "  NO EVENT: all items keep their base prices."]
    rows += [
        "  The four event types below are equally likely.",
        "  CATEGORY BOOM: one named category gains 25% value.",
        "  DAMAGED STOCK: shown damaged count; each is worth 0.",
        "  Their category stays hidden; item numbers are kept.",
        "  RARE / COMMON MARKET: affected values rise or fall 20%.",
        "  Rare: base price >=1000. Common: base price <1000.",
        "  Clues and resale use adjusted values, rounded down.",
        "", "  3. CLUE CARDS",
        "  Buy 0-3 different cards by number; 0 ends shopping.",
        "  Shopping also ends when three cards are bought.",
        "  Pay now; use at most one card per round, once per card.",
        "  Unused cards refund 50% of the price paid, rounded down.",
        f"  Opening DAMAGED STOCK: card prices are {100-damaged_card_percent}% off."
    ]
    rows += (["  Set categories for cards 2/6 in the shop; then fixed."] if rage else
             ["  Choose the category when using cards 2/6."])
    leads = ", ".join([">" + str(p) + "%" for p in round_percentages])
    rows += [
        "", "  4. BIDDING",
        f"  Rounds 1-5 required lead: {leads}.",
        "  Highest bid must beat the second-highest by that lead.",
        "  Up to five sealed-bid rounds; any sale ends the game.",
        "  A highest-bid tie means no sale.",
        "  Bid 2 to your balance; 1 means PASS THIS ROUND.",
        "  Losing bids cost 0. You may bid again next round.",
        "  Pass/timeout: a computer sale is your loss, even at a loss."
    ]
    if rage:
        rows += [f"  One {bid_time_limit}s timer covers card selection (or skip) and bidding.",
                 "  With no cards, the full time is for bidding.",
                 "  Invalid input keeps the timer running; timeout bids 0."]
    else:
        rows += ["  No time limit."]
    rows += ["", "  5. COMPUTER BIDDING",
             "  Computers buy no cards; bids stay within their balance.",
             "  A is cautious and probes more; B is more aggressive.",
             "  Each round starts with a new, noisy appraisal.",
             "  A/B raw appraisals: 70%-130% of the adjusted total."]
    if rage:
        rows += ["  C varies more: raw appraisals 50%-130% of that total."]
    rows += ["  Choices: risk, low probe, follow, or normal bidding.",
             "  Risk/probe choices can override following.",
             "  Risk bids may use public catalogue price averages.",
             "  Any computer can overestimate and buy at a loss.",
             "  Computer bids are set before your current input."]
    if rage:
        rows += ["  DIFFICULTY 1",
                 "  If behind, computers may follow last round's top bid.",
                 "  Probing varies; normal bids firm up in Rounds 4-5.",
                 "  DIFFICULTY 2",
                 "  Past bids are ignored; probing decreases each round.",
                 "  Opening/late rounds add bidding pressure.",
                 "  Risk bids are possible only in Rounds 4-5."]
    else:
        rows += ["  If behind, computers may follow last round's top bid.",
                 "  Probing varies; normal bids firm up in Rounds 4-5."]
    rows += ["", "  6. RESULTS",
             "  The buyer pays the bid and resells all items.",
             "  Net profit = final balance - starting coins."]
    rows += (["  DIFFICULTY 1: positive-profit purchase, or the computer",
              "  buyer loses money: you win the game.",
              "  DIFFICULTY 2: only a positive-profit purchase wins.",
              "  All other results give the computers one point."] if rage else
             ["  WIN: buy at positive net profit, or the computer buyer",
              "  loses money. Break-even or unsold after Round 5: no win."])
    if rage:
        rows += [f"  History: latest {history_limit} matches per difficulty."]
    else:
        rows += [f"  History: latest {history_limit} games."]
    rows += [f"  PROFILE: cumulative stats and latest-{history_limit} win rates.",
             "  Rage profile results count completed matches.",
             "  Completed games/matches unlock cosmetic rewards."]
    show_panel("RAGE MODE RULES" if rage else "NORMAL MODE RULES", rows)
    show_price_table()


def show_normal_rules():
    show_mode_rules()


def show_rules_menu():
    while True:
        show()
        show_panel("GAME RULES", [menu_option(1, "NORMAL MODE RULES"),
                   menu_option(2, "RAGE MODE RULES"), menu_option(0, "RETURN TO HOME")])
        choice = get_number("\n  Select an option [0-2] > ", 0, 2)

        if choice == 0:
            return
        if choice == 1:
            show_normal_rules()
        else:
            show_rage_rules()


def show_rage_rules():
    show_mode_rules(rage=True)


def show_price_table():
    show("\nPUBLIC PRICE TABLE - BASE PRICES IN COINS")
    show("Rare/Common events select items by their base prices.")
    for category in catalogue:
        show_table(category.upper(), ["ITEM", "PRICE"], catalogue[category], [43, 16], right=(1,))
