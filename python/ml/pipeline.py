"""
pipeline.py — ML Pipeline Orchestrator.

Runs two model types:
    Model B (origination-only): Genuine predictor using only features
        known at time of lending. Produces honest AUC and lift metrics.
    Model A (behavioral): Risk segmentation tool using all features
        including payment history. Produces segment rankings.

Usage:
    python pipeline.py
    python pipeline.py --db data/mortgage_analytics.duckdb
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime

import joblib

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "etl"))
from utils import load_config

from features import load_feature_matrix, prepare_feature_set, split_by_loan_age
from safety import (
    check_target_distribution, check_feature_leakage,
    check_split_validity, check_post_training, SafetyCheckFailed
)
from train import train_model
from evaluate import evaluate_model
from score import score_loans, rank_segments


def setup_ml_logging(log_file):
    """Configure ML-specific logging."""
    os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-5s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, mode="w"),
        ],
    )
    return logging.getLogger("ml")


def run_model_b(df, config, feature_names_out):
    """
    Model B: Origination-only predictor.
    Uses only features available at time of lending.
    Produces genuine predictive metrics.
    """
    log = logging.getLogger("ml")
    log.info("\n" + "=" * 60)
    log.info("MODEL B: ORIGINATION RISK PREDICTOR")
    log.info("=" * 60)
    log.info("Features: origination-only (no payment history)")
    log.info("Purpose: predict delinquency from borrower/loan characteristics")

    # Prepare origination-only features
    X, y, feat_names = prepare_feature_set(df, config, model_type="origination")
    feature_names_out["model_b"] = feat_names

    # Safety: check target distribution
    check_target_distribution(y, config)

    # Safety: check for leakage (should find none for origination features)
    leakage = check_feature_leakage(X, y, config, feat_names)

    # Split
    X_train, X_test, y_train, y_test, split_info = split_by_loan_age(X, y, df)

    # Safety: check split validity
    check_split_validity(y_train, y_test, config)

    # Train both LR and RF
    results = {}
    best_model = None
    best_auc = -1

    for model_name in ["logistic_regression", "random_forest"]:
        try:
            trained = train_model(X_train, y_train, model_name, config)
            metrics = evaluate_model(trained, X_test, y_test, feat_names, config)

            # Post-training safety check
            post_status = check_post_training(metrics, "origination", config)
            metrics["safety_status"] = post_status

            results[model_name] = {
                "trained": trained,
                "metrics": metrics,
            }

            if metrics["auc_roc"] > best_auc:
                best_auc = metrics["auc_roc"]
                best_model = model_name

        except Exception as e:
            log.error(f"  {model_name} FAILED: {e}")
            results[model_name] = {"error": str(e)}

    log.info(f"\n  Best Model B: {best_model} (AUC: {best_auc:.4f})")

    return {
        "results": results,
        "best_model": best_model,
        "split_info": split_info,
        "leakage_flags": leakage,
    }


def run_model_a(df, config, feature_names_out):
    """
    Model A: Behavioral risk segmentation tool.
    Uses all features including payment history.
    Produces segment rankings, not predictive metrics.
    """
    log = logging.getLogger("ml")
    log.info("\n" + "=" * 60)
    log.info("MODEL A: BEHAVIORAL RISK SEGMENTATION")
    log.info("=" * 60)
    log.info("Features: origination + payment history (behavioral)")
    log.info("Purpose: score and rank loan segments by current risk")

    # Prepare full feature set
    X, y, feat_names = prepare_feature_set(df, config, model_type="behavioral")
    feature_names_out["model_a"] = feat_names

    # Train RF only (best for segmentation)
    trained = train_model(X, y, "random_forest", config)

    # Score all loans (no train/test split — we use the full dataset for scoring)
    scored_df = score_loans(trained, X, df, config)

    # Rank segments
    segments = rank_segments(scored_df, config)

    # Get feature importance
    from evaluate import _get_feature_importance
    importance = _get_feature_importance(trained["model"], feat_names)
    if importance:
        log.info(f"\n  Feature importance (behavioral model):")
        for feat in importance[:10]:
            log.info(f"    {feat['feature']}: {feat['importance']:.4f}")

    return {
        "trained": trained,
        "segments": segments,
        "scored_df": scored_df,
        "feature_importance": importance,
    }


def save_all(model_b_output, model_a_output, config, feature_names):
    """Save all artifacts."""
    log = logging.getLogger("ml")
    output_dir = config["paths"]["output_dir"]
    os.makedirs(output_dir, exist_ok=True)

    log.info("\n" + "=" * 60)
    log.info("SAVING ARTIFACTS")
    log.info("=" * 60)

    # ── Model B artifacts ──
    best_name = model_b_output["best_model"]
    if best_name and best_name in model_b_output["results"]:
        best = model_b_output["results"][best_name]["trained"]
        path = os.path.join(output_dir, "model_b.joblib")
        joblib.dump({"model": best["model"], "scaler": best["scaler"],
                     "model_name": best_name}, path)
        log.info(f"  Model B saved: {path}")

    # ── Model A artifacts ──
    a_trained = model_a_output["trained"]
    path = os.path.join(output_dir, "model_a.joblib")
    joblib.dump({"model": a_trained["model"], "scaler": a_trained["scaler"],
                 "model_name": "random_forest"}, path)
    log.info(f"  Model A saved: {path}")

    # ── Segments CSV ──
    seg_path = os.path.join(output_dir, "risk_segments.csv")
    model_a_output["segments"].to_csv(seg_path, index=False)
    log.info(f"  Segments saved: {seg_path} ({len(model_a_output['segments']):,} segments)")

    # ── Evaluation report JSON ──
    report = {
        "generated_at": datetime.now().isoformat(),
        "model_b": {
            "purpose": "Origination risk predictor — genuine predictive model",
            "features_used": feature_names.get("model_b", []),
            "split_info": model_b_output["split_info"],
            "leakage_flags": model_b_output["leakage_flags"],
            "models": {},
        },
        "model_a": {
            "purpose": "Behavioral risk segmentation — current portfolio risk scoring",
            "features_used": feature_names.get("model_a", []),
            "feature_importance": model_a_output["feature_importance"],
            "total_segments": len(model_a_output["segments"]),
        },
    }

    for name, data in model_b_output["results"].items():
        if "metrics" in data:
            report["model_b"]["models"][name] = data["metrics"]

    report_path = os.path.join(output_dir, "evaluation_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    log.info(f"  Report saved: {report_path}")


def run(db_path, config_path=None):
    """Main entry point."""
    # Load config
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), "config_ml.yaml")
    config = load_config(config_path)

    log = setup_ml_logging(config["paths"]["log_file"])

    log.info("=" * 60)
    log.info("MORTGAGE DELINQUENCY RISK MODEL")
    log.info("=" * 60)

    # Load features
    sql_path = config["paths"]["feature_sql"]
    df = load_feature_matrix(db_path, sql_path)

    feature_names = {}

    # ── Run Model B (origination predictor) ──
    try:
        model_b_output = run_model_b(df, config, feature_names)
    except SafetyCheckFailed as e:
        log.error(f"\nMODEL B ABORTED: {e}")
        return

    # ── Run Model A (behavioral segmentation) ──
    try:
        model_a_output = run_model_a(df, config, feature_names)
    except Exception as e:
        log.error(f"\nMODEL A FAILED: {e}")
        return

    # ── Save everything ──
    save_all(model_b_output, model_a_output, config, feature_names)

    # ── Final summary ──
    log.info("\n" + "=" * 60)
    log.info("PIPELINE COMPLETE")
    log.info("=" * 60)

    best_name = model_b_output["best_model"]
    if best_name and best_name in model_b_output["results"]:
        best_metrics = model_b_output["results"][best_name]["metrics"]
        log.info(f"  Model B ({best_name}):")
        log.info(f"    AUC: {best_metrics['auc_roc']:.4f}")
        log.info(f"    Lift at 10%: {best_metrics['lift_analysis'][2]['capture_rate_pct']:.1f}% capture")

    log.info(f"  Model A (behavioral RF):")
    log.info(f"    Segments scored: {len(model_a_output['segments']):,}")
    top_seg = model_a_output["segments"].head(1).iloc[0] if len(model_a_output["segments"]) > 0 else None
    if top_seg is not None:
        log.info(f"    Highest risk: {top_seg['credit_score_band']} / "
                 f"{top_seg['ltv_bucket']} / {int(top_seg['orig_year'])} "
                 f"→ {top_seg['actual_dlq_rate']:.1f}% DLQ")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mortgage Delinquency Risk Model")
    parser.add_argument("--db", "-d", default="data/mortgage_analytics.duckdb")
    parser.add_argument("--config", "-c", default=None)
    args = parser.parse_args()

    run(args.db, args.config)
