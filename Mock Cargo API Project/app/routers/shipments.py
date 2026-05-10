from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_company
from app.models.company import Company
from app.schemas.shipment import ShipmentCreate, ShipmentCreateResponse, ShipmentListResponse, ShipmentTrackingResponse
from app.schemas.status import ShipmentHistoryResponse
from app.services.shipment_service import create_shipment, list_company_shipments
from app.services.tracking_service import get_tracking_response, get_visible_history

router = APIRouter()


@router.post("", response_model=ShipmentCreateResponse)
def create_shipment_endpoint(
    payload: ShipmentCreate,
    db: Session = Depends(get_db),
    company: Company = Depends(get_current_company),
) -> ShipmentCreateResponse:
    return create_shipment(db=db, company=company, payload=payload)


@router.get("", response_model=list[ShipmentListResponse])
def list_shipments_endpoint(
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    company: Company = Depends(get_current_company),
) -> list[ShipmentListResponse]:
    return list_company_shipments(db=db, company=company, status=status, limit=limit, offset=offset)


@router.get("/{tracking_code}", response_model=ShipmentTrackingResponse)
def get_shipment_by_tracking_code(tracking_code: str, db: Session = Depends(get_db)) -> ShipmentTrackingResponse:
    return get_tracking_response(db=db, tracking_code=tracking_code)


@router.get("/{tracking_code}/history", response_model=list[ShipmentHistoryResponse])
def get_shipment_history(tracking_code: str, db: Session = Depends(get_db)) -> list[ShipmentHistoryResponse]:
    return get_visible_history(db=db, tracking_code=tracking_code)
