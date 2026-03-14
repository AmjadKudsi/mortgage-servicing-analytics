-- ============================================================
-- feature_engineering.sql
-- Purpose: Build the ML-ready feature matrix from the loans table.
--          Produces features for both Model A (behavioral) and
--          Model B (origination-only). Python selects which to use.
-- ============================================================

SELECT
    loan_id,

    -- ── Origination features (Model B uses only these) ──
    credit_score,
    ltv,
    dti,
    orig_interest_rate,
    loan_age,
    orig_loan_amount,
    num_borrowers,
    CAST(orig_year AS INTEGER) AS orig_year,
    credit_score_band,
    ltv_bucket,
    rate_bucket,
    COALESCE(channel, 'Unknown') AS channel,
    COALESCE(property_type, 'Unknown') AS property_type,
    COALESCE(occupancy_status, 'Unknown') AS occupancy_status,
    COALESCE(loan_purpose, 'Unknown') AS loan_purpose,
    CASE WHEN first_time_homebuyer = 'Y' THEN 1 ELSE 0 END AS is_first_time_buyer,

    -- ── Behavioral features (Model A adds these) ──

    -- Delinquent month count in last 12 months
    (
        LENGTH(REPLACE(SUBSTRING(payment_history, 37, 12), '0', ''))
        - LENGTH(REPLACE(REPLACE(SUBSTRING(payment_history, 37, 12), '0', ''), 'X', ''))
    ) AS dlq_count_12m,

    -- Worst DPD in last 12 months
    CASE
        WHEN SUBSTRING(payment_history, 37, 12) LIKE '%9%' THEN 9
        WHEN SUBSTRING(payment_history, 37, 12) LIKE '%8%' THEN 8
        WHEN SUBSTRING(payment_history, 37, 12) LIKE '%7%' THEN 7
        WHEN SUBSTRING(payment_history, 37, 12) LIKE '%6%' THEN 6
        WHEN SUBSTRING(payment_history, 37, 12) LIKE '%5%' THEN 5
        WHEN SUBSTRING(payment_history, 37, 12) LIKE '%4%' THEN 4
        WHEN SUBSTRING(payment_history, 37, 12) LIKE '%3%' THEN 3
        WHEN SUBSTRING(payment_history, 37, 12) LIKE '%2%' THEN 2
        WHEN SUBSTRING(payment_history, 37, 12) LIKE '%1%' THEN 1
        ELSE 0
    END AS max_dpd_12m,

    -- Consecutive months current (from most recent backward)
    CASE
        WHEN SUBSTRING(payment_history, 48, 1) != '0' THEN 0
        WHEN SUBSTRING(payment_history, 47, 1) != '0' THEN 1
        WHEN SUBSTRING(payment_history, 46, 1) != '0' THEN 2
        WHEN SUBSTRING(payment_history, 45, 1) != '0' THEN 3
        WHEN SUBSTRING(payment_history, 44, 1) != '0' THEN 4
        WHEN SUBSTRING(payment_history, 43, 1) != '0' THEN 5
        WHEN SUBSTRING(payment_history, 42, 1) != '0' THEN 6
        WHEN SUBSTRING(payment_history, 41, 1) != '0' THEN 7
        WHEN SUBSTRING(payment_history, 40, 1) != '0' THEN 8
        WHEN SUBSTRING(payment_history, 39, 1) != '0' THEN 9
        WHEN SUBSTRING(payment_history, 38, 1) != '0' THEN 10
        WHEN SUBSTRING(payment_history, 37, 1) != '0' THEN 11
        ELSE 12
    END AS consecutive_current,

    -- Trend: recent 6 months vs prior 6 months (positive = worsening)
    (
        LENGTH(REPLACE(SUBSTRING(payment_history, 43, 6), '0', ''))
        - LENGTH(REPLACE(REPLACE(SUBSTRING(payment_history, 43, 6), '0', ''), 'X', ''))
    ) - (
        LENGTH(REPLACE(SUBSTRING(payment_history, 37, 6), '0', ''))
        - LENGTH(REPLACE(REPLACE(SUBSTRING(payment_history, 37, 6), '0', ''), 'X', ''))
    ) AS dlq_trend_6m,

    current_upb,
    COALESCE(current_credit_score, credit_score) AS latest_credit_score,

    -- ── Target ──
    is_delinquent,
    is_seriously_delinquent,
    dpd_bucket

FROM loans
WHERE loan_id IS NOT NULL
  AND credit_score IS NOT NULL
  AND ltv IS NOT NULL
  AND loan_age IS NOT NULL
  AND payment_history IS NOT NULL
  AND LENGTH(payment_history) >= 48
