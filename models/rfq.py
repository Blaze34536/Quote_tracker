from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date
from uuid import UUID

class parts_details(BaseModel):
    id: Optional[UUID] = None
    rfq_id: Optional[UUID] = None 
    rfq_part_no: str
    quoted_part_no: str
    supplier: Optional[str] = None
    date_code: Optional[str] = None
    rfq_qty: int = Field(..., ge=0) # Must be greater or equal to 0
    quoted_qty: int = Field(..., ge=0)
    make: Optional[str] = None
    lead_time: Optional[str] = None
    unit_price_usd: float
    exchange_rate: float
    unit_price_inr: float
    remarks: Optional[str] = None

class RFQ_Tracker(BaseModel):
    id: Optional[UUID] = None
    rfq_no: str
    rfq_date: date = Field(default_factory=date.today)
    company_name: str
    sales_person: str
    customer_name: str
    status: str = "Draft"
    
    items: List[parts_details] = [] 

    class Config:
        from_attributes = True