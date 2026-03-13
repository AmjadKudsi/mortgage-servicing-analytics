-- ============================================================
-- 04_roll_rates.sql
-- Purpose: Month-to-month transition probabilities between
--          delinquency states, derived from payment history strings
-- Author: Amjad Ali Kudsi
-- Consumer: Tableau Page 2, report roll rate matrix
--
-- How it works:
--   Field payment_history is a 48-char string. Each character
--   represents one month: '0'=Current, '1'=30DPD, '2'=60DPD,
--   '3'=90DPD, '4'+=120+DPD, 'X'=not reported.
--   Position 1 = oldest month, position 48 = most recent.
--   We extract consecutive character pairs and count transitions.
-- ============================================================

WITH char_pairs AS (
    -- For each loan, extract each consecutive month pair from the history string
    -- positions 43-48 = most recent 6 months (most relevant for current behavior)
    -- Using positions 37-48 gives us 12 months of transition data
    SELECT
        loan_id,
        pos,
        SUBSTRING(payment_history, pos, 1) AS state_from,
        SUBSTRING(payment_history, pos + 1, 1) AS state_to
    FROM loans
    CROSS JOIN generate_series(37, 47) AS t(pos)
    WHERE payment_history IS NOT NULL
      AND LENGTH(payment_history) >= 48
      AND SUBSTRING(payment_history, pos, 1) NOT IN ('X', ' ', '')
      AND SUBSTRING(payment_history, pos + 1, 1) NOT IN ('X', ' ', '')
),
labeled AS (
    -- Map single characters to readable bucket names
    SELECT
        loan_id,
        CASE state_from
            WHEN '0' THEN 'Current'
            WHEN '1' THEN '30_DPD'
            WHEN '2' THEN '60_DPD'
            WHEN '3' THEN '90_DPD'
            ELSE '120_Plus'
        END AS from_bucket,
        CASE state_to
            WHEN '0' THEN 'Current'
            WHEN '1' THEN '30_DPD'
            WHEN '2' THEN '60_DPD'
            WHEN '3' THEN '90_DPD'
            ELSE '120_Plus'
        END AS to_bucket
    FROM char_pairs
    WHERE state_from BETWEEN '0' AND '9'
      AND state_to BETWEEN '0' AND '9'
)
SELECT
    from_bucket,
    to_bucket,
    COUNT(*) AS transitions,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY from_bucket), 2) AS transition_pct
FROM labeled
GROUP BY from_bucket, to_bucket
ORDER BY
    CASE from_bucket
        WHEN 'Current' THEN 1 WHEN '30_DPD' THEN 2 WHEN '60_DPD' THEN 3
        WHEN '90_DPD' THEN 4 ELSE 5
    END,
    CASE to_bucket
        WHEN 'Current' THEN 1 WHEN '30_DPD' THEN 2 WHEN '60_DPD' THEN 3
        WHEN '90_DPD' THEN 4 ELSE 5
    END
