# Recent game transcripts; profile progress is saved separately.
from settings import history_limit, history_marker
from interface import get_number, show, show_panel, menu_option


def history_difficulty(record):
    for difficulty in [1, 2]:
        if record.splitlines()[0] == f"RAGE DIFFICULTY: {difficulty}":
            return difficulty
    return 0  # Older records without a difficulty label.


def read_history(filename, difficulty=None):
    """Read completed transcripts, optionally filtering one Rage difficulty."""
    try:
        with open(filename, "r", encoding="utf-8") as file:
            content = file.read()
        records = [part.strip() for part in content.split(history_marker) if part.strip()]
        if difficulty is not None:
            records = [record for record in records if history_difficulty(record) == difficulty]
        return records
    except FileNotFoundError:
        return []
    except (OSError, UnicodeError) as error:
        show("HISTORY COULD NOT BE READ:", error)
        return None


def save_history(lines, filename="normal_history.txt"):
    """Keep recent records with separate limits for the two Rage difficulties."""
    records = read_history(filename)
    if records is None:
        return
    records.append("\n".join(lines).strip())
    if filename == "rage_history.txt":
        counts = [0, 0, 0]
        recent = []
        for record in reversed(records):
            difficulty = history_difficulty(record)
            if counts[difficulty] < history_limit:
                recent.append(record)
                counts[difficulty] += 1
        records = list(reversed(recent))
    else:
        records = records[-history_limit:]
    # Six newline characters leave five blank lines between games.
    text = ("\n" * 6 + history_marker).join(records)
    try:
        with open(filename, "w", encoding="utf-8") as file:
            file.write(history_marker + text + "\n")
    except (OSError, UnicodeError) as error:
        print("History could not be saved:", error)


def show_history(filename, difficulty=None):
    records = read_history(filename, difficulty)
    if records is None:
        return
    if not records:
        show("NO HISTORY FOUND.")
        return

    show("\nHISTORY IS DISPLAYED FROM NEWEST TO OLDEST.\n")
    records = list(reversed(records[-history_limit:]))
    blocks = []
    for i in range(len(records)):
        blocks.append(f"GAME {i + 1}\n" + records[i])
    show(("\n" * 6).join(blocks))


def show_history_menu():
    while True:
        show()
        show_panel("GAME HISTORY", [menu_option(1, "NORMAL MODE HISTORY"),
                   menu_option(2, "RAGE MODE HISTORY"), menu_option(3, "CLEAR HISTORY"),
                   menu_option(0, "RETURN TO HOME")])
        choice = get_number("\n  SELECT AN OPTION [0-3] > ", 0, 3)

        if choice == 0:
            return
        if choice == 1:
            show("\nNORMAL MODE HISTORY")
            show_history("normal_history.txt")
        elif choice == 2:
            show_rage_records_menu()
        else:
            show_clear_history_menu()


def clear_history(filename):
    try:
        # Write mode clears the entire file, including all old record markers.
        with open(filename, "w", encoding="utf-8") as file:
            file.write("")
        show("ALL HISTORY CONTENTS CLEARED:", filename)
    except (OSError, UnicodeError) as error:
        show("HISTORY COULD NOT BE CLEARED:", error)


def show_clear_history_menu():
    while True:
        show()
        show_panel("CLEAR HISTORY", [menu_option(1, "NORMAL MODE"),
                   menu_option(2, "RAGE MODE (BOTH DIFFICULTIES)"),
                   menu_option(0, "RETURN TO VIEW GAME HISTORY")])
        choice = get_number("\n  SELECT AN OPTION [0-2] > ", 0, 2)
        if choice == 0:
            return
        filename = "normal_history.txt" if choice == 1 else "rage_history.txt"
        clear_history(filename)


def show_rage_records_menu():
    while True:
        show()
        show_panel("RAGE MODE HISTORY", [menu_option(1, "DIFFICULTY 1", True),
                   menu_option(2, "DIFFICULTY 2", True),
                   menu_option(0, "RETURN TO VIEW GAME HISTORY")])
        difficulty = get_number("\n  SELECT DIFFICULTY [0-2] > ", 0, 2)
        if difficulty == 0:
            return
        show("\nRAGE MODE HISTORY - DIFFICULTY", difficulty)
        show_history("rage_history.txt", difficulty)
