from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from ..dependencies import get_db
from ..schemas.lead import (
    CreateOpportunityRequest,
    UpdateLeadRequest,
    UpdateFullOpportunityRequest,
    UpdateStageRequest
)
from ..services import lead_service

router = APIRouter(tags=["Leads"])

@router.get("")
@router.get("/")
def get_leads(username: str = Query(..., description="Presales username untuk filter akses group"), db: Session = Depends(get_db)):
    result = lead_service.get_leads_by_group_logic(db, username)
    if result.get("status") == 403:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=result.get("message"))
    elif result.get("status") != 200:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result.get("message"))
    return result

@router.get("/activity-log")
def get_lead_activity_log(username: str = Query(..., description="Presales username"), db: Session = Depends(get_db)):
    return lead_service.get_activity_log_by_group(db, username)

@router.get("/opportunity/{opp_id}/summary")
def get_opportunity_summary(opp_id: str, db: Session = Depends(get_db)):
    result = lead_service.get_opportunity_summary(db, opp_id)
    if result.get("status") == 404:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result.get("message"))
    elif result.get("status") != 200:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result.get("message"))
    return result

@router.post("")
@router.post("/")
def create_opportunity(request: CreateOpportunityRequest, db: Session = Depends(get_db)):
    result = lead_service.add_multi_line_opportunity(db, request.model_dump())
    if result.get("status") != 200:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result.get("message"))
    return result

@router.put("/cost-notes")
def update_cost_notes(request: UpdateLeadRequest, db: Session = Depends(get_db)):
    result = lead_service.update_lead(db, request.model_dump())
    if result.get("status") == 404:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result.get("message"))
    elif result.get("status") != 200:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result.get("message"))
    return result

@router.put("/full")
def update_full_opportunity(request: UpdateFullOpportunityRequest, db: Session = Depends(get_db)):
    result = lead_service.update_full_opportunity(db, request.model_dump())
    if result.get("status") == 404:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result.get("message"))
    elif result.get("status") != 200:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result.get("message"))
    return result

@router.put("/stage")
def update_stage(request: UpdateStageRequest, db: Session = Depends(get_db)):
    result = lead_service.update_opportunity_stage(
        db=db,
        opp_id=request.opportunity_id,
        new_stage=request.new_stage,
        user_actor=request.user_actor,
        po_boq_link=request.po_boq_link,
        project_id=request.project_id
    )
    if result.get("status") == 404:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result.get("message"))
    elif result.get("status") != 200:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result.get("message"))
    return result

@router.get("/{uid}")
def get_lead_by_uid(uid: str, db: Session = Depends(get_db)):
    result = lead_service.get_lead_by_uid(db, uid)
    if result.get("status") == 404:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result.get("message"))
    elif result.get("status") != 200:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result.get("message"))
    return result

@router.delete("/{uid}")
def delete_lead(uid: str, user_actor: str = Query(..., description="Username peminta penghapusan"), db: Session = Depends(get_db)):
    result = lead_service.delete_opportunity_by_uid(db, uid, user_actor)
    if result.get("status") == 404:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result.get("message"))
    elif result.get("status") != 200:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result.get("message"))
    return result
