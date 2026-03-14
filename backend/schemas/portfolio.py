from pydantic import BaseModel
from datetime import date, datetime
from uuid import UUID
from typing import Optional

class HoldingCreate(BaseModel):
    symbol: str
    name: str
    asset_type: str
    buy_price: float
    quantity: float
    buy_date: date

class HoldingResponse(BaseModel):
    id: UUID
    user_id: str
    symbol: str
    name: str
    asset_type: str
    buy_price: float
    quantity: float
    buy_date: date
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
