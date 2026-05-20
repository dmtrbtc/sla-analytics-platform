"""Stage 2: Queue transition graph, residence time, owner moves."""
import pandas as pd, json, sys, io, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SRC = r"D:/SLA_test"
OUT = r"D:/Otrs_SLA/.claude/worktrees/sad-shockley-d10f2d/forensic"

h = pd.read_csv(f"{SRC}/history_2026-05-11_07-00-28.csv", encoding="utf-8-sig")
h["event_time"] = pd.to_datetime(h["event_time"], errors="coerce")
h = h.sort_values(["ticket_id", "event_time"]).reset_index(drop=True)

# --- Build per-ticket queue timeline using Move events + initial queue snapshot ---
# For each ticket, walk the history; use queue_name column (which represents queue at time of event).
# A queue change happens when queue_name changes between consecutive events.
h["prev_queue"] = h.groupby("ticket_id")["queue_name"].shift()
h["prev_time"]  = h.groupby("ticket_id")["event_time"].shift()
moves = h[(h["prev_queue"].notna()) & (h["prev_queue"] != h["queue_name"])].copy()
print(f"Detected queue transitions: {len(moves)} across {moves['ticket_id'].nunique()} tickets")

# Build transition graph (src -> dst, count)
g = moves.groupby(["prev_queue", "queue_name"]).size().reset_index(name="n").sort_values("n", ascending=False)
g.to_csv(f"{OUT}/02_transitions.csv", index=False, encoding="utf-8-sig")
print("\nTop 25 transitions:")
print(g.head(25).to_string(index=False))

# --- Residence time per queue (sum of stay durations across tickets) ---
# Compute queue stay segments per ticket
segments = []
for tid, grp in h.groupby("ticket_id"):
    grp = grp.sort_values("event_time")
    seg_q = None; seg_start = None
    for _, row in grp.iterrows():
        if seg_q is None:
            seg_q = row["queue_name"]; seg_start = row["event_time"]
        elif row["queue_name"] != seg_q:
            segments.append((tid, seg_q, seg_start, row["event_time"]))
            seg_q = row["queue_name"]; seg_start = row["event_time"]
    if seg_q is not None:
        segments.append((tid, seg_q, seg_start, grp["event_time"].max()))
seg = pd.DataFrame(segments, columns=["ticket_id","queue","start","end"])
seg["hours"] = (seg["end"] - seg["start"]).dt.total_seconds()/3600
seg.to_csv(f"{OUT}/02_segments.csv", index=False, encoding="utf-8-sig")

resid = seg.groupby("queue").agg(
    total_h=("hours","sum"),
    mean_h=("hours","mean"),
    median_h=("hours","median"),
    p90_h=("hours", lambda s: s.quantile(0.9)),
    n_segments=("hours","count"),
    n_tickets=("ticket_id","nunique"),
).sort_values("total_h", ascending=False)
resid.to_csv(f"{OUT}/02_queue_residence.csv", encoding="utf-8-sig")
print("\nTop 20 queues by total residence hours (in observed 7-day window):")
print(resid.head(20).to_string())

# --- Bounce detection: tickets visiting same queue more than once (loops) ---
bounce = seg.groupby(["ticket_id","queue"]).size().reset_index(name="visits")
bouncers = bounce[bounce["visits"]>=2].sort_values("visits", ascending=False)
print(f"\nTickets that re-entered the same queue (bounce): {bouncers['ticket_id'].nunique()}")
print(bouncers.head(15).to_string(index=False))
bouncers.to_csv(f"{OUT}/02_bouncers.csv", index=False, encoding="utf-8-sig")

# --- Owner changes ---
own_evt = h[h["event_name"]=="OwnerUpdate"].copy()
own_per_tkt = own_evt.groupby("ticket_id").size().sort_values(ascending=False)
print(f"\nOwnerUpdate events: {len(own_evt)} across {own_evt['ticket_id'].nunique()} tickets")
print("Top reassignment-storm tickets:")
print(own_per_tkt.head(15).to_string())

# Owner reassignment storm = >=3 owner changes for a ticket in observation window
storms = own_per_tkt[own_per_tkt>=3]
print(f"Tickets with >=3 owner changes (reassignment storms): {len(storms)}")

# --- Move events count per ticket → transfer storms ---
moves_per_tkt = moves.groupby("ticket_id").size().sort_values(ascending=False)
xfer_storms = moves_per_tkt[moves_per_tkt>=3]
print(f"Tickets with >=3 queue moves (routing storms): {len(xfer_storms)}")
print(moves_per_tkt.head(15).to_string())

summary = {
    "queue_transitions": int(len(moves)),
    "transition_unique_pairs": int(g.shape[0]),
    "top_transitions": g.head(20).to_dict(orient="records"),
    "queues_by_residence_h_top10": resid.head(10).reset_index().to_dict(orient="records"),
    "bounce_tickets": int(bouncers["ticket_id"].nunique()),
    "owner_reassignment_storms_gte3": int(len(storms)),
    "routing_storms_gte3moves": int(len(xfer_storms)),
}
with open(f"{OUT}/02_flow.json","w",encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
print("\nFlow analysis saved.")
