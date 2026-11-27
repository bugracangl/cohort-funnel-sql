-- Power BI ve BI araçları için hazır analitik SQL görünüm (VIEW) katmanı

DROP VIEW IF EXISTS vw_funnel_steps;
DROP VIEW IF EXISTS vw_funnel_by_channel;
DROP VIEW IF EXISTS vw_cohort_retention;
DROP VIEW IF EXISTS vw_cohort_by_channel;
DROP VIEW IF EXISTS vw_channel_summary;
DROP VIEW IF EXISTS vw_user_journey;

-- 1. Genel 5 adımlı kronolojik dönüşüm hunisi
CREATE VIEW vw_funnel_steps AS
WITH step_1 AS (
    SELECT user_id, MIN(event_ts) AS ts
    FROM events
    WHERE event_name = 'signup'
    GROUP BY user_id
),
step_2 AS (
    SELECT e.user_id, MIN(e.event_ts) AS ts
    FROM events e
    JOIN step_1 prev ON e.user_id = prev.user_id
    WHERE e.event_name = 'onboarding_complete' AND e.event_ts >= prev.ts
    GROUP BY e.user_id
),
step_3 AS (
    SELECT e.user_id, MIN(e.event_ts) AS ts
    FROM events e
    JOIN step_2 prev ON e.user_id = prev.user_id
    WHERE e.event_name = 'first_project' AND e.event_ts >= prev.ts
    GROUP BY e.user_id
),
step_4 AS (
    SELECT e.user_id, MIN(e.event_ts) AS ts
    FROM events e
    JOIN step_3 prev ON e.user_id = prev.user_id
    WHERE e.event_name = 'invite_team' AND e.event_ts >= prev.ts
    GROUP BY e.user_id
),
step_5 AS (
    SELECT e.user_id, MIN(e.event_ts) AS ts
    FROM events e
    JOIN step_4 prev ON e.user_id = prev.user_id
    WHERE e.event_name = 'subscribed' AND e.event_ts >= prev.ts
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
    CASE WHEN top_users = 0 THEN 0.0 ELSE ROUND(100.0 * users / top_users, 2) END AS overall_conversion_pct,
    CASE WHEN prev_users IS NULL THEN 100.0 WHEN prev_users = 0 THEN 0.0 ELSE ROUND(100.0 * users / prev_users, 2) END AS step_conversion_pct,
    CASE WHEN prev_users IS NULL OR prev_users = 0 THEN 0.0 ELSE ROUND(100.0 * (prev_users - users) / prev_users, 2) END AS drop_off_pct
FROM funnel_metrics
ORDER BY step_order;

-- 2. Kanal dilimleyicisi (slicer) ile kullanılabilen kanal bazlı dönüşüm hunisi
CREATE VIEW vw_funnel_by_channel AS
WITH base_users AS (
    SELECT DISTINCT channel FROM users
),
step_1 AS (
    SELECT u.channel, e.user_id, MIN(e.event_ts) AS ts
    FROM events e
    JOIN users u ON e.user_id = u.user_id
    WHERE e.event_name = 'signup'
    GROUP BY u.channel, e.user_id
),
step_2 AS (
    SELECT prev.channel, e.user_id, MIN(e.event_ts) AS ts
    FROM events e
    JOIN step_1 prev ON e.user_id = prev.user_id
    WHERE e.event_name = 'onboarding_complete' AND e.event_ts >= prev.ts
    GROUP BY prev.channel, e.user_id
),
step_3 AS (
    SELECT prev.channel, e.user_id, MIN(e.event_ts) AS ts
    FROM events e
    JOIN step_2 prev ON e.user_id = prev.user_id
    WHERE e.event_name = 'first_project' AND e.event_ts >= prev.ts
    GROUP BY prev.channel, e.user_id
),
step_4 AS (
    SELECT prev.channel, e.user_id, MIN(e.event_ts) AS ts
    FROM events e
    JOIN step_3 prev ON e.user_id = prev.user_id
    WHERE e.event_name = 'invite_team' AND e.event_ts >= prev.ts
    GROUP BY prev.channel, e.user_id
),
step_5 AS (
    SELECT prev.channel, e.user_id, MIN(e.event_ts) AS ts
    FROM events e
    JOIN step_4 prev ON e.user_id = prev.user_id
    WHERE e.event_name = 'subscribed' AND e.event_ts >= prev.ts
    GROUP BY prev.channel, e.user_id
),
counts AS (
    SELECT b.channel, 1 AS step_order, 'signup' AS step_name, COUNT(s.user_id) AS users
    FROM base_users b LEFT JOIN step_1 s ON b.channel = s.channel GROUP BY b.channel
    UNION ALL
    SELECT b.channel, 2 AS step_order, 'onboarding_complete' AS step_name, COUNT(s.user_id) AS users
    FROM base_users b LEFT JOIN step_2 s ON b.channel = s.channel GROUP BY b.channel
    UNION ALL
    SELECT b.channel, 3 AS step_order, 'first_project' AS step_name, COUNT(s.user_id) AS users
    FROM base_users b LEFT JOIN step_3 s ON b.channel = s.channel GROUP BY b.channel
    UNION ALL
    SELECT b.channel, 4 AS step_order, 'invite_team' AS step_name, COUNT(s.user_id) AS users
    FROM base_users b LEFT JOIN step_4 s ON b.channel = s.channel GROUP BY b.channel
    UNION ALL
    SELECT b.channel, 5 AS step_order, 'subscribed' AS step_name, COUNT(s.user_id) AS users
    FROM base_users b LEFT JOIN step_5 s ON b.channel = s.channel GROUP BY b.channel
),
funnel_metrics AS (
    SELECT
        channel,
        step_order,
        step_name,
        users,
        FIRST_VALUE(users) OVER (PARTITION BY channel ORDER BY step_order) AS top_users,
        LAG(users) OVER (PARTITION BY channel ORDER BY step_order) AS prev_users
    FROM counts
)
SELECT
    channel,
    step_order,
    step_name,
    users,
    CASE WHEN top_users = 0 THEN 0.0 ELSE ROUND(100.0 * users / top_users, 2) END AS overall_conversion_pct,
    CASE WHEN prev_users IS NULL THEN 100.0 WHEN prev_users = 0 THEN 0.0 ELSE ROUND(100.0 * users / prev_users, 2) END AS step_conversion_pct,
    CASE WHEN prev_users IS NULL OR prev_users = 0 THEN 0.0 ELSE ROUND(100.0 * (prev_users - users) / prev_users, 2) END AS drop_off_pct
FROM funnel_metrics
ORDER BY channel, step_order;

-- 3. Genel aylık kohort tutundurma matrisi
CREATE VIEW vw_cohort_retention AS
WITH user_cohorts AS (
    SELECT user_id, signup_date, strftime('%Y-%m', signup_date) AS cohort_month
    FROM users
),
cohort_sizes AS (
    SELECT cohort_month, COUNT(DISTINCT user_id) AS cohort_size
    FROM user_cohorts
    GROUP BY cohort_month
),
user_monthly_activity AS (
    SELECT DISTINCT
        u.cohort_month,
        u.user_id,
        (CAST(strftime('%Y', e.event_ts) AS INTEGER) - CAST(strftime('%Y', u.signup_date) AS INTEGER)) * 12
        + (CAST(strftime('%m', e.event_ts) AS INTEGER) - CAST(strftime('%m', u.signup_date) AS INTEGER)) AS month_number
    FROM user_cohorts u
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

-- 4. Kanal dilimleyicisi (slicer) destekli aylık kohort tutundurma
CREATE VIEW vw_cohort_by_channel AS
WITH user_cohorts AS (
    SELECT user_id, channel, signup_date, strftime('%Y-%m', signup_date) AS cohort_month
    FROM users
),
cohort_sizes AS (
    SELECT channel, cohort_month, COUNT(DISTINCT user_id) AS cohort_size
    FROM user_cohorts
    GROUP BY channel, cohort_month
),
user_monthly_activity AS (
    SELECT DISTINCT
        u.channel,
        u.cohort_month,
        u.user_id,
        (CAST(strftime('%Y', e.event_ts) AS INTEGER) - CAST(strftime('%Y', u.signup_date) AS INTEGER)) * 12
        + (CAST(strftime('%m', e.event_ts) AS INTEGER) - CAST(strftime('%m', u.signup_date) AS INTEGER)) AS month_number
    FROM user_cohorts u
    JOIN events e ON u.user_id = e.user_id
    WHERE (
        (CAST(strftime('%Y', e.event_ts) AS INTEGER) - CAST(strftime('%Y', u.signup_date) AS INTEGER)) * 12
        + (CAST(strftime('%m', e.event_ts) AS INTEGER) - CAST(strftime('%m', u.signup_date) AS INTEGER))
    ) >= 0
)
SELECT
    a.channel,
    a.cohort_month,
    cs.cohort_size,
    a.month_number,
    COUNT(DISTINCT a.user_id) AS active_users,
    ROUND(100.0 * COUNT(DISTINCT a.user_id) / cs.cohort_size, 2) AS retention_pct
FROM user_monthly_activity a
JOIN cohort_sizes cs ON a.channel = cs.channel AND a.cohort_month = cs.cohort_month
GROUP BY a.channel, a.cohort_month, cs.cohort_size, a.month_number
ORDER BY a.channel, a.cohort_month, a.month_number;

-- 5. Edinme kanalı performans özeti
CREATE VIEW vw_channel_summary AS
WITH user_milestones AS (
    SELECT
        u.user_id,
        u.channel,
        MAX(CASE WHEN e.event_name = 'onboarding_complete' THEN 1 ELSE 0 END) AS is_onboarded,
        MAX(CASE WHEN e.event_name = 'first_project' THEN 1 ELSE 0 END) AS is_activated,
        MAX(CASE WHEN e.event_name = 'subscribed' THEN 1 ELSE 0 END) AS is_subscribed
    FROM users u
    LEFT JOIN events e ON u.user_id = e.user_id
    GROUP BY u.user_id, u.channel
)
SELECT
    channel,
    COUNT(*) AS total_users,
    SUM(is_onboarded) AS onboarded_users,
    SUM(is_activated) AS activated_users,
    SUM(is_subscribed) AS subscribed_users,
    ROUND(100.0 * SUM(is_activated) / COUNT(*), 2) AS activation_rate_pct,
    ROUND(100.0 * SUM(is_subscribed) / COUNT(*), 2) AS paid_conversion_pct
FROM user_milestones
GROUP BY channel
ORDER BY paid_conversion_pct DESC, total_users DESC;

-- 6. Power BI KPI kartları ve özel filtreler için kullanıcı düzeyinde yolculuk tablosu
CREATE VIEW vw_user_journey AS
WITH step_1 AS (
    SELECT user_id, MIN(event_ts) AS ts FROM events WHERE event_name = 'signup' GROUP BY user_id
),
step_2 AS (
    SELECT e.user_id, MIN(e.event_ts) AS ts
    FROM events e JOIN step_1 prev ON e.user_id = prev.user_id
    WHERE e.event_name = 'onboarding_complete' AND e.event_ts >= prev.ts
    GROUP BY e.user_id
),
step_3 AS (
    SELECT e.user_id, MIN(e.event_ts) AS ts
    FROM events e JOIN step_2 prev ON e.user_id = prev.user_id
    WHERE e.event_name = 'first_project' AND e.event_ts >= prev.ts
    GROUP BY e.user_id
),
step_4 AS (
    SELECT e.user_id, MIN(e.event_ts) AS ts
    FROM events e JOIN step_3 prev ON e.user_id = prev.user_id
    WHERE e.event_name = 'invite_team' AND e.event_ts >= prev.ts
    GROUP BY e.user_id
),
step_5 AS (
    SELECT e.user_id, MIN(e.event_ts) AS ts
    FROM events e JOIN step_4 prev ON e.user_id = prev.user_id
    WHERE e.event_name = 'subscribed' AND e.event_ts >= prev.ts
    GROUP BY e.user_id
)
SELECT
    u.user_id,
    u.signup_date,
    strftime('%Y-%m', u.signup_date) AS cohort_month,
    u.channel,
    u.plan_tier,
    CASE WHEN s1.user_id IS NOT NULL THEN 1 ELSE 0 END AS reached_signup,
    CASE WHEN s2.user_id IS NOT NULL THEN 1 ELSE 0 END AS reached_onboarding,
    CASE WHEN s3.user_id IS NOT NULL THEN 1 ELSE 0 END AS reached_first_project,
    CASE WHEN s4.user_id IS NOT NULL THEN 1 ELSE 0 END AS reached_invite_team,
    CASE WHEN s5.user_id IS NOT NULL THEN 1 ELSE 0 END AS reached_subscribed
FROM users u
LEFT JOIN step_1 s1 ON u.user_id = s1.user_id
LEFT JOIN step_2 s2 ON u.user_id = s2.user_id
LEFT JOIN step_3 s3 ON u.user_id = s3.user_id
LEFT JOIN step_4 s4 ON u.user_id = s4.user_id
LEFT JOIN step_5 s5 ON u.user_id = s5.user_id;
