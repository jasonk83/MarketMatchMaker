"""
app.py — The Marketplace Matchmaker (Streamlit Simulation)
Two-Sided Platform Simulation for Undergraduate IT Students.
Teaches two-sided network effects, chicken-or-egg liquidity, CAC saturation,
multi-homing rivalry, and disintermediation (off-platform leakage).
"""

import os
import streamlit as st
import pandas as pd
import altair as alt

from simulation import (
    simulate_round_1,
    simulate_round_2,
    compute_final_scores,
    get_optimal_benchmark,
    Round1Result,
    Round2Result,
    FinalScorecard,
)
import leaderboard


# -----------------------------------------------------------------------------
# Configuration & Custom CSS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="The Marketplace Matchmaker",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    /* Metric Card Styling */
    .metric-card {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 12px;
    }
    .metric-title {
        color: #94A3B8;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .metric-value {
        color: #F8FAFC;
        font-size: 1.8rem;
        font-weight: 700;
        margin-top: 4px;
    }
    .metric-sub {
        color: #38BDF8;
        font-size: 0.85rem;
        margin-top: 2px;
    }
    .danger-sub {
        color: #F87171 !important;
    }
    .success-sub {
        color: #4ADE80 !important;
    }
    /* Section Callout Card */
    .callout-box {
        background-color: #1E293B;
        border-left: 4px solid #3B82F6;
        padding: 14px 18px;
        border-radius: 4px;
        margin-bottom: 16px;
    }
    .warning-box {
        background-color: rgba(245, 158, 11, 0.12);
        border-left: 4px solid #F59E0B;
        padding: 14px 18px;
        border-radius: 4px;
        margin-bottom: 16px;
    }
    .danger-box {
        background-color: rgba(239, 68, 68, 0.12);
        border-left: 4px solid #EF4444;
        padding: 14px 18px;
        border-radius: 4px;
        margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Session State Initialization & Recovery
# -----------------------------------------------------------------------------
if "player_name" not in st.session_state:
    st.session_state.player_name = ""
if "company_name" not in st.session_state:
    st.session_state.company_name = ""
if "active_step" not in st.session_state:
    st.session_state.active_step = "registration"
if "r1_result" not in st.session_state:
    st.session_state.r1_result = None
if "r2_result" not in st.session_state:
    st.session_state.r2_result = None
if "scorecard" not in st.session_state:
    st.session_state.scorecard = None


def recover_player_state(first_name: str) -> bool:
    """Recovers the player's saved state from the database if present."""
    record = leaderboard.get_player(first_name)
    if not record:
        return False
    
    st.session_state.player_name = record["first_name"]
    st.session_state.company_name = record["company_name"]
    
    status = record["status"]
    if status == "In Round 1":
        st.session_state.active_step = "round1"
    elif status == "In Round 2":
        # Reconstruct R1 result
        r1 = simulate_round_1(
            buyer_spend=record["r1_buyer_spend"],
            supplier_spend=record["r1_supplier_spend"],
            trust_spend=record["r1_trust_spend"],
            take_rate=record["r1_take_rate"],
        )
        st.session_state.r1_result = r1
        st.session_state.active_step = "round2"
    elif status == "Completed":
        # Reconstruct R1 & R2
        r1 = simulate_round_1(
            buyer_spend=record["r1_buyer_spend"],
            supplier_spend=record["r1_supplier_spend"],
            trust_spend=record["r1_trust_spend"],
            take_rate=record["r1_take_rate"],
        )
        r2 = simulate_round_2(
            r1=r1,
            buyer_spend=record["r2_buyer_spend"],
            supplier_spend=record["r2_supplier_spend"],
            trust_spend=record["r2_trust_spend"],
            take_rate=record["r2_take_rate"],
        )
        scorecard = compute_final_scores(r1, r2)
        st.session_state.r1_result = r1
        st.session_state.r2_result = r2
        st.session_state.scorecard = scorecard
        st.session_state.active_step = "final_scorecard"
    return True


# -----------------------------------------------------------------------------
# Main Navigation Tabs
# -----------------------------------------------------------------------------
tab_player, tab_leaderboard = st.tabs([
    "🐾 Launch Your Marketplace (Player Console)",
    "🏆 Live Class Leaderboard & Instructor Debrief",
])


# =============================================================================
# TAB 1: PLAYER CONSOLE
# =============================================================================
with tab_player:
    # Header
    st.title("🐾 The Marketplace Matchmaker")
    st.caption("Strategic Simulation of Two-Sided Platform Economics & Network Effects")

    # Step 0: Registration
    if st.session_state.active_step == "registration":
        st.markdown("""
        <div class="callout-box">
            <h4>👋 Welcome, Founder!</h4>
            You have just raised <strong>$5.0M in Seed Capital</strong> to launch an on-demand, peer-to-peer 
            <strong>Dog Walking Marketplace</strong>. Your mission is to solve the classic 
            <em>Chicken-or-Egg Cold Start Problem</em>, conquer multi-homing competitors, defend against 
            off-platform disintermediation, and build a high-valuation platform.
        </div>
        """, unsafe_allow_html=True)

        col_reg1, col_reg2 = st.columns([1, 1])
        with col_reg1:
            input_name = st.text_input("Founder First Name", placeholder="e.g. Jordan").strip()
            input_company = st.text_input("Marketplace Company Name", placeholder="e.g. Bark Avenue, ZoomieWalks, PawPath").strip()

            if st.button("🚀 Claim $5.0M Seed & Enter Round 1", type="primary", use_container_width=True):
                if not input_name or not input_company:
                    st.error("Please enter both your First Name and Company Name to begin.")
                else:
                    # Check if returning player
                    recovered = recover_player_state(input_name)
                    if recovered:
                        st.info(f"Welcome back, {st.session_state.player_name}! Restoring your saved session...")
                        st.rerun()
                    else:
                        # New player registration
                        record, _ = leaderboard.register_or_get_player(input_name, input_company)
                        st.session_state.player_name = record["first_name"]
                        st.session_state.company_name = record["company_name"]
                        st.session_state.active_step = "round1"
                        st.rerun()

        with col_reg2:
            st.markdown("""
            ### 🎯 Core Learning Objectives
            - **Two-Sided Liquidity**: 1 active dog walker can fulfill walks for up to **8 dog owners** (~32 walks/mo).
            - **Chicken-or-Egg Risk**: Attracting too many owners creates 90+ min wait times; attracting too many walkers leaves them idle and causes starvation churn.
            - **Platform Governance**: Without background checks and pet insurance, trust collapses.
            - **Defensibility**: High take rates tempt users to exchange numbers and pay via **Venmo** off-app.
            """)

    # Top Status Bar for Active Players
    if st.session_state.active_step != "registration":
        top_c1, top_c2, top_c3 = st.columns([2, 2, 1])
        with top_c1:
            st.markdown(f"**Founder:** `{st.session_state.player_name}` | **Company:** `{st.session_state.company_name}`")
        with top_c2:
            status_text = {
                "round1": "⏳ Round 1: Cold Start Liquidity",
                "round1_report": "📊 Round 1 Diagnostic Report",
                "round2": "🟡 Round 2: Multi-Homing & Leakage Threat",
                "final_scorecard": "✅ Final Scorecard (Locked)",
            }.get(st.session_state.active_step, "")
            st.markdown(f"**Stage:** {status_text}")
        with top_c3:
            if st.button("🔄 Switch Founder", use_container_width=True):
                st.session_state.player_name = ""
                st.session_state.company_name = ""
                st.session_state.active_step = "registration"
                st.session_state.r1_result = None
                st.session_state.r2_result = None
                st.session_state.scorecard = None
                st.rerun()
        st.divider()

    # Step 1: Round 1 Strategy Allocation
    if st.session_state.active_step == "round1":
        st.subheader("Round 1: The Liquidity Crisis (Cold Start Launch)")
        st.markdown("""
        <div class="callout-box">
            <strong>The Chicken-or-Egg Challenge:</strong> Dog owners will not join without reliable nearby dog walkers, 
            and dog walkers will not stay active without steady walk bookings.<br>
            • <strong>Seed Capital:</strong> $5.00M available.<br>
            • <strong>Capacity Rule:</strong> 1 active dog walker serves up to <strong>8 regular dog owners</strong>.<br>
            • <strong>Walk Price:</strong> Standardized at <strong>$30 per walk</strong>.
        </div>
        """, unsafe_allow_html=True)

        col_l, col_r = st.columns([3, 2])
        with col_l:
            st.markdown("#### ⚙️ Quantitative Capital Levers")
            buyer_spend = st.slider(
                "1. Buyer Acquisition Spend (Dog Owners)",
                min_value=0.0,
                max_value=5.0,
                value=1.2,
                step=0.05,
                format="$%.2fM",
                help="Funds first-walk discount coupons, localized ads, and community campaigns. CAC rises with aggressive spend."
            ) * 1_000_000.0

            supplier_spend = st.slider(
                "2. Supplier Acquisition Spend (Dog Walkers)",
                min_value=0.0,
                max_value=5.0,
                value=0.75,
                step=0.05,
                format="$%.2fM",
                help="Funds guaranteed hourly minimums, onboarding bonuses, and walker equipment."
            ) * 1_000_000.0

            trust_spend = st.slider(
                "3. Platform Governance & Trust Spend",
                min_value=0.0,
                max_value=5.0,
                value=0.45,
                step=0.05,
                format="$%.2fM",
                help="Funds $25k Pet Emergency Insurance pools, automated background checks, and live GPS route tracking."
            ) * 1_000_000.0

            take_rate_pct = st.radio(
                "4. Platform Take Rate (Commission % per $30 walk)",
                options=[5, 10, 15, 20, 25],
                index=1,
                horizontal=True,
                format_func=lambda x: f"{x}%",
                help="Higher take rates yield more revenue per walk, but squeeze walker earnings and depress walker onboarding."
            )
            take_rate = take_rate_pct / 100.0

        with col_r:
            st.markdown("#### 💰 Budget Tracker")
            total_spend_r1 = buyer_spend + supplier_spend + trust_spend
            cash_left = 5_000_000.0 - total_spend_r1

            st.metric("Total Round 1 Spend", f"${total_spend_r1/1_000_000:.2f}M", f"${5.0 - total_spend_r1/1_000_000:.2f}M Seed Remaining")

            if total_spend_r1 > 5_000_000.0:
                st.markdown("""
                <div class="danger-box">
                    🚨 <strong>Budget Overdraft!</strong> You have allocated more than your $5.0M seed capital. 
                    Reduce your spend sliders before committing.
                </div>
                """, unsafe_allow_html=True)
            elif total_spend_r1 > 3_500_000.0:
                st.markdown("""
                <div class="warning-box">
                    ⚠️ <strong>Capital Depletion Warning:</strong> Spending over $3.5M leaves under $1.5M for Round 2. 
                    You risk entering Round 2 severely under-capitalized against emerging rivals.
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="callout-box">
                    ✅ <strong>Prudent Reserve:</strong> You are retaining sufficient seed capital to defend your position in Round 2.
                </div>
                """, unsafe_allow_html=True)

            st.markdown("""
            **Strategic Check:**
            - Base Dog Owner CAC: ~$60
            - Base Dog Walker CAC: ~$350
            - Target Ratio: 1 Walker per 8 Dog Owners
            """)

            if st.button("🔒 Commit Round 1 Strategy (Blind Decision)", type="primary", use_container_width=True, disabled=(total_spend_r1 > 5_000_000.0)):
                r1_result = simulate_round_1(
                    buyer_spend=buyer_spend,
                    supplier_spend=supplier_spend,
                    trust_spend=trust_spend,
                    take_rate=take_rate,
                )
                st.session_state.r1_result = r1_result
                
                # Persist to DB
                leaderboard.save_round_1_results(
                    first_name=st.session_state.player_name,
                    r1_buyer=buyer_spend,
                    r1_supplier=supplier_spend,
                    r1_trust=trust_spend,
                    r1_take=take_rate,
                    owners=r1_result.owners_acquired,
                    walkers=r1_result.walkers_acquired,
                    balance=r1_result.balance_ratio,
                    state=r1_result.state_classification,
                    liquidity=r1_result.liquidity_rate,
                    net_rev=r1_result.platform_net_revenue,
                    cash_end=r1_result.cash_end,
                )
                st.session_state.active_step = "round1_report"
                st.rerun()

    # Step 2: Round 1 Diagnostic Report
    if st.session_state.active_step == "round1_report":
        r1 = st.session_state.r1_result
        st.subheader("📊 Round 1 Diagnostic Report")

        if r1.state_classification == "DEMAND_OVERLOAD":
            st.markdown("""
            <div class="danger-box">
                ⚠️ <strong>DEMAND OVERLOAD CRISIS:</strong> Dog owner demand overwhelmed your dog walker capacity! 
                Severe wait times resulted in high customer cancellation and churn.
            </div>
            """, unsafe_allow_html=True)
        elif r1.state_classification == "SUPPLY_STARVATION":
            st.markdown("""
            <div class="danger-box">
                ⚠️ <strong>SUPPLY STARVATION CRISIS:</strong> You recruited too many walkers for your demand. 
                Walkers sat idle with empty schedules, earned low income, and churned off the platform!
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="callout-box" style="border-left-color: #10B981;">
                ✅ <strong>HYPER-LOCAL LIQUIDITY SYNCHRONIZED:</strong> Exceptional synchronization! 
                Supply and demand matched tightly within the 1-to-8 ratio, yielding low wait times and happy participants.
            </div>
            """, unsafe_allow_html=True)

        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("Owners Acquired", f"{r1.owners_acquired:,}", f"{r1.surviving_owners:,} surviving")
        col_m2.metric("Walker Capacity", f"{r1.walker_capacity:,} owners", f"{r1.walkers_acquired:,} walkers active")
        col_m3.metric("Avg Wait Time", f"{r1.avg_wait_time_minutes} mins", f"Balance: {r1.balance_ratio:.2f}")
        col_m4.metric("Net Revenue Earned", f"${r1.platform_net_revenue/1_000_000:.2f}M", f"GMV: ${r1.gross_merchandise_value/1_000_000:.2f}M")

        # Capacity vs Demand Chart
        chart_data = pd.DataFrame({
            "Side": ["Dog Owner Demand", "Walker Capacity (Walkers × 8)", "Matched Surviving Owners"],
            "Users": [r1.owners_acquired, r1.walker_capacity, r1.surviving_owners],
            "Type": ["Demand", "Capacity", "Matched"],
        })
        chart = alt.Chart(chart_data).mark_bar(cornerRadius=6).encode(
            x=alt.X("Side:N", title=""),
            y=alt.Y("Users:Q", title="Number of People / Capacity"),
            color=alt.Color("Side:N", legend=None, scale=alt.Scale(
                domain=["Dog Owner Demand", "Walker Capacity (Walkers × 8)", "Matched Surviving Owners"],
                range=["#3B82F6", "#F59E0B", "#10B981"]
            )),
            tooltip=["Side", "Users"]
        ).properties(height=260)
        st.altair_chart(chart, use_container_width=True)

        st.markdown(f"**Diagnostic Feedback:**\n\n{r1.feedback}")

        st.markdown(f"""
        <div class="callout-box">
            💰 <strong>Capital Carried Forward to Round 2:</strong><br>
            • Seed Remaining: <strong>${(5_000_000.0 - r1.total_spend)/1_000_000:.2f}M</strong><br>
            • Round 1 Net Revenue Added: <strong>+${r1.platform_net_revenue/1_000_000:.2f}M</strong><br>
            • <strong>Total Available Cash for Round 2: ${r1.cash_end/1_000_000:.2f}M</strong>
        </div>
        """, unsafe_allow_html=True)

        if st.button("⚡ Proceed to Round 2: The Rival Threat", type="primary", use_container_width=True):
            st.session_state.active_step = "round2"
            st.rerun()

    # Step 3: Round 2 Strategy Allocation
    if st.session_state.active_step == "round2":
        r1 = st.session_state.r1_result
        available_cash_r2 = r1.cash_end

        st.subheader("Round 2: The Multi-Homing & Disintermediation Threat")
        
        st.markdown("""
        <div class="warning-box">
            <h4>🚨 Urgent Market Crisis Briefing:</h4>
            <strong>1. Rival Entrant 'BarkBuddy':</strong> A well-funded competitor has just entered the city with an aggressive 
            <strong>12% Take Rate</strong> and heavy walker poaching bonuses. If your take rate is 20%+ or you underfund walker retention, 
            walkers will multi-home and defect to BarkBuddy.<br><br>
            <strong>2. Off-Platform Leakage ('The Venmo Temptation'):</strong> Repeat dog owners and walkers who matched in Round 1 now know each other! 
            They are tempted to text each other directly and pay via Venmo to bypass platform fees.<br>
            <em>The Only Defense:</em> <strong>Cumulative Governance & Trust Spend</strong>. Dog owners will refuse to go off-app if they would forfeit your 
            $25k Pet Emergency Insurance, real-time GPS tracking, and instant dispute resolution!
        </div>
        """, unsafe_allow_html=True)

        col2_l, col2_r = st.columns([3, 2])
        max_spend_val = max(0.1, available_cash_r2 / 1_000_000.0)

        with col2_l:
            st.markdown("#### ⚙️ Round 2 Capital Levers")
            buyer_spend_2 = st.slider(
                "1. Buyer Growth & Loyalty Budget",
                min_value=0.0,
                max_value=float(max_spend_val),
                value=float(min(1.10, max_spend_val * 0.45)),
                step=0.05,
                format="$%.2fM",
                help="Funds new dog owner acquisition (70%) and existing owner retention subsidies (30%)."
            ) * 1_000_000.0

            supplier_spend_2 = st.slider(
                "2. Supplier Growth & Rival Defense Budget",
                min_value=0.0,
                max_value=float(max_spend_val),
                value=float(min(0.80, max_spend_val * 0.35)),
                step=0.05,
                format="$%.2fM",
                help="Funds new walker recruitment (65%) and walker retention bonuses (35%) to prevent BarkBuddy poaching."
            ) * 1_000_000.0

            trust_spend_2 = st.slider(
                "3. Platform Governance & Trust Moat",
                min_value=0.0,
                max_value=float(max_spend_val),
                value=float(min(0.50, max_spend_val * 0.20)),
                step=0.05,
                format="$%.2fM",
                help="Cumulative trust spend creates switching friction that stops Venmo leakage dead in its tracks."
            ) * 1_000_000.0

            take_rate_pct_2 = st.radio(
                "4. Round 2 Take Rate (BarkBuddy is at 12%)",
                options=[5, 10, 15, 20, 25],
                index=2,
                horizontal=True,
                format_func=lambda x: f"{x}%",
                help="20% and 25% take rates trigger massive multi-homing defection to BarkBuddy and heavy Venmo leakage."
            )
            take_rate_2 = take_rate_pct_2 / 100.0

        with col2_r:
            st.markdown("#### 💰 Round 2 Budget Tracker")
            total_spend_r2 = buyer_spend_2 + supplier_spend_2 + trust_spend_2
            cash_rem_after_spend = available_cash_r2 - total_spend_r2

            st.metric("Total Round 2 Spend", f"${total_spend_r2/1_000_000:.2f}M", f"${available_cash_r2/1_000_000:.2f}M Available Cash")

            if total_spend_r2 > available_cash_r2:
                st.markdown("""
                <div class="danger-box">
                    🚨 <strong>Exceeds Available Cash!</strong> Reduce your spend sliders to stay within your available funds.
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="callout-box">
                    Unspent Cash Reserves: <strong>${cash_rem_after_spend/1_000_000:.2f}M</strong><br>
                    (Note: 100% of unspent cash is credited to your Enterprise Valuation at the end!)
                </div>
                """, unsafe_allow_html=True)

            cum_trust = r1.trust_spend + trust_spend_2
            st.markdown(f"**Cumulative Trust Moat:** `${cum_trust/1_000_000:.2f}M` (Target: `$0.8M+` for max Venmo defense)")

            if st.button("🔒 Lock Final Strategy (Submit Round 2)", type="primary", use_container_width=True, disabled=(total_spend_r2 > available_cash_r2)):
                r2_result = simulate_round_2(
                    r1=r1,
                    buyer_spend=buyer_spend_2,
                    supplier_spend=supplier_spend_2,
                    trust_spend=trust_spend_2,
                    take_rate=take_rate_2,
                )
                scorecard = compute_final_scores(r1, r2_result)
                
                st.session_state.r2_result = r2_result
                st.session_state.scorecard = scorecard

                # Persist to DB and mark Completed
                leaderboard.save_round_2_and_complete(
                    first_name=st.session_state.player_name,
                    r2_buyer=buyer_spend_2,
                    r2_supplier=supplier_spend_2,
                    r2_trust=trust_spend_2,
                    r2_take=take_rate_2,
                    r2_liquidity=r2_result.liquidity_rate,
                    r2_retention=r2_result.retention_rate,
                    r2_net_rev=r2_result.platform_net_revenue,
                    r2_leakage_gmv=r2_result.gmv_lost_to_venmo,
                    r2_cash_rem=r2_result.cash_remaining,
                    liquidity_score=scorecard.liquidity_score,
                    retention_score=scorecard.retention_score,
                    valuation_m=scorecard.enterprise_valuation,
                    valuation_score=scorecard.valuation_score,
                    composite_score=scorecard.composite_score,
                )
                st.session_state.active_step = "final_scorecard"
                st.rerun()

    # Step 4: Final Scorecard (Single Attempt Permanently Locked)
    if st.session_state.active_step == "final_scorecard":
        sc = st.session_state.scorecard
        r1 = st.session_state.r1_result
        r2 = st.session_state.r2_result

        st.subheader(f"🏁 Final Executive Scorecard — {st.session_state.company_name}")
        st.markdown("""
        <div class="callout-box" style="border-left-color: #10B981;">
            🔒 <strong>ATTEMPT COMPLETED & LOCKED:</strong> Your strategic decisions are finalized and recorded on the 
            <strong>Live Class Leaderboard</strong>.
        </div>
        """, unsafe_allow_html=True)

        # Headline Score Banner
        score_c1, score_c2, score_c3, score_c4 = st.columns(4)
        with score_c1:
            st.markdown(f"""
            <div class="metric-card" style="border-color: #3B82F6;">
                <div class="metric-title">Composite Index Score</div>
                <div class="metric-value" style="color: #60A5FA;">{sc.composite_score:.1f} / 100</div>
                <div class="metric-sub">Weighted 1/3 each</div>
            </div>
            """, unsafe_allow_html=True)
        with score_c2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Marketplace Liquidity</div>
                <div class="metric-value">{sc.liquidity_score:.1f}%</div>
                <div class="metric-sub">{sc.completed_walks:,} completed walks</div>
            </div>
            """, unsafe_allow_html=True)
        with score_c3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Platform Retention</div>
                <div class="metric-value">{sc.retention_score:.1f}%</div>
                <div class="metric-sub">{r2.active_owners:,} owners | {r2.active_walkers:,} walkers</div>
            </div>
            """, unsafe_allow_html=True)
        with score_c4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Enterprise Valuation</div>
                <div class="metric-value">${sc.enterprise_valuation:.2f}M</div>
                <div class="metric-sub">${sc.operating_valuation:.2f}M Ops + ${sc.cash_remaining:.2f}M Cash</div>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        col_f1, col_f2 = st.columns([1, 1])
        with col_f1:
            st.markdown("#### 🔄 Transaction Fate in Round 2")
            fate_df = pd.DataFrame({
                "Outcome": [
                    "Completed on Platform",
                    "Leaked to Venmo Off-App",
                    "Unmatched / Shortage",
                ],
                "Walks": [
                    sc.completed_walks,
                    sc.walks_lost_to_leakage,
                    sc.walks_unmatched,
                ],
            })
            fate_chart = alt.Chart(fate_df).mark_arc(innerRadius=60).encode(
                theta=alt.Theta("Walks:Q"),
                color=alt.Color("Outcome:N", scale=alt.Scale(
                    domain=["Completed on Platform", "Leaked to Venmo Off-App", "Unmatched / Shortage"],
                    range=["#10B981", "#EF4444", "#94A3B8"]
                )),
                tooltip=["Outcome", "Walks"]
            ).properties(height=260)
            st.altair_chart(fate_chart, use_container_width=True)

            st.markdown(f"""
            - **Completed Walks:** `{sc.completed_walks:,}` (${r2.gross_merchandise_value/1_000_000:.2f}M GMV)
            - **Walks Leaked to Venmo:** `{sc.walks_lost_to_leakage:,}` (${r2.gmv_lost_to_venmo/1_000_000:.2f}M lost GMV)
            - **Walkers Lost to BarkBuddy:** `{r2.walkers_lost_to_rival:,}` ({int(r2.walker_defection_rate*100)}% defection)
            """)

        with col_f2:
            st.markdown("#### 📑 Strategic Executive Debrief")
            st.markdown(sc.overall_debrief)
            st.markdown("---")
            st.markdown(f"**Round 1 Performance:**\n\n{sc.feedback_r1}")
            st.markdown("---")
            st.markdown(f"**Round 2 Defense:**\n\n{sc.feedback_r2}")


# =============================================================================
# TAB 2: LIVE CLASS LEADERBOARD & INSTRUCTOR DEBRIEF
# =============================================================================
with tab_leaderboard:
    st.title("🏆 Live Class Leaderboard")
    st.caption("Auto-refreshes every 3 seconds — projected during classroom gameplay")

    @st.fragment(run_every=3)
    def render_live_leaderboard():
        df = leaderboard.get_leaderboard_dataframe()
        
        # Summary counts
        analytics = leaderboard.get_class_analytics()
        col_c1, col_c2, col_c3, col_c4 = st.columns(4)
        col_c1.metric("Registered Founders", analytics["total_founders"])
        col_c2.metric("Completed Attempts", analytics["completed_count"])
        col_c3.metric("In Progress", analytics["in_r1_count"] + analytics["in_r2_count"])
        col_c4.metric("Avg Composite Score", f"{analytics['avg_composite']:.1f}")

        st.markdown("### 📊 Ranked Platform Standings")
        if df.empty:
            st.info("No founders registered yet. Tell students to claim their seed funding in the Player Console!")
        else:
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Rank": st.column_config.TextColumn(width="small"),
                    "Founder": st.column_config.TextColumn(width="medium"),
                    "Marketplace Company": st.column_config.TextColumn(width="medium"),
                    "Status": st.column_config.TextColumn(width="small"),
                    "Composite Score": st.column_config.TextColumn(width="small"),
                    "Liquidity %": st.column_config.TextColumn(width="small"),
                    "Retention %": st.column_config.TextColumn(width="small"),
                    "Valuation ($M)": st.column_config.TextColumn(width="small"),
                }
            )

    render_live_leaderboard()

    st.divider()

    # PIN-Protected Instructor Panel
    st.subheader("🔒 Instructor Control Panel & Class Debrief")
    default_pin = os.environ.get("INSTRUCTOR_PIN", "2026")
    try:
        default_pin = st.secrets.get("INSTRUCTOR_PIN", default_pin)
    except Exception:
        pass

    instructor_pin = st.text_input("Enter Instructor PIN", type="password", placeholder="PIN required (default: 2026)")

    if instructor_pin == default_pin:
        st.success("🔓 Instructor Access Granted")
        analytics = leaderboard.get_class_analytics()

        # Class-wide Analytics
        st.markdown("### 📈 Class-Wide Strategy Analytics")
        an_col1, an_col2, an_col3, an_col4 = st.columns(4)
        an_col1.metric("Avg R1 Take Rate", f"{analytics['avg_r1_take']:.1f}%")
        an_col2.metric("Avg R2 Take Rate", f"{analytics['avg_r2_take']:.1f}%")
        an_col3.metric("Total Class GMV Leaked to Venmo", f"${analytics['total_leakage_gmv']/1_000_000:.2f}M")
        an_col4.metric("Avg Enterprise Valuation", f"${analytics['avg_valuation']:.2f}M")

        # R1 Strategy distribution
        st.markdown("#### Round 1 Liquidity Decisions:")
        r1_states = analytics["r1_states"]
        if r1_states:
            state_df = pd.DataFrame([
                {"Strategy Outcome": k.replace("_", " ").title(), "Student Count": v}
                for k, v in r1_states.items()
            ])
            state_chart = alt.Chart(state_df).mark_bar(cornerRadius=4).encode(
                x="Strategy Outcome:N",
                y="Student Count:Q",
                color=alt.Color("Strategy Outcome:N", scale=alt.Scale(
                    domain=["Balanced", "Demand Overload", "Supply Starvation"],
                    range=["#10B981", "#EF4444", "#F59E0B"]
                ))
            ).properties(height=220)
            st.altair_chart(state_chart, use_container_width=True)

        # Toggleable Optimal Benchmark Reveal
        st.markdown("---")
        st.markdown("### 💡 Pedagogical Benchmark Strategy Reveal")
        if st.checkbox("Reveal Master Benchmark Strategy & Optimal Allocations"):
            benchmark = get_optimal_benchmark()
            b_sc = benchmark["scorecard"]
            b_r1 = benchmark["r1_result"]
            b_r2 = benchmark["r2_result"]

            st.markdown(f"""
            <div class="callout-box" style="border-left-color: #38BDF8;">
                <h4>🏆 Optimal Platform Blueprint (Composite: {b_sc.composite_score:.1f}/100)</h4>
                <strong>Round 1 Allocation:</strong><br>
                • Buyer Spend: $1.20M | Walker Spend: $0.75M | Trust Spend: $0.45M | Take Rate: 10%<br>
                • <em>Result:</em> Perfect 1:1 balance ratio ({b_r1.balance_ratio:.2f}), 12 min wait times, ${(b_r1.platform_net_revenue)/1_000_000:.2f}M Net Revenue.<br><br>
                <strong>Round 2 Allocation:</strong><br>
                • Buyer Spend: $1.10M | Walker Spend: $0.80M | Trust Spend: $0.50M | Take Rate: 15%<br>
                • <em>Result:</em> Cumulative Trust Moat reaches <strong>$0.95M</strong>, slashing Venmo leakage to under 3%! 
                Enterprise Valuation: <strong>${b_sc.enterprise_valuation:.2f}M</strong>.<br><br>
                <strong>Teaching Rationale:</strong><br>
                {benchmark["rationale"]}
            </div>
            """, unsafe_allow_html=True)

        # Admin Actions
        st.markdown("---")
        st.markdown("### 🛠️ Classroom Management")
        del_col1, del_col2 = st.columns(2)
        with del_col1:
            st.markdown("#### Delete Individual Entry")
            df_full = leaderboard.get_leaderboard_dataframe()
            if not df_full.empty:
                student_to_delete = st.selectbox("Select student to remove", options=df_full["Founder"].tolist())
                if st.button("🗑️ Delete Selected Student", type="secondary"):
                    leaderboard.delete_player(student_to_delete)
                    st.success(f"Removed {student_to_delete} from leaderboard.")
                    st.rerun()
            else:
                st.caption("No entries to remove.")

        with del_col2:
            st.markdown("#### Reset Entire Leaderboard")
            st.caption("Wipes all student records for the next class section.")
            if st.button("⚠️ Clear Leaderboard for New Class", type="primary"):
                leaderboard.reset_leaderboard()
                st.success("Leaderboard cleared successfully!")
                st.rerun()

    elif instructor_pin:
        st.error("Incorrect PIN. Please re-enter or check your environment configuration.")
