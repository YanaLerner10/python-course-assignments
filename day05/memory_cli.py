# memory_cli.py
"""
Command-line interface for the Memory Game.

Usage:
    python memory_cli.py

How to play:
- The game shows a numeric sequence (numbers 0-9) for a short moment.
- Memorize it and then type the sequence (numbers separated by spaces).
- If correct, the sequence grows by one number and next round starts.
- If incorrect, the game ends and your score is shown.
"""

import time
import os
from memory_logic import MemoryGame, MemoryError
from typing import List

DISPLAY_SECONDS = 1.2  # seconds to show sequence each round
PAUSE_SECONDS = 0.5    # short pause before clearing screen


def clear_screen():
    """Clear terminal screen (works on Windows, macOS, Linux)."""
    os.system("cls" if os.name == "nt" else "clear")


def parse_input_to_list(s: str) -> List[int]:
    """Parse user input like '1 4 0' or '140' into list of ints."""
    s = s.strip()
    if not s:
        return []
    # accept either space-separated or contiguous digits
    if " " in s:
        parts = s.split()
        return [int(p) for p in parts]
    else:
        # each char should be a digit
        return [int(ch) for ch in s]


def play():
    print("Memory Game — repeat the sequence of digits.")
    print("At each round a new digit (0-9) is appended. Type the sequence when prompted.")
    print("Press Enter to start.")
    input()

    game = MemoryGame()
    round_time = 0

    try:
        while True:
            seq = game.next_round()
            print(f"Round {game.round}: Watch the sequence...")
            # show sequence
            print(" ", " ".join(str(x) for x in seq))
            time.sleep(DISPLAY_SECONDS)
            time.sleep(PAUSE_SECONDS)
            clear_screen()
            # prompt user
            user_raw = input("Type the sequence (digits separated by spaces or contiguous), then press Enter:\n> ")
            try:
                response = parse_input_to_list(user_raw)
            except ValueError:
                print("Invalid input: please enter digits 0-9 separated by spaces or continuous.")
                # treat as incorrect
                correct, score = False, max(0, game.round - 1)
                print(f"Wrong! Your score: {score}")
                break

            correct, score = game.check_response(response)
            if correct:
                print(f"Correct! Score: {score}")
                time.sleep(0.6)
                clear_screen()
                continue
            else:
                print("Incorrect!")
                print(f"The correct sequence was: {' '.join(str(x) for x in seq)}")
                print(f"Your final score: {score}")
                break

    except MemoryError:
        print("Game over. Reset to play again.")

    print("Thanks for playing!")


if __name__ == "__main__":
    play()
