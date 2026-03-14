"""
safety.py — Pre-training and post-training safety checks.

Detects data leakage, validates distributions, and flags
suspicious results before they make it into the final report.
"""

import logging
import numpy as np
import pandas as pd

log = logging.getLogger("ml")


class SafetyCheckFailed(Exception):
    """Raised when a critical safety check fails and pipeline should abort."""
    pass


def check_target_distribution(y, config):
    """
    Verify the target variable has a reasonable distribution.
    Aborts if delinquency rate is unreasonably low or high.
    """
    rate = float(y.mean())
    min_rate = config["safety"]["min_delinquency_rate"]
    max_rate = config["safety"]["max_delinquency_rate"]

    log.info(f"  Target distribution: {rate:.4f} ({100*rate:.2f}%)")

    if rate < min_rate:
        raise SafetyCheckFailed(
            f"Delinquency rate {rate:.4f} is below minimum {min_rate}. "
            f"Data may be filtered incorrectly."
        )
    if rate > max_rate:
        raise SafetyCheckFailed(
            f"Delinquency rate {rate:.4f} exceeds maximum {max_rate}. "
            f"Target variable may be defined incorrectly."
        )
    return True


def check_feature_leakage(X, y, config, feature_names):
    """
    Check for features that are suspiciously correlated with the target.
    Returns a list of flagged features with their correlation values.
    """
    threshold = config["safety"]["leakage_correlation_threshold"]
    flagged = []

    for i, col in enumerate(feature_names):
        if X.iloc[:, i].nunique() <= 1:
            continue
        try:
            corr = abs(np.corrcoef(X.iloc[:, i].astype(float), y.astype(float))[0, 1])
            if np.isnan(corr):
                continue
            if corr >= threshold:
                flagged.append({"feature": col, "correlation": round(corr, 4)})
        except (ValueError, TypeError):
            continue

    if flagged:
        log.warning(f"  LEAKAGE WARNING: {len(flagged)} feature(s) with "
                    f"correlation >= {threshold}:")
        for f in flagged:
            log.warning(f"    {f['feature']}: {f['correlation']}")
    else:
        log.info(f"  Leakage check: PASS (no features above {threshold} correlation)")

    return flagged


def check_split_validity(y_train, y_test, config):
    """Verify both train and test sets have enough delinquent loans."""
    min_count = config["safety"]["min_test_delinquent_count"]

    train_dlq = int(y_train.sum())
    test_dlq = int(y_test.sum())

    log.info(f"  Split validity: train has {train_dlq:,} DLQ, test has {test_dlq:,} DLQ")

    if test_dlq < min_count:
        raise SafetyCheckFailed(
            f"Test set has only {test_dlq} delinquent loans "
            f"(minimum: {min_count}). Split may be incorrect."
        )
    if train_dlq < min_count:
        raise SafetyCheckFailed(
            f"Train set has only {train_dlq} delinquent loans "
            f"(minimum: {min_count}). Split may be incorrect."
        )
    return True


def check_post_training(metrics, model_type, config):
    """
    Post-training sanity check on model metrics.
    Returns a status dict with flags.
    """
    auc = metrics.get("auc_roc", 0)
    threshold = config["safety"]["auc_leakage_flag"]

    status = {
        "auc_flag": False,
        "perfect_precision": False,
        "perfect_recall": False,
        "diagnosis": "healthy",
    }

    if auc >= threshold:
        status["auc_flag"] = True
        if model_type == "origination":
            status["diagnosis"] = "LEAKAGE_SUSPECTED"
            log.error(f"  POST-TRAINING ALERT: {model_type} model AUC={auc:.4f} "
                      f"exceeds {threshold}. Likely data leakage.")
        else:
            status["diagnosis"] = "expected_behavioral"
            log.info(f"  POST-TRAINING NOTE: {model_type} model AUC={auc:.4f}. "
                     f"Expected for behavioral features — reporting as segmentation tool.")

    if metrics.get("precision", 0) == 1.0:
        status["perfect_precision"] = True
    if metrics.get("recall", 0) == 1.0:
        status["perfect_recall"] = True

    # Overfitting check: would need train AUC to compare, but we flag extreme values
    if auc >= 0.999 and model_type == "origination":
        status["diagnosis"] = "LEAKAGE_CONFIRMED"
        log.error(f"  ABORT RECOMMENDED: Origination model AUC={auc:.4f} indicates "
                  f"target leakage in features.")

    return status
