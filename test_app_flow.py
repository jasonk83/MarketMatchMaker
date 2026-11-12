"""
test_app_flow.py — Comprehensive tests for Streamlit App user flow,
button disappearance, auto-scrolling triggers, and state progression.
"""

import os
import unittest
from streamlit.testing.v1 import AppTest
import leaderboard
from leaderboard import DB_PATH


class TestAppFlow(unittest.TestCase):
    def setUp(self):
        # Clear or reset test entries if needed
        pass

    def test_complete_player_flow_and_button_disappearance(self):
        """
        Tests the full simulation flow from Registration -> Round 1 -> Round 1 Report ->
        Round 2 -> Final Scorecard -> Leaderboard.
        Ensures buttons cleanly disappear upon selection and step transitions without lingering.
        """
        at = AppTest.from_file("app.py", default_timeout=15)
        at.run()

        # Step 0: Registration
        self.assertEqual(at.session_state.active_step, "registration")
        self.assertEqual(at.session_state.scroll_to_top_trigger, 0)

        # Enter Founder Name and Company
        at.text_input[0].input("Taylor").run()
        at.text_input[1].input("HappyPaws").run()

        # Click Claim Seed Button
        claim_btn = None
        for b in at.button:
            if "Claim $5.0M Seed" in b.label:
                claim_btn = b
                break
        self.assertIsNotNone(claim_btn, "Claim seed button should be present in registration")
        claim_btn.click().run()

        # Verify Transition to Round 1
        self.assertEqual(at.session_state.active_step, "round1")
        self.assertGreaterEqual(at.session_state.scroll_to_top_trigger, 1)

        # Verify that Claim Seed button disappeared
        for b in at.button:
            self.assertNotIn("Claim $5.0M Seed", b.label)

        # Verify Round 1 levers are present
        self.assertEqual(len(at.slider), 3)
        # Allocate spend: $1.5M Buyer, $1.0M Supplier, $0.5M Trust
        at.slider[0].set_value(1.5).run()
        at.slider[1].set_value(1.0).run()
        at.slider[2].set_value(0.5).run()

        # Find Commit Round 1 button
        commit_r1_btn = None
        for b in at.button:
            if "Commit Round 1 Strategy" in b.label:
                commit_r1_btn = b
                break
        self.assertIsNotNone(commit_r1_btn, "Commit Round 1 button should be present")
        self.assertFalse(commit_r1_btn.disabled, "Commit Round 1 button should be enabled after spend allocation")

        # Click Commit Round 1
        trigger_before = at.session_state.scroll_to_top_trigger
        commit_r1_btn.click().run()

        # Verify Step 2: Round 1 Report
        self.assertEqual(at.session_state.active_step, "round1_report")
        self.assertGreater(at.session_state.scroll_to_top_trigger, trigger_before)
        self.assertIsNotNone(at.session_state.r1_result)

        # Verify that Commit Round 1 button DISAPPEARED
        for b in at.button:
            self.assertNotIn("Commit Round 1 Strategy", b.label)

        # Find Proceed to Round 2 button
        proceed_r2_btn = None
        for b in at.button:
            if "Proceed to Round 2" in b.label:
                proceed_r2_btn = b
                break
        self.assertIsNotNone(proceed_r2_btn, "Proceed to Round 2 button should be present on report")

        # Click Proceed to Round 2
        trigger_before = at.session_state.scroll_to_top_trigger
        proceed_r2_btn.click().run()

        # Verify Step 3: Round 2
        self.assertEqual(at.session_state.active_step, "round2")
        self.assertGreater(at.session_state.scroll_to_top_trigger, trigger_before)

        # Verify Proceed to Round 2 button DISAPPEARED
        for b in at.button:
            self.assertNotIn("Proceed to Round 2", b.label)

        # Verify Round 2 Levers and allocate
        self.assertGreaterEqual(len(at.slider), 3)
        # Allocate within available cash
        avail_cash_m = at.session_state.r1_result.cash_end / 1_000_000.0
        spend_chunk = round(min(0.8, avail_cash_m / 3.5), 2)
        at.slider[0].set_value(spend_chunk).run()
        at.slider[1].set_value(spend_chunk).run()
        at.slider[2].set_value(spend_chunk).run()

        # Find Lock Final Strategy button
        lock_r2_btn = None
        for b in at.button:
            if "Lock Final Strategy" in b.label:
                lock_r2_btn = b
                break
        self.assertIsNotNone(lock_r2_btn, "Lock Final Strategy button should be present in Round 2")
        self.assertFalse(lock_r2_btn.disabled, "Lock Final Strategy button should be enabled")

        # Click Lock Final Strategy
        trigger_before = at.session_state.scroll_to_top_trigger
        lock_r2_btn.click().run()

        # Verify Step 4: Final Scorecard
        self.assertEqual(at.session_state.active_step, "final_scorecard")
        self.assertGreater(at.session_state.scroll_to_top_trigger, trigger_before)
        self.assertIsNotNone(at.session_state.scorecard)

        # Verify Lock Final Strategy button DISAPPEARED
        for b in at.button:
            self.assertNotIn("Lock Final Strategy", b.label)

        # Find Take me to the Leaderboard button
        lb_btn = None
        for b in at.button:
            if "Take me to the Leaderboard" in b.label:
                lb_btn = b
                break
        self.assertIsNotNone(lb_btn, "Take me to the Leaderboard button should be present on final scorecard")

        # Click Take me to the Leaderboard
        trigger_before = at.session_state.scroll_to_top_trigger
        lb_btn.click().run()

        # Verify Navigation to Leaderboard
        self.assertEqual(at.session_state.main_tab_nav, "🏆🐕 Live Class Leaderboard & Instructor Debrief")
        self.assertGreater(at.session_state.scroll_to_top_trigger, trigger_before)

    def test_text_field_commitment_and_boundary_guards(self):
        """
        Tests typing spend directly into text inputs (e.g. 1.25M, $750k, $500,000)
        and verifies commit button enables, commits exact dollar values, and disappears.
        """
        at = AppTest.from_file("app.py", default_timeout=15)
        at.run()

        # Register
        at.text_input[0].input("Sam").run()
        at.text_input[1].input("BarkClub").run()
        claim_btn = [b for b in at.button if "Claim $5.0M Seed" in b.label][0]
        claim_btn.click().run()

        self.assertEqual(at.session_state.active_step, "round1")

        # Initially $0 spend -> Commit button is clickable but validates spend safely
        commit_btn = [b for b in at.button if "Commit Round 1 Strategy" in b.label][0]
        self.assertFalse(commit_btn.disabled, "Commit button remains interactive to prevent dropped clicks in browser")
        commit_btn.click().run()
        self.assertEqual(at.session_state.active_step, "round1", "Zero spend click must not advance to report")
        self.assertIsNotNone(at.session_state.r1_commit_error)
        self.assertIn("No Capital Allocated", at.session_state.r1_commit_error)

        # Type text spend directly into text inputs:
        # In r1, let's find text inputs with keys r1_buyer_text, r1_supplier_text, r1_trust_text
        for ti in at.text_input:
            if ti.key == "r1_buyer_text":
                ti.input("1.25M").run()
            elif ti.key == "r1_supplier_text":
                ti.input("$750k").run()
            elif ti.key == "r1_trust_text":
                ti.input("$500,000").run()

        # Re-fetch commit button
        commit_btn = [b for b in at.button if "Commit Round 1 Strategy" in b.label][0]
        self.assertFalse(commit_btn.disabled, "Commit button should be enabled after valid text input spend")

        # Click Commit
        commit_btn.click().run()

        # Verify Round 1 Report reached
        self.assertEqual(at.session_state.active_step, "round1_report")
        self.assertEqual(at.session_state.r1_result.buyer_spend, 1_250_000.0)
        self.assertEqual(at.session_state.r1_result.supplier_spend, 750_000.0)
        self.assertEqual(at.session_state.r1_result.trust_spend, 500_000.0)

        # Verify Commit button disappeared
        self.assertEqual(len([b for b in at.button if "Commit Round 1 Strategy" in b.label]), 0)

    def test_simultaneous_text_entry_and_commit_without_enter(self):
        """
        Simulates real-world browser behavior: user types spend into an open text field
        and clicks 'Commit Round 1 Strategy' immediately without pressing Enter or blurring first.
        Verifies that the commit succeeds on the very first click and advances to Round 1 report.
        """
        at = AppTest.from_file("app.py", default_timeout=15).run()
        at.text_input[0].input("Morgan").run()
        at.text_input[1].input("BarkFast").run()
        claim_btn = [b for b in at.button if "Claim $5.0M Seed" in b.label][0]
        claim_btn.click().run()

        self.assertEqual(at.session_state.active_step, "round1")

        # In a real browser, typing and clicking the button in the same client event loop:
        ti = [t for t in at.text_input if t.key == "r1_buyer_text"][0]
        ti.input("2.5M")
        commit_btn = [b for b in at.button if "Commit Round 1 Strategy" in b.label][0]
        commit_btn.click()
        at.run()

        # Verify it committed on the first click and transitioned to round1_report
        self.assertEqual(at.session_state.active_step, "round1_report")
        self.assertEqual(at.session_state.r1_result.buyer_spend, 2_500_000.0)
        # Commit button must be gone
        self.assertEqual(len([b for b in at.button if "Commit Round 1 Strategy" in b.label]), 0)

        # On Round 1 report, verify Proceed to Round 2 button is present
        proceed_btn = [b for b in at.button if "Proceed to Round 2" in b.label][0]
        proceed_btn.click().run()

        # Verify Proceed button disappears and advances to round2
        self.assertEqual(at.session_state.active_step, "round2")
        self.assertEqual(len([b for b in at.button if "Proceed to Round 2" in b.label]), 0)

    def test_overdraft_guard_prevents_commitment(self):
        """
        Tests that attempting to commit an overdraft (> $5.0M) does not advance to report,
        shows an overdraft error, and does not corrupt state.
        """
        at = AppTest.from_file("app.py", default_timeout=15).run()
        at.text_input[0].input("OverdraftTester").run()
        at.text_input[1].input("OverdraftCo").run()
        claim_btn = [b for b in at.button if "Claim $5.0M Seed" in b.label][0]
        claim_btn.click().run()

        # Allocate 3.0M + 3.0M = 6.0M (> 5.0M)
        for ti in at.text_input:
            if ti.key == "r1_buyer_text":
                ti.input("3.0M").run()
            elif ti.key == "r1_supplier_text":
                ti.input("3.0M").run()

        commit_btn = [b for b in at.button if "Commit Round 1 Strategy" in b.label][0]
        commit_btn.click().run()

        # Must remain in round1
        self.assertEqual(at.session_state.active_step, "round1")
        self.assertIsNotNone(at.session_state.r1_commit_error)
        self.assertIn("Budget Overdraft", at.session_state.r1_commit_error)
        # Button remains present to allow student to correct allocations
        self.assertEqual(len([b for b in at.button if "Commit Round 1 Strategy" in b.label]), 1)


if __name__ == "__main__":
    unittest.main()
