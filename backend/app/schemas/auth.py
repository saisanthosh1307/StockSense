from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app.models.user import RoleEnum

class UserBase(BaseModel):
    name: str
    email: str
    role: Optional[RoleEnum] = RoleEnum.WAREHOUSE_STAFF

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserOut(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

class OTPRequest(BaseModel):
    email: str

class OTPResetPassword(BaseModel):
    email: str
    otp: str
    new_password: str

class UserRoleUpdate(BaseModel):
    role: RoleEnum
