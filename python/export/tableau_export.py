"""
tableau_export.py — Export SQL query results as CSVs for Tableau.

Runs the analytical queries from sql/duckdb/ and exports results
as clean CSV files. Also exports a loan-level detail file with
key columns for maximum flexibility in Tableau.

Usage:
    python tableau_export.py
    python tableau_export.py --db data/mortgage_analytics.duckdb --output data/clean/tableau/
"""

import os
import sys
import argparse

import duckdb
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "etl"))
from sql_runner import run_query, run_query_string


# Queries to export and their output filenames
QUERY_EXPORTS = [
    ("sql/duckdb/02_portfolio_summary.sql", "portfolio_summary.csv"),
    ("sql/duckdb/03_delinquency_analysis.sql", "delinquency_by_dpd.csv"),
    ("sql/duckdb/04_roll_rates.sql", "roll_rates.csv"),
    ("sql/duckdb/05_risk_segmentation.sql", "risk_segments.csv"),
    ("sql/duckdb/07_vintage_comparison.sql", "vintage_comparison.csv"),
    ("sql/duckdb/08_geographic_analysis.sql", "geographic.csv"),
]

# Columns to include in the loan-level detail export
DETAIL_COLUMNS = """
    loan_id,
    pool_prefix,
    CAST(orig_year AS INTEGER) AS orig_year,
    orig_quarter,
    property_state,
    credit_score,
    credit_score_band,
    ltv,
    ltv_bucket,
    dti,
    orig_interest_rate,
    rate_bucket,
    orig_loan_amount,
    current_upb,
    loan_age,
    channel,
    property_type,
    occupancy_status,
    loan_purpose,
    num_borrowers,
    first_time_homebuyer,
    dpd_bucket,
    delinquency_status,
    is_delinquent,
    is_seriously_delinquent,
    current_credit_score,
    servicer_name,
    payment_history
"""


def export_all(db_path, output_dir, sql_dir="sql/duckdb/"):
    """Export all query results and loan-level detail to CSV."""

    os.makedirs(output_dir, exist_ok=True)
    print(f"Exporting Tableau data from: {db_path}")
    print(f"Output directory: {output_dir}")
    print()

    # ── Export pre-aggregated query results ──
    for sql_file, csv_name in QUERY_EXPORTS:
        # Resolve path relative to project root
        if not os.path.exists(sql_file):
            # Try relative to script location
            alt = os.path.join(os.path.dirname(__file__), "..", "..", sql_file)
            if os.path.exists(alt):
                sql_file = alt
            else:
                print(f"  SKIP: {sql_file} not found")
                continue

        df = run_query(sql_file, db_path)
        out_path = os.path.join(output_dir, csv_name)
        df.to_csv(out_path, index=False)
        print(f"  {csv_name}: {len(df):,} rows")

    # ── Export loan-level detail ──
    print()
    print("  Exporting loan-level detail (this may take a moment)...")

    detail_sql = f"SELECT {DETAIL_COLUMNS} FROM loans"
    df_detail = run_query_string(detail_sql, db_path)
    detail_path = os.path.join(output_dir, "loans_detail.csv")
    df_detail.to_csv(detail_path, index=False)
    size_mb = os.path.getsize(detail_path) / (1024 * 1024)
    print(f"  loans_detail.csv: {len(df_detail):,} rows ({size_mb:.1f} MB)")

    # ── Summary ──
    print()
    total_files = len(QUERY_EXPORTS) + 1
    print(f"Done. {total_files} files exported to {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export data for Tableau")
    parser.add_argument("--db", "-d", default="data/mortgage_analytics.duckdb")
    parser.add_argument("--output", "-o", default="data/clean/tableau/")
    args = parser.parse_args()

    export_all(args.db, args.output)
