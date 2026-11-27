"""Terminal biçimlendirme, Markdown raporu ve saf Python SVG grafikleri."""

from __future__ import annotations

from html import escape
from pathlib import Path

from .analyzer import AnalysisResult, CohortMatrix, FunnelStep

STEP_LABELS_TR: dict[str, str] = {
    "signup": "Kayıt (signup)",
    "onboarding_complete": "Kurulum (onboarding)",
    "first_project": "İlk Proje (first_project)",
    "invite_team": "Ekip Daveti (invite_team)",
    "subscribed": "Abonelik (subscribed)",
}

CHANNEL_LABELS_TR: dict[str, str] = {
    "referral": "Referans (referral)",
    "organic": "Organik (organic)",
    "paid_search": "Ücretli Arama (paid_search)",
    "social": "Sosyal Medya (social)",
}


def _step_label(name: str) -> str:
    return STEP_LABELS_TR.get(name, name)


def _channel_label(name: str) -> str:
    return CHANNEL_LABELS_TR.get(name, name)


def _compute_insights(result: AnalysisResult) -> list[str]:
    insights: list[str] = []

    if result.funnel:
        top = result.funnel[0]
        bottom = result.funnel[-1]
        insights.append(
            f"Uçtan uca genel dönüşüm (`{top.step_name}` -> `{bottom.step_name}`): "
            f"**%{bottom.overall_conversion_pct:.2f}** ({bottom.users} / {top.users} kullanıcı)."
        )
        drop_steps = [s for s in result.funnel[1:] if s.drop_off_pct > 0]
        if drop_steps:
            worst = max(drop_steps, key=lambda s: s.drop_off_pct)
            insights.append(
                f"En büyük huni darboğazı: **{_step_label(worst.step_name)}** adımında "
                f"**%{worst.drop_off_pct:.2f}** kayıp."
            )

    m1_values = [r.retention[1] for r in result.cohorts.rows if 1 in r.retention]
    if m1_values:
        avg_m1 = sum(m1_values) / len(m1_values)
        insights.append(f"Kohortlar genelinde ortalama 1. Ay tutundurma oranı: **%{avg_m1:.2f}**.")

    if result.channels:
        best = result.channels[0]
        insights.append(
            f"En yüksek dönüşüm sağlayan edinme kanalı: **{_channel_label(best.channel)}** "
            f"(**%{best.paid_conversion_pct:.2f}** ücretli dönüşüm, **%{best.activation_rate_pct:.2f}** aktivasyon)."
        )

    return insights


def format_terminal_report(result: AnalysisResult) -> str:
    """Terminal için okunabilir Türkçe analiz özeti üretir."""
    lines: list[str] = []
    lines.append("=" * 82)
    lines.append("ÜRÜN ANALİTİĞİ RAPORU (PYTHON + SQLITE)")
    lines.append("=" * 82)

    active_filters = {k: v for k, v in result.filters.items() if v}
    if active_filters:
        lines.append("Filtreler: " + ", ".join(f"{k}={v}" for k, v in active_filters.items()))
        lines.append("-" * 82)

    lines.append("\n1. DÖNÜŞÜM HUNİSİ (FUNNEL)")
    lines.append(f"{'Adım':<28} {'Kişi':>7} {'Genel %':>10} {'Adım %':>9} {'Kayıp %':>9}  Görsel")
    lines.append("-" * 82)
    for s in result.funnel:
        bar_len = max(0, min(18, round(s.overall_conversion_pct / 5.5)))
        bar = "#" * bar_len + "." * (18 - bar_len)
        lines.append(
            f"{_step_label(s.step_name):<28} {s.users:>7} {s.overall_conversion_pct:>9.2f}% "
            f"{s.step_conversion_pct:>8.2f}% {s.drop_off_pct:>8.2f}%  [{bar}]"
        )

    lines.append("\n2. AYLIK KOHORT TUTUNDURMA MATRİSİ (COHORT RETENTION)")
    if not result.cohorts.rows:
        lines.append("Kohort verisi bulunamadı.")
    else:
        max_m = result.cohorts.max_month
        header = f"{'Kohort':<10} {'Kişi':>6} " + " ".join(f"{'Ay ' + str(m):>7}" for m in range(max_m + 1))
        lines.append(header)
        lines.append("-" * len(header))
        for row in result.cohorts.rows:
            cells = []
            for m in range(max_m + 1):
                if m in row.retention:
                    cells.append(f"{row.retention[m]:>6.1f}%")
                else:
                    cells.append(f"{'-':>7}")
            lines.append(f"{row.cohort_month:<10} {row.cohort_size:>6} " + " ".join(cells))

    lines.append("\n3. EDİNME KANALI PERFORMANSI")
    lines.append(f"{'Kanal':<14} {'Kullanıcı':>9} {'Kurulum':>9} {'Aktif':>8} {'Ücretli':>8} {'Akt. %':>8} {'Ücr. %':>8}")
    lines.append("-" * 82)
    for ch in result.channels:
        lines.append(
            f"{ch.channel:<14} {ch.total_users:>9} {ch.onboarded_users:>9} "
            f"{ch.activated_users:>8} {ch.subscribed_users:>8} "
            f"{ch.activation_rate_pct:>7.2f}% {ch.paid_conversion_pct:>7.2f}%"
        )

    insights = _compute_insights(result)
    if insights:
        lines.append("\n4. ÖNE ÇIKAN BULGULAR")
        for item in insights:
            lines.append(f" - {item.replace('**', '').replace('`', '')}")

    lines.append("=" * 82)
    return "\n".join(lines)


def generate_markdown_report(
    result: AnalysisResult,
    cohort_svg: str | None = None,
    funnel_svg: str | None = None,
) -> str:
    """GitHub uyumlu Türkçe Markdown raporu üretir."""
    lines: list[str] = ["# Ürün Analitiği Raporu", ""]

    active_filters = {k: v for k, v in result.filters.items() if v}
    if active_filters:
        filter_str = ", ".join(f"`{k}={v}`" for k, v in active_filters.items())
        lines.extend([f"> **Filtreler:** {filter_str}", ""])

    lines.extend(["## Öne Çıkan Bulgular", ""])
    for item in _compute_insights(result):
        lines.append(f"- {item}")
    lines.append("")

    lines.extend(["## Dönüşüm Hunisi (Funnel)", ""])
    if funnel_svg:
        lines.extend([f"![Dönüşüm Hunisi Grafiği]({funnel_svg})", ""])

    lines.extend([
        "| Sıra | Adım | Kullanıcı | Genel Dönüşüm | Adım Dönüşümü | Adım Kaybı |",
        "|---:|---|---:|---:|---:|---:|",
    ])
    for s in result.funnel:
        lines.append(
            f"| {s.step_order} | {_step_label(s.step_name)} | {s.users} | "
            f"%{s.overall_conversion_pct:.2f} | %{s.step_conversion_pct:.2f} | %{s.drop_off_pct:.2f} |"
        )
    lines.append("")

    lines.extend(["## Aylık Kohort Tutundurma Matrisi", ""])
    if cohort_svg:
        lines.extend([f"![Aylık Kohort Tutundurma Isı Haritası]({cohort_svg})", ""])

    if result.cohorts.rows:
        max_m = result.cohorts.max_month
        month_headers = " | ".join(f"Ay {m}" for m in range(max_m + 1))
        month_sep = " | ".join("---:" for _ in range(max_m + 1))
        lines.append(f"| Kohort | Boyut | {month_headers} |")
        lines.append(f"|---|---:|{month_sep}|")
        for row in result.cohorts.rows:
            vals = " | ".join(
                f"%{row.retention[m]:.1f}" if m in row.retention else "-"
                for m in range(max_m + 1)
            )
            lines.append(f"| {row.cohort_month} | {row.cohort_size} | {vals} |")
        lines.append("")

    lines.extend([
        "## Edinme Kanalı Kırılımı",
        "",
        "| Kanal | Toplam Kullanıcı | Kurulum | Aktivasyon | Abone | Aktivasyon Oranı | Ücretli Dönüşüm |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])
    for ch in result.channels:
        lines.append(
            f"| {_channel_label(ch.channel)} | {ch.total_users} | {ch.onboarded_users} | "
            f"{ch.activated_users} | {ch.subscribed_users} | "
            f"%{ch.activation_rate_pct:.2f} | %{ch.paid_conversion_pct:.2f} |"
        )
    lines.append("")
    return "\n".join(lines)


def _interpolate_color(pct: float) -> tuple[str, str]:
    """Tutundurma yüzdesini (0-100) dolgu ve yazı rengine eşler."""
    ratio = max(0.0, min(1.0, pct / 100.0))
    r = round(234 + (15 - 234) * ratio)
    g = round(242 + (98 - 242) * ratio)
    b = round(255 + (254 - 255) * ratio)
    fill = f"#{r:02x}{g:02x}{b:02x}"
    text = "#ffffff" if ratio >= 0.48 else "#161616"
    return fill, text


def generate_cohort_svg(cohorts: CohortMatrix, output_path: str | Path) -> Path:
    """Harici kütüphane olmadan Türkçe SVG kohort ısı haritası üretir."""
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    pad_x = 24
    pad_y = 24
    title_h = 46
    label_w = 96
    size_w = 78
    cell_w = 74
    cell_h = 36
    header_h = 32
    gap = 4

    num_months = (cohorts.max_month + 1) if cohorts.rows else 1
    num_rows = len(cohorts.rows)

    width = pad_x * 2 + label_w + size_w + num_months * (cell_w + gap)
    height = pad_y * 2 + title_h + header_h + max(1, num_rows) * (cell_h + gap) + 12

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" rx="12" fill="#ffffff" stroke="#e5e7eb"/>',
        f'<text x="{pad_x}" y="{pad_y + 20}" font-family="Segoe UI, Arial, sans-serif" font-size="18" font-weight="700" fill="#111827">Aylık Kohort Tutundurma Isı Haritası</text>',
        f'<text x="{pad_x}" y="{pad_y + 39}" font-family="Segoe UI, Arial, sans-serif" font-size="12" fill="#6b7280">Kayıt sonrası N. ayda aktif olarak geri dönen kullanıcı yüzdesi</text>',
    ]

    grid_top = pad_y + title_h
    parts.append(
        f'<text x="{pad_x}" y="{grid_top + 20}" font-family="Segoe UI, Arial, sans-serif" font-size="12" font-weight="600" fill="#374151">Kohort</text>'
    )
    parts.append(
        f'<text x="{pad_x + label_w + size_w - 10}" y="{grid_top + 20}" text-anchor="end" font-family="Segoe UI, Arial, sans-serif" font-size="12" font-weight="600" fill="#374151">Kullanıcı</text>'
    )

    grid_x = pad_x + label_w + size_w + 8
    for m in range(num_months):
        cx = grid_x + m * (cell_w + gap) + cell_w / 2
        parts.append(
            f'<text x="{cx:.1f}" y="{grid_top + 20}" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="12" font-weight="600" fill="#374151">Ay {m}</text>'
        )

    for r_idx, row in enumerate(cohorts.rows):
        ry = grid_top + header_h + r_idx * (cell_h + gap)
        cy_text = ry + cell_h / 2 + 4
        parts.append(
            f'<text x="{pad_x}" y="{cy_text:.1f}" font-family="Segoe UI, Arial, sans-serif" font-size="12" font-weight="600" fill="#1f2937">{escape(row.cohort_month)}</text>'
        )
        parts.append(
            f'<text x="{pad_x + label_w + size_w - 10}" y="{cy_text:.1f}" text-anchor="end" font-family="Segoe UI, Arial, sans-serif" font-size="12" fill="#4b5563">{row.cohort_size}</text>'
        )
        for m in range(num_months):
            cx = grid_x + m * (cell_w + gap)
            if m in row.retention:
                pct = row.retention[m]
                fill, text_color = _interpolate_color(pct)
                parts.append(
                    f'<rect x="{cx}" y="{ry}" width="{cell_w}" height="{cell_h}" rx="6" fill="{fill}"/>'
                )
                parts.append(
                    f'<text x="{cx + cell_w / 2:.1f}" y="{cy_text:.1f}" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="12" font-weight="600" fill="{text_color}">%{pct:.1f}</text>'
                )
            else:
                parts.append(
                    f'<rect x="{cx}" y="{ry}" width="{cell_w}" height="{cell_h}" rx="6" fill="#f9fafb" stroke="#f3f4f6"/>'
                )

    parts.append("</svg>")
    out_path.write_text("\n".join(parts), encoding="utf-8")
    return out_path


def generate_funnel_svg(funnel: list[FunnelStep], output_path: str | Path) -> Path:
    """Harici kütüphane olmadan Türkçe yatay dönüşüm hunisi SVG grafiği üretir."""
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    pad_x = 24
    pad_y = 24
    title_h = 52
    label_w = 195
    bar_max_w = 340
    stats_w = 175
    row_h = 44
    gap = 10

    num_rows = max(1, len(funnel))
    width = pad_x * 2 + label_w + bar_max_w + stats_w
    height = pad_y * 2 + title_h + num_rows * (row_h + gap)

    palette = ["#0f62fe", "#2563eb", "#3b82f6", "#0284c7", "#0d9488"]

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" rx="12" fill="#ffffff" stroke="#e5e7eb"/>',
        f'<text x="{pad_x}" y="{pad_y + 20}" font-family="Segoe UI, Arial, sans-serif" font-size="18" font-weight="700" fill="#111827">5 Adımlı Dönüşüm Hunisi (Funnel)</text>',
        f'<text x="{pad_x}" y="{pad_y + 40}" font-family="Segoe UI, Arial, sans-serif" font-size="12" fill="#6b7280">Kayıttan ücretli aboneliğe kadar adım bazlı kullanıcı sayısı ve dönüşüm oranı</text>',
    ]

    start_y = pad_y + title_h
    bar_x = pad_x + label_w

    for idx, step in enumerate(funnel):
        ry = start_y + idx * (row_h + gap)
        cy = ry + row_h / 2 + 4
        pct = max(0.0, min(100.0, step.overall_conversion_pct))
        fill_w = max(4.0, bar_max_w * (pct / 100.0)) if step.users > 0 else 0.0
        color = palette[idx % len(palette)]

        parts.append(
            f'<text x="{pad_x}" y="{cy:.1f}" font-family="Segoe UI, Arial, sans-serif" font-size="13" font-weight="600" fill="#1f2937">{escape(_step_label(step.step_name))}</text>'
        )
        parts.append(
            f'<rect x="{bar_x}" y="{ry + 6}" width="{bar_max_w}" height="{row_h - 12}" rx="8" fill="#f3f4f6"/>'
        )
        if fill_w > 0:
            parts.append(
                f'<rect x="{bar_x}" y="{ry + 6}" width="{fill_w:.1f}" height="{row_h - 12}" rx="8" fill="{color}"/>'
            )

        stats_x = bar_x + bar_max_w + 14
        drop_text = f" (kayıp %{step.drop_off_pct:.1f})" if step.step_order > 1 else ""
        parts.append(
            f'<text x="{stats_x}" y="{cy:.1f}" font-family="Segoe UI, Arial, sans-serif" font-size="12" font-weight="600" fill="#111827">{step.users} kişi · %{pct:.1f}</text>'
        )
        if drop_text:
            parts.append(
                f'<text x="{stats_x}" y="{cy + 14:.1f}" font-family="Segoe UI, Arial, sans-serif" font-size="11" fill="#dc2626">{escape(drop_text.strip())}</text>'
            )

    parts.append("</svg>")
    out_path.write_text("\n".join(parts), encoding="utf-8")
    return out_path
