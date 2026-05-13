# 🤖 KOBI WhatsApp Customer Bot

KOBİ'ler için WhatsApp tabanlı müşteri asistanı. Müşteri mesajları webhook üzerinden alınır, akış Python koduyla yönetilir ve LLM yalnızca gerekli metin yorumlama/özetleme adımlarında kullanılır.

## 🎯 Özellikler

- ✅ **WhatsApp Entegrasyonu**: Meta WhatsApp Business API ile mesaj alma/gönderme
- ✅ **LLM Yardımcı Katmanı**: Sadece intent çıkarma ve metin özetleme için kullanılır
- ✅ **Ürün Sorgusu**: KOBI veritabanından stok ve fiyat bilgisi
- ✅ **Kargo Takibi**: Mack Kargo API'sı ile teslimat durumu
- ✅ **Modular Tasarım**: Kolay genişletme ve bakım

## 🏗️ Sistem Mimarisi

```
WhatsApp Message
       ↓
   Webhook (/webhook)
       ↓
   Message Processing
       ↓
   Gemini LLM (with Tool Calling)
       ↓
   ┌─────────────────────────────┐
   ↓              ↓              ↓
KOBI DB   Mack Kargo API   Other Tools
   ↓              ↓              ↓
   └─────────────────────────────┘
       ↓
   Response Generation
       ↓
   WhatsApp API
       ↓
   Mesaj Gönderme
```

## 📁 Dosya Yapısı

```
KOBİ Customer Whatsapp Bot Project/
├── whatsapp_bot.py          # Ana bot uygulaması
├── config.py                # Konfigürasyon yönetimi
├── prompts.py               # WhatsApp LLM prompt templates
├── database.py              # Veritabanı işlemleri (placeholder)
├── api_clients.py           # Harici API clients
├── requirements.txt         # Python bağımlılıkları
├── .env                     # Environment değişkenleri
└── README.md                # Bu dosya
```

## 🚀 Kurulum

### 1. Bağımlılıkları Yükle

```bash
# Virtual environment oluştur (önerilir)
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# Bağımlılıkları yükle
pip install -r requirements.txt
```

### 2. Environment Ayarları

`.env.template` dosyasından `.env` dosyası oluştur:

```bash
# Windows
copy .env.template .env

# macOS/Linux
cp .env.template .env
```

`.env` dosyasını doldur:

```env
# Mevcut API Keys (Zaten var)
GEMINI_API_KEY=your_key_here
WHATSAPP_API_TOKEN=your_token_here
WHATSAPP_PHONE_ID=your_phone_id_here

# Aşağıdakiler SENDE SOKILACAKlar (Kullanıcı sağlayacak)
KOBI_API_BASE_URL=http://your-backend:3000
KOBI_API_KEY=your_api_key_here
DATABASE_URL=postgresql://user:pass@localhost:5432/kobi_db
MACK_KARGO_API_URL=https://api.mackkargo.com
MACK_KARGO_API_KEY=your_mack_key_here
```

## 🔧 Konfigürasyon

### Config.py

Merkezi konfigürasyon:

```python
from config import Config

# Tüm ayarlar
print(Config.GEMINI_MODEL)  # "gemini-2.0-flash"
print(Config.WHATSAPP_PHONE_ID)
print(Config.KOBI_API_BASE_URL)
```

### LLM Model Seçimi

`config.py`'da GEMINI_MODEL değerini değiştir:

```python
GEMINI_MODEL = "gemini-2.0-flash"  # En hızlı
# veya
GEMINI_MODEL = "gemini-1.5-pro"     # Daha güçlü
# veya
GEMINI_MODEL = "gemini-2.5-flash"   # Yeni model
```

## 📡 API Bağlantıları

### 1. KOBI Backend API (Kullanıcı Sağlayacak)

Endpoints:

```
POST /api/products/search
  Body: {"kobi_id": "123", "product_name": "iPhone"}
  Response: {"product": {...}}

GET /api/customers/{phone}/kobis
  Response: {"kobis": [{...}]}

POST /api/orders/create
  Body: {"kobi_id": "123", "customer_phone": "5551234567", "products": [...]}
```

### 2. Mack Kargo API (Kullanıcı Sağlayacak)

```
GET /api/shipment/status?phone_number=5551234567
  Headers: {"Authorization": "Bearer API_KEY"}
  Response: {"status": "in_transit", "current_location": "..."}

GET /api/tracking/{tracking_number}
  Response: {"status": "delivered", ...}
```

### 3. Veritabanı (Kullanıcı Sağlayacak)

`database.py` dosyasındaki `_init_connection()` metodunu doldur:

```python
# PostgreSQL örneği
import psycopg2
self.connection = psycopg2.connect(DB_URL)

# veya MySQL
import pymysql
self.connection = pymysql.connect(host=DB_HOST, user=DB_USER, ...)
```

Gerekli Tablolar:

```sql
-- KOBI'ler
CREATE TABLE kobis (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255),
    phone VARCHAR(20),
    email VARCHAR(255),
    address TEXT
);

-- Ürünler
CREATE TABLE products (
    id VARCHAR(50) PRIMARY KEY,
    kobi_id VARCHAR(50) REFERENCES kobis(id),
    name VARCHAR(255),
    price DECIMAL(10, 2),
    stock_quantity INT,
    description TEXT
);

-- Müşteriler
CREATE TABLE customers (
    id VARCHAR(50) PRIMARY KEY,
    phone VARCHAR(20) UNIQUE,
    name VARCHAR(255),
    email VARCHAR(255)
);

-- Müşteri-KOBI İlişkisi
CREATE TABLE customer_kobi (
    customer_id VARCHAR(50) REFERENCES customers(id),
    kobi_id VARCHAR(50) REFERENCES kobis(id),
    PRIMARY KEY (customer_id, kobi_id)
);

-- Siparişler/Kargolar
CREATE TABLE shipments (
    id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50) REFERENCES customers(id),
    kobi_id VARCHAR(50) REFERENCES kobis(id),
    tracking_number VARCHAR(50),
    status VARCHAR(50),
    created_at TIMESTAMP,
    estimated_delivery DATE
);
```

## ▶️ Çalıştırma

### Geliştirme Modu

```bash
# Config.py'ı kontrol et
python config.py

# Bot'u başlat
python whatsapp_bot.py

# Flask sunucusu http://localhost:5000'de çalışacak
```

### WhatsApp Webhook Testi

```bash
# Webhook verification (local test)
curl "http://localhost:5000/webhook?hub.verify_token=test_token&hub.challenge=test"

# Mesaj gönderme (test)
curl -X POST http://localhost:5000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "object": "whatsapp_business_account",
    "entry": [{
      "changes": [{
        "value": {
          "messages": [{
            "from": "5551234567",
            "type": "text",
            "text": {"body": "Merhaba, iPhone var mı?"}
          }]
        }
      }]
    }]
  }'
```

### Doğrulama

```bash
# Bot'u başlat
python whatsapp_bot.py

# Webhook sağlığını kontrol et
curl http://localhost:5000/health
```

## 🛠️ LLM Rolü

LLM yalnızca bu durumlarda devreye girer:

### Kullanım Alanları

- Serbest metinden intent çıkarma
- Sipariş mesajından ürün ve adet çıkarma
- Ürün API cevabını sade Türkçe ile açıklama
- Kargo API cevabını sade Türkçe ile açıklama

## 💬 Örnek Konuşmalar

### Ürün Sorgusu
```
👤 Müşteri: iPhone 15 var mı? Kaç tane kaldı?
🤖 LLM: get_product_info çağrısı yapılıyor...
📊 DB: iPhone 15, ₺25,000, 10 adet
💬 Bot: Evet, iPhone 15 stoklarda var! 
        Fiyat: ₺25,000 - Kalan: 10 adet
```

### Kargo Sorgusu
```
👤 Müşteri: Siparişimin durumu nedir?
🤖 LLM: get_shipment_status çağrısı yapılıyor...
📦 Kargo: MACK123456, İstanbul'da, Teslim: 15.05
💬 Bot: Siparişiniz İstanbul'da. 
        Tahmini teslim: 15 Mayıs
```

## 🔐 Güvenlik Önerileri

1. **API Keys**: `.env` dosyasını asla commit etme
   ```bash
   echo ".env" >> .gitignore
   ```

2. **HTTPS**: Production'da HTTPS kullan

3. **Rate Limiting**: `config.py`'da ayarla
   ```python
   RATE_LIMIT_REQUESTS_PER_MINUTE = 30
   ```

4. **Input Validation**: Her request'i doğrula

5. **Logging**: Sensitive verileri loglama
   ```python
   # API KEY'i log etme!
   logger.info(f"Phone: {phone}")  # ✅
   logger.info(f"Token: {token}")  # ❌
   ```

## 📊 Monitoring

### Health Check
```bash
curl http://localhost:5000/health
# {"status": "ok"}
```

### Logs
```bash
tail -f logs/bot.log
```

### Error Tracking
Exceptions otomatik olarak error tracking'e gönderiliyor.

## 🐛 Troubleshooting

### "GEMINI_API_KEY not found"
```bash
# .env dosyasını kontrol et
cat .env | grep GEMINI_API_KEY

# veya set et
export GEMINI_API_KEY=your_key
```

### "Database connection error"
```python
# database.py'da _init_connection'ı doldur
# PostgreSQL/MySQL bağlantı string'ini kontrol et
```

### "WhatsApp webhook not responding"
```bash
# Verify token'ı kontrol et
echo $VERIFY_TOKEN

# Webhook URL'ini Meta Dashboard'da kaydet:
# https://your-domain.com/webhook
```

## 🚀 Production Deployment

### 1. Ortamı Hazırla

```bash
# Production config
export FLASK_ENV=production

# Güvenli anahtarlar oluştur
python -c "import secrets; print(secrets.token_hex(16))"
```

### 2. WSGI Server Kur

```bash
pip install gunicorn

# Çalıştır
gunicorn -w 4 -b 0.0.0.0:5000 whatsapp_bot:app
```

### 3. Reverse Proxy (Nginx)

```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
    }
    
    location /webhook {
        proxy_pass http://localhost:5000/webhook;
    }
}
```

### 4. Database Setup

```bash
# Migrations çalıştır
python -m alembic upgrade head

# Backup ayarla
pg_dump kobi_db > backup.sql
```

## 📚 Ekler

### Kullanışlı Links
- [Gemini API Docs](https://ai.google.dev/)
- [WhatsApp Business API](https://developers.facebook.com/docs/whatsapp/cloud-api/)
- [Mack Kargo API](https://www.mackkargo.com/api)

### Environment Variables Kontrolü

```bash
# Tüm required vars kontrol et
python -c "from config import validate_config; validate_config()"
```

## 📝 Lisans

Kullanıcı tarafından sağlanan.

## 📞 İletişim

Sorularınız için [destek](mailto:support@example.com) ile iletişime geçin.

---

**Not**: Bu proje için KOBI Backend API, Veritabanı ve Mack Kargo API bağlantılarını kullanıcı sağlayacaktır. Placeholder'lar `database.py` ve `api_clients.py` dosyalarında işaretlenmiştir.
