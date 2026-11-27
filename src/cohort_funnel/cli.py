"""cohort-funnel-sql için komut satırı arayüzü (CLI)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .analyzer import analyze_all, result_to_dict
from .db import init_db, load_csv_data, open_connection
from .generator import export_csv, generate_dataset, populate_database
from .powerbi import export_powerbi_csvs
from .report import (
    format_terminal_report,
    generate_cohort_svg,
    generate_funnel_svg,
    generate_markdown_report,
)


def _export_reports(result, out_dir: Path, emit_json: bool = False) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    cohort_svg_path = generate_cohort_svg(result.cohorts, out_dir / "cohort_heatmap.svg")
    funnel_svg_path = generate_funnel_svg(result.funnel, out_dir / "funnel_chart.svg")
    md_text = generate_markdown_report(
        result,
        cohort_svg=cohort_svg_path.name,
        funnel_svg=funnel_svg_path.name,
    )
    md_path = out_dir / "report.md"
    md_path.write_text(md_text, encoding="utf-8")

    print(f"\nMarkdown raporu kaydedildi : {md_path}")
    print(f"Kohort ısı haritası       : {cohort_svg_path}")
    print(f"Dönüşüm hunisi grafiği    : {funnel_svg_path}")

    if emit_json:
        json_path = out_dir / "summary.json"
        json_path.write_text(json.dumps(result_to_dict(result), indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"JSON özeti kaydedildi     : {json_path}")


def cmd_demo(args: argparse.Namespace) -> int:
    db_path = Path(args.db)
    out_dir = Path(args.out_dir)

    with open_connection(db_path) as conn:
        init_db(conn, reset=True)
        n_users, n_events = populate_database(
            conn,
            num_users=args.users,
            months=args.months,
            seed=args.seed,
        )
        print(f"{db_path} içine {n_users} kullanıcı ve {n_events} olay (event) üretildi.")
        result = analyze_all(conn, channel=args.channel)
        bi_files = export_powerbi_csvs(conn, out_dir / "powerbi")

    print(format_terminal_report(result))
    _export_reports(result, out_dir=out_dir, emit_json=True)
    print(f"Power BI CSV dosyaları   : {out_dir / 'powerbi'} ({len(bi_files)} dosya)")
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    db_path = Path(args.db)
    with open_connection(db_path) as conn:
        init_db(conn, reset=True)
        n_users, n_events = populate_database(
            conn,
            num_users=args.users,
            months=args.months,
            seed=args.seed,
        )
    print(f"SQLite veritabanı dolduruldu: {db_path} ({n_users} kullanıcı, {n_events} olay).")

    if args.csv_dir:
        users, events = generate_dataset(num_users=args.users, months=args.months, seed=args.seed)
        users_p, events_p = export_csv(users, events, args.csv_dir)
        print(f"CSV dosyaları oluşturuldu: {users_p}, {events_p}")
    return 0


def cmd_load(args: argparse.Namespace) -> int:
    db_path = Path(args.db)
    with open_connection(db_path) as conn:
        init_db(conn, reset=args.reset)
        n_users, n_events = load_csv_data(conn, args.users_csv, args.events_csv)
    print(f"{db_path} içine {n_users} kullanıcı ve {n_events} olay yüklendi.")
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    db_path = Path(args.db)
    if not db_path.is_file():
        raise FileNotFoundError(f"Veritabanı dosyası bulunamadı: {db_path}")

    with open_connection(db_path) as conn:
        result = analyze_all(
            conn,
            start_date=args.start_date,
            end_date=args.end_date,
            channel=args.channel,
        )

    print(format_terminal_report(result))
    if args.out_dir:
        _export_reports(result, out_dir=Path(args.out_dir), emit_json=args.json)
    return 0


def cmd_export_bi(args: argparse.Namespace) -> int:
    db_path = Path(args.db)
    if not db_path.is_file():
        raise FileNotFoundError(f"Veritabanı dosyası bulunamadı: {db_path}")

    with open_connection(db_path) as conn:
        exported = export_powerbi_csvs(conn, Path(args.out_dir))

    print(f"Power BI için {len(exported)} CSV dosyası oluşturuldu: {args.out_dir}")
    for path in exported:
        print(f" - {path.name}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cohort-funnel",
        description="Python ve SQLite ile Kohort Tutundurma & Dönüşüm Hunisi Analizi.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_demo = sub.add_parser("demo", help="Örnek veri üret, SQL analizini çalıştır ve raporları dışa aktar.")
    p_demo.add_argument("--db", default="data/analytics.db", help="SQLite veritabanı yolu.")
    p_demo.add_argument("--out-dir", default="output", help="Markdown/SVG/JSON çıktı klasörü.")
    p_demo.add_argument("--users", type=int, default=1500, help="Üretilecek sentetik kullanıcı sayısı.")
    p_demo.add_argument("--months", type=int, default=6, help="Kohort ay sayısı.")
    p_demo.add_argument("--seed", type=int, default=42, help="Tekrarlanabilirlik için rastgelelik tohumu.")
    p_demo.add_argument("--channel", default=None, help="Opsiyonel edinme kanalı filtresi.")
    p_demo.set_defaults(func=cmd_demo)

    p_gen = sub.add_parser("generate", help="SQLite (ve isteğe bağlı CSV) için sentetik veri üret.")
    p_gen.add_argument("--db", default="data/analytics.db", help="SQLite veritabanı yolu.")
    p_gen.add_argument("--csv-dir", default=None, help="users.csv ve events.csv çıktısı için opsiyonel klasör.")
    p_gen.add_argument("--users", type=int, default=1500, help="Üretilecek kullanıcı sayısı.")
    p_gen.add_argument("--months", type=int, default=6, help="Kohort ay sayısı.")
    p_gen.add_argument("--seed", type=int, default=42, help="Rastgelelik tohumu.")
    p_gen.set_defaults(func=cmd_generate)

    p_load = sub.add_parser("load", help="Kendi users.csv ve events.csv dosyalarını SQLite'a yükle.")
    p_load.add_argument("--db", default="data/analytics.db", help="SQLite veritabanı yolu.")
    p_load.add_argument("--users-csv", required=True, help="users.csv dosya yolu.")
    p_load.add_argument("--events-csv", required=True, help="events.csv dosya yolu.")
    p_load.add_argument("--reset", action="store_true", help="Yüklemeden önce tabloları sıfırla.")
    p_load.set_defaults(func=cmd_load)

    p_an = sub.add_parser("analyze", help="Mevcut veritabanı üzerinde SQL funnel ve kohort analizi çalıştır.")
    p_an.add_argument("--db", default="data/analytics.db", help="SQLite veritabanı yolu.")
    p_an.add_argument("--start-date", default=None, help="Başlangıç tarihi filtresi (YYYY-MM-DD).")
    p_an.add_argument("--end-date", default=None, help="Bitiş tarihi filtresi (YYYY-MM-DD).")
    p_an.add_argument("--channel", default=None, help="Edinme kanalı filtresi.")
    p_an.add_argument("--out-dir", default=None, help="Markdown/SVG çıktıları için opsiyonel klasör.")
    p_an.add_argument("--json", action="store_true", help="--out-dir verildiğinde summary.json da üret.")
    p_an.set_defaults(func=cmd_analyze)

    p_bi = sub.add_parser("export-bi", help="Power BI Desktop için SQL VIEW tablolarını CSV olarak dışa aktar.")
    p_bi.add_argument("--db", default="data/analytics.db", help="SQLite veritabanı yolu.")
    p_bi.add_argument("--out-dir", default="output/powerbi", help="Power BI CSV çıktı klasörü.")
    p_bi.set_defaults(func=cmd_export_bi)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
