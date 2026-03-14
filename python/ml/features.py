"""
features.py — Load feature matrix and prepare Model A / Model B feature sets.
"""

import os
import sys
import logging
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "etl"))
from sql_runner import run_query

log = logging.getLogger("ml")


def load_feature_matrix(db_path, sql_path):
    """Load raw feature matrix from DuckDB via SQL."""
    if not os.path.exists(sql_path):
        alt = os.path.join(os.path.dirname(__file__), "feature_engineering.sql")
        if os.path.exists(alt):
            sql_path = alt

    log.info(f"Loading features from: {db_path}")
    df = run_query(sql_path, db_path)
    log.info(f"  Rows: {len(df):,}")
    log.info(f"  Delinquent: {df['is_delinquent'].sum():,} "
             f"({100 * df['is_delinquent'].mean():.2f}%)")
    return df


def prepare_feature_set(df, config, model_type="origination"):
    """
    Prepare X and y for a given model type.

    model_type:
        'origination' → Model B (origination features only)
        'behavioral'  → Model A (origination + payment history features)

    Returns: X (DataFrame), y (Series), feature_names (list)
    """
    numeric = list(config["origination_features_numeric"])
    categorical = list(config["origination_features_categorical"])
    binary = list(config["origination_features_binary"])
    target = config["target"]

    if model_type == "behavioral":
        numeric = numeric + list(config["behavioral_features_extra"])

    # ── Numeric: fill nulls with median ──
    X_num = df[numeric].copy()
    for col in numeric:
        X_num[col] = X_num[col].fillna(X_num[col].median())

    # ── Categorical: one-hot encode ──
    X_cat = pd.get_dummies(
        df[categorical], columns=categorical,
        drop_first=True, dtype=int,
    )

    # ── Binary ──
    X_bin = df[binary].copy().fillna(0).astype(int)

    # ── Combine ──
    X = pd.concat([X_num, X_cat, X_bin], axis=1)
    y = df[target].astype(int)

    log.info(f"  Prepared [{model_type}]: {X.shape[1]} features "
             f"({len(numeric)} num + {X_cat.shape[1]} cat + {len(binary)} bin)")

    return X, y, list(X.columns)


def split_by_loan_age(X, y, df):
    """
    Time-based split: older loans → train, newer loans → test.
    Returns X_train, X_test, y_train, y_test, split_info dict.
    """
    median_age = df["loan_age"].median()
    train_mask = df["loan_age"] >= median_age
    test_mask = df["loan_age"] < median_age

    X_train, y_train = X[train_mask].copy(), y[train_mask].copy()
    X_test, y_test = X[test_mask].copy(), y[test_mask].copy()

    # Reset indices to avoid alignment issues
    X_train.reset_index(drop=True, inplace=True)
    X_test.reset_index(drop=True, inplace=True)
    y_train.reset_index(drop=True, inplace=True)
    y_test.reset_index(drop=True, inplace=True)

    split_info = {
        "split_method": "loan_age_median",
        "median_age": float(median_age),
        "train_size": len(X_train),
        "test_size": len(X_test),
        "train_dlq_rate": round(float(y_train.mean()), 4),
        "test_dlq_rate": round(float(y_test.mean()), 4),
    }

    log.info(f"  Split at loan_age={median_age:.0f}: "
             f"train={len(X_train):,} ({100*y_train.mean():.2f}% DLQ), "
             f"test={len(X_test):,} ({100*y_test.mean():.2f}% DLQ)")

    return X_train, X_test, y_train, y_test, split_info
