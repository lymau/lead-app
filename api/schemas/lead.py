from datetime import date
from typing import Optional, List, Union
from pydantic import BaseModel

class ProductLine(BaseModel):
    pillar: str
    solution: str
    service: str
    pillar_product: Optional[str] = None
    solution_product: Optional[str] = None
    brand: Optional[str] = None
    channel: Optional[str] = None
    distributor_name: Optional[str] = None
    cost: Optional[float] = 0.0
    notes: Optional[str] = ""

class CreateOpportunityRequest(BaseModel):
    # Parent data
    presales_name: str
    salesgroup_id: str
    sales_name: str
    responsible_name: str
    opportunity_name: str
    start_date: Union[date, str]
    company_name: str
    vertical_industry: str
    stage: Optional[str] = "Open"
    route_to_market: Optional[str] = "Direct"
    # Product lines
    product_lines: List[ProductLine]

class UpdateLeadRequest(BaseModel):
    uid: str
    user: str
    cost: Optional[float] = None
    notes: Optional[str] = None

class UpdateFullOpportunityRequest(BaseModel):
    uid: str
    user: str
    salesgroup_id: str
    sales_name: str
    responsible_name: str
    pillar: str
    pillar_product: Optional[str] = None
    solution: str
    solution_product: Optional[str] = None
    service: str
    brand: Optional[str] = None
    company_name: str
    vertical_industry: str
    distributor_name: Optional[str] = None
    start_date: Union[date, str]
    route_to_market: str

class UpdateStageRequest(BaseModel):
    opportunity_id: str
    new_stage: str
    user_actor: str
    po_boq_link: Optional[str] = None
    project_id: Optional[str] = None
