# Power BI Dashboard Kurulum Rehberi

Bu rehber, SQLite veritabanındaki hazır SQL `VIEW` tablolarını (`sql/powerbi_views.sql`) kullanarak **Power BI Desktop** üzerinde etkileşimli **Kohort ve Dönüşüm Hunisi Dashboard'u** oluşturmanız için hazırlanmıştır.

---

## 1. Power BI Verilerini Üretme

Aşağıdaki komutlardan birini çalıştırdığınızda `output/powerbi/` klasörüne **Türkçe sütun ve değerlere sahip** 6 adet temiz CSV tablosu üretilir:

```powershell
$env:PYTHONPATH = "src"
python -m cohort_funnel.cli demo
# veya mevcut bir veritabanından yalnızca BI tablolarını çıkarmak için:
python -m cohort_funnel.cli export-bi --db data/analytics.db --out-dir output/powerbi
```

### Üretilen Tablolar
| Dosya | Kaynak SQL View | Kullanım Amacı |
|---|---|---|
| `bi_kullanici_yolculugu.csv` | `vw_user_journey` | KPI kartları (toplam kullanıcı, aktivasyon, ücretli abone) ve tarih/kanal dilimleme |
| `bi_huni_genel.csv` | `vw_funnel_steps` | Genel 5 adımlı dönüşüm hunisi |
| `bi_huni_kanal.csv` | `vw_funnel_by_channel` | Kanal dilimleyicisi (`kanal`) ile etkileşimli çalışan huni |
| `bi_kohort_genel.csv` | `vw_cohort_retention` | Genel aylık kohort tutundurma ısı haritası |
| `bi_kohort_kanal.csv` | `vw_cohort_by_channel` | Kanal dilimleyicisiyle filtrelenebilen kohort matrisi |
| `bi_kanal_ozeti.csv` | `vw_channel_summary` | Edinme kanalı performans karşılaştırması |

---

## 2. Power BI Desktop'ta Görselleri Kurma (Adım Adım)

1. **Power BI Desktop**'ı açın -> **Veri Al (Get Data) -> Metin/CSV (Text/CSV)**.
2. `output/powerbi/` içindeki **`bi_kullanici_yolculugu.csv`**, **`bi_huni_kanal.csv`**, **`bi_kohort_kanal.csv`** ve **`bi_kanal_ozeti.csv`** dosyalarını yükleyin.
3. **Model Görünümü (Model View)** sekmesinde ortak bir `kanal` boyut tablosu oluşturarak (veya her görselin kendi `kanal` sütununu bağlayarak) tek bir **Kanal Dilimleyicisi (Slicer)** ile tüm sayfayı kontrol edin.

### Önerilen 4 Ana Görsel

1. **Üst KPI Kartları (Card Visual):**
   * `bi_kullanici_yolculugu` üzerinden:
     * **Toplam Kullanıcı:** `kullanici_id` (Say / Count)
     * **Aktivasyon Oranı:** `ilk_proje_tamam` (Ortalama / Average, `%` biçiminde)
     * **Ücretli Dönüşüm:** `abonelik_tamam` (Ortalama / Average, `%` biçiminde)

2. **Dönüşüm Hunisi (Funnel Chart):**
   * Kaynak: `bi_huni_kanal` (tüm kanallar toplamı veya tek kanal seçildiğinde `kullanici_sayisi` toplamı; tekil genel görünüm için `bi_huni_genel`)
   * **Category (Kategori):** `adim_adi` *(sıralama için `adim_sirasi` sütununa göre "Sütuna Göre Sırala" yapın)*
   * **Values (Değerler):** `kullanici_sayisi`

3. **Kohort Tutundurma Isı Haritası (Matrix Visual):**
   * Kaynak: `bi_kohort_genel` (veya tekil kanal filtresi için `bi_kohort_kanal`)
   * **Rows (Satırlar):** `kohort_ayi`
   * **Columns (Sütunlar):** `ay_no`
   * **Values (Değerler):** `tutundurma_yuzdesi` *(Ortalama / İlk)*
   * **Isı Haritası Rengi:** Görsel Biçimlendirme -> **Hücre öğeleri (Cell elements)** -> **Arka plan rengi (Background color)** açıp açık maviden (`#EAF2FF`) koyu maviye (`#0F62FE`) gradyan verin.

4. **Kanal Dönüşüm Grafiği (Clustered Bar Chart):**
   * Kaynak: `bi_kanal_ozeti`
   * **Y-axis:** `kanal`
   * **X-axis:** `aktivasyon_orani_yuzde` ve `ucretli_donusum_yuzde`

---

## 3. GitHub'a Ekleme

Dashboard'unuzu tamamladıktan sonra:
1. Dosyayı `powerbi/cohort_funnel_dashboard.pbix` olarak kaydedin.
2. Dashboard'un tam ekran görüntüsünü `assets/powerbi_dashboard.png` olarak kaydedin.
3. Ana [README.md](../README.md) dosyasına görseli eklediğinizde proje tam bir **SQL + Python + Power BI** portföy vitrinine dönüşür.
