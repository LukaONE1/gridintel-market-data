
import unittest

from nfl_model import win_probability


class TestNFLModel(unittest.TestCase):

    def test_equal_ratings_neutral_field(self):
        result = win_probability(1500, 1500, home_advantage=0)
        self.assertEqual(result["home_win_probability"], 0.5)
        self.assertEqual(result["away_win_probability"], 0.5)

    def test_home_advantage(self):
        result = win_probability(1500, 1500)
        self.assertGreater(result["home_win_probability"], 0.5)

    def test_probabilities_sum_to_one(self):
        result = win_probability(1600, 1450)
        total = (
            result["home_win_probability"]
            + result["away_win_probability"]
        )
        self.assertAlmostEqual(total, 1.0)

    def test_invalid_scale(self):
        with self.assertRaises(ValueError):
            win_probability(1500, 1500, scale=0)

    def test_not_validated(self):
        result = win_probability(1500, 1500)
        self.assertFalse(result["validated"])


if __name__ == "__main__":
    unittest.main()
