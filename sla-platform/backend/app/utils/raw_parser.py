import logging
import re
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)
_UNKNOWN_EVENTS: set[str] = set()


RAW_MOVE = re.compile(r"^%%(.+?)%%(\d+)%%(.+?)%%(\d+)(%%)?$")
RAW_OWNER = re.compile(r"^%%(.+?)%%(\d+)(%%)?$")
RAW_STATE = re.compile(r"^%%(.+?)%%(.+?)%%$")
RAW_PENDING = re.compile(r"^%%(\d{4}-\d{2}-\d{2} \d{2}:\d{2})(%%)?$")
RAW_PENDING_CLEAR = re.compile(r"^%%00-00-00 00:00(%%)?$")
RAW_SLA = re.compile(r"^%%(.*?)%%(\d+|NULL)%%(.*?)%%(\d+|NULL)(%%)?$")
RAW_NEWTICKET = re.compile(
    r"^%%(\d+)%%(.+?)%%\d+%%(.+?)%%(\d+)(%%)?$"
)


def parse_event_raw(event_name: str, event_raw_name: str) -> dict:
    parsed: dict = {}

    if event_name == "Move":
        m = RAW_MOVE.match(event_raw_name)
        if m:
            parsed["dest_queue"] = m.group(1)
            parsed["dest_queue_id"] = m.group(2)
            parsed["src_queue"] = m.group(3)
            parsed["src_queue_id"] = m.group(4)

    elif event_name == "OwnerUpdate":
        m = RAW_OWNER.match(event_raw_name)
        if m:
            parsed["new_owner"] = m.group(1)

    elif event_name == "StateUpdate":
        m = RAW_STATE.match(event_raw_name)
        if m:
            parsed["old_state"] = m.group(1)
            parsed["new_state"] = m.group(2)

    elif event_name == "SetPendingTime":
        m = RAW_PENDING_CLEAR.match(event_raw_name)
        if m:
            parsed["pending_until"] = None
            parsed["pending_cleared"] = True
        else:
            m = RAW_PENDING.match(event_raw_name)
            if m:
                try:
                    parsed["pending_until"] = datetime.strptime(
                        m.group(1), "%Y-%m-%d %H:%M"
                    )
                    parsed["pending_cleared"] = False
                except ValueError:
                    pass
            else:
                parsed["pending_cleared"] = False

    elif event_name == "SLAUpdate":
        m = RAW_SLA.match(event_raw_name)
        if m:
            parsed["old_sla"] = m.group(1) if m.group(1) != "NULL" else None
            parsed["new_sla"] = m.group(3) if m.group(3) != "NULL" else None

    elif event_name == "ServiceUpdate":
        m = RAW_SLA.match(event_raw_name)
        if m:
            parsed["old_service"] = m.group(1) if m.group(1) != "NULL" else None
            parsed["new_service"] = m.group(3) if m.group(3) != "NULL" else None

    elif event_name == "NewTicket":
        m = RAW_NEWTICKET.match(event_raw_name)
        if m:
            parsed["new_ticket_number"] = m.group(1)
            parsed["new_queue"] = m.group(2)
            parsed["new_state"] = m.group(3)
        else:
            parsed["new_ticket_number"] = None

    elif event_name in ("Lock", "Unlock"):
        parsed["lock_action"] = event_name.lower()

    elif event_name == "EscalationSolutionTimeStart":
        parsed["escalation_type"] = "solution"
    elif event_name == "EscalationResponseTimeStart":
        parsed["escalation_type"] = "response"
    elif event_name == "EscalationSolutionTimeStop":
        parsed["escalation_type"] = "solution"
        parsed["escalation_stopped"] = True
    elif event_name == "EscalationResponseTimeStop":
        parsed["escalation_type"] = "response"
        parsed["escalation_stopped"] = True

    elif event_name == "SendAnswer":
        parsed["communication_type"] = "answer"
    elif event_name == "EmailCustomer":
        parsed["communication_type"] = "email"
    elif event_name == "PhoneCallCustomer":
        parsed["communication_type"] = "phone_customer"
    elif event_name == "PhoneCallAgent":
        parsed["communication_type"] = "phone_agent"
    elif event_name == "WebRequestCustomer":
        parsed["communication_type"] = "web_request"
    elif event_name == "AddNote":
        parsed["communication_type"] = "note"
    elif event_name == "FollowUp":
        parsed["communication_type"] = "followup"

    elif event_name == "TitleUpdate":
        parsed["update_type"] = "title"
    elif event_name == "PriorityUpdate":
        parsed["update_type"] = "priority"
    elif event_name == "TypeUpdate":
        parsed["update_type"] = "type"
    elif event_name == "CustomerUpdate":
        parsed["update_type"] = "customer"

    elif event_name == "TicketDynamicFieldUpdate":
        parsed["update_type"] = "dynamic_field"

    elif event_name == "Merged":
        parsed["merged"] = True

    elif event_name == "Misc":
        raw_lower = event_raw_name.lower()
        if "pending" in raw_lower:
            parsed["misc_type"] = "pending_info"
        elif "timeaccounting" in raw_lower:
            parsed["misc_type"] = "time_accounting"
        else:
            parsed["misc_type"] = "other"

    elif event_name == "SendAgentNotification":
        parsed["notification"] = True
    elif event_name == "SendAutoReply":
        parsed["communication_type"] = "auto_reply"
    elif event_name == "SendCustomerNotification":
        parsed["notification"] = True

    elif event_name == "TimeAccounting":
        parsed["misc_type"] = "time_accounting"

    elif event_name == "TicketLinkAdd":
        parsed["misc_type"] = "link_add"
    elif event_name in ("Subscribe", "Unsubscribe"):
        parsed["misc_type"] = event_name.lower()
    elif event_name == "LoopProtection":
        parsed["misc_type"] = "loop_protection"
    elif event_name == "Forward":
        parsed["communication_type"] = "forward"

    elif event_name in (
        "EscalationSolutionTimeNotifyBefore",
        "EscalationResponseTimeNotifyBefore",
    ):
        parsed["escalation_type"] = "notify_before"

    else:
        if event_name not in _UNKNOWN_EVENTS:
            _UNKNOWN_EVENTS.add(event_name)
            logger.warning("Unknown event type encountered", extra={"event_name": event_name})

    return parsed


def extract_owner_from_event(event_owner_name: str) -> Optional[str]:
    if not event_owner_name or event_owner_name == "root@localhost":
        return None
    return event_owner_name


def is_system_owner(owner: Optional[str]) -> bool:
    return owner is None or owner == "root@localhost"


def extract_team_prefix(queue_name: Optional[str]) -> Optional[str]:
    if not queue_name:
        return None
    parts = queue_name.split("-")
    if len(parts) >= 2:
        return f"{parts[0]}-{parts[1]}"
    return queue_name
