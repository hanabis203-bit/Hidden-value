import interface as ui
from game import play_game, play_rage_match
from interface import get_number, show, show_home, show_rules_menu
from records import show_history_menu
from progress import get_player_title, show_progress_menu


def main():
    """Route terminal menu choices and handle the replay loop."""
    pages = {4: "profile", 6: "achievements", 7: "collection", 8: "titles"}
    while True:
        choice = show_home(get_player_title())

        if choice == 0:
            show("\nThanks for playing Hidden Value. Goodbye!")
            break

        if choice in [1, 2]:
            while True:
                if choice == 1:
                    play_game()
                else:
                    if play_rage_match() is False:
                        break
                if get_number("\nPlay again? 1 = Yes, 0 = Return to home: ", 0, 1) == 0:
                    break
        elif choice == 3:
            show_history_menu()
        elif choice in pages:
            show_progress_menu(pages[choice])
        elif choice == 5:
            show_rules_menu()


if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        ui.game_log = None
        show("\nGame stopped.")
