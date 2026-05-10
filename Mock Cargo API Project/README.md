# Mock Cargo API

A standalone mock cargo/logistics API built with FastAPI. It uses SQLite by default for local development and can be pointed at PostgreSQL for production.

This project simulates a cargo company service that can be integrated later with:
- another backend (e.g. SME/admin panel)
- a WhatsApp bot

It intentionally keeps authentication and tracking logic simple while preserving realistic API behavior.

## Why This Exists

This API provides a fake but realistic cargo workflow:
- SMEs can create shipments for customers using predefined Turkish product names.
- The system generates tracking codes.
- Customers or a WhatsApp bot can query current shipment status by tracking code.
- Status appears to change over time without workers (Celery/Redis/Kafka) by using a `visible_at` timeline.
- A configurable random delay simulation can add realistic delivery delays.

## Tech Stack

- Python 3.11+
- FastAPI
- SQLite for local development, PostgreSQL for production
- SQLAlchemy ORM
- Alembic migrations
- Pydantic schemas
- Uvicorn
- python-dotenv
- Docker + Docker Compose
- Optional minimal pytest setup in dependencies

## Project Structure

```text
mock-cargo-api/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── dependencies.py
│   ├── core/
│   │   ├── status_flow.py
│   │   └── tracking_code.py
│   ├── models/
│   │   ├── company.py
│   │   ├── product.py
│   │   ├── shipment.py
│   │   ├── shipment_item.py
│   │   └── shipment_status_history.py
│   ├── routers/
│   │   ├── companies.py
│   │   ├── products.py
│   │   └── shipments.py
│   ├── schemas/
│   │   ├── company.py
│   │   ├── product.py
│   │   ├── shipment.py
│   │   └── status.py
│   ├── services/
│   │   ├── shipment_service.py
│   │   ├── stock_service.py
│   │   └── tracking_service.py
│   └── seed.py
├── alembic/
│   ├── env.py
│   └── versions/
├── alembic.ini
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

## Visible Tracking Mechanism (No Worker Required)

When a shipment is created, all future statuses are inserted immediately into `shipment_status_history`.
Each status row has a `visible_at` value.

When `GET /shipments/{tracking_code}` is called:
1. API finds the latest history row where `visible_at <= now_utc`.
2. API uses that row as the current visible state.

This creates fake live tracking without background jobs.

## Random Delay Simulation

When a shipment is created, the API can randomly mark it as delayed.

- Delay probability is controlled by `DELAY_PROBABILITY` (default `0.35`).
- Delay duration is randomly selected between `MIN_DELAY_SECONDS` and `MAX_DELAY_SECONDS` (default `40-120`).
- If delayed, an extra `delayed` history event is inserted with a Turkish delay reason.
- `out_for_delivery` and `delivered` visibility times are pushed forward by `delay_seconds`.

## Status Flow

- created (0s)
- preparing (+20s)
- shipped (+40s)
- in_transit (+60s)
- out_for_delivery (+100s)
- delivered (+140s)

Delayed shipments add:
- delayed (+80s, location: Transfer Merkezi, description: Turkish delay reason)
- out_for_delivery and delivered are shifted by +delay_seconds

Turkish descriptions/locations:
- created: `Kargo kaydı oluşturuldu.` at `Ana Depo`
- preparing: `Ürünler kargoya hazırlanıyor.` at `Ana Depo`
- shipped: `Kargo depodan çıkış yaptı.` at `İstanbul Transfer Merkezi`
- in_transit: `Kargo transfer sürecinde.` at `Bölgesel Transfer Merkezi`
- out_for_delivery: `Kargo dağıtıma çıktı.` at `Yerel Dağıtım Şubesi`
- delivered: `Kargo teslim edildi.` at `Müşteri Adresi`

## Tracking Code Format

`KRG-YYYYMMDD-000001`

Example: `KRG-20260510-000041`

## Environment Variables

Copy `.env.example` to `.env` and adjust values if needed:

```env
# Local development defaults to SQLite. Override with a Postgres URL for production.
DATABASE_URL=sqlite:///./mock_cargo.db
APP_NAME=Mock Cargo API
DEBUG=True
DELAY_PROBABILITY=0.35
MIN_DELAY_SECONDS=40
MAX_DELAY_SECONDS=120
```

## Run Locally (Without Docker)

1. Create and activate virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Ensure a database is available. For local development the project defaults to SQLite (no extra DB install required). If you prefer Postgres locally, set `DATABASE_URL` to your Postgres URL and start the server.

4. Apply migrations:

```bash
alembic upgrade head
```

5. Seed data:

```bash
python -m app.seed
```

6. Run API:

```bash
uvicorn app.main:app --reload
```

API: `http://127.0.0.1:8000`
Docs: `http://127.0.0.1:8000/docs`

## Run With Docker Compose

1. Create `.env` from `.env.example`.
2. Start services:

```bash
docker compose up --build
```

3. Run migrations inside API container:

```bash
docker compose exec mock-cargo-api alembic upgrade head
```

4. Seed database:

```bash
docker compose exec mock-cargo-api python -m app.seed
```

## API Endpoints

### Health

```bash
curl http://127.0.0.1:8000/health
```

### Products

```bash
curl http://127.0.0.1:8000/products
curl http://127.0.0.1:8000/products/1
```

### Companies

Create:

```bash
curl -X POST http://127.0.0.1:8000/companies \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Organic Foods SME",
    "email": "info@organicfoods.com"
  }'
```

List:

```bash
curl http://127.0.0.1:8000/companies
```

### Create Shipment (Requires API Key)

```bash
curl -X POST http://127.0.0.1:8000/shipments \
  -H "Content-Type: application/json" \
  -H "X-API-Key: REPLACE_WITH_COMPANY_API_KEY" \
  -d '{
    "customer_name": "Ahmet Yılmaz",
    "customer_phone": "+905551112233",
    "delivery_address": "Kadıköy, İstanbul",
    "items": [
      {"product_id": 1, "quantity": 3},
      {"product_id": 2, "quantity": 1}
    ]
  }'
```

You can create shipments using demo products from the mock database or with custom product names.

Example using a demo product:

```json
{
  "customer_name": "Ahmet Yılmaz",
  "customer_phone": "+905551112233",
  "delivery_address": "Kadıköy, İstanbul",
  "items": [
    {"product_id": 1, "quantity": 2}
  ]
}
```

Example using custom products:

```json
{
  "customer_name": "Mehmet Demir",
  "customer_phone": "+905559998877",
  "delivery_address": "Beşiktaş, İstanbul",
  "items": [
    {"custom_product_name": "El Yapımı Lavanta Sabunu", "quantity": 1},
    {"custom_product_name": "Özel Hediye Paketi", "quantity": 1}
  ]
}
```

Mixed demo + custom example:

```json
{
  "customer_name": "Ayşe Kaya",
  "customer_phone": "+905551234567",
  "delivery_address": "Üsküdar, İstanbul",
  "items": [
    {"product_id": 2, "quantity": 1},
    {"custom_product_name": "KOBİ Özel Ürün Seti", "quantity": 1}
  ]
}
```

Example delayed tracking response:

```json
{
  "tracking_code": "KRG-20260510-000001",
  "customer_name": "Ahmet Yılmaz",
  "status": "in_transit",
  "status_text": "Kargo transfer sürecinde.",
  "location": "Bölgesel Transfer Merkezi",
  "estimated_delivery": "2026-05-10T15:30:00",
  "is_delayed": true,
  "delay_reason": "Yoğun yağmur nedeniyle teslimat gecikebilir.",
  "delay_seconds": 85
}
```

Example non-delayed tracking response:

```json
{
  "tracking_code": "KRG-20260510-000002",
  "customer_name": "Mehmet Demir",
  "status": "shipped",
  "status_text": "Kargo depodan çıkış yaptı.",
  "location": "İstanbul Transfer Merkezi",
  "estimated_delivery": "2026-05-10T15:30:00",
  "is_delayed": false,
  "delay_reason": null,
  "delay_seconds": null
}
```

### Public Tracking Endpoint

```bash
curl http://127.0.0.1:8000/shipments/KRG-20260510-000001
```

### Public Tracking History Endpoint

```bash
curl http://127.0.0.1:8000/shipments/KRG-20260510-000001/history
```

### List Company Shipments (Requires API Key)

```bash
curl "http://127.0.0.1:8000/shipments?status=in_transit&limit=20&offset=0" \
  -H "X-API-Key: REPLACE_WITH_COMPANY_API_KEY"
```

## Seeded Data

`python -m app.seed` inserts:
- 2 companies
- 8 products

Products:
- Kavanoz (KAV-001)
- Zeytinyağı (OIL-001)
- Un (FLR-001)
- Bal (HNY-001)
- Sabun (SOP-001)
- Kahve (COF-001)
- Pirinç (RIC-001)
- Makarna (PST-001)

## Integration Notes (Backend or WhatsApp Bot)

- This service is standalone and only exposes cargo API behavior.
- Another backend can store `tracking_code` and call:
  - `GET /shipments/{tracking_code}` for latest status
  - `GET /shipments/{tracking_code}/history` for visible timeline
- A WhatsApp bot can poll `GET /shipments/{tracking_code}` every 5 seconds to simulate live tracking updates.
- SME backend should store each company's `api_key` and send it as `X-API-Key` for protected endpoints.
