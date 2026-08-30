"""
Data normalization layer for Deals and Work Orders boards.
Handles missing values, dirty headers, currency cleanup, date parsing,
and categorical alignment.
"""

import re
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple


# Probability map for weighted pipeline calculations
PROBABILITY_MAP = {
    "high": 0.80,
    "medium": 0.50,
    "low": 0.20
}


def clean_string(val: Any) -> str:
    """Strip whitespace and normalize casing for general text fields."""
    if pd.isna(val) or val is None:
        return ""
    return str(val).strip()


def parse_numeric(val: Any) -> float:
    """Parse numeric and currency strings safely into float; returns np.nan on failure."""
    if pd.isna(val) or val is None:
        return np.nan
    if isinstance(val, (int, float)):
        return float(val)
    
    # Remove currency symbols, commas, and whitespace
    cleaned = re.sub(r"[^\d.-]", "", str(val).strip())
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return np.nan


def parse_date(val: Any) -> pd.Timestamp:
    """Resiliently parse mixed dates into pandas Timestamp."""
    if pd.isna(val) or val is None:
        return pd.NaT
    try:
        return pd.to_datetime(val, errors="coerce")
    except Exception:
        return pd.NaT


def normalize_deals_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and standardize Deals DataFrame.
    Filters duplicated headers and normalizes status, stage, sector, and value.
    """
    if df.empty:
        return df

    cleaned_df = df.copy()

    # Normalize column names: strip whitespace
    cleaned_df.columns = [str(col).strip() for col in cleaned_df.columns]

    # Drop duplicated mid-sheet header rows (where Deal Status == 'Deal Status')
    if "Deal Status" in cleaned_df.columns:
        cleaned_df = cleaned_df[cleaned_df["Deal Status"].astype(str).str.strip() != "Deal Status"]

    # Normalize string identifiers
    if "Deal Name" in cleaned_df.columns:
        cleaned_df["Deal Name"] = cleaned_df["Deal Name"].fillna("").astype(str).str.strip()
    if "Client Code" in cleaned_df.columns:
        cleaned_df["Client Code"] = cleaned_df["Client Code"].fillna("").astype(str).str.strip().str.upper()
        # Normalized client code suffix (e.g. COMPANY089 -> 089) for safe cross-board matching
        cleaned_df["Client_Code_Clean"] = cleaned_df["Client Code"].str.replace("COMPANY", "", regex=False).str.strip()

    # Normalize Sector
    if "Sector/service" in cleaned_df.columns:
        cleaned_df["Sector"] = cleaned_df["Sector/service"].fillna("Unspecified").astype(str).str.strip()
    elif "Sector" not in cleaned_df.columns:
        cleaned_df["Sector"] = "Unspecified"

    # Normalize Deal Status
    if "Deal Status" in cleaned_df.columns:
        cleaned_df["Deal Status"] = cleaned_df["Deal Status"].fillna("Unknown").astype(str).str.strip().str.capitalize()
    
    # Normalize Deal Stage
    if "Deal Stage" in cleaned_df.columns:
        cleaned_df["Deal Stage"] = cleaned_df["Deal Stage"].fillna("Unassigned").astype(str).str.strip()

    # Parse Monetary Value
    val_col = "Masked Deal value" if "Masked Deal value" in cleaned_df.columns else "Deal Value"
    if val_col in cleaned_df.columns:
        cleaned_df["Deal_Value"] = cleaned_df[val_col].apply(parse_numeric)
    else:
        cleaned_df["Deal_Value"] = np.nan

    # Parse Probability & Numeric Weight
    prob_col = "Closure Probability" if "Closure Probability" in cleaned_df.columns else "Probability"
    if prob_col in cleaned_df.columns:
        cleaned_df["Closure_Probability_Raw"] = cleaned_df[prob_col].fillna("").astype(str).str.strip()
        cleaned_df["Probability_Weight"] = cleaned_df["Closure_Probability_Raw"].str.lower().map(PROBABILITY_MAP)
    else:
        cleaned_df["Closure_Probability_Raw"] = ""
        cleaned_df["Probability_Weight"] = np.nan

    # Dates
    if "Created Date" in cleaned_df.columns:
        cleaned_df["Created_Date"] = cleaned_df["Created Date"].apply(parse_date)
    if "Tentative Close Date" in cleaned_df.columns:
        cleaned_df["Tentative_Close_Date"] = cleaned_df["Tentative Close Date"].apply(parse_date)
    if "Close Date (A)" in cleaned_df.columns:
        cleaned_df["Actual_Close_Date"] = cleaned_df["Close Date (A)"].apply(parse_date)

    return cleaned_df


def normalize_work_orders_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and standardize Work Orders DataFrame.
    Standardizes execution status, sector, contracted amounts, billing, and collections.
    """
    if df.empty:
        return df

    cleaned_df = df.copy()
    cleaned_df.columns = [str(col).strip() for col in cleaned_df.columns]

    # Standardize Identifiers
    if "Deal name masked" in cleaned_df.columns:
        cleaned_df["Deal_Name"] = cleaned_df["Deal name masked"].fillna("").astype(str).str.strip()
    elif "Deal Name" in cleaned_df.columns:
        cleaned_df["Deal_Name"] = cleaned_df["Deal Name"].fillna("").astype(str).str.strip()

    if "Customer Name Code" in cleaned_df.columns:
        cleaned_df["Customer_Code"] = cleaned_df["Customer Name Code"].fillna("").astype(str).str.strip().str.upper()
        # Extract numeric core (e.g. WOCOMPANY_002 -> 002) for entity cross-board matching
        cleaned_df["Client_Code_Clean"] = (
            cleaned_df["Customer_Code"]
            .str.replace("WOCOMPANY_", "", regex=False)
            .str.replace("WOCOMPANY", "", regex=False)
            .str.strip()
        )

    if "Serial #" in cleaned_df.columns:
        cleaned_df["Serial_Number"] = cleaned_df["Serial #"].fillna("").astype(str).str.strip()

    # Execution Status
    if "Execution Status" in cleaned_df.columns:
        cleaned_df["Execution_Status"] = cleaned_df["Execution Status"].fillna("Unassigned").astype(str).str.strip()
    else:
        cleaned_df["Execution_Status"] = "Unassigned"

    # Sector
    if "Sector" in cleaned_df.columns:
        cleaned_df["Sector"] = cleaned_df["Sector"].fillna("Unspecified").astype(str).str.strip()

    # Parse all monetary fields
    financial_mappings = {
        "Amount in Rupees (Excl of GST) (Masked)": "Contract_Value_Excl_GST",
        "Amount in Rupees (Incl of GST) (Masked)": "Contract_Value_Incl_GST",
        "Billed Value in Rupees (Excl of GST.) (Masked)": "Billed_Value_Excl_GST",
        "Billed Value in Rupees (Incl of GST.) (Masked)": "Billed_Value_Incl_GST",
        "Collected Amount in Rupees (Incl of GST.) (Masked)": "Collected_Amount_Incl_GST",
        "Amount to be billed in Rs. (Exl. of GST) (Masked)": "To_Be_Billed_Excl_GST",
        "Amount to be billed in Rs. (Incl. of GST) (Masked)": "To_Be_Billed_Incl_GST",
        "Amount Receivable (Masked)": "Amount_Receivable"
    }

    for raw_col, clean_col in financial_mappings.items():
        if raw_col in cleaned_df.columns:
            cleaned_df[clean_col] = cleaned_df[raw_col].apply(parse_numeric)
        else:
            cleaned_df[clean_col] = np.nan

    # Dates
    date_cols = {
        "Probable Start Date": "Probable_Start_Date",
        "Probable End Date": "Probable_End_Date",
        "Data Delivery Date": "Data_Delivery_Date",
        "Date of PO/LOI": "PO_Date",
        "Last invoice date": "Last_Invoice_Date"
    }

    for raw_date, clean_date in date_cols.items():
        if raw_date in cleaned_df.columns:
            cleaned_df[clean_date] = cleaned_df[raw_date].apply(parse_date)

    return cleaned_df
