"""
evaluate.py — Model evaluation with ML and business metrics.
"""

import logging
import numpy as np
import pandas as pd
from sklearn.metrics import (
    roc_auc_score, precision_score, recall_score, f1_score,
    confusion_matrix,
)

log = logging.getLogger("ml")


def evaluate_model(trained, X_test, y_test, feature_names, config):
    """
    Evaluate a trained model with both ML and business metrics.

    Args:
        trained: dict from train.train_model()
        X_test: test features
        y_test: test target
        feature_names: list of feature names
        config: ML config dict

    Returns:
        dict with all metrics, lift analysis, feature importance
    """
    model = trained["model"]
    scaler = trained["scaler"]
    model_name = trained["model_name"]

    # Get probabilities
    X_eval = scaler.transform(X_test) if scaler else X_test
    y_prob = model.predict_proba(X_eval)[:, 1]
    y_pred = model.predict(X_eval)

    # ── ML metrics ──
    auc = roc_auc_score(y_test, y_prob)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    cm = confusion_matrix(y_test, y_pred)

    log.info(f"\n  {model_name}:")
    log.info(f"    AUC-ROC:   {auc:.4f}")
    log.info(f"    Precision: {precision:.4f}")
    log.info(f"    Recall:    {recall:.4f}")
    log.info(f"    F1:        {f1:.4f}")

    # ── Lift analysis ──
    lift_percentiles = config.get("lift_percentiles", [1, 5, 10, 20])
    lift_results = _compute_lift(y_test, y_prob, lift_percentiles)

    log.info(f"    Lift:")
    total_dlq = int(y_test.sum())
    for row in lift_results:
        log.info(f"      Top {row['top_pct']}% ({row['loans_reviewed']:,} loans) "
                 f"→ {row['delinquencies_caught']:,}/{total_dlq:,} "
                 f"({row['capture_rate_pct']:.1f}%)")

    # ── Feature importance ──
    importance = _get_feature_importance(model, feature_names)
    if importance:
        log.info(f"    Top 5 features:")
        for feat in importance[:5]:
            log.info(f"      {feat['feature']}: {feat['importance']:.4f}")

    return {
        "model_name": model_name,
        "train_time": trained["train_time"],
        "auc_roc": round(auc, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "confusion_matrix": cm.tolist(),
        "lift_analysis": lift_results,
        "feature_importance": importance,
    }


def _compute_lift(y_true, y_prob, percentiles):
    """Compute lift table: what % of delinquencies found in top N% of scores."""
    df = pd.DataFrame({"y": y_true.values, "p": y_prob})
    df = df.sort_values("p", ascending=False)
    total_dlq = df["y"].sum()

    results = []
    for pct in percentiles:
        n = max(1, int(len(df) * pct / 100))
        caught = df.head(n)["y"].sum()
        capture = 100 * caught / total_dlq if total_dlq > 0 else 0
        results.append({
            "top_pct": pct,
            "loans_reviewed": n,
            "delinquencies_caught": int(caught),
            "capture_rate_pct": round(capture, 1),
        })
    return results


def _get_feature_importance(model, feature_names):
    """Extract feature importance, works for RF and LR."""
    importance = []
    if hasattr(model, "feature_importances_"):
        imp = model.feature_importances_
    elif hasattr(model, "coef_"):
        imp = np.abs(model.coef_[0])
    else:
        return importance

    for name, val in sorted(zip(feature_names, imp), key=lambda x: -x[1])[:15]:
        importance.append({"feature": name, "importance": round(float(val), 4)})
    return importance
