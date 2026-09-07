from pydantic import BaseModel, EmailStr
from typing import Optional

class SendEmailRequest(BaseModel):
    recipient_email: str
    subject: str
    body_html: str
