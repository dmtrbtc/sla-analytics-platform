"""Stage 6: Queue governance — black holes, dynamic SLA candidates, entropy."""
import pandas as pd, json, sys, io, math
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SRC = r"D:/SLA_test"
OUT = r"D:/Otrs_SLA/.claude/worktrees/sad-shockley-d10f2d/forensic"

op = pd.read_excel(f"{SRC}/List_of_open_tickets_sorted_by_time_left_until_solution_deadline.xlsx")
op.columns = [c.strip() for c in op.columns]
closed = op[op["Состояние"].astype(str).str.startswith("closed")].copy()
closed["breached"] = (closed["SolutionTime"]<0)

h = pd.read_csv(f"{SRC}/history_2026-05-11_07-00-28.csv", encoding="utf-8-sig")
h["event_time"] = pd.to_datetime(h["event_time"], errors="coerce")
h = h.sort_values(["ticket_id","event_time"]).reset_index(drop=True)
h["next_time"] = h.groupby("ticket_id")["event_time"].shift(-1)
h["dt_h"] = (h["next_time"] - h["event_time"]).dt.total_seconds()/3600

# --- Breach rate per queue (from closed) ---
qstat = closed.groupby("Очередь").agg(
    closed_n=("Ticket#","count"),
    breaches=("breached","sum"),
    breach_rate=("breached","mean"),
).sort_values("breaches", ascending=False)
qstat = qstat[qstat["closed_n"]>=10]
print("Queues with >=10 closed tickets, ranked by breach count:")
print(qstat.head(25).to_string())
qstat.to_csv(f"{OUT}/06_queue_breach_stats.csv", encoding="utf-8-sig")

# --- Per-SLA breach (governance: which SLAs are unrealistic?) ---
sla_stat = closed.groupby("SLA").agg(
    n=("Ticket#","count"),
    breaches=("breached","sum"),
    breach_rate=("breached","mean"),
).sort_values("breaches", ascending=False)
sla_stat = sla_stat[sla_stat["n"]>=10]
print("\nPer-SLA realism (SLAs with >=10 closed, sorted by breach count):")
print(sla_stat.head(30).to_string())
sla_stat.to_csv(f"{OUT}/06_sla_realism.csv", encoding="utf-8-sig")
print("\nWorst SLAs by breach RATE (>=10 closed):")
print(sla_stat.sort_values("breach_rate", ascending=False).head(15).to_string())

# --- Queue entropy: how varied are routes leaving a queue? ---
# Higher entropy => routing decisions widely fanned-out (likely manual triage)
moves = h.copy()
moves["prev_q"] = moves.groupby("ticket_id")["queue_name"].shift()
moves = moves[(moves["prev_q"].notna()) & (moves["prev_q"]!=moves["queue_name"])]
def entropy(s):
    p = s.value_counts(normalize=True)
    return float(-(p*p.map(lambda x: math.log2(x))).sum())
out_n = moves.groupby("prev_q").size().rename("out_n")
uniq = moves.groupby("prev_q")["queue_name"].nunique().rename("unique_targets")
ent  = moves.groupby("prev_q")["queue_name"].apply(entropy).rename("entropy")
q_ent = pd.concat([out_n, uniq, ent], axis=1).sort_values("entropy", ascending=False)
print("\nQueue routing entropy (out-degree variance — high = chaotic):")
print(q_ent.head(20).to_string())
q_ent.to_csv(f"{OUT}/06_queue_entropy.csv", encoding="utf-8-sig")

# --- Black-hole detection: queues where tickets stay long, almost no exit, no owner work ---
seg = pd.read_csv(f"{OUT}/02_segments.csv", encoding="utf-8-sig")
seg["hours"] = pd.to_numeric(seg["hours"], errors="coerce")
acc = pd.read_csv(f"{OUT}/05_queue_accountability.csv", encoding="utf-8-sig")

# Join queue stats
bh = seg.groupby("queue").agg(
    seg_count=("ticket_id","count"),
    mean_h=("hours","mean"),
    median_h=("hours","median"),
    max_h=("hours","max"),
).reset_index()
bh = bh.merge(acc, left_on="queue", right_on="queue_name", how="left")
bh = bh.merge(out_n.reset_index().rename(columns={"prev_q":"queue"}), on="queue", how="left").fillna({"out_n":0})
# Black-hole index: low out_n, high mean stay, high no_owner_pct
bh["bh_index"] = (bh["mean_h"].fillna(0)) * (1 - bh["out_n"].fillna(0)/bh["seg_count"].clip(lower=1)) * bh["no_owner_pct"].fillna(0)
bh = bh.sort_values("bh_index", ascending=False)
print("\nBlack-hole index (high = long stays, few exits, no owner accountability):")
print(bh[["queue","seg_count","mean_h","out_n","no_owner_pct","bh_index"]].head(20).to_string(index=False))
bh.to_csv(f"{OUT}/06_blackhole_index.csv", index=False, encoding="utf-8-sig")

# --- Cross-queue SLA loss propagation ---
# Among breached closed tickets — which originating queue carried them? (We use only currently-known queue, but we can check trajectory if ticket in history)
br_overlap = set(closed.loc[closed["breached"],"Ticket#"].astype(str)) & set(h["ticket_number"].astype(str))
print(f"\nBreached closed tickets also in observed history: {len(br_overlap)}")

summary = {
    "queue_breach_top10": qstat.head(10).reset_index().to_dict(orient="records"),
    "sla_worst_breach_rate_top10": sla_stat.sort_values("breach_rate",ascending=False).head(10).reset_index().to_dict(orient="records"),
    "queue_entropy_top10": q_ent.head(10).reset_index().to_dict(orient="records"),
    "blackhole_top10": bh.head(10)[["queue","seg_count","mean_h","out_n","no_owner_pct","bh_index"]].to_dict(orient="records"),
}
with open(f"{OUT}/06_governance.json","w",encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
print("\nGovernance analysis saved.")
