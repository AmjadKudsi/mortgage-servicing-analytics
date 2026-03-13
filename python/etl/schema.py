"""
schema.py — Column definitions loaded from config.yaml.
Author: Amjad Ali Kudsi

Provides structured access to column names, types, sentinels,
and derived column definitions. Nothing is hardcoded here —
everything comes from the config file.
"""


class Schema:
    """Parses the config and exposes column metadata."""

    def __init__(self, config):
        self._config = config
        self._columns = config["columns"]
        self._sentinels = config.get("sentinels", {})
        self._derived = config.get("derived", {})
        self._sc_map = config.get("sc_field_map", {})
        self._validation = config.get("validation", {})

    # ── Column names in positional order ──
    @property
    def column_names(self):
        return [c[1] for c in self._columns]

    @property
    def expected_field_count(self):
        return len(self._columns)

    # ── Type groups ──
    @property
    def float_columns(self):
        return [c[1] for c in self._columns if c[2] == "float"]

    @property
    def int_columns(self):
        return [c[1] for c in self._columns if c[2] == "int"]

    @property
    def str_columns(self):
        return [c[1] for c in self._columns if c[2] == "str"]

    # ── Sentinel values ──
    @property
    def sentinels(self):
        return self._sentinels

    # ── SC format mapping ──
    @property
    def sc_field_map(self):
        return self._sc_map

    # ── Derived column configs ──
    @property
    def dpd_map(self):
        return self._derived.get("dpd_map", {})

    @property
    def dpd_numeric_gte(self):
        return self._derived.get("dpd_numeric_gte", 4)

    @property
    def dpd_default(self):
        return self._derived.get("dpd_default", "Other")

    @property
    def credit_score_bands(self):
        return self._derived.get("credit_score_bands", [])

    @property
    def ltv_buckets(self):
        return self._derived.get("ltv_buckets", [])

    @property
    def rate_buckets(self):
        return self._derived.get("rate_buckets", [])

    # ── Validation thresholds ──
    @property
    def validation(self):
        return self._validation

    # ── Column name → position index lookup ──
    def column_index(self, name):
        for pos, col_name, _ in self._columns:
            if col_name == name:
                return pos
        raise KeyError(f"Column '{name}' not found in schema")
