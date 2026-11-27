-- Edinme kanalı bazlı dönüşüm kırılımı.
-- İsteğe bağlı parametreler: :start_date, :end_date

WITH filtered_users AS (
    SELECT user_id, channel
    FROM users
    WHERE (:start_date IS NULL OR signup_date >= :start_date)
      AND (:end_date IS NULL OR signup_date <= :end_date)
),
user_milestones AS (
    SELECT
        u.user_id,
        u.channel,
        MAX(CASE WHEN e.event_name = 'onboarding_complete' THEN 1 ELSE 0 END) AS is_onboarded,
        MAX(CASE WHEN e.event_name = 'first_project' THEN 1 ELSE 0 END) AS is_activated,
        MAX(CASE WHEN e.event_name = 'subscribed' THEN 1 ELSE 0 END) AS is_subscribed
    FROM filtered_users u
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
