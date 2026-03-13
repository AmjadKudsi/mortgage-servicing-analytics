"""
data_quality.py — Automated Data Quality Report Generator.

Runs SQL checks against the DuckDB database, evaluates results
against thresholds from config.yaml, and produces a styled
self-contained HTML report.

Usage:
    python data_quality.py
    python data_quality.py --config python/etl/config.yaml --db data/mortgage_analytics.duckdb
"""

import os
import sys
import argparse
from datetime import datetime

import duckdb
from jinja2 import Environment, FileSystemLoader

# Add parent paths so we can import from etl
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "etl"))
from utils import load_config


def _query(con, sql):
    """Run a SQL string and return list of dicts."""
    result = con.execute(sql).fetchdf()
    return result.to_dict("records")


def _query_one(con, sql):
    """Run a SQL string and return a single dict."""
    rows = _query(con, sql)
    return rows[0] if rows else {}


def build_report_data(con, config):
    """Gather all DQ check results into a single dict for the template."""

    total = con.execute("SELECT COUNT(*) FROM loans").fetchone()[0]
    thresholds = config.get("validation", {})
    critical = thresholds.get("max_null_pct_critical", {})
    warning = thresholds.get("max_null_pct_warning", {})
    min_per_pool = thresholds.get("min_loans_per_file", 100)

    data = {}

    # ── 1. Load Summary ──
    summary = _query_one(con, """
        SELECT
            COUNT(*) AS total_loans,
            ROUND(SUM(current_upb), 0) AS total_upb,
            COUNT(DISTINCT pool_prefix) AS pools_loaded,
            COUNT(DISTINCT property_state) AS states_covered,
            CAST(MIN(orig_year) AS INTEGER) AS earliest_vintage,
            CAST(MAX(orig_year) AS INTEGER) AS latest_vintage
        FROM loans
    """)
    data["summary"] = summary

    # ── 2. Completeness ──
    check_cols = [
        "loan_id", "credit_score", "ltv", "dti", "current_upb",
        "delinquency_status", "property_state", "orig_interest_rate",
        "payment_history", "current_credit_score",
    ]
    completeness = []
    for col in check_cols:
        null_count = con.execute(
            f"SELECT COUNT(*) FROM loans WHERE {col} IS NULL"
        ).fetchone()[0]
        null_pct = round(100 * null_count / total, 3) if total > 0 else 0

        # Determine threshold and status
        if col in critical:
            threshold = critical[col]
            status = "FAIL" if null_pct > threshold else "PASS"
        elif col in warning:
            threshold = warning[col]
            status = "WARN" if null_pct > threshold else "PASS"
        else:
            threshold = 10.0  # default
            status = "WARN" if null_pct > threshold else "PASS"

        completeness.append({
            "column": col,
            "null_pct": null_pct,
            "threshold": threshold,
            "status": status,
        })

    data["completeness"] = completeness

    # ── 3. Validity ──
    validity = []

    checks = [
        ("Credit score outside 300–850",
         "SELECT COUNT(*) FROM loans WHERE credit_score IS NOT NULL AND (credit_score < 300 OR credit_score > 850)"),
        ("LTV outside 1–200",
         "SELECT COUNT(*) FROM loans WHERE ltv IS NOT NULL AND (ltv < 1 OR ltv > 200)"),
        ("Interest rate outside 0.1–15%",
         "SELECT COUNT(*) FROM loans WHERE orig_interest_rate IS NOT NULL AND (orig_interest_rate < 0.1 OR orig_interest_rate > 15)"),
        ("Negative current UPB",
         "SELECT COUNT(*) FROM loans WHERE current_upb < 0"),
        ("Empty property state",
         "SELECT COUNT(*) FROM loans WHERE property_state IS NULL OR LENGTH(TRIM(property_state)) = 0"),
        ("Payment history shorter than 10 chars",
         "SELECT COUNT(*) FROM loans WHERE payment_history IS NOT NULL AND LENGTH(payment_history) < 10"),
    ]

    for label, sql in checks:
        violations = con.execute(sql).fetchone()[0]
        pct = round(100 * violations / total, 3) if total > 0 else 0
        status = "PASS" if pct < 0.5 else ("WARN" if pct < 2.0 else "FAIL")
        validity.append({
            "check": label,
            "violations": violations,
            "pct": pct,
            "status": status,
        })

    data["validity"] = validity

    # ── 4. Consistency ──
    consistency = []

    # UPB exceeds original amount
    c1 = con.execute("""
        SELECT COUNT(*) FROM loans
        WHERE current_upb > orig_loan_amount
          AND orig_loan_amount > 0
          AND current_upb > 0
          AND dpd_bucket = 'Current'
    """).fetchone()[0]
    consistency.append({
        "check": "Current UPB exceeds original amount (performing loans)",
        "violations": c1,
        "pct": round(100 * c1 / total, 3),
        "status": "PASS" if c1 / total < 0.01 else "WARN",
        "note": "May occur for loans with capitalized arrearages after modification",
    })

    # Duplicate loan IDs
    c2 = con.execute("""
        SELECT COUNT(*) FROM (
            SELECT loan_id FROM loans
            WHERE loan_id IS NOT NULL
            GROUP BY loan_id HAVING COUNT(*) > 1
        )
    """).fetchone()[0]
    consistency.append({
        "check": "Duplicate loan IDs",
        "violations": c2,
        "pct": round(100 * c2 / total, 3),
        "status": "PASS" if c2 == 0 else "FAIL",
        "note": "",
    })

    # Null loan_age (known SC file limitation)
    c3 = con.execute(
        "SELECT COUNT(*) FROM loans WHERE loan_age IS NULL"
    ).fetchone()[0]
    consistency.append({
        "check": "Missing loan_age",
        "violations": c3,
        "pct": round(100 * c3 / total, 3),
        "status": "PASS" if c3 / total < 0.01 else "WARN",
        "note": "Expected for SC-format files which do not populate this field",
    })

    data["consistency"] = consistency

    # ── 5. Distribution Profiles ──

    # Credit score bands
    dist_credit = _query(con, """
        SELECT credit_score_band AS band, COUNT(*) AS loans,
               ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 1) AS pct
        FROM loans WHERE credit_score_band != 'Unknown'
        GROUP BY credit_score_band
        ORDER BY MIN(credit_score)
    """)
    data["dist_credit"] = dist_credit

    # DPD buckets
    dist_dpd = _query(con, """
        SELECT dpd_bucket AS bucket, COUNT(*) AS loans,
               ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) AS pct
        FROM loans GROUP BY dpd_bucket
        ORDER BY CASE dpd_bucket
            WHEN 'Current' THEN 1 WHEN '30_DPD' THEN 2 WHEN '60_DPD' THEN 3
            WHEN '90_DPD' THEN 4 WHEN '120_Plus_DPD' THEN 5 ELSE 6 END
    """)
    data["dist_dpd"] = dist_dpd

    # Vintage
    dist_vintage = _query(con, """
        SELECT CAST(orig_year AS INTEGER) AS year, COUNT(*) AS loans,
               ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 1) AS pct
        FROM loans WHERE orig_year IS NOT NULL
        GROUP BY orig_year ORDER BY orig_year
    """)
    data["dist_vintage"] = dist_vintage

    # ── 6. Per-Pool Manifest ──
    pools = _query(con, """
        SELECT pool_prefix AS pool, COUNT(*) AS loans
        FROM loans GROUP BY pool_prefix ORDER BY pool_prefix
    """)
    for p in pools:
        p["status"] = "PASS" if p["loans"] >= min_per_pool else "WARN"
    data["pools"] = pools

    # ── Overall status ──
    all_statuses = (
        [c["status"] for c in completeness] +
        [v["status"] for v in validity] +
        [c["status"] for c in consistency]
    )
    if "FAIL" in all_statuses:
        data["overall_status"] = "FAIL"
    elif "WARN" in all_statuses:
        data["overall_status"] = "WARN"
    else:
        data["overall_status"] = "PASS"

    return data


def generate_report(config_path, db_path, output_path):
    """Main entry point: gather data, render template, write HTML."""
    config = load_config(config_path)
    con = duckdb.connect(db_path, read_only=True)

    print(f"Running DQ checks against: {db_path}")
    data = build_report_data(con, config)
    con.close()

    data["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data["db_path"] = db_path

    # Render template
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("dq_report.html")
    html = template.render(**data)

    # Write output
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        f.write(html)

    # Print summary
    pass_count = sum(1 for s in [c["status"] for c in data["completeness"]] +
                     [v["status"] for v in data["validity"]] +
                     [c["status"] for c in data["consistency"]] if s == "PASS")
    warn_count = sum(1 for s in [c["status"] for c in data["completeness"]] +
                     [v["status"] for v in data["validity"]] +
                     [c["status"] for c in data["consistency"]] if s == "WARN")
    fail_count = sum(1 for s in [c["status"] for c in data["completeness"]] +
                     [v["status"] for v in data["validity"]] +
                     [c["status"] for c in data["consistency"]] if s == "FAIL")

    print(f"Overall: {data['overall_status']}  "
          f"(PASS: {pass_count}, WARN: {warn_count}, FAIL: {fail_count})")
    print(f"Report saved: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Data Quality Report")
    parser.add_argument("--config", "-c", default="python/etl/config.yaml")
    parser.add_argument("--db", "-d", default="data/mortgage_analytics.duckdb")
    parser.add_argument("--output", "-o", default="reports/data_quality_report.html")
    args = parser.parse_args()

    # Resolve config path
    if not os.path.exists(args.config):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        alt = os.path.join(script_dir, "..", "etl", "config.yaml")
        if os.path.exists(alt):
            args.config = alt

    generate_report(args.config, args.db, args.output)
