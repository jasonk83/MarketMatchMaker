"""
test_leaderboard.py — Tests for SQLite persistence and session recovery
"""

import unittest
import os
import leaderboard


TEST_DB = "/tmp/test_marketplace_matchmaker.db"


class TestLeaderboard(unittest.TestCase):
    def setUp(self):
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)
        leaderboard.init_db(TEST_DB)

    def tearDown(self):
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)

    def test_registration_and_recovery(self):
        # Register new student
        player, is_new = leaderboard.register_or_get_player("Jordan", "BarkAvenue", db_path=TEST_DB)
        self.assertTrue(is_new)
        self.assertEqual(player["first_name"], "Jordan")
        self.assertEqual(player["company_name"], "BarkAvenue")
        self.assertEqual(player["status"], "In Round 1")

        # Re-registering with different casing returns existing player
        player_recovered, is_new_2 = leaderboard.register_or_get_player("jordan", "OtherName", db_path=TEST_DB)
        self.assertFalse(is_new_2)
        self.assertEqual(player_recovered["company_name"], "BarkAvenue")

    def test_round_progression(self):
        leaderboard.register_or_get_player("Alex", "PupPals", db_path=TEST_DB)
        leaderboard.save_round_1_results(
            first_name="Alex",
            r1_buyer=1_200_000,
            r1_supplier=750_000,
            r1_trust=450_000,
            r1_take=0.10,
            owners=15000,
            walkers=1850,
            balance=0.99,
            state="BALANCED",
            liquidity=88.5,
            net_rev=650000,
            cash_end=3250000,
            db_path=TEST_DB,
        )

        player = leaderboard.get_player("alex", db_path=TEST_DB)
        self.assertEqual(player["status"], "In Round 2")
        self.assertEqual(player["r1_cash_end"], 3250000)

        # Complete Round 2
        leaderboard.save_round_2_and_complete(
            first_name="Alex",
            r2_buyer=1_100_000,
            r2_supplier=800_000,
            r2_trust=500_000,
            r2_take=0.15,
            r2_liquidity=85.0,
            r2_retention=91.0,
            r2_net_rev=1100000,
            r2_leakage_gmv=45000,
            r2_cash_rem=1950000,
            liquidity_score=86.4,
            retention_score=91.0,
            valuation_m=35.5,
            valuation_score=71.0,
            composite_score=82.8,
            db_path=TEST_DB,
        )

        completed_player = leaderboard.get_player("alex", db_path=TEST_DB)
        self.assertEqual(completed_player["status"], "Completed")
        self.assertEqual(completed_player["composite_score"], 82.8)

        # Test leaderboard dataframe format
        df = leaderboard.get_leaderboard_dataframe(db_path=TEST_DB)
        self.assertEqual(len(df), 1)
        self.assertIn("Rank", df.columns)
        self.assertEqual(df.iloc[0]["Status"], "✅ Completed")

        # Test analytics
        analytics = leaderboard.get_class_analytics(db_path=TEST_DB)
        self.assertEqual(analytics["total_founders"], 1)
        self.assertEqual(analytics["completed_count"], 1)
        self.assertEqual(analytics["avg_composite"], 82.8)


if __name__ == "__main__":
    unittest.main()
