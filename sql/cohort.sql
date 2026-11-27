-- Aylık kohort tutundurma (retention) matrisi.
-- İsteğe bağlı parametreler: :start_date, :end_date, :channel

WITH filtered_users AS (
    SELECT
        user_id,
        signup_date,
        strftime('%Y-%m', signup_date) AS cohort_month
    FROM users
    WHERE (:start_date IS NULL OR signup_date >= :start_date)
      AND (:end_date IS NULL OR signup_date <= :end_date)
      AND (:channel IS NULL OR channel = :channel)
),
cohort_sizes AS (
    SELECT
        cohort_month,
        COUNT(DISTINCT user_id) AS cohort_size
    FROM filtered_users
    GROUP BY cohort_month
),
user_monthly_activity AS (
    SELECT DISTINCT
        u.cohort_month,
        u.user_id,
        (CAST(strftime('%Y', e.event_ts) AS INTEGER) - CAST(strftime('%Y', u.signup_date) AS INTEGER)) * 12
        + (CAST(strftime('%m', e.event_ts) AS INTEGER) - CAST(strftime('%m', u.signup_date) AS INTEGER)) AS month_number
    FROM filtered_users u
    JOIN events e ON u.user_id = e.user_id
    WHERE (
        (CAST(strftime('%Y', e.event_ts) AS INTEGER) - CAST(strftime('%Y', u.signup_date) AS INTEGER)) * 12
        + (CAST(strftime('%m', e.event_ts) AS INTEGER) - CAST(strftime('%m', u.signup_date) AS INTEGER))
    ) >= 0
)
SELECT
    a.cohort_month,
    cs.cohort_size,
    a.month_number,
    COUNT(DISTINCT a.user_id) AS active_users,
    ROUND(100.0 * COUNT(DISTINCT a.user_id) / cs.cohort_size, 2) AS retention_pct
FROM user_monthly_activity a
JOIN cohort_sizes cs ON a.cohort_month = cs.cohort_month
GROUP BY a.cohort_month, cs.cohort_size, a.month_number
ORDER BY a.cohort_month, a.month_number;
