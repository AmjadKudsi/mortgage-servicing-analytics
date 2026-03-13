-- ============================================================
-- 05_risk_segmentation.sql
-- Purpose: Cross-tabulation of risk dimensions with delinquency
--          rates and UPB exposure per segment
-- Author: Amjad Ali Kudsi
-- Consumer: ML feature matrix, risk heatmap, report top-10
-- ============================================================

SELECT
    credit_score_band,
    ltv_bucket,
    rate_bucket,
    CAST(orig_year AS INTEGER)                                  AS orig_year,
    COUNT(*)                                                    AS loans,
    ROUND(SUM(current_upb), 0)                                 AS total_upb,
    ROUND(100.0 * SUM(is_delinquent) / COUNT(*), 2)           AS dlq_rate_pct,
    ROUND(100.0 * SUM(is_seriously_delinquent) / COUNT(*), 2) AS serious_dlq_pct,
    ROUND(AVG(credit_score), 0)                                AS avg_fico,
    ROUND(AVG(orig_interest_rate), 3)                          AS avg_rate,
    ROUND(AVG(loan_age), 0)                                    AS avg_loan_age
FROM loans
WHERE credit_score_band != 'Unknown'
  AND ltv_bucket != 'Unknown'
  AND orig_year IS NOT NULL
GROUP BY credit_score_band, ltv_bucket, rate_bucket, orig_year
HAVING COUNT(*) >= 20
ORDER BY dlq_rate_pct DESC
