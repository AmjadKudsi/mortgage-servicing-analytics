"""
cleaner.py — Data cleaning and derived column generation.

Takes a raw DataFrame from the parser, applies type casting,
sentinel replacement, and computes derived columns.
All bucket boundaries and mappings come from the config via schema.
Returns a cleaning report alongside the cleaned DataFrame.
"""

import logging
import pandas as pd

log = logging.getLogger("etl")


def clean(df, schema):
    """
    Clean a parsed DataFrame.

    Steps:
        1. Strip whitespace, replace blanks with null
        2. Cast numeric columns to proper types
        3. Replace sentinel values with null
        4. Compute derived columns (UPB, vintage, buckets, flags)

    Returns:
        tuple: (cleaned DataFrame, cleaning_report dict)
    """
    report = {
        "rows_in": len(df),
        "sentinel_replacements": {},
        "cast_failures": {},
        "null_rates": {},
    }

    # ── 1. Strip whitespace, replace blanks ──
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].str.strip()
    df.replace("", pd.NA, inplace=True)

    # ── 2. Cast numeric columns ──
    for col in schema.float_columns:
        if col in df.columns:
            original_nulls = df[col].isna().sum()
            df[col] = pd.to_numeric(df[col], errors="coerce")
            new_nulls = df[col].isna().sum()
            failures = new_nulls - original_nulls
            if failures > 0:
                report["cast_failures"][col] = int(failures)

    for col in schema.int_columns:
        if col in df.columns:
            original_nulls = df[col].isna().sum()
            df[col] = pd.to_numeric(df[col], errors="coerce")
            new_nulls = df[col].isna().sum()
            failures = new_nulls - original_nulls
            if failures > 0:
                report["cast_failures"][col] = int(failures)

    # ── 3. Replace sentinel values ──
    for col, sentinel_list in schema.sentinels.items():
        if col in df.columns:
            mask = df[col].isin(sentinel_list)
            count = mask.sum()
            if count > 0:
                df.loc[mask, col] = pd.NA
                report["sentinel_replacements"][col] = int(count)

    # ── 4. Derived columns ──
    _derive_current_upb(df)
    _derive_vintage(df)
    _derive_dpd_bucket(df, schema)
    _derive_credit_score_band(df, schema)
    _derive_ltv_bucket(df, schema)
    _derive_rate_bucket(df, schema)
    _derive_flags(df)

    # ── Compute null rates for key columns ──
    key_cols = ["loan_id", "credit_score", "ltv", "dti",
                "delinquency_status", "current_upb", "property_state"]
    for col in key_cols:
        if col in df.columns:
            null_pct = round(100 * df[col].isna().sum() / len(df), 2)
            report["null_rates"][col] = null_pct

    report["rows_out"] = len(df)

    # Log summary
    if report["cast_failures"]:
        log.info(f"  Cast failures: {report['cast_failures']}")
    if report["sentinel_replacements"]:
        total_sents = sum(report["sentinel_replacements"].values())
        log.info(f"  Sentinels replaced: {total_sents:,} across "
                 f"{len(report['sentinel_replacements'])} columns")
    log.info(f"  Cleaned: {report['rows_out']:,} rows, "
             f"key null rates: {report['null_rates']}")

    return df, report


# ── Derived column helpers ──

def _derive_current_upb(df):
    """
    Resolve the UPB split across F40/F41/F42.
    Priority: take the maximum non-zero value across the three fields.
    """
    upb_cols = ["current_ib_upb", "current_actual_upb", "current_deferred_upb"]
    existing = [c for c in upb_cols if c in df.columns]
    if existing:
        df["current_upb"] = df[existing].max(axis=1).fillna(0.0)
    else:
        df["current_upb"] = 0.0


def _derive_vintage(df):
    """Extract orig_year and orig_quarter from orig_date (YYYYMM string)."""
    df["orig_year"] = pd.to_numeric(
        df["orig_date"].astype(str).str[:4], errors="coerce"
    )

    def to_quarter(val):
        try:
            s = str(int(val))
            yr, mo = s[:4], int(s[4:6])
            return f"{yr}Q{(mo - 1) // 3 + 1}"
        except (ValueError, TypeError):
            return pd.NA

    df["orig_quarter"] = df["orig_date"].apply(to_quarter)


def _derive_dpd_bucket(df, schema):
    """Map delinquency_status codes to clean bucket labels."""
    dpd_map = schema.dpd_map
    gte_threshold = schema.dpd_numeric_gte
    default_label = schema.dpd_default

    def classify(status):
        if pd.isna(status):
            return "Unknown"
        s = str(status).strip()
        # Check explicit map first
        if s in dpd_map:
            return dpd_map[s]
        # Check if it's a numeric code >= threshold
        try:
            if int(s) >= gte_threshold:
                return "120_Plus_DPD"
        except ValueError:
            pass
        return default_label

    df["dpd_bucket"] = df["delinquency_status"].apply(classify)


def _derive_credit_score_band(df, schema):
    """Assign credit score to bands defined in config."""
    bands = schema.credit_score_bands

    def classify(score):
        if pd.isna(score):
            return "Unknown"
        s = int(score)
        for low, high, label in bands:
            if low <= s <= high:
                return label
        return "Unknown"

    df["credit_score_band"] = df["credit_score"].apply(classify)


def _derive_ltv_bucket(df, schema):
    """Assign LTV to buckets defined in config."""
    buckets = schema.ltv_buckets

    def classify(ltv):
        if pd.isna(ltv):
            return "Unknown"
        v = int(ltv)
        for low, high, label in buckets:
            if low <= v <= high:
                return label
        return "Unknown"

    df["ltv_bucket"] = df["ltv"].apply(classify)


def _derive_rate_bucket(df, schema):
    """Assign origination interest rate to buckets."""
    buckets = schema.rate_buckets

    def classify(rate):
        if pd.isna(rate):
            return "Unknown"
        r = float(rate)
        for low, high, label in buckets:
            if low <= r <= high:
                return label
        return "Unknown"

    df["rate_bucket"] = df["orig_interest_rate"].apply(classify)


def _derive_flags(df):
    """Binary flags for delinquency status."""
    df["is_delinquent"] = (df["dpd_bucket"] != "Current").astype(int)
    df["is_seriously_delinquent"] = df["dpd_bucket"].isin(
        ["90_DPD", "120_Plus_DPD", "REO_Acquired"]
    ).astype(int)
