"""
leaderboard.py — Shared SQLite Persistence and Session Recovery
Manages the live class leaderboard for "The Marketplace Matchmaker".
Provides session recovery, instructor PIN-protected controls, and class-wide analytics.
"""

import os
import sqlite3
import datetime
from typing import Optional, Dict, Any, List, Tuple
import pandas as pd


DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DEFAULT_DATA_DIR, "marketplace_matchmaker.db")


def get_db_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
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
                status TEXT NOT NULL, -- 'In Round 1', 'Round 1 Report', 'In Round 2', 'Completed'
                student_pin TEXT DEFAULT '',
                
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
                r1_owners_per_walker INTEGER DEFAULT 8,
                r1_liquidity REAL DEFAULT 0.0,
                r1_net_rev REAL DEFAULT 0.0,
                r1_cash_end REAL DEFAULT 5000000.0,
                
                -- Round 2 Inputs
                r2_buyer_spend REAL DEFAULT 0.0,
                r2_supplier_spend REAL DEFAULT 0.0,
                r2_trust_spend REAL DEFAULT 0.0,
                r2_take_rate REAL DEFAULT 0.15,
                
                -- Round 2 Metrics
                r2_owners_per_walker INTEGER DEFAULT 8,
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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        # Backward compatibility migration for student_pin and dynamic walker capacity columns
        try:
            conn.execute("ALTER TABLE players ADD COLUMN student_pin TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE players ADD COLUMN r1_owners_per_walker INTEGER DEFAULT 8")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE players ADD COLUMN r2_owners_per_walker INTEGER DEFAULT 8")
        except sqlite3.OperationalError:
            pass
    conn.close()


def get_app_setting(key: str, default: str = "", db_path: str = DB_PATH) -> str:
    """Retrieves a persistent configuration value from the SQLite settings table."""
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    try:
        cur.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
        row = cur.fetchone()
        if row:
            return row["value"]
    except sqlite3.OperationalError:
        init_db(db_path)
        cur.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
        row = cur.fetchone()
        if row:
            return row["value"]
    finally:
        conn.close()
    return default


def set_app_setting(key: str, value: str, db_path: str = DB_PATH) -> None:
    """Saves a persistent configuration value in the SQLite settings table."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)", (key, value))
    except sqlite3.OperationalError:
        init_db(db_path)
        with conn:
            conn.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)", (key, value))
    finally:
        conn.close()


def normalize_name(name: str) -> str:
    return name.strip().lower()


def get_player(identifier: str, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    norm = normalize_name(identifier)
    if not norm:
        return None
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM players WHERE normalized_name = ?", (norm,))
    row = cur.fetchone()
    if not row:
        cur.execute("SELECT * FROM players WHERE student_pin = ? ORDER BY updated_at DESC LIMIT 1", (identifier.strip(),))
        row = cur.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def get_player_by_pin(pin: str, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    if not pin or not pin.strip():
        return None
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM players WHERE student_pin = ? ORDER BY updated_at DESC LIMIT 1", (pin.strip(),))
    row = cur.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def generate_unique_pin(db_path: str = DB_PATH) -> str:
    """
    Generates a unique 4-digit PIN that is not currently assigned to any player.
    Guarantees that multiple students with identical first names never collide.
    """
    import random
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    try:
        cur.execute("SELECT student_pin FROM players WHERE student_pin != ''")
        existing_pins = {str(row[0]).strip() for row in cur.fetchall()}
    except Exception:
        existing_pins = set()
    finally:
        conn.close()

    for _ in range(10000):
        pin = f"{random.randint(1000, 9999)}"
        if pin not in existing_pins:
            return pin
    # Fallback if 1000-9999 is fully saturated
    return f"{random.randint(10000, 99999)}"



def register_or_get_player(
    first_name: str,
    company_name: str,
    pin: Optional[str] = None,
    db_path: str = DB_PATH,
) -> Tuple[Dict[str, Any], bool]:
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
    if pin is None:
        if "_" in first_name:
            pin = first_name.split("_")[-1].strip()
        elif "#" in first_name:
            pin = first_name.split("#")[-1].strip()
        else:
            pin = ""

    with conn:
        conn.execute("""
            INSERT INTO players (
                normalized_name, first_name, company_name, status,
                student_pin, r1_cash_end, created_at, updated_at
            ) VALUES (?, ?, ?, 'In Round 1', ?, 5000000.0, ?, ?)
        """, (norm, first_name.strip(), company_name.strip(), pin, now, now))
    
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
    status: str = "Round 1 Report",
    r1_owners_per_walker: int = 8,
) -> None:
    norm = normalize_name(first_name)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn = get_db_connection(db_path)
    with conn:
        conn.execute("""
            UPDATE players SET
                status = ?,
                r1_buyer_spend = ?,
                r1_supplier_spend = ?,
                r1_trust_spend = ?,
                r1_take_rate = ?,
                r1_owners_acquired = ?,
                r1_walkers_acquired = ?,
                r1_balance_ratio = ?,
                r1_state = ?,
                r1_owners_per_walker = ?,
                r1_liquidity = ?,
                r1_net_rev = ?,
                r1_cash_end = ?,
                updated_at = ?
            WHERE normalized_name = ?
        """, (
            status,
            r1_buyer, r1_supplier, r1_trust, r1_take,
            owners, walkers, balance, state,
            r1_owners_per_walker,
            liquidity, net_rev, cash_end, now, norm
        ))
    conn.close()


def proceed_to_round_2(first_name: str, db_path: str = DB_PATH) -> None:
    """Advances player status from 'Round 1 Report' to 'In Round 2'."""
    norm = normalize_name(first_name)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn = get_db_connection(db_path)
    with conn:
        conn.execute("""
            UPDATE players SET
                status = 'In Round 2',
                updated_at = ?
            WHERE normalized_name = ?
        """, (now, norm))
    conn.close()


def step_back_to_round_1(first_name: str, db_path: str = DB_PATH) -> None:
    """Steps player status back from 'Round 1 Report' to 'In Round 1' to allow modifying choices."""
    norm = normalize_name(first_name)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn = get_db_connection(db_path)
    with conn:
        conn.execute("""
            UPDATE players SET
                status = 'In Round 1',
                updated_at = ?
            WHERE normalized_name = ?
        """, (now, norm))
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
    r2_owners_per_walker: int = 8,
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
                r2_owners_per_walker = ?,
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
            r2_owners_per_walker,
            r2_liquidity, r2_retention, r2_net_rev, r2_leakage_gmv, r2_cash_rem,
            liquidity_score, retention_score, valuation_m, valuation_score, composite_score,
            now, norm
        ))
    conn.close()


def get_leaderboard_dataframe(db_path: str = DB_PATH, full_details: bool = True) -> pd.DataFrame:
    """
    Returns the ranked leaderboard dataframe formatted for the UI.
    If full_details is False, returns only Rank, Founder, Composite Score, and Valuation ($M).
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
                WHEN 'Round 1 Report' THEN 3
                ELSE 4
            END,
            composite_score DESC,
            valuation_m DESC,
            updated_at ASC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        if not full_details:
            return pd.DataFrame(columns=["Rank", "Founder", "Composite Score", "Valuation ($M)"])
        return pd.DataFrame(columns=[
            "Rank", "Founder", "Marketplace Company", "Status",
            "Composite Score", "Liquidity %", "Retention %", "Valuation ($M)",
            "R1 Take", "R2 Take"
        ])
    
    # Format status badges
    def format_badge(status):
        if status == "Completed":
            return "✅ Completed"
        elif status in ("In Round 2", "Round 1 Report"):
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
    if not full_details:
        return df[["Rank", "Founder", "Composite Score", "Valuation ($M)"]]
    return df


def get_student_export_dataframe(db_path: str = DB_PATH) -> pd.DataFrame:
    """
    Returns an exhaustive student dataset formatted for CSV export in the Instructor Panel.
    Includes both strategic decision allocations and outcome metrics.
    """
    conn = get_db_connection(db_path)
    query = """
        SELECT
            first_name AS "Founder",
            student_pin AS "Student PIN",
            company_name AS "Company",
            status AS "Status",
            composite_score AS "Composite Score",
            liquidity_score AS "Liquidity Score",
            retention_score AS "Retention Score",
            valuation_m AS "Valuation ($M)",
            r1_buyer_spend AS "R1 Buyer Spend ($)",
            r1_supplier_spend AS "R1 Walker Spend ($)",
            r1_trust_spend AS "R1 Trust Spend ($)",
            r1_take_rate AS "R1 Take Rate",
            r1_state AS "R1 Balance State",
            r1_owners_per_walker AS "R1 Walker Efficiency (Owners/Walker)",
            r1_liquidity AS "R1 Liquidity %",
            r1_net_rev AS "R1 Net Revenue ($)",
            r1_cash_end AS "R1 Ending Cash ($)",
            r2_buyer_spend AS "R2 Buyer Spend ($)",
            r2_supplier_spend AS "R2 Walker Spend ($)",
            r2_trust_spend AS "R2 Trust Spend ($)",
            r2_take_rate AS "R2 Take Rate",
            r2_owners_per_walker AS "R2 Walker Efficiency (Owners/Walker)",
            r2_liquidity AS "R2 Liquidity %",
            r2_retention AS "R2 Retention %",
            r2_net_rev AS "R2 Net Revenue ($)",
            r2_leakage_gmv AS "R2 Leakage GMV ($)",
            r2_cash_remaining AS "R2 Cash Remaining ($)",
            created_at AS "Created At",
            updated_at AS "Updated At"
        FROM players
        ORDER BY
            CASE status
                WHEN 'Completed' THEN 1
                WHEN 'In Round 2' THEN 2
                WHEN 'Round 1 Report' THEN 3
                ELSE 4
            END,
            composite_score DESC,
            valuation_m DESC,
            updated_at ASC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    if not df.empty:
        df.insert(0, "Rank", [f"#{i+1}" for i in range(len(df))])
    return df


def delete_player(first_name: str, db_path: str = DB_PATH) -> bool:
    norm = normalize_name(first_name)
    conn = get_db_connection(db_path)
    with conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM players WHERE normalized_name = ?", (norm,))
        deleted = cur.rowcount > 0
        if not deleted and first_name.strip():
            cur.execute("DELETE FROM players WHERE student_pin = ?", (first_name.strip(),))
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
    Computes class-wide aggregates for the Instructor Panel with consolidated queries.
    """
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT
            COUNT(*) AS total_founders,
            SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS completed_count,
            SUM(CASE WHEN status IN ('In Round 2', 'Round 1 Report') THEN 1 ELSE 0 END) AS in_r2_count,
            SUM(CASE WHEN status = 'In Round 1' THEN 1 ELSE 0 END) AS in_r1_count,
            AVG(CASE WHEN status = 'Completed' THEN composite_score ELSE NULL END) AS avg_composite,
            AVG(CASE WHEN status = 'Completed' THEN liquidity_score ELSE NULL END) AS avg_liquidity,
            AVG(CASE WHEN status = 'Completed' THEN retention_score ELSE NULL END) AS avg_retention,
            AVG(CASE WHEN status = 'Completed' THEN valuation_m ELSE NULL END) AS avg_valuation,
            AVG(CASE WHEN status = 'Completed' THEN r1_take_rate ELSE NULL END) AS avg_r1_take,
            AVG(CASE WHEN status = 'Completed' THEN r2_take_rate ELSE NULL END) AS avg_r2_take,
            SUM(CASE WHEN status = 'Completed' THEN r2_leakage_gmv ELSE 0.0 END) AS total_leakage_gmv
        FROM players
    """)
    row = cur.fetchone()
    
    # R1 State Distribution among those who finished R1
    cur.execute("""
        SELECT r1_state, COUNT(*) 
        FROM players 
        WHERE status IN ('In Round 2', 'Round 1 Report', 'Completed') 
        GROUP BY r1_state
    """)
    r1_states = dict(cur.fetchall())
    conn.close()
    
    total_founders = (row[0] if row else 0) or 0
    completed_count = (row[1] if row else 0) or 0
    in_r2_count = (row[2] if row else 0) or 0
    in_r1_count = (row[3] if row else 0) or 0
    avg_composite = round((row[4] if row and row[4] is not None else 0.0), 1)
    avg_liquidity = round((row[5] if row and row[5] is not None else 0.0), 1)
    avg_retention = round((row[6] if row and row[6] is not None else 0.0), 1)
    avg_valuation = round((row[7] if row and row[7] is not None else 0.0), 2)
    avg_r1_take = round(((row[8] if row and row[8] is not None else 0.0) * 100), 1)
    avg_r2_take = round(((row[9] if row and row[9] is not None else 0.0) * 100), 1)
    total_leakage_gmv = round((row[10] if row and row[10] is not None else 0.0), 2)

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
