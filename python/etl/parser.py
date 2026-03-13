"""
parser.py — File parsers for DI-format and SC-format LLD files.

Each parser reads a raw file and returns a pandas DataFrame
with column names applied from the schema. No cleaning happens here —
just reading, labeling, and basic structural validation.
"""

import logging
import pandas as pd

log = logging.getLogger("etl")


def parse_di_file(filepath, schema):
    """
    Parse a flat DI/DNA/HQA file.
    Each row is one loan with all fields in a single line.

    Returns:
        tuple: (DataFrame, parse_report dict)
    """
    col_names = schema.column_names
    expected = schema.expected_field_count

    rows = []
    skipped = 0
    skip_reasons = {}

    with open(filepath, "r") as f:
        for line_num, line in enumerate(f, 1):
            fields = line.strip().split("|")
            n = len(fields)

            if n >= expected - 2:
                # Pad short rows to exactly the expected count
                while len(fields) < expected:
                    fields.append("")
                rows.append(fields[:expected])
            else:
                skipped += 1
                reason = f"too_few_fields ({n})"
                skip_reasons[reason] = skip_reasons.get(reason, 0) + 1

    df = pd.DataFrame(rows, columns=col_names)

    report = {
        "rows_parsed": len(rows),
        "rows_skipped": skipped,
        "skip_reasons": skip_reasons,
    }

    log.info(f"  Parsed: {len(rows):,} loans, {skipped} skipped")
    if skip_reasons:
        for reason, count in skip_reasons.items():
            log.info(f"    Skip reason: {reason} × {count}")

    return df, report


def parse_sc_file(filepath, schema):
    """
    Parse an SC-format file (record types 10, 20, 50, 80).
    Merges record type 20 (origination) and 50 (performance) by loan_id.
    Returns a DataFrame in the same schema as DI files.

    Returns:
        tuple: (DataFrame, parse_report dict)
    """
    col_names = schema.column_names
    expected = schema.expected_field_count
    sc_map = schema.sc_field_map

    rec20 = {}
    rec50 = {}
    header_count = 0
    footer_count = 0

    with open(filepath, "r") as f:
        for line in f:
            fields = line.strip().split("|")
            rec_type = fields[0].strip()
            if rec_type == "20":
                loan_id = fields[1].strip()
                rec20[loan_id] = fields
            elif rec_type == "50":
                loan_id = fields[1].strip()
                rec50[loan_id] = fields
            elif rec_type == "10":
                header_count += 1
            elif rec_type == "80":
                footer_count += 1

    # Build a column_name → position_index lookup
    col_index = {name: i for i, name in enumerate(col_names)}

    # Merge rec20 + rec50 into unified rows
    rows = []
    unmatched = 0
    for loan_id, r20 in rec20.items():
        r50 = rec50.get(loan_id)
        if r50 is None:
            unmatched += 1
            continue

        row = [""] * expected

        # Map fields using the sc_field_map from config
        for col_name, (rec_type, field_idx) in sc_map.items():
            target_idx = col_index.get(col_name)
            if target_idx is None:
                continue

            if rec_type == 20:
                source = r20
            else:
                source = r50

            if field_idx < len(source):
                row[target_idx] = source[field_idx].strip()

        # Ensure loan_id and pool_prefix are set
        row[col_index["loan_id"]] = loan_id
        # Extract pool prefix from loan_id (letters + first digits)
        prefix = ""
        for ch in loan_id:
            if ch.isdigit() and len(prefix) > 3:
                break
            prefix += ch
        row[col_index["pool_prefix"]] = prefix.rstrip("0").rstrip("")

        rows.append(row)

    df = pd.DataFrame(rows, columns=col_names)

    report = {
        "rows_parsed": len(rows),
        "rows_skipped": unmatched,
        "skip_reasons": {f"no_matching_rec50": unmatched} if unmatched else {},
        "rec20_count": len(rec20),
        "rec50_count": len(rec50),
    }

    log.info(f"  Parsed: {len(rows):,} loans "
             f"(rec20={len(rec20):,}, rec50={len(rec50):,}, unmatched={unmatched})")

    return df, report
