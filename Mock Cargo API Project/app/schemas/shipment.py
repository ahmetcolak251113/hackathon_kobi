from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ShipmentItemCreate(BaseModel):
    product_id: int | None = None
    custom_product_name: str | None = None
    quantity: int = Field(gt=0)

    @model_validator(mode="after")
    def check_either_product_or_custom(self):
        if (self.product_id is None and (self.custom_product_name is None or self.custom_product_name == "")):
            raise ValueError("Either product_id or custom_product_name must be provided")
        if self.product_id is not None and self.custom_product_name:
            raise ValueError("Provide only one of product_id or custom_product_name, not both")
        return self


class ShipmentCreate(BaseModel):
    customer_name: str
    customer_phone: str
    delivery_address: str
    items: list[ShipmentItemCreate] = Field(min_length=1)


class ShipmentCreateResponse(BaseModel):
    shipment_id: int
    tracking_code: str
    status: str
    estimated_delivery: datetime


class ShipmentTrackingResponse(BaseModel):
    tracking_code: str
    customer_name: str
    status: str
    status_text: str
    location: str
    estimated_delivery: datetime
    is_delayed: bool
    delay_reason: str | None
    delay_seconds: int | None


class ShipmentItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int | None
    product_name: str | None = None
    custom_product_name: str | None = None
    quantity: int
    unit_price: Decimal | None

    # provide a convenience property for Pydantic models built from SQLAlchemy objects
    @property
    def product_name(self) -> str | None:  # type: ignore[override]
        # if the underlying model has a product attribute, return its name
        product = getattr(self, "product", None)
        if product:
            return getattr(product, "name", None)
        return None


class ShipmentListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tracking_code: str
    customer_name: str
    customer_phone: str
    delivery_address: str
    current_status: str
    estimated_delivery: datetime
    is_delayed: bool
    delay_reason: str | None
    delay_seconds: int | None
    created_at: datetime
    updated_at: datetime
