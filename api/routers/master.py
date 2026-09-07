from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..dependencies import get_db
from ..schemas.master import AddCompanyRequest, AddDistributorRequest
from ..services import master_service

router = APIRouter(tags=["Master Data"])

@router.get("/presales")
def get_presales(db: Session = Depends(get_db)):
    return master_service.get_master_data(db, "getPresales")

@router.get("/pam-mapping")
def get_pam_mapping(db: Session = Depends(get_db)):
    return master_service.get_master_data(db, "getPAMMapping")

@router.get("/brands")
def get_brands(db: Session = Depends(get_db)):
    return master_service.get_master_data(db, "getBrands")

@router.get("/pillars")
def get_pillars(db: Session = Depends(get_db)):
    return master_service.get_master_data(db, "getPillars")

@router.get("/stages")
def get_stages(db: Session = Depends(get_db)):
    return master_service.get_master_data(db, "getPresalesStages")

@router.get("/sales-groups")
def get_sales_groups(db: Session = Depends(get_db)):
    return master_service.get_master_data(db, "getSalesGroups")

@router.get("/sales-names")
def get_sales_names(db: Session = Depends(get_db)):
    return master_service.get_master_data(db, "getSalesNames")

@router.get("/responsibles")
def get_responsibles(db: Session = Depends(get_db)):
    return master_service.get_master_data(db, "getResponsibles")

@router.get("/companies")
def get_companies(db: Session = Depends(get_db)):
    return master_service.get_master_data(db, "getCompanies")

@router.get("/distributors")
def get_distributors(db: Session = Depends(get_db)):
    return master_service.get_master_data(db, "getDistributors")

@router.get("/opportunities")
def get_opportunities(db: Session = Depends(get_db)):
    return master_service.get_master_data(db, "getOpportunities")

@router.get("/activity-log")
def get_activity_log(db: Session = Depends(get_db)):
    return master_service.get_master_data(db, "getActivityLog")

@router.post("/companies")
def add_company(request: AddCompanyRequest, db: Session = Depends(get_db)):
    result = master_service.add_master_company(db, request.company_name, request.vertical_industry)
    if result["status"] != 200:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result["message"])
    return result

@router.post("/distributors")
def add_distributor(request: AddDistributorRequest, db: Session = Depends(get_db)):
    result = master_service.add_master_distributor(db, request.distributor_name)
    if result["status"] == 400:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["message"])
    elif result["status"] != 200:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result["message"])
    return result
