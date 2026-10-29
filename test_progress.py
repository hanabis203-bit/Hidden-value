"""Standard-library checks. Run: python test_progress.py"""
import json
import os
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import game
import interface as ui
import main
import progress
import records
import rewards
from settings import catalogue, history_limit, starting_coins


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.folder = TemporaryDirectory()
        self.previous = os.getcwd()
        os.chdir(self.folder.name)
        self.output = StringIO()
        self.redirect = redirect_stdout(self.output)
        self.redirect.__enter__()
        ui.game_log = None

    def tearDown(self):
        ui.game_log = None
        self.redirect.__exit__(None, None, None)
        os.chdir(self.previous)
        self.folder.cleanup()

    def test_initial_import_and_independent_reset(self):
        records.save_history(["NET PROFIT: +1200 coins", "You win!"])
        for difficulty, ending in [(1, "WIN"), (2, "LOSE")]:
            records.save_history([f"RAGE DIFFICULTY: {difficulty}",
                                  f"MATCH RESULT: YOU {ending}!"], "rage_history.txt")
        data = progress.load_data()
        self.assertEqual([data["profile"][key]["played"] for key, _ in progress.modes], [1, 1, 1])
        self.assertEqual([data["profile"][key]["wins"] for key, _ in progress.modes], [1, 1, 0])
        self.assertEqual(data["profile"]["normal"]["best_profit"], 1200)
        # Clearing profile must not re-import the old history on the next load.
        with patch("builtins.input", side_effect=["2", "0"]):
            progress.show_progress_menu("profile")
        self.assertEqual(progress.load_data()["profile"]["normal"]["played"], 0)
        self.assertEqual(len(records.read_history("normal_history.txt")), 1)
        records.clear_history("normal_history.txt")
        self.assertEqual(Path("normal_history.txt").read_text(), "")
        self.assertEqual(progress.load_data()["profile"]["normal"]["played"], 0)

    def test_counts_recent_rates_and_rewards(self):
        summary = {"profit": 1500, "items": ["USB cable", "Mouse"]}
        for number in range(20):
            progress.record_result("normal", number % 2 == 0, [summary])
        progress.record_result("rage1", False, [{"profit": -100, "items": ["Mouse"]}] * 2)
        progress.record_result("rage2", True, [summary] * 3)
        data = progress.load_data()
        stats = data["profile"]["normal"]
        self.assertEqual((stats["played"], stats["wins"]), (20, 10))
        self.assertEqual((len(stats["recent"]), sum(stats["recent"])), (15, 7))
        self.assertEqual(stats["total_profit"], 30000)
        self.assertEqual(stats["best_streak"], 1)
        self.assertEqual(data["profile"]["rage1"]["played"], 1)
        self.assertEqual(data["profile"]["rage1"]["total_profit"], -200)
        self.assertEqual(data["profile"]["rage2"]["played"], 1)
        self.assertEqual(data["profile"]["rage2"]["total_profit"], 4500)
        self.assertEqual(len(data["collection"]), 2)
        self.assertTrue({"first_win", "big_profit", "rage_master"}.issubset(data["achievements"]))
        self.assertEqual(progress.get_player_title(), "UNRANKED")
        # A title or achievement reset cannot erase another section.
        for section in ["achievements", "collection", "titles"]:
            before = progress.load_data()
            with patch("builtins.input", side_effect=["2", "0"]):
                progress.show_progress_menu(section)
            after = progress.load_data()
            self.assertEqual(after[section], progress.new_data()[section])
            for other in progress.pages:
                if other != section:
                    self.assertEqual(after[other], before[other])
        self.assertEqual(progress.get_player_title(), "UNRANKED")
        # Restored titles require a new qualifying result, not old achievements.
        progress.record_result("normal", False, [{"profit": -1, "items": []}])
        self.assertEqual(progress.get_player_title(), "UNRANKED")

    def test_full_games_matches_and_history(self):
        lot = [{"name": name, "category": category, "value": value}
               for category, items in catalogue.items() for name, value in items[:2]]
        def computer_bid(total, balance, aggressive=False, volatile=False, **kwargs):
            return 800 if volatile else 1000 if aggressive else 2500
        with patch.object(game, "create_warehouse", side_effect=lambda: [dict(item) for item in lot]), \
             patch.object(game, "apply_event", return_value=("NO EVENT", "Test")), \
             patch.object(game, "buy_clues"), patch.object(game, "get_bid", return_value=500), \
             patch.object(game, "get_computer_bid", side_effect=computer_bid), \
             patch.object(game.sys.stdin, "isatty", return_value=True):
            # Direct entry without the home menu must not count this game twice.
            self.assertTrue(game.play_game())
            for difficulty in [1, 2]:
                with patch.object(game, "choose_rage_difficulty", return_value=difficulty):
                    game.play_rage_match()
        data = progress.load_data()
        for key, _ in progress.modes:
            self.assertEqual(data["profile"][key]["played"], 1)
        self.assertEqual([data["profile"][key]["wins"] for key, _ in progress.modes], [1, 1, 0])
        self.assertEqual(len(data["collection"]), 8)
        self.assertTrue(records.read_history("normal_history.txt")[-1].endswith("You win!"))
        for difficulty, outcome in [(1, "WIN"), (2, "LOSE")]:
            saved = records.read_history("rage_history.txt", difficulty)[-1]
            self.assertTrue(saved.endswith(f"MATCH RESULT: YOU {outcome}!"))
            self.assertNotIn("ACHIEVEMENT UNLOCKED", saved)
            self.assertNotIn("\033", saved)
        self.assertIsNone(ui.game_log)

    def test_history_limits_and_order(self):
        for number in range(history_limit + 2):
            records.save_history([f"TEST {number}", "You win!"])
            for difficulty in [1, 2]:
                records.save_history([f"RAGE DIFFICULTY: {difficulty}", f"TEST {number}",
                                      "MATCH RESULT: YOU WIN!"], "rage_history.txt")
        self.assertEqual(len(records.read_history("normal_history.txt")), 15)
        for difficulty in [1, 2]:
            self.assertEqual(len(records.read_history("rage_history.txt", difficulty)), 15)
        self.assertIn("\n" * 6 + records.history_marker, Path("normal_history.txt").read_text())
        self.output.seek(0)
        self.output.truncate()
        records.show_history("normal_history.txt")
        text = self.output.getvalue()
        self.assertLess(text.index("TEST 16\n"), text.index("TEST 2\n"))

    def test_invalid_files_are_preserved(self):
        for text in ["{broken", json.dumps({"profile": []}), "[]"]:
            Path(progress.data_file).write_text(text)
            self.assertIsNone(progress.load_data())
            self.assertEqual(Path(progress.data_file).read_text(), text)
        with patch("progress.os.replace", side_effect=OSError("read only")):
            self.assertFalse(progress.save_data(progress.new_data()))
        self.assertEqual(Path(progress.data_file).read_text(), "[]")

    def test_menu_routes_table_widths_and_input_errors(self):
        # Visit every new page, view its table, then return to home.
        answers = ["bad", "9"]
        for option in [4, 6, 7, 8]:
            answers += [str(option), "bad", "3", "1", "0"]
        answers += ["0"]
        with patch("builtins.input", side_effect=answers):
            main.main()
        text = self.output.getvalue()
        for title in ["PLAYER PROFILE", "ACHIEVEMENTS", "ITEM COLLECTION", "TITLES"]:
            self.assertIn(title, text)
        self.assertIn("Invalid input", text)
        self.assertIn("RAGE D1", text)
        self.assertIn("RAGE D2", text)
        self.assertNotIn("PERSONAL WIN RATE", text)
        for line in text.splitlines():
            if " | " in line or line.startswith("|") or line.startswith("="):
                self.assertEqual(ui.display_width(line), 62, line)

    def test_sale_profit_and_pass_rules(self):
        for percent in game.round_percentages:
            price = 1000 + percent * 10
            self.assertIsNone(game.check_sale([price, 1000, 800], percent))
            self.assertEqual(game.check_sale([price + 1, 1000, 800], percent), 0)
        self.assertIsNone(game.check_sale([1000, 1600, 1600], 0))
        lot = [{"name": "Laptop", "category": "Electronics", "value": 2000}]
        for rage, difficulty in [(False, 1), (True, 1), (True, 2)]:
            for bid in [0, 1, 500]:
                players = game.create_players(rage)
                bids = [bid, 2500, 800] + ([500] if rage else [])
                won = game.show_result(lot, players, 1, [bids], rage, difficulty)
                self.assertEqual(won, bid > 1 and (not rage or difficulty == 1))
                self.assertEqual(players[1]["balance"], starting_coins - 500)

    def test_all_30_achievements_and_old_save_compatibility(self):
        self.assertEqual(len(rewards.achievements), 30)
        self.assertEqual(len({row[0] for row in rewards.achievements}), 30)
        data = progress.new_data()
        data["achievements"] = ["first_win", "big_profit", "rage_master"]
        del data["title_rules"]
        data["titles"] = ["ROOKIE BIDDER", "SMART BIDDER", "VALUE HUNTER", "RAGE CHAMPION"]
        # The previous JSON format loads without a reset or conversion.
        Path(progress.data_file).write_text(json.dumps(data))
        migrated = progress.load_data()
        for section in ["profile", "achievements", "collection"]:
            self.assertEqual(migrated[section], data[section])
        self.assertEqual(migrated["titles"], [])
        self.assertEqual(migrated["title_rules"], rewards.title_rules_version)
        data = migrated
        for stats in data["profile"].values():
            stats.update(played=50, wins=25, best_streak=5)
        data["collection"] = [name for items in catalogue.values() for name, _ in items]
        progress.save_data(data)
        games = [{"profit": 2000, "items": [], "purchased": True,
                  "rounds": 1, "bought": 0, "used": 0},
                 {"profit": 2000, "items": [], "purchased": True,
                  "rounds": 5, "bought": 2, "used": 1}]
        progress.record_result("rage2", True, games)
        after = progress.load_data()
        self.assertEqual(set(after["achievements"]), {row[0] for row in rewards.achievements})
        self.assertEqual(after["titles"], ["ROOKIE BIDDER", "SEASONED BIDDER"])
        self.assertNotIn("AUCTION KING", after["titles"])
        self.assertEqual(len(after["collection"]), 32)

    def test_profit_card_and_round_achievement_boundaries(self):
        profile = progress.new_data()["profile"]
        def earned(game, mode="normal", won=False):
            return rewards.earned_achievements(profile, [], mode, won, [game])
        for profit, expected in [(0, []), (1, ["profit_1"]),
                                 (499, ["profit_1"]), (500, ["profit_1", "profit_500"]),
                                 (999, ["profit_1", "profit_500"]),
                                 (1000, ["profit_1", "profit_500", "big_profit"]),
                                 (1999, ["profit_1", "profit_500", "big_profit"]),
                                 (2000, ["profit_1", "profit_500", "big_profit", "profit_2000"])]:
            self.assertEqual(set(earned({"profit": profit})), set(expected))
        # Winning because a computer loses must not count as a profitable buy.
        game_info = {"profit": -50, "purchased": False, "bought": 0, "used": 1, "rounds": 1}
        self.assertEqual(earned(game_info, won=True), ["first_win"])
        game_info.update(profit=100, purchased=True, used=0)
        self.assertTrue({"no_clue_win", "early_bird"}.issubset(earned(game_info)))
        self.assertNotIn("informed_win", earned(game_info))
        game_info.update(bought=2, used=1, rounds=5)
        self.assertTrue({"informed_win", "last_chance"}.issubset(earned(game_info)))
        self.assertNotIn("no_clue_win", earned(game_info))
        self.assertNotIn("early_bird", earned(game_info))

    def test_streak_collection_and_mode_milestones(self):
        profile = progress.new_data()["profile"]
        for stats in profile.values():
            stats.update(played=2, wins=2, best_streak=2)
        earned = rewards.earned_achievements(profile, [], "normal", False, [])
        self.assertNotIn("streak_3", earned)  # Two wins in three modes are not six in a row.
        self.assertNotIn("rage_master", earned)
        profile["rage1"].update(played=5, wins=5, best_streak=5)
        earned = rewards.earned_achievements(profile, [], "rage1", True, [])
        self.assertTrue({"rage1_win", "rage1_5", "streak_3", "streak_5"}.issubset(earned))
        self.assertNotIn("rage2_5", earned)
        items = [name for name, _ in catalogue["Electronics"]]
        earned = rewards.earned_achievements(profile, items, "normal", False, [])
        self.assertTrue({"collect_8", "category_all", "rare_find"}.issubset(earned))
        self.assertNotIn("collect_16", earned)
        earned = rewards.earned_achievements(profile, ["USB cable"] * 32, "normal", False, [])
        self.assertNotIn("collect_8", earned)
        self.assertNotIn("category_all", earned)
        self.assertNotIn("rare_find", earned)

    def test_real_game_records_clue_use_and_sale_round(self):
        lot = [{"name": name, "category": category, "value": value}
               for category, items in catalogue.items() for name, value in items[-2:]]
        def shop(player, *args):
            player.update(cards=[2], cost=80, balance=starting_coins - 80)
        with patch.object(game, "create_warehouse", side_effect=lambda: [dict(item) for item in lot]), \
             patch.object(game, "apply_event", return_value=("NO EVENT", "Test")), \
             patch.object(game, "get_computer_bid", return_value=1000):
            with patch.object(game, "buy_clues", side_effect=shop), \
                 patch.object(game, "get_number", return_value=3), \
                 patch.object(game, "get_bid", return_value=1600), \
                 patch.object(progress, "record_result", wraps=progress.record_result) as record:
                self.assertTrue(game.play_game())
                summary = record.call_args.args[2][0]
                self.assertEqual((summary["bought"], summary["used"], summary["rounds"]), (1, 1, 1))
                self.assertTrue(summary["purchased"])
            data = progress.load_data()
            self.assertTrue({"informed_win", "early_bird"}.issubset(data["achievements"]))
            self.assertNotIn("no_clue_win", data["achievements"])
            with patch.object(game, "buy_clues"), \
                 patch.object(game, "get_bid", side_effect=[1000, 1000, 1000, 1000, 1600]), \
                 patch.object(progress, "record_result", wraps=progress.record_result) as record:
                self.assertTrue(game.play_game())
                summary = record.call_args.args[2][0]
                self.assertEqual((summary["bought"], summary["used"], summary["rounds"]), (0, 0, 5))
            self.assertTrue({"no_clue_win", "last_chance"}.issubset(progress.load_data()["achievements"]))

    def test_six_title_thresholds_and_king_dependencies(self):
        profile = progress.new_data()["profile"]
        def earned(achievements=(), owned=()):
            return rewards.earned_titles(profile, list(achievements), list(owned))
        self.assertEqual(earned(), [])  # No default title or zero-game win rate.
        for stats in profile.values():
            stats.update(played=15, wins=8, best_profit=1500, total_profit=100000)
        self.assertEqual(earned(), ["ROOKIE BIDDER", "SEASONED BIDDER", "MASTER BIDDER", "VALUE HUNTER"])
        self.assertNotIn("LEGENDARY HUNTER", earned())  # Exactly 300000 is insufficient.
        profile["normal"]["total_profit"] += 1
        self.assertIn("LEGENDARY HUNTER", earned())
        all_achievements = [row[0] for row in rewards.achievements]
        self.assertEqual(earned(all_achievements), [row[0] for row in rewards.titles])
        self.assertNotIn("AUCTION KING", earned(all_achievements[:-1]))
        profile["rage2"]["played"] = 14
        self.assertNotIn("SEASONED BIDDER", earned(all_achievements))
        self.assertNotIn("AUCTION KING", earned(all_achievements))
        profile["rage2"]["played"] = 15
        profile["rage1"].update(played=16, wins=8)
        self.assertNotIn("MASTER BIDDER", earned())  # Strictly above 50%.
        profile["rage1"]["played"] = 15
        profile["rage2"]["best_profit"] = 1499
        self.assertNotIn("VALUE HUNTER", earned())
        profile["rage2"]["best_profit"] = None
        self.assertNotIn("VALUE HUNTER", earned())
        profile["rage2"]["best_profit"] = 1500
        profile["normal"]["wins"] = 0
        self.assertNotIn("ROOKIE BIDDER", earned())
        # Lifetime milestones remain obtained if current profile values fall.
        self.assertIn("AUCTION KING", earned(all_achievements, [row[0] for row in rewards.titles[:-1]]))

    def test_title_awards_are_last_saved_and_not_repeated(self):
        data = progress.new_data()
        for stats in data["profile"].values():
            stats.update(played=1, wins=1, best_streak=1)
        progress.save_data(data)
        self.output.seek(0)
        self.output.truncate()
        progress.record_result("rage2", True, [{"profit": 0, "items": []}])
        text = self.output.getvalue()
        self.assertEqual(text.count("NEW TITLE UNLOCKED"), 2)
        self.assertGreater(text.index("NEW TITLE UNLOCKED"), text.index("PLAYER PROGRESS"))
        self.assertIn("MASTER BIDDER", text.split("NEW TITLE UNLOCKED")[-1])
        self.assertEqual(progress.get_player_title(), "MASTER BIDDER")
        self.output.seek(0)
        self.output.truncate()
        for _ in range(2):
            progress.record_result("normal", False, [{"profit": -100, "items": []}])
        self.assertNotIn("NEW TITLE UNLOCKED", self.output.getvalue())
        self.assertIn("MASTER BIDDER", progress.load_data()["titles"])

    def test_individual_achievement_panels_and_split_title_tables(self):
        data = progress.new_data()
        data["achievements"] = ["first_win", "big_profit", "rage_master"]
        self.output.seek(0)
        self.output.truncate()
        progress.show_achievements(data)
        text = self.output.getvalue()
        for number in range(1, 31):
            self.assertEqual(text.count(f"ACHIEVEMENT {number:02d} / 30"), 1)
        self.assertEqual(text.count("REQUIREMENT"), 30)
        self.assertEqual(text.count("NOT OBTAINED"), 27)
        self.assertIn("Earn net profit of at least 1000 coins", text)
        self.output.seek(0)
        self.output.truncate()
        data["titles"] = ["ROOKIE BIDDER", "MASTER BIDDER"]
        progress.show_titles(data)
        text = self.output.getvalue()
        self.assertEqual(text.count("OWNED TITLES"), 1)
        self.assertEqual(text.count("UNOBTAINED TITLES"), 1)
        owned, locked = text.split("UNOBTAINED TITLES")
        self.assertIn("ROOKIE BIDDER", owned)
        self.assertIn("MASTER BIDDER", owned)
        self.assertNotIn("SEASONED BIDDER", owned)
        self.assertIn("SEASONED BIDDER", locked)
        self.assertNotIn("ROOKIE BIDDER", locked)

    def test_title_colors_rainbow_and_clean_log(self):
        class TTYBuffer(StringIO):
            def isatty(self):
                return True
        output = TTYBuffer()
        with redirect_stdout(output):
            ui.game_log = []
            self.assertEqual(len(set(rewards.title_colors.values())), 6)
            for name, _ in rewards.titles:
                styled = ui.format_title(name)
                self.assertIn("\033[", styled)
                ui.show_table("TITLE TEST", ["TITLE", "STATUS"], [(styled, "OBTAINED")], [43, 16])
            # The English Auction King title keeps its special rainbow effect.
            import re
            king = ui.format_title("AUCTION KING")
            self.assertEqual(ui.plain_text(king), "AUCTION KING")
            colors = [re.search(r"(\033\[[0-9;]*m)" + char, king).group(1)
                      for char in "AUCT"]
            self.assertEqual(len(set(colors)), 4)
            self.assertTrue(all("\033" not in line for line in ui.game_log))
            for line in output.getvalue().splitlines():
                if " | " in line or line.startswith("|") or line.startswith("="):
                    self.assertEqual(ui.display_width(line), 62)
        ui.game_log = None

    def test_home_and_difficulty_options_use_uniform_distinct_colors(self):
        import re
        class TTYBuffer(StringIO):
            def isatty(self):
                return True
        output = TTYBuffer()
        style = r"\033\[[0-9;]*m"
        with redirect_stdout(output), patch("builtins.input", return_value="0"):
            self.assertEqual(ui.show_home(), 0)
            lines = output.getvalue().splitlines()
            heading = next(line for line in lines if "WELCOME TO HIDDEN VALUE" in line)
            self.assertEqual(re.findall(style, heading), [ui.home_title_color, "\033[0m"])
            self.assertEqual(len(set(ui.menu_colors.values())), 9)
            self.assertNotIn(ui.home_title_color, ui.menu_colors.values())
            for number in range(9):
                row = next(line for line in lines if ui.plain_text(line).strip().startswith(f"[{number}]"))
                self.assertEqual(re.findall(style, row), [ui.menu_colors[number], "\033[0m"])
            output.seek(0)
            output.truncate()
            self.assertEqual(game.choose_rage_difficulty(), 0)
            lines = output.getvalue().splitlines()
            self.assertNotEqual(ui.difficulty_colors[1], ui.difficulty_colors[2])
            for number in [1, 2]:
                row = next(line for line in lines if f"DIFFICULTY {number} -" in line)
                self.assertEqual(re.findall(style, row), [ui.difficulty_colors[number], "\033[0m"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
