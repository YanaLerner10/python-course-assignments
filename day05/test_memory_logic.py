# test_memory_logic.py
import unittest
from memory_logic import MemoryGame, MemoryError

class TestMemoryGame(unittest.TestCase):
    def test_sequence_growth_and_determinism(self):
        g1 = MemoryGame(seed=123)
        seq1 = g1.next_round()
        self.assertEqual(len(seq1), 1)
        seq2 = g1.next_round()
        self.assertEqual(len(seq2), 2)

        # determinism: same seed produces same sequence
        g2 = MemoryGame(seed=123)
        self.assertEqual(g2.next_round(), seq1)
        self.assertEqual(g2.next_round(), seq2)

    def test_check_response_correct(self):
        g = MemoryGame(seed=1)
        seq = g.next_round()
        ok, score = g.check_response(seq.copy())
        self.assertTrue(ok)
        self.assertEqual(score, 1)
        # next round and correct again
        seq2 = g.next_round()
        ok2, score2 = g.check_response(seq2.copy())
        self.assertTrue(ok2)
        self.assertEqual(score2, 2)

    def test_check_response_incorrect_marks_over(self):
        g = MemoryGame(seed=2)
        seq = g.next_round()
        # create wrong response by altering first digit
        wrong = seq.copy()
        wrong[0] = (wrong[0] + 1) % 10
        ok, score = g.check_response(wrong)
        self.assertFalse(ok)
        # score should be 0 since failed on first round
        self.assertEqual(score, 0)
        self.assertTrue(g.over)
        with self.assertRaises(MemoryError):
            g.next_round()  # cannot continue when game over

    def test_input_validation(self):
        g = MemoryGame(seed=3)
        g.next_round()
        with self.assertRaises(TypeError):
            g.check_response("not a list")  # must be list of ints

if __name__ == "__main__":
    unittest.main()
