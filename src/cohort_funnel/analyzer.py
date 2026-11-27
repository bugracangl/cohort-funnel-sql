"""SQLite SQL sorguları üzerinde çalışan analitik orkestrasyon katmanı."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .db import query_file


@dataclass
class FunnelStep:
    step_order: int
    step_name: str
    users: int
    overall_conversion_pct: float
    step_conversion_pct: float
    drop_off_pct: float


@dataclass
class CohortRow:
    cohort_month: str
    cohort_size: int
    retention: dict[int, float] = field(default_factory=dict)
    active_counts: dict[int, int] = field(default_factory=dict)


@dataclass
class CohortMatrix:
    rows: list[CohortRow]
    max_month: int


@dataclass
class ChannelMetric:
    channel: str
    total_users: int
    onboarded_users: int
    activated_users: int
    subscribed_users: int
    activation_rate_pct: float
    paid_conversion_pct: float


@dataclass
class AnalysisResult:
    funnel: list[FunnelStep]
    cohorts: CohortMatrix
    channels: list[ChannelMetric]
    filters: dict[str, str | None]


def run_funnel(
    conn: sqlite3.Connection,
    start_date: str | None = None,
    end_date: str | None = None,
    channel: str | None = None,
    sql_dir: Path | None = None,
) -> list[FunnelStep]:
    """Sıralı dönüşüm hunisi (funnel) SQL sorgusunu çalıştırır ve adımları döner."""
    rows = query_file(
        conn,
        "funnel.sql",
        params={"start_date": start_date, "end_date": end_date, "channel": channel},
        sql_dir=sql_dir,
    )
    return [
        FunnelStep(
            step_order=int(r["step_order"]),
            step_name=str(r["step_name"]),
            users=int(r["users"]),
            overall_conversion_pct=float(r["overall_conversion_pct"]),
            step_conversion_pct=float(r["step_conversion_pct"]),
            drop_off_pct=float(r["drop_off_pct"]),
        )
        for r in rows
    ]


def run_cohort_retention(
    conn: sqlite3.Connection,
    start_date: str | None = None,
    end_date: str | None = None,
    channel: str | None = None,
    sql_dir: Path | None = None,
) -> CohortMatrix:
    """Aylık kohort tutundurma SQL sorgusunu çalıştırır ve matris yapısına dönüştürür."""
    rows = query_file(
        conn,
        "cohort.sql",
        params={"start_date": start_date, "end_date": end_date, "channel": channel},
        sql_dir=sql_dir,
    )
    grouped: dict[str, CohortRow] = {}
    max_month = 0

    for r in rows:
        cm = str(r["cohort_month"])
        m_num = int(r["month_number"])
        max_month = max(max_month, m_num)
        if cm not in grouped:
            grouped[cm] = CohortRow(cohort_month=cm, cohort_size=int(r["cohort_size"]))
        grouped[cm].retention[m_num] = float(r["retention_pct"])
        grouped[cm].active_counts[m_num] = int(r["active_users"])

    ordered_rows = [grouped[k] for k in sorted(grouped.keys())]
    return CohortMatrix(rows=ordered_rows, max_month=max_month)


def run_channel_summary(
    conn: sqlite3.Connection,
    start_date: str | None = None,
    end_date: str | None = None,
    sql_dir: Path | None = None,
) -> list[ChannelMetric]:
    """Edinme kanalı dönüşüm kırılımı SQL sorgusunu çalıştırır."""
    rows = query_file(
        conn,
        "channel_summary.sql",
        params={"start_date": start_date, "end_date": end_date},
        sql_dir=sql_dir,
    )
    return [
        ChannelMetric(
            channel=str(r["channel"]),
            total_users=int(r["total_users"]),
            onboarded_users=int(r["onboarded_users"]),
            activated_users=int(r["activated_users"]),
            subscribed_users=int(r["subscribed_users"]),
            activation_rate_pct=float(r["activation_rate_pct"]),
            paid_conversion_pct=float(r["paid_conversion_pct"]),
        )
        for r in rows
    ]


def analyze_all(
    conn: sqlite3.Connection,
    start_date: str | None = None,
    end_date: str | None = None,
    channel: str | None = None,
    sql_dir: Path | None = None,
) -> AnalysisResult:
    """Dönüşüm hunisi, kohort tutundurma ve kanal özeti analizlerinin tümünü çalıştırır."""
    return AnalysisResult(
        funnel=run_funnel(conn, start_date=start_date, end_date=end_date, channel=channel, sql_dir=sql_dir),
        cohorts=run_cohort_retention(conn, start_date=start_date, end_date=end_date, channel=channel, sql_dir=sql_dir),
        channels=run_channel_summary(conn, start_date=start_date, end_date=end_date, sql_dir=sql_dir),
        filters={"start_date": start_date, "end_date": end_date, "channel": channel},
    )


def result_to_dict(result: AnalysisResult) -> dict[str, Any]:
    """AnalysisResult nesnesini JSON serileştirmeye uygun sözlüğe çevirir."""
    return {
        "filters": result.filters,
        "funnel": [vars(step) for step in result.funnel],
        "cohorts": {
            "max_month": result.cohorts.max_month,
            "rows": [
                {
                    "cohort_month": row.cohort_month,
                    "cohort_size": row.cohort_size,
                    "retention_pct": {str(k): v for k, v in row.retention.items()},
                    "active_users": {str(k): v for k, v in row.active_counts.items()},
                }
                for row in result.cohorts.rows
            ],
        },
        "channels": [vars(ch) for ch in result.channels],
    }
