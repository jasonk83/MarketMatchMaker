# 🐾 The Marketplace Matchmaker

An interactive, two-sided platform economics simulation built in **Streamlit** for undergraduate IT, business, and computer science students.

Students step into the shoes of venture-backed founders launching a peer-to-peer **Dog Walking Marketplace** with **$5.0M in seed capital**, confronting the classic challenges of modern digital platform strategy across a 2-Round challenge.

---

## 🎯 Core Pedagogical Concepts

1. **Two-Sided Network Effects & The Chicken-or-Egg Problem**:
   - Buyers (dog owners) require supply density; suppliers (dog walkers) require demand liquidity.
   - Operating capacity: **1 active dog walker services up to 8 dog owners** (32 walks/month).
   - *Lopsided spend triggers severe failure*: **Demand Overload** causes 90+ min wait times and customer churn; **Supply Starvation** leaves walkers idle, causing income starvation churn.

2. **Customer Acquisition Costs (CAC) & Saturation**:
   - Concave diminishing returns: aggressive single-round spend inflates CAC (base CAC ~$60 for dog owners, ~$350 for dog walkers).

3. **Multi-Homing Friction & Rival Poaching**:
   - In Round 2, VC-backed rival **"BarkBuddy"** enters with an aggressive **12% Take Rate**.
   - Setting a 20%–25% take rate causes an exodus of walkers who multi-home and defect to the cheaper competitor.

4. **Platform Governance & Disintermediation (Off-Platform Leakage)**:
   - Repeat buyers and walkers are tempted to exchange numbers and pay via **Venmo** off-app to bypass commissions.
   - **Platform Governance & Trust Spend** builds the only defensible lock-in: dog owners refuse to risk off-app transactions without the platform's **$25,000 Pet Emergency Guarantee**, live GPS route tracking, and automated dispute resolution.

5. **Composite Index Scoring (0–100)**:
   - Equal 1/3 weight across **Marketplace Liquidity %**, **Retention Rate %**, and **Enterprise Valuation ($M)**.
   - Hoarding cash without building liquidity is penalized (at most 3.3/100 Composite Score), rewarding sustainable capital efficiency.

---

## 🏗️ Architecture & File Structure

```
Surge!_ClassDemo/
├── app.py                     # Streamlit frontend with Player Console & Live Leaderboard
├── simulation.py              # Pure Python two-sided platform economic engine
├── leaderboard.py             # SQLite persistence, session recovery, and class analytics
├── test_simulation.py         # Automated test suite for economic model invariants
├── test_leaderboard.py        # Automated test suite for SQLite state persistence
├── requirements.txt           # Python dependencies for Streamlit Cloud
├── .streamlit/
│   └── config.toml            # High-contrast theme & server settings
├── MARKETPLACE_MATCHMAKER_PLAN.md # Strategic design specification
└── README.md                  # Documentation and deployment guide
```

---

## 🚀 Running the App Locally

### 1. Prerequisites
- Python 3.10+
- `pip` or virtual environment

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Streamlit
```bash
streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## ☁️ Deploying to Streamlit Community Cloud

1. Push this repository to GitHub:
   ```bash
   git init
   git add .
   git commit -m "feat: complete Marketplace Matchmaker simulation"
   git remote add origin https://github.com/<your-username>/<repo-name>.git
   git push -u origin main
   ```
2. Log into [share.streamlit.io](https://share.streamlit.io).
3. Click **"New App"**, select this repository and branch (`main`), and set the main file path to `app.py`.
4. (Optional) Set the instructor PIN in **App Settings > Secrets**:
   ```toml
   INSTRUCTOR_PIN = "2026"
   ```
5. Click **"Deploy"**. The app will be live and ready for classroom use!

---

## 🎓 Instructor Guide & Classroom Flow

### Recommended Session Schedule (40–50 minutes):
1. **Introduction & Registration (5 mins)**:
   - Direct students to the app URL.
   - Project the **🏆 Live Class Leaderboard** on the classroom screen.
   - Students enter their First Name and Company Name to claim their $5.0M seed capital (`⏳ In Round 1`).
2. **Round 1 Gameplay (10 mins)**:
   - Students allocate Round 1 budgets across Buyer, Supplier, and Trust levers and choose their Take Rate.
   - Real-time leaderboard updates to `🟡 In Round 2` as students submit.
3. **Round 2 Crisis Briefing & Submission (10 mins)**:
   - The market crisis hits: Rival *BarkBuddy* (12% commission) launches and Venmo disintermediation begins.
   - Students allocate remaining cash and lock their final attempt (`✅ Completed`).
4. **Instructor Debrief (15–20 mins)**:
   - The instructor enters the PIN (`2026` by default) under the **Live Class Leaderboard** tab.
   - Review class-wide analytics: percentage of students who suffered Demand Overload vs Supply Starvation, average take rates, and total GMV lost to Venmo.
   - Toggle the **"Optimal Benchmark Strategy Reveal"** to reveal the **2:1 Spend Rule** and how cumulative trust creates unbeatable defensibility.
   - Use the **Classroom Management** tools to clear the leaderboard for the next section.
