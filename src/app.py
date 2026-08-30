"""
Skylark Drones - Executive Business Intelligence AI Agent
Interactive Streamlit Application connecting dynamically to Monday.com.
"""

import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

from src.monday_client import MondayDataClient
from src.agent import SkylarkBIAgent
from src.normalization import normalize_deals_df, normalize_work_orders_df
from src.metrics import audit_data_quality

# Load environment variables
load_dotenv()

st.set_page_config(
    page_title="Skylark Drones | Executive BI Agent",
    page_icon="🚁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# Sidebar Configuration & Dynamic Data Sync
# ---------------------------------------------------------
st.sidebar.title("🚁 Skylark BI Agent")
st.sidebar.caption("Executive Intelligence for Monday.com")

with st.sidebar.expander("🔑 Connection & API Settings", expanded=False):
    monday_token = st.text_input(
        "Monday API Token",
        value=os.getenv("MONDAY_API_TOKEN", ""),
        type="password",
        help="Personal API Token v2 from Monday.com"
    )
    deals_board_id = st.text_input(
        "Deals Board ID",
        value=os.getenv("DEALS_BOARD_ID", "5030962471"),
        help="Numeric Board ID for Deals tracker."
    )
    wo_board_id = st.text_input(
        "Work Orders Board ID",
        value=os.getenv("WORK_ORDERS_BOARD_ID", "5030962593"),
        help="Numeric Board ID for Work Orders tracker."
    )
    gemini_key = st.text_input(
        "Gemini API Key",
        value=os.getenv("GEMINI_API_KEY", ""),
        type="password",
        help="Google Gemini API Key."
    )

refresh_btn = st.sidebar.button("🔄 Refresh Data from Monday.com", use_container_width=True)

# ---------------------------------------------------------
# Dynamic Data Ingestion
# ---------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def get_cached_board_data(token: str, deals_id: str, wo_id: str):
    if not token or not deals_id or not wo_id:
        return None, None, {"status": "unconfigured", "message": "Missing credentials or Board IDs."}

    try:
        client = MondayDataClient(api_token=token)
        health = client.health_check()
        if not isinstance(health, dict) or health.get("status") != "connected":
            msg = health.get("message", "API Authentication Failed") if isinstance(health, dict) else "Auth failed"
            return None, None, {"status": "error", "message": msg}

        raw_deals = client.get_board_dataframe(deals_id)
        raw_wo = client.get_board_dataframe(wo_id)

        clean_deals = normalize_deals_df(raw_deals)
        clean_wo = normalize_work_orders_df(raw_wo)

        user_info = health.get("user", {}) if isinstance(health.get("user"), dict) else {}
        return clean_deals, clean_wo, {"status": "connected", "user": user_info}
    except Exception as e:
        return None, None, {"status": "error", "message": str(e)}

if refresh_btn:
    st.cache_data.clear()

with st.spinner("Connecting to Monday.com API..."):
    deals_df, wo_df, conn_status = get_cached_board_data(monday_token, deals_board_id, wo_board_id)

# ---------------------------------------------------------
# Sidebar Health Status
# ---------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.subheader("📡 Data Feed Health")
if isinstance(conn_status, dict) and conn_status.get("status") == "connected":
    st.sidebar.success(f"Connected to Monday.com API\n\n• Deals Board: `{len(deals_df)} items`\n• Work Orders: `{len(wo_df)} items`")
elif isinstance(conn_status, dict) and conn_status.get("status") == "unconfigured":
    st.sidebar.warning("⚠️ Credentials not configured in .env or sidebar.")
else:
    err_text = conn_status.get("message", "Unknown error") if isinstance(conn_status, dict) else str(conn_status)
    st.sidebar.error(f"❌ Connection Error: {err_text}")

# ---------------------------------------------------------
# Main UI
# ---------------------------------------------------------
st.title("🚁 Skylark Drones - Executive BI Intelligence")
st.markdown("Dynamic conversational analytics across **Sales Pipeline (Deals)** and **Project Execution (Work Orders)**.")

# Quick Action Buttons
st.markdown("**Quick Executive Inquiries:**")
col1, col2, col3, col4 = st.columns(4)
query_to_run = None

if col1.button("📊 Pipeline by Sector", use_container_width=True):
    query_to_run = "What is our sales pipeline breakdown by sector?"
if col2.button("🎯 Weighted Pipeline", use_container_width=True):
    query_to_run = "What is our total weighted pipeline and how is it calculated?"
if col3.button("💰 Billed vs Collected", use_container_width=True):
    query_to_run = "How much has been billed versus collected across all work orders?"
if col4.button("⚡ Leadership Update", use_container_width=True):
    query_to_run = "Give me a comprehensive leadership update combining deals and work orders."

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display Chat Messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("caveats"):
            with st.expander("⚠️ Data Quality Notices & Exclusions", expanded=False):
                for caveat in msg["caveats"]:
                    st.caption(f"• {caveat}")

# Chat Input & Execution
user_input = st.chat_input("Ask a question about sales pipeline, operational risk, billing, or leadership metrics...")
prompt = query_to_run or user_input

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        if deals_df is None or wo_df is None:
            st.error("Cannot query boards. Please check your Monday.com API Token and Board IDs in the sidebar.")
        else:
            with st.spinner("Analyzing operational data and generating executive briefing..."):
                agent = SkylarkBIAgent(gemini_api_key=gemini_key)
                result = agent.answer_query(prompt, deals_df, wo_df)

                st.markdown(result["answer"])
                if result.get("caveats"):
                    with st.expander("⚠️ Data Quality Notices & Exclusions", expanded=False):
                        for c in result["caveats"]:
                            st.caption(f"• {c}")

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result["answer"],
                    "caveats": result.get("caveats", [])
                })

# ---------------------------------------------------------
# Sidebar Data Quality Audit
# ---------------------------------------------------------
with st.sidebar.expander("🔍 Board Data Quality Audit", expanded=False):
    if deals_df is not None and wo_df is not None and not deals_df.empty:
        audit = audit_data_quality(deals_df, wo_df)
        st.write(f"**Deals Records:** {audit.get('total_deal_records')}")
        st.write(f"**Missing Deal Values:** {audit.get('deals_missing_deal_value')}")
        st.write(f"**Missing Probabilities:** {audit.get('deals_missing_probability')} ({audit.get('probability_missing_percentage')}%)")
        st.write(f"**Work Orders:** {audit.get('total_work_orders')}")
        st.write(f"**Negative AR Records:** {audit.get('work_orders_negative_receivables')}")
    else:
        st.caption("Connect to Monday.com to inspect data quality metrics.")