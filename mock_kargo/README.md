# Mock Cargo API

Mock cargo/logistics API built with FastAPI. Uses SQLite locally, PostgreSQL for production.

## Tech Stack

- Python 3.11+, FastAPI, SQLAlchemy, Alembic, Pydantic
- SQLite (local), PostgreSQL (production)
- Docker + Docker Compose

## Project Structure

```
app/
├── main.py, config.py, database.py
├── core/ (status_flow, tracking_code)
├── models/ (shipment, shipment_item, shipment_status_history, company, product)
├── routers/ (shipments)
├── schemas/ (shipment, status, company, product)
├── services/ (shipment_service, tracking_service, stock_service)
└── seed.py
alembic/ (migrations)
```

## How It Works

**Visible Timeline:** Statuses are pre-inserted with `visible_at` timestamps. Latest visible status at query time is returned (no background workers).

**Delay Simulation:** Configurable probability (default `0.35`) to randomly delay shipment. Delay duration: `40-120s` (configurable). Shifts delivery times accordingly.

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

```env
DATABASE_URL=sqlite:///./mock_cargo.db
APP_NAME=Mock Cargo API
DEBUG=True
DELAY_PROBABILITY=0.35
MIN_DELAY_SECONDS=40
MAX_DELAY_SECONDS=120
```

## Run Locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

API: http://127.0.0.1:3000 | Docs: http://127.0.0.1:3000/docs

## Docker

```bash
docker compose up --build
docker compose exec mock-cargo-api alembic upgrade head
docker compose exec mock-cargo-api python -m app.seed
```

## API Endpoints

### Health

```bash
curl http://127.0.0.1:3000/health
```

### Create Shipment

```bash
curl -X POST http://127.0.0.1:3000/shipments \
  -H "Content-Type: application/json" \
  -d '{"customer_name": "Ahmet Yılmaz", "customer_phone": "+905551112233", "delivery_address": "Kadıköy, İstanbul", "items": [{"product_id": 1, "quantity": 2}]}'
```

Demo products: `{"product_id": 1, "quantity": 2}`
Custom products: `{"custom_product_name": "El Yapımı Lavanta Sabunu", "quantity": 1}`
Mixed: Both in same items list

### Tracking Response

```json
{
  "tracking_code": "KRG-20260510-000001",
  "customer_name": "Ahmet Yılmaz",
  "customer_phone": "+905551112233",
  "status": "in_transit",
  "status_text": "Kargo transfer sürecinde.",
  "location": "Bölgesel Transfer Merkezi",
  "estimated_delivery": "2026-05-10T15:30:00",
  "is_delayed": true,
  "delay_reason": "Yoğun yağmur nedeniyle teslimat gecikebilir.",
  "delay_seconds": 85,
  "items": [{"product_name": "Kavanoz", "quantity": 3}, {"product_name": "Zeytinyağı", "quantity": 1}]
}
```

### Other Endpoints

```bash
# Get tracking
curl http://127.0.0.1:3000/shipments/KRG-20260510-000001

# Search by phone
curl http://127.0.0.1:3000/shipments/by-phone/+905551112233

# Tracking history
curl http://127.0.0.1:3000/shipments/KRG-20260510-000001/history
```

## Seeded Data

Products: Kavanoz, Zeytinyağı, Un, Bal, Sabun, Kahve, Pirinç, Makarna
