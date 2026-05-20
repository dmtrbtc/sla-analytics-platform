"""Stage 5: Owner forensic analysis — load, idle, reassignment, accountability gaps."""
import pandas as pd, json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SRC = r"D:/SLA_test"
OUT = r"D:/Otrs_SLA/.claude/worktrees/sad-shockley-d10f2d/forensic"

h = pd.read_csv(f"{SRC}/history_2026-05-11_07-00-28.csv", encoding="utf-8-sig")
h["event_time"] = pd.to_datetime(h["event_time"], errors="coerce")
h = h.sort_values(["ticket_id","event_time"]).reset_index(drop=True)
h["next_time"] = h.groupby("ticket_id")["event_time"].shift(-1)
h["dt_h"] = (h["next_time"] - h["event_time"]).dt.total_seconds()/3600

DEFAULT = "OTRS Admin (root@localhost)"

# --- Owner load: per owner, how many distinct tickets touched, and observation hours ---
owner_load = h.groupby("event_owner_name").agg(
    tickets=("ticket_id","nunique"),
    events=("event_name","count"),
    hours_held=("dt_h","sum"),
).sort_values("tickets", ascending=False)
print("Top 25 owners by ticket count (observed window):")
print(owner_load.head(25).to_string())
owner_load.to_csv(f"{OUT}/05_owner_load.csv", encoding="utf-8-sig")

# --- Pure agent activity (exclude DEFAULT/root + notifications) ---
agent = h[h["event_owner_name"]!=DEFAULT].copy()
agent_action = agent[agent["event_name"].isin([
    "SendAnswer","EmailCustomer","PhoneCallCustomer","SendCustomerNotification",
    "AddNote","TimeAccounting","StateUpdate","Move","Lock","Unlock"
])]
print("\nAgent meaningful actions per owner (top 25):")
print(agent_action.groupby("event_owner_name").size().sort_values(ascending=False).head(25).to_string())

# --- Idle owners: own tickets but no meaningful actions ---
# Owners that appear as event_owner but never as initiator of an action event
all_owners = set(h.loc[h["event_owner_name"]!=DEFAULT, "event_owner_name"].dropna().unique())
active_owners = set(agent_action.loc[agent_action["event_owner_name"]!=DEFAULT, "event_owner_name"].dropna().unique())
idle = all_owners - active_owners
print(f"\nOwners with NO meaningful action in window: {len(idle)} (of {len(all_owners)} agent owners)")
print("Sample idle owners:", list(idle)[:15])

# --- OwnerUpdate events: reassignment patterns ---
ow = h[h["event_name"]=="OwnerUpdate"].copy()
ow_count = ow.groupby("ticket_id").size().sort_values(ascending=False)
print(f"\nReassignment storms (>=3 owner changes): {(ow_count>=3).sum()} tickets")
print("Top tickets by owner changes:")
print(ow_count.head(15).to_string())

# --- Cross-queue movement vs owner: hot-potato detection ---
moves = h.copy()
moves["prev_q"] = moves.groupby("ticket_id")["queue_name"].shift()
moves["prev_o"] = moves.groupby("ticket_id")["event_owner_name"].shift()
moves = moves[(moves["prev_q"].notna()) & (moves["prev_q"]!=moves["queue_name"])]
hot_potato = moves.groupby("ticket_id").size().sort_values(ascending=False)
hot_potato_top = hot_potato.head(20).to_dict()

# --- Tickets where owner = root/default for ENTIRE history (no real ownership) ---
per_ticket = h.groupby("ticket_id")["event_owner_name"].agg(lambda s: set(s.dropna()))
no_real_owner = per_ticket[per_ticket.apply(lambda S: S.issubset({DEFAULT}))]
print(f"\nTickets with ONLY root@localhost as owner across observed window: {len(no_real_owner)} / {len(per_ticket)} = {len(no_real_owner)/len(per_ticket):.1%}")

# --- Queues without owner accountability ---
# Sum hours per queue with no real owner
def owner_unset(o):
    if pd.isna(o): return True
    return str(o).strip().lower() in ("","otrs admin (root@localhost)","root@localhost")
h["no_owner"] = h["event_owner_name"].apply(owner_unset)
q_acc = h.groupby("queue_name").apply(
    lambda d: pd.Series({
        "hours_total": d["dt_h"].sum(),
        "hours_no_owner": d.loc[d["no_owner"],"dt_h"].sum(),
        "tickets": d["ticket_id"].nunique(),
    }), include_groups=False
)
q_acc["no_owner_pct"] = q_acc["hours_no_owner"]/q_acc["hours_total"].replace({0:None})
q_acc = q_acc.sort_values("hours_no_owner", ascending=False)
print("\nQueues by NO-OWNER hours (top 20):")
print(q_acc.head(20).to_string())
q_acc.to_csv(f"{OUT}/05_queue_accountability.csv", encoding="utf-8-sig")

# --- Closed file owner stats ---
closed = pd.read_csv(f"{SRC}/List_of_tickets_closed_sorted_by_solution_time_Created_2026_05_20.csv",
                     sep=";", encoding="utf-8-sig", low_memory=False)
print("\nClosed file owner dist:")
print(closed["Агент (владелец)"].value_counts().head(15).to_string())

# In closed CSV breach by owner
closed["SolutionDiffInMin"] = pd.to_numeric(closed["SolutionDiffInMin"], errors="coerce")
closed["breached"] = closed["SolutionDiffInMin"].fillna(0)>0
o_br = closed.groupby("Агент (владелец)").agg(
    n=("Ticket#","count"),
    breaches=("breached","sum"),
    breach_rate=("breached","mean"),
).sort_values("breaches", ascending=False)
print("\nClosed-sample breach by owner:")
print(o_br.to_string())

summary = {
    "owners_total": int(len(all_owners))+1,
    "owners_with_zero_actions": int(len(idle)),
    "tickets_only_root_owner": int(len(no_real_owner)),
    "tickets_with_history": int(len(per_ticket)),
    "no_real_owner_pct": float(len(no_real_owner)/len(per_ticket)),
    "reassignment_storms_gte3": int((ow_count>=3).sum()),
    "hot_potato_top": {int(k):int(v) for k,v in hot_potato_top.items()},
    "queue_accountability_top10": q_acc.head(10).reset_index().to_dict(orient="records"),
    "closed_breach_by_owner": o_br.reset_index().to_dict(orient="records"),
}
with open(f"{OUT}/05_owner.json","w",encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
print("\nOwner forensic saved.")
