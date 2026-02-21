"""Common schemas used across services"""
from pydantic import BaseModel
from typing import Optional


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str
    detail: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None
    status_code: int


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    version: Optional[str] = None
    database: Optional[str] = None