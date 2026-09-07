from pydantic import BaseModel

class AddCompanyRequest(BaseModel):
    company_name: str
    vertical_industry: str

class AddDistributorRequest(BaseModel):
    distributor_name: str
