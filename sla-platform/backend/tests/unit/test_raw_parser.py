"""Unit tests for raw_parser.py — all event type parsing."""

from datetime import datetime

from app.utils.raw_parser import (
    extract_owner_from_event,
    extract_team_prefix,
    is_system_owner,
    parse_event_raw,
)


def test_parse_move():
    result = parse_event_raw("Move", "%%Support-Queue%%42%%Escalation-Queue%%7%%")
    assert result["dest_queue"] == "Support-Queue"
    assert result["dest_queue_id"] == "42"
    assert result["src_queue"] == "Escalation-Queue"
    assert result["src_queue_id"] == "7"


def test_parse_move_no_match():
    result = parse_event_raw("Move", "invalid")
    assert result == {}


def test_parse_owner_update():
    result = parse_event_raw("OwnerUpdate", "%%agent.smith%%99%%")
    assert result["new_owner"] == "agent.smith"


def test_parse_owner_update_no_match():
    result = parse_event_raw("OwnerUpdate", "")
    assert result == {}


def test_parse_state_update():
    result = parse_event_raw("StateUpdate", "%%open%%closed successful%%")
    assert result["old_state"] == "open"
    assert result["new_state"] == "closed successful"


def test_parse_state_update_no_match():
    result = parse_event_raw("StateUpdate", "bad")
    assert result == {}


def test_parse_set_pending_time():
    result = parse_event_raw("SetPendingTime", "%%2025-03-15 14:30%%")
    assert result["pending_until"] == datetime(2025, 3, 15, 14, 30)
    assert result["pending_cleared"] is False


def test_parse_set_pending_time_clear():
    result = parse_event_raw("SetPendingTime", "%%00-00-00 00:00%%")
    assert result["pending_until"] is None
    assert result["pending_cleared"] is True


def test_parse_set_pending_time_invalid():
    result = parse_event_raw("SetPendingTime", "invalid")
    assert result.get("pending_cleared") is False


def test_parse_sla_update():
    result = parse_event_raw("SLAUpdate", "%%Support-SLA%%42%%Critical-SLA%%7%%")
    assert result["old_sla"] == "Support-SLA"
    assert result["new_sla"] == "Critical-SLA"


def test_parse_sla_update_null():
    result = parse_event_raw("SLAUpdate", "%%NULL%%0%%Critical-SLA%%7%%")
    assert result["old_sla"] is None
    assert result["new_sla"] == "Critical-SLA"


def test_parse_service_update():
    result = parse_event_raw("ServiceUpdate", "%%OldService%%1%%NewService%%2%%")
    assert result["old_service"] == "OldService"
    assert result["new_service"] == "NewService"


def test_parse_new_ticket():
    result = parse_event_raw("NewTicket", "%%1001%%Support%%3%%open%%1%%")
    assert result["new_ticket_number"] == "1001"
    assert result["new_queue"] == "Support"
    assert result["new_state"] == "open"


def test_parse_new_ticket_no_match():
    result = parse_event_raw("NewTicket", "bad")
    assert result["new_ticket_number"] is None


def test_parse_lock():
    result = parse_event_raw("Lock", "")
    assert result["lock_action"] == "lock"


def test_parse_unlock():
    result = parse_event_raw("Unlock", "")
    assert result["lock_action"] == "unlock"


def test_parse_escalation_solution_start():
    result = parse_event_raw("EscalationSolutionTimeStart", "")
    assert result["escalation_type"] == "solution"


def test_parse_escalation_response_start():
    result = parse_event_raw("EscalationResponseTimeStart", "")
    assert result["escalation_type"] == "response"


def test_parse_escalation_solution_stop():
    result = parse_event_raw("EscalationSolutionTimeStop", "")
    assert result["escalation_type"] == "solution"
    assert result["escalation_stopped"] is True


def test_parse_escalation_response_stop():
    result = parse_event_raw("EscalationResponseTimeStop", "")
    assert result["escalation_type"] == "response"
    assert result["escalation_stopped"] is True


def test_parse_send_answer():
    result = parse_event_raw("SendAnswer", "")
    assert result["communication_type"] == "answer"


def test_parse_email_customer():
    result = parse_event_raw("EmailCustomer", "")
    assert result["communication_type"] == "email"


def test_parse_phone_call_customer():
    result = parse_event_raw("PhoneCallCustomer", "")
    assert result["communication_type"] == "phone_customer"


def test_parse_phone_call_agent():
    result = parse_event_raw("PhoneCallAgent", "")
    assert result["communication_type"] == "phone_agent"


def test_parse_web_request():
    result = parse_event_raw("WebRequestCustomer", "")
    assert result["communication_type"] == "web_request"


def test_parse_add_note():
    result = parse_event_raw("AddNote", "")
    assert result["communication_type"] == "note"


def test_parse_follow_up():
    result = parse_event_raw("FollowUp", "")
    assert result["communication_type"] == "followup"


def test_parse_send_auto_reply():
    result = parse_event_raw("SendAutoReply", "")
    assert result["communication_type"] == "auto_reply"


def test_parse_title_update():
    result = parse_event_raw("TitleUpdate", "")
    assert result["update_type"] == "title"


def test_parse_priority_update():
    result = parse_event_raw("PriorityUpdate", "")
    assert result["update_type"] == "priority"


def test_parse_type_update():
    result = parse_event_raw("TypeUpdate", "")
    assert result["update_type"] == "type"


def test_parse_customer_update():
    result = parse_event_raw("CustomerUpdate", "")
    assert result["update_type"] == "customer"


def test_parse_dynamic_field_update():
    result = parse_event_raw("TicketDynamicFieldUpdate", "")
    assert result["update_type"] == "dynamic_field"


def test_parse_merged():
    result = parse_event_raw("Merged", "")
    assert result["merged"] is True


def test_parse_misc_pending():
    result = parse_event_raw("Misc", "pending something")
    assert result["misc_type"] == "pending_info"


def test_parse_misc_time_accounting():
    result = parse_event_raw("Misc", "TimeAccounting entry")
    assert result["misc_type"] == "time_accounting"


def test_parse_misc_other():
    result = parse_event_raw("Misc", "some random misc event")
    assert result["misc_type"] == "other"


def test_parse_forward():
    result = parse_event_raw("Forward", "")
    assert result["communication_type"] == "forward"


def test_parse_notification_send_agent():
    result = parse_event_raw("SendAgentNotification", "")
    assert result["notification"] is True


def test_parse_notification_send_customer():
    result = parse_event_raw("SendCustomerNotification", "")
    assert result["notification"] is True


def test_parse_time_accounting():
    result = parse_event_raw("TimeAccounting", "")
    assert result["misc_type"] == "time_accounting"


def test_parse_ticket_link_add():
    result = parse_event_raw("TicketLinkAdd", "")
    assert result["misc_type"] == "link_add"


def test_parse_subscribe():
    result = parse_event_raw("Subscribe", "")
    assert result["misc_type"] == "subscribe"


def test_parse_unsubscribe():
    result = parse_event_raw("Unsubscribe", "")
    assert result["misc_type"] == "unsubscribe"


def test_parse_loop_protection():
    result = parse_event_raw("LoopProtection", "")
    assert result["misc_type"] == "loop_protection"


def test_parse_escalation_notify_before_solution():
    result = parse_event_raw("EscalationSolutionTimeNotifyBefore", "")
    assert result["escalation_type"] == "notify_before"


def test_parse_escalation_notify_before_response():
    result = parse_event_raw("EscalationResponseTimeNotifyBefore", "")
    assert result["escalation_type"] == "notify_before"


def test_parse_unknown_event():
    result = parse_event_raw("TotallyUnknownEventType", "")
    assert result == {}


def test_parse_empty_event_name():
    result = parse_event_raw("", "")
    assert result == {}


def test_is_system_owner_none():
    assert is_system_owner(None) is True


def test_is_system_owner_root():
    assert is_system_owner("root@localhost") is True


def test_is_system_owner_real():
    assert is_system_owner("agent@test.dev") is False


def test_extract_owner_from_event_none():
    assert extract_owner_from_event(None) is None


def test_extract_owner_from_event_root():
    assert extract_owner_from_event("root@localhost") is None


def test_extract_owner_from_event_real():
    assert extract_owner_from_event("agent@test.dev") == "agent@test.dev"


def test_extract_team_prefix_standard():
    assert extract_team_prefix("Support-Queue") == "Support-Queue"


def test_extract_team_prefix_long():
    assert extract_team_prefix("IT-Support-Level2") == "IT-Support"


def test_extract_team_prefix_single():
    assert extract_team_prefix("Support") == "Support"


def test_extract_team_prefix_none():
    assert extract_team_prefix(None) is None


def test_extract_team_prefix_empty():
    assert extract_team_prefix("") is None
