
import unittest
from main import numeric, normalize


class TestNFLModel(unittest.TestCase):

    def test_valid_number(self):
        self.assertEqual(
            numeric({"price": "0.45"}, "price"),
            0.45
        )

    def test_invalid_number(self):
        self.assertIsNone(
            numeric({"price": "invalid"}, "price")
        )

    def test_missing_number(self):
        self.assertIsNone(
            numeric({}, "price")
        )

    def test_valid_market_quote(self):
        market = {
            "ticker": "TEST-NFL",
            "title": "Test NFL market",
            "yes_bid_dollars": "0.43",
            "yes_ask_dollars": "0.44",
            "volume_fp": "100"
        }

        result = normalize(market, "KXNFLGAME")

        self.assertEqual(result["ticker"], "TEST-NFL")
        self.assertTrue(result["usable_quote"])

    def test_missing_market_quote(self):
        market = {
            "ticker": "TEST-NFL",
            "volume_fp": "100"
        }

        result = normalize(market, "KXNFLGAME")

        self.assertFalse(result["usable_quote"])


if __name__ == "__main__":
    unittest.main()
