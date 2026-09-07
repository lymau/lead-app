from pydantic import BaseModel
from typing import Optional, Any

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    status: int
    data: Optional[Any] = None
    message: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    username: str
    new_password: str
