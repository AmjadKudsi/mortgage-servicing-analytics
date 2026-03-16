"""
portfolio_export.py — Export data as JSON for the GitHub Pages portfolio.

Exports SQL query results and ML artifacts as lightweight JSON files
that the portfolio's JavaScript loads for interactive displays.

Usage:
    python portfolio_export.py
    python portfolio_export.py --db data/mortgage_analytics.duckdb
"""

import os
import sys
import json
import argparse

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "etl"))
from sql_runner import run_query, run_query_string


def export_all(db_path, ml_dir, output_dir):
    """Export all data needed by the portfolio site."""
    os.makedirs(output_dir, exist_ok=True)
    print(f"Exporting portfolio data...")

    # ── Portfolio summary ──
    summary = run_query_string("""
        SELECT COUNT(*) AS total_loans,
               ROUND(SUM(current_upb)/1e9, 1) AS upb_billions,
               ROUND(100.0 * SUM(is_delinquent)/COUNT(*), 2) AS dlq_rate,
               ROUND(100.0 * SUM(is_seriously_delinquent)/COUNT(*), 2) AS serious_dlq,
               ROUND(AVG(credit_score), 0) AS avg_fico,
               ROUND(AVG(orig_interest_rate), 2) AS avg_rate,
               COUNT(DISTINCT CAST(orig_year AS INTEGER)) AS vintage_count
        FROM loans
    """, db_path).iloc[0].to_dict()
    # Convert numpy types to native Python
    summary = {k: float(v) if hasattr(v, 'item') else v for k, v in summary.items()}
    _save(summary, output_dir, "summary.json")

    # ── Vintage comparison ──
    vintage_sql = _find_sql("sql/duckdb/07_vintage_comparison.sql")
    if vintage_sql:
        df = run_query(vintage_sql, db_path)
        df["orig_year"] = df["orig_year"].astype(int)
        _save(df.to_dict("records"), output_dir, "vintage.json")

    # ── Geographic ──
    geo_sql = _find_sql("sql/duckdb/08_geographic_analysis.sql")
    if geo_sql:
        df = run_query(geo_sql, db_path)
        df["loans"] = df["loans"].astype(int)
        _save(df.to_dict("records"), output_dir, "geographic.json")

    # ── DPD distribution ──
    dpd_sql = _find_sql("sql/duckdb/03_delinquency_analysis.sql")
    if dpd_sql:
        df = run_query(dpd_sql, db_path)
        df["loans"] = df["loans"].astype(int)
        _save(df.to_dict("records"), output_dir, "delinquency.json")

    # ── Roll rates ──
    roll_sql = _find_sql("sql/duckdb/04_roll_rates.sql")
    if roll_sql:
        df = run_query(roll_sql, db_path)
        _save(df.to_dict("records"), output_dir, "roll_rates.json")

    # ── ML evaluation report ──
    eval_path = os.path.join(ml_dir, "evaluation_report.json")
    if os.path.exists(eval_path):
        with open(eval_path) as f:
            eval_data = json.load(f)
        _save(eval_data, output_dir, "evaluation.json")
        print(f"  evaluation.json")

    # ── Risk segments ──
    seg_path = os.path.join(ml_dir, "risk_segments.csv")
    if os.path.exists(seg_path):
        df = pd.read_csv(seg_path)
        df["loans"] = df["loans"].astype(int)
        df["orig_year"] = df["orig_year"].astype(int)
        _save(df.head(30).to_dict("records"), output_dir, "risk_segments.json")

    print(f"Done. Files exported to {output_dir}")


def _save(data, output_dir, filename):
    """Save data as JSON."""
    path = os.path.join(output_dir, filename)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"  {filename}")


def _find_sql(relative_path):
    """Find SQL file relative to project root or script location."""
    if os.path.exists(relative_path):
        return relative_path
    alt = os.path.join(os.path.dirname(__file__), "..", "..", relative_path)
    return alt if os.path.exists(alt) else None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export portfolio data")
    parser.add_argument("--db", "-d", default="data/mortgage_analytics.duckdb")
    parser.add_argument("--ml", "-m", default="python/ml/model_artifacts")
    parser.add_argument("--output", "-o", default="docs/data/")
    args = parser.parse_args()
    export_all(args.db, args.ml, args.output)
