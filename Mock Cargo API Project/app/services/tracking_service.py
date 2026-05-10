from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.shipment import Shipment
from app.models.shipment_status_history import ShipmentStatusHistory
from app.schemas.shipment import ShipmentTrackingResponse
from app.schemas.status import ShipmentHistoryResponse


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_shipment_or_404(db: Session, tracking_code: str) -> Shipment:
    shipment = db.query(Shipment).filter(Shipment.tracking_code == tracking_code).first()
    if not shipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")
    return shipment


def resolve_visible_status(db: Session, shipment_id: int) -> ShipmentStatusHistory | None:
    return (
        db.query(ShipmentStatusHistory)
        .filter(
            ShipmentStatusHistory.shipment_id == shipment_id,
            ShipmentStatusHistory.visible_at <= utc_now(),
        )
        .order_by(ShipmentStatusHistory.visible_at.desc())
        .first()
    )


def get_tracking_response(db: Session, tracking_code: str) -> ShipmentTrackingResponse:
    shipment = get_shipment_or_404(db, tracking_code)
    latest_status = resolve_visible_status(db, shipment.id)

    if latest_status and shipment.current_status != latest_status.status:
        shipment.current_status = latest_status.status
        db.commit()
        db.refresh(shipment)

    status_text = latest_status.description if latest_status else "Kargo kaydı oluşturuldu."
    location = latest_status.location if latest_status else "Ana Depo"
    status_name = latest_status.status if latest_status else shipment.current_status

    return ShipmentTrackingResponse(
        tracking_code=shipment.tracking_code,
        customer_name=shipment.customer_name,
        status=status_name,
        status_text=status_text,
        location=location,
        estimated_delivery=shipment.estimated_delivery,
        is_delayed=shipment.is_delayed,
        delay_reason=shipment.delay_reason,
        delay_seconds=shipment.delay_seconds,
    )


def get_visible_history(db: Session, tracking_code: str) -> list[ShipmentHistoryResponse]:
    shipment = get_shipment_or_404(db, tracking_code)

    rows = (
        db.query(ShipmentStatusHistory)
        .filter(
            ShipmentStatusHistory.shipment_id == shipment.id,
            ShipmentStatusHistory.visible_at <= utc_now(),
        )
        .order_by(ShipmentStatusHistory.visible_at.asc())
        .all()
    )

    return [
        ShipmentHistoryResponse(
            status=row.status,
            description=row.description,
            location=row.location,
            visible_at=row.visible_at,
        )
        for row in rows
    ]
