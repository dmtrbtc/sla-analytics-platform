"""Stage 4: Breach attribution — for each breached open ticket, walk its history
and attribute the breach time to the queue/owner who held it during the breach window.
"""
import pandas as pd, json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SRC = r"D:/SLA_test"
OUT = r"D:/Otrs_SLA/.claude/worktrees/sad-shockley-d10f2d/forensic"

op = pd.read_excel(f"{SRC}/List_of_open_tickets_sorted_by_time_left_until_solution_deadline.xlsx")
op.columns = [str(c).strip() for c in op.columns]
breached = op[op["SolutionTime"] < 0].copy()
print(f"Breached open tickets: {len(breached)}")

# Aggregate by queue (where the ticket currently sits)
breach_by_queue = breached.groupby("Очередь").agg(
    n=("Ticket#","count"),
    median_sec=("SolutionTime","median"),
    p10_sec=("SolutionTime", lambda s: s.quantile(0.1)),  # most negative
    sum_sec=("SolutionTime","sum"),
).sort_values("n", ascending=False)
breach_by_queue["median_h"] = breach_by_queue["median_sec"]/3600
breach_by_queue["worst_h"] = breach_by_queue["p10_sec"]/3600
breach_by_queue["total_loss_days"] = -breach_by_queue["sum_sec"]/86400
print("\nBreach attribution by *current* queue (where it sits):")
print(breach_by_queue.head(25).to_string())
breach_by_queue.to_csv(f"{OUT}/04_breach_by_queue.csv", encoding="utf-8-sig")

# Now combine with history — for breached tickets present in history, where did time go?
h = pd.read_csv(f"{SRC}/history_2026-05-11_07-00-28.csv", encoding="utf-8-sig")
h["event_time"] = pd.to_datetime(h["event_time"], errors="coerce")
h = h.sort_values(["ticket_id","event_time"]).reset_index(drop=True)
h["next_time"] = h.groupby("ticket_id")["event_time"].shift(-1)
h["dt_h"] = (h["next_time"] - h["event_time"]).dt.total_seconds()/3600

# breached ticket numbers as strings
breached["Ticket#"] = breached["Ticket#"].astype(str)
h_ticket_nums = pd.Series(h["ticket_number"].astype(str).unique())
overlap = set(breached["Ticket#"]) & set(h_ticket_nums)
print(f"\nBreached tickets present in observed 7-day history: {len(overlap)}")

bh = h[h["ticket_number"].astype(str).isin(overlap)].copy()
# Time in pending vs open vs new
state_share = bh.groupby("state_name")["dt_h"].sum().sort_values(ascending=False)
print("\nFor breached tickets in observed window — time by state:")
print(state_share.to_string())

# Queue holding time among breached tickets
q_share = bh.groupby("queue_name")["dt_h"].sum().sort_values(ascending=False)
print("\nFor breached tickets — observed holding hours by queue (top 15):")
print(q_share.head(15).to_string())
q_share.to_csv(f"{OUT}/04_breached_holding_by_queue.csv", encoding="utf-8-sig", header=["hours"])

# Owner share
o_share = bh.groupby("event_owner_name")["dt_h"].sum().sort_values(ascending=False)
print("\nFor breached tickets — observed holding hours by owner (top 15):")
print(o_share.head(15).to_string())

# Fraction of breached-ticket time with no real owner
def owner_unset(o):
    if pd.isna(o): return True
    s=str(o).strip().lower()
    return s in ("","otrs admin (root@localhost)","root@localhost")
bh["no_owner"] = bh["event_owner_name"].apply(owner_unset)
no_own_share = bh.loc[bh["no_owner"],"dt_h"].sum() / bh["dt_h"].sum()
print(f"\nFor breached tickets — % observed time with NO real owner: {no_own_share:.1%}")

# Movement among breached
moves = bh[bh["event_name"]=="Move"]
print(f"Moves observed among breached tickets in window: {len(moves)}")
mv_pairs = bh.copy()
mv_pairs["prev_q"] = mv_pairs.groupby("ticket_id")["queue_name"].shift()
mv_pairs = mv_pairs[mv_pairs["prev_q"].notna() & (mv_pairs["prev_q"]!=mv_pairs["queue_name"])]
print(f"Effective queue transitions among breached tickets in window: {len(mv_pairs)}")
print(mv_pairs.groupby(["prev_q","queue_name"]).size().sort_values(ascending=False).head(15).to_string())

summary = {
    "breached_open_total": int(len(breached)),
    "top_breach_queues": breach_by_queue.head(20).reset_index().to_dict(orient="records"),
    "breached_in_history_window": len(overlap),
    "breached_state_hours": state_share.to_dict(),
    "breached_queue_hours_top10": q_share.head(10).to_dict(),
    "breached_no_owner_share": float(no_own_share),
}
with open(f"{OUT}/04_breach.json","w",encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
print("\nBreach attribution saved.")
