"""Power BI Desktop için SQL VIEW tablolarını Türkçe CSV dosyalarına aktarır."""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Callable

from .db import ensure_views

STEP_NAMES_TR: dict[str, str] = {
    "signup": "Kayıt",
    "onboarding_complete": "Kurulum",
    "first_project": "İlk Proje",
    "invite_team": "Ekip Daveti",
    "subscribed": "Abonelik",
}

CHANNEL_NAMES_TR: dict[str, str] = {
    "referral": "Referans",
    "organic": "Organik",
    "paid_search": "Ücretli Arama",
    "social": "Sosyal Medya",
}

PLAN_NAMES_TR: dict[str, str] = {
    "free": "Ücretsiz",
    "pro": "Pro",
    "team": "Ekip",
}

# (sql_view_adi, cikti_csv_adi, {sql_sutunu: (turkce_baslik, donusturucu_veya_None)})
BI_EXPORT_SPECS: list[tuple[str, str, list[tuple[str, str, Callable[[object], object] | None]]]] = [
    (
        "vw_funnel_steps",
        "bi_huni_genel.csv",
        [
            ("step_order", "adim_sirasi", None),
            ("step_name", "adim_adi", lambda v: STEP_NAMES_TR.get(str(v), v)),
            ("users", "kullanici_sayisi", None),
            ("overall_conversion_pct", "genel_donusum_yuzdesi", None),
            ("step_conversion_pct", "adim_donusum_yuzdesi", None),
            ("drop_off_pct", "kayip_yuzdesi", None),
        ],
    ),
    (
        "vw_funnel_by_channel",
        "bi_huni_kanal.csv",
        [
            ("channel", "kanal", lambda v: CHANNEL_NAMES_TR.get(str(v), v)),
            ("step_order", "adim_sirasi", None),
            ("step_name", "adim_adi", lambda v: STEP_NAMES_TR.get(str(v), v)),
            ("users", "kullanici_sayisi", None),
            ("overall_conversion_pct", "genel_donusum_yuzdesi", None),
            ("step_conversion_pct", "adim_donusum_yuzdesi", None),
            ("drop_off_pct", "kayip_yuzdesi", None),
        ],
    ),
    (
        "vw_cohort_retention",
        "bi_kohort_genel.csv",
        [
            ("cohort_month", "kohort_ayi", None),
            ("cohort_size", "kohort_boyutu", None),
            ("month_number", "ay_no", None),
            ("active_users", "aktif_kullanici", None),
            ("retention_pct", "tutundurma_yuzdesi", None),
        ],
    ),
    (
        "vw_cohort_by_channel",
        "bi_kohort_kanal.csv",
        [
            ("channel", "kanal", lambda v: CHANNEL_NAMES_TR.get(str(v), v)),
            ("cohort_month", "kohort_ayi", None),
            ("cohort_size", "kohort_boyutu", None),
            ("month_number", "ay_no", None),
            ("active_users", "aktif_kullanici", None),
            ("retention_pct", "tutundurma_yuzdesi", None),
        ],
    ),
    (
        "vw_channel_summary",
        "bi_kanal_ozeti.csv",
        [
            ("channel", "kanal", lambda v: CHANNEL_NAMES_TR.get(str(v), v)),
            ("total_users", "toplam_kullanici", None),
            ("onboarded_users", "kurulum_yapan", None),
            ("activated_users", "aktiflesen", None),
            ("subscribed_users", "abone_olan", None),
            ("activation_rate_pct", "aktivasyon_orani_yuzde", None),
            ("paid_conversion_pct", "ucretli_donusum_yuzde", None),
        ],
    ),
    (
        "vw_user_journey",
        "bi_kullanici_yolculugu.csv",
        [
            ("user_id", "kullanici_id", None),
            ("signup_date", "kayit_tarihi", None),
            ("cohort_month", "kohort_ayi", None),
            ("channel", "kanal", lambda v: CHANNEL_NAMES_TR.get(str(v), v)),
            ("plan_tier", "plan_paketi", lambda v: PLAN_NAMES_TR.get(str(v), v)),
            ("reached_signup", "kayit_tamam", None),
            ("reached_onboarding", "kurulum_tamam", None),
            ("reached_first_project", "ilk_proje_tamam", None),
            ("reached_invite_team", "ekip_daveti_tamam", None),
            ("reached_subscribed", "abonelik_tamam", None),
        ],
    ),
]

# Yüzde sütunlarının Türkçe başlık adları — bu sütunlar ondalık virgülle yazılır (75,07)
# Türkçe Windows Power BI virgülü ondalık ayraç olarak doğrudan okur → ekstra ayar gerekmez
YUZDE_SUTUNLARI: set[str] = {
    "tutundurma_yuzdesi",
    "genel_donusum_yuzdesi",
    "adim_donusum_yuzdesi",
    "kayip_yuzdesi",
    "aktivasyon_orani_yuzde",
    "ucretli_donusum_yuzde",
}

BI_EXPORTS: list[tuple[str, str]] = [(view, fname) for view, fname, _ in BI_EXPORT_SPECS]


def _format_deger(val: object, tr_sutun_adi: str) -> object:
    """Yüzde sütunlarını Türkçe ondalık virgülle formatlar (75.07 → '75,07')."""
    if tr_sutun_adi in YUZDE_SUTUNLARI and val is not None:
        try:
            return f"{float(val):.2f}".replace(".", ",")
        except (ValueError, TypeError):
            pass
    return val


def export_powerbi_csvs(
    conn: sqlite3.Connection,
    output_dir: str | Path,
    sql_dir: Path | None = None,
) -> list[Path]:
    """Power BI görünüm (VIEW) sonuçlarını Türkçe başlık/değerlerle UTF-8 BOM CSV olarak dışa aktarır."""
    ensure_views(conn, sql_dir=sql_dir)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    exported: list[Path] = []
    for view_name, filename, col_specs in BI_EXPORT_SPECS:
        rows = conn.execute(f"SELECT * FROM {view_name};").fetchall()
        headers = [tr_name for _, tr_name, _ in col_specs]

        target = out / filename
        # Power BI ve Excel'de Türkçe karakterlerin sorunsuz açılması için utf-8-sig kullanılır
        # Sütun ayracı olarak noktalı virgül (;) kullanılır — Türkçe lokal için standart
        with target.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(headers)
            for row in rows:
                out_row = []
                for src_col, tr_name, transform in col_specs:
                    val = row[src_col]
                    val = transform(val) if transform is not None else val
                    out_row.append(_format_deger(val, tr_name))
                writer.writerow(out_row)

        exported.append(target)

    return exported
