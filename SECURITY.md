# Güvenlik Politikası

## Desteklenen Sürümler

| Sürüm | Durum |
|-------|-------|
| 1.1.x | ✅ Güvenlik güncellemeleri alıyor |
| 1.0.x | ❌ Artık desteklenmiyor |

## Güvenlik Açığı Bildirme

Bu proje **sentetik veri** ve **analitik demo** amaçlıdır, production veri işleme için tasarlanmamıştır. Ancak güvenlik açığı bulursanız:

### Özel Bildirim (Tercih Edilen)

**[GitHub Security Advisories](https://github.com/bugracangl/cohort-funnel-sql/security/advisories/new)** üzerinden özel olarak bildirin.

### Alternatif: E-posta

`security@bugracangl.github.io` (GitHub üzerinden yönlendirilir)

### Bildirimde Olması Gerekenler

1. Açığın türü ve etkisi
2. Yeniden üretim adımları (PoC)
3. Etkilenen dosya/fonksiyon
4. Önerilen çözüm (varsa)

## Yanıt Süresi

- **İlk yanıt**: 72 saat içinde
- **Değerlendirme**: 7 gün içinde
- **Düzeltme**: Kritikse 30 gün, ortaysa 90 gün içinde

## Kapsam Dışı

Bu proje şunları **kapsamaz** (production kullanımına uygun değil):
- Kullanıcı kimlik doğrulama / yetkilendirme
- Hassas veri şifreleme / PII koruma
- SQL injection koruması (parametreli sorgular kullanılmamıştır - sadece sabit SQL dosyaları)
- Rate limiting / DoS koruması
- Audit logging

## Güvenli Kullanım İçin Öneriler

Eğer bu kodu production'a uyarlamak isterseniz:

1. **Parametreli sorgular** kullanın (SQL injection önlemi)
2. **Girdi validasyonu** ekleyin (CSV yükleme, tarih formatları)
3. **Kimlik doğrulama** katmanı ekleyin
4. **Veritabanı bağlantı havuzu** ve **şifreleme** (SSL/TLS) kullanın
5. **Loglama ve izleme** (audit trail) ekleyin
6. **Bağımlılık taraması** düzenli yapın (`pip-audit`, `safety`, Dependabot)

## Teşekkürler

Güvenliği ciddiye alan ve sorumlu bildirim yapan tüm araştırmacılara teşekkür ederiz.

---

**Not:** Bu bir demo/portfolio projesidir. Gerçek finansal, sağlık veya kişisel verilerle kullanmayın.