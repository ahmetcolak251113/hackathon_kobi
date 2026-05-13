from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.shipment import ShipmentCreate, ShipmentCreateResponse, ShipmentTrackingResponse
from app.schemas.status import ShipmentHistoryResponse
from app.services.shipment_service import create_shipment, list_shipments_by_phone
from app.services.tracking_service import get_tracking_response, get_visible_history

router = APIRouter()


@router.post("", response_model=ShipmentCreateResponse)
def create_shipment_endpoint(
    payload: ShipmentCreate,
    db: Session = Depends(get_db),
) -> ShipmentCreateResponse:
    return create_shipment(db=db, payload=payload)


@router.get("/by-phone/{customer_phone}", response_model=list[ShipmentTrackingResponse])
def get_shipments_by_phone(
    customer_phone: str = Path(..., description="Customer phone number"),
    db: Session = Depends(get_db),
) -> list[ShipmentTrackingResponse]:
    shipments = list_shipments_by_phone(db=db, customer_phone=customer_phone)
    return [get_tracking_response(db=db, tracking_code=shipment.tracking_code) for shipment in shipments]


@router.get("/{tracking_code}", response_model=ShipmentTrackingResponse)
def get_shipment_by_tracking_code(tracking_code: str, db: Session = Depends(get_db)) -> ShipmentTrackingResponse:
    return get_tracking_response(db=db, tracking_code=tracking_code)


@router.get("/{tracking_code}/history", response_model=list[ShipmentHistoryResponse])
def get_shipment_history(tracking_code: str, db: Session = Depends(get_db)) -> list[ShipmentHistoryResponse]:
    return get_visible_history(db=db, tracking_code=tracking_code)
