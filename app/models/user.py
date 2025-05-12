from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


class UserIn(BaseModel):
    email: EmailStr
    password: str
    full_name: str = Field(..., min_length=1)


class UserOut(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    created_at: datetime


class UserUpdate(BaseModel):
    full_name: str = Field(..., min_length=1)


class PasswordUpdate(BaseModel):
    old_password: str
    new_password: str
