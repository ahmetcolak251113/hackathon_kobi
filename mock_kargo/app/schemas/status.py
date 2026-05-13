from datetime import datetime

from pydantic import BaseModel


class ShipmentHistoryResponse(BaseModel):
    status: str
    description: str
    location: str
    visible_at: datetime
