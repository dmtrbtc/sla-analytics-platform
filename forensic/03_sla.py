"""Stage 3: SLA breach attribution + stage-level loss analysis.

Sources:
- history.csv: Escalation*Time* events, StateUpdate (pending), Move, OwnerUpdate
- open xlsx: 14764 open tickets with SolutionTime, AgentReactionTime (deadline string)
- closed csv: 49 closed tickets with SolutionInMin/SolutionDiffInMin
- backlog: state + queue snapshot
"""
import pandas as pd, json, sys, io, re, math
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SRC = r"D:/SLA_test"
OUT = r"D:/Otrs_SLA/.claude/worktrees/sad-shockley-d10f2d/forensic"

# --- Closed tickets: parse & validate SLA solution metrics ---
closed = pd.read_csv(f"{SRC}/List_of_tickets_closed_sorted_by_solution_time_Created_2026_05_20.csv",
                     sep=";", encoding="utf-8-sig", low_memory=False)
# Column names — use raw
print("Closed cols (first 50):", list(closed.columns)[:50])
print(f"Closed sample: {len(closed)} rows")
# Cast key cols
for col in ["SolutionInMin","SolutionDiffInMin","FirstResponseInMin","FirstResponseDiffInMin","SolutionTimeWorkingTime"]:
    if col in closed.columns:
        closed[col] = pd.to_numeric(closed[col], errors="coerce")
# Breach = SolutionDiffInMin > 0 means breached past deadline
if "SolutionDiffInMin" in closed.columns:
    closed["sla_breached"] = closed["SolutionDiffInMin"].fillna(0) > 0
    print(f"\n[CLOSED] SLA breach rate: {closed['sla_breached'].mean():.1%}")
    print(closed.groupby("Очередь")["sla_breached"].agg(["sum","count","mean"]).sort_values("mean", ascending=False).to_string())

# Closure timing distribution
print("\nClosed SolutionInMin describe:")
print(closed["SolutionInMin"].describe())

# --- Open tickets xlsx ---
op = pd.read_excel(f"{SRC}/List_of_open_tickets_sorted_by_time_left_until_solution_deadline.xlsx")
op.columns = [str(c).strip() for c in op.columns]
print("\nOpen columns:", list(op.columns))
print("Open rows:", len(op))
# SolutionTime is a string like "5 h" / "-2 d 3 h" etc; parse to hours signed
def parse_dur(s):
    if pd.isna(s): return None
    s=str(s).strip()
    neg = s.startswith("-")
    s = s.lstrip("-")
    h=0
    m = re.search(r"(\d+)\s*d", s);  h += int(m.group(1))*24 if m else 0
    m = re.search(r"(\d+)\s*h", s);  h += int(m.group(1)) if m else 0
    m = re.search(r"(\d+)\s*m", s);  h += int(m.group(1))/60 if m else 0
    return -h if neg else h

op["sol_time_h"] = op["SolutionTime"].apply(parse_dur)
op["resp_time_h"] = op["AgentReactionTime"].apply(parse_dur)
op["sla_breached_open"] = op["sol_time_h"] < 0
op["resp_breached_open"] = op["resp_time_h"] < 0
print(f"\n[OPEN] solution deadline parsed: total={op['sol_time_h'].notna().sum()}")
print(f"[OPEN] breaching solution deadline now: {op['sla_breached_open'].sum()} / {len(op)} = {op['sla_breached_open'].mean():.1%}")
print(f"[OPEN] breaching first-response deadline now: {op['resp_breached_open'].sum()} / {op['resp_time_h'].notna().sum()}")

# breach by queue
qcol = "Очередь"
q_breach = op.groupby(qcol).agg(
    open_n=("Ticket#","count"),
    breached_solution=("sla_breached_open","sum"),
    breach_pct=("sla_breached_open","mean"),
    breached_response=("resp_breached_open","sum"),
    worst_solution_h=("sol_time_h","min"),
).sort_values("breached_solution", ascending=False)
print("\nTop 25 queues by absolute open-breach count:")
print(q_breach.head(25).to_string())
q_breach.to_csv(f"{OUT}/03_open_breach_by_queue.csv", encoding="utf-8-sig")

# --- History: stage-level time loss from real events ---
h = pd.read_csv(f"{SRC}/history_2026-05-11_07-00-28.csv", encoding="utf-8-sig")
h["event_time"] = pd.to_datetime(h["event_time"], errors="coerce")
h = h.sort_values(["ticket_id","event_time"]).reset_index(drop=True)

# For each ticket compute time spent per state, per owner-status, per pending
h["next_time"] = h.groupby("ticket_id")["event_time"].shift(-1)
h["dt_h"] = (h["next_time"] - h["event_time"]).dt.total_seconds()/3600

state_h = h.groupby("state_name")["dt_h"].sum().sort_values(ascending=False)
print("\nHours observed by state (7-day window, all tickets):")
print(state_h.to_string())
state_h.to_csv(f"{OUT}/03_state_hours.csv", encoding="utf-8-sig", header=["hours"])

# Pending time (idle / on-hold leakage)
pend = h[h["state_name"].astype(str).str.contains("pending", case=False, na=False)]
pend_hours_total = pend["dt_h"].sum()
total_obs_hours = h["dt_h"].sum()
print(f"\nPending state share of observed lifecycle hours: {pend_hours_total:.0f} / {total_obs_hours:.0f} = {pend_hours_total/total_obs_hours:.1%}")

# Hours with no owner ("" or "OTRS Admin (root@localhost)") -> ownership gap
def owner_unset(o):
    if pd.isna(o): return True
    s=str(o).strip().lower()
    return s in ("", "otrs admin (root@localhost)", "root@localhost")
h["no_owner"] = h["event_owner_name"].apply(owner_unset)
no_own_h = h.loc[h["no_owner"],"dt_h"].sum()
print(f"Time observed with NO real owner (root/blank): {no_own_h:.0f}h ({no_own_h/total_obs_hours:.1%} of lifecycle time)")

# Time in queue but unlocked (no lock event preceding) — approximate by Lock/Unlock transitions per ticket
# Lock events
locks = h[h["event_name"].isin(["Lock","Unlock"])].copy()
print(f"\nLock events: {(locks['event_name']=='Lock').sum()}  Unlocks: {(locks['event_name']=='Unlock').sum()}")
# Among observed tickets, how many never get locked? -> potential black-hole (work never started)
locked_tickets = set(h.loc[h["event_name"]=="Lock","ticket_id"])
all_tickets = set(h["ticket_id"].unique())
never_locked = all_tickets - locked_tickets
print(f"Tickets in history that were NEVER locked (no agent picked them up): {len(never_locked)} / {len(all_tickets)} = {len(never_locked)/len(all_tickets):.1%}")

# Escalation events: SolutionStart/NotifyBefore/Stop occurrences indicate breach pressure
esc = h[h["event_name"].astype(str).str.startswith("Escalation")]
print("\nEscalation events breakdown:")
print(esc["event_name"].value_counts().to_string())

# Tickets with EscalationResponseTimeNotifyBefore but no first response within window
notify = h[h["event_name"]=="EscalationResponseTimeNotifyBefore"]
print(f"\nTickets receiving FirstResponse breach warnings: {notify['ticket_id'].nunique()}")
# Response events
resp_evts = {"SendAnswer","EmailCustomer","PhoneCallCustomer","SendCustomerNotification"}
responded = set(h.loc[h["event_name"].isin(resp_evts),"ticket_id"])
notify_tkts = set(notify["ticket_id"])
warned_no_resp = notify_tkts - responded
print(f"Of warned tickets, never sent a customer-facing response: {len(warned_no_resp)}")

# Save SLA summary
summary = {
    "closed_sample": int(len(closed)),
    "closed_breach_rate": float(closed["sla_breached"].mean()) if "sla_breached" in closed.columns else None,
    "open_total": int(len(op)),
    "open_solution_breached_now": int(op["sla_breached_open"].sum()),
    "open_solution_breach_rate": float(op["sla_breached_open"].mean()),
    "open_response_breached_now": int(op["resp_breached_open"].sum()),
    "open_worst_breach_hours": float(op["sol_time_h"].min()),
    "state_hours_top": state_h.head(15).to_dict(),
    "pending_share_of_lifecycle": float(pend_hours_total/total_obs_hours) if total_obs_hours else None,
    "no_owner_share": float(no_own_h/total_obs_hours) if total_obs_hours else None,
    "tickets_never_locked": int(len(never_locked)),
    "history_observed_tickets": int(len(all_tickets)),
    "escalation_breakdown": esc["event_name"].value_counts().to_dict(),
    "first_response_warned_then_never_responded": int(len(warned_no_resp)),
}
with open(f"{OUT}/03_sla.json","w",encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
print("\nSLA summary saved.")
