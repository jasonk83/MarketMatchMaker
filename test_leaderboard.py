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
        self.assertEqual(player["status"], "Round 1 Report")
        self.assertEqual(player["r1_cash_end"], 3250000)

        leaderboard.proceed_to_round_2("Alex", db_path=TEST_DB)
        player = leaderboard.get_player("alex", db_path=TEST_DB)
        self.assertEqual(player["status"], "In Round 2")

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

    def test_condensed_leaderboard_and_settings(self):
        leaderboard.register_or_get_player("Sam", "FetchClub", db_path=TEST_DB)
        leaderboard.save_round_1_results(
            first_name="Sam",
            r1_buyer=1_000_000,
            r1_supplier=800_000,
            r1_trust=400_000,
            r1_take=0.15,
            owners=10000,
            walkers=1250,
            balance=1.0,
            state="BALANCED",
            liquidity=85.0,
            net_rev=500000,
            cash_end=3300000,
            db_path=TEST_DB,
        )

        # Condensed leaderboard (default)
        df_condensed = leaderboard.get_leaderboard_dataframe(db_path=TEST_DB, full_details=False)
        self.assertEqual(list(df_condensed.columns), ["Rank", "Founder", "Composite Score", "Valuation ($M)"])

        # Full leaderboard
        df_full = leaderboard.get_leaderboard_dataframe(db_path=TEST_DB, full_details=True)
        self.assertIn("Marketplace Company", df_full.columns)
        self.assertIn("Status", df_full.columns)
        self.assertIn("Liquidity %", df_full.columns)

    def test_pin_registration_and_lookup(self):
        # Register two founders with same base name but distinct PINs using underscore separator
        p1, is_new1 = leaderboard.register_or_get_player("Jordan_1234", "BarkAvenue", pin="1234", db_path=TEST_DB)
        self.assertTrue(is_new1)
        self.assertEqual(p1["student_pin"], "1234")

        p2, is_new2 = leaderboard.register_or_get_player("Jordan_5678", "PupSpot", pin="5678", db_path=TEST_DB)
        self.assertTrue(is_new2)
        self.assertEqual(p2["student_pin"], "5678")

        # Verify lookup by PIN
        found1 = leaderboard.get_player_by_pin("1234", db_path=TEST_DB)
        self.assertIsNotNone(found1)
        self.assertEqual(found1["company_name"], "BarkAvenue")

        found2 = leaderboard.get_player_by_pin("5678", db_path=TEST_DB)
        self.assertIsNotNone(found2)
        self.assertEqual(found2["company_name"], "PupSpot")

    def test_wal_mode_enabled(self):
        conn = leaderboard.get_db_connection(TEST_DB)
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode;")
        mode = cur.fetchone()[0]
        conn.close()
        self.assertEqual(mode.lower(), "wal")

    def test_generate_unique_pin(self):
        # Generate initial PIN
        pin1 = leaderboard.generate_unique_pin(db_path=TEST_DB)
        self.assertTrue(pin1.isdigit())
        self.assertEqual(len(pin1), 4)

        # Register player with that PIN
        leaderboard.register_or_get_player("Jordan_" + pin1, "BarkCo", pin=pin1, db_path=TEST_DB)

        # Next PIN must NOT equal pin1
        pin2 = leaderboard.generate_unique_pin(db_path=TEST_DB)
        self.assertNotEqual(pin1, pin2)

    def test_get_student_export_dataframe(self):
        leaderboard.register_or_get_player("Jordan_1111", "BarkCo", pin="1111", db_path=TEST_DB)
        leaderboard.save_round_1_results(
            first_name="Jordan_1111",
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
            r1_owners_per_walker=11,
        )
        leaderboard.proceed_to_round_2("Jordan_1111", db_path=TEST_DB)
        leaderboard.save_round_2_and_complete(
            first_name="Jordan_1111",
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
            r2_owners_per_walker=7,
        )

        player = leaderboard.get_player("Jordan_1111", db_path=TEST_DB)
        self.assertEqual(player["r1_owners_per_walker"], 11)
        self.assertEqual(player["r2_owners_per_walker"], 7)

        df = leaderboard.get_student_export_dataframe(db_path=TEST_DB)
        self.assertFalse(df.empty)
        self.assertEqual(len(df), 1)
        self.assertIn("Founder", df.columns)
        self.assertIn("Student PIN", df.columns)
        self.assertIn("R1 Walker Efficiency (Owners/Walker)", df.columns)
        self.assertIn("R2 Walker Efficiency (Owners/Walker)", df.columns)
        self.assertEqual(df.iloc[0]["R1 Walker Efficiency (Owners/Walker)"], 11)
        self.assertEqual(df.iloc[0]["R2 Walker Efficiency (Owners/Walker)"], 7)

    def test_delete_and_reset(self):
        leaderboard.register_or_get_player("Jordan_2222", "BarkCo", pin="2222", db_path=TEST_DB)
        leaderboard.register_or_get_player("Alex_3333", "PupPals", pin="3333", db_path=TEST_DB)
        self.assertEqual(len(leaderboard.get_leaderboard_dataframe(db_path=TEST_DB)), 2)

        # Delete by PIN
        deleted = leaderboard.delete_player("2222", db_path=TEST_DB)
        self.assertTrue(deleted)
        self.assertEqual(len(leaderboard.get_leaderboard_dataframe(db_path=TEST_DB)), 1)

        # Reset leaderboard
        leaderboard.set_app_setting("classroom_app_url", "http://test:8501", db_path=TEST_DB)
        leaderboard.reset_leaderboard(db_path=TEST_DB)
        self.assertEqual(len(leaderboard.get_leaderboard_dataframe(db_path=TEST_DB)), 0)
        # Settings preserved
        self.assertEqual(leaderboard.get_app_setting("classroom_app_url", db_path=TEST_DB), "http://test:8501")


if __name__ == "__main__":
    unittest.main()


