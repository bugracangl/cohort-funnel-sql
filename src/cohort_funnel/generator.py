"""Tekrarlanabilir sentetik SaaS ürün olayı (event) veri üreticisi."""

from __future__ import annotations

import calendar
import csv
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

CHANNELS: dict[str, dict[str, float]] = {
    "organic": {"weight": 0.35, "onboard": 0.78, "project": 0.68, "invite": 0.45, "subscribe": 0.42, "ret_boost": 1.05},
    "referral": {"weight": 0.20, "onboard": 0.86, "project": 0.76, "invite": 0.58, "subscribe": 0.52, "ret_boost": 1.20},
    "paid_search": {"weight": 0.28, "onboard": 0.70, "project": 0.58, "invite": 0.38, "subscribe": 0.34, "ret_boost": 0.90},
    "social": {"weight": 0.17, "onboard": 0.62, "project": 0.48, "invite": 0.30, "subscribe": 0.26, "ret_boost": 0.80},
}

# Ay farkına göre temel tutundurma (retention) olasılıkları (1. Ay .. N. Ay)
BASE_MONTHLY_RETENTION = {
    1: 0.46,
    2: 0.34,
    3: 0.27,
    4: 0.23,
    5: 0.20,
    6: 0.18,
}


def _add_months(year: int, month: int, offset: int) -> tuple[int, int]:
    total = (year * 12 + (month - 1)) + offset
    return total // 12, (total % 12) + 1


def _days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def generate_dataset(
    num_users: int = 1500,
    start_year: int = 2026,
    start_month: int = 1,
    months: int = 6,
    seed: int = 42,
) -> tuple[list[tuple[str, str, str, str]], list[tuple[str, str, str]]]:
    """Gerçekçi kullanıcılar ile kronolojik sıralı funnel ve tutundurma olayları üretir."""
    rng = random.Random(seed)
    channel_names = list(CHANNELS.keys())
    channel_weights = [CHANNELS[c]["weight"] for c in channel_names]

    end_year, end_month = _add_months(start_year, start_month, months - 1)
    window_end = datetime(end_year, end_month, _days_in_month(end_year, end_month), 23, 59, 59)

    users: list[tuple[str, str, str, str]] = []
    events: list[tuple[str, str, str]] = []

    for idx in range(1, num_users + 1):
        user_id = f"usr_{idx:05d}"
        month_offset = rng.randrange(months)
        y, m = _add_months(start_year, start_month, month_offset)
        day = rng.randint(1, _days_in_month(y, m))
        signup_dt = datetime(y, m, day, rng.randint(6, 22), rng.randint(0, 59), rng.randint(0, 59))
        signup_date_str = signup_dt.strftime("%Y-%m-%d")

        channel = rng.choices(channel_names, weights=channel_weights, k=1)[0]
        profile = CHANNELS[channel]
        plan_tier = "free"

        events.append((user_id, "signup", signup_dt.strftime("%Y-%m-%dT%H:%M:%S")))
        last_ts = signup_dt

        # Sıralı dönüşüm hunisi (funnel) adımları
        funnel_steps = [
            ("onboarding_complete", profile["onboard"], timedelta(minutes=rng.randint(5, 180))),
            ("first_project", profile["project"], timedelta(hours=rng.randint(1, 72))),
            ("invite_team", profile["invite"], timedelta(days=rng.randint(1, 7), hours=rng.randint(0, 12))),
            ("subscribed", profile["subscribe"], timedelta(days=rng.randint(1, 14), hours=rng.randint(0, 12))),
        ]

        is_subscribed = False
        for step_name, prob, delta in funnel_steps:
            if rng.random() > prob:
                break
            candidate_ts = last_ts + delta
            if candidate_ts > window_end:
                break
            events.append((user_id, step_name, candidate_ts.strftime("%Y-%m-%dT%H:%M:%S")))
            last_ts = candidate_ts
            if step_name == "subscribed":
                is_subscribed = True
                plan_tier = rng.choice(["pro", "team"])

        users.append((user_id, signup_date_str, channel, plan_tier))

        # Analiz penceresi içindeki takip eden aylarda tutundurma oturumları üret
        remaining_months = (end_year - y) * 12 + (end_month - m)
        sub_boost = 1.65 if is_subscribed else 1.0
        for m_off in range(1, remaining_months + 1):
            base_prob = BASE_MONTHLY_RETENTION.get(m_off, max(0.10, 0.18 - 0.015 * (m_off - 6)))
            ret_prob = min(0.92, base_prob * profile["ret_boost"] * sub_boost)
            if rng.random() <= ret_prob:
                ay, am = _add_months(y, m, m_off)
                sessions = rng.randint(1, 3)
                for _ in range(sessions):
                    aday = rng.randint(1, _days_in_month(ay, am))
                    ats = datetime(ay, am, aday, rng.randint(8, 22), rng.randint(0, 59), rng.randint(0, 59))
                    if ats <= window_end:
                        events.append((user_id, "active_session", ats.strftime("%Y-%m-%dT%H:%M:%S")))

    return users, events


def populate_database(
    conn: sqlite3.Connection,
    num_users: int = 1500,
    start_year: int = 2026,
    start_month: int = 1,
    months: int = 6,
    seed: int = 42,
) -> tuple[int, int]:
    """Sentetik veri setini üretip SQLite veritabanına ekler."""
    users, events = generate_dataset(
        num_users=num_users,
        start_year=start_year,
        start_month=start_month,
        months=months,
        seed=seed,
    )
    with conn:
        conn.executemany(
            "INSERT INTO users (user_id, signup_date, channel, plan_tier) VALUES (?, ?, ?, ?);",
            users,
        )
        conn.executemany(
            "INSERT INTO events (user_id, event_name, event_ts) VALUES (?, ?, ?);",
            events,
        )
    return len(users), len(events)


def export_csv(
    users: list[tuple[str, str, str, str]],
    events: list[tuple[str, str, str]],
    output_dir: str | Path,
) -> tuple[Path, Path]:
    """Üretilen kullanıcı ve olay verilerini CSV dosyalarına yazar."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    users_path = out / "users.csv"
    events_path = out / "events.csv"

    with users_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["user_id", "signup_date", "channel", "plan_tier"])
        writer.writerows(users)

    with events_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["user_id", "event_name", "event_ts"])
        writer.writerows(events)

    return users_path, events_path
