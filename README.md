# Hidden Value

Ever wondered whether a dusty warehouse hides worthless clutter or a fortune?

Welcome to **Hidden Value**, where every clue could turn a risky bid into a winning deal! Designed for students and casual players who enjoy strategy and surprises, this terminal auction game challenges you to value eight hidden items and compete against computer bidders. Buy information, react to public events, and decide when to bid or wait. Play at your own pace in Normal Mode, or face the 25-second countdown in Rage Mode. Discover items, unlock achievements, and chase the title of Auction King.

**REVEAL THE HIDDEN VALUE, THEN BID WITHOUT HESITATION 😋**

Built as an individual final project for **COMP9001, University of Sydney**. The program applies **file I/O, multidimensional lists and testing**, alongside functions, dictionaries, loops and exception handling.

## Main rules and game modes

Each bidder starts with **6000 coins**. A warehouse contains **eight hidden items**: two different items from each of Electronics, Tools, Decorations and Collectibles, randomly selected from a public catalogue of 32.

| Mode | Computer rivals | Time per bidding round | Public events |
| --- | --- | --- | --- |
| Normal | A and B | No limit | 70% no event; 30% one fixed event per game |
| Rage Difficulty 1 | A, B and C | 25 seconds | One guaranteed event, fixed for that game |
| Rage Difficulty 2 | A, B and C | 25 seconds | A guaranteed event is drawn each round |

- An auction lasts up to **five sealed-bid rounds**. The highest bid must exceed the second-highest by **more than 50%, 40%, 30%, 20% and 0%**, respectively. A highest-bid tie means no sale. Any successful sale ends that game.
- Only the buyer pays a bid, then automatically resells the warehouse at its current value. Losing bids cost nothing.
- If you buy, **net profit = resale value - purchase price - clue costs + unused-card refunds**. Breaking even does not count as a profitable purchase.
- **Normal and Rage 1:** win by buying at positive net profit, or by remaining an active bidder when a computer buys at a loss. A computer-loss win can still leave you with clue expenses.
- **Rage 2:** only your own positive-profit purchase wins.
- **Bid 1 means pass this round.** If you pass or time out in the sale round, a computer purchase is your loss even if that computer loses money. An earlier pass does not stop you bidding again.
- Rage uses **best of three**: the first side to two game wins takes the match. Every game you do not win gives the computers one point. Funds, items and cards reset between games.

## How to start

Use **Python 3**; the project has been tested with Python **3.12.14**. No extra packages are required.

Keep all seven runtime Python files in one folder. Open a terminal in that folder and run:

```bash
python main.py
```

On systems that use the `python3` command:

```bash
python3 main.py
```

Use an interactive terminal at least **62 columns wide** for the coloured tables and live countdown. Rage Mode requires interactive terminal input. Redirected output is plain text.

## How to play

1. **Choose a mode.** Enter `1` for Normal or `2` for Rage. For Rage, then choose Difficulty `1` or `2`; `0` returns home.
2. **Read the event.** It is announced before shopping. Home option `5` shows mode rules and the public catalogue with base prices.
3. **Buy your clues.** Enter a card ID to buy it. Buy up to **three different cards**, or enter `0` to start bidding. Shopping ends automatically after three purchases. Costs are deducted immediately.
4. **Use or save a card.** Select one available card, or `0` to skip. Each card can be used once, with at most one card per round. Its name, description and revealed information share one colour. Earlier valid information stays visible.
5. **Enter your bid.** Use a whole number from `2` to your balance, or `1` to pass. In Rage, one **25-second timer covers card selection and bidding together**. Invalid input does not restart it; timeout records a bid of `0`. With no cards, the full time is for bidding.
6. **Check the bids.** All bids are revealed together. The comparison shows whether the lead was met. If there is no sale, continue to the next round. Unsold after Round 5 means no win.
7. **See the settlement.** All items are revealed, followed by adjusted warehouse value, buyer, your net profit and balance, and computer profits. Unused cards refund **50% of the actual price paid**, rounded down. New achievements and discoveries are recorded; new titles are announced last.
8. **Continue or return home.** Enter `1` to play again or `0` to return home. A Rage match continues automatically until one side has two wins. Its progress is saved when the entire match finishes.

Press **Ctrl-C** at any time to stop. An unfinished game or match does not add a completed result to your profile.

### Clue cards

| ID | Card | Price | Information revealed |
| --- | --- | --- | --- |
| 1 | Random Estimate | 50 | Anonymous random item: 80%-120% of its value, rounded down |
| 2 | Category Scan | 80 | Count items worth at least 300 in a chosen category |
| 3 | Random Appraisal | 80 | Random item's number and exact value |
| 4 | Rare Item Count | 220 | Count items currently worth at least 1000 |
| 5 | Second-Highest Scan | 220 | Second-highest item value, without its identity |
| 6 | Category Value Range | 120 | Chosen category's total in a 500-coin band |
| 7 | Mid-Value Count | 60 | Count items currently worth 300-999 |
| 8 | Low-Value Total Range | 40 | Combined value of items below 300, in a 100-coin band |

In Normal, choose categories when using cards 2 and 6. In Rage, set them during shopping, before the timer; those choices stay fixed for that game. An opening **Damaged Stock** event gives **20% off all clue cards**.

### Public events

- **Category Boom:** a named category gains 25% value.
- **Damaged Stock:** damaged items become worth zero. The announcement reveals their count but hides their category.
- **Rare Market:** items with base prices of at least 1000 rise or fall by 20%.
- **Common Market:** items with base prices below 1000 rise or fall by 20%.

The four types are equally likely when an event is drawn. Clues and resale use adjusted values, rounded down. In Rage 2, events start from base prices each round, so effects do not stack; previous-round clues expire and are cleared.

### Explore between games

| Home option | What it shows |
| --- | --- |
| 3 - View Game History | Recent transcripts, newest first; separate Rage difficulty views and history clearing |
| 4 - Player Profile | Per-mode results, cumulative and recent win rates, profit and streaks |
| 5 - Game Rules | Mode rules, computer bidding behaviour and the public price table |
| 6 - Achievements | 30 achievements, each with its own requirement and status table |
| 7 - Item Collection | Discovery progress for all 32 catalogue items |
| 8 - Titles | Separate tables for obtained and unobtained titles |
| 0 - Exit | Ends the program |

Profile, achievement, collection and title pages use `1` to view, `2` to clear that section and `0` to return home. Clearing one section leaves the others intact. Revealed items count towards collection regardless of the buyer. Six cosmetic titles range from **Rookie Bidder** to **Auction King**; full conditions appear in the title menu. The highest obtained title appears on the home screen. Titles give no bidding bonuses.

## How it works

1. **Warehouse and events** (`game.py`): `random.sample` selects two distinct items per category. Events adjust each item's stored base price.
2. **Computer decisions** (`game.py`): a hand-written decision tree uses `if` / `elif` branches for risk, probing, following or ordinary bids. A is cautious, B is aggressive and C is more variable. Appraisals are noisy versions of the actual warehouse total, so computers can overpay. Normal and Rage 1 can react to prior public bids; Rage 2 ignores them as events change. Quotes are set before your current input and stay within computer balances.
3. **Auction and settlement** (`game.py`): bid rows form a two-dimensional list. Integer comparisons enforce the strict lead rule. Settlement credits resale income and refunds once, then applies the mode's win condition.
4. **Progress** (`records.py`, `progress.py`, `rewards.py`): text files preserve transcripts, JSON stores player progress, and completed results are checked against reward conditions.

### Advanced topics

| Topic | Use in this project |
| --- | --- |
| **File I/O** | UTF-8 text histories and JSON progress persist across sessions. Progress is written to a temporary file before replacing the previous save. |
| **Multidimensional lists** | `bid_history[round][bidder]` stores bids for computer responses, sale checks and settlement. |
| **Testing** | `unittest` and mocks check boundaries and complete game flows. Temporary directories protect real saves during tests. |

Other Python techniques include **functions and modules** to separate responsibilities; **lists, tuples and dictionaries** for items, cards and players; **loops and conditional branches** for menus and rounds; **sorting** for sale checks and value clues; **exception handling** for invalid numbers and file errors; **string formatting** for tables; and **`time.monotonic()`** for the shared deadline. ANSI escape codes provide terminal colours and the countdown.

## Files

| File | Contents |
| --- | --- |
| `main.py` | Starts the program, routes the home menu and handles replay |
| `game.py` | Warehouse generation, events, cards, computer decisions, auctions and settlement |
| `interface.py` | Input validation, countdown, colours, tables, home page and rules |
| `settings.py` | Game parameters, eight clue cards and public item catalogue |
| `records.py` | Reads, saves, displays and clears recent transcripts |
| `progress.py` | Saves and displays profiles, achievements, collection and titles |
| `rewards.py` | Conditions for 30 achievements and six titles, plus title colours |
| `test_progress.py` | Optional standard-library test script |
| `README_zh.md` | Chinese version of this README |

## Saved data

These files are created automatically in the **working folder**:

| File | Contents |
| --- | --- |
| `normal_history.txt` | Latest 15 completed Normal games |
| `rage_history.txt` | Latest 15 completed matches for EACH Rage difficulty |
| `player_data.json` | Cumulative profile statistics, recent rates, achievements, collection and titles |

The profile counts Normal games and complete Rage matches separately. Recent rates use up to 15 results per mode since the last profile reset; cumulative statistics have no 15-result cap. Rage profit totals include the games within completed matches. On first use, available completed history is imported; deleted older records cannot be recovered.

Clearing history does not clear progress. Clearing a profile does not import old histories again. Retained milestones can unlock cleared rewards after a later result. Older saves keep profile, achievement and collection data; legacy titles are checked under updated rules after their one-time migration. Titles are checked after completed results and remain obtained if a qualifying win rate later falls.

No downloaded datasets, trained models or online services are needed. Catalogue values and reward definitions are included in the Python files.

## Testing

From the project folder, run:

```bash
python test_progress.py
```

The **16 test groups** cover sale thresholds and ties, refunds, pass rules, Normal and Rage outcomes, history limits, independent resets, save compatibility, achievement and title conditions, menu routes and colour formatting. Tests use temporary folders and leave personal saves unchanged.
