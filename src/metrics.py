import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional

PROBABILITY_WEIGHTS = {
    "High": 0.8,
    "Medium": 0.5,
    "Low": 0.2
}

def calculate_deals_pipeline_metrics(deals_df: pd.DataFrame, sector: Optional[str] = None) -> Dict[str, Any]:
    """Deterministic calculation of Deals pipeline metrics."""
    df = deals_df.copy()
    
    if sector and sector.lower() != "all":
        df = df[df["Sector/service"].astype(str).str.lower() == sector.lower()]
        
    total_records = len(df)
    open_df = df[df["Deal Status"] == "Open"]
    won_df = df[df["Deal Status"] == "Won"]
    dead_df = df[df["Deal Status"] == "Dead"]
    on_hold_df = df[df["Deal Status"] == "On Hold"]
    
    # Financial sums
    total_open_value = open_df["Masked Deal value"].dropna().sum()
    open_with_value_count = open_df["Masked Deal value"].notna().sum()
    open_missing_value_count = len(open_df) - open_with_value_count
    
    total_won_value = won_df["Masked Deal value"].dropna().sum()
    won_with_value_count = won_df["Masked Deal value"].notna().sum()
    
    # Weighted Pipeline (only on open deals with both value and probability)
    open_weighted_candidates = open_df[open_df["Masked Deal value"].notna() & open_df["Closure Probability"].notna()].copy()
    open_weighted_candidates["Weight"] = open_weighted_candidates["Closure Probability"].map(PROBABILITY_WEIGHTS).fillna(0.0)
    open_weighted_candidates["Weighted Value"] = open_weighted_candidates["Masked Deal value"] * open_weighted_candidates["Weight"]
    
    weighted_pipeline_value = open_weighted_candidates["Weighted Value"].sum()
    weighted_records_count = len(open_weighted_candidates)
    missing_prob_count = len(open_df) - open_df["Closure Probability"].notna().sum()
    
    # Sector breakdown for Open Pipeline
    sector_group = (
        open_df.groupby("Sector/service")["Masked Deal value"]
        .agg(["sum", "count"])
        .reset_index()
        .rename(columns={"sum": "Total Open Value", "count": "Open Deals Count"})
        .sort_values(by="Total Open Value", ascending=False)
    )
    
    return {
        "sector_filter": sector or "All",
        "total_deal_records": total_records,
        "counts": {
            "open": len(open_df),
            "won": len(won_df),
            "dead": len(dead_df),
            "on_hold": len(on_hold_df)
        },
        "open_pipeline": {
            "total_unweighted_value": float(total_open_value),
            "deals_with_value": int(open_with_value_count),
            "deals_missing_value": int(open_missing_value_count),
            "weighted_pipeline_value": float(weighted_pipeline_value),
            "weighted_deals_count": int(weighted_records_count),
            "deals_missing_probability": int(missing_prob_count)
        },
        "won_pipeline": {
            "total_won_value": float(total_won_value),
            "won_deals_with_value": int(won_with_value_count)
        },
        "open_by_sector": sector_group.to_dict(orient="records"),
        "caveats": [
            f"Closure probability missing for {missing_prob_count} of {len(open_df)} open deals; weighted value calculated on {weighted_records_count} complete records.",
            f"Deal value is missing for {open_missing_value_count} open deals."
        ]
    }

def calculate_work_order_metrics(wo_df: pd.DataFrame, sector: Optional[str] = None) -> Dict[str, Any]:
    """Deterministic calculation of Work Order operational and financial metrics."""
    df = wo_df.copy()
    
    if sector and sector.lower() != "all":
        df = df[df["Sector"].astype(str).str.lower() == sector.lower()]
        
    total_projects = len(df)
    
    # Execution status breakdown
    exec_counts = df["Execution Status"].value_counts(dropna=False).to_dict()
    
    # Financial metrics
    total_contract_excl_gst = df["Amount in Rupees (Excl of GST) (Masked)"].dropna().sum()
    total_contract_incl_gst = df["Amount in Rupees (Incl of GST) (Masked)"].dropna().sum()
    
    total_billed_incl_gst = df["Billed Value in Rupees (Incl of GST.) (Masked)"].dropna().sum()
    total_collected_incl_gst = df["Collected Amount in Rupees (Incl of GST.) (Masked)"].dropna().sum()
    
    total_ar = df["Amount Receivable (Masked)"].dropna().sum()
    total_to_be_billed_incl_gst = df["Amount to be billed in Rs. (Incl. of GST) (Masked)"].dropna().sum()
    
    # Operational Risks
    at_risk_df = df[df["Execution Status"].isin(["Pause / struck", "Details pending from Client"])]
    at_risk_items = at_risk_df[["Serial #", "Deal name masked", "Customer Name Code", "Execution Status", "Sector"]].to_dict(orient="records")
    
    # Anomaly checks
    negative_ar_count = (df["Amount Receivable (Masked)"] < 0).sum()
    negative_to_bill_count = (df["Amount to be billed in Rs. (Incl. of GST) (Masked)"] < 0).sum()
    
    return {
        "sector_filter": sector or "All",
        "total_work_orders": total_projects,
        "execution_status_breakdown": exec_counts,
        "financials": {
            "total_contract_value_incl_gst": float(total_contract_incl_gst),
            "total_contract_value_excl_gst": float(total_contract_excl_gst),
            "total_billed_incl_gst": float(total_billed_incl_gst),
            "total_collected_incl_gst": float(total_collected_incl_gst),
            "total_receivable_outstanding": float(total_ar),
            "amount_remaining_to_bill_incl_gst": float(total_to_be_billed_incl_gst)
        },
        "operational_risks": {
            "at_risk_count": len(at_risk_df),
            "projects": at_risk_items
        },
        "anomalies": {
            "negative_receivables_count": int(negative_ar_count),
            "negative_to_bill_count": int(negative_to_bill_count)
        },
        "caveats": [
            f"Found {negative_ar_count} accounts with negative receivable balances (likely credit balances or adjustments).",
            f"Found {negative_to_bill_count} records with negative amount-to-bill."
        ]
    }

def calculate_cross_board_summary(deals_df: pd.DataFrame, wo_df: pd.DataFrame, sector: Optional[str] = None) -> Dict[str, Any]:
    """Deterministic unified cross-board commercial and operational summary."""
    deals_metrics = calculate_deals_pipeline_metrics(deals_df, sector=sector)
    wo_metrics = calculate_work_order_metrics(wo_df, sector=sector)
    
    return {
        "sector": sector or "All Sectors",
        "commercial_funnel": {
            "open_deals_count": deals_metrics["counts"]["open"],
            "open_pipeline_value": deals_metrics["open_pipeline"]["total_unweighted_value"],
            "weighted_pipeline_value": deals_metrics["open_pipeline"]["weighted_pipeline_value"],
            "won_deals_count": deals_metrics["counts"]["won"],
            "won_deals_value": deals_metrics["won_pipeline"]["total_won_value"]
        },
        "operational_execution": {
            "total_work_orders": wo_metrics["total_work_orders"],
            "completed": wo_metrics["execution_status_breakdown"].get("Completed", 0),
            "ongoing": wo_metrics["execution_status_breakdown"].get("Ongoing", 0),
            "at_risk": wo_metrics["operational_risks"]["at_risk_count"],
            "contracted_value": wo_metrics["financials"]["total_contract_value_incl_gst"],
            "billed_value": wo_metrics["financials"]["total_billed_incl_gst"],
            "collected_value": wo_metrics["financials"]["total_collected_incl_gst"],
            "outstanding_ar": wo_metrics["financials"]["total_receivable_outstanding"]
        },
        "data_quality_caveats": deals_metrics["caveats"] + wo_metrics["caveats"]
    }
