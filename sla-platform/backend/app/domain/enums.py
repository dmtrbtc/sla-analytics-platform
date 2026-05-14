from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    ANALYST = "analyst"
    TEAM_LEAD = "team_lead"
    VIEWER = "viewer"


class ImportStatus(StrEnum):
    DRAFT = "draft"
    UPLOADING = "uploading"
    VALIDATING = "validating"
    PARSING = "parsing"
    NORMALIZING = "normalizing"
    REBUILDING = "rebuilding"
    COMPUTING_SLA = "computing_sla"
    COMPLETED = "completed"
    FAILED = "failed"


class EventType(StrEnum):
    STATE_UPDATE = "StateUpdate"
    MOVE = "Move"
    OWNER_UPDATE = "OwnerUpdate"
    NEW_TICKET = "NewTicket"
    LOCK = "Lock"
    UNLOCK = "Unlock"
    SET_PENDING_TIME = "SetPendingTime"
    FOLLOW_UP = "FollowUp"
    SLA_UPDATE = "SLAUpdate"
    SERVICE_UPDATE = "ServiceUpdate"
    ESCALATION_SOLUTION_START = "EscalationSolutionTimeStart"
    ESCALATION_RESPONSE_START = "EscalationResponseTimeStart"
    ESCALATION_SOLUTION_STOP = "EscalationSolutionTimeStop"
    ESCALATION_RESPONSE_STOP = "EscalationResponseTimeStop"
    SEND_ANSWER = "SendAnswer"
    EMAIL_CUSTOMER = "EmailCustomer"
    PHONE_CALL_CUSTOMER = "PhoneCallCustomer"
    ADD_NOTE = "AddNote"
    TITLE_UPDATE = "TitleUpdate"
    PRIORITY_UPDATE = "PriorityUpdate"
    TYPE_UPDATE = "TypeUpdate"
    CUSTOMER_UPDATE = "CustomerUpdate"
    MERGED = "Merged"
    MISC = "Misc"


class ConfidenceLevel(StrEnum):
    FULL = "full"
    PARTIAL = "partial"
    MINIMAL = "minimal"
