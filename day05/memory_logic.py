# memory_logic.py
"""
Memory game logic.

Game behaviour:
- Each round the game appends one random digit (0-9) to the current sequence.
- Player must repeat the full sequence in order.
- If correct, next round begins (sequence grows by 1).
- If incorrect, game ends; score = number of rounds completed.

This module contains no I/O and is fully testable.
"""

from __future__ import annotations
import random
from typing import List, Optional, Tuple


class MemoryError(Exception):
    pass


class MemoryGame:
    def __init__(self, seed: Optional[int] = None):
        """
        Create a new game. If seed is provided, sequence generation is deterministic.
        """
        self.seed = seed
        self._rng = random.Random(seed)
        self.reset()

    def reset(self, seed: Optional[int] = None) -> None:
        """Reset the game. Optionally provide a new seed."""
        if seed is not None:
            self.seed = seed
            self._rng = random.Random(seed)
        else:
            self._rng = random.Random(self.seed)
        self.sequence: List[int] = []
        self.round: int = 0
        self.over: bool = False

    def next_round(self) -> List[int]:
        """
        Advance the game by one round: append a new random digit (0-9),
        increment round counter, and return the new full sequence.
        """
        if self.over:
            raise MemoryError("Game is over. Please reset to start a new game.")
        new_digit = self._rng.randint(0, 9)
        self.sequence.append(new_digit)
        self.round += 1
        return self.sequence.copy()

    def get_sequence(self) -> List[int]:
        """Return the current sequence (copy)."""
        return self.sequence.copy()

    def check_response(self, response: List[int]) -> Tuple[bool, int]:
        """
        Check player's response against the current sequence.

        Returns:
            (is_correct: bool, score: int)
        Where score is the number of rounds successfully completed (i.e., self.round if correct).
        If incorrect, game becomes over and score is number of completed rounds - 1 (if failed this round).
        """
        if self.over:
            raise MemoryError("Game is over. Please reset to start a new game.")
        if not isinstance(response, list) or not all(isinstance(x, int) for x in response):
            raise TypeError("response must be a list of integers")

        # correct if lists are identical
        if response == self.sequence:
            # correct this round
            return True, self.round
        else:
            # wrong: mark game over
            self.over = True
            # score = rounds completed before failing (round - 1 if you failed this round after next_round was called)
            # but we consider round as round number attempted; as you failed current round, score is round - 1
            score = max(0, self.round - 1)
            return False, score
