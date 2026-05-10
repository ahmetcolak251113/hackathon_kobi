from decimal import Decimal

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.company import Company
from app.models.product import Product

COMPANIES = [
    {"name": "Organic Foods SME", "email": "info@organicfoods.com"},
    {"name": "Natural Market Ltd.", "email": "hello@naturalmarket.com"},
]

PRODUCTS = [
    {"name": "Kavanoz", "sku": "KAV-001", "stock_quantity": 500, "unit_price": Decimal("12.50")},
    {"name": "Zeytinyağı", "sku": "OIL-001", "stock_quantity": 200, "unit_price": Decimal("180.00")},
    {"name": "Un", "sku": "FLR-001", "stock_quantity": 1000, "unit_price": Decimal("35.00")},
    {"name": "Bal", "sku": "HNY-001", "stock_quantity": 150, "unit_price": Decimal("220.00")},
    {"name": "Sabun", "sku": "SOP-001", "stock_quantity": 300, "unit_price": Decimal("45.00")},
    {"name": "Kahve", "sku": "COF-001", "stock_quantity": 250, "unit_price": Decimal("95.00")},
    {"name": "Pirinç", "sku": "RIC-001", "stock_quantity": 600, "unit_price": Decimal("50.00")},
    {"name": "Makarna", "sku": "PST-001", "stock_quantity": 700, "unit_price": Decimal("28.00")},
]


def seed_companies(db: Session) -> None:
    for data in COMPANIES:
        exists = db.query(Company).filter(Company.email == data["email"]).first()
        if not exists:
            db.add(Company(**data))


def seed_products(db: Session) -> None:
    for data in PRODUCTS:
        exists = db.query(Product).filter(Product.sku == data["sku"]).first()
        if not exists:
            db.add(Product(**data))
            continue

        exists.name = data["name"]
        exists.stock_quantity = data["stock_quantity"]
        exists.unit_price = data["unit_price"]
        exists.is_active = True


def run_seed() -> None:
    db = SessionLocal()
    try:
        seed_companies(db)
        seed_products(db)
        db.commit()
        print("Seed completed successfully.")
    except Exception as exc:
        db.rollback()
        print(f"Seed failed: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
