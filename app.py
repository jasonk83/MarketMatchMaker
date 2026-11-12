"""
app.py — The Marketplace Matchmaker (Streamlit Simulation)
Two-Sided Platform Simulation for Undergraduate IT Students.
Teaches two-sided network effects, chicken-or-egg liquidity, CAC saturation,
multi-homing rivalry, and disintermediation (off-platform leakage).
"""

import os
import sys

# Ensure Streamlit operates in a writable environment on Android/Linux VM,
# preventing read-only filesystem errors when managing internal telemetry/state.
os.environ["HOME"] = "/tmp"
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

try:
    import streamlit.runtime.metrics_util as _metrics_util
    class _DummyInstallation:
        installation_id = "surge-classdemo-offline-id"
        installation_id_v3 = "surge-classdemo-offline-id"
        installation_id_v4 = "surge-classdemo-offline-id"
    _metrics_util.Installation._instance = _DummyInstallation()
except Exception:
    pass

import datetime
import subprocess
from typing import Optional, Tuple
import streamlit as st
import streamlit.components.v1 as components
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
    page_title="The Marketplace Matchmaker 🐶🐾",
    page_icon="🐶",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    /* Metric Card Styling */
    .metric-card {
        background-color: #1E293B !important;
        border: 1px solid #334155 !important;
        border-radius: 10px !important;
        padding: 16px 20px !important;
        margin-bottom: 12px !important;
        color: #F8FAFC !important;
    }
    .metric-card * {
        color: #F8FAFC !important;
    }
    .metric-title {
        color: #94A3B8 !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }
    .metric-value {
        color: #F8FAFC !important;
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        margin-top: 4px !important;
    }
    .metric-sub {
        color: #60A5FA !important;
        font-size: 0.85rem !important;
        margin-top: 2px !important;
    }
    .danger-sub {
        color: #F87171 !important;
    }
    .success-sub {
        color: #4ADE80 !important;
    }
    .info-tooltip-wrap {
        position: relative;
        display: inline-block;
        vertical-align: middle;
    }
    .info-tooltip-btn {
        background: transparent !important;
        border: none !important;
        cursor: pointer !important;
        padding: 0 4px !important;
        font-size: 0.95rem !important;
        line-height: 1 !important;
        display: inline-flex !important;
        align-items: center !important;
    }
    .info-tooltip-btn:focus-visible, .info-tooltip-btn:focus {
        outline: 2px solid #60A5FA !important;
        outline-offset: 2px !important;
        border-radius: 4px !important;
    }
    .info-tooltip-bubble {
        visibility: hidden;
        opacity: 0;
        width: 250px;
        background-color: #0F172A !important;
        color: #F8FAFC !important;
        text-align: left;
        border-radius: 8px;
        padding: 10px 14px;
        position: absolute;
        z-index: 999;
        bottom: 130%;
        left: 50%;
        transform: translateX(-50%);
        box-shadow: 0 10px 25px rgba(0,0,0,0.6);
        border: 1px solid #475569 !important;
        font-size: 0.82rem !important;
        font-weight: 400 !important;
        text-transform: none !important;
        letter-spacing: normal !important;
        line-height: 1.4 !important;
        transition: opacity 0.2s ease, visibility 0.2s ease;
        pointer-events: none;
    }
    .info-tooltip-bubble::after {
        content: "";
        position: absolute;
        top: 100%;
        left: 50%;
        margin-left: -6px;
        border-width: 6px;
        border-style: solid;
        border-color: #475569 transparent transparent transparent;
    }
    .info-tooltip-wrap:hover .info-tooltip-bubble,
    .info-tooltip-wrap:focus-within .info-tooltip-bubble {
        visibility: visible;
        opacity: 1;
        pointer-events: auto;
    }
    /* Section Callout Card */
    .callout-box {
        background-color: #1E293B !important;
        border-left: 4px solid #60A5FA !important;
        padding: 14px 18px !important;
        border-radius: 4px !important;
        margin-bottom: 16px !important;
        color: #F8FAFC !important;
    }
    .callout-box * {
        color: #F8FAFC !important;
    }
    .warning-box {
        background-color: #2D2310 !important;
        border-left: 4px solid #F59E0B !important;
        padding: 14px 18px !important;
        border-radius: 4px !important;
        margin-bottom: 16px !important;
        color: #F8FAFC !important;
    }
    .warning-box * {
        color: #F8FAFC !important;
    }
    .danger-box {
        background-color: #2D1416 !important;
        border-left: 4px solid #F87171 !important;
        padding: 14px 18px !important;
        border-radius: 4px !important;
        margin-bottom: 16px !important;
        color: #F8FAFC !important;
    }
    .danger-box * {
        color: #F8FAFC !important;
    }

    /* Touch-friendly radio pill buttons (WCAG 2.5.5 min 44x44px target) */
    div[data-testid="stRadio"] > div[role="radiogroup"] {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label {
        min-height: 44px !important;
        min-width: 52px !important;
        padding: 8px 16px !important;
        border-radius: 22px !important;
        background-color: #1E293B !important;
        border: 1px solid #475569 !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        cursor: pointer !important;
        transition: all 0.15s ease-in-out !important;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label * {
        color: #F8FAFC !important;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover {
        border-color: #60A5FA !important;
        background-color: #243248 !important;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:focus-within,
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:focus-visible {
        outline: 2px solid #60A5FA !important;
        outline-offset: 2px !important;
    }
    div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input:checked) {
        border-color: #60A5FA !important;
        background-color: #1E3A8A !important;
        box-shadow: 0 0 0 1px #60A5FA !important;
    }

    /* Mobile Responsive Optimizations */
    @media (max-width: 768px) {
        .block-container {
            padding: 1rem 0.75rem 2rem 0.75rem !important;
        }
        h1, .stMarkdown h1 {
            font-size: 1.6rem !important;
        }
        h2, .stMarkdown h2 {
            font-size: 1.3rem !important;
        }
        h3, .stMarkdown h3 {
            font-size: 1.1rem !important;
        }
        .metric-card {
            padding: 12px 14px !important;
            margin-bottom: 8px !important;
        }
        .metric-title {
            font-size: 0.75rem !important;
        }
        .metric-value {
            font-size: 1.4rem !important;
        }
        .metric-sub {
            font-size: 0.75rem !important;
        }
        .callout-box, .warning-box, .danger-box {
            padding: 10px 12px !important;
            margin-bottom: 12px !important;
        }
        input[type="text"], input[type="password"] {
            min-height: 44px !important;
            font-size: 1rem !important;
        }
    }

    /* Clean button disappearance styling (Zero layout shift, instant visual feedback) */
    .btn-clicked-hide,
    button[data-clicked="true"],
    [data-testid="stButton"] button[data-clicked="true"] {
        opacity: 0 !important;
        pointer-events: none !important;
        cursor: default !important;
        transition: opacity 0.1s ease-out !important;
    }

    /* Zero layout shift for utility components */
    iframe[title="st.iframe"] {
        position: absolute !important;
        top: -9999px !important;
        left: -9999px !important;
        width: 0px !important;
        height: 0px !important;
        border: none !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }
    div[data-testid="stCustomComponentV1"]:has(iframe[title="st.iframe"]) {
        height: 0px !important;
        min-height: 0px !important;
        margin: 0 !important;
        padding: 0 !important;
    }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# App Access & QR Code Generation
# -----------------------------------------------------------------------------
def get_app_access_url() -> str:
    custom_url = leaderboard.get_app_setting("classroom_app_url", "")
    if custom_url.strip():
        return custom_url.strip()
    try:
        if hasattr(st, "context") and hasattr(st.context, "headers"):
            headers = st.context.headers
            host = headers.get("host") or headers.get("Host")
            if host:
                host_clean = host.split(":")[0]
                if host_clean not in ("localhost", "127.0.0.1", ""):
                    proto = headers.get("x-forwarded-proto") or headers.get("X-Forwarded-Proto") or "http"
                    return f"{proto}://{host}"
    except Exception:
        pass
    try:
        import streamlit.net_util as net_util
        ip = net_util.get_internal_ip()
        if ip and ip != "127.0.0.1":
            return f"http://{ip}:8501"
    except Exception:
        pass
    return "http://localhost:8501"


@st.cache_data
def get_qr_code_image_bytes(url: str):
    """
    Generates QR code PNG bytes.
    Gracefully falls back to public QR API or None if qrcode package is not installed.
    """
    try:
        import qrcode
        import io
        qr = qrcode.QRCode(
            version=1,
            box_size=6,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except ImportError:
        # Fallback to public QR code API if qrcode is not installed in the runtime environment
        try:
            import urllib.request
            import urllib.parse
            encoded_url = urllib.parse.quote(url)
            api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=220x220&data={encoded_url}"
            req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                return resp.read()
        except Exception:
            return None
    except Exception:
        return None


# -----------------------------------------------------------------------------
# Versioning & Footer
# -----------------------------------------------------------------------------
def get_app_version_and_date() -> str:
    """Returns dynamically computed version string 'Version 1.X • Month DD, YYYY' based on git commits."""
    commit_count = 5
    formatted_date = datetime.date.today().strftime("%B %d, %Y")
    try:
        # Get count of commits
        res_count = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(__file__) or ".",
            timeout=2,
        )
        if res_count.returncode == 0 and res_count.stdout.strip().isdigit():
            commit_count = int(res_count.stdout.strip())

        # Get date of latest commit
        res_date = subprocess.run(
            ["git", "log", "-1", "--format=%cd", "--date=format:%B %d, %Y"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(__file__) or ".",
            timeout=2,
        )
        if res_date.returncode == 0 and res_date.stdout.strip():
            formatted_date = res_date.stdout.strip()
    except Exception:
        pass
    return f"Version 1.{commit_count} • {formatted_date}"


def render_app_footer():
    """Renders a left-justified version and date line at the very bottom of the screen."""
    ver_str = get_app_version_and_date()
    st.markdown(
        f"""
        <div style="margin-top: 45px; padding-top: 15px; border-top: 1px solid #334155; text-align: left; font-size: 0.82rem; color: #94A3B8;">
            {ver_str}
        </div>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# Dedicated Instructor Control Panel Page (?view=instructor)
# -----------------------------------------------------------------------------
def render_instructor_page(app_access_url: str):
    """
    Renders the dedicated, secure Instructor Control Panel.
    Contains strictly:
    1. Display and Projection Controls
    2. Export Student Results option (CSV)
    3. Pedagogical Benchmark Strategy Reveal
    4. Classroom Management sections
    Does not include gameplay elements or the student leaderboard.
    """
    st.markdown("# 🔒 The Marketplace Matchmaker — Instructor Control Panel")
    st.caption("Administrative, pedagogical, and projection controls for course instructors.")

    default_pin = os.environ.get("INSTRUCTOR_PIN", "2026")
    try:
        default_pin = st.secrets.get("INSTRUCTOR_PIN", default_pin)
    except Exception:
        pass

    if not st.session_state.get("instructor_authenticated", False):
        st.markdown("""
        <div class="callout-box" style="border-left-color: #60A5FA;">
            <h3 style="margin-top: 0; color: #F8FAFC;">🔑 Instructor Verification Required</h3>
            Enter your instructor PIN to access projection settings, download student CSV results, reveal teaching benchmarks, and manage classroom data.
        </div>
        """, unsafe_allow_html=True)

        col_pin_in, col_pin_btn = st.columns([2, 1], vertical_alignment="bottom")
        with col_pin_in:
            entered_pin = st.text_input(
                "Enter Instructor PIN",
                type="password",
                key="instructor_auth_pin_input",
                placeholder="Enter 4-digit PIN",
            ).strip()
        with col_pin_btn:
            if st.button("🔓 Authenticate", type="primary", use_container_width=True):
                failed_attempts = st.session_state.get("instructor_failed_pin_attempts", 0)
                if failed_attempts >= 3:
                    import time
                    time.sleep(2.0)
                if entered_pin == default_pin.strip():
                    st.session_state.instructor_authenticated = True
                    st.session_state.instructor_failed_pin_attempts = 0
                    st.rerun()
                else:
                    st.session_state.instructor_failed_pin_attempts = failed_attempts + 1
                    new_count = failed_attempts + 1
                    if new_count >= 3:
                        st.error(f"Incorrect PIN ({new_count} consecutive failed attempts). A 2-second security cooldown has been applied to protect classroom settings.")
                    else:
                        st.error("Incorrect PIN. Please re-enter or check your environment configuration.")

        st.write("")
        st.link_button("🎮 Return to Student Gameplay", url=app_access_url)
        return

    # Authenticated Action Bar
    top_c1, top_c2 = st.columns([3, 2], vertical_alignment="center")
    with top_c1:
        st.success("🔓 Instructor Access Granted — Active Session")
    with top_c2:
        c_out, c_back = st.columns([1, 1])
        with c_out:
            if st.button("🔒 Sign Out / Lock", use_container_width=True):
                st.session_state.instructor_authenticated = False
                st.rerun()
        with c_back:
            st.link_button("🎮 Student View", url=app_access_url, use_container_width=True)

    st.divider()

    # Section 1: Display & Projection Controls
    st.markdown("### 🎛️ Display & Projection Controls")
    disp_col1, disp_col2 = st.columns(2)
    with disp_col1:
        is_full_setting = leaderboard.get_app_setting("show_full_leaderboard", "false") == "true"
        full_toggle = st.toggle(
            "👁️ Display Full Information on Leaderboard",
            value=is_full_setting,
            help="When enabled, reveals Company, Status, Liquidity %, Retention %, and Take Rates across all screens."
        )
        if full_toggle != is_full_setting:
            leaderboard.set_app_setting("show_full_leaderboard", "true" if full_toggle else "false")
            st.rerun()

    with disp_col2:
        current_custom_url = leaderboard.get_app_setting("classroom_app_url", "")
        new_custom_url = st.text_input("📱 Classroom App URL (for QR Code)", value=current_custom_url, placeholder="e.g. http://10.102.151.26:8501")
        col_url_save, col_qr_dl = st.columns(2)
        with col_url_save:
            if st.button("Save QR Code URL", use_container_width=True):
                leaderboard.set_app_setting("classroom_app_url", new_custom_url.strip())
                st.cache_data.clear()
                st.success("App URL updated! The header QR code has refreshed.")
                st.rerun()
        with col_qr_dl:
            qr_target_url = new_custom_url.strip() or current_custom_url.strip() or app_access_url
            qr_bytes = get_qr_code_image_bytes(qr_target_url)
            if qr_bytes:
                st.download_button(
                    label="📥 Download QR Code (PNG)",
                    data=qr_bytes,
                    file_name="classroom_join_qr_code.png",
                    mime="image/png",
                    use_container_width=True,
                    help="Download high-resolution QR code image for classroom presentation slides."
                )

    # Section 2: Export Student Results (CSV)
    st.markdown("---")
    st.markdown("### 📥 Export Student Results")
    df_export = leaderboard.get_student_export_dataframe()
    if not df_export.empty:
        csv_bytes = df_export.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Student Results (CSV)",
            data=csv_bytes,
            file_name="marketplace_matchmaker_student_results.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.caption("No student results to export yet.")

    # Section 3: Toggleable Optimal Benchmark Reveal
    st.markdown("---")
    st.markdown("### 💡 Pedagogical Benchmark Strategy Reveal")
    if st.checkbox("Reveal Master Benchmark Strategy & Optimal Allocations"):
        benchmark = get_optimal_benchmark()
        b_sc = benchmark["scorecard"]
        b_r1 = benchmark["r1_result"]
        b_r2 = benchmark["r2_result"]

        st.markdown(f"""
        <div class="callout-box" style="border-left-color: #60A5FA;">
            <h3>🏆 Instructor Pedagogical Benchmark (Composite: {b_sc.composite_score:.1f}/100)</h3>
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

    # Section 4: Admin Actions (Classroom Management)
    st.markdown("---")
    st.markdown("### 🛠️ Classroom Management")
    del_col1, del_col2 = st.columns(2)
    with del_col1:
        st.markdown("### Delete Individual Entry")
        df_full = leaderboard.get_leaderboard_dataframe(full_details=True)
        if not df_full.empty:
            student_to_delete = st.selectbox("Select student to remove", options=df_full["Founder"].tolist())
            if st.button("🗑️ Delete Selected Student", type="secondary", use_container_width=True):
                leaderboard.delete_player(student_to_delete)
                st.success(f"Removed {student_to_delete} from leaderboard.")
                st.rerun()
        else:
            st.caption("No entries to remove.")

    with del_col2:
        st.markdown("### Reset Entire Leaderboard")
        st.caption("Wipes all student records for the next class section. Requires PIN confirmation.")
        confirm_clear_pin = st.text_input(
            "Confirm Instructor PIN to Reset",
            type="password",
            key="confirm_clear_pin_inst_view",
            placeholder="Enter PIN to confirm wipe",
        )
        if st.button("⚠️ Clear Leaderboard for New Class", type="primary", use_container_width=True):
            if confirm_clear_pin.strip() == default_pin.strip():
                leaderboard.reset_leaderboard()
                st.success("Leaderboard cleared successfully!")
                st.rerun()
            else:
                st.error("PIN confirmation failed. You must re-enter the instructor PIN above to clear the leaderboard.")


# Top Header with Prominent Dog Emojis & QR Code Popover
app_access_url = get_app_access_url()

# Check for dedicated Instructor Control Panel view (?view=instructor)
if st.query_params.get("view") == "instructor":
    render_instructor_page(app_access_url)
    render_app_footer()
    st.stop()

qr_code_bytes = get_qr_code_image_bytes(app_access_url)

head_col1, head_col2 = st.columns([3, 1], vertical_alignment="center")
with head_col1:
    st.markdown("# 🐶🐾 The Marketplace Matchmaker")
    st.caption("Strategic Simulation of Two-Sided Platform Economics & Network Effects")
with head_col2:
    with st.popover("📱 Scan App QR Code", use_container_width=True):
        st.markdown("### 🐶 Join the Marketplace")
        st.caption("Scan to launch the simulation on your phone or laptop:")
        if qr_code_bytes:
            st.image(
                qr_code_bytes,
                width=220,
                alt=f"QR code linking to the Marketplace Matchmaker application at {app_access_url}",
            )
        else:
            st.info("ℹ️ Scannable QR code available once `qrcode` is installed (`pip install qrcode`).")
        st.code(app_access_url, language=None)
        st.caption("URL can be customized in the Instructor Control Panel.")

st.write("")


# -----------------------------------------------------------------------------
# Session State Initialization & Recovery
# -----------------------------------------------------------------------------
if "player_name" not in st.session_state:
    st.session_state.player_name = ""
if "player_pin" not in st.session_state:
    st.session_state.player_pin = ""
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
if "scroll_to_top_trigger" not in st.session_state:
    st.session_state.scroll_to_top_trigger = 0


def recover_player_state(identifier: str) -> bool:
    """Recovers the player's saved state from the database if present."""
    record = leaderboard.get_player(identifier)
    if not record:
        return False
    
    st.session_state.player_name = record["first_name"]
    st.session_state.company_name = record["company_name"]
    st.session_state.player_pin = record.get("student_pin", "")
    st.query_params["student_pin"] = record.get("student_pin", "")
    st.query_params["founder"] = record["first_name"]
    
    status = record["status"]
    if status == "In Round 1":
        st.session_state.active_step = "round1"
    elif status in ("Round 1 Report", "In Round 1 Report"):
        r1_eff = record.get("r1_owners_per_walker") or 8
        r1 = simulate_round_1(
            buyer_spend=record["r1_buyer_spend"],
            supplier_spend=record["r1_supplier_spend"],
            trust_spend=record["r1_trust_spend"],
            take_rate=record["r1_take_rate"],
            owners_per_walker=r1_eff,
        )
        st.session_state.r1_result = r1
        st.session_state.active_step = "round1_report"
    elif status == "In Round 2":
        # Reconstruct R1 result
        r1_eff = record.get("r1_owners_per_walker") or 8
        r1 = simulate_round_1(
            buyer_spend=record["r1_buyer_spend"],
            supplier_spend=record["r1_supplier_spend"],
            trust_spend=record["r1_trust_spend"],
            take_rate=record["r1_take_rate"],
            owners_per_walker=r1_eff,
        )
        st.session_state.r1_result = r1
        st.session_state.active_step = "round2"
    elif status == "Completed":
        # Reconstruct R1 & R2
        r1_eff = record.get("r1_owners_per_walker") or 8
        r1 = simulate_round_1(
            buyer_spend=record["r1_buyer_spend"],
            supplier_spend=record["r1_supplier_spend"],
            trust_spend=record["r1_trust_spend"],
            take_rate=record["r1_take_rate"],
            owners_per_walker=r1_eff,
        )
        r2_eff = record.get("r2_owners_per_walker") or 8
        r2 = simulate_round_2(
            r1=r1,
            buyer_spend=record["r2_buyer_spend"],
            supplier_spend=record["r2_supplier_spend"],
            trust_spend=record["r2_trust_spend"],
            take_rate=record["r2_take_rate"],
            owners_per_walker=r2_eff,
        )
        scorecard = compute_final_scores(r1, r2)
        st.session_state.r1_result = r1
        st.session_state.r2_result = r2
        st.session_state.scorecard = scorecard
        st.session_state.active_step = "final_scorecard"
    return True


# Auto-recover session from URL query parameters on initial page load / refresh
if not st.session_state.player_name:
    qp_pin = st.query_params.get("student_pin", "").strip()
    qp_founder = st.query_params.get("founder", "").strip()
    if qp_pin:
        player_record = leaderboard.get_player_by_pin(qp_pin)
        if player_record:
            recover_player_state(player_record["first_name"])
    elif qp_founder:
        pin_from_name = None
        if "_" in qp_founder:
            pin_from_name = qp_founder.split("_")[-1].strip()
        elif "#" in qp_founder:
            pin_from_name = qp_founder.split("#")[-1].strip()
        if pin_from_name:
            player_record = leaderboard.get_player_by_pin(pin_from_name)
            if player_record and leaderboard.normalize_name(player_record["first_name"]) == leaderboard.normalize_name(qp_founder):
                recover_player_state(player_record["first_name"])


# -----------------------------------------------------------------------------
# Quantitative Lever Control Component (Slider + Open Text Field)
# -----------------------------------------------------------------------------
def try_parse_spend_input(text_val: str, max_val: float) -> Tuple[Optional[float], bool]:
    """
    Attempts to parse text input into a float in millions ($M).
    Returns (parsed_value_or_None, is_valid_format).
    """
    if not text_val or not str(text_val).strip():
        return (None, True)
    raw = str(text_val).strip().replace("$", "").replace(",", "")
    try:
        if raw.lower().endswith("k"):
            num = float(raw[:-1].strip())
            val = (num * 1000.0) / 1_000_000.0
        elif raw.lower().endswith("m"):
            val = float(raw[:-1].strip())
        else:
            val = float(raw)
            if val > 1000.0:  # Direct dollars e.g. 1,250,000 -> 1.25M
                val = val / 1_000_000.0
        if val < 0.0:
            return (None, False)
        return (max(0.0, min(float(max_val), val)), True)
    except Exception:
        return (None, False)


def parse_spend_input(text_val: str, current_val: float, max_val: float) -> float:
    """
    Parses open text input into a float representing millions of dollars ($M).
    Handles:
    - Decimal millions: '1.25', '1.234', '0.5'
    - Formatted millions: '$1.25M', '1.25m'
    - Thousands notation: '500k', '$750K'
    - Raw whole dollars: '1,250,000', '1250000', '$1,234,567'
    Clamps result within [0.0, max_val].
    """
    val, ok = try_parse_spend_input(text_val, max_val)
    if ok and val is not None:
        return val
    return current_val


def _sync_lever_from_slider(prefix: str):
    val = st.session_state[f"{prefix}_slider"]
    st.session_state[f"{prefix}_val"] = val
    st.session_state[f"{prefix}_text"] = f"${val:.2f}M"
    st.session_state[f"{prefix}_format_error"] = False


def _sync_lever_from_text(prefix: str, max_val: float):
    raw = st.session_state.get(f"{prefix}_text", "")
    curr = st.session_state.get(f"{prefix}_val", 0.0)
    parsed_val, is_valid = try_parse_spend_input(raw, max_val)
    if not is_valid:
        st.session_state[f"{prefix}_format_error"] = True
        return
    st.session_state[f"{prefix}_format_error"] = False
    parsed = curr if parsed_val is None else parsed_val
    st.session_state[f"{prefix}_val"] = parsed
    # Slider is clamped to max_val and rounded to 2 decimals
    st.session_state[f"{prefix}_slider"] = max(0.0, min(float(max_val), round(parsed, 2)))
    if abs(parsed - round(parsed, 2)) < 1e-4:
        st.session_state[f"{prefix}_text"] = f"${parsed:.2f}M"
    elif abs(parsed - round(parsed, 4)) < 1e-6:
        st.session_state[f"{prefix}_text"] = f"${parsed:.4f}M"
    else:
        st.session_state[f"{prefix}_text"] = f"${parsed:.6f}M"


def render_lever_control(
    label: str,
    key_prefix: str,
    default_m: float,
    max_m: float,
    help_text: str,
    step_m: float = 0.01,
) -> float:
    """
    Renders a synchronized Slider + Open Text Field lever.
    Allows students to adjust with the slider or type fine-tuned amounts (e.g. 1.23M, 500k, $1,234,500)
    to prevent leaving investment resources unallocated on the table.
    Returns exact spend in dollars (float).
    """
    val_key = f"{key_prefix}_val"
    slider_key = f"{key_prefix}_slider"
    text_key = f"{key_prefix}_text"

    max_m = float(max(0.01, max_m))

    if val_key not in st.session_state:
        init_val = min(float(default_m), max_m)
        st.session_state[val_key] = init_val
        st.session_state[slider_key] = init_val
        st.session_state[text_key] = f"${init_val:.2f}M"

    # Guard against max_m changes (e.g. Round 2 cash limit updates)
    if st.session_state[slider_key] > max_m:
        st.session_state[slider_key] = max_m
    if st.session_state[val_key] > max_m:
        st.session_state[val_key] = max_m
        st.session_state[text_key] = f"${max_m:.2f}M"

    st.markdown(f"**{label}**", help=help_text)
    col_s, col_t = st.columns([3, 1])
    with col_s:
        st.slider(
            label=f"{label} (Slider)",
            min_value=0.0,
            max_value=max_m,
            step=step_m,
            format="$%.2fM",
            key=slider_key,
            on_change=_sync_lever_from_slider,
            args=(key_prefix,),
            label_visibility="collapsed",
            help=help_text,
        )
    with col_t:
        st.text_input(
            label=f"{label} (Open Field)",
            key=text_key,
            placeholder="e.g. 1.25M or 750k",
            on_change=_sync_lever_from_text,
            args=(key_prefix, max_m),
            label_visibility="collapsed",
            help="Type exact spend: e.g. 1.25M, $750k, or $1,234,567 to allocate every dollar.",
        )
        if st.session_state.get(f"{key_prefix}_format_error", False):
            st.caption("⚠️ Unrecognized. Try e.g. `1.25M`, `$750k`, or `$500,000`")
        else:
            st.caption("Exact spend: e.g. 1.25M, 750k")

    return float(st.session_state[val_key]) * 1_000_000.0


def get_lever_spend_dollars(prefix: str, max_val_m: float) -> float:
    """
    Returns exact spend in dollars ($), prioritizing recent open text field entry if valid,
    and falling back to the synchronized float value or slider.
    """
    text_val = st.session_state.get(f"{prefix}_text", "")
    parsed_val, is_valid = try_parse_spend_input(text_val, max_val_m)
    if is_valid and parsed_val is not None:
        st.session_state[f"{prefix}_val"] = parsed_val
        return float(parsed_val) * 1_000_000.0
    val = st.session_state.get(f"{prefix}_val")
    if val is None:
        val = st.session_state.get(f"{prefix}_slider", 0.0)
    return float(val) * 1_000_000.0


# -----------------------------------------------------------------------------
# Smooth Viewport Auto-Scroll & Button Disappearance Client Controller
# -----------------------------------------------------------------------------
_scroll_signal = f'<div id="surge-scroll-trigger" data-step="{st.session_state.active_step}" data-trigger="{st.session_state.scroll_to_top_trigger}" style="display:none;"></div>'
_scroll_js = """
<script>
(function() {
    function installTopController() {
        try {
            const pWin = (window.parent && window.parent.document) ? window.parent : window;
            const pDoc = pWin.document;
            if (!pDoc) return;

            // Define or update scroll function on parent window
            pWin.surgeScrollToTop = function(smooth) {
                const behavior = smooth ? 'smooth' : 'auto';
                try { pWin.scrollTo({ top: 0, left: 0, behavior: behavior }); } catch(e) {}
                try { pDoc.documentElement.scrollTo({ top: 0, left: 0, behavior: behavior }); } catch(e) {}
                try { pDoc.body.scrollTo({ top: 0, left: 0, behavior: behavior }); } catch(e) {}
                const selectors = [
                    '[data-testid="stAppViewContainer"]',
                    'section.main',
                    '.main',
                    '[data-testid="stMainBlockContainer"]',
                    '[data-testid="stApp"]',
                    '[data-testid="stMain"]',
                    '#root'
                ];
                selectors.forEach(function(sel) {
                    try {
                        const els = pDoc.querySelectorAll(sel);
                        els.forEach(function(el) {
                            if (el) {
                                try { el.scrollTo({ top: 0, left: 0, behavior: behavior }); } catch(err) {}
                                el.scrollTop = 0;
                            }
                        });
                    } catch(e) {}
                });
                try {
                    const allEls = pDoc.querySelectorAll('div, section, main');
                    allEls.forEach(function(el) {
                        if (el.scrollHeight > el.clientHeight && el.clientHeight > 200) {
                            const style = pWin.getComputedStyle(el);
                            if (style.overflowY === 'auto' || style.overflowY === 'scroll') {
                                try { el.scrollTo({ top: 0, left: 0, behavior: behavior }); } catch(e) {}
                                el.scrollTop = 0;
                            }
                        }
                    });
                } catch(e) {}
            };

            // Attach parent document click listener once using capture phase
            if (!pWin._surgeClickActive) {
                pWin._surgeClickActive = true;
                pDoc.addEventListener('click', function(e) {
                    // Smoothly scroll back to top of the app every time something is clicked
                    if (typeof pWin.surgeScrollToTop === 'function') {
                        pWin.surgeScrollToTop(true);
                        setTimeout(function() { pWin.surgeScrollToTop(true); }, 50);
                        setTimeout(function() { pWin.surgeScrollToTop(true); }, 150);
                        setTimeout(function() { pWin.surgeScrollToTop(true); }, 300);
                    }

                    // Check if clicked element is an action button
                    const btn = e.target.closest ? e.target.closest('button, [role="button"]') : null;
                    if (btn) {
                        const txt = (btn.innerText || btn.textContent || '').toLowerCase();
                        const isMajorAction = txt.includes('commit round 1') ||
                                              txt.includes('proceed to round 2') ||
                                              txt.includes('lock final strategy') ||
                                              txt.includes('take me to the leaderboard') ||
                                              txt.includes('claim $5.0m') ||
                                              txt.includes('confirm reset');
                        if (isMajorAction) {
                            const w = btn.offsetWidth;
                            const h = btn.offsetHeight;
                            if (w > 0 && h > 0) {
                                btn.style.width = w + 'px';
                                btn.style.height = h + 'px';
                                btn.style.minWidth = w + 'px';
                                btn.style.minHeight = h + 'px';
                            }
                            btn.style.opacity = '0';
                            btn.style.pointerEvents = 'none';
                            btn.style.cursor = 'default';
                            btn.style.transition = 'opacity 0.1s ease-out';
                            btn.setAttribute('data-clicked', 'true');
                        }
                    }
                }, true);
            }

            // Immediately scroll parent to top on every render/stage update
            if (typeof pWin.surgeScrollToTop === 'function') {
                pWin.surgeScrollToTop(true);
                setTimeout(function() { pWin.surgeScrollToTop(true); }, 50);
                setTimeout(function() { pWin.surgeScrollToTop(true); }, 150);
                setTimeout(function() { pWin.surgeScrollToTop(true); }, 350);
            }
        } catch(e) {}
    }

    installTopController();
})();
</script>
"""
components.html(_scroll_signal + _scroll_js, height=0, width=0)


# -----------------------------------------------------------------------------
# Main Navigation Tabs
# -----------------------------------------------------------------------------
TAB_PLAYER = "🐶 Launch Your Marketplace (Player Console)"
TAB_LEADERBOARD = "🏆🐕 Live Class Leaderboard & Instructor Debrief"

if "main_tab_nav" not in st.session_state:
    st.session_state.main_tab_nav = TAB_PLAYER

tab_player, tab_leaderboard = st.tabs(
    [TAB_PLAYER, TAB_LEADERBOARD],
    key="main_tab_nav",
    on_change="rerun",
)


# =============================================================================
# TAB 1: PLAYER CONSOLE
# =============================================================================
with tab_player:
    # Step 0: Registration
    if st.session_state.active_step == "registration":
        st.header("👋🐶 Welcome, Founder!")
        st.markdown("""
        <div class="callout-box">
            <strong>Seed Capital Raised:</strong> You have just raised <strong>$5.0M in Seed Capital</strong> to launch an on-demand, peer-to-peer 
            <strong>Dog Walking Marketplace 🐕</strong>. Your mission is to solve the classic 
            <em>Chicken-or-Egg Cold Start Problem</em>, conquer multi-homing competitors (like BarkBuddy 🐩), defend against 
            off-platform Venmo leakage, and build a high-valuation platform.
        </div>
        """, unsafe_allow_html=True)

        col_reg1, col_reg2 = st.columns([1, 1])
        with col_reg1:
            input_name = st.text_input("🐕‍🦺 Founder First Name", placeholder="e.g. Jordan").strip()
            input_company = st.text_input("🐶 Dog Walking Startup Name", placeholder="e.g. Bark Avenue, ZoomieWalks, PawPath").strip()

            if st.button("🐶🚀 Claim $5.0M Seed & Enter Round 1", type="primary", use_container_width=True, key="btn_claim_seed"):
                if not input_name or not input_company:
                    st.error("Please enter both your First Name and Company Name to begin.")
                else:
                    if "_" in input_name:
                        founder_full_name = input_name
                        pin = input_name.split("_")[-1].strip()
                    elif "#" in input_name:
                        parts = input_name.split("#")
                        pin = parts[-1].strip()
                        founder_full_name = f"{parts[0].strip()}_{pin}"
                    else:
                        pin = leaderboard.generate_unique_pin()
                        founder_full_name = f"{input_name}_{pin}"

                    # Check if returning player
                    recovered = recover_player_state(founder_full_name)
                    if recovered:
                        st.info(f"Welcome back, {st.session_state.player_name}! Restoring your saved session...")
                        st.session_state.scroll_to_top_trigger += 1
                        st.rerun()
                    else:
                        # New player registration
                        record, _ = leaderboard.register_or_get_player(founder_full_name, input_company, pin=pin)
                        st.session_state.player_name = record["first_name"]
                        st.session_state.company_name = record["company_name"]
                        st.session_state.player_pin = pin
                        st.query_params["student_pin"] = pin
                        st.query_params["founder"] = record["first_name"]
                        for k in list(st.session_state.keys()):
                            if k.startswith(("r1_buyer", "r1_supplier", "r1_trust", "r2_buyer", "r2_supplier", "r2_trust")):
                                del st.session_state[k]
                        st.session_state.active_step = "round1"
                        st.session_state.scroll_to_top_trigger += 1
                        st.rerun()

        with col_reg2:
            st.markdown("""
            ### 🎯 Core Learning Objectives
            - **Two-Sided Liquidity**: 1 active dog walker fulfills walks for **5 to 12 dog owners** (average ~8), driven by walker stamina, experience, and neighborhood route density.
            - **Chicken-or-Egg Risk**: Attracting too many owners creates 90+ min wait times; attracting too many walkers leaves them idle and causes starvation churn.
            - **Platform Governance**: Without background checks and pet insurance, trust collapses.
            - **Defensibility**: High take rates tempt users to exchange numbers and pay via **Venmo** off-app.
            """)

    # Top Status Bar for Active Players
    if st.session_state.active_step != "registration":
        top_c1, top_c2, top_c3 = st.columns([2, 2, 1], vertical_alignment="center")
        with top_c1:
            pin_badge = f" (PIN: `{st.session_state.player_pin}`)" if st.session_state.player_pin else ""
            st.markdown(f"**🐕 Founder:** `{st.session_state.player_name}`{pin_badge} | **🏢 Startup:** `{st.session_state.company_name}`")
        with top_c2:
            status_text = {
                "round1": "⏳ Round 1: Cold Start Dog Liquidity",
                "round1_report": "📊 Round 1 Diagnostic Report",
                "round2": "🟡 Round 2: Multi-Homing & Leakage Threat",
                "final_scorecard": "🏆 Final Scorecard (Top Dog Rank)",
            }.get(st.session_state.active_step, "")
            st.markdown(f"**Stage:** {status_text}")
        with top_c3:
            with st.popover("🔄 Switch Founder", use_container_width=True):
                st.markdown("### 🔄 Switch Founder?")
                st.caption("Switching founder resets your local session on this device. You can restore your progress anytime using your name or PIN.")
                if st.button("⚠️ Confirm Reset Session", type="primary", use_container_width=True):
                    st.session_state.player_name = ""
                    st.session_state.player_pin = ""
                    st.session_state.company_name = ""
                    st.session_state.active_step = "registration"
                    st.session_state.main_tab_nav = TAB_PLAYER
                    st.session_state.r1_result = None
                    st.session_state.r2_result = None
                    st.session_state.scorecard = None
                    st.query_params.clear()
                    for k in list(st.session_state.keys()):
                        if k.startswith(("r1_buyer", "r1_supplier", "r1_trust", "r2_buyer", "r2_supplier", "r2_trust")):
                            del st.session_state[k]
                    st.rerun()
        st.divider()

    # Step 1: Round 1 Strategy Allocation
    if st.session_state.active_step == "round1":
        st.header("Round 1: 🐶 The Liquidity Crisis (Cold Start Launch)")
        st.markdown("""
        <div class="callout-box">
            <strong>🐕 The Chicken-or-Egg Challenge:</strong> Dog owners will not join without reliable nearby dog walkers, 
            and dog walkers will not stay active without steady walk bookings.<br>
            • <strong>Seed Capital:</strong> $5.00M available.<br>
            • <strong>Capacity Rule:</strong> 1 active dog walker serves between <strong>5 and 12 regular dog owners</strong> (average ~8), depending on walker quality, experience, and route clustering.<br>
            • <strong>Walk Price:</strong> Standardized at <strong>$30 per walk</strong>.
        </div>
        """, unsafe_allow_html=True)

        col_l, col_r = st.columns([3, 2])
        with col_l:
            st.markdown("### ⚙️ Quantitative Capital Levers")
            
            # Mobile Budget Progress Bar (Immediate feedback above levers for phone screens)
            r1_curr_spend = (
                float(st.session_state.get("r1_buyer_val", 0.0)) +
                float(st.session_state.get("r1_supplier_val", 0.0)) +
                float(st.session_state.get("r1_trust_val", 0.0))
            ) * 1_000_000.0
            r1_curr_left = 5_000_000.0 - r1_curr_spend
            r1_prog_ratio = min(1.0, max(0.0, r1_curr_spend / 5_000_000.0))
            if r1_curr_left >= 0:
                st.progress(r1_prog_ratio, text=f"📊 Allocated: ${r1_curr_spend/1_000_000:.2f}M / $5.00M (${r1_curr_left:,.0f} unallocated)")
            else:
                st.progress(1.0, text=f"🚨 Overdraft: ${r1_curr_spend/1_000_000:.2f}M / $5.00M (${-r1_curr_left:,.0f} OVER BUDGET)")
                st.markdown(f"""
                <div class="danger-box" role="alert" aria-live="assertive" style="padding: 8px 12px !important; margin-top: 6px !important; margin-bottom: 6px !important;">
                    🚨 <strong>Budget Overdraft:</strong> You have allocated ${r1_curr_spend/1_000_000:.2f}M, exceeding your $5.00M seed capital by <strong>${-r1_curr_left:,.0f}</strong>. Reduce allocations before committing.
                </div>
                """, unsafe_allow_html=True)

            st.caption("💡 Adjust sliders or type fine-tuned amounts in the open fields (e.g. `1.25M`, `$750k`, or `$1,234,567`) to deploy every dollar.")

            buyer_spend = render_lever_control(
                "1. 🐶 Dog Owner Marketing (Buyer CAC)",
                key_prefix="r1_buyer",
                default_m=0.0,
                max_m=5.0,
                help_text="Funds first-walk discount coupons, localized ads, and community campaigns. CAC rises with aggressive spend."
            )

            supplier_spend = render_lever_control(
                "2. 🦮 Dog Walker Recruitment (Supplier CAC)",
                key_prefix="r1_supplier",
                default_m=0.0,
                max_m=5.0,
                help_text="Funds guaranteed hourly minimums, onboarding bonuses, and walker equipment."
            )

            trust_spend = render_lever_control(
                "3. 🦴 Pet Emergency Insurance, Walker Background Checks, GPS Walk Tracking (Trust Moat)",
                key_prefix="r1_trust",
                default_m=0.0,
                max_m=5.0,
                help_text="Funds $25k Pet Emergency Insurance pools, automated background checks, and live GPS route tracking."
            )

            take_rate_pct = st.radio(
                "4. 🥩 Platform Take Rate (% per $30 walk)",
                options=[5, 10, 15, 20, 25],
                index=1,
                horizontal=True,
                key="r1_take_rate_pct",
                format_func=lambda x: f"{x}%",
                help="Higher take rates yield more revenue per walk, but squeeze walker earnings and depress walker onboarding."
            )
            take_rate = float(take_rate_pct) / 100.0

        with col_r:
            st.markdown("### 💰 Budget Tracker")
            total_spend_r1 = buyer_spend + supplier_spend + trust_spend
            cash_left = 5_000_000.0 - total_spend_r1

            st.metric(
                "Total Round 1 Spend",
                f"${total_spend_r1/1_000_000:.2f}M",
                f"${cash_left:,.0f} unallocated" if cash_left >= 0 else f"${-cash_left:,.0f} OVER BUDGET",
                delta_color="normal" if cash_left >= 0 else "inverse"
            )

            if st.session_state.get("r1_commit_error"):
                st.markdown(f"""
                <div class="danger-box" role="alert" aria-live="assertive">
                    {st.session_state.r1_commit_error}
                </div>
                """, unsafe_allow_html=True)

            if round(total_spend_r1, 2) > 5_000_000.0:
                st.markdown(f"""
                <div class="danger-box" role="alert" aria-live="assertive">
                    🚨 <strong>Budget Overdraft!</strong> You have allocated ${total_spend_r1:,.0f}, exceeding your $5.0M seed capital. 
                    Reduce your spend sliders/fields before committing.
                </div>
                """, unsafe_allow_html=True)
            elif total_spend_r1 <= 0.0:
                st.markdown("""
                <div class="warning-box">
                    ⚠️ <strong>No Capital Allocated:</strong> All levers are at $0. Allocate your $5.0M seed capital across the levers to formulate your strategy before committing.
                </div>
                """, unsafe_allow_html=True)
            elif cash_left == 0.0:
                st.markdown("""
                <div class="callout-box" style="border-left-color: #10B981;">
                    🎯 <strong>Zero Waste Allocation:</strong> 100% of seed capital ($5,000,000) deployed with maximum efficiency!
                </div>
                """, unsafe_allow_html=True)
            elif cash_left < 100_000.0:
                st.markdown(f"""
                <div class="callout-box" style="border-left-color: #10B981;">
                    ✅ <strong>Tight Allocation:</strong> Only <strong>${cash_left:,.0f}</strong> unallocated. Maximum capital is working for your marketplace.
                </div>
                """, unsafe_allow_html=True)
            elif total_spend_r1 > 3_500_000.0:
                st.markdown(f"""
                <div class="warning-box">
                    ⚠️ <strong>Capital Depletion Warning:</strong> Spending over $3.5M leaves under ${cash_left:,.0f} (${cash_left/1_000_000:.2f}M) for Round 2. 
                    You risk entering Round 2 severely under-capitalized against emerging rivals.
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="callout-box">
                    ✅ <strong>Prudent Reserve:</strong> Retaining <strong>${cash_left:,.0f}</strong> (${cash_left/1_000_000:.2f}M) in seed reserves to defend your position in Round 2.
                </div>
                """, unsafe_allow_html=True)

            st.markdown("""
            **Strategic Check:**
            - Base Dog Owner CAC: ~$60
            - Base Dog Walker CAC: ~$350
            - Target Ratio: 1 Walker per 5–12 Dog Owners (Target baseline: ~8)
            """)

            def _handle_commit_r1():
                b_spend = get_lever_spend_dollars("r1_buyer", 5.0)
                s_spend = get_lever_spend_dollars("r1_supplier", 5.0)
                t_spend = get_lever_spend_dollars("r1_trust", 5.0)
                tot = b_spend + s_spend + t_spend
                if round(tot, 2) > 5_000_000.0:
                    st.session_state.r1_commit_error = f"🚨 <strong>Budget Overdraft!</strong> You have allocated ${tot:,.0f} (${tot/1_000_000:.2f}M), exceeding your $5.0M seed capital. Please reduce spend before committing."
                    return
                if tot <= 0.0:
                    st.session_state.r1_commit_error = "⚠️ <strong>No Capital Allocated:</strong> All levers are at $0. Please allocate your $5.0M seed capital across levers before committing."
                    return
                st.session_state.r1_commit_error = None
                t_rate = float(st.session_state.get("r1_take_rate_pct", 10)) / 100.0
                r1_res = simulate_round_1(
                    buyer_spend=b_spend,
                    supplier_spend=s_spend,
                    trust_spend=t_spend,
                    take_rate=t_rate,
                )
                st.session_state.r1_result = r1_res
                leaderboard.save_round_1_results(
                    first_name=st.session_state.player_name,
                    r1_buyer=b_spend,
                    r1_supplier=s_spend,
                    r1_trust=t_spend,
                    r1_take=t_rate,
                    owners=r1_res.owners_acquired,
                    walkers=r1_res.walkers_acquired,
                    balance=r1_res.balance_ratio,
                    state=r1_res.state_classification,
                    liquidity=r1_res.liquidity_rate,
                    net_rev=r1_res.platform_net_revenue,
                    cash_end=r1_res.cash_end,
                    r1_owners_per_walker=r1_res.owners_per_walker,
                )
                st.session_state.active_step = "round1_report"
                st.session_state.scroll_to_top_trigger += 1

            commit_r1_clicked = st.button(
                "🐕‍🦺 Commit Round 1 Strategy (Blind Decision)",
                type="primary",
                use_container_width=True,
                disabled=False,
                key="btn_commit_round_1",
                on_click=_handle_commit_r1,
            )
            if commit_r1_clicked and st.session_state.active_step == "round1":
                _handle_commit_r1()
                st.rerun()

    # Step 2: Round 1 Diagnostic Report
    if st.session_state.active_step == "round1_report":
        r1 = st.session_state.r1_result
        st.header("📊 Round 1 Diagnostic Report")

        if r1.state_classification == "INACTIVE":
            st.markdown("""
            <div class="warning-box">
                💤 <strong>INACTIVE MARKETPLACE:</strong> No capital was allocated to acquire users or walkers. 
                Your marketplace remained completely dormant.
            </div>
            """, unsafe_allow_html=True)
        elif r1.state_classification == "DEMAND_OVERLOAD":
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
            st.markdown(f"""
            <div class="callout-box" style="border-left-color: #10B981;">
                ✅ <strong>HYPER-LOCAL LIQUIDITY SYNCHRONIZED:</strong> Exceptional synchronization! 
                Supply and demand matched tightly within the balanced capacity ratio ({r1.owners_per_walker} owners/walker), yielding low wait times and happy participants.
            </div>
            """, unsafe_allow_html=True)

        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("🐶 Owners Acquired", f"{r1.owners_acquired:,}", f"{r1.surviving_owners:,} surviving")
        col_m2.metric("🦮 Walker Capacity", f"{r1.walker_capacity:,} owners", f"{r1.walkers_acquired:,} walkers @ {r1.owners_per_walker}/wk ({r1.walker_efficiency_rating})")
        col_m3.metric("⏱️ Avg Wait Time", f"{r1.avg_wait_time_minutes} mins", f"Balance: {r1.balance_ratio:.2f}")
        col_m4.metric("💰 Net Revenue Earned", f"${r1.platform_net_revenue/1_000_000:.2f}M", f"GMV: ${r1.gross_merchandise_value/1_000_000:.2f}M")

        # Capacity vs Demand Horizontal Bar Chart (Optimized for Mobile Screens & Long Labels)
        fulfilled_pups = r1.matched_walks // 12
        chart_data = pd.DataFrame({
            "Side": ["🐶 Dog Owner Demand", f"🦮 Walker Capacity (Walkers × {r1.owners_per_walker})", "🐾 Matched Happy Pups"],
            "Users": [r1.owners_acquired, r1.walker_capacity, fulfilled_pups],
            "Type": ["Demand", "Capacity", "Matched"],
        })
        chart = alt.Chart(chart_data).mark_bar(cornerRadius=6).encode(
            y=alt.Y("Side:N", title="", sort=None, axis=alt.Axis(labelLimit=250)),
            x=alt.X("Users:Q", title="Number of People / Capacity"),
            color=alt.Color("Side:N", legend=None, scale=alt.Scale(
                domain=["🐶 Dog Owner Demand", f"🦮 Walker Capacity (Walkers × {r1.owners_per_walker})", "🐾 Matched Happy Pups"],
                range=["#60A5FA", "#F59E0B", "#10B981"]
            )),
            tooltip=["Side", "Users"]
        )
        bar_text = chart.mark_text(align="left", dx=5).encode(
            text=alt.Text("Users:Q", format=","),
            color=alt.value("#F8FAFC")
        )
        st.altair_chart((chart + bar_text).properties(height=200), use_container_width=True)

        st.markdown(f"**Diagnostic Feedback:**\n\n{r1.feedback}")

        st.markdown(f"""
        <div class="callout-box">
            💰 <strong>Capital Carried Forward to Round 2:</strong><br>
            • Seed Remaining: <strong>${(5_000_000.0 - r1.total_spend)/1_000_000:.2f}M</strong><br>
            • Round 1 Net Revenue Added: <strong>+${r1.platform_net_revenue/1_000_000:.2f}M</strong><br>
            • <strong>Total Available Cash for Round 2: ${r1.cash_end/1_000_000:.2f}M</strong>
        </div>
        """, unsafe_allow_html=True)

        def _handle_proceed_to_round_2():
            leaderboard.proceed_to_round_2(st.session_state.player_name)
            st.session_state.active_step = "round2"
            st.session_state.scroll_to_top_trigger += 1

        proceed_r2_clicked = st.button(
            "⚡ Proceed to Round 2: Rival Threat (BarkBuddy 🐕)",
            type="primary",
            use_container_width=True,
            key="btn_proceed_to_round_2",
            on_click=_handle_proceed_to_round_2,
        )
        if proceed_r2_clicked and st.session_state.active_step == "round1_report":
            _handle_proceed_to_round_2()
            st.rerun()

    # Step 3: Round 2 Strategy Allocation
    if st.session_state.active_step == "round2":
        r1 = st.session_state.r1_result
        available_cash_r2 = r1.cash_end

        st.header("Round 2: 🐕 Rival BarkBuddy & The Venmo Temptation")
        
        st.markdown("""
        <div class="warning-box">
            <h3>🚨 Urgent Market Crisis Briefing</h3>
            <strong>1. Rival Entrant 'BarkBuddy' 🐩:</strong> A well-funded competitor has just entered the city with an aggressive 
            <strong>12% Take Rate</strong> and heavy walker poaching bonuses. If your take rate is 20%+ or you underfund walker retention, 
            walkers will multi-home and defect to BarkBuddy.<br><br>
            <strong>2. Off-Platform Leakage ('The Venmo Temptation' 📱):</strong> Repeat dog owners and walkers who matched in Round 1 now know each other! 
            They are tempted to text each other directly and pay via Venmo to bypass platform fees.<br>
            <em>The Only Defense:</em> <strong>Cumulative Governance & Trust Moat 🦴</strong>. Dog owners will refuse to go off-app if they would forfeit your 
            $25k Pet Emergency Insurance, real-time GPS tracking, and instant dispute resolution!
        </div>
        """, unsafe_allow_html=True)

        # Round 1 Fleet Baseline Carried Forward
        st.markdown("### 🐾 Round 1 Fleet Baseline Carried Forward")
        b_c1, b_c2, b_c3, b_c4, b_c5 = st.columns(5)
        b_c1.metric("🐶 Surviving Owners", f"{r1.surviving_owners:,}")
        b_c2.metric("🦮 Active Walkers", f"{r1.surviving_walkers:,}")
        b_c3.metric("⭐ R1 Fleet Quality", f"{r1.owners_per_walker}/wk", r1.walker_efficiency_rating)
        b_c4.metric("🥩 R1 Take Rate", f"{int(r1.take_rate * 100)}%")
        b_c5.metric("💰 Available Cash", f"${available_cash_r2/1_000_000:.2f}M")

        col2_l, col2_r = st.columns([3, 2])
        if available_cash_r2 <= 0.0:
            with col2_l:
                st.markdown("""
                <div class="danger-box" role="alert" aria-live="assertive">
                    🚨 <strong>No Capital Remaining:</strong> You have $0 in cash reserves. 
                    Spend levers are locked to $0.0M. You can only adjust your Platform Take Rate.
                </div>
                """, unsafe_allow_html=True)
                buyer_spend_2 = 0.0
                supplier_spend_2 = 0.0
                trust_spend_2 = 0.0

                take_rate_pct_2 = st.radio(
                    "Platform Take Rate in Round 2 (BarkBuddy is at 12%)",
                    options=[5, 10, 15, 20, 25],
                    index=2,
                    horizontal=True,
                    format_func=lambda x: f"{x}%",
                    help="20% and 25% take rates trigger massive multi-homing defection to BarkBuddy and heavy Venmo leakage."
                )
                take_rate_2 = take_rate_pct_2 / 100.0
        else:
            max_spend_val = max(0.05, available_cash_r2 / 1_000_000.0)

            with col2_l:
                st.markdown("### ⚙️ Round 2 Capital Levers")
                
                # Mobile Budget Progress Bar (Immediate feedback above levers for phone screens)
                r2_curr_spend = (
                    float(st.session_state.get("r2_buyer_val", 0.0)) +
                    float(st.session_state.get("r2_supplier_val", 0.0)) +
                    float(st.session_state.get("r2_trust_val", 0.0))
                ) * 1_000_000.0
                r2_curr_left = available_cash_r2 - r2_curr_spend
                r2_prog_ratio = min(1.0, max(0.0, r2_curr_spend / available_cash_r2))
                if r2_curr_left >= 0:
                    st.progress(r2_prog_ratio, text=f"📊 Allocated: ${r2_curr_spend/1_000_000:.2f}M / ${available_cash_r2/1_000_000:.2f}M (${r2_curr_left:,.0f} unallocated)")
                else:
                    st.progress(1.0, text=f"🚨 Overdraft: ${r2_curr_spend/1_000_000:.2f}M / ${available_cash_r2/1_000_000:.2f}M (${-r2_curr_left:,.0f} OVER BUDGET)")
                    st.markdown(f"""
                    <div class="danger-box" role="alert" aria-live="assertive" style="padding: 8px 12px !important; margin-top: 6px !important; margin-bottom: 6px !important;">
                        🚨 <strong>Budget Overdraft:</strong> You have allocated ${r2_curr_spend/1_000_000:.2f}M, exceeding your ${available_cash_r2/1_000_000:.2f}M available reserves by <strong>${-r2_curr_left:,.0f}</strong>. Reduce allocations before committing.
                    </div>
                    """, unsafe_allow_html=True)

                st.caption("💡 Adjust sliders or type fine-tuned amounts in the open fields (e.g. `1.10M`, `$800k`, or exact dollars) to maximize capital efficiency.")

                buyer_spend_2 = render_lever_control(
                    "1. 🐶 Dog Owner Growth & Retention Subsidies",
                    key_prefix="r2_buyer",
                    default_m=0.0,
                    max_m=float(max_spend_val),
                    help_text="Funds new dog owner acquisition (70%) and existing owner retention subsidies (30%)."
                )

                supplier_spend_2 = render_lever_control(
                    "2. 🦮 Dog Walker Retention & BarkBuddy Defense",
                    key_prefix="r2_supplier",
                    default_m=0.0,
                    max_m=float(max_spend_val),
                    help_text="Funds new walker recruitment (65%) and walker retention bonuses (35%) to prevent BarkBuddy poaching. Round 2 walkers will operate at a drawn efficiency of 5–12 owners each."
                )

                trust_spend_2 = render_lever_control(
                    "3. 🦴 Pet Emergency Insurance & Platform Trust Moat (Anti-Leakage Shield)",
                    key_prefix="r2_trust",
                    default_m=0.0,
                    max_m=float(max_spend_val),
                    help_text="Funds $25k Pet Emergency Insurance, automated walker background checks, and live GPS tracking. Cumulative trust spend with Round 1 creates switching friction that stops Venmo leakage dead in its tracks."
                )

                take_rate_pct_2 = st.radio(
                    "4. 🥩 Round 2 Take Rate (BarkBuddy is at 12%)",
                    options=[5, 10, 15, 20, 25],
                    index=2,
                    horizontal=True,
                    key="r2_take_rate_pct",
                    format_func=lambda x: f"{x}%",
                    help="20% and 25% take rates trigger massive multi-homing defection to BarkBuddy and heavy Venmo leakage."
                )
                take_rate_2 = float(take_rate_pct_2) / 100.0

        with col2_r:
            st.markdown("### 💰 Round 2 Budget Tracker")
            total_spend_r2 = buyer_spend_2 + supplier_spend_2 + trust_spend_2
            cash_rem_after_spend = available_cash_r2 - total_spend_r2

            st.metric(
                "Total Round 2 Spend",
                f"${total_spend_r2/1_000_000:.2f}M",
                f"${cash_rem_after_spend:,.0f} unallocated" if cash_rem_after_spend >= 0 else f"${-cash_rem_after_spend:,.0f} OVER BUDGET",
                delta_color="normal" if cash_rem_after_spend >= 0 else "inverse"
            )

            if round(total_spend_r2, 2) > round(available_cash_r2, 2):
                st.markdown(f"""
                <div class="danger-box" role="alert" aria-live="assertive">
                    🚨 <strong>Exceeds Available Cash!</strong> You have allocated ${total_spend_r2:,.0f}, exceeding your ${available_cash_r2:,.0f} reserves.
                    Reduce your spend sliders/fields to stay within available funds.
                </div>
                """, unsafe_allow_html=True)
            elif available_cash_r2 > 0 and total_spend_r2 <= 0.0:
                st.markdown("""
                <div class="warning-box">
                    ⚠️ <strong>No Capital Allocated:</strong> All levers are at $0. Allocate your available cash reserves across growth, retention, and trust before submitting.
                </div>
                """, unsafe_allow_html=True)
            elif cash_rem_after_spend == 0.0:
                st.markdown("""
                <div class="callout-box" style="border-left-color: #10B981;">
                    🎯 <strong>Zero Waste Deployment:</strong> 100% of available capital deployed to expand your platform and fend off rivals!
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="callout-box">
                    💼 <strong>Round 2 Capital Allocation:</strong><br>
                    • Total Spent: <strong>${total_spend_r2/1_000_000:.2f}M</strong> (${total_spend_r2:,.0f})<br>
                    • Unspent Cash Reserves: <strong>${cash_rem_after_spend/1_000_000:.2f}M</strong> (${cash_rem_after_spend:,.0f})<br>
                    <em>(Note: 100% of unspent cash is credited to your Enterprise Valuation at the end!)</em>
                </div>
                """, unsafe_allow_html=True)

            cum_trust = r1.trust_spend + trust_spend_2
            st.markdown(f"**🦴 Cumulative Trust Moat:** `${cum_trust/1_000_000:.2f}M` (Target: `$0.8M+` for max Venmo defense)")

            st.markdown("""
            **Strategic Check:**
            - **Rival Take Rate:** BarkBuddy charges **12%** (take rates above 15% trigger severe walker defection).
            - **Anti-Leakage Defense:** Cumulative Trust Moat of **$0.80M+** ($800k) virtually eliminates Venmo leakage.
            - **Fleet Quality Draw:** Walkers in Round 2 will operate at a newly drawn efficiency of **5–12 owners each**.
            """)

            if st.session_state.get("r2_commit_error"):
                st.markdown(f"""
                <div class="danger-box" role="alert" aria-live="assertive">
                    {st.session_state.r2_commit_error}
                </div>
                """, unsafe_allow_html=True)

            def _handle_lock_round_2(available_cash: float):
                max_val = max(0.05, available_cash / 1_000_000.0) if available_cash > 0.0 else 0.0
                b_spend_2 = get_lever_spend_dollars("r2_buyer", max_val) if available_cash > 0 else 0.0
                s_spend_2 = get_lever_spend_dollars("r2_supplier", max_val) if available_cash > 0 else 0.0
                t_spend_2 = get_lever_spend_dollars("r2_trust", max_val) if available_cash > 0 else 0.0
                tot_2 = b_spend_2 + s_spend_2 + t_spend_2
                if round(tot_2, 2) > round(available_cash, 2):
                    st.session_state.r2_commit_error = f"🚨 <strong>Exceeds Available Cash!</strong> You have allocated ${tot_2:,.0f}, exceeding your ${available_cash:,.0f} available reserves."
                    return
                if available_cash > 0.0 and tot_2 <= 0.0:
                    st.session_state.r2_commit_error = "⚠️ <strong>No Capital Allocated:</strong> Please allocate your available cash reserves across growth, retention, and trust before submitting."
                    return
                st.session_state.r2_commit_error = None
                t_rate_2 = float(st.session_state.get("r2_take_rate_pct", 15)) / 100.0
                r1_curr = st.session_state.r1_result
                r2_result = simulate_round_2(
                    r1=r1_curr,
                    buyer_spend=b_spend_2,
                    supplier_spend=s_spend_2,
                    trust_spend=t_spend_2,
                    take_rate=t_rate_2,
                )
                scorecard = compute_final_scores(r1_curr, r2_result)
                st.session_state.r2_result = r2_result
                st.session_state.scorecard = scorecard

                leaderboard.save_round_2_and_complete(
                    first_name=st.session_state.player_name,
                    r2_buyer=b_spend_2,
                    r2_supplier=s_spend_2,
                    r2_trust=t_spend_2,
                    r2_take=t_rate_2,
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
                    r2_owners_per_walker=r2_result.owners_per_walker,
                )
                st.session_state.active_step = "final_scorecard"
                st.session_state.scroll_to_top_trigger += 1

            lock_r2_clicked = st.button(
                "🔒 Lock Final Strategy (Submit Round 2 🐶)",
                type="primary",
                use_container_width=True,
                disabled=False,
                key="btn_lock_round_2",
                on_click=_handle_lock_round_2,
                args=(available_cash_r2,),
            )
            if lock_r2_clicked and st.session_state.active_step == "round2":
                _handle_lock_round_2(available_cash_r2)
                st.rerun()

    # Step 4: Final Scorecard (Single Attempt Permanently Locked)
    if st.session_state.active_step == "final_scorecard":
        sc = st.session_state.scorecard
        r1 = st.session_state.r1_result
        r2 = st.session_state.r2_result

        st.header(f"🏁🐕 Final Executive Scorecard — {st.session_state.company_name}")
        st.markdown("""
        <div class="callout-box" style="border-left-color: #10B981;">
            🔒 <strong>ATTEMPT COMPLETED & LOCKED:</strong> Your strategic decisions are finalized and recorded on the 
            <strong>Live Class Leaderboard 🏆</strong>.
        </div>
        """, unsafe_allow_html=True)

        # Headline Score Banner with Accessible Business Tooltips (Keyboard & Mobile Focusable)
        score_c1, score_c2, score_c3, score_c4 = st.columns(4)
        with score_c1:
            st.markdown(f"""
            <div class="metric-card" style="border-color: #60A5FA;">
                <div class="metric-title">
                    🏆 Composite Index Score
                    <span class="info-tooltip-wrap">
                        <button type="button" class="info-tooltip-btn" aria-label="Learn more about Composite Score" tabindex="0">ℹ️</button>
                        <span class="info-tooltip-bubble" role="tooltip">Composite Score: Overall platform performance index (0–100) weighting Marketplace Liquidity, Platform Retention, and Enterprise Valuation equally (1/3 each).</span>
                    </span>
                </div>
                <div class="metric-value" style="color: #60A5FA;">{sc.composite_score:.1f} / 100</div>
                <div class="metric-sub">Weighted 1/3 each</div>
            </div>
            """, unsafe_allow_html=True)
        with score_c2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">
                    🎾 Marketplace Liquidity
                    <span class="info-tooltip-wrap">
                        <button type="button" class="info-tooltip-btn" aria-label="Learn more about Marketplace Liquidity" tabindex="0">ℹ️</button>
                        <span class="info-tooltip-bubble" role="tooltip">Marketplace Liquidity: Measures how easily and quickly buyers and sellers match. High liquidity means dog owners promptly find available walkers without long wait times or cancellations.</span>
                    </span>
                </div>
                <div class="metric-value">{sc.liquidity_score:.1f}%</div>
                <div class="metric-sub">{sc.completed_walks:,} completed walks 🐾</div>
            </div>
            """, unsafe_allow_html=True)
        with score_c3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">
                    🐕 Platform Retention
                    <span class="info-tooltip-wrap">
                        <button type="button" class="info-tooltip-btn" aria-label="Learn more about Platform Retention" tabindex="0">ℹ️</button>
                        <span class="info-tooltip-bubble" role="tooltip">Platform Retention: The percentage of buyers and sellers who remain active on your platform over time instead of switching to competitors (like BarkBuddy) or transacting off-platform via Venmo.</span>
                    </span>
                </div>
                <div class="metric-value">{sc.retention_score:.1f}%</div>
                <div class="metric-sub">{r2.active_owners:,} owners 🐶 | {r2.active_walkers:,} walkers 🦮</div>
            </div>
            """, unsafe_allow_html=True)
        with score_c4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">
                    💎 Enterprise Valuation
                    <span class="info-tooltip-wrap">
                        <button type="button" class="info-tooltip-btn" aria-label="Learn more about Enterprise Valuation" tabindex="0">ℹ️</button>
                        <span class="info-tooltip-bubble" role="tooltip">Enterprise Valuation: The estimated total market worth of your company, calculated from annual operating profit multiplied by an industry multiple (8×–14× based on retention quality) plus remaining cash.</span>
                    </span>
                </div>
                <div class="metric-value">${sc.enterprise_valuation:.2f}M</div>
                <div class="metric-sub">${sc.operating_valuation:.2f}M Ops + ${sc.cash_remaining:.2f}M Cash</div>
            </div>
            """, unsafe_allow_html=True)

        with st.expander("📚 100-Level Business Concepts: Understanding Your Core Metrics"):
            st.markdown("""
            - **🎾 Marketplace Liquidity**: In business and economics, **liquidity** refers to how easily buyers and sellers can conduct transactions. For a platform marketplace, high liquidity means when a customer wants a service (a dog walk), a supplier is readily available nearby, leading to fast matches and high customer satisfaction.
            - **🐕 Platform Retention**: **Customer and supplier retention** measures how effectively your business keeps existing users coming back. In two-sided platforms, low retention is dangerous because it signals either customer defection to rivals (*multi-homing*) or disintermediation, where users bypass your platform fee to transact directly off-app (*the Venmo leak*).
            - **💎 Enterprise Valuation**: **Enterprise valuation** represents the overall economic value of the company as an investment asset. It evaluates both **operating profitability** (recurring cash flow scaled by a quality multiple) and **balance sheet strength** (unspent cash reserves).
            """)

        st.divider()

        col_f1, col_f2 = st.columns([1, 1])
        with col_f1:
            st.markdown("### 🔄 Transaction Fate in Round 2")
            total_walks = max(1, sc.completed_walks + sc.walks_lost_to_leakage + sc.walks_unmatched)
            pct_completed = (sc.completed_walks / total_walks) * 100.0
            pct_leakage = (sc.walks_lost_to_leakage / total_walks) * 100.0
            pct_unmatched = (sc.walks_unmatched / total_walks) * 100.0

            fate_df = pd.DataFrame({
                "Outcome": [
                    "Completed on Platform 🐶",
                    "Leaked to Venmo Off-App 📱",
                    "Unmatched / Shortage 😿",
                ],
                "Walks": [
                    sc.completed_walks,
                    sc.walks_lost_to_leakage,
                    sc.walks_unmatched,
                ],
                "Percent": [
                    f"{pct_completed:.1f}%",
                    f"{pct_leakage:.1f}%",
                    f"{pct_unmatched:.1f}%",
                ],
            })
            base = alt.Chart(fate_df).encode(
                theta=alt.Theta("Walks:Q", stack=True),
                tooltip=["Outcome", "Walks", "Percent"]
            )
            arc = base.mark_arc(innerRadius=60).encode(
                color=alt.Color("Outcome:N", legend=alt.Legend(orient="bottom", title=None, labelLimit=250), scale=alt.Scale(
                    domain=["Completed on Platform 🐶", "Leaked to Venmo Off-App 📱", "Unmatched / Shortage 😿"],
                    range=["#0284C7", "#F97316", "#94A3B8"]
                ))
            )
            text = base.transform_filter("datum.Walks > 0").mark_text(
                radius=85, size=12, fontWeight="bold"
            ).encode(
                text="Percent:N",
                color=alt.value("#F8FAFC")
            )
            fate_chart = (arc + text).properties(height=280)
            st.altair_chart(fate_chart, use_container_width=True)

            st.markdown(f"""
            - **🐾 Completed Walks:** `{sc.completed_walks:,}` (${r2.gross_merchandise_value/1_000_000:.2f}M GMV)
            - **📱 Walks Leaked to Venmo:** `{sc.walks_lost_to_leakage:,}` (${r2.gmv_lost_to_venmo/1_000_000:.2f}M lost GMV)
            - **🐩 Walkers Lost to BarkBuddy:** `{r2.walkers_lost_to_rival:,}` ({int(r2.walker_defection_rate*100)}% defection)
            """)

        with col_f2:
            st.markdown("### 🎲 Fleet Quality & Efficiency Evolution")
            col_eq1, col_eq2 = st.columns(2)
            with col_eq1:
                st.metric(
                    "Round 1 Fleet Quality",
                    f"{r1.owners_per_walker} owners/wk",
                    r1.walker_efficiency_rating,
                    delta_color="off"
                )
            with col_eq2:
                st.metric(
                    "Round 2 Fleet Quality",
                    f"{r2.owners_per_walker} owners/wk",
                    r2.walker_efficiency_rating,
                    delta_color="off"
                )
            st.caption("Walker capacity is randomly drawn between 5 and 12 owners per walker each round based on walker experience, stamina, and route efficiency.")

            st.markdown("### 📑 Strategic Executive Debrief")
            st.markdown(sc.overall_debrief)
            st.markdown("---")
            st.markdown(f"**Round 1 Performance:**\n\n{sc.feedback_r1}")
            st.markdown("---")
            st.markdown(f"**Round 2 Defense:**\n\n{sc.feedback_r2}")

        st.write("")
        st.divider()

        def _navigate_to_leaderboard():
            st.session_state.main_tab_nav = TAB_LEADERBOARD
            st.session_state.scroll_to_top_trigger += 1

        nav_lb_clicked = st.button(
            "🏆 Take me to the Leaderboard",
            type="primary",
            use_container_width=True,
            key="btn_take_me_to_leaderboard",
            on_click=_navigate_to_leaderboard,
        )
        if nav_lb_clicked and st.session_state.main_tab_nav != TAB_LEADERBOARD:
            _navigate_to_leaderboard()
            st.rerun()


# =============================================================================
# TAB 2: LIVE CLASS LEADERBOARD & INSTRUCTOR DEBRIEF
# =============================================================================
with tab_leaderboard:
    st.header("🏆🐕 Live Class Leaderboard")

    # Leaderboard Controls: Manual Refresh & Auto-Polling Toggle (Conserves Mobile Battery & Data)
    col_lb_head, col_lb_ctrl = st.columns([3, 2], vertical_alignment="center")
    with col_lb_head:
        st.caption("Classroom rankings across all student founder ventures.")
    with col_lb_ctrl:
        c_ref, c_tog = st.columns([1, 2], vertical_alignment="center")
        with c_ref:
            if st.button("🔄 Refresh", help="Manually refresh standings", use_container_width=True):
                st.rerun()
        with c_tog:
            auto_poll = st.toggle(
                "⚡ Auto-Refresh (3s)",
                value=False,
                help="Enable 3-second live refresh. Recommended for classroom projector; leave off on mobile to conserve battery."
            )

    poll_interval = 3 if auto_poll else None

    @st.fragment(run_every=poll_interval)
    def render_live_leaderboard():
        show_full = leaderboard.get_app_setting("show_full_leaderboard", "false") == "true"
        df = leaderboard.get_leaderboard_dataframe(full_details=show_full)

        # 🏆 Your Standing Highlight Card (Instantly visible on mobile without scrolling)
        curr_player = st.session_state.get("player_name", "").strip()
        curr_pin = st.session_state.get("player_pin", "").strip()
        if curr_player and not df.empty:
            my_rows = df[df["Founder"].astype(str).str.strip().str.lower() == curr_player.lower()]
            if my_rows.empty and curr_pin:
                my_rows = df[df["Founder"].astype(str).str.endswith(f"_{curr_pin}")]
            if not my_rows.empty:
                my_row = my_rows.iloc[0]
                rank_str = my_row["Rank"]
                comp_score = my_row["Composite Score"]
                val_str = my_row["Valuation ($M)"]
                comp_name = st.session_state.get("company_name", "Your Startup")
                comp_display = comp_score if comp_score != "-" else "In Progress"
                val_display = val_str if val_str != "-" else "In Progress"
                st.markdown(f"""
                <div class="metric-card" style="border: 2px solid #60A5FA !important; margin-bottom: 16px;">
                    <div class="metric-title" style="color: #60A5FA !important;">🏆 Your Current Standing</div>
                    <div style="display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 8px; margin-top: 6px;">
                        <div>
                            <span class="metric-value" style="color: #60A5FA;">{rank_str}</span>
                            <span style="font-size: 1.1rem; color: #F8FAFC; margin-left: 10px; font-weight: 600;">{comp_name}</span>
                        </div>
                        <div style="font-size: 1rem; color: #F8FAFC;">
                            Composite Score: <strong style="color: #60A5FA;">{comp_display}</strong> | 
                            Valuation: <strong style="color: #60A5FA;">{val_display}</strong>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # Summary counts
        analytics = leaderboard.get_class_analytics()
        col_c1, col_c2, col_c3, col_c4 = st.columns(4)
        col_c1.metric("🐕 Registered Founders", analytics["total_founders"])
        col_c2.metric("✅ Completed Attempts", analytics["completed_count"])
        col_c3.metric("⏳ In Progress", analytics["in_r1_count"] + analytics["in_r2_count"])
        col_c4.metric("⭐ Avg Composite Score", f"{analytics['avg_composite']:.1f}")

        if not show_full:
            st.caption("🔒 Standings view: Showing Composite Score & Valuation. Use the Instructor Control Panel below to reveal full breakdown.")
        else:
            st.caption("🔓 Full breakdown view: Company, Status, Liquidity %, Retention %, and Take Rates revealed.")

        st.markdown("### 📊 Ranked Platform Standings")

        if df.empty:
            st.info("🐶 No founders registered yet. Tell students to scan the QR code and claim seed funding in the Player Console!")
        else:
            col_cfg = {
                "Rank": st.column_config.TextColumn(width="small"),
                "Founder": st.column_config.TextColumn(width="medium"),
                "Composite Score": st.column_config.TextColumn(
                    width="small",
                    help="Composite Score: Overall platform performance index (0–100) weighting Marketplace Liquidity, Platform Retention, and Enterprise Valuation equally (1/3 each)."
                ),
                "Valuation ($M)": st.column_config.TextColumn(
                    width="small",
                    help="Enterprise Valuation: Total financial worth of the business based on recurring operating earnings multiplied by an industry multiple (8×–14× based on retention quality) plus remaining cash reserves."
                ),
            }
            if show_full:
                col_cfg.update({
                    "Marketplace Company": st.column_config.TextColumn(width="medium"),
                    "Status": st.column_config.TextColumn(width="small"),
                    "Liquidity %": st.column_config.TextColumn(
                        width="small",
                        help="Marketplace Liquidity: The percentage of desired service transactions successfully matched between buyers and sellers without excessive wait times or order cancellations."
                    ),
                    "Retention %": st.column_config.TextColumn(
                        width="small",
                        help="Platform Retention: The percentage of buyers and sellers who remain active on your platform rather than defecting to competitors or bypassing platform fees via Venmo."
                    ),
                    "R1 Take": st.column_config.TextColumn(width="small", help="Round 1 commission rate charged per walk ($30 base fee)."),
                    "R2 Take": st.column_config.TextColumn(width="small", help="Round 2 commission rate. Higher take rates increase revenue per transaction but risk user defection and off-platform disintermediation."),
                })

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config=col_cfg,
            )

            with st.expander("♿ Accessible Table View (Screen Reader Friendly)"):
                st.table(df)

    render_live_leaderboard()

    # Class-Wide Strategy Analytics (Public for all participants and classroom debrief)
    st.markdown("### 📈 Class-Wide Strategy Analytics")
    analytics = leaderboard.get_class_analytics()
    an_col1, an_col2, an_col3, an_col4 = st.columns(4)
    an_col1.metric("Avg R1 Take Rate", f"{analytics['avg_r1_take']:.1f}%")
    an_col2.metric("Avg R2 Take Rate", f"{analytics['avg_r2_take']:.1f}%")
    an_col3.metric("Total Class GMV Leaked to Venmo", f"${analytics['total_leakage_gmv']/1_000_000:.2f}M")
    an_col4.metric("Avg Enterprise Valuation", f"${analytics['avg_valuation']:.2f}M")

    # R1 Strategy distribution (Color-Blind Safe Palette with Direct Count Labels)
    st.markdown("### 🐕‍🦺 Round 1 Liquidity Decisions")
    r1_states = analytics["r1_states"]
    if r1_states:
        state_df = pd.DataFrame([
            {"Strategy Outcome": k.replace("_", " ").title(), "Student Count": v}
            for k, v in r1_states.items()
        ])
        state_chart = alt.Chart(state_df).mark_bar(cornerRadius=4).encode(
            x=alt.X("Strategy Outcome:N", title="Strategy Outcome"),
            y=alt.Y("Student Count:Q", title="Student Count"),
            color=alt.Color("Strategy Outcome:N", legend=alt.Legend(orient="bottom", title=None), scale=alt.Scale(
                domain=["Balanced", "Demand Overload", "Supply Starvation", "Inactive"],
                range=["#0284C7", "#F87171", "#F59E0B", "#94A3B8"]
            )),
            tooltip=["Strategy Outcome", "Student Count"]
        )
        text = state_chart.mark_text(dy=-10).encode(
            text="Student Count:Q",
            color=alt.value("#F8FAFC")
        )
        st.altair_chart((state_chart + text).properties(height=240), use_container_width=True)

    st.divider()

    # Dedicated Instructor Page Link (Opens in New Tab)
    st.markdown("""
    <div class="callout-box" style="border-left-color: #60A5FA;">
        <h3 style="margin-top: 0; color: #F8FAFC;">🔒 Instructor Control Panel</h3>
        Classroom projection settings, student grade CSV exports, master teaching benchmark reveal, and database reset tools are accessible in a dedicated, secure instructor tab.
    </div>
    """, unsafe_allow_html=True)
    instructor_tab_url = f"{app_access_url}?view=instructor"
    col_inst_btn, _ = st.columns([1, 1])
    with col_inst_btn:
        st.link_button(
            "🔐 Open Instructor Control Panel (New Tab)",
            url=instructor_tab_url,
            type="secondary",
            use_container_width=True,
        )
    st.caption(f"Instructor direct URL: `{instructor_tab_url}`")


# Render Version & Date Footer (Left-justified at the very bottom of the page)
render_app_footer()
