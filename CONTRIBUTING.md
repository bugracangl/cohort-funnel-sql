# Katkı Rehberi

Bu projeye katkı sağlamak için teşekkürler! 🎉

## Başlarken

1. **Fork** yapın ve yerel klonlayın
2. **Branch** oluşturun: `git checkout -b feature/amazing-feature`
3. Değişikliklerinizi yapın
4. **Test** edin: `make test`
5. **Lint** kontrolü: `make lint`
6. **Commit** atın: `git commit -m "feat: açıklayıcı mesaj"`
7. **Push** edin ve **PR** açın

## Geliştirme Ortamı

```bash
# Bağımlılık yok (sadece Python 3.10+)
# İsteğe bağlı: geliştirme araçları
pip install ruff black mypy pre-commit

# pre-commit hook'ları kurun (önerilir)
pre-commit install
```

## Kod Standartları

| Araç | Komut | Açıklama |
|------|-------|----------|
| **ruff** | `ruff check .` | Hızlı linting (flake8 + isort + daha fazlası) |
| **ruff format** | `ruff format .` | Black uyumlu formatting |
| **mypy** | `mypy src/` | Static type checking |

### Commit Mesaj Formatı

[Conventional Commits](https://www.conventionalcommits.org/) standardını kullanıyoruz:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Tipler:**
- `feat`: Yeni özellik
- `fix`: Hata düzeltmesi
- `docs`: Dokümantasyon
- `style`: Formatlama (kod mantığını değiştirmez)
- `refactor`: Yeniden yapılandırma
- `test`: Test ekleme/güncelleme
- `chore`: Bakım, bağımlılıklar, CI

**Örnekler:**
```
feat(analyzer): kanal bazlı filtreleme eklendi
fix(generator): ay aralığı hesaplamasında off-by-one hatası düzeltildi
docs(readme): Power BI bağlantı notu eklendi
chore(deps): ruff 0.5.x'e güncellendi
```

## Test Yazma

```bash
# Tüm testler
make test
# veya
PYTHONPATH=src python -m unittest discover -s tests -v

# Tek test dosyası
PYTHONPATH=src python -m unittest tests.test_analytics -v
```

Yeni test eklerken:
- `tests/` klasörüne `test_<modül>.py` formatında dosya ekleyin
- `unittest.TestCase` kullanın
- Edge case'leri test edin (boş veri, sınır değerler, hata durumları)

## PR Süreci

1. PR açın → **Draft** olarak başlatın, hazır olunca "Ready for review" yapın
2. CI kontrolleri geçmeli (GitHub Actions: test, lint)
3. En az 1 onay (`Approve`) alın
4. `Squash and merge` ile birleştirin (varsayılan)

## Sürümleme

[Semantic Versioning](https://semver.org/) kullanıyoruz:
- `MAJOR`: Breaking change
- `MINOR`: Geriye uyumlu yeni özellik
- `PATCH`: Geriye uyumlu hata düzeltmesi

## Lisans

Katkılarınız [MIT Lisansı](LICENSE) kapsamında kabul edilir.

---

**Sorunuz mu var?** Issue açın veya mevcut issue'larda tartışın.