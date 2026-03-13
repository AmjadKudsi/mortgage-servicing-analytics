"""
detector.py — File format detection and field validation.
Author: Amjad Ali Kudsi

Reads the first few rows of a file, determines whether it's
SC-format (record types 10/20/50/80) or DI-format (flat),
and validates field count against the schema.
"""

import logging

log = logging.getLogger("etl")


def detect_file(filepath, schema):
    """
    Inspect a file and return a detection report.

    Returns:
        dict with keys:
            format:         "DI" or "SC"
            fields_per_row: int (median field count across sample rows)
            matches_schema: bool (whether field count matches expected)
            total_lines:    int (approximate, from sample)
            sample_values:  dict of first row's key fields
            issues:         list of strings describing any problems
    """
    expected = schema.expected_field_count
    issues = []

    with open(filepath, "r") as f:
        sample_lines = []
        for i, line in enumerate(f):
            if i >= 20:
                break
            stripped = line.strip()
            if stripped:
                sample_lines.append(stripped)

    if not sample_lines:
        return {
            "format": "UNKNOWN",
            "fields_per_row": 0,
            "matches_schema": False,
            "total_lines": 0,
            "sample_values": {},
            "issues": ["File is empty or unreadable"],
        }

    # ── Detect format ──
    first_field = sample_lines[0].split("|")[0].strip()
    if first_field in ("10", "20", "50", "80"):
        file_format = "SC"
        # For SC files, check field count on record type 20 rows
        field_counts = []
        for line in sample_lines:
            fields = line.split("|")
            if fields[0].strip() == "20":
                field_counts.append(len(fields))
    else:
        file_format = "DI"
        field_counts = [len(line.split("|")) for line in sample_lines]

    # ── Field count validation ──
    if field_counts:
        median_count = sorted(field_counts)[len(field_counts) // 2]
    else:
        median_count = 0

    # DI files should have exactly 90 fields (89 pipe separators = 90 fields)
    # Allow ±2 tolerance for trailing pipes or minor format variations
    if file_format == "DI":
        matches = abs(median_count - expected) <= 2
        if not matches:
            issues.append(
                f"Expected {expected} fields, found {median_count}. "
                f"Schema mismatch — check if Freddie Mac changed the format."
            )
    else:
        # SC files have different field counts per record type — that's fine
        matches = True

    # ── Extract sample key values (first data row) ──
    sample_values = {}
    if file_format == "DI" and sample_lines:
        fields = sample_lines[0].split("|")
        col_names = schema.column_names
        for key in ["reporting_period", "pool_prefix", "loan_id",
                     "property_state", "orig_date", "credit_score",
                     "delinquency_status", "orig_interest_rate"]:
            idx = schema.column_index(key)
            if idx < len(fields):
                sample_values[key] = fields[idx].strip()
    elif file_format == "SC":
        # Get sample from first record type 20
        for line in sample_lines:
            fields = line.split("|")
            if fields[0].strip() == "20":
                sample_values["loan_id"] = fields[1].strip() if len(fields) > 1 else ""
                sample_values["property_state"] = fields[12].strip() if len(fields) > 12 else ""
                sample_values["credit_score"] = fields[29].strip() if len(fields) > 29 else ""
                break

    # ── Count total lines (fast scan) ──
    total_lines = 0
    with open(filepath, "r") as f:
        for _ in f:
            total_lines += 1

    report = {
        "format": file_format,
        "fields_per_row": median_count,
        "matches_schema": matches,
        "total_lines": total_lines,
        "sample_values": sample_values,
        "issues": issues,
    }

    log.info(f"  Detected: {file_format} format, {median_count} fields/row, "
             f"{total_lines:,} lines, schema_match={matches}")
    if issues:
        for issue in issues:
            log.warning(f"  ⚠ {issue}")

    return report
