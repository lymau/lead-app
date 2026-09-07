from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from ..dependencies import get_db
from ..schemas.notification import SendEmailRequest
from ..services import notification_service

router = APIRouter(tags=["Notifications"])

@router.post("/send-email")
def send_email(request: SendEmailRequest):
    result = notification_service.send_email_notification(
        recipient_email=request.recipient_email,
        subject=request.subject,
        body_html=request.body_html
    )
    if result["status"] != 200:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["message"]
        )
    return result

@router.post("/inactive-reminder")
def trigger_inactive_reminder(
    target_email: str = Query("krisa.kurniawan@sisindokom.com", description="Target recipient email"),
    db: Session = Depends(get_db)
):
    result = notification_service.check_and_remind_inactive_presales(db, target_email=target_email)
    if result["status"] != 200:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["message"]
        )
    return result

@router.get("/registered-emails")
def get_registered_emails(db: Session = Depends(get_db)):
    return notification_service.get_registered_emails(db)
