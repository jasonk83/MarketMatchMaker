"""
simulation.py — Economic Engine for "The Marketplace Matchmaker"
Pure Python simulation of a two-sided dog walking marketplace across 2 rounds.
Models two-sided network effects, chicken-or-egg liquidity, CAC saturation,
multi-homing rivalry, and disintermediation (off-platform leakage).
"""

from dataclasses import dataclass
from typing import Dict, Any, Tuple


WALK_PRICE = 30.0  # standard price per dog walk
WALKS_PER_OWNER_PER_ROUND = 12  # average walks per active owner in a round
BENCHMARK_VALUATION_CEILING = 50.0  # $50M benchmark ceiling for 100/100 score


@dataclass
class Round1Result:
    buyer_spend: float
    supplier_spend: float
    trust_spend: float
    take_rate: float
    
    # Acquisition metrics
    owners_acquired: int
    walkers_acquired: int
    walker_capacity: int
    balance_ratio: float
    state_classification: str  # "DEMAND_OVERLOAD", "SUPPLY_STARVATION", "BALANCED"
    
    # Operating metrics
    avg_wait_time_minutes: int
    owner_churn_rate: float
    walker_churn_rate: float
    safety_incident_rate: float
    trust_gate_passed: bool
    
    # Surviving cohort
    surviving_owners: int
    surviving_walkers: int
    
    # Financial metrics
    matched_walks: int
    gross_merchandise_value: float
    platform_net_revenue: float
    total_spend: float
    cash_end: float
    liquidity_rate: float  # 0.0 to 100.0
    feedback: str = ""


@dataclass
class Round2Result:
    buyer_spend: float
    supplier_spend: float
    trust_spend: float
    take_rate: float
    
    # Starting cohort from R1
    start_owners: int
    start_walkers: int
    available_cash: float
    
    # New acquisition in R2
    new_owners_acquired: int
    new_walkers_acquired: int
    
    # BarkBuddy Rival Threat (Multi-Homing)
    rival_take_rate: float
    walker_defection_rate: float
    walkers_lost_to_rival: int
    
    # Venmo Threat (Disintermediation / Leakage)
    cumulative_trust_spend: float
    trust_moat_strength: float  # 0.0 to 1.0
    venmo_leakage_rate: float
    walks_lost_to_venmo: int
    gmv_lost_to_venmo: float
    
    # Final active network
    active_owners: int
    active_walkers: int
    walker_capacity: int
    balance_ratio: float
    state_classification: str
    
    # Operations and Financials
    potential_walks: int
    completed_walks: int
    gross_merchandise_value: float
    platform_net_revenue: float
    total_spend: float
    cash_remaining: float
    liquidity_rate: float
    retention_rate: float


@dataclass
class FinalScorecard:
    composite_score: float  # 0.0 to 100.0
    liquidity_score: float  # 0.0 to 100.0
    retention_score: float  # 0.0 to 100.0
    valuation_score: float  # 0.0 to 100.0
    
    enterprise_valuation: float  # In Millions ($M)
    operating_valuation: float  # In Millions ($M)
    cash_remaining: float  # In Millions ($M)
    annualized_net_revenue: float  # In Millions ($M)
    quality_multiple: float
    
    # Transaction fate counts
    completed_walks: int
    walks_lost_to_leakage: int
    walks_unmatched: int
    
    # Pedagogical feedback
    feedback_r1: str
    feedback_r2: str
    overall_debrief: str


def simulate_round_1(
    buyer_spend: float,
    supplier_spend: float,
    trust_spend: float,
    take_rate: float,
    seed_capital: float = 5_000_000.0,
) -> Round1Result:
    """
    Simulates Round 1: The Liquidity Crisis (Cold Start / Chicken-or-Egg).
    """
    total_spend = buyer_spend + supplier_spend + trust_spend
    # Cap total spend to available seed capital
    if total_spend > seed_capital:
        # Scale proportionally if somehow overspent
        scale = seed_capital / total_spend
        buyer_spend *= scale
        supplier_spend *= scale
        trust_spend *= scale
        total_spend = seed_capital

    # 1. Buyer (Dog Owner) Acquisition with concave saturation
    # Base CAC ~$60, rising with single-round aggressive spend
    if buyer_spend > 0:
        cac_buyer = 60.0 * (1.0 + 0.55 * (buyer_spend / 1_500_000.0) ** 1.2)
        owners_acquired = int(buyer_spend / cac_buyer)
    else:
        cac_buyer = 60.0
        owners_acquired = 0

    # 2. Supplier (Dog Walker) Acquisition with concave saturation & take-rate sensitivity
    # Base CAC ~$350; walkers are sensitive to take rates during launch
    if supplier_spend > 0:
        cac_walker = 350.0 * (1.0 + 0.50 * (supplier_spend / 800_000.0) ** 1.2)
        take_rate_modifier = (
            1.10 if take_rate <= 0.10
            else (1.00 if take_rate <= 0.15
            else (0.85 if take_rate <= 0.20 else 0.70))
        )
        walkers_acquired = int((supplier_spend / cac_walker) * take_rate_modifier)
    else:
        cac_walker = 350.0
        walkers_acquired = 0

    # 3. Supply-to-Demand Balance Ratio (Optimal is 1 Walker per 8 Dog Owners)
    walker_capacity = walkers_acquired * 8
    
    if owners_acquired == 0 and walker_capacity == 0:
        balance_ratio = 1.0
        state = "BALANCED"
        avg_wait_time = 15
        owner_churn = 1.0
        walker_churn = 1.0
    elif walker_capacity == 0:
        balance_ratio = 0.0
        state = "DEMAND_OVERLOAD"
        avg_wait_time = 90
        owner_churn = 0.85
        walker_churn = 0.0
    elif owners_acquired == 0:
        balance_ratio = 99.0
        state = "SUPPLY_STARVATION"
        avg_wait_time = 5
        owner_churn = 0.0
        walker_churn = 0.85
    else:
        balance_ratio = round(walker_capacity / owners_acquired, 3)
        if balance_ratio < 0.88:
            state = "DEMAND_OVERLOAD"
            shortage = (owners_acquired - walker_capacity) / owners_acquired
            avg_wait_time = int(12 + shortage * 80)
            owner_churn = min(0.70, 0.10 + 0.65 * shortage)
            walker_churn = 0.05
        elif balance_ratio > 1.15:
            state = "SUPPLY_STARVATION"
            idle_ratio = (walker_capacity - owners_acquired) / walker_capacity
            avg_wait_time = max(5, int(12 - idle_ratio * 7))
            owner_churn = 0.08
            walker_churn = min(0.70, 0.08 + 0.65 * idle_ratio)
        else:
            state = "BALANCED"
            avg_wait_time = 12
            owner_churn = 0.06
            walker_churn = 0.06

    # 4. Platform Governance & Trust Gate
    # Adequate trust spend ($300k+) provides background checks, $25k insurance, GPS
    if trust_spend < 150_000.0:
        trust_gate_passed = False
        safety_incident_rate = 0.08 * (1.0 - (trust_spend / 150_000.0))
        trust_conversion_factor = max(0.40, 0.50 + 0.50 * (trust_spend / 150_000.0))
        owner_churn = min(0.85, owner_churn + 0.15)
    else:
        trust_gate_passed = True
        safety_incident_rate = 0.005
        trust_conversion_factor = 1.0

    # 5. Surviving Cohort
    surviving_owners = int(owners_acquired * (1.0 - owner_churn))
    surviving_walkers = int(walkers_acquired * (1.0 - walker_churn))

    # 6. Walk Matching and Financials
    max_serviceable_owners = min(surviving_owners, surviving_walkers * 8)
    potential_total_walks = owners_acquired * WALKS_PER_OWNER_PER_ROUND
    matched_walks = int(max_serviceable_owners * WALKS_PER_OWNER_PER_ROUND * trust_conversion_factor)
    
    gmv = matched_walks * WALK_PRICE
    net_revenue = gmv * take_rate
    cash_end = max(0.0, (seed_capital - total_spend) + net_revenue)

    # Liquidity % in Round 1
    if potential_total_walks > 0:
        liquidity_rate = round(min(100.0, (matched_walks / potential_total_walks) * 100.0), 1)
    else:
        liquidity_rate = 0.0

    res = Round1Result(
        buyer_spend=buyer_spend,
        supplier_spend=supplier_spend,
        trust_spend=trust_spend,
        take_rate=take_rate,
        owners_acquired=owners_acquired,
        walkers_acquired=walkers_acquired,
        walker_capacity=walker_capacity,
        balance_ratio=balance_ratio,
        state_classification=state,
        avg_wait_time_minutes=avg_wait_time,
        owner_churn_rate=round(owner_churn, 3),
        walker_churn_rate=round(walker_churn, 3),
        safety_incident_rate=round(safety_incident_rate, 4),
        trust_gate_passed=trust_gate_passed,
        surviving_owners=surviving_owners,
        surviving_walkers=surviving_walkers,
        matched_walks=matched_walks,
        gross_merchandise_value=gmv,
        platform_net_revenue=net_revenue,
        total_spend=total_spend,
        cash_end=cash_end,
        liquidity_rate=liquidity_rate,
    )
    res.feedback = _generate_r1_feedback(res)
    return res


def simulate_round_2(
    r1: Round1Result,
    buyer_spend: float,
    supplier_spend: float,
    trust_spend: float,
    take_rate: float,
) -> Round2Result:
    """
    Simulates Round 2: The Multi-Homing & Disintermediation Threat.
    Incorporates rival 'BarkBuddy' (12% take rate) and off-platform Venmo leakage.
    """
    available_cash = r1.cash_end
    total_spend = buyer_spend + supplier_spend + trust_spend
    if total_spend > available_cash and available_cash > 0:
        scale = available_cash / total_spend
        buyer_spend *= scale
        supplier_spend *= scale
        trust_spend *= scale
        total_spend = available_cash

    # 1. Cumulative Trust Spend & Trust Moat
    cumulative_trust = r1.trust_spend + trust_spend
    # Trust moat suppresses off-platform leakage: $800k+ cumulative achieves near max protection
    trust_moat_strength = min(0.90, cumulative_trust / 850_000.0)

    # 2. Round 2 Buyer Acquisition and Retention
    # 70% of spend goes to new owner growth, 30% reinforces existing retention
    cac_buyer_r2 = 65.0 * (1.0 + 0.60 * (buyer_spend / 1_500_000.0) ** 1.2)
    new_owners = int((buyer_spend * 0.70) / cac_buyer_r2) if buyer_spend > 0 else 0
    buyer_retention_budget = buyer_spend * 0.30
    buyer_retention_defense = min(0.15, buyer_retention_budget / 400_000.0)
    base_owner_retention = 0.82 + buyer_retention_defense
    retained_owners = int(r1.surviving_owners * min(0.95, base_owner_retention))

    # 3. Round 2 Supplier Acquisition and Retention
    cac_walker_r2 = 380.0 * (1.0 + 0.55 * (supplier_spend / 800_000.0) ** 1.2)
    take_rate_supplier_mod = (
        1.10 if take_rate <= 0.10
        else (1.00 if take_rate <= 0.15
        else (0.85 if take_rate <= 0.20 else 0.70))
    )
    new_walkers = int(((supplier_spend * 0.65) / cac_walker_r2) * take_rate_supplier_mod) if supplier_spend > 0 else 0
    walker_retention_budget = supplier_spend * 0.35
    walker_retention_defense = min(0.20, walker_retention_budget / 450_000.0)

    # 4. Threat 1: Rival 'BarkBuddy' Defection (Multi-Homing)
    # BarkBuddy take rate is 12%
    rival_take_rate = 0.12
    if take_rate <= 0.05:
        base_defection = 0.01  # We undercut BarkBuddy! Walkers stay and defect to us
    elif take_rate <= 0.10:
        base_defection = 0.04  # Still cheaper than BarkBuddy
    elif take_rate <= 0.15:
        base_defection = 0.15  # Slightly higher than BarkBuddy
    elif take_rate <= 0.20:
        base_defection = 0.35  # Squeezing walkers -> high multi-homing defection
    else:  # 0.25
        base_defection = 0.52  # Aggressive 25% take rate causes massive walker mutiny

    # Retention spend mitigates defection
    walker_defection_rate = max(0.02, base_defection * (1.0 - walker_retention_defense))
    
    total_pre_defection_walkers = r1.surviving_walkers + new_walkers
    walkers_lost_to_rival = int(total_pre_defection_walkers * walker_defection_rate)
    active_walkers = max(0, total_pre_defection_walkers - walkers_lost_to_rival)

    # 5. Threat 2: Off-Platform Venmo Disintermediation (Leakage)
    # Commission avoidance incentive vs. Platform Trust Moat
    if take_rate <= 0.05:
        base_leakage_incentive = 0.04
    elif take_rate <= 0.10:
        base_leakage_incentive = 0.09
    elif take_rate <= 0.15:
        base_leakage_incentive = 0.18
    elif take_rate <= 0.20:
        base_leakage_incentive = 0.38
    else:  # 0.25
        base_leakage_incentive = 0.55

    # Trust moat (insurance, GPS, replacement guarantee) sharply suppresses leakage
    venmo_leakage_rate = max(0.02, base_leakage_incentive * (1.0 - trust_moat_strength * 0.88))

    # Active customer network
    active_owners = retained_owners + new_owners
    walker_capacity = active_walkers * 8

    # Balance classification in R2
    if active_owners == 0 and walker_capacity == 0:
        balance_ratio = 1.0
        state = "BALANCED"
    elif walker_capacity == 0:
        balance_ratio = 0.0
        state = "DEMAND_OVERLOAD"
    elif active_owners == 0:
        balance_ratio = 99.0
        state = "SUPPLY_STARVATION"
    else:
        balance_ratio = round(walker_capacity / active_owners, 3)
        if balance_ratio < 0.88:
            state = "DEMAND_OVERLOAD"
        elif balance_ratio > 1.15:
            state = "SUPPLY_STARVATION"
        else:
            state = "BALANCED"

    # 6. Walk Matching & Leakage Fate
    max_serviceable_owners = min(active_owners, walker_capacity)
    potential_walks = max_serviceable_owners * WALKS_PER_OWNER_PER_ROUND
    
    walks_lost_to_venmo = int(potential_walks * venmo_leakage_rate)
    completed_walks = max(0, potential_walks - walks_lost_to_venmo)
    
    gmv_lost_to_venmo = walks_lost_to_venmo * WALK_PRICE
    gmv_completed = completed_walks * WALK_PRICE
    platform_net_revenue = gmv_completed * take_rate
    
    cash_remaining = max(0.0, (available_cash - total_spend) + platform_net_revenue)

    # R2 Liquidity Rate: completed walks / (active_owners * 12)
    total_owner_demand_walks = active_owners * WALKS_PER_OWNER_PER_ROUND
    if total_owner_demand_walks > 0:
        liquidity_rate = round(min(100.0, (completed_walks / total_owner_demand_walks) * 100.0), 1)
    else:
        liquidity_rate = 0.0

    # R2 Retention Rate: surviving participants vs acquired across lifetime
    total_acquired_owners = r1.owners_acquired + new_owners
    total_acquired_walkers = r1.walkers_acquired + new_walkers
    total_acquired = total_acquired_owners + total_acquired_walkers
    total_surviving = active_owners + active_walkers
    
    if total_acquired > 0:
        retention_rate = round(min(100.0, (total_surviving / total_acquired) * 100.0), 1)
    else:
        retention_rate = 0.0

    return Round2Result(
        buyer_spend=buyer_spend,
        supplier_spend=supplier_spend,
        trust_spend=trust_spend,
        take_rate=take_rate,
        start_owners=r1.surviving_owners,
        start_walkers=r1.surviving_walkers,
        available_cash=available_cash,
        new_owners_acquired=new_owners,
        new_walkers_acquired=new_walkers,
        rival_take_rate=rival_take_rate,
        walker_defection_rate=round(walker_defection_rate, 3),
        walkers_lost_to_rival=walkers_lost_to_rival,
        cumulative_trust_spend=cumulative_trust,
        trust_moat_strength=round(trust_moat_strength, 3),
        venmo_leakage_rate=round(venmo_leakage_rate, 3),
        walks_lost_to_venmo=walks_lost_to_venmo,
        gmv_lost_to_venmo=gmv_lost_to_venmo,
        active_owners=active_owners,
        active_walkers=active_walkers,
        walker_capacity=walker_capacity,
        balance_ratio=balance_ratio,
        state_classification=state,
        potential_walks=potential_walks,
        completed_walks=completed_walks,
        gross_merchandise_value=gmv_completed,
        platform_net_revenue=platform_net_revenue,
        total_spend=total_spend,
        cash_remaining=cash_remaining,
        liquidity_rate=liquidity_rate,
        retention_rate=retention_rate,
    )


def compute_final_scores(r1: Round1Result, r2: Round2Result) -> FinalScorecard:
    """
    Computes the 0–100 Composite Index Score across:
    1. Marketplace Liquidity % (33.3%)
    2. Retention Rate % (33.3%)
    3. Enterprise Valuation ($M normalized to 0-100) (33.3%)
    """
    # 1. Composite Liquidity Score (weighted across R1 and R2)
    liquidity_score = round(0.40 * r1.liquidity_rate + 0.60 * r2.liquidity_rate, 1)

    # 2. Retention Score
    retention_score = r2.retention_rate

    # 3. Enterprise Valuation ($M)
    # Annualized Net Revenue = R2 Net Revenue * 4.0 (quarterly round annualized to 4 quarters)
    annualized_net_rev_m = (r2.platform_net_revenue * 4.0) / 1_000_000.0
    cash_remaining_m = r2.cash_remaining / 1_000_000.0

    # Quality Multiple scales with liquidity, retention, and trust moat
    # Range: 5.0x to 16.0x for top-tier marketplace benchmarks
    if r2.completed_walks > 0:
        base_multiple = 11.5
        quality_multiple = round(
            base_multiple
            * (liquidity_score / 100.0)
            * (retention_score / 100.0)
            * (1.0 + r2.trust_moat_strength * 0.40),
            2
        )
        operating_valuation_m = round(annualized_net_rev_m * quality_multiple, 2)
    else:
        quality_multiple = 0.0
        operating_valuation_m = 0.0

    enterprise_valuation_m = round(cash_remaining_m + operating_valuation_m, 2)

    # Valuation Score normalized against $50M ceiling
    valuation_score = round(min(100.0, max(0.0, (enterprise_valuation_m / BENCHMARK_VALUATION_CEILING) * 100.0)), 1)

    # Composite Index (0–100)
    composite_score = round((liquidity_score + retention_score + valuation_score) / 3.0, 1)

    # Transaction fates
    completed_walks = r2.completed_walks
    walks_lost_to_leakage = r2.walks_lost_to_venmo
    potential_total_demand = r2.active_owners * WALKS_PER_OWNER_PER_ROUND
    walks_unmatched = max(0, potential_total_demand - (completed_walks + walks_lost_to_leakage))

    # Diagnostic feedback generation
    feedback_r1 = _generate_r1_feedback(r1)
    feedback_r2 = _generate_r2_feedback(r2)
    overall_debrief = _generate_overall_debrief(composite_score, liquidity_score, retention_score, valuation_score, r1, r2)

    return FinalScorecard(
        composite_score=composite_score,
        liquidity_score=liquidity_score,
        retention_score=retention_score,
        valuation_score=valuation_score,
        enterprise_valuation=enterprise_valuation_m,
        operating_valuation=operating_valuation_m,
        cash_remaining=cash_remaining_m,
        annualized_net_revenue=annualized_net_rev_m,
        quality_multiple=quality_multiple,
        completed_walks=completed_walks,
        walks_lost_to_leakage=walks_lost_to_leakage,
        walks_unmatched=walks_unmatched,
        feedback_r1=feedback_r1,
        feedback_r2=feedback_r2,
        overall_debrief=overall_debrief,
    )


def _generate_r1_feedback(r1: Round1Result) -> str:
    parts = []
    if r1.state_classification == "DEMAND_OVERLOAD":
        parts.append(
            f"⚠️ **Demand Overload**: You acquired {r1.owners_acquired:,} owners but only {r1.walker_capacity:,} walker capacity. "
            f"Average wait times surged to {r1.avg_wait_time_minutes} minutes, causing {int(r1.owner_churn_rate*100)}% owner churn."
        )
    elif r1.state_classification == "SUPPLY_STARVATION":
        parts.append(
            f"⚠️ **Supply Starvation**: You recruited {r1.walkers_acquired:,} walkers ({r1.walker_capacity:,} capacity) for only {r1.owners_acquired:,} owners. "
            f"Idle walkers lacked bookings, causing {int(r1.walker_churn_rate*100)}% walker churn."
        )
    else:
        parts.append(
            f"✅ **Hyper-Local Liquidity Synchronized**: Your supply-to-demand ratio ({r1.balance_ratio:.2f}) was in the optimal zone (1 walker per 8 owners). "
            f"Wait times stayed swift (~{r1.avg_wait_time_minutes}m) with minimal churn."
        )

    if not r1.trust_gate_passed:
        parts.append(
            f"❌ **Trust Deficit**: Trust spend of ${r1.trust_spend:,.0f} fell below the $150k safety threshold. "
            f"Unvetted walkers triggered safety concerns ({r1.safety_incident_rate*100:.1f}% incident rate) and suppressed booking conversion."
        )
    else:
        parts.append("🛡️ **Trust Gate Cleared**: Automated verification and $25k pet guarantees reassured dog owners and unlocked high conversion.")

    return "\n\n".join(parts)


def _generate_r2_feedback(r2: Round2Result) -> str:
    parts = []
    # Rival Multi-homing feedback
    if r2.take_rate >= 0.20:
        parts.append(
            f"🚨 **Rival Exploitation**: Your high take rate ({int(r2.take_rate*100)}%) severely squeezed walker margins compared to BarkBuddy's 12%. "
            f"You lost {r2.walkers_lost_to_rival:,} walkers ({int(r2.walker_defection_rate*100)}% defection rate) to the rival platform."
        )
    elif r2.take_rate <= 0.10:
        parts.append(
            f"🛡️ **Competitive Pricing Shield**: Your {int(r2.take_rate*100)}% take rate undercut BarkBuddy (12%), defending walker loyalty."
        )
    else:
        parts.append(
            f"⚖️ **Balanced Commission**: A 15% take rate remained viable alongside BarkBuddy with moderate retention spend."
        )

    # Disintermediation / Venmo feedback
    if r2.venmo_leakage_rate > 0.20:
        parts.append(
            f"💸 **Heavy Venmo Disintermediation**: Due to high take rates and insufficient trust lock-in, {int(r2.venmo_leakage_rate*100)}% of matches bypassed your platform via Venmo. "
            f"You leaked ${r2.gmv_lost_to_venmo:,.0f} in GMV off-app."
        )
    elif r2.trust_moat_strength > 0.70:
        parts.append(
            f"🔒 **Strong Platform Moat**: Cumulative trust investments (${r2.cumulative_trust_spend:,.0f}) locked users onto your platform. "
            f"Dog owners refused to risk off-app Venmo transactions without your GPS tracking and $25k pet insurance."
        )
    else:
        parts.append(
            f"ℹ️ **Moderate Off-Platform Leakage**: {int(r2.venmo_leakage_rate*100)}% of transactions took place off-app via Venmo."
        )

    return "\n\n".join(parts)


def _generate_overall_debrief(
    composite: float,
    liquidity: float,
    retention: float,
    valuation: float,
    r1: Round1Result,
    r2: Round2Result,
) -> str:
    if composite >= 80.0:
        grade = "🏆 Exceptional Marketplace Strategist"
        summary = (
            "You mastered the two-sided chicken-or-egg problem, balanced supply and demand with discipline, "
            "and constructed a defensible trust moat that repelled both rival poaching and Venmo disintermediation."
        )
    elif composite >= 60.0:
        grade = "📈 Solid Operator with Strategic Vulnerabilities"
        summary = (
            "You successfully built marketplace scale, but either took on excessive commission friction, "
            "suffered from localized liquidity imbalances, or left margins exposed to off-platform leakage."
        )
    elif composite >= 35.0:
        grade = "⚠️ Vulnerable Marketplace Under Stress"
        summary = (
            "Your marketplace experienced significant friction: either severe chicken-or-egg mismatches, "
            "high churn from long wait times, or an exodus of walkers and GMV to rival BarkBuddy and Venmo."
        )
    else:
        grade = "🛑 Failed Launch / Capital Misallocation"
        summary = (
            "The platform collapsed under extreme cold-start failure, fatal supply/demand imbalance, "
            "or severe under-capitalization. Review the benchmark strategy to see how balanced capital allocation builds defensibility."
        )

    return f"### {grade}\n\n**Composite Score: {composite:.1f}/100**\n\n{summary}"


def get_optimal_benchmark() -> Dict[str, Any]:
    """
    Returns the optimal pedagogical benchmark strategy for the Instructor Debrief reveal.
    """
    r1 = simulate_round_1(
        buyer_spend=1_200_000.0,
        supplier_spend=750_000.0,
        trust_spend=450_000.0,
        take_rate=0.10,
    )
    r2 = simulate_round_2(
        r1=r1,
        buyer_spend=1_100_000.0,
        supplier_spend=800_000.0,
        trust_spend=500_000.0,
        take_rate=0.15,
    )
    scorecard = compute_final_scores(r1, r2)
    
    return {
        "r1_decisions": {
            "buyer_spend": 1_200_000.0,
            "supplier_spend": 750_000.0,
            "trust_spend": 450_000.0,
            "take_rate": 0.10,
        },
        "r2_decisions": {
            "buyer_spend": 1_100_000.0,
            "supplier_spend": 800_000.0,
            "trust_spend": 500_000.0,
            "take_rate": 0.15,
        },
        "r1_result": r1,
        "r2_result": r2,
        "scorecard": scorecard,
        "rationale": (
            "1. **Synchronized Ratio (2:1 Spend Rule)**: Because 1 walker serves 8 owners and walker CAC ($350) is ~6x buyer CAC ($60), "
            "spending ~$1.2M on buyers and ~$750k on walkers keeps capacity and demand in lockstep (~1:1 ratio), eliminating wait-time and idle churn.\n"
            "2. **Subsidized Cold Start (10% R1 Take Rate)**: Low initial take rate speeds up walker recruitment and builds market liquidity before monetization.\n"
            "3. **Cumulative Trust Moat ($950k across R1 & R2)**: Investing heavily in $25k pet guarantees, automated vetting, and live GPS tracking creates "
            "insurmountable switching friction. Even when raising take rate to 15% in R2, owners and walkers refuse to leave for Venmo or BarkBuddy."
        ),
    }
