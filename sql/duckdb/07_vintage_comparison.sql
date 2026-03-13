-- ============================================================
-- 07_vintage_comparison.sql
-- Purpose: Side-by-side performance metrics across all vintages
-- Consumer: Tableau Page 3, report vintage table, dashboard
-- ============================================================

SELECT
    CAST(orig_year AS INTEGER)                                  AS orig_year,
    COUNT(*)                                                    AS loans,
    ROUND(SUM(current_upb) / 1e9, 2)                           AS upb_billions,
    ROUND(100.0 * SUM(is_delinquent) / COUNT(*), 2)           AS dlq_rate_pct,
    ROUND(100.0 * SUM(is_seriously_delinquent) / COUNT(*), 2) AS serious_dlq_pct,
    ROUND(AVG(credit_score), 0)                                AS avg_fico,
    ROUND(AVG(orig_interest_rate), 3)                          AS avg_rate,
    ROUND(AVG(ltv), 1)                                         AS avg_ltv,
    ROUND(AVG(loan_age), 0)                                    AS avg_loan_age,
    -- DPD bucket breakdown within each vintage
    ROUND(100.0 * SUM(CASE WHEN dpd_bucket = '30_DPD' THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct_30dpd,
    ROUND(100.0 * SUM(CASE WHEN dpd_bucket = '60_DPD' THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct_60dpd,
    ROUND(100.0 * SUM(CASE WHEN dpd_bucket = '90_DPD' THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct_90dpd,
    ROUND(100.0 * SUM(CASE WHEN dpd_bucket = '120_Plus_DPD' THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct_120plus,
    -- Credit score band distribution
    ROUND(100.0 * SUM(CASE WHEN credit_score_band = 'Excellent (780+)' THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_excellent,
    ROUND(100.0 * SUM(CASE WHEN credit_score_band = 'Fair (620-679)' THEN 1 ELSE 0 END) / COUNT(*), 1)   AS pct_fair
FROM loans
WHERE orig_year IS NOT NULL
GROUP BY orig_year
ORDER BY orig_year
