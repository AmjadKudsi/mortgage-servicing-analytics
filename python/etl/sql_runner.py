"""
sql_runner.py — Executes SQL query files against the DuckDB database.

Used by all downstream consumers (Tableau export, report generator,
ML pipeline, JSON exporter) to get data. SQL is the single source of truth.

Usage:
    # Print results to console
    python sql_runner.py --query sql/duckdb/02_portfolio_summary.sql

    # Export to CSV
    python sql_runner.py --query sql/duckdb/03_delinquency_analysis.sql --format csv --output data/clean/delinquency.csv

    # Export to JSON
    python sql_runner.py --query sql/duckdb/08_geographic_analysis.sql --format json --output docs/data/geo.json

    # Use from Python
    from sql_runner import run_query
    df = run_query("sql/duckdb/02_portfolio_summary.sql", "data/mortgage_analytics.duckdb")
"""

import os
import sys
import argparse
import duckdb
import pandas as pd


def run_query(sql_path, db_path, params=None):
    """
    Execute a .sql file against DuckDB and return a DataFrame.

    Args:
        sql_path: Path to the .sql file
        db_path:  Path to the .duckdb database
        params:   Optional dict of parameters to substitute (future use)

    Returns:
        pandas DataFrame with query results
    """
    with open(sql_path, "r") as f:
        sql = f.read()

    # Strip comments-only preamble, find actual SQL statements
    # Support multiple statements separated by semicolons
    # Execute the last SELECT statement (others may be setup CTEs or temp views)
    con = duckdb.connect(db_path, read_only=True)
    try:
        result = con.execute(sql).fetchdf()
    finally:
        con.close()

    return result


def run_query_string(sql, db_path):
    """Execute a raw SQL string and return a DataFrame."""
    con = duckdb.connect(db_path, read_only=True)
    try:
        result = con.execute(sql).fetchdf()
    finally:
        con.close()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run SQL queries against DuckDB")
    parser.add_argument("--query", "-q", required=True, help="Path to .sql file")
    parser.add_argument("--db", "-d", default="data/mortgage_analytics.duckdb", help="Path to DuckDB database")
    parser.add_argument("--format", "-f", choices=["print", "csv", "json"], default="print")
    parser.add_argument("--output", "-o", help="Output file path (for csv/json)")
    args = parser.parse_args()

    df = run_query(args.query, args.db)

    if args.format == "print":
        print(df.to_string(index=False))
    elif args.format == "csv":
        out = args.output or args.query.replace(".sql", ".csv")
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        df.to_csv(out, index=False)
        print(f"Exported {len(df)} rows to {out}")
    elif args.format == "json":
        out = args.output or args.query.replace(".sql", ".json")
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        df.to_json(out, orient="records", indent=2)
        print(f"Exported {len(df)} rows to {out}")
