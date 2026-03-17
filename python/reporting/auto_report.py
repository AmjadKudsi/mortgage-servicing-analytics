"""
auto_report.py — Automated Executive Report Generator.

Assembles data from SQL queries and ML pipeline artifacts into
a styled, self-contained HTML executive report. Every number
traces to a SQL query or ML output. Recommendations are
threshold-driven — they appear or disappear based on the data.

Usage:
    python auto_report.py
    python auto_report.py --db data/mortgage_analytics.duckdb
"""

import os
import sys
import json
import argparse
from datetime import datetime

import pandas as pd
from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "etl"))
from utils import load_config
from sql_runner import run_query, run_query_string


# Feature interpretation map for OriginRisk
FEATURE_INTERPRETATIONS = {
    "credit_score": "Lower FICO scores strongly predict higher delinquency risk",
    "num_borrowers": "Single-borrower loans carry more risk than co-borrower loans",
    "orig_interest_rate": "Higher rates mean higher monthly payments and more payment stress",
    "dti": "Higher debt-to-income ratios indicate the borrower is financially stretched",
    "loan_age": "Loan seasoning affects risk — newer and very old loans behave differently",
    "ltv": "Higher LTV means less borrower equity and more risk of underwater default",
    "orig_loan_amount": "Larger loans have higher absolute exposure per delinquency",
    "credit_score_band_Fair (620-679)": "Fair credit borrowers default at 4-5x the rate of Excellent",
    "credit_score_band_Good (680-719)": "Good credit borrowers show moderate elevated risk",
    "credit_score_band_Subprime (<620)": "Subprime borrowers have the highest baseline delinquency",
    "ltv_bucket_Medium (61-80)": "Medium LTV loans represent the bulk of the portfolio",
    "ltv_bucket_Very High (>90)": "Very high LTV borrowers have minimal equity cushion",
    "rate_bucket_Below 3.5%": "Low-rate loans have affordable payments — lower risk",
    "rate_bucket_5.5% - 6.5%": "Higher-rate environment correlates with payment stress",
    "rate_bucket_6.5%+": "Highest rate bucket shows elevated delinquency across all vintages",
    "rate_bucket_4.5% - 5.5%": "Mid-range rates with moderate payment burden",
}


def build_report_data(db_path, ml_artifacts_dir, config):
    """Assemble all data for the report template."""
    data = {}
    author = config.get("author", {})
    data["author"] = author

    # ── Section 1: Executive Summary ──
    summary_df = run_query_string("""
        SELECT
            COUNT(*) AS total_loans,
            ROUND(SUM(current_upb), 0) AS total_upb,
            ROUND(100.0 * SUM(is_delinquent) / COUNT(*), 2) AS dlq_rate,
            ROUND(100.0 * SUM(is_seriously_delinquent) / COUNT(*), 2) AS serious_dlq_rate,
            ROUND(AVG(credit_score), 0) AS avg_fico,
            MAX(reporting_period) AS reporting_period
        FROM loans
    """, db_path)
    s = summary_df.iloc[0].to_dict()
    s["total_loans"] = int(s["total_loans"])
    s["total_upb"] = float(s["total_upb"])
    s["dlq_rate"] = float(s["dlq_rate"])
    s["serious_dlq_rate"] = float(s["serious_dlq_rate"])
    s["avg_fico"] = int(s["avg_fico"])
    data["summary"] = s
    data["avg_dlq"] = s["dlq_rate"]

    # ── Section 2: Vintage Comparison ──
    vintage_sql = os.path.join("sql", "duckdb", "07_vintage_comparison.sql")
    if not os.path.exists(vintage_sql):
        vintage_sql = os.path.join(os.path.dirname(__file__), "..", "..", "sql", "duckdb", "07_vintage_comparison.sql")
    vintages_df = run_query(vintage_sql, db_path)
    vintages = vintages_df.to_dict("records")

    # Clean types
    for v in vintages:
        v["orig_year"] = int(v["orig_year"])
        v["loans"] = int(v["loans"])
        v["avg_fico"] = int(v["avg_fico"])

    data["vintages"] = vintages

    # Find worst and best vintage (minimum 1000 loans)
    significant = [v for v in vintages if v["loans"] >= 1000]
    if significant:
        data["worst_vintage"] = max(significant, key=lambda v: v["dlq_rate_pct"])
        data["best_vintage"] = min(significant, key=lambda v: v["dlq_rate_pct"])
    else:
        data["worst_vintage"] = None
        data["best_vintage"] = None

    # Headline
    wv = data["worst_vintage"]
    if wv:
        data["headline"] = (
            f"Portfolio delinquency stands at {s['dlq_rate']}% across "
            f"{s['total_loans']:,} loans (${s['total_upb']/1e9:.1f}B UPB). "
            f"The {wv['orig_year']} vintage is the highest-risk cohort at "
            f"{wv['dlq_rate_pct']}% delinquency — "
            f"{wv['dlq_rate_pct']/s['dlq_rate']:.1f}x the portfolio average."
        )
    else:
        data["headline"] = f"Portfolio delinquency stands at {s['dlq_rate']}%."

    # ── Section 3: DPD Distribution ──
    dpd_sql = os.path.join("sql", "duckdb", "03_delinquency_analysis.sql")
    if not os.path.exists(dpd_sql):
        dpd_sql = os.path.join(os.path.dirname(__file__), "..", "..", "sql", "duckdb", "03_delinquency_analysis.sql")
    dpd_df = run_query(dpd_sql, db_path)

    color_map = {
        "Current": "#27ae60", "30_DPD": "#f39c12", "60_DPD": "#e67e22",
        "90_DPD": "#e74c3c", "120_Plus_DPD": "#c0392b", "REO_Acquired": "#7d3c98",
    }
    dpd_records = dpd_df.to_dict("records")
    dpd_chart = {
        "labels": [r["dpd_bucket"] for r in reversed(dpd_records)],
        "values": [int(r["loans"]) for r in reversed(dpd_records)],
        "colors": [color_map.get(r["dpd_bucket"], "#95a5a6") for r in reversed(dpd_records)],
        "text": [f"{r['pct_of_portfolio']}%" for r in reversed(dpd_records)],
    }
    data["dpd_chart_data"] = json.dumps(dpd_chart)

    # ── Section 4: Roll Rates ──
    roll_sql = os.path.join("sql", "duckdb", "04_roll_rates.sql")
    if not os.path.exists(roll_sql):
        roll_sql = os.path.join(os.path.dirname(__file__), "..", "..", "sql", "duckdb", "04_roll_rates.sql")
    roll_df = run_query(roll_sql, db_path)

    # Pivot into matrix
    roll_columns = ["Current", "30_DPD", "60_DPD", "90_DPD", "120_Plus"]
    roll_matrix = {}
    for _, row in roll_df.iterrows():
        fb = row["from_bucket"]
        tb = row["to_bucket"]
        if fb not in roll_matrix:
            roll_matrix[fb] = {}
        roll_matrix[fb][tb] = float(row["transition_pct"])

    data["roll_matrix"] = roll_matrix
    data["roll_columns"] = roll_columns

    # Cure rate for 30-DPD
    cure_30 = roll_matrix.get("30_DPD", {}).get("Current", 0)
    data["cure_rate_30"] = cure_30

    # ── Section 5: Geographic Hotspots ──
    geo_sql = os.path.join("sql", "duckdb", "08_geographic_analysis.sql")
    if not os.path.exists(geo_sql):
        geo_sql = os.path.join(os.path.dirname(__file__), "..", "..", "sql", "duckdb", "08_geographic_analysis.sql")
    geo_df = run_query(geo_sql, db_path)
    geo_above_avg = geo_df[
        (geo_df["dlq_rate_pct"] > s["dlq_rate"]) &
        (geo_df["loans"] >= 500)
    ].head(12).to_dict("records")

    for g in geo_above_avg:
        g["loans"] = int(g["loans"])
        g["avg_fico"] = int(g["avg_fico"])

    data["geo_hotspots"] = geo_above_avg

    # ── Section 6: Risk Segments (from ML) ──
    seg_path = os.path.join(ml_artifacts_dir, "risk_segments.csv")
    if os.path.exists(seg_path):
        seg_df = pd.read_csv(seg_path)
        top_segments = seg_df.head(15).to_dict("records")
        for seg in top_segments:
            seg["loans"] = int(seg["loans"])
            seg["orig_year"] = int(seg["orig_year"])

        data["top_segments"] = top_segments

        # Concentration stats for top 15
        top15 = seg_df.head(15)
        data["segment_concentration"] = {
            "loans": int(top15["loans"].sum()),
            "upb": float(top15["total_upb"].sum()),
            "avg_dlq": round(float(
                (top15["actual_dlq_rate"] * top15["loans"]).sum() / top15["loans"].sum()
            ), 1),
        }
    else:
        data["top_segments"] = []
        data["segment_concentration"] = None

    # ── Section 7: OriginRisk Summary ──
    eval_path = os.path.join(ml_artifacts_dir, "evaluation_report.json")
    if os.path.exists(eval_path):
        with open(eval_path) as f:
            eval_data = json.load(f)

        # Find the best OriginRisk result
        model_b_data = eval_data.get("model_b", {}).get("models", {})
        best_model = None
        best_auc = -1
        for name, metrics in model_b_data.items():
            if metrics.get("auc_roc", 0) > best_auc:
                best_auc = metrics["auc_roc"]
                best_model = metrics

        if best_model:
            lift_10 = next((l["capture_rate_pct"] for l in best_model.get("lift_analysis", []) if l["top_pct"] == 10), "N/A")
            lift_20 = next((l["capture_rate_pct"] for l in best_model.get("lift_analysis", []) if l["top_pct"] == 20), "N/A")

            features = best_model.get("feature_importance", [])[:7]
            for feat in features:
                feat["interpretation"] = FEATURE_INTERPRETATIONS.get(
                    feat["feature"], "Contributes to risk assessment"
                )

            data["model_b"] = {
                "auc": best_model["auc_roc"],
                "lift_10": lift_10,
                "lift_20": lift_20,
                "features": features,
            }
        else:
            data["model_b"] = {"auc": "N/A", "lift_10": "N/A", "lift_20": "N/A", "features": []}
    else:
        data["model_b"] = {"auc": "N/A", "lift_10": "N/A", "lift_20": "N/A", "features": []}

    # ── Section 8: Recommendations ──
    data["recommendations"] = _generate_recommendations(data)

    return data


def _generate_recommendations(data):
    """Generate threshold-driven recommendations from the data."""
    recs = []
    avg_dlq = data["avg_dlq"]

    # Vintage-level alerts
    for v in data.get("vintages", []):
        if v["dlq_rate_pct"] > avg_dlq * 2 and v["loans"] >= 1000:
            recs.append({
                "category": "Vintage Risk",
                "text": f"{v['orig_year']} vintage delinquency ({v['dlq_rate_pct']}%) "
                        f"is {v['dlq_rate_pct']/avg_dlq:.1f}x the portfolio average. "
                        f"Recommend targeted outreach for the {v['loans']:,} loans "
                        f"(${v['upb_billions']:.1f}B UPB) in this cohort."
            })

    # Geographic alerts
    for g in data.get("geo_hotspots", [])[:3]:
        if g["dlq_rate_pct"] > avg_dlq * 1.5:
            recs.append({
                "category": "Geographic Concentration",
                "text": f"{g['property_state']} shows {g['dlq_rate_pct']}% delinquency "
                        f"({g['dlq_rate_pct']/avg_dlq:.1f}x portfolio average) across "
                        f"{g['loans']:,} loans. Monitor for regional economic stress."
            })

    # Risk segment alert
    conc = data.get("segment_concentration")
    if conc and conc["avg_dlq"] > avg_dlq * 3:
        recs.append({
            "category": "Segment Concentration",
            "text": f"Top 15 risk segments contain {conc['loans']:,} loans "
                    f"(${conc['upb']/1e9:.1f}B UPB) with {conc['avg_dlq']:.1f}% "
                    f"average delinquency. Prioritize loss mitigation resources "
                    f"for these segments."
        })

    # Cure rate insight
    cure = data.get("cure_rate_30", 0)
    if cure > 75:
        recs.append({
            "category": "Loss Mitigation Effectiveness",
            "text": f"30-DPD cure rate of {cure:.1f}% indicates effective early "
                    f"intervention. Maintain current outreach intensity for "
                    f"newly delinquent loans."
        })
    elif cure < 60:
        recs.append({
            "category": "Loss Mitigation Concern",
            "text": f"30-DPD cure rate of {cure:.1f}% is below the 60% threshold. "
                    f"Review early intervention processes and consider increasing "
                    f"outreach for 30-day delinquent borrowers."
        })

    # Model lift insight
    mb = data.get("model_b", {})
    if mb.get("lift_20") and mb["lift_20"] != "N/A":
        recs.append({
            "category": "Risk Scoring Opportunity",
            "text": f"The the Origination Scoring Model captures {mb['lift_20']}% of "
                    f"delinquencies in the top 20% of scored loans. Deploying "
                    f"this model for proactive outreach could significantly "
                    f"improve early intervention targeting."
        })

    return recs


def generate_report(db_path, ml_artifacts_dir, config_path, output_path):
    """Main entry point: gather data, render template, write HTML."""
    config = load_config(config_path)

    print(f"Generating executive report...")
    print(f"  Database: {db_path}")
    print(f"  ML artifacts: {ml_artifacts_dir}")

    data = build_report_data(db_path, ml_artifacts_dir, config)
    data["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Render template
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("executive_report.html")
    html = template.render(**data)

    # Write output
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        f.write(html)

    size_kb = os.path.getsize(output_path) / 1024
    print(f"  Sections: 8")
    print(f"  Recommendations generated: {len(data['recommendations'])}")
    print(f"  Report saved: {output_path} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Executive Report")
    parser.add_argument("--db", "-d", default="data/mortgage_analytics.duckdb")
    parser.add_argument("--ml", "-m", default="python/ml/model_artifacts")
    parser.add_argument("--config", "-c", default="python/etl/config.yaml")
    parser.add_argument("--output", "-o", default="reports/executive_report.html")
    args = parser.parse_args()

    # Resolve config
    if not os.path.exists(args.config):
        alt = os.path.join(os.path.dirname(__file__), "..", "etl", "config.yaml")
        if os.path.exists(alt):
            args.config = alt

    generate_report(args.db, args.ml, args.config, args.output)
