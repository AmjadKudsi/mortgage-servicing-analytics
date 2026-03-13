-- ============================================================
-- 03_delinquency_analysis.sql
-- Purpose: Delinquency rates sliced by every key dimension
-- Consumer: Tableau Page 1, dashboard charts, report
-- ============================================================

-- A: Delinquency by DPD bucket (portfolio-wide distribution)
SELECT
    dpd_bucket,
    COUNT(*)                                          AS loans,
    ROUND(SUM(current_upb), 0)                        AS total_upb,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) AS pct_of_portfolio
FROM loans
GROUP BY dpd_bucket
ORDER BY
    CASE dpd_bucket
        WHEN 'Current' THEN 1
        WHEN '30_DPD' THEN 2
        WHEN '60_DPD' THEN 3
        WHEN '90_DPD' THEN 4
        WHEN '120_Plus_DPD' THEN 5
        WHEN 'REO_Acquired' THEN 6
        ELSE 7
    END
