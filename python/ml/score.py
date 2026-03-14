"""
score.py — Score all loans and generate risk-ranked segments.
"""

import logging
import pandas as pd

log = logging.getLogger("ml")


def score_loans(trained, X, df, config):
    """
    Score every loan with a risk probability.
    Returns the DataFrame with a 'risk_score' column added.
    """
    model = trained["model"]
    scaler = trained["scaler"]

    X_score = scaler.transform(X) if scaler else X
    df = df.copy()
    df["risk_score"] = model.predict_proba(X_score)[:, 1]

    log.info(f"  Scored {len(df):,} loans")
    log.info(f"    Mean risk score: {df['risk_score'].mean():.4f}")
    log.info(f"    Median: {df['risk_score'].median():.4f}")
    log.info(f"    95th percentile: {df['risk_score'].quantile(0.95):.4f}")

    return df


def rank_segments(scored_df, config):
    """
    Aggregate scored loans into risk-ranked segments.
    Returns a DataFrame sorted by average risk score descending.
    """
    min_size = config.get("min_segment_size", 30)

    segments = scored_df.groupby(
        ["credit_score_band", "ltv_bucket", "rate_bucket", "orig_year"]
    ).agg(
        loans=("loan_id", "count"),
        total_upb=("current_upb", "sum"),
        avg_risk_score=("risk_score", "mean"),
        actual_dlq_rate=("is_delinquent", "mean"),
        avg_fico=("credit_score", "mean"),
        avg_rate=("orig_interest_rate", "mean"),
    ).reset_index()

    segments = segments[segments["loans"] >= min_size].copy()
    segments = segments.sort_values("avg_risk_score", ascending=False)

    # Format for readability
    segments["actual_dlq_rate"] = (segments["actual_dlq_rate"] * 100).round(2)
    segments["avg_risk_score"] = (segments["avg_risk_score"] * 100).round(2)
    segments["avg_fico"] = segments["avg_fico"].round(0)
    segments["avg_rate"] = segments["avg_rate"].round(3)
    segments["total_upb"] = segments["total_upb"].round(0)

    log.info(f"  Segments (≥{min_size} loans): {len(segments):,}")

    # Log top 10
    log.info(f"\n  Top 10 riskiest segments:")
    for _, row in segments.head(10).iterrows():
        log.info(f"    {row['credit_score_band']:>20s} | "
                 f"{row['ltv_bucket']:>15s} | "
                 f"{row['rate_bucket']:>12s} | "
                 f"{int(row['orig_year'])} | "
                 f"Score: {row['avg_risk_score']:>5.1f}% | "
                 f"DLQ: {row['actual_dlq_rate']:>5.2f}% | "
                 f"{int(row['loans']):>6,} loans")

    return segments
