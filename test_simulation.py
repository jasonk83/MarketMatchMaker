"""
test_simulation.py — Automated verification of economic invariants for "The Marketplace Matchmaker"
"""

import unittest
from simulation import (
    simulate_round_1,
    simulate_round_2,
    compute_final_scores,
    get_optimal_benchmark,
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


if __name__ == "__main__":
    unittest.main()
