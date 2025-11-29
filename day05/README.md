# Memory Game (Python)

A simple command-line Memory Game implemented in pure Python with no external libraries.
Each round the game adds a random digit (0–9) to a sequence.
Your task is to memorize and repeat the full sequence.
If you repeat it correctly, the sequence grows by one.
If you make a mistake, the game ends.

The project is split into logic, CLI interface, and tests.

## Files
memory_logic.py       # Core game logic (no I/O)
memory_cli.py         # Command-line interface
test_memory_logic.py  # Unit tests using unittest

## How to Run
Play the game:
python memory_cli.py

### Run tests:
python -m unittest test_memory_logic.py

## Game Flow

The game shows you a sequence of digits for a short moment.

After the screen clears, type the sequence back (spaces optional).

Each correct answer increases the sequence length.

A wrong answer ends the game and shows your final score.


Deterministic mode using random seed

Simple and clean architecture
