from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


class HealthResponse(BaseModel):
    status: str
    version: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: str
    password: str


class UserCreate(BaseModel):
    email: str
    display_name: str
    password: str
    role: str = "viewer"


class UserResponse(BaseModel):
    id: UUID
    email: str
    display_name: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ImportSessionResponse(BaseModel):
    id: UUID
    status: str
    backlog_file: Optional[str] = None
    history_file: Optional[str] = None
    backlog_sha256: Optional[str] = None
    history_sha256: Optional[str] = None
    backlog_rows: Optional[int] = None
    history_rows: Optional[int] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    stats: dict = {}
    error_details: list = []
    imported_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int


class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None


class ImportSessionCreate(BaseModel):
    pass


class ImportSessionStart(BaseModel):
    import_id: UUID


class ImportUploadResponse(BaseModel):
    id: UUID
    status: str
    message: str


class PipelineStatusResponse(BaseModel):
    import_id: UUID
    status: str
    stats: dict = {}
    error_count: int = 0
