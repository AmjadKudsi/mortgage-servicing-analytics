-- ============================================================
-- 06_prepayment_analysis.sql
-- Purpose: Portfolio-level prepayment behavior by comparing
--          original UPB to current UPB across vintages and rates
-- Author: Amjad Ali Kudsi
-- Consumer: Tableau Page 3, report
--
-- Note: This computes cumulative principal paydown, not monthly
--       SMM/CPR (which requires sequential monthly snapshots
--       we don't have in this single-point-in-time dataset).
-- ============================================================

SELECT
    CAST(orig_year AS INTEGER)                        AS orig_year,
    rate_bucket,
    COUNT(*)                                          AS loans,
    ROUND(SUM(orig_loan_amount), 0)                   AS total_orig_amount,
    ROUND(SUM(current_upb), 0)                        AS total_current_upb,
    ROUND(SUM(orig_loan_amount) - SUM(current_upb), 0) AS total_paydown,
    ROUND(
        100.0 * (SUM(orig_loan_amount) - SUM(current_upb))
        / NULLIF(SUM(orig_loan_amount), 0), 2
    )                                                  AS paydown_pct,
    ROUND(AVG(loan_age), 0)                           AS avg_loan_age_months,
    ROUND(AVG(orig_interest_rate), 3)                 AS avg_rate
FROM loans
WHERE orig_year IS NOT NULL
  AND orig_loan_amount > 0
  AND current_upb >= 0
GROUP BY orig_year, rate_bucket
ORDER BY orig_year, rate_bucket
