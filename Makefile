# Makefile - Cohort Funnel SQL Projesi
# Kullanım: make <komut>

.PHONY: help demo test lint format typecheck clean install precommit ci docs

# Varsayılan hedef
help:
	@echo "📦 Cohort Funnel SQL - Komutlar"
	@echo ""
	@echo "  Geliştirme:"
	@echo "    make demo        - Demo çalıştır (veri üret + analiz + grafikler)"
	@echo "    make install     - Geliştirme araçlarını kur (ruff, black, mypy, pre-commit)"
	@echo "    make precommit   - pre-commit hook'larını kur"
	@echo ""
	@echo "  Test & Kalite:"
	@echo "    make test        - Tüm testleri çalıştır"
	@echo "    make lint        - Kod kalitesi kontrolü (ruff)"
	@echo "    make format      - Kod formatla (ruff format)"
	@echo "    make typecheck   - Tip kontrolü (mypy)"
	@echo "    make ci          - CI pipeline'ı yerel çalıştır (lint + typecheck + test)"
	@echo ""
	@echo "  Temizlik:"
	@echo "    make clean       - Önbellek ve çıktı dosyalarını temizle"
	@echo ""
	@echo "  Dokümantasyon:"
	@echo "    make docs        - README linklerini kontrol et"

# Demo çalıştır
demo:
	@echo "🚀 Demo başlatılıyor..."
	PYTHONPATH=src python -m cohort_funnel.cli demo

# Testler
test:
	@echo "🧪 Testler çalıştırılıyor..."
	PYTHONPATH=src python -m unittest discover -s tests -v

# Linting
lint:
	@echo "🔍 Kod kalitesi kontrol ediliyor..."
	ruff check src/ tests/

# Formatlama
format:
	@echo "✨ Kod formatlanıyor..."
	ruff format src/ tests/

# Tip kontrolü
typecheck:
	@echo "🔍 Tip kontrolü yapılıyor..."
	mypy src/

# CI pipeline
ci: lint typecheck test
	@echo "✅ CI pipeline başarılı!"

# Geliştirme araçları kur
install:
	@echo "📦 Geliştirme araçları kuruluyor..."
	pip install --upgrade pip
	pip install ruff black mypy pre-commit

# pre-commit kur
precommit:
	@echo "🪝 pre-commit hook'ları kuruluyor..."
	pre-commit install
	@echo "✅ Hook'lar kuruldu. Commit öncesi otomatik çalışacak."

# Temizlik
clean:
	@echo "🧹 Temizlik yapılıyor..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf output/ 2>/dev/null || true
	rm -rf dist/ build/ *.egg-info 2>/dev/null || true
	@echo "✅ Temizlik tamamlandı."

# Dokümantasyon link kontrolü (basit)
docs:
	@echo "🔗 README linkleri kontrol ediliyor..."
	@grep -oP 'https?://[^)\s]+' README.md | sort -u | while read url; do \
		echo "  Kontrol: $$url"; \
		curl -s -o /dev/null -w "%{http_code}" "$$url" | grep -q "^2" && echo "    ✅ OK" || echo "    ⚠️  Erışilemeyen link"; \
	done