from datetime import datetime, timedelta, timezone
import random
import re

from sqlalchemy.orm import Session

from app.config import settings
from app.core.status_flow import DELAY_REASONS, STATUS_FLOW
from app.core.tracking_code import generate_tracking_code
from app.models.shipment import Shipment
from app.models.shipment_item import ShipmentItem
from app.models.shipment_status_history import ShipmentStatusHistory
from app.schemas.shipment import ShipmentCreate, ShipmentCreateResponse, ShipmentListResponse
from app.services.stock_service import get_products_for_items, validate_and_decrease_stock


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_phone_number(phone_number: str) -> str:
    return re.sub(r"\D+", "", phone_number)


def create_shipment(db: Session, payload: ShipmentCreate) -> ShipmentCreateResponse:
    products_map = get_products_for_items(db, payload.items)
    validate_and_decrease_stock(products_map, payload.items)

    min_delay = min(settings.min_delay_seconds, settings.max_delay_seconds)
    max_delay = max(settings.min_delay_seconds, settings.max_delay_seconds)
    is_delayed = random.random() < settings.delay_probability
    delay_seconds = random.randint(min_delay, max_delay) if is_delayed else None
    delay_reason = random.choice(DELAY_REASONS) if is_delayed else None

    estimated_delivery = utc_now() + timedelta(hours=3)
    if delay_seconds is not None:
        estimated_delivery += timedelta(seconds=delay_seconds)

    shipment = Shipment(
        company_id=None,
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        delivery_address=payload.delivery_address,
        tracking_code="PENDING",
        current_status="created",
        estimated_delivery=estimated_delivery,
        is_delayed=is_delayed,
        delay_reason=delay_reason,
        delay_seconds=delay_seconds,
    )
    db.add(shipment)
    db.flush()

    shipment.tracking_code = generate_tracking_code(shipment.created_at, shipment.id)

    for item in payload.items:
        if item.product_id is not None:
            product = products_map[item.product_id]
            db.add(
                ShipmentItem(
                    shipment_id=shipment.id,
                    product_id=product.id,
                    quantity=item.quantity,
                    unit_price=product.unit_price,
                )
            )
        else:
            db.add(
                ShipmentItem(
                    shipment_id=shipment.id,
                    product_id=None,
                    custom_product_name=item.custom_product_name,
                    quantity=item.quantity,
                    unit_price=None,
                )
            )

    delayed_threshold_statuses = {"out_for_delivery", "delivered"}
    delay_delta = timedelta(seconds=delay_seconds) if delay_seconds is not None else timedelta(seconds=0)

    for status, description, location, offset in STATUS_FLOW:
        visible_at = shipment.created_at + offset
        if is_delayed and status in delayed_threshold_statuses:
            visible_at += delay_delta

        db.add(
            ShipmentStatusHistory(
                shipment_id=shipment.id,
                status=status,
                description=description,
                location=location,
                visible_at=visible_at,
            )
        )

    if is_delayed and delay_reason:
        db.add(
            ShipmentStatusHistory(
                shipment_id=shipment.id,
                status="delayed",
                description=delay_reason,
                location="Transfer Merkezi",
                visible_at=shipment.created_at + timedelta(seconds=80),
            )
        )

    db.commit()
    db.refresh(shipment)

    return ShipmentCreateResponse(
        shipment_id=shipment.id,
        tracking_code=shipment.tracking_code,
        status=shipment.current_status,
        estimated_delivery=shipment.estimated_delivery,
    )


def list_company_shipments(
    db: Session,
    company_id: int | None = None,
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[ShipmentListResponse]:
    query = db.query(Shipment)
    if company_id is not None:
        query = query.filter(Shipment.company_id == company_id)
    if status:
        query = query.filter(Shipment.current_status == status)

    shipments = (
        query.order_by(Shipment.created_at.desc())
        .offset(max(offset, 0))
        .limit(min(max(limit, 1), 100))
        .all()
    )

    return [ShipmentListResponse.model_validate(shipment) for shipment in shipments]


def list_shipments_by_phone(db: Session, customer_phone: str) -> list[ShipmentListResponse]:
    normalized_target = normalize_phone_number(customer_phone)

    shipments = (
        db.query(Shipment)
        .order_by(Shipment.created_at.desc())
        .all()
    )

    matching_shipments = [
        shipment
        for shipment in shipments
        if normalize_phone_number(shipment.customer_phone) == normalized_target
    ]

    return [ShipmentListResponse.model_validate(shipment) for shipment in matching_shipments]
