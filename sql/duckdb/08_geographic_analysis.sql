-- ============================================================
-- 08_geographic_analysis.sql
-- Purpose: State-level portfolio metrics for choropleth map
--          and geographic risk assessment
-- Consumer: Dashboard map, Tableau Page 1, report hotspots
-- ============================================================

SELECT
    property_state,
    COUNT(*)                                                    AS loans,
    ROUND(SUM(current_upb) / 1e9, 3)                           AS upb_billions,
    ROUND(100.0 * SUM(is_delinquent) / COUNT(*), 2)           AS dlq_rate_pct,
    ROUND(100.0 * SUM(is_seriously_delinquent) / COUNT(*), 2) AS serious_dlq_pct,
    ROUND(AVG(credit_score), 0)                                AS avg_fico,
    ROUND(AVG(orig_interest_rate), 3)                          AS avg_rate,
    ROUND(AVG(ltv), 1)                                         AS avg_ltv,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2)         AS pct_of_portfolio,
    ROUND(100.0 * SUM(current_upb) / SUM(SUM(current_upb)) OVER(), 2) AS pct_of_upb
FROM loans
WHERE property_state IS NOT NULL
GROUP BY property_state
ORDER BY dlq_rate_pct DESC
