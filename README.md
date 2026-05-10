# hackathon_kobi
# KOBI Akilli Yonetim Sistemi - Proje Dokumantasyonu

Bu proje, kucuk ve orta olcekli isletmelerin (KOBI) ile kooperatiflerin hem fiziksel magazalarindaki hem de e-ticaret uzerindeki operasyonlarini tek bir merkezden yonetmelerini saglayan, ayni zamanda yapay zeka ile gelecek satis tahminleri ureten bir hackathon projesidir.

Asagida projedeki temel dosyalarin islevleri ve icerikleri detaylandirilmistir.

## Dosya Yapisi ve Icerikleri

### 1. create_db.py (Veritabani Kurulumu ve Veri Uretimi)
Sistemin temel veri yapisini olusturan ve test surecini kolaylastiran baslangic dosyasidir.
* **Tablo Olusturma:** SQLite kullanilarak isletme operasyonlari icin gerekli 10 adet tabloyu (kobiler, tedarikciler, urunler, musteriler, siparisler, siparis_kalemleri, tedarik_alimlari, alim_kalemleri, stok_hareketleri, kargo_gecikmeleri) `SME_DB.db` dosyasi icerisinde iliskisel (Foreign Key) yapida olusturur.
* **Statik Veri Girisi:** Sistemin bos kalmamasi adina ornek isletme, urun, musteri ve tedarikci verilerini veritabanina ekler.
* **Sentetik Gecmis Veri Uretimi (Yapay Zeka Icin):** Yapay zeka modelinin (Prophet) egitilebilmesi adina gecmis 180 gunu kapsayan gercege yakin, rastgele dagilimli yuzlerce siparis (satis) ve tedarik (alim) verisi uretir. Ayni zamanda bu islem sirasinda stok hareketlerini gecmise donuk olarak otomatik isler.

### 2. prophet_statistics.py (Yapay Zeka Tahmin Modulu)
Gecmis verileri analiz ederek gelecege yonelik stratejik onguruler sunan makine ogrenmesi (Zaman Serisi Tahmini) dosyasidir. Meta'nin acik kaynakli `prophet` kuthupanesini ve veri isleme icin `pandas` kullanir.
* **get_overall_revenue_forecast:** Isletmenin genel satis verilerini (iptal edilenler haric) alarak belirtilen gun sayisi kadar (ornek: 14 gun) gelecekteki ciro beklentisini hesaplar. Pozitif veya negatif trend durumunu, yuzdelik degisimi dondurur.
* **get_product_sales_forecast / get_all_products_forecast:** Satis verilerini urun bazinda ayristirir. Her bir urunun onumuzdeki gunlerdeki satis trendini, tahmini minimum-maksimum gunluk satis adetlerini hesaplayarak isletmenin kritik stok planlamasi yapmasina yardimci olur.

### 3. main.py (Backend - API Sunucusu)
Sistemin kalbini olusturan, `FastAPI` ile yazilmis sunucu dosyasidir. Veritabani ile frontend (kullanici arayuzu) arasindaki kopruyu kurar.
* **CRUD Endpointleri:** 10 farkli veritabani tablosu icin standart Ekle (POST), Listele (GET), Guncelle (PUT) ve Sil (DELETE) HTTP isteklerini yonetir.
* **Ozet ve Raporlama Uclari:** Isletme ozeti icin anlik verileri (toplam urun, kritik stoktaki urunler, siparis sayilari vb.) toplayip donduren API ucuna sahiptir.
* **Fiziksel / Elden Satis Sistemi:** `/api/hizli_satis` ve `/api/stok_artir` islevleri ile fiziki dukkan operasyonlarini kolaylastirir. Tek bir API cagirisi ile ayni anda hem stok dusumunu saglar hem de ilgili loglari `stok_hareketleri` tablosuna otomatik olarak isler. Stok yetersizliginde sistem uyari dondurur.
* **Tahmin Entegrasyonu:** `prophet_statistics.py` icerisindeki yapay zeka islevlerini disari sunan API uclarina sahiptir.
* **Frontend Sunumu:** Kullanici `/` dizinine girdiginde dogrudan `index.html` dosyasini tarayiciya gonderir.

### 4. index.html (Frontend - Kullanici Arayuzu)
Single Page Application (SPA) mantigi ile calisan, kullanicinin sayfa yenilemeden tum islerini halledebildigi, `Bootstrap 5` tabanli arayuz dosyasidir.
* **Dinamik Tablo Yapisi:** Sol menuden secilen sekmeye gore `main.py` uzerinden ilgili JSON verilerini ceker ve tablolari dinamik olarak olusturur.
* **Dinamik Form Altyapisi:** Tablo gosterimine ek olarak, API semalarina uygun otomatik Ekle/Duzenle formlari uretir.
* **Isletme Ozeti (Dashboard):** Sisteme giris yapildiginda temel isletme istatistiklerini (toplam siparis, kritik stok vb.) kartlar halinde sunar.
* **Yapay Zeka Gosterge Paneli:** Backend uzerinden gelen Prophet verilerini isleyerek isletme sahibine "Genel Ciro Beklentisi" ve "Urun Bazli Satis Trendleri" olarak iki parca halinde gorsellestirir.
* **Hizli Islem Butonlari:** Urunler sekmesinde her urune ozel "Satis Yap" ve "Stok Artir" secenekleri sunar. Bu sayede kasada satilan bir urun, sadece adedi girilerek saniyeler icerisinde envanterden dusulebilir.

## Kurulum ve Calistirma

1. **Gereksinimlerin Yuklenmesi:**
Terminal uzerinden projenin calismasi icin gerekli kutuphaneleri yukleyin.
```bash
pip install fastapi uvicorn pydantic pandas prophet sqlite3
```