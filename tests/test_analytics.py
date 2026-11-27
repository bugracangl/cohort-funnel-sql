"""SQL funnel, kohort tutundurma, CSV yükleme ve raporlama için birim testleri."""

from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cohort_funnel.analyzer import analyze_all, run_channel_summary, run_cohort_retention, run_funnel
from cohort_funnel.cli import main as cli_main
from cohort_funnel.db import get_connection, init_db, load_csv_data
from cohort_funnel.powerbi import BI_EXPORTS, export_powerbi_csvs
from cohort_funnel.report import generate_cohort_svg, generate_funnel_svg, generate_markdown_report


class TestAnalyticsSQL(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = get_connection(":memory:")
        init_db(self.conn)

    def tearDown(self) -> None:
        self.conn.close()

    def test_strict_sequential_funnel_enforces_event_order(self) -> None:
        with self.conn:
            self.conn.executemany(
                "INSERT INTO users (user_id, signup_date, channel, plan_tier) VALUES (?, ?, ?, ?);",
                [
                    ("u1", "2026-01-05", "organic", "pro"),
                    ("u2", "2026-01-06", "organic", "free"),
                    ("u3", "2026-01-07", "referral", "free"),
                ],
            )
            self.conn.executemany(
                "INSERT INTO events (user_id, event_name, event_ts) VALUES (?, ?, ?);",
                [
                    # u1 tüm 5 adımı geçerli kronolojik sırada tamamlar
                    ("u1", "signup", "2026-01-05T10:00:00"),
                    ("u1", "onboarding_complete", "2026-01-05T10:15:00"),
                    ("u1", "first_project", "2026-01-05T12:00:00"),
                    ("u1", "invite_team", "2026-01-06T09:00:00"),
                    ("u1", "subscribed", "2026-01-08T14:00:00"),
                    # u2 kullanıcısında first_project, onboarding_complete ÖNCESİNDE -> 2. adımda durur
                    ("u2", "signup", "2026-01-06T10:00:00"),
                    ("u2", "first_project", "2026-01-06T10:05:00"),
                    ("u2", "onboarding_complete", "2026-01-06T11:00:00"),
                    # u3 yalnızca kayıt olur
                    ("u3", "signup", "2026-01-07T08:00:00"),
                ],
            )

        steps = run_funnel(self.conn)
        counts = {s.step_name: s.users for s in steps}
        self.assertEqual(counts["signup"], 3)
        self.assertEqual(counts["onboarding_complete"], 2)
        self.assertEqual(counts["first_project"], 1)
        self.assertEqual(counts["invite_team"], 1)
        self.assertEqual(counts["subscribed"], 1)

        # Kanal filtresi huniyi yalnızca referral kullanıcılarıyla sınırlar
        ref_steps = run_funnel(self.conn, channel="referral")
        self.assertEqual(ref_steps[0].users, 1)
        self.assertEqual(ref_steps[1].users, 0)

    def test_cohort_retention_crosses_year_boundary(self) -> None:
        with self.conn:
            self.conn.executemany(
                "INSERT INTO users (user_id, signup_date, channel, plan_tier) VALUES (?, ?, ?, ?);",
                [
                    ("u1", "2025-12-10", "organic", "free"),
                    ("u2", "2025-12-20", "paid_search", "free"),
                    ("u3", "2026-01-05", "organic", "pro"),
                ],
            )
            self.conn.executemany(
                "INSERT INTO events (user_id, event_name, event_ts) VALUES (?, ?, ?);",
                [
                    ("u1", "signup", "2025-12-10T09:00:00"),
                    ("u1", "active_session", "2026-01-12T10:00:00"),
                    ("u1", "active_session", "2026-02-04T11:00:00"),
                    ("u2", "signup", "2025-12-20T09:00:00"),
                    # u2 Ocak ve Şubat aylarında aktif değil
                    ("u3", "signup", "2026-01-05T15:00:00"),
                    ("u3", "active_session", "2026-02-09T16:00:00"),
                ],
            )

        matrix = run_cohort_retention(self.conn)
        self.assertEqual(len(matrix.rows), 2)

        dec = matrix.rows[0]
        self.assertEqual(dec.cohort_month, "2025-12")
        self.assertEqual(dec.cohort_size, 2)
        self.assertEqual(dec.retention[0], 100.0)
        self.assertEqual(dec.retention[1], 50.0)
        self.assertEqual(dec.retention[2], 50.0)

        jan = matrix.rows[1]
        self.assertEqual(jan.cohort_month, "2026-01")
        self.assertEqual(jan.cohort_size, 1)
        self.assertEqual(jan.retention[0], 100.0)
        self.assertEqual(jan.retention[1], 100.0)

    def test_channel_summary_and_csv_load_and_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            users_csv = tmp_path / "users.csv"
            events_csv = tmp_path / "events.csv"

            with users_csv.open("w", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                w.writerow(["user_id", "signup_date", "channel", "plan_tier"])
                w.writerow(["u1", "2026-02-01", "referral", "pro"])
                w.writerow(["u2", "2026-02-02", "social", "free"])

            with events_csv.open("w", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                w.writerow(["user_id", "event_name", "event_ts"])
                w.writerow(["u1", "signup", "2026-02-01T10:00:00"])
                w.writerow(["u1", "onboarding_complete", "2026-02-01T10:20:00"])
                w.writerow(["u1", "first_project", "2026-02-01T11:00:00"])
                w.writerow(["u1", "invite_team", "2026-02-02T11:00:00"])
                w.writerow(["u1", "subscribed", "2026-02-03T11:00:00"])
                w.writerow(["u2", "signup", "2026-02-02T09:00:00"])

            n_u, n_e = load_csv_data(self.conn, users_csv, events_csv)
            self.assertEqual((n_u, n_e), (2, 6))

            channels = run_channel_summary(self.conn)
            self.assertEqual(channels[0].channel, "referral")
            self.assertEqual(channels[0].paid_conversion_pct, 100.0)

            res = analyze_all(self.conn)
            cohort_svg_path = generate_cohort_svg(res.cohorts, tmp_path / "heatmap.svg")
            funnel_svg_path = generate_funnel_svg(res.funnel, tmp_path / "funnel.svg")
            self.assertTrue(cohort_svg_path.is_file())
            self.assertTrue(funnel_svg_path.is_file())
            self.assertIn("<svg", cohort_svg_path.read_text(encoding="utf-8"))
            self.assertIn("<svg", funnel_svg_path.read_text(encoding="utf-8"))

            md = generate_markdown_report(res, cohort_svg="heatmap.svg", funnel_svg="funnel.svg")
            self.assertIn("## Dönüşüm Hunisi (Funnel)", md)
            self.assertIn("![Aylık Kohort Tutundurma Isı Haritası](heatmap.svg)", md)
            self.assertIn("![Dönüşüm Hunisi Grafiği](funnel.svg)", md)

    def test_cli_demo_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            db_path = tmp_path / "demo.db"
            out_dir = tmp_path / "out"
            rc = cli_main(
                [
                    "demo",
                    "--db",
                    str(db_path),
                    "--out-dir",
                    str(out_dir),
                    "--users",
                    "250",
                    "--months",
                    "4",
                    "--seed",
                    "7",
                ]
            )
            self.assertEqual(rc, 0)
            self.assertTrue(db_path.is_file())
            self.assertTrue((out_dir / "report.md").is_file())
            self.assertTrue((out_dir / "cohort_heatmap.svg").is_file())
            self.assertTrue((out_dir / "funnel_chart.svg").is_file())
            self.assertTrue((out_dir / "summary.json").is_file())
            for _, fname in BI_EXPORTS:
                self.assertTrue((out_dir / "powerbi" / fname).is_file())

    def test_powerbi_views_and_export_bi_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            db_path = tmp_path / "bi.db"
            bi_dir = tmp_path / "powerbi"

            rc_gen = cli_main(["generate", "--db", str(db_path), "--users", "120", "--months", "3", "--seed", "11"])
            self.assertEqual(rc_gen, 0)

            rc_bi = cli_main(["export-bi", "--db", str(db_path), "--out-dir", str(bi_dir)])
            self.assertEqual(rc_bi, 0)

            for _, fname in BI_EXPORTS:
                csv_file = bi_dir / fname
                self.assertTrue(csv_file.is_file())
                self.assertGreater(csv_file.stat().st_size, 0)

            with (bi_dir / "bi_huni_genel.csv").open("r", encoding="utf-8-sig", newline="") as f:
                rows = list(csv.DictReader(f, delimiter=";"))
                self.assertEqual(rows[0]["adim_adi"], "Kayıt")
                self.assertEqual(int(rows[0]["kullanici_sayisi"]), 120)

            with (bi_dir / "bi_kanal_ozeti.csv").open("r", encoding="utf-8-sig", newline="") as f:
                ch_rows = list(csv.DictReader(f, delimiter=";"))
                self.assertTrue(any(r["kanal"] == "Referans" for r in ch_rows))

            conn = get_connection(db_path)
            try:
                journey_count = conn.execute("SELECT COUNT(*) FROM vw_user_journey;").fetchone()[0]
                funnel_top = conn.execute("SELECT users FROM vw_funnel_steps WHERE step_order = 1;").fetchone()[0]
                self.assertEqual(journey_count, 120)
                self.assertEqual(funnel_top, 120)
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
