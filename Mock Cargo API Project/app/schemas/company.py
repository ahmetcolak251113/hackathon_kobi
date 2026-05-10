from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class CompanyCreate(BaseModel):
    name: str
    email: EmailStr


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    api_key: str
    created_at: datetime
