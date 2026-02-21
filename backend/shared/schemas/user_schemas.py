"""
User-related Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime
from enum import Enum
import uuid


class UserRole(str, Enum):
    USER = "user"
    ANALYST = "analyst"
    ADMIN = "admin"


class UserRegister(BaseModel):
    """User registration schema"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = Field(None, max_length=100)

    @field_validator('username')
    @classmethod
    def username_validation(cls, v):
        v = v.lower().strip()
        if not v.replace('_', '').isalnum():
            raise ValueError('Username must be alphanumeric')
        return v

    @field_validator('password')
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Must contain uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Must contain lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Must contain digit')
        return v


class UserLogin(BaseModel):
    """Login schema"""
    username: str
    password: str


class UserUpdate(BaseModel):
    """Profile update schema"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=100)


class PasswordChange(BaseModel):
    """Password change schema"""
    current_password: str
    new_password: str = Field(..., min_length=8)

    @field_validator('new_password')
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Must contain uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Must contain lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Must contain digit')
        return v


class UserResponse(BaseModel):
    """User response schema"""
    id: uuid.UUID
    username: str
    email: str
    full_name: Optional[str]
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime]

    model_config = {
        "from_attributes": True,
        "json_encoders": {uuid.UUID: str}
    }


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class TokenData(BaseModel):
    """Decoded token data"""
    user_id: str
    username: str
    role: UserRole
    exp: Optional[datetime] = None