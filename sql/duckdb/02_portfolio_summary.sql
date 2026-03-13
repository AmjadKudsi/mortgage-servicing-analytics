-- ============================================================
-- 02_portfolio_summary.sql
-- Purpose: Top-level portfolio KPIs and breakdowns
-- Consumer: Dashboard KPI cards, report summary section
-- ============================================================

-- Overall portfolio snapshot
SELECT
    COUNT(*)                                                    AS total_loans,
    ROUND(SUM(current_upb), 0)                                 AS total_upb,
    ROUND(AVG(credit_score), 0)                                AS avg_credit_score,
    ROUND(AVG(orig_interest_rate), 3)                          AS avg_orig_rate,
    ROUND(AVG(ltv), 1)                                         AS avg_ltv,
    ROUND(100.0 * SUM(is_delinquent) / COUNT(*), 2)           AS delinquency_rate_pct,
    ROUND(100.0 * SUM(is_seriously_delinquent) / COUNT(*), 2) AS serious_dlq_rate_pct,
    SUM(is_delinquent)                                         AS delinquent_loans,
    SUM(is_seriously_delinquent)                                AS seriously_delinquent_loans,
    MIN(orig_year)                                              AS earliest_vintage,
    MAX(orig_year)                                              AS latest_vintage,
    COUNT(DISTINCT property_state)                              AS states_covered,
    COUNT(DISTINCT pool_prefix)                                 AS pools_loaded
FROM loans
