-- SaaS / ürün olay (event) analitiği için ilişkisel veritabanı şeması

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    user_id     TEXT PRIMARY KEY,
    signup_date TEXT NOT NULL,          -- ISO-8601 tarih formatı: YYYY-AA-GG
    channel     TEXT NOT NULL,          -- organic | paid_search | referral | social
    plan_tier   TEXT NOT NULL DEFAULT 'free'
);

CREATE TABLE IF NOT EXISTS events (
    event_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT NOT NULL,
    event_name  TEXT NOT NULL,          -- signup | onboarding_complete | first_project | invite_team | subscribed | active_session
    event_ts    TEXT NOT NULL,          -- ISO-8601 zaman damgası: YYYY-AA-GGTHH:MM:SS
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_users_signup_date ON users(signup_date);
CREATE INDEX IF NOT EXISTS idx_users_channel     ON users(channel);
CREATE INDEX IF NOT EXISTS idx_events_user_ts    ON events(user_id, event_ts);
CREATE INDEX IF NOT EXISTS idx_events_name_user  ON events(event_name, user_id);
