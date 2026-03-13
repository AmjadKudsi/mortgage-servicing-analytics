"""
loader.py — DuckDB table creation and data insertion.

Idempotent: if data from the same pool_prefix already exists,
it is deleted before re-inserting. Safe to re-run after fixing bugs.

Uses explicit column types from the schema to avoid DuckDB
mis-inferring types from the first file loaded (e.g., an empty
string column being guessed as INT).
"""

import logging
import duckdb

log = logging.getLogger("etl")

# Map config types to DuckDB SQL types
_TYPE_MAP = {
    "str": "VARCHAR",
    "int": "DOUBLE",      # DOUBLE not INT — pandas NaN requires float-compatible type
    "float": "DOUBLE",
}


def init_database(db_path):
    """Remove stale WAL files if present."""
    import os
    wal_path = db_path + ".wal"
    if os.path.exists(wal_path):
        os.remove(wal_path)
        log.info(f"Removed stale WAL file: {wal_path}")


def _build_create_sql(table_name, schema):
    """Build an explicit CREATE TABLE from the schema. No type guessing."""
    col_defs = []
    for _, col_name, col_type in schema._config["columns"]:
        duck_type = _TYPE_MAP.get(col_type, "VARCHAR")
        col_defs.append(f'"{col_name}" {duck_type}')

    # Derived columns added by cleaner.py
    for col_name, duck_type in [
        ("current_upb", "DOUBLE"),
        ("orig_year", "DOUBLE"),
        ("orig_quarter", "VARCHAR"),
        ("dpd_bucket", "VARCHAR"),
        ("credit_score_band", "VARCHAR"),
        ("ltv_bucket", "VARCHAR"),
        ("rate_bucket", "VARCHAR"),
        ("is_delinquent", "INTEGER"),
        ("is_seriously_delinquent", "INTEGER"),
    ]:
        col_defs.append(f'"{col_name}" {duck_type}')

    cols_sql = ",\n    ".join(col_defs)
    return f"CREATE TABLE {table_name} (\n    {cols_sql}\n)"


def load_dataframe(df, db_path, table_name="loans", schema=None):
    """
    Load a cleaned DataFrame into DuckDB.

    - Creates the table with explicit types if it doesn't exist.
    - Deletes existing rows for the same pool_prefix (idempotent).
    - Inserts all rows.
    - Returns total row count after insert.
    """
    con = duckdb.connect(db_path)

    # ── Create table with explicit schema ──
    tables = [row[0] for row in con.execute("SHOW TABLES").fetchall()]
    if table_name not in tables:
        if schema is not None:
            create_sql = _build_create_sql(table_name, schema)
            con.execute(create_sql)
            log.info(f"  Created table '{table_name}' with explicit schema")
        else:
            con.execute(f"CREATE TABLE {table_name} AS SELECT * FROM df WHERE 1=0")
            log.info(f"  Created table '{table_name}' (auto-inferred)")

    # ── Match DataFrame columns to table columns ──
    table_cols = [row[0] for row in con.execute(f"DESCRIBE {table_name}").fetchall()]
    common_cols = [c for c in df.columns if c in table_cols]

    # ── Delete existing data for this pool_prefix (idempotent) ──
    pool_prefixes = df["pool_prefix"].dropna().unique().tolist()
    if pool_prefixes:
        placeholders = ", ".join(f"'{p}'" for p in pool_prefixes)
        deleted = con.execute(
            f"SELECT COUNT(*) FROM {table_name} WHERE pool_prefix IN ({placeholders})"
        ).fetchone()[0]
        if deleted > 0:
            con.execute(
                f"DELETE FROM {table_name} WHERE pool_prefix IN ({placeholders})"
            )
            log.info(f"  Removed {deleted:,} existing rows for pool(s): {pool_prefixes}")

    # ── Insert using explicit column list ──
    cols_sql = ", ".join(f'"{c}"' for c in common_cols)
    con.execute(f'INSERT INTO {table_name} ({cols_sql}) SELECT {cols_sql} FROM df')
    total = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]

    con.close()
    return total
