"""
leaderboard.py — Shared SQLite Persistence and Session Recovery
Manages the live class leaderboard for "The Marketplace Matchmaker".
Provides session recovery, instructor PIN-protected controls, and class-wide analytics.
"""

import sqlite3
import datetime
from typing import Optional, Dict, Any, List, Tuple
import pandas as pd


DB_PATH = "/tmp/marketplace_matchmaker.db"


def get_db_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DB_PATH) -> None:
    """Initializes the database schema if not already created."""
    conn = get_db_connection(db_path)
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS players (
                normalized_name TEXT PRIMARY KEY,
                first_name TEXT NOT NULL,
                company_name TEXT NOT NULL,
                status TEXT NOT NULL, -- 'In Round 1', 'In Round 2', 'Completed'
                
                -- Round 1 Inputs
                r1_buyer_spend REAL DEFAULT 0.0,
                r1_supplier_spend REAL DEFAULT 0.0,
                r1_trust_spend REAL DEFAULT 0.0,
                r1_take_rate REAL DEFAULT 0.15,
                
                -- Round 1 Metrics
                r1_owners_acquired INTEGER DEFAULT 0,
                r1_walkers_acquired INTEGER DEFAULT 0,
                r1_balance_ratio REAL DEFAULT 1.0,
                r1_state TEXT DEFAULT 'BALANCED',
                r1_liquidity REAL DEFAULT 0.0,
                r1_net_rev REAL DEFAULT 0.0,
                r1_cash_end REAL DEFAULT 5000000.0,
                
                -- Round 2 Inputs
                r2_buyer_spend REAL DEFAULT 0.0,
                r2_supplier_spend REAL DEFAULT 0.0,
                r2_trust_spend REAL DEFAULT 0.0,
                r2_take_rate REAL DEFAULT 0.15,
                
                -- Round 2 Metrics
                r2_liquidity REAL DEFAULT 0.0,
                r2_retention REAL DEFAULT 0.0,
                r2_net_rev REAL DEFAULT 0.0,
                r2_leakage_gmv REAL DEFAULT 0.0,
                r2_cash_remaining REAL DEFAULT 0.0,
                
                -- Final Scores
                liquidity_score REAL DEFAULT 0.0,
                retention_score REAL DEFAULT 0.0,
                valuation_m REAL DEFAULT 0.0,
                valuation_score REAL DEFAULT 0.0,
                composite_score REAL DEFAULT 0.0,
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.close()


def normalize_name(name: str) -> str:
    return name.strip().lower()


def get_player(first_name: str, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    norm = normalize_name(first_name)
    if not norm:
        return None
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM players WHERE normalized_name = ?", (norm,))
    row = cur.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def register_or_get_player(first_name: str, company_name: str, db_path: str = DB_PATH) -> Tuple[Dict[str, Any], bool]:
    """
    Registers a new founder or returns their existing progress.
    Returns (player_dict, is_new).
    """
    norm = normalize_name(first_name)
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM players WHERE normalized_name = ?", (norm,))
    row = cur.fetchone()
    
    if row:
        player_dict = dict(row)
        conn.close()
        return player_dict, False
        
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with conn:
        conn.execute("""
            INSERT INTO players (
                normalized_name, first_name, company_name, status,
                r1_cash_end, created_at, updated_at
            ) VALUES (?, ?, ?, 'In Round 1', 5000000.0, ?, ?)
        """, (norm, first_name.strip(), company_name.strip(), now, now))
    
    cur.execute("SELECT * FROM players WHERE normalized_name = ?", (norm,))
    new_player = dict(cur.fetchone())
    conn.close()
    return new_player, True


def save_round_1_results(
    first_name: str,
    r1_buyer: float,
    r1_supplier: float,
    r1_trust: float,
    r1_take: float,
    owners: int,
    walkers: int,
    balance: float,
    state: str,
    liquidity: float,
    net_rev: float,
    cash_end: float,
    db_path: str = DB_PATH,
) -> None:
    norm = normalize_name(first_name)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn = get_db_connection(db_path)
    with conn:
        conn.execute("""
            UPDATE players SET
                status = 'In Round 2',
                r1_buyer_spend = ?,
                r1_supplier_spend = ?,
                r1_trust_spend = ?,
                r1_take_rate = ?,
                r1_owners_acquired = ?,
                r1_walkers_acquired = ?,
                r1_balance_ratio = ?,
                r1_state = ?,
                r1_liquidity = ?,
                r1_net_rev = ?,
                r1_cash_end = ?,
                updated_at = ?
            WHERE normalized_name = ?
        """, (
            r1_buyer, r1_supplier, r1_trust, r1_take,
            owners, walkers, balance, state,
            liquidity, net_rev, cash_end, now, norm
        ))
    conn.close()


def save_round_2_and_complete(
    first_name: str,
    r2_buyer: float,
    r2_supplier: float,
    r2_trust: float,
    r2_take: float,
    r2_liquidity: float,
    r2_retention: float,
    r2_net_rev: float,
    r2_leakage_gmv: float,
    r2_cash_rem: float,
    liquidity_score: float,
    retention_score: float,
    valuation_m: float,
    valuation_score: float,
    composite_score: float,
    db_path: str = DB_PATH,
) -> None:
    norm = normalize_name(first_name)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn = get_db_connection(db_path)
    with conn:
        conn.execute("""
            UPDATE players SET
                status = 'Completed',
                r2_buyer_spend = ?,
                r2_supplier_spend = ?,
                r2_trust_spend = ?,
                r2_take_rate = ?,
                r2_liquidity = ?,
                r2_retention = ?,
                r2_net_rev = ?,
                r2_leakage_gmv = ?,
                r2_cash_remaining = ?,
                liquidity_score = ?,
                retention_score = ?,
                valuation_m = ?,
                valuation_score = ?,
                composite_score = ?,
                updated_at = ?
            WHERE normalized_name = ?
        """, (
            r2_buyer, r2_supplier, r2_trust, r2_take,
            r2_liquidity, r2_retention, r2_net_rev, r2_leakage_gmv, r2_cash_rem,
            liquidity_score, retention_score, valuation_m, valuation_score, composite_score,
            now, norm
        ))
    conn.close()


def get_leaderboard_dataframe(db_path: str = DB_PATH) -> pd.DataFrame:
    """
    Returns the ranked leaderboard dataframe formatted for the UI.
    """
    conn = get_db_connection(db_path)
    query = """
        SELECT
            first_name AS "Founder",
            company_name AS "Marketplace Company",
            status AS "Status",
            composite_score AS "Composite Score",
            liquidity_score AS "Liquidity %",
            retention_score AS "Retention %",
            valuation_m AS "Valuation ($M)",
            r1_take_rate AS "R1 Take",
            r2_take_rate AS "R2 Take",
            updated_at
        FROM players
        ORDER BY
            CASE status
                WHEN 'Completed' THEN 1
                WHEN 'In Round 2' THEN 2
                ELSE 3
            END,
            composite_score DESC,
            valuation_m DESC,
            updated_at ASC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        return pd.DataFrame(columns=[
            "Rank", "Founder", "Marketplace Company", "Status",
            "Composite Score", "Liquidity %", "Retention %", "Valuation ($M)",
            "R1 Take", "R2 Take"
        ])
    
    # Format status badges
    def format_badge(status):
        if status == "Completed":
            return "✅ Completed"
        elif status == "In Round 2":
            return "🟡 In Round 2"
        return "⏳ In Round 1"

    df["Status"] = df["Status"].apply(format_badge)
    df["R1 Take"] = df["R1 Take"].apply(lambda x: f"{int(x*100)}%" if pd.notnull(x) else "-")
    df["R2 Take"] = df["R2 Take"].apply(lambda x: f"{int(x*100)}%" if pd.notnull(x) else "-")
    df["Composite Score"] = df["Composite Score"].apply(lambda x: f"{x:.1f}" if pd.notnull(x) else "-")
    df["Liquidity %"] = df["Liquidity %"].apply(lambda x: f"{x:.1f}%" if pd.notnull(x) else "-")
    df["Retention %"] = df["Retention %"].apply(lambda x: f"{x:.1f}%" if pd.notnull(x) else "-")
    df["Valuation ($M)"] = df["Valuation ($M)"].apply(lambda x: f"${x:.2f}M" if pd.notnull(x) else "-")
    
    # Insert Rank column
    df.insert(0, "Rank", [f"#{i+1}" for i in range(len(df))])
    df = df.drop(columns=["updated_at"], errors="ignore")
    return df


def delete_player(first_name: str, db_path: str = DB_PATH) -> bool:
    norm = normalize_name(first_name)
    conn = get_db_connection(db_path)
    with conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM players WHERE normalized_name = ?", (norm,))
        deleted = cur.rowcount > 0
    conn.close()
    return deleted


def reset_leaderboard(db_path: str = DB_PATH) -> None:
    conn = get_db_connection(db_path)
    with conn:
        conn.execute("DELETE FROM players")
    conn.close()


def get_class_analytics(db_path: str = DB_PATH) -> Dict[str, Any]:
    """
    Computes class-wide aggregates for the Instructor Panel.
    """
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM players")
    total_founders = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM players WHERE status = 'Completed'")
    completed_count = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM players WHERE status = 'In Round 2'")
    in_r2_count = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM players WHERE status = 'In Round 1'")
    in_r1_count = cur.fetchone()[0]

    # R1 State Distribution among those who finished R1
    cur.execute("""
        SELECT r1_state, COUNT(*) 
        FROM players 
        WHERE status IN ('In Round 2', 'Completed') 
        GROUP BY r1_state
    """)
    r1_states = dict(cur.fetchall())
    
    # Averages among completed
    cur.execute("""
        SELECT 
            AVG(composite_score),
            AVG(liquidity_score),
            AVG(retention_score),
            AVG(valuation_m),
            AVG(r1_take_rate),
            AVG(r2_take_rate),
            SUM(r2_leakage_gmv)
        FROM players 
        WHERE status = 'Completed'
    """)
    row = cur.fetchone()
    conn.close()
    
    avg_composite = round(row[0] or 0.0, 1)
    avg_liquidity = round(row[1] or 0.0, 1)
    avg_retention = round(row[2] or 0.0, 1)
    avg_valuation = round(row[3] or 0.0, 2)
    avg_r1_take = round((row[4] or 0.0) * 100, 1)
    avg_r2_take = round((row[5] or 0.0) * 100, 1)
    total_leakage_gmv = round(row[6] or 0.0, 2)

    return {
        "total_founders": total_founders,
        "completed_count": completed_count,
        "in_r2_count": in_r2_count,
        "in_r1_count": in_r1_count,
        "r1_states": r1_states,
        "avg_composite": avg_composite,
        "avg_liquidity": avg_liquidity,
        "avg_retention": avg_retention,
        "avg_valuation": avg_valuation,
        "avg_r1_take": avg_r1_take,
        "avg_r2_take": avg_r2_take,
        "total_leakage_gmv": total_leakage_gmv,
    }


# Auto-initialize DB when module is imported
init_db()
