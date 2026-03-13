"""
validator.py — Post-load quality gates.

Runs checks against the loaded DuckDB database and reports
pass/warn/fail results. Does not modify data.
"""

import logging
import duckdb

log = logging.getLogger("etl")


def validate(db_path, table_name, schema):
    """
    Run all post-load validation checks.

    Returns:
        dict with keys:
            passed:   bool (True if no critical failures)
            checks:   list of dicts, each with {name, status, detail}
            summary:  DataFrame of vintage-level stats
    """
    thresholds = schema.validation
    con = duckdb.connect(db_path, read_only=True)
    checks = []

    log.info("")
    log.info("=" * 60)
    log.info("POST-LOAD VALIDATION")
    log.info("=" * 60)

    # ── 1. Total row count ──
    total = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
    checks.append({
        "name": "total_rows",
        "status": "PASS" if total > 0 else "FAIL",
        "detail": f"{total:,} loans loaded",
    })
    log.info(f"  Total rows: {total:,}")

    # ── 2. Duplicate loan IDs ──
    dup_count = con.execute(f"""
        SELECT COUNT(*) FROM (
            SELECT loan_id, COUNT(*) as cnt
            FROM {table_name}
            WHERE loan_id IS NOT NULL
            GROUP BY loan_id
            HAVING COUNT(*) > 1
        )
    """).fetchone()[0]
    max_dups = thresholds.get("max_duplicate_loan_ids", 0)
    dup_status = "PASS" if dup_count <= max_dups else "WARN"
    checks.append({
        "name": "duplicate_loan_ids",
        "status": dup_status,
        "detail": f"{dup_count:,} duplicate loan IDs (threshold: {max_dups})",
    })
    log.info(f"  Duplicate loan IDs: {dup_count:,} [{dup_status}]")

    # ── 3. Null rates on critical columns ──
    critical_thresholds = thresholds.get("max_null_pct_critical", {})
    warning_thresholds = thresholds.get("max_null_pct_warning", {})

    all_cols = {**critical_thresholds, **warning_thresholds}
    # Also check current_upb (derived column)
    if "current_upb" not in all_cols:
        all_cols["current_upb"] = 2.0

    for col, max_pct in all_cols.items():
        try:
            null_count = con.execute(
                f"SELECT COUNT(*) FROM {table_name} WHERE {col} IS NULL"
            ).fetchone()[0]
        except Exception:
            checks.append({
                "name": f"null_{col}",
                "status": "SKIP",
                "detail": f"Column '{col}' not found in table",
            })
            continue

        null_pct = round(100 * null_count / total, 2) if total > 0 else 0
        is_critical = col in critical_thresholds

        if null_pct > max_pct:
            status = "FAIL" if is_critical else "WARN"
        else:
            status = "PASS"

        checks.append({
            "name": f"null_{col}",
            "status": status,
            "detail": f"{null_pct}% null (threshold: {max_pct}%)",
        })
        log.info(f"  Null rate [{col}]: {null_pct}% [{status}]")

    # ── 4. Value range checks ──
    range_checks = [
        ("credit_score", 300, 850, "Credit score"),
        ("ltv", 1, 200, "LTV"),
        ("orig_interest_rate", 0.1, 15.0, "Orig interest rate"),
    ]
    for col, low, high, label in range_checks:
        try:
            out_of_range = con.execute(f"""
                SELECT COUNT(*) FROM {table_name}
                WHERE {col} IS NOT NULL AND ({col} < {low} OR {col} > {high})
            """).fetchone()[0]
        except Exception:
            continue

        pct = round(100 * out_of_range / total, 2) if total > 0 else 0
        status = "PASS" if pct < 1.0 else "WARN"
        checks.append({
            "name": f"range_{col}",
            "status": status,
            "detail": f"{out_of_range:,} loans out of [{low}, {high}] ({pct}%)",
        })
        log.info(f"  Range [{label}]: {out_of_range:,} out of range [{status}]")

    # ── 5. Vintage coverage ──
    vintage_df = con.execute(f"""
        SELECT
            orig_year,
            COUNT(*) as loans,
            ROUND(SUM(current_upb), 0) as total_upb,
            ROUND(100.0 * SUM(is_delinquent) / COUNT(*), 2) as dlq_rate_pct,
            ROUND(AVG(credit_score), 0) as avg_fico,
            ROUND(AVG(orig_interest_rate), 3) as avg_rate
        FROM {table_name}
        WHERE orig_year IS NOT NULL
        GROUP BY orig_year
        ORDER BY orig_year
    """).fetchdf()

    vintage_count = len(vintage_df)
    checks.append({
        "name": "vintage_coverage",
        "status": "PASS" if vintage_count >= 5 else "WARN",
        "detail": f"{vintage_count} distinct origination years",
    })

    log.info(f"\n  Vintage summary ({vintage_count} years):")
    for _, row in vintage_df.iterrows():
        log.info(f"    {int(row['orig_year'])}: "
                 f"{int(row['loans']):>8,} loans  "
                 f"${row['total_upb']:>16,.0f}  "
                 f"DLQ {row['dlq_rate_pct']:>5.2f}%  "
                 f"FICO {int(row['avg_fico'])}  "
                 f"Rate {row['avg_rate']:.3f}%")

    # ── 6. Per-pool row counts ──
    pool_df = con.execute(f"""
        SELECT pool_prefix, COUNT(*) as loans
        FROM {table_name}
        GROUP BY pool_prefix
        ORDER BY pool_prefix
    """).fetchdf()

    min_per_file = thresholds.get("min_loans_per_file", 100)
    small_pools = pool_df[pool_df["loans"] < min_per_file]
    if len(small_pools) > 0:
        checks.append({
            "name": "small_pools",
            "status": "WARN",
            "detail": f"{len(small_pools)} pool(s) have fewer than {min_per_file} loans",
        })
        for _, row in small_pools.iterrows():
            log.info(f"  ⚠ Pool '{row['pool_prefix']}' has only {int(row['loans'])} loans")

    con.close()

    # ── Overall result ──
    has_failures = any(c["status"] == "FAIL" for c in checks)
    has_warnings = any(c["status"] == "WARN" for c in checks)
    overall = "FAIL" if has_failures else ("WARN" if has_warnings else "PASS")

    log.info(f"\n  Overall validation: {overall}")
    log.info(f"    PASS: {sum(1 for c in checks if c['status'] == 'PASS')}")
    log.info(f"    WARN: {sum(1 for c in checks if c['status'] == 'WARN')}")
    log.info(f"    FAIL: {sum(1 for c in checks if c['status'] == 'FAIL')}")

    return {
        "passed": not has_failures,
        "overall": overall,
        "checks": checks,
        "summary": vintage_df,
    }
