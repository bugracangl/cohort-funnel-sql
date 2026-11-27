"""SQLite veritabanı yardımcıları ve SQL dosya okuyucu."""

from __future__ import annotations

import csv
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

# sql/ klasörünü proje köküne göre konumlandır (src/cohort_funnel/db.py dosyasından iki üst dizin)
DEFAULT_SQL_DIR = Path(__file__).resolve().parents[2] / "sql"


def get_connection(db_path: str | Path) -> sqlite3.Connection:
    """Yabancı anahtarlar (foreign keys) etkin ve sözlük benzeri satırlarla SQLite bağlantısı açar."""
    if str(db_path) != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def open_connection(db_path: str | Path) -> Iterator[sqlite3.Connection]:
    """SQLite bağlantısını açan ve işlem sonunda güvenle kapatan bağlam yöneticisi."""
    conn = get_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()


def read_sql(filename: str, sql_dir: Path | None = None) -> str:
    """sql/ klasöründen bir SQL dosyasını okur."""
    base_dir = sql_dir or DEFAULT_SQL_DIR
    path = base_dir / filename
    if not path.is_file():
        raise FileNotFoundError(f"SQL dosyası bulunamadı: {path}")
    return path.read_text(encoding="utf-8")


def init_db(conn: sqlite3.Connection, reset: bool = False, sql_dir: Path | None = None) -> None:
    """sql/schema.sql ve sql/powerbi_views.sql dosyalarını çalıştırarak şemayı ve görünümleri kurar."""
    if reset:
        conn.executescript(
            """
            PRAGMA foreign_keys = OFF;
            DROP VIEW IF EXISTS vw_funnel_steps;
            DROP VIEW IF EXISTS vw_funnel_by_channel;
            DROP VIEW IF EXISTS vw_cohort_retention;
            DROP VIEW IF EXISTS vw_cohort_by_channel;
            DROP VIEW IF EXISTS vw_channel_summary;
            DROP VIEW IF EXISTS vw_user_journey;
            DROP TABLE IF EXISTS events;
            DROP TABLE IF EXISTS users;
            PRAGMA foreign_keys = ON;
            """
        )
    schema_sql = read_sql("schema.sql", sql_dir=sql_dir)
    conn.executescript(schema_sql)
    views_sql = read_sql("powerbi_views.sql", sql_dir=sql_dir)
    conn.executescript(views_sql)
    conn.commit()


def ensure_views(conn: sqlite3.Connection, sql_dir: Path | None = None) -> None:
    """Mevcut veritabanında Power BI SQL görünümlerinin güncel olduğundan emin olur."""
    views_sql = read_sql("powerbi_views.sql", sql_dir=sql_dir)
    conn.executescript(views_sql)
    conn.commit()


def query_file(
    conn: sqlite3.Connection,
    filename: str,
    params: dict[str, Any] | None = None,
    sql_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Bir .sql dosyasındaki SELECT sorgusunu çalıştırır ve sonuçları sözlük listesi olarak döner."""
    sql = read_sql(filename, sql_dir=sql_dir)
    cursor = conn.execute(sql, params or {})
    return [dict(row) for row in cursor.fetchall()]


def load_csv_data(
    conn: sqlite3.Connection,
    users_csv: str | Path,
    events_csv: str | Path,
) -> tuple[int, int]:
    """users ve events CSV dosyalarını tek bir transaction içinde SQLite'a yükler."""
    users_path = Path(users_csv)
    events_path = Path(events_csv)
    if not users_path.is_file():
        raise FileNotFoundError(f"Kullanıcı CSV dosyası bulunamadı: {users_path}")
    if not events_path.is_file():
        raise FileNotFoundError(f"Olay (events) CSV dosyası bulunamadı: {events_path}")

    with users_path.open("r", encoding="utf-8", newline="") as f:
        user_rows = [
            (
                row["user_id"],
                row["signup_date"],
                row["channel"],
                row.get("plan_tier") or "free",
            )
            for row in csv.DictReader(f)
        ]

    with events_path.open("r", encoding="utf-8", newline="") as f:
        event_rows = [
            (
                row["user_id"],
                row["event_name"],
                row["event_ts"],
            )
            for row in csv.DictReader(f)
        ]

    with conn:
        conn.executemany(
            "INSERT OR REPLACE INTO users (user_id, signup_date, channel, plan_tier) VALUES (?, ?, ?, ?);",
            user_rows,
        )
        conn.executemany(
            "INSERT INTO events (user_id, event_name, event_ts) VALUES (?, ?, ?);",
            event_rows,
        )

    return len(user_rows), len(event_rows)
