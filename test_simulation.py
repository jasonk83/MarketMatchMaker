"""
test_simulation.py — Automated verification of economic invariants for "The Marketplace Matchmaker"
"""

import unittest
from simulation import (
    simulate_round_1,
    simulate_round_2,
    compute_final_scores,
    get_optimal_benchmark,
    parse_spend_input,
)


class TestMarketplaceSimulation(unittest.TestCase):
    def test_cash_hoarding_invariant(self):
        """
        Verify that hoarding all $5M cash and spending $0 in R1 & R2 results in:
        - $5.0M Enterprise Valuation (pure cash)
        - 0% Liquidity
        - 0% Retention
        - Valuation Score = 10.0 (5M / 50M * 100)
        - Composite Score ~ 3.3/100
        """
        r1 = simulate_round_1(buyer_spend=0.0, supplier_spend=0.0, trust_spend=0.0, take_rate=0.15)
        self.assertEqual(r1.owners_acquired, 0)
        self.assertEqual(r1.walkers_acquired, 0)
        self.assertEqual(r1.matched_walks, 0)
        self.assertEqual(r1.cash_end, 5_000_000.0)

        r2 = simulate_round_2(r1, buyer_spend=0.0, supplier_spend=0.0, trust_spend=0.0, take_rate=0.15)
        self.assertEqual(r2.active_owners, 0)
        self.assertEqual(r2.completed_walks, 0)
        self.assertEqual(r2.cash_remaining, 5_000_000.0)

        scorecard = compute_final_scores(r1, r2)
        self.assertEqual(scorecard.liquidity_score, 0.0)
        self.assertEqual(scorecard.retention_score, 0.0)
        self.assertEqual(scorecard.enterprise_valuation, 5.0)
        self.assertEqual(scorecard.valuation_score, 10.0)  # 5 / 50 * 100
        self.assertAlmostEqual(scorecard.composite_score, 3.3, places=1)

    def test_demand_overload(self):
        """
        Lopsided buyer spend ($2.5M) and negligible supplier spend ($50k)
        triggers DEMAND_OVERLOAD with wait times > 60m and high owner churn.
        """
        r1 = simulate_round_1(buyer_spend=2_500_000.0, supplier_spend=50_000.0, trust_spend=200_000.0, take_rate=0.15)
        self.assertEqual(r1.state_classification, "DEMAND_OVERLOAD")
        self.assertGreater(r1.avg_wait_time_minutes, 60)
        self.assertGreater(r1.owner_churn_rate, 0.40)
        self.assertLess(r1.balance_ratio, 0.88)

    def test_supply_starvation(self):
        """
        Lopsided supplier spend ($2.0M) and negligible buyer spend ($50k)
        triggers SUPPLY_STARVATION with high walker churn due to lack of bookings.
        """
        r1 = simulate_round_1(buyer_spend=50_000.0, supplier_spend=2_000_000.0, trust_spend=200_000.0, take_rate=0.15)
        self.assertEqual(r1.state_classification, "SUPPLY_STARVATION")
        self.assertGreater(r1.walker_churn_rate, 0.40)
        self.assertGreater(r1.balance_ratio, 1.15)

    def test_trust_gate_threshold(self):
        """
        Underfunding trust (< $150k) triggers safety incidents and conversion penalties.
        """
        r1_low_trust = simulate_round_1(buyer_spend=1_000_000.0, supplier_spend=600_000.0, trust_spend=50_000.0, take_rate=0.15)
        self.assertFalse(r1_low_trust.trust_gate_passed)
        self.assertGreater(r1_low_trust.safety_incident_rate, 0.01)

        r1_high_trust = simulate_round_1(buyer_spend=1_000_000.0, supplier_spend=600_000.0, trust_spend=350_000.0, take_rate=0.15)
        self.assertTrue(r1_high_trust.trust_gate_passed)
        self.assertLessEqual(r1_high_trust.safety_incident_rate, 0.005)

    def test_r2_high_take_rate_penalties(self):
        """
        In Round 2, a 25% take rate with low trust spend causes heavy defection to BarkBuddy (>=40%)
        and high Venmo disintermediation (>=30%).
        """
        r1 = simulate_round_1(buyer_spend=1_200_000.0, supplier_spend=700_000.0, trust_spend=300_000.0, take_rate=0.10)
        r2_greedy = simulate_round_2(
            r1=r1,
            buyer_spend=800_000.0,
            supplier_spend=300_000.0,
            trust_spend=50_000.0,  # Negligible trust moat
            take_rate=0.25,        # 25% take rate
        )
        self.assertGreaterEqual(r2_greedy.walker_defection_rate, 0.40)
        self.assertGreaterEqual(r2_greedy.venmo_leakage_rate, 0.30)
        self.assertGreater(r2_greedy.walks_lost_to_venmo, 1000)

    def test_optimal_benchmark_score(self):
        """
        The optimal benchmark strategy should achieve a high composite score (>=85.0).
        """
        benchmark = get_optimal_benchmark()
        scorecard = benchmark["scorecard"]
        self.assertGreaterEqual(scorecard.composite_score, 85.0)
        self.assertGreaterEqual(scorecard.liquidity_score, 80.0)
        self.assertGreaterEqual(scorecard.retention_score, 80.0)
        self.assertGreaterEqual(scorecard.valuation_score, 80.0)


    def test_r2_phantom_money_exploit_prevented(self):
        """
        Verify that if available_cash <= 0, Round 2 zeroes out all spend
        and prevents acquiring users with non-existent money.
        """
        # Create an R1 with 0 cash remaining and zero cohort
        r1_broke = simulate_round_1(buyer_spend=0.0, supplier_spend=0.0, trust_spend=0.0, take_rate=0.05)
        r1_broke.cash_end = 0.0

        r2_attempt = simulate_round_2(
            r1=r1_broke,
            buyer_spend=1_000_000.0,
            supplier_spend=1_000_000.0,
            trust_spend=500_000.0,
            take_rate=0.15,
        )
        self.assertEqual(r2_attempt.total_spend, 0.0)
        self.assertEqual(r2_attempt.buyer_spend, 0.0)
        self.assertEqual(r2_attempt.supplier_spend, 0.0)
        self.assertEqual(r2_attempt.trust_spend, 0.0)
        self.assertEqual(r2_attempt.new_owners_acquired, 0)
        self.assertEqual(r2_attempt.new_walkers_acquired, 0)
        self.assertEqual(r2_attempt.cash_remaining, 0.0)

    def test_r2_supply_demand_imbalance_churn(self):
        """
        Verify Round 2 imbalance churn:
        - balance_ratio < 0.88 causes unfulfilled demand owner churn.
        - balance_ratio > 1.15 causes idle walker churn.
        """
        r1 = simulate_round_1(buyer_spend=1_200_000.0, supplier_spend=750_000.0, trust_spend=450_000.0, take_rate=0.10, owners_per_walker=8)

        # R2 Demand Overload
        r2_overload = simulate_round_2(
            r1=r1,
            buyer_spend=2_000_000.0,
            supplier_spend=50_000.0,
            trust_spend=100_000.0,
            take_rate=0.15,
            owners_per_walker=8,
        )
        self.assertEqual(r2_overload.state_classification, "DEMAND_OVERLOAD")
        self.assertLess(r2_overload.balance_ratio, 0.88)
        self.assertIn("Round 2 Demand Overload", r2_overload.feedback if hasattr(r2_overload, "feedback") else "")
        # Unfulfilled owners churned
        potential_owners = int(r1.surviving_owners * 0.95) + r2_overload.new_owners_acquired
        self.assertLess(r2_overload.active_owners, potential_owners)

        # R2 Supply Starvation
        r2_starvation = simulate_round_2(
            r1=r1,
            buyer_spend=50_000.0,
            supplier_spend=2_000_000.0,
            trust_spend=100_000.0,
            take_rate=0.15,
            owners_per_walker=8,
        )
        self.assertEqual(r2_starvation.state_classification, "SUPPLY_STARVATION")
        self.assertGreater(r2_starvation.balance_ratio, 1.15)
        # Idle walkers churned
        cac_walker = 380.0 * (1.0 + 0.55 * (2_000_000.0 / 800_000.0) ** 1.2)
        new_w = int(((2_000_000.0 * 0.65) / cac_walker) * 1.0)
        total_pre_w = r1.surviving_walkers + new_w
        defection_w = r2_starvation.walkers_lost_to_rival
        pot_w = total_pre_w - defection_w
        self.assertLess(r2_starvation.active_walkers, pot_w)

    def test_inactive_zero_spend_classification(self):
        """
        Verify that spending $0 classifies state as INACTIVE rather than BALANCED.
        """
        r1 = simulate_round_1(buyer_spend=0.0, supplier_spend=0.0, trust_spend=0.0, take_rate=0.15)
        self.assertEqual(r1.state_classification, "INACTIVE")
        self.assertIn("Inactive", r1.feedback)

        r2 = simulate_round_2(r1, buyer_spend=0.0, supplier_spend=0.0, trust_spend=0.0, take_rate=0.15)
        self.assertEqual(r2.state_classification, "INACTIVE")


    def test_negative_input_clamping(self):
        """
        Verify that negative spend values and extreme take rates are clamped gracefully.
        """
        r1 = simulate_round_1(buyer_spend=-500_000.0, supplier_spend=-200_000.0, trust_spend=-100_000.0, take_rate=-0.5)
        self.assertEqual(r1.total_spend, 0.0)
        self.assertEqual(r1.owners_acquired, 0)
        self.assertEqual(r1.walkers_acquired, 0)
        self.assertGreaterEqual(r1.take_rate, 0.01)

        r2 = simulate_round_2(r1, buyer_spend=-100_000.0, supplier_spend=-50_000.0, trust_spend=-10_000.0, take_rate=2.0)
        self.assertEqual(r2.total_spend, 0.0)
        self.assertEqual(r2.new_owners_acquired, 0)
        self.assertLessEqual(r2.take_rate, 0.50)

    def test_r2_balance_ratio_matches_classification(self):
        """
        Verify that in Round 2, balance_ratio is strictly < 0.88 for DEMAND_OVERLOAD,
        > 1.15 for SUPPLY_STARVATION, and between 0.88 and 1.15 for BALANCED.
        """
        r1 = simulate_round_1(buyer_spend=1_200_000.0, supplier_spend=750_000.0, trust_spend=450_000.0, take_rate=0.10, owners_per_walker=8)

        # Balanced strategy
        r2_bal = simulate_round_2(r1, buyer_spend=800_000.0, supplier_spend=950_000.0, trust_spend=500_000.0, take_rate=0.15, owners_per_walker=8)
        self.assertEqual(r2_bal.state_classification, "BALANCED")
        self.assertGreaterEqual(r2_bal.balance_ratio, 0.88)
        self.assertLessEqual(r2_bal.balance_ratio, 1.15)

        # Overload strategy
        r2_over = simulate_round_2(r1, buyer_spend=2_500_000.0, supplier_spend=50_000.0, trust_spend=100_000.0, take_rate=0.15, owners_per_walker=8)
        self.assertEqual(r2_over.state_classification, "DEMAND_OVERLOAD")
        self.assertLess(r2_over.balance_ratio, 0.88)

        # Starvation strategy
        r2_starv = simulate_round_2(r1, buyer_spend=50_000.0, supplier_spend=2_500_000.0, trust_spend=100_000.0, take_rate=0.15, owners_per_walker=8)
        self.assertEqual(r2_starv.state_classification, "SUPPLY_STARVATION")
        self.assertGreater(r2_starv.balance_ratio, 1.15)


    def test_random_walker_efficiency_range_and_override(self):
        """
        Verify that walker capacity efficiency:
        - Defaults to a random integer between 5 and 12 (inclusive) when omitted.
        - Accurately computes walker_capacity = walkers_acquired * owners_per_walker.
        - Correctly assigns quality efficiency labels (Low/Standard/High).
        - Faithfully respects an explicit override (crucial for persistence and benchmarks).
        """
        # Test random draw over multiple iterations
        for _ in range(20):
            r1 = simulate_round_1(buyer_spend=500_000.0, supplier_spend=500_000.0, trust_spend=200_000.0, take_rate=0.15)
            self.assertIsInstance(r1.owners_per_walker, int)
            self.assertGreaterEqual(r1.owners_per_walker, 5)
            self.assertLessEqual(r1.owners_per_walker, 12)
            self.assertEqual(r1.walker_capacity, r1.walkers_acquired * r1.owners_per_walker)

            r2 = simulate_round_2(r1, buyer_spend=300_000.0, supplier_spend=300_000.0, trust_spend=100_000.0, take_rate=0.15)
            self.assertIsInstance(r2.owners_per_walker, int)
            self.assertGreaterEqual(r2.owners_per_walker, 5)
            self.assertLessEqual(r2.owners_per_walker, 12)

        # Test explicit overrides and ratings
        r1_low = simulate_round_1(buyer_spend=500_000.0, supplier_spend=500_000.0, trust_spend=200_000.0, take_rate=0.15, owners_per_walker=6)
        self.assertEqual(r1_low.owners_per_walker, 6)
        self.assertIn("Low", r1_low.walker_efficiency_rating)

        r1_std = simulate_round_1(buyer_spend=500_000.0, supplier_spend=500_000.0, trust_spend=200_000.0, take_rate=0.15, owners_per_walker=8)
        self.assertEqual(r1_std.owners_per_walker, 8)
        self.assertIn("Standard", r1_std.walker_efficiency_rating)

        r1_high = simulate_round_1(buyer_spend=500_000.0, supplier_spend=500_000.0, trust_spend=200_000.0, take_rate=0.15, owners_per_walker=11)
        self.assertEqual(r1_high.owners_per_walker, 11)
        self.assertIn("High", r1_high.walker_efficiency_rating)

    def test_parse_spend_input_fine_tuning(self):
        """
        Verify that parse_spend_input correctly interprets:
        - Decimal millions ($1.25M, 1.234)
        - Thousands notation (500k, $750K)
        - Exact whole dollar amounts ($1,234,567, 1250000)
        - Range clamping [0.0, max_val]
        - Graceful recovery on invalid text input
        """
        # Decimal representations
        self.assertEqual(parse_spend_input("1.25", 1.0, 5.0), 1.25)
        self.assertEqual(parse_spend_input("$1.25M", 1.0, 5.0), 1.25)
        self.assertEqual(parse_spend_input("1.25m", 1.0, 5.0), 1.25)
        self.assertEqual(parse_spend_input("0.485", 1.0, 5.0), 0.485)

        # Thousands notation
        self.assertEqual(parse_spend_input("500k", 1.0, 5.0), 0.5)
        self.assertEqual(parse_spend_input("$750K", 1.0, 5.0), 0.75)
        self.assertEqual(parse_spend_input("250k", 1.0, 5.0), 0.25)

        # Exact whole dollars
        self.assertEqual(parse_spend_input("1,250,000", 1.0, 5.0), 1.25)
        self.assertEqual(parse_spend_input("$1,234,567", 1.0, 5.0), 1.234567)
        self.assertEqual(parse_spend_input("4999999", 1.0, 5.0), 4.999999)

        # Clamping
        self.assertEqual(parse_spend_input("-10", 1.0, 5.0), 0.0)
        self.assertEqual(parse_spend_input("10.0", 1.0, 5.0), 5.0)
        self.assertEqual(parse_spend_input("$6,000,000", 1.0, 5.0), 5.0)

        # Invalid or empty fallback
        self.assertEqual(parse_spend_input("", 1.2, 5.0), 1.2)
        self.assertEqual(parse_spend_input("   ", 1.2, 5.0), 1.2)
        self.assertEqual(parse_spend_input("not-a-number", 1.2, 5.0), 1.2)


if __name__ == "__main__":
    unittest.main()


