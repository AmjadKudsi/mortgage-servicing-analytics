-- ============================================================
-- 01_data_quality.sql
-- Purpose: Automated data quality assessment
-- Consumer: DQ report generator, pipeline validation
-- ============================================================

-- Section A: Null rates per key column
SELECT
    'loan_id' AS column_name, ROUND(100.0 * SUM(CASE WHEN loan_id IS NULL THEN 1 ELSE 0 END) / COUNT(*), 3) AS null_pct,
    COUNT(*) AS total_rows
FROM loans
UNION ALL SELECT 'credit_score', ROUND(100.0 * SUM(CASE WHEN credit_score IS NULL THEN 1 ELSE 0 END) / COUNT(*), 3), COUNT(*) FROM loans
UNION ALL SELECT 'ltv', ROUND(100.0 * SUM(CASE WHEN ltv IS NULL THEN 1 ELSE 0 END) / COUNT(*), 3), COUNT(*) FROM loans
UNION ALL SELECT 'dti', ROUND(100.0 * SUM(CASE WHEN dti IS NULL THEN 1 ELSE 0 END) / COUNT(*), 3), COUNT(*) FROM loans
UNION ALL SELECT 'current_upb', ROUND(100.0 * SUM(CASE WHEN current_upb IS NULL OR current_upb = 0 THEN 1 ELSE 0 END) / COUNT(*), 3), COUNT(*) FROM loans
UNION ALL SELECT 'delinquency_status', ROUND(100.0 * SUM(CASE WHEN delinquency_status IS NULL THEN 1 ELSE 0 END) / COUNT(*), 3), COUNT(*) FROM loans
UNION ALL SELECT 'property_state', ROUND(100.0 * SUM(CASE WHEN property_state IS NULL THEN 1 ELSE 0 END) / COUNT(*), 3), COUNT(*) FROM loans
UNION ALL SELECT 'orig_interest_rate', ROUND(100.0 * SUM(CASE WHEN orig_interest_rate IS NULL THEN 1 ELSE 0 END) / COUNT(*), 3), COUNT(*) FROM loans
UNION ALL SELECT 'payment_history', ROUND(100.0 * SUM(CASE WHEN payment_history IS NULL THEN 1 ELSE 0 END) / COUNT(*), 3), COUNT(*) FROM loans
UNION ALL SELECT 'current_credit_score', ROUND(100.0 * SUM(CASE WHEN current_credit_score IS NULL THEN 1 ELSE 0 END) / COUNT(*), 3), COUNT(*) FROM loans
ORDER BY null_pct DESC
