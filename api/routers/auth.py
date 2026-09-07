from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..dependencies import get_db
from ..schemas.auth import LoginRequest, LoginResponse, ChangePasswordRequest
from ..services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    result = auth_service.validate_presales_login(db, request.username, request.password)
    if result["status"] == 401:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result["message"]
        )
    elif result["status"] != 200:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("message", "Internal Server Error")
        )
    return result

@router.post("/change-password")
def change_password(request: ChangePasswordRequest, db: Session = Depends(get_db)):
    result = auth_service.change_user_password(db, request.username, request.new_password)
    if result["status"] != 200:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("message", "Failed to change password")
        )
    return result

@router.get("/users")
def get_users(db: Session = Depends(get_db)):
    return auth_service.get_presales_users_list(db)
