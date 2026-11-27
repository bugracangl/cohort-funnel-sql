# Değişiklik Kaydı

Bu proje [Keep a Changelog](https://keepachangelog.com/tr/1.0.0/) formatını takip eder
ve [Semantic Versioning](https://semver.org/lang/tr/) standardını uygular.

## [1.1.0] - 2026-11-27

### Eklendi
- GitHub Pages otomatik deploy workflow (`.github/workflows/pages.yml`)
- Dependabot güvenlik güncellemeleri (`.github/dependabot.yml`)
- Issue şablonları: Hata bildirimi ve özellik önerisi (`.github/ISSUE_TEMPLATE/`)
- Pull Request şablonu (`.github/PULL_REQUEST_TEMPLATE.md`)
- Katkı rehberi (`CONTRIBUTING.md`)
- Makefile: yaygın komutlar için kısayollar (`demo`, `test`, `lint`, `format`, `ci`, `clean`)
- pre-commit hooks yapılandırması (`.pre-commit-config.yaml`)
- Değişiklik kaydı (`CHANGELOG.md`)
- Güvenlik politikası (`SECURITY.md`)
- EditorConfig (`.editorconfig`)
- README'ye: Canlı dashboard linki, Power BI bağlantı notu, Dürüstlük/Şeffaflık notu
- `index.html` (GitHub Pages için kök dizine kopyalanan dashboard)
- LICENSE: Telif hakkı sahibi Türkçe karakterlerle güncellendi

### Düzeltildi
- `assets/dashboard.html` ve `index.html`: GitHub linki `bugracan0719` → `bugracangl` olarak düzeltildi

### Güvenlik
- Dependabot ile haftalık bağımlılık ve GitHub Actions güncellemeleri aktif edildi

---

## [1.0.0] - 2026-11-27

### Eklendi
- **İlk sürüm**: Python + SQLite ile kohort tutundurma ve dönüşüm huni analizi
- 5 adımlı kronolojik dönüşüm huni (CTE + Window Functions)
- Aylık kohort tutundurma matrisi (yıl geçişine dayanıklı)
- Edinme kanalı performans karşılaştırması (referral, organic, paid_search, social)
- Sentetik veri üreticisi (seed ile tekrarlanabilir, gerçekçi SaaS davranışları)
- CLI arayüzü: `demo`, `generate`, `load`, `analyze`, `export-bi`
- Terminal tablosu, Markdown raporu, JSON özeti çıktıları
- Saf Python ile SVG grafikler (funnel chart, cohort heatmap)
- Power BI entegrasyonu için SQL VIEW katmanı ve CSV export
- GitHub Actions CI pipeline (testler)
- Windows için `demo_baslat.bat` tek tıkla çalıştırma
- MIT Lisansı

---

## Sürümleme Notları

- `v1.0.0`: İlk kararlı sürüm, temel analiz özellikleri tamam
- `v1.1.0`: Prodüksiyon hazırlığı: CI/CD, dokümantasyon, katkı standartları, güvenlik

### Gelecek Sürümler İçin Planlananlar

- [ ] v1.2.0: PyPI paketi (`pip install cohort-funnel-sql`)
- [ ] v1.2.0: Docker image desteği
- [ ] v1.3.0: Gerçek zamanlı veri akışı simülasyonu
- [ ] v1.3.0: Cohort karşılaştırma API'sı