"""
Deterministic Business Intelligence Metrics Engine.
Computes precise mathematical aggregations, pipeline health,
weighted forecasts, billing reconciliations, and operational risks in pure Python.
"""

from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np


def calculate_pipeline_summary(df: pd.DataFrame, sector: Optional[str] = None) -> Dict[str, Any]:
    """Calculate core sales funnel metrics for Deals."""
    if df.empty:
        return {"error": "Deals board is empty"}

    filtered = df.copy()
    if sector and sector != "All":
        filtered = filtered[filtered["Sector"].astype(str).str.lower() == sector.lower()]

    total_deals = len(filtered)
    status_counts = filtered["Deal Status"].value_counts().to_dict()

    open_deals = filtered[filtered["Deal Status"] == "Open"]
    won_deals = filtered[filtered["Deal Status"] == "Won"]
    dead_deals = filtered[filtered["Deal Status"].isin(["Dead", "Lost"])]

    open_pipeline_val = open_deals["Deal_Value"].dropna().sum()
    won_val = won_deals["Deal_Value"].dropna().sum()

    # Data quality caveats
    missing_vals_open = open_deals["Deal_Value"].isna().sum()
    caveats = []
    if missing_vals_open > 0:
        caveats.append(
            f"Deal Value is missing for {missing_vals_open} of {len(open_deals)} open deals. "
            "Pipeline value represents only populated records."
        )

    return {
        "sector_filter": sector or "All",
        "total_deals_count": total_deals,
        "open_deals_count": len(open_deals),
        "won_deals_count": len(won_deals),
        "dead_deals_count": len(dead_deals),
        "total_open_pipeline_value": float(open_pipeline_val),
        "total_won_value": float(won_val),
        "status_distribution": status_counts,
        "caveats": caveats,
    }


def calculate_weighted_pipeline(df: pd.DataFrame, sector: Optional[str] = None) -> Dict[str, Any]:
    """Calculate closure-probability-weighted pipeline value."""
    if df.empty:
        return {"error": "Deals board is empty"}

    open_deals = df[df["Deal Status"] == "Open"].copy()
    if sector and sector != "All":
        open_deals = open_deals[open_deals["Sector"].astype(str).str.lower() == sector.lower()]

    total_open = len(open_deals)
    valid_prob = open_deals.dropna(subset=["Probability_Weight", "Deal_Value"])
    
    missing_prob_count = open_deals["Probability_Weight"].isna().sum()
    missing_val_count = open_deals["Deal_Value"].isna().sum()

    weighted_value = (valid_prob["Deal_Value"] * valid_prob["Probability_Weight"]).sum()
    unweighted_usable_value = valid_prob["Deal_Value"].sum()

    caveats = [
        f"Closure Probability is missing for {missing_prob_count} of {total_open} open deals ({round((missing_prob_count/max(1, total_open))*100, 1)}%).",
        f"Weighted pipeline strictly aggregates the {len(valid_prob)} deals containing both a valid deal value and a closure probability."
    ]

    return {
        "sector_filter": sector or "All",
        "total_open_deals": total_open,
        "deals_used_in_weighted_calc": len(valid_prob),
        "weighted_pipeline_value": float(weighted_value),
        "unweighted_usable_value": float(unweighted_usable_value),
        "high_confidence_deals_count": int((open_deals["Probability_Weight"] >= 0.8).sum()),
        "medium_confidence_deals_count": int(((open_deals["Probability_Weight"] >= 0.4) & (open_deals["Probability_Weight"] < 0.8)).sum()),
        "low_confidence_deals_count": int((open_deals["Probability_Weight"] < 0.4).sum()),
        "caveats": caveats,
    }


def calculate_deals_by_sector(df: pd.DataFrame) -> Dict[str, Any]:
    """Aggregate sales pipeline opportunities by industry sector safely."""
    if df.empty:
        return {"error": "Deals board is empty"}

    open_deals = df[df["Deal Status"] == "Open"].copy()
    if open_deals.empty:
        return {"sector_breakdown": [], "top_sector": "None", "caveats": ["No open deals found."]}

    # Identify primary identifier column safely
    name_col = "Deal_Name" if "Deal_Name" in open_deals.columns else ("Item Name" if "Item Name" in open_deals.columns else open_deals.columns[0])

    sector_summary = (
        open_deals.groupby("Sector", as_index=False)
        .agg(
            open_deals_count=(name_col, "count"),
            total_pipeline_value=("Deal_Value", "sum"),
            deals_with_missing_value=("Deal_Value", lambda x: x.isna().sum())
        )
        .sort_values(by="total_pipeline_value", ascending=False)
    )

    top_sector = sector_summary.iloc[0]["Sector"] if not sector_summary.empty else "N/A"

    return {
        "sector_breakdown": sector_summary.to_dict(orient="records"),
        "top_sector": top_sector,
        "caveats": ["Deals without assigned sectors are categorized under 'Unspecified'."]
    }


def calculate_deals_by_stage(df: pd.DataFrame, sector: Optional[str] = None) -> Dict[str, Any]:
    """Aggregate deal distribution across sales funnel stages."""
    if df.empty:
        return {"error": "Deals board is empty"}

    filtered = df.copy()
    if sector and sector != "All":
        filtered = filtered[filtered["Sector"].astype(str).str.lower() == sector.lower()]

    stage_summary = (
        filtered.groupby("Deal Stage")
        .agg(
            count=("Deal Name", "count"),
            total_value=("Deal_Value", "sum")
        )
        .reset_index()
        .sort_values(by="count", ascending=False)
    )

    return {
        "sector_filter": sector or "All",
        "stage_breakdown": stage_summary.to_dict(orient="records"),
        "caveats": []
    }


def calculate_work_orders_summary(df: pd.DataFrame, sector: Optional[str] = None) -> Dict[str, Any]:
    """Calculate operational project execution metrics."""
    if df.empty:
        return {"error": "Work Orders board is empty"}

    filtered = df.copy()
    if sector and sector != "All":
        filtered = filtered[filtered["Sector"].astype(str).str.lower() == sector.lower()]

    exec_counts = filtered["Execution_Status"].value_counts().to_dict()
    total_wo = len(filtered)
    completed = filtered[filtered["Execution_Status"] == "Completed"]
    ongoing = filtered[filtered["Execution_Status"] == "Ongoing"]
    not_started = filtered[filtered["Execution_Status"] == "Not Started"]

    contracted_val = filtered["Contract_Value_Incl_GST"].dropna().sum()

    return {
        "sector_filter": sector or "All",
        "total_work_orders": total_wo,
        "completed_count": len(completed),
        "ongoing_count": len(ongoing),
        "not_started_count": len(not_started),
        "execution_distribution": exec_counts,
        "total_contracted_value_incl_gst": float(contracted_val),
        "completion_rate_percentage": round((len(completed) / max(1, total_wo)) * 100, 1),
        "caveats": []
    }


def calculate_billing_and_collections(df: pd.DataFrame, sector: Optional[str] = None) -> Dict[str, Any]:
    """Reconcile contracted, billed, and collected cash balances."""
    if df.empty:
        return {"error": "Work Orders board is empty"}

    filtered = df.copy()
    if sector and sector != "All":
        filtered = filtered[filtered["Sector"].astype(str).str.lower() == sector.lower()]

    contracted = filtered["Contract_Value_Incl_GST"].dropna().sum()
    billed = filtered["Billed_Value_Incl_GST"].dropna().sum()
    collected = filtered["Collected_Amount_Incl_GST"].dropna().sum()
    receivable = filtered["Amount_Receivable"].dropna().sum()
    to_be_billed = filtered["To_Be_Billed_Incl_GST"].dropna().sum()

    return {
        "sector_filter": sector or "All",
        "total_contracted_value_incl_gst": float(contracted),
        "total_billed_value_incl_gst": float(billed),
        "total_collected_amount_incl_gst": float(collected),
        "total_amount_receivable": float(receivable),
        "total_to_be_billed_incl_gst": float(to_be_billed),
        "collection_efficiency_percentage": round((collected / max(1.0, billed)) * 100, 1),
        "caveats": [
            "Financial values include GST.",
            "Accounts Receivable (AR) reflects currently outstanding customer balances."
        ]
    }


def calculate_receivables_summary(df: pd.DataFrame, sector: Optional[str] = None) -> Dict[str, Any]:
    """Inspect accounts receivable and highlight negative balance anomalies."""
    if df.empty:
        return {"error": "Work Orders board is empty"}

    filtered = df.copy()
    if sector and sector != "All":
        filtered = filtered[filtered["Sector"].astype(str).str.lower() == sector.lower()]

    total_ar = filtered["Amount_Receivable"].dropna().sum()
    positive_ar = filtered[filtered["Amount_Receivable"] > 0]
    negative_ar = filtered[filtered["Amount_Receivable"] < 0]

    caveats = []
    if len(negative_ar) > 0:
        caveats.append(
            f"Detected {len(negative_ar)} work order records with negative receivables (totaling ₹{abs(negative_ar['Amount_Receivable'].sum()):,.2f}). "
            "These typically indicate client advances or over-billing adjustments and are flagged for finance review."
        )

    return {
        "sector_filter": sector or "All",
        "total_outstanding_ar": float(total_ar),
        "active_ar_accounts_count": len(positive_ar),
        "negative_ar_records_count": len(negative_ar),
        "caveats": caveats
    }


def calculate_at_risk_projects(df: pd.DataFrame, sector: Optional[str] = None) -> Dict[str, Any]:
    """Identify operationally stalled or high-risk projects."""
    if df.empty:
        return {"error": "Work Orders board is empty"}

    filtered = df.copy()
    if sector and sector != "All":
        filtered = filtered[filtered["Sector"].astype(str).str.lower() == sector.lower()]

    risk_statuses = ["Pause / struck", "Details pending from Client"]
    at_risk_df = filtered[filtered["Execution_Status"].isin(risk_statuses)]

    risk_list = []
    for _, row in at_risk_df.iterrows():
        risk_list.append({
            "deal_name": row.get("Deal_Name", "Unknown"),
            "customer": row.get("Customer_Code", "Unknown"),
            "serial": row.get("Serial_Number", "N/A"),
            "status": row.get("Execution_Status", "N/A"),
            "contract_value": row.get("Contract_Value_Incl_GST", 0.0),
        })

    return {
        "sector_filter": sector or "All",
        "total_at_risk_count": len(at_risk_df),
        "at_risk_projects": risk_list,
        "caveats": [
            f"Flagged {len(at_risk_df)} projects currently categorized as 'Pause / struck' or 'Details pending from Client'."
        ]
    }


def calculate_leadership_summary(
    deals_df: pd.DataFrame,
    wo_df: pd.DataFrame,
    sector: Optional[str] = None
) -> Dict[str, Any]:
    """Generate cross-board executive briefing across sales, operations, and cash."""
    pipeline = calculate_pipeline_summary(deals_df, sector=sector)
    weighted = calculate_weighted_pipeline(deals_df, sector=sector)
    execution = calculate_work_orders_summary(wo_df, sector=sector)
    finances = calculate_billing_and_collections(wo_df, sector=sector)
    risks = calculate_at_risk_projects(wo_df, sector=sector)

    combined_caveats = []
    for sub in [pipeline, weighted, finances, risks]:
        combined_caveats.extend(sub.get("caveats", []))

    return {
        "sector_filter": sector or "All",
        "commercial_pipeline_value": pipeline.get("total_open_pipeline_value", 0.0),
        "weighted_pipeline_value": weighted.get("weighted_pipeline_value", 0.0),
        "won_commercial_value": pipeline.get("total_won_value", 0.0),
        "total_work_orders": execution.get("total_work_orders", 0),
        "completed_projects": execution.get("completed_count", 0),
        "at_risk_projects_count": risks.get("total_at_risk_count", 0),
        "contracted_value_incl_gst": finances.get("total_contracted_value_incl_gst", 0.0),
        "billed_value_incl_gst": finances.get("total_billed_value_incl_gst", 0.0),
        "collected_amount_incl_gst": finances.get("total_collected_amount_incl_gst", 0.0),
        "outstanding_receivables": finances.get("total_amount_receivable", 0.0),
        "caveats": combined_caveats,
    }


def audit_data_quality(deals_df: pd.DataFrame, wo_df: pd.DataFrame) -> Dict[str, Any]:
    """Comprehensive data health audit across both boards."""
    total_deals = len(deals_df) if not deals_df.empty else 0
    missing_val = deals_df["Deal_Value"].isna().sum() if not deals_df.empty and "Deal_Value" in deals_df.columns else 0
    missing_prob = deals_df["Probability_Weight"].isna().sum() if not deals_df.empty and "Probability_Weight" in deals_df.columns else 0

    total_wo = len(wo_df) if not wo_df.empty else 0
    neg_ar = (wo_df["Amount_Receivable"] < 0).sum() if not wo_df.empty and "Amount_Receivable" in wo_df.columns else 0

    return {
        "total_deal_records": total_deals,
        "deals_missing_deal_value": int(missing_val),
        "deals_missing_probability": int(missing_prob),
        "probability_missing_percentage": round((missing_prob / max(1, total_deals)) * 100, 1),
        "total_work_orders": total_wo,
        "work_orders_negative_receivables": int(neg_ar),
    }