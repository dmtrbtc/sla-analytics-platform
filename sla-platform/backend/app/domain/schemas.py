from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class HealthResponse(BaseModel):
    status: str
    version: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class LoginRequest(BaseModel):
    email: str
    password: str


class UserCreate(BaseModel):
    email: str
    display_name: str
    password: str
    role: str = "viewer"

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = {"admin", "analyst", "viewer"}
        if v not in allowed:
            raise ValueError(f"Role must be one of: {', '.join(sorted(allowed))}")
        return v


class UserUpdate(BaseModel):
    email: Optional[str] = None
    display_name: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            allowed = {"admin", "analyst", "viewer"}
            if v not in allowed:
                raise ValueError(f"Role must be one of: {', '.join(sorted(allowed))}")
        return v


class UserResponse(BaseModel):
    id: UUID
    email: str
    display_name: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MeResponse(BaseModel):
    id: UUID
    email: str
    display_name: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

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


# === API Envelope ===
class APIResponse(BaseModel):
    data: Any = None
    message: str = "OK"


class ErrorResponse(BaseModel):
    detail: str
    errors: list[dict] = []


# === Team schemas ===
class TeamResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    queue_prefix: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TeamCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    queue_prefix: Optional[str] = None
    is_active: bool = True


class TeamUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    queue_prefix: Optional[str] = None
    is_active: Optional[bool] = None


# === SLA schemas ===
class SLADefinitionResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    metric_type: str
    warning_seconds: int
    critical_seconds: int
    is_active: bool = True
    business_hours_only: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class SLADefinitionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    metric_type: str
    warning_seconds: int = Field(..., gt=0)
    critical_seconds: int = Field(..., gt=0)
    is_active: bool = True
    business_hours_only: bool = True


class SLADefinitionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    metric_type: Optional[str] = None
    warning_seconds: Optional[int] = Field(None, gt=0)
    critical_seconds: Optional[int] = Field(None, gt=0)
    is_active: Optional[bool] = None
    business_hours_only: Optional[bool] = None


class SLAMetricResponse(BaseModel):
    id: int
    ticket_id: int
    metric_name: str
    metric_seconds: float
    sla_breached: bool
    queue_name: Optional[str] = None
    owner: Optional[str] = None
    team_prefix: Optional[str] = None
    sla_definition_id: Optional[int] = None
    import_id: Optional[UUID] = None
    confidence: Optional[float] = None
    computed_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# === SLA Queue Rule schemas ===
class SLAQueueRuleResponse(BaseModel):
    id: UUID
    name: str
    queue_pattern: str
    priority: int = 0
    response_target_seconds: int
    resolution_target_seconds: int
    is_active: bool = True
    description: Optional[str] = None
    created_by: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class SLAQueueRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    queue_pattern: str = Field(..., min_length=1, max_length=200)
    priority: int = 0
    response_target_seconds: int = Field(..., gt=0)
    resolution_target_seconds: int = Field(..., gt=0)
    is_active: bool = True
    description: Optional[str] = None

    @field_validator("resolution_target_seconds")
    @classmethod
    def resolution_must_exceed_response(cls, v: int, info) -> int:
        if "response_target_seconds" in info.data and v <= info.data["response_target_seconds"]:
            raise ValueError("resolution_target_seconds must be greater than response_target_seconds")
        return v


class SLAQueueRuleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    queue_pattern: Optional[str] = Field(None, min_length=1, max_length=200)
    priority: Optional[int] = None
    response_target_seconds: Optional[int] = Field(None, gt=0)
    resolution_target_seconds: Optional[int] = Field(None, gt=0)
    is_active: Optional[bool] = None
    description: Optional[str] = None


# === Ticket schemas ===
class TicketSnapshotResponse(BaseModel):
    id: int
    ticket_id: int
    ticket_number: Optional[str] = None
    title: Optional[str] = None
    queue_name: Optional[str] = None
    state_name: Optional[str] = None
    owner_name: Optional[str] = None
    priority: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at_ts: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    last_import_id: Optional[UUID] = None
    model_config = ConfigDict(from_attributes=True)


class TicketEventResponse(BaseModel):
    id: int
    ticket_id: int
    ticket_number: Optional[str] = None
    event_seq: Optional[int] = None
    event_time: Optional[datetime] = None
    event_type: Optional[str] = None
    queue_name: Optional[str] = None
    state_name: Optional[str] = None
    owner_name: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# === Paginated responses ===
class PaginatedResponse(BaseModel):
    items: list
    total: int
    limit: int = 50
    offset: int = 0


class PaginatedResponseTickets(BaseModel):
    tickets: list
    total: int
    page: int = 1
    page_size: int = 50
