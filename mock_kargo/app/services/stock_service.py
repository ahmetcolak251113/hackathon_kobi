from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.product import Product
from app.schemas.shipment import ShipmentItemCreate


def get_products_for_items(db: Session, items: list[ShipmentItemCreate]) -> dict[int, Product]:
    # Only collect product_ids for items that specify a demo product
    product_ids = {item.product_id for item in items if item.product_id is not None}
    if not product_ids:
        return {}

    products = db.query(Product).filter(Product.id.in_(product_ids), Product.is_active.is_(True)).all()

    products_map = {product.id: product for product in products}
    missing_ids = sorted(product_ids - set(products_map.keys()))
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Products not found or inactive: {missing_ids}",
        )

    return products_map


def validate_and_decrease_stock(products: dict[int, Product], items: list[ShipmentItemCreate]) -> None:
    # Only validate/decrease stock for items that reference a demo product
    for item in items:
        if item.product_id is None:
            continue
        product = products.get(item.product_id)
        if product is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Product id {item.product_id} not found")
        if product.stock_quantity < item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for product {product.name} (id={product.id})",
            )

    for item in items:
        if item.product_id is None:
            continue
        products[item.product_id].stock_quantity -= item.quantity
