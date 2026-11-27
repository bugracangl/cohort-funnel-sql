-- Zincirlenmiş CTE'ler ile kronolojik sıralı 5 adımlı dönüşüm hunisi (funnel).
-- İsteğe bağlı parametreler: :start_date, :end_date, :channel

WITH filtered_users AS (
    SELECT user_id
    FROM users
    WHERE (:start_date IS NULL OR signup_date >= :start_date)
      AND (:end_date IS NULL OR signup_date <= :end_date)
      AND (:channel IS NULL OR channel = :channel)
),
step_1 AS (
    SELECT e.user_id, MIN(e.event_ts) AS ts
    FROM events e
    JOIN filtered_users u ON e.user_id = u.user_id
    WHERE e.event_name = 'signup'
    GROUP BY e.user_id
),
step_2 AS (
    SELECT e.user_id, MIN(e.event_ts) AS ts
    FROM events e
    JOIN step_1 prev ON e.user_id = prev.user_id
    WHERE e.event_name = 'onboarding_complete'
      AND e.event_ts >= prev.ts
    GROUP BY e.user_id
),
step_3 AS (
    SELECT e.user_id, MIN(e.event_ts) AS ts
    FROM events e
    JOIN step_2 prev ON e.user_id = prev.user_id
    WHERE e.event_name = 'first_project'
      AND e.event_ts >= prev.ts
    GROUP BY e.user_id
),
step_4 AS (
    SELECT e.user_id, MIN(e.event_ts) AS ts
    FROM events e
    JOIN step_3 prev ON e.user_id = prev.user_id
    WHERE e.event_name = 'invite_team'
      AND e.event_ts >= prev.ts
    GROUP BY e.user_id
),
step_5 AS (
    SELECT e.user_id, MIN(e.event_ts) AS ts
    FROM events e
    JOIN step_4 prev ON e.user_id = prev.user_id
    WHERE e.event_name = 'subscribed'
      AND e.event_ts >= prev.ts
    GROUP BY e.user_id
),
counts AS (
    SELECT 1 AS step_order, 'signup'              AS step_name, COUNT(*) AS users FROM step_1
    UNION ALL
    SELECT 2 AS step_order, 'onboarding_complete' AS step_name, COUNT(*) AS users FROM step_2
    UNION ALL
    SELECT 3 AS step_order, 'first_project'       AS step_name, COUNT(*) AS users FROM step_3
    UNION ALL
    SELECT 4 AS step_order, 'invite_team'         AS step_name, COUNT(*) AS users FROM step_4
    UNION ALL
    SELECT 5 AS step_order, 'subscribed'          AS step_name, COUNT(*) AS users FROM step_5
),
funnel_metrics AS (
    SELECT
        step_order,
        step_name,
        users,
        FIRST_VALUE(users) OVER (ORDER BY step_order) AS top_users,
        LAG(users) OVER (ORDER BY step_order) AS prev_users
    FROM counts
)
SELECT
    step_order,
    step_name,
    users,
    CASE
        WHEN top_users = 0 THEN 0.0
        ELSE ROUND(100.0 * users / top_users, 2)
    END AS overall_conversion_pct,
    CASE
        WHEN prev_users IS NULL THEN 100.0
        WHEN prev_users = 0 THEN 0.0
        ELSE ROUND(100.0 * users / prev_users, 2)
    END AS step_conversion_pct,
    CASE
        WHEN prev_users IS NULL OR prev_users = 0 THEN 0.0
        ELSE ROUND(100.0 * (prev_users - users) / prev_users, 2)
    END AS drop_off_pct
FROM funnel_metrics
ORDER BY step_order;
