# KOBİ Akıllı Yönetim Sistemi
### *Yapay Zeka Destekli, WhatsApp Entegrasyonlu KOBİ & Kooperatif Operasyon Platformu*

---

## Proje Hakkında

Bu proje, küçük ve orta ölçekli işletmelerin (KOBİ) ve kooperatiflerin **hem fiziksel mağaza hem de e-ticaret operasyonlarını tek bir akıllı panelden yönetmesini** sağlayan, yapay zeka destekli bir yönetim ve müşteri iletişim platformudur.

Proje üç bağımsız ama birbirine entegre çalışan modülden oluşmaktadır:

| Modül | Teknoloji | Durum |
|---|---|---|
| **KOBİ Yönetim Paneli** (Ana Backend + Frontend) | FastAPI + SQLite + Prophet ML |  Aktif |
| **WhatsApp Müşteri Botu** | Flask + Gemini AI + Meta Cloud API | ⚙️ Geliştiriliyor |
| **Mock Kargo API** | FastAPI + SQLAlchemy + SQLite/PostgreSQL |  Simüle Edildi |

> **Not:** Hava Durumu API'si ve Kargo API'si şu an simüle (mock) edilmektedir. Gerçek entegrasyon çalışmaları devam etmektedir.

---

##  Sistem Mimarisi

```
                  ┌─────────────────────────────────────────────┐
                  │           KOBİ YÖNETİM PANELİ              │
                  │  (index.html + app.js → FastAPI Backend)    │
                  └──────────────┬──────────────────────────────┘
                                 │
          ┌──────────────────────┼────────────────────────┐
          │                      │                        │
          ▼                      ▼                        ▼
  ┌──────────────┐    ┌─────────────────────┐   ┌───────────────────┐
  │  SQLite DB   │    │  Prophet ML Modülü  │   │  Gemini AI (LLM)  │
  │ (SME_DB.db)  │    │  (Satış Tahmini)    │   │  (Rapor & Taslak) │
  └──────────────┘    └─────────────────────┘   └───────────────────┘
          │
          ▼
  ┌──────────────────────────────────────────────────────────┐
  │                 WHATSAPP MÜŞTERİ BOTU                    │
  │     (Flask + Webhook → Intent Detection → Response)      │
  └───────────────────┬──────────────────────────────────────┘
                      │
         ┌────────────┴──────────────┐
         ▼                           ▼
  ┌─────────────┐          ┌────────────────────┐
  │  KOBI API   │          │  Mock Kargo API    │
  │  (Sipariş   │          │  (Takip & Durum    │
  │   Onayı)    │          │   Simülasyonu)     │
  └─────────────┘          └────────────────────┘
```

---

##  Proje Yapısı

```
HACKHATON/
│
├── README.md                          ← Bu dosya (Proje genel bakışı)
├── requirements.txt                   ← Tüm Python bağımlılıkları
│
├── Hackathon_project/                 ←  ANA MODÜL: KOBİ Yönetim Sistemi
│   ├── main.py                        ← FastAPI backend (tüm API endpoint'leri)
│   ├── index.html                     ← SPA Frontend (Bootstrap 5 tabanlı)
│   ├── app.js                         ← Frontend JavaScript mantığı
│   ├── requirements.txt
│   ├── DB/
│   │   └── SME_DB.db                  ← SQLite veritabanı
│   └── Statistics/
│       ├── prophet_statistics.py      ← Prophet ML: Satış tahmini
│       └── report.py                  ← Gemini ile rapor & taslak üretimi
│
├── KOBİ Customer Whatsapp Bot Project/  ←  WhatsApp Müşteri Botu
│   ├── whatsapp_bot.py               ← Flask webhook + intent işleme
│   ├── config.py                     ← Konfigürasyon yönetimi
│   ├── prompts.py                    ← LLM prompt şablonları
│   ├── database.py                   ← DB bağlantı katmanı (placeholder)
│   ├── api_clients.py                ← Harici API istemcileri
│   └── .env                          ← API anahtarları (git'e eklenmez)
│
└── Mock Cargo API Project/            ← Kargo Simülasyon Servisi
    ├── app/
    │   ├── main.py                   ← FastAPI uygulaması
    │   ├── routers/                  ← shipments, companies, products
    │   ├── models/                   ← SQLAlchemy modelleri
    │   ├── schemas/                  ← Pydantic şemaları
    │   ├── services/                 ← İş mantığı katmanı
    │   └── core/
    │       ├── status_flow.py        ← Kargo durum geçiş motoru
    │       └── tracking_code.py     ← Takip kodu üretici
    ├── alembic/                      ← DB migration'ları
    ├── Dockerfile
    └── docker-compose.yml
```

---

## Modül Detayları

### 1 KOBİ Yönetim Paneli (`Hackathon_project/`)

KOBİ sahibinin günlük tüm operasyonlarını yönettiği ana panel. FastAPI ile sunulan RESTful API, SQLite veritabanı ve Bootstrap 5 tabanlı tek sayfalı web arayüzünden oluşur.

####  Temel Özellikler

| Özellik | Açıklama |
|---|---|
| **Dashboard** | Toplam ürün, kritik stok, müşteri ve tedarikçi sayısı |
| **Stok Yönetimi** | Ürün ekleme, düzenleme, hızlı satış ve stok artırma |
| **Depo Yönetimi** | Hammadde/malzeme takibi, kritik eşik uyarıları |
| **Müşteri & Tedarikçi** | Tam CRUD işlemleri |
| **Kargo Takip** | Kargo durumu izleme ve gecikme uyarıları |
| **Sipariş Onay Sistemi** | WhatsApp'tan gelen siparişleri onaylama/reddetme |
| **Yapay Zeka Tahminleri** | Prophet ile 14 günlük satış tahmini |
| **Grafik Analizi** | Zaman serisi, pasta ve karşılaştırmalı grafikler |
| **AI Taslak Üretimi** | Tedarikçi mesajı, depo sipariş, kargo özür taslakları |
| **AI Rapor** | Gemini ile otomatik işletme raporu üretimi |
| **Hava Durumu Uyarısı** | Kargo gecikme riski bildirimi *(simüle)* |

####  Veritabanı Tabloları (SME_DB.db)

- `tedarikciler` — Tedarikçi bilgileri
- `urunler` — Ürün envanteri
- `depo_malzemeleri` — Hammadde/malzeme deposu
- `musteriler` — Müşteri kayıtları
- `kargo_takip` — Kargo durumları
- `stok_hareketleri` — Tüm satış & alım logları
- `siparis_onay` — WhatsApp'tan gelen onay bekleyen siparişler

####  Yapay Zeka Bileşenleri

- **Prophet ML**: 180 günlük geçmiş satış verisinden trend analizi ve 14 günlük tahmin
- **Gemini LLM**: Tedarikçi sipariş taslağı, depo alım mesajı, kargo gecikme özrü, genel işletme raporu üretimi

---

### 2️ WhatsApp Müşteri Botu (`KOBİ Customer Whatsapp Bot Project/`)

Müşterilerin WhatsApp üzerinden işletme ile iletişim kurmasını sağlayan akıllı bot.

####  Desteklenen Akışlar

```
Müşteri Mesajı → Intent Detection → İşlem → WhatsApp Cevabı

1. KARGO TAKİP:
   "KBT12345678 nerede?" → Takip no çıkar → Kargo API → Durum bildir

2. SİPARİŞ VERME:
   "2 adet kahve almak istiyorum" → Sipariş talebi oluştur
   → KOBİ API'ye gönder → KOBİ onayı bekle
   → Onaylanırsa: kargo kodu + bildirim
   → Reddedilirse: iptal bildirimi

3. SELAMLAMA:
   "Merhaba" → Karşılama menüsü göster
```

####  Bağlantı Noktaları

| Servis | Endpoint | Durum |
|---|---|---|
| Meta WhatsApp Cloud API | `graph.facebook.com/v18.0/.../messages` |  Entegre |
| KOBİ Yönetim API | `POST /api/siparis-onay/talep` |  Entegre |
| Mock Kargo API | `GET /shipments/{tracking_code}` |  Simüle |
| Gemini AI | `gemini-2.5-flash` modeli | Geliştiriliyor |

---

### 3️ Mock Kargo API (`Mock Cargo API Project/`)

Gerçek bir kargo şirketi API'sini simüle eden bağımsız servis. Gerçek entegrasyon yapılana kadar tüm sistemi ayakta tutan kargo altyapısıdır.

####  Kargo Durum Akışı

```
created (0s)
    ↓
preparing (+20s)
    ↓
shipped (+40s)
    ↓
in_transit (+60s)
    ↓  [%35 ihtimalle gecikme eklenir]
out_for_delivery (+100s)
    ↓
delivered (+140s)
```

####  Öne Çıkan Özellikler

- **Worker gerektirmez**: Tüm gelecek durum geçişleri `visible_at` timestamp'i ile önceden veritabanına yazılır
- **Gerçekçi gecikme simülasyonu**: Türkçe gecikme nedenleri, Türk lokasyonları
- **Takip kodu formatı**: `KRG-YYYYMMDD-XXXXXX`
- **Docker desteği**: `docker compose up` ile çalıştırılabilir

---

## Uçtan Uca Sipariş Akışı

```
1. Müşteri WhatsApp'tan sipariş yazar
        ↓
2. Bot intent'i algılar, sipariş özetini KOBİ API'ye gönderir
        ↓
3. KOBİ panelinde "Bekleyen Siparişler" bölümüne düşer
        ↓
4. KOBİ sahibi panelden ONAYLA veya REDDET'e basar
        ↓
5a. ONAYLA → Kargo kaydı otomatik oluşur
           → Müşteriye WhatsApp ile kargo kodu gönderilir
5b. REDDET → Müşteriye iptal bildirimi gönderilir
        ↓
6. Müşteri kargo kodunu WhatsApp'tan botla sorgulayabilir
        ↓
7. Bot Mock Kargo API'ye bağlanır, güncel durumu bildirir
```

---

##  Kurulum & Çalıştırma

### Genel Bağımlılıklar

```bash
# Kök dizinde
pip install -r requirements.txt
```

### KOBİ Yönetim Paneli

```bash
cd Hackathon_project/
uvicorn main:app --reload --port 8001
# → http://127.0.0.1:8001
```

### WhatsApp Botu

```bash
cd "KOBİ Customer Whatsapp Bot Project/"
# .env dosyasını düzenle (API anahtarlarını gir)
python whatsapp_bot.py
# → http://localhost:5000
```

### Mock Kargo API

```bash
cd "Mock Cargo API Project/"
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --port 8000
# → http://127.0.0.1:8000/docs
```

---

##  API Endpoint Özeti

### KOBİ Yönetim API (`port 8001`)

| Method | Endpoint | Açıklama |
|---|---|---|
| GET | `/api/ozet` | Dashboard özet verileri |
| GET | `/api/analiz/kritik-aksiyonlar` | Kritik stok & kargo uyarıları |
| GET | `/api/hava-durumu-uyarisi` | Hava durumu kargo riski *(simüle)* |
| GET | `/api/tahmin/genel` | Genel ciro tahmini (Prophet) |
| GET | `/api/tahmin/urunler` | Ürün bazlı satış tahmini |
| GET | `/api/ai-rapor` | Gemini ile işletme raporu |
| POST | `/api/hizli_satis` | Hızlı satış (stok düşümü) |
| GET/POST/PUT/DELETE | `/api/{tablo}` | Genel CRUD |
| POST | `/api/siparis-onay/talep` | Yeni sipariş talebi (Bot'tan) |
| GET | `/api/siparis-onay/bekleyenler` | Bekleyen siparişler (Panel) |
| POST | `/api/siparis-onay/{id}/onayla` | Sipariş onayla |
| POST | `/api/siparis-onay/{id}/reddet` | Sipariş reddet |

### Mock Kargo API (`port 8000`)

| Method | Endpoint | Açıklama |
|---|---|---|
| GET | `/shipments/{tracking_code}` | Kargo durumu sorgula |
| GET | `/shipments/{tracking_code}/history` | Durum geçmişi |
| POST | `/shipments` | Yeni kargo oluştur *(API Key gerekli)* |
| GET | `/companies` | Şirket listesi |
| GET | `/products` | Ürün listesi |

---

## Teknoloji Yığını

| Katman | Teknoloji |
|---|---|
| **Backend** | Python 3.11+, FastAPI, Flask |
| **Veritabanı** | SQLite (geliştirme), PostgreSQL (prodüksiyon) |
| **ORM / Migration** | SQLAlchemy, Alembic |
| **ML / Tahmin** | Meta Prophet, Pandas, NumPy |
| **AI / LLM** | Google Gemini 2.5 Flash (google-generativeai) |
| **Frontend** | HTML5, Bootstrap 5, Vanilla JS, Chart.js |
| **Mesajlaşma** | Meta WhatsApp Business Cloud API |
| **Konteyner** | Docker, Docker Compose |
| **Sunucu** | Uvicorn (FastAPI), Gunicorn (Flask prod) |
| **Test** | pytest |

---

## Yol Haritası (Gelecek Entegrasyonlar)

- [ ] Gerçek kargo firması API entegrasyonu (Mock → Canlı)
- [ ] Gerçek hava durumu API entegrasyonu (OpenWeather / Meteoblue)
- [ ] Gemini Function Calling ile WhatsApp botunun tam otomasyonu
- [ ] PostgreSQL'e geçiş (prodüksiyon ortamı)
- [ ] Çoklu KOBİ desteği (multi-tenant mimari)
- [ ] Mobil uygulama veya PWA desteği
- [ ] Sipariş geçmişi ve müşteri sadakat sistemi

---

##  Takım

Bu proje **Yapay Zeka ve Teknolojisi Akademisi Hackathon** kapsamında geliştirilmiştir.

- 1 Ahmet ÇOLAK
- 2 Barış UYUMAZ

---

