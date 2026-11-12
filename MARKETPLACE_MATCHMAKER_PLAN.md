# Implementation Plan — "The Marketplace Matchmaker" (Streamlit Simulation)

## Goal Description
Build a standalone, interactive web simulation in **Streamlit** for an undergraduate IT class: **"The Marketplace Matchmaker"**. Students step into the role of founders launching their own peer-to-peer **Dog Walking Marketplace** with **$5.0M in seed capital**, navigating a **2-Round strategic challenge** designed to teach:
- **Two-Sided Network Effects & The Chicken-or-Egg Problem**
- **Fragmentation Reduction & Hyper-Local Marketplace Liquidity**
- **Customer Acquisition Costs (CAC) & Diminishing Returns**
- **Multi-Homing Friction & Disintermediation (Off-Platform Leakage)**

The project will be initialized as a clean Git repository ready for instant deployment to **Streamlit Community Cloud**.

```mermaid
flowchart TD
    Setup["Founder Onboarding: Enter First Name + Dog-Walking Company Name ($5M Seed)"] -->|Registers '⏳ In Round 1' on Live Leaderboard| R1["Round 1: The Liquidity Crisis (Cold Start)"]
    R1 -->|Blind Commit: 3 Spend Sliders + 5 Take Rate Tiers| EngineR1["Round 1 Economic Engine"]
    EngineR1 -->|Updates Badge to '🟡 In Round 2' & Carries Over Cash + Net Rev| ReportR1["Round 1 Diagnostic Report"]
    ReportR1 --> R2["Round 2: The Multi-Homing & Disintermediation Threat"]
    R2 -->|Crisis Briefing: Rival 'BarkBuddy' + Off-App Venmo Leakage| EngineR2["Round 2 Economic Engine"]
    EngineR2 -->|Locks Single Attempt ('✅ Completed')| FinalScore["Final Scorecard (0-100 Composite Index)"]
    FinalScore -->|3s Auto-Refresh| Leaderboard["Live Class Leaderboard & PIN-Protected ('2026') Instructor Debrief"]
```

---

## Core Gameplay & Economic Mechanics

### 1. Founder Onboarding & Standardized Scenario
- **Founder Identity**: At the start of the game, each student enters:
  1. **First Name** (e.g., *Jordan*)
  2. **Dog-Walking Company Name** (e.g., *ZoomieWalks*, *Bark Avenue*, *PawPath*)
  - Both **First Name** and **Company Name** immediately register on the **Live Class Leaderboard** with status `⏳ In Round 1`.
- **Session Recovery & Strict Single Attempt**:
  - Progress is persisted in the shared SQLite/in-memory store keyed by normalized **First Name**.
  - If a student accidentally refreshes their browser mid-game (e.g., during Round 2), re-entering their First Name automatically restores their exact state and company name so they can finish.
  - Once Round 2 is submitted (`✅ Completed`), their attempt is permanently locked—re-entering their First Name displays their locked Final Scorecard rather than allowing a replay.
- **Seed Capital & Carryover Rules**:
  - Students start **Round 1** with **$5.0M** in seed funding.
  - **Available Cash in Round 2** = `($5.0M - Round 1 Total Spend) + Round 1 Platform Net Revenue`.
  - If a student sets Round 1 total spend above **$3.5M**, a prominent warning alerts them that they risk entering Round 2 under-capitalized.

---

### 2. Capital Allocation Levers (Per Round — Pure Quantitative Controls)
Students control **3 quantitative budget sliders** (`$0.0M` to available cash, in `$50k` increments) and **1 discrete Take Rate selector**:

| Lever | Control Type | What It Funds | Economic Impact in Model |
| :--- | :--- | :--- | :--- |
| **1. Buyer Acquisition (Dog Owners)** | Slider (`$0M – Available`) | First-walk subsidies, discount coupons, local digital ad blitzes | Acquires dog owners with diminishing marginal returns (`CAC_buyer` rises at high spend). Also defends buyer retention in Round 2. |
| **2. Supplier Acquisition (Dog Walkers)** | Slider (`$0M – Available`) | Guaranteed minimum hourly earnings, onboarding bonuses, free background checks | Acquires active dog walkers (`CAC_walker` rises with scale). Each active walker can serve up to **8 regular dog owners** (32 walks/mo). |
| **3. Platform Governance & Trust** | Slider (`$0M – Available`) | Dispute mediation, $25k pet insurance pools, automated ID verification, GPS walk tracking | Boosts booking conversion & trust in Round 1; creates **switching friction & platform lock-in** in Round 2 (owners won't risk Venmo off-app if they lose the $25k pet insurance & GPS tracker). |
| **4. Take Rate / Commission** | 5 Discrete Tiers (`5%`, `10%`, `15%`, `20%`, `25%`) | Platform fee deducted from each $30 walk transaction | Directly determines Net Revenue (`GMV × Take Rate`). However, `20%` and `25%` squeeze walker earnings and trigger heavy **Multi-Homing** and **Venmo Disintermediation** in Round 2. |

---

### 3. Round-by-Round Simulation Math (`simulation.py`)

#### Round 1: The Liquidity Crisis (Chicken-or-Egg Launch)
- **Raw Acquisition**:
  - `Owners Acquired_1 = f(Buyer Spend_1)` with concave saturation (base CAC ~$60, rising with aggressive single-round spend).
  - `Walkers Acquired_1 = g(Supplier Spend_1)` with concave saturation (base CAC ~$350, modified negatively if Take Rate >= 20%).
- **Supply-to-Demand Balance Ratio (`R_1`)**:
  - Optimal capacity is **1 Walker per 8 Dog Owners** (`Walker Capacity = Walkers × 8`).
  - **Case A — Demand Overload (`Owners > Walker Capacity`)**:
    - Unmatched owners face long wait times (up to 90+ mins) and unfulfilled walk requests.
    - **Owner Liquidity Churn** spikes proportionally to the shortage.
  - **Case B — Supply Starvation (`Walker Capacity > Owners`)**:
    - Walkers sit idle with empty schedules and low earnings.
    - **Walker Starvation Churn** spikes proportionally to excess idle capacity.
- **Trust Gate**:
  - Adequate **Governance & Trust Spend** verifies walkers and reassures dog owners. Underfunding Trust reduces match conversion and causes safety-incident churn.
- **Round 1 Output**:
  - Retains surviving Owners & Walkers into Round 2, updates leaderboard status to `🟡 In Round 2`, and adds **Round 1 Net Revenue** to unspent seed cash for Round 2.

#### Round 2: The Multi-Homing & Disintermediation Threat
At the start of Round 2, students receive a standardized **Market Crisis Briefing**:
1. **Rival Entry ("BarkBuddy")**: A well-funded VC rival launches in the city with a `12%` take rate and aggressive walker poaching bonuses.
2. **Off-Platform Leakage ("The Venmo Temptation")**: Repeat dog owners and walkers who matched in Round 1 are tempted to text each other directly and pay via Venmo to bypass the platform fee.

- **Multi-Homing Defection Rate**:
  - Spikes if the student's **Round 2 Take Rate** exceeds BarkBuddy's (`20%` or `25%`) and if Round 2 Buyer/Supplier retention budgets are underfunded.
- **Disintermediation (Off-Platform Venmo Leakage) Rate**:
  - Driven by the interaction between **Take Rate** and **Cumulative Governance & Trust Spend**:
    - High Take Rate (`20%–25%`) creates a strong financial incentive to move off-app.
    - High **Governance & Trust Spend** (pet insurance guarantees, automated scheduling/billing, GPS walk tracking, dispute protection) suppresses disintermediation because both sides value the platform's protection more than the commission savings.

---

### 4. Scoring & Ranking System (`0–100 Composite Index`)
At the end of Round 2, students are evaluated on three core KPIs that combine with **equal weight (1/3 each)** into a **0–100 Composite Index Score**:

1. **Marketplace Liquidity (%)** *(33.3% weight)*:
   - Percentage of potential walk demand successfully matched with verified walkers without excessive wait times (`0–100`).
2. **Retention Rate (%)** *(33.3% weight)*:
   - Combined survival & loyalty rate of acquired Dog Owners and Walkers after accounting for liquidity churn, rival multi-homing losses, and off-app Venmo disintermediation (`0–100`).
3. **Enterprise Valuation ($M — Normalized 0–100 Score)** *(33.3% weight)*:
   - Includes **100% of Unspent Cash on Hand** plus **Operating Platform Value**:
     `Enterprise Valuation ($M) = Unspent Cash Remaining + (Round 2 Annualized Net Revenue × Quality Multiple)`
   - Where `Quality Multiple` scales with Liquidity %, Retention %, and Trust Moat.
   - Normalized against a $50M benchmark ceiling (`min(100, (Valuation / $50M) × 100)`). Because Valuation is 1/3 of the Composite Score and unspent cash alone is at most $5M (10/100 on Valuation, 0 on Liquidity, 0 on Retention = 3.3/100 Composite Score), hoarding cash is naturally penalized while prudent capital efficiency is rewarded.

`Composite Score (0–100) = (Liquidity Score + Retention Score + Valuation Score) / 3`

---

## Proposed File Structure

### 1. `simulation.py`
- Pure Python economic engine implementing:
  - `simulate_round_1(buyer_spend, supplier_spend, trust_spend, take_rate)`
  - `simulate_round_2(r1_result, buyer_spend, supplier_spend, trust_spend, take_rate)`
  - `compute_final_scores(r1_result, r2_result)`
  - `get_optimal_benchmark()` for the Instructor Debrief reveal.
  - Personalized diagnostic feedback generator explaining the exact causes of a student's results.

### 2. `leaderboard.py`
- Thread-safe shared persistence using `@st.cache_resource` + local SQLite database (`/tmp/marketplace_matchmaker.db`).
- Stores `first_name`, `company_name`, `status` (`In Round 1`, `In Round 2`, `Completed`), Round 1 & Round 2 decisions, Liquidity %, Retention %, Enterprise Valuation ($M), and Composite Score (0–100).
- Supports automatic session recovery by `first_name`, individual row deletion by the instructor, and full leaderboard reset.

### 3. `app.py`
- Main Streamlit application with two top-level navigation tabs:
  1. **🐾 Launch Your Marketplace (Player Console)**:
     - **Step 0 — Founder Registration**: Input **First Name** and **Dog-Walking Company Name**, view the $5.0M seed briefing, and register onto the live board (`⏳ In Round 1`).
     - **Step 1 — Round 1 Allocation (Blind Commit)**: 3 quantitative budget sliders + 5-tier Take Rate radio selector with strategic tooltips and a warning if Round 1 spend exceeds $3.5M.
     - **Step 2 — Round 1 Diagnostic Report**: Supply Capacity vs. Owner Demand chart, Wait Times, Churn breakdown, Net Revenue earned, and updated Cash Pool for Round 2 (`🟡 In Round 2`).
     - **Step 3 — Round 2 Crisis Briefing & Allocation (Blind Commit)**: Alerts on rival *"BarkBuddy"* and Venmo disintermediation; 3 budget sliders + 5-tier Take Rate selector.
     - **Step 4 — Final Executive Scorecard (`✅ Completed`)**: Headline **0–100 Composite Index Score**, **Marketplace Liquidity %**, **Retention Rate %**, **Enterprise Valuation ($M)** (breaking out Operating Value + Unspent Cash), transaction fate chart (Completed vs. Multi-Homed to Rival vs. Disintermediated to Venmo), and personalized executive debrief.
  2. **🏆 Live Class Leaderboard & Instructor Debrief**:
     - Uses `@st.fragment(run_every="3s")` for seamless **3-second live auto-refresh** on the classroom projector screen.
     - Displays ranked table with **Rank**, **First Name**, **Company Name**, **Status Badge** (`⏳ In Round 1` / `🟡 In Round 2` / `✅ Completed`), **Composite Score (0–100)**, **Liquidity %**, **Retention %**, **Enterprise Valuation ($M)**, and **R1/R2 Take Rates**.
     - **PIN-Protected Instructor Panel** (Default PIN: `2026`, overridable via `st.secrets["INSTRUCTOR_PIN"]` or env var):
       - **Class-Wide Mistake & Strategy Analytics**: Shows how many students fell into Demand Overload vs. Supply Starvation in Round 1, average Take Rate chosen, and average GMV lost to Venmo disintermediation in Round 2.
       - **Toggleable "Optimal Benchmark Strategy Reveal"**: Walks the class through the ideal allocation and why `10% -> 15%` take rates + high Governance/Trust spend maximizes long-term platform value.
       - **Admin Management**: Delete individual student/test entries or clear the entire leaderboard for the next class section.

### 4. `requirements.txt`, `.streamlit/config.toml`, & `README.md`
- Dependencies, clean high-contrast UI theme, instructor teaching notes, and GitHub -> Streamlit Community Cloud deployment steps.

---

## Verification Plan

### Automated Verification (`test_simulation.py`)
- Test economic model invariants:
  - Cash hoarding ($0 spend in R1 & R2) yields $5.0M valuation (from unspent cash) but 0% Liquidity and 0% Retention, resulting in a bottom-tier ~3.3/100 Composite Score.
  - Lopsided Buyer spend in R1 triggers **Demand Overload**, high wait times, and low liquidity.
  - Lopsided Supplier spend in R1 triggers **Supply Starvation** and walker churn.
  - `25%` Take Rate in R2 triggers heavy **Multi-Homing** to *BarkBuddy* and **Venmo Disintermediation**, mitigated only partially if Governance & Trust is heavily funded.
  - Balanced strategy achieves `85+` Composite Score.
- Test `leaderboard.py` persistence:
  - Registration creates `⏳ In Round 1` entry with `First Name` and `Company Name`.
  - Refreshing and re-entering `First Name` recovers mid-game state or locked final score.
  - Instructor delete-single-entry and full-reset functions work cleanly.

### Live App Verification
- Run `streamlit run app.py --server.headless=true` in the VM environment and verify zero errors.
- Initialize Git repository with clean commits ready to push to GitHub.
