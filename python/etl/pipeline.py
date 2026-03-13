"""
pipeline.py — Main ETL orchestrator.
Author: Amjad Ali Kudsi

Calls each module in sequence:
    1. Load config → build schema
    2. Scan input directory for LLD files
    3. For each file: detect → parse → clean → load
    4. Run post-load validation
    5. Save manifest

Usage:
    python pipeline.py
    python pipeline.py --config python/etl/config.yaml
"""

import os
import sys
import argparse
import logging
import pandas as pd

from utils import setup_logging, load_config, timed
from schema import Schema
from detector import detect_file
from parser import parse_di_file, parse_sc_file
from cleaner import clean
from loader import init_database, load_dataframe
from validator import validate


@timed
def process_file(filepath, schema, db_path, table_name):
    """
    Process a single file through detect → parse → clean → load.

    Returns:
        dict: file-level manifest entry
    """
    log = logging.getLogger("etl")
    filename = os.path.basename(filepath)
    file_size_mb = os.path.getsize(filepath) / (1024 * 1024)

    log.info(f"Processing: {filename} ({file_size_mb:.1f} MB)")

    entry = {
        "file": filename,
        "size_mb": round(file_size_mb, 1),
        "status": "OK",
    }

    # ── Step A: Detect ──
    detection = detect_file(filepath, schema)
    entry["format"] = detection["format"]
    entry["total_lines"] = detection["total_lines"]

    if detection["issues"]:
        # Non-fatal issues — continue but note them
        entry["detection_issues"] = "; ".join(detection["issues"])

    if not detection["matches_schema"] and detection["format"] == "DI":
        entry["status"] = "SKIPPED"
        entry["error"] = "Schema mismatch — field count does not match expected"
        log.error(f"  SKIPPED: {entry['error']}")
        return entry

    # ── Step B: Parse ──
    try:
        if detection["format"] == "DI":
            df, parse_report = parse_di_file(filepath, schema)
        elif detection["format"] == "SC":
            df, parse_report = parse_sc_file(filepath, schema)
        else:
            entry["status"] = "SKIPPED"
            entry["error"] = f"Unknown format: {detection['format']}"
            return entry

        entry["rows_parsed"] = parse_report["rows_parsed"]
        entry["rows_skipped"] = parse_report["rows_skipped"]

        if parse_report["rows_parsed"] == 0:
            entry["status"] = "SKIPPED"
            entry["error"] = "No rows parsed from file"
            log.error(f"  SKIPPED: No parseable rows")
            return entry

    except Exception as e:
        entry["status"] = "ERROR"
        entry["error"] = f"Parse error: {str(e)}"
        log.error(f"  PARSE ERROR: {e}")
        return entry

    # ── Step C: Clean ──
    try:
        df, clean_report = clean(df, schema)
        entry["null_rates"] = clean_report["null_rates"]
    except Exception as e:
        entry["status"] = "ERROR"
        entry["error"] = f"Clean error: {str(e)}"
        log.error(f"  CLEAN ERROR: {e}")
        return entry

    # ── Step D: Load ──
    try:
        total_in_db = load_dataframe(df, db_path, table_name, schema=schema)
        entry["rows_loaded"] = len(df)
        entry["total_in_db"] = total_in_db

        # Summary stats
        entry["total_upb"] = round(df["current_upb"].sum(), 0)
        years = df["orig_year"].dropna().unique()
        if len(years) > 0:
            entry["vintages"] = f"{int(min(years))}-{int(max(years))}"

        log.info(f"  Loaded: {len(df):,} rows → DuckDB (DB total: {total_in_db:,})")

    except Exception as e:
        entry["status"] = "ERROR"
        entry["error"] = f"Load error: {str(e)}"
        log.error(f"  LOAD ERROR: {e}")
        return entry

    return entry


def run(config_path):
    """Main pipeline entry point."""
    # ── Load config and schema ──
    config = load_config(config_path)
    schema = Schema(config)

    paths = config["paths"]
    db_config = config["database"]

    log = setup_logging(paths["log_file"])

    log.info("=" * 60)
    log.info("MORTGAGE SERVICING ANALYTICS — ETL PIPELINE")
    log.info("=" * 60)
    log.info(f"Config:   {config_path}")
    log.info(f"Input:    {paths['input_dir']}")
    log.info(f"Database: {paths['database']}")
    log.info(f"Schema:   {schema.expected_field_count} columns")
    log.info("")

    input_dir = paths["input_dir"]
    db_path = paths["database"]
    table_name = db_config["table_name"]

    # ── Ensure directories exist ──
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    os.makedirs(paths["reports_dir"], exist_ok=True)

    # ── Initialize database ──
    init_database(db_path)

    # ── Find LLD files ──
    files = sorted([
        f for f in os.listdir(input_dir)
        if f.endswith(".txt") and "lld" in f.lower()
    ])

    if not files:
        log.error(f"No LLD files found in {input_dir}")
        sys.exit(1)

    log.info(f"Found {len(files)} file(s) to process:")
    for f in files:
        size = os.path.getsize(os.path.join(input_dir, f)) / (1024 * 1024)
        log.info(f"  {f} ({size:.1f} MB)")
    log.info("")

    # ── Process each file ──
    manifest = []
    for filename in files:
        filepath = os.path.join(input_dir, filename)
        entry = process_file(filepath, schema, db_path, table_name)
        manifest.append(entry)
        log.info("")

    # ── Post-load validation ──
    validation_result = validate(db_path, table_name, schema)

    # ── Save manifest ──
    manifest_df = pd.DataFrame(manifest)
    manifest_path = paths["manifest_file"]
    manifest_df.to_csv(manifest_path, index=False)
    log.info(f"\nManifest saved: {manifest_path}")

    # ── Final summary ──
    success = sum(1 for m in manifest if m["status"] == "OK")
    errors = sum(1 for m in manifest if m["status"] == "ERROR")
    skipped = sum(1 for m in manifest if m["status"] == "SKIPPED")

    log.info("")
    log.info("=" * 60)
    log.info("PIPELINE COMPLETE")
    log.info("=" * 60)
    log.info(f"  Files:      {len(files)} total, "
             f"{success} loaded, {errors} errors, {skipped} skipped")
    log.info(f"  Validation: {validation_result['overall']}")

    if not validation_result["passed"]:
        log.warning("  ⚠ Validation has FAILURES. Review the checks above.")
        log.warning("  Fix issues and re-run the pipeline (idempotent — safe to re-run).")

    return manifest, validation_result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Mortgage Servicing Analytics — ETL Pipeline"
    )
    parser.add_argument(
        "--config", "-c",
        default="python/etl/config.yaml",
        help="Path to config.yaml",
    )
    args = parser.parse_args()

    if not os.path.exists(args.config):
        # Try relative to script location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        alt_path = os.path.join(script_dir, "config.yaml")
        if os.path.exists(alt_path):
            args.config = alt_path
        else:
            print(f"Config not found: {args.config}")
            sys.exit(1)

    run(args.config)
