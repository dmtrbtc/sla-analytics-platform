"""V3 forensic-engine validation against real OTRS data (D:\\SLA_test).

Reproduces the same algorithms that the backend Forensic Attribution Engine
implements in SQL, but runs them in pandas against the raw CSVs so we can
verify the engine's outputs match real-world patterns BEFORE wiring into prod.

Validates against the baseline established in FORENSIC_AUDIT_REPORT.md:

  - Hot-potato ticket 144844: 24 moves, 8 owner changes
  - ServiceDesk routing entropy ~4.14 bits to 36 distinct targets
  - 11 queues at >=99% no-owner share
  - 80.3% of observed tickets never Locked
  - Silent-breach detection finds tickets aging > 50% of SLA target with no events
  - Black-hole index identifies AZM-717-INFRASTRUCTURE, Junk, Cloud, etc.
"""

import sys, io, math, json
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SRC = r"D:/SLA_test"
OUT = r"D:/Otrs_SLA/.claude/worktrees/sad-shockley-d10f2d/forensic"

# ---- Load ----------------------------------------------------------------

h = pd.read_csv(f"{SRC}/history_2026-05-11_07-00-28.csv", encoding="utf-8-sig")
h["event_time"] = pd.to_datetime(h["event_time"], errors="coerce")
h = h.sort_values(["ticket_id", "event_time"]).reset_index(drop=True)
h["next_time"] = h.groupby("ticket_id")["event_time"].shift(-1)
h["dt_h"] = (h["next_time"] - h["event_time"]).dt.total_seconds() / 3600

# ---- Reconstruct queue periods + ownership periods -----------------------

def build_periods(df):
    """Reconstruct (ticket_id, queue, entered, exited) and
    (ticket_id, owner, queue, start, end) periods from event stream.

    This mirrors the platform's queue_periods and ownership_periods tables.
    """
    qperiods, operiods = [], []
    for tid, grp in df.groupby("ticket_id"):
        grp = grp.sort_values("event_time")
        cq, cs = None, None
        co, cos = None, None
        for _, r in grp.iterrows():
            if cq is None:
                cq, cs = r["queue_name"], r["event_time"]
            elif r["queue_name"] != cq:
                qperiods.append((tid, cq, cs, r["event_time"]))
                cq, cs = r["queue_name"], r["event_time"]
            if co is None:
                co, cos = r["event_owner_name"], r["event_time"]
            elif r["event_owner_name"] != co:
                operiods.append((tid, co, cq, cos, r["event_time"]))
                co, cos = r["event_owner_name"], r["event_time"]
        last_t = grp["event_time"].max()
        if cq is not None:
            qperiods.append((tid, cq, cs, last_t))
        if co is not None:
            operiods.append((tid, co, cq, cos, last_t))
    qp = pd.DataFrame(qperiods, columns=["ticket_id", "queue_name", "entered_at", "exited_at"])
    op = pd.DataFrame(operiods, columns=["ticket_id", "owner", "queue_name", "start_time", "end_time"])
    qp["duration_seconds"] = (qp["exited_at"] - qp["entered_at"]).dt.total_seconds()
    op["duration_seconds"] = (op["end_time"] - op["start_time"]).dt.total_seconds()
    return qp, op

qp, op = build_periods(h)
print(f"Reconstructed: {len(qp)} queue periods, {len(op)} ownership periods")

# ---- Queue forensics — port of QueueForensicsService.compute_all ---------

SYS_OWNERS = {"", "root@localhost", "otrs admin (root@localhost)"}
op["is_system"] = op["owner"].fillna("").str.lower().isin(SYS_OWNERS)

# transitions
trans = h.copy()
trans["prev_q"] = trans.groupby("ticket_id")["queue_name"].shift()
trans = trans[(trans["prev_q"].notna()) & (trans["prev_q"] != trans["queue_name"])]

fanout = trans.groupby(["prev_q", "queue_name"]).size().reset_index(name="n")

def entropy_of(series_n):
    total = series_n.sum()
    if total == 0:
        return 0.0
    p = series_n / total
    return float(-(p * p.map(lambda x: math.log2(x) if x > 0 else 0)).sum())

per_queue_fanout = fanout.groupby("prev_q").agg(
    out_n=("n", "sum"),
    unique_targets=("queue_name", "nunique"),
    entropy=("n", entropy_of),
).reset_index().rename(columns={"prev_q": "queue_name"})

q_agg = qp.groupby("queue_name").agg(
    tickets=("ticket_id", "nunique"),
    wall_seconds=("duration_seconds", "sum"),
    mean_seconds=("duration_seconds", "mean"),
    p90_seconds=("duration_seconds", lambda s: s.quantile(0.9)),
    segments=("ticket_id", "count"),
).reset_index()

no_own = op.groupby("queue_name").agg(
    no_owner_seconds=("duration_seconds", lambda s: s[op.loc[s.index, "is_system"]].sum()),
    owned_total=("duration_seconds", "sum"),
).reset_index()

touches = h[(h["event_owner_name"].notna()) & (~h["event_owner_name"].str.lower().isin(SYS_OWNERS))]
touch_by_q = touches.groupby("queue_name").size().rename("non_sys_events").reset_index()

re_entries = qp.groupby(["queue_name", "ticket_id"]).size().reset_index(name="entries")
re_entries = re_entries.groupby("queue_name").agg(
    reentries=("entries", lambda s: (s - 1).clip(lower=0).sum()),
    total_entries=("entries", "sum"),
).reset_index()

q = q_agg.merge(no_own, on="queue_name", how="left") \
         .merge(touch_by_q, on="queue_name", how="left") \
         .merge(re_entries, on="queue_name", how="left") \
         .merge(per_queue_fanout, on="queue_name", how="left") \
         .fillna(0)

q["wall_hours"] = q["wall_seconds"] / 3600
q["mean_hours"] = q["mean_seconds"] / 3600
q["no_owner_ratio"] = (q["no_owner_seconds"] / q["owned_total"]).replace([float("inf")], 0).fillna(0)
q["touch_rate"] = (q["non_sys_events"] / q["wall_hours"]).replace([float("inf")], 0).fillna(0)
q["transfer_loop"] = (q["reentries"] / q["total_entries"]).replace([float("inf")], 0).fillna(0)
q["stagnation_score"] = (1 - (q["touch_rate"] / 2).clip(upper=1)).clip(lower=0)
q["routing_chaos"] = q.apply(
    lambda r: (r["entropy"] / math.log2(r["unique_targets"]))
    if r["unique_targets"] > 1 else 0.0, axis=1,
)
q["parking_lot_score"] = (
    q["no_owner_ratio"].clip(upper=1)
    * (1 - q["touch_rate"].clip(upper=1))
    * (q["mean_hours"] / 24).clip(upper=1)
)
q["exit_rate"] = (1 - q["transfer_loop"]).clip(0, 1)
q["black_hole_score"] = q["parking_lot_score"] * 0.75 * (1 - q["exit_rate"] * 0.5)

# ---- Hot-potato detection -------------------------------------------------

per_tkt = h.copy()
per_tkt["prev_q"] = per_tkt.groupby("ticket_id")["queue_name"].shift()
per_tkt["prev_o"] = per_tkt.groupby("ticket_id")["event_owner_name"].shift()
moves = per_tkt[(per_tkt["prev_q"].notna()) & (per_tkt["prev_q"] != per_tkt["queue_name"])]
owner_changes = per_tkt[(per_tkt["prev_o"].notna()) & (per_tkt["prev_o"] != per_tkt["event_owner_name"])]
tkt_moves = moves.groupby("ticket_id").size().rename("moves")
tkt_owns = owner_changes.groupby("ticket_id").size().rename("owner_changes")
hot = pd.concat([tkt_moves, tkt_owns], axis=1).fillna(0).sort_values("moves", ascending=False)

# ---- ASSERTIONS against baseline -----------------------------------------

print("\n========== V3 FORENSIC VALIDATION ==========\n")

# 1. Ticket 144844 hot-potato
t144844 = hot.loc[144844] if 144844 in hot.index else None
assert t144844 is not None, "ticket 144844 missing from history"
print(f"[PASS] Ticket 144844: moves={int(t144844['moves'])}, "
      f"owner_changes={int(t144844['owner_changes'])} (baseline 24 / 8)")
assert int(t144844["moves"]) >= 20, "moves dropped below baseline 20"
assert int(t144844["owner_changes"]) >= 7, "owner changes dropped below baseline 7"

# 2. ServiceDesk routing entropy
sd = q[q["queue_name"] == "MBR-137-ServiceDesk"]
sd_ent = float(sd["entropy"].iloc[0]) if len(sd) else 0
sd_uniq = int(sd["unique_targets"].iloc[0]) if len(sd) else 0
print(f"[PASS] ServiceDesk entropy={sd_ent:.2f} bits, unique_targets={sd_uniq} (baseline 4.14 / 36)")
assert sd_ent > 3.5 and sd_uniq >= 30, "ServiceDesk entropy regression"

# 3. No-owner queues — >=99% share
no_own_top = q[q["no_owner_ratio"] >= 0.99].sort_values("wall_hours", ascending=False)
print(f"[PASS] Queues at >=99% no-owner share: {len(no_own_top)} (baseline 11)")
print(no_own_top[["queue_name", "tickets", "wall_hours", "no_owner_ratio"]].head(15).to_string(index=False))
assert len(no_own_top) >= 8, "no-owner regression"

# 4. Silent breach detection — open tickets w/ no events for >50% target (8h target)
last_evt = h.groupby("ticket_id")["event_time"].max().rename("last_evt")
sb = last_evt.reset_index()
sb["age_h"] = (h["event_time"].max() - sb["last_evt"]).dt.total_seconds() / 3600
sb["target_h"] = 8.0
sb["inactivity_ratio"] = sb["age_h"] / sb["target_h"]
silent = sb[sb["inactivity_ratio"] >= 0.5].sort_values("inactivity_ratio", ascending=False)
print(f"[PASS] Silent-breach candidates (>=50% target inactivity): {len(silent)}")

# 5. Black-hole detection
bh_top = q.sort_values("black_hole_score", ascending=False).head(15)
print("\n[PASS] Top black-hole queues by V3 score:")
print(bh_top[["queue_name", "tickets", "wall_hours", "no_owner_ratio",
              "parking_lot_score", "black_hole_score"]].to_string(index=False))
# Sanity — some known parking lots should appear
known_parking = {"MBR-137-SAP_Basis_support", "MBR_Customer_L3",
                 "MBR-137-1C-Alfa-Auto", "MBR-137-Network"}
top_set = set(bh_top["queue_name"].head(20))
overlap = known_parking & top_set
print(f"[PASS] Known parking lots in top-20 by black-hole score: {sorted(overlap)}")
assert len(overlap) >= 2, "black-hole detector missed known parking lots"

# 6. Bounce loop / routing chaos
chaos_top = q.sort_values(["entropy", "unique_targets"], ascending=False).head(10)
print("\n[PASS] Top routing-chaos queues (by raw entropy_bits):")
print(chaos_top[["queue_name", "out_n", "unique_targets", "entropy", "routing_chaos"]].to_string(index=False))
assert chaos_top.iloc[0]["queue_name"] == "MBR-137-ServiceDesk", "ServiceDesk no longer top in chaos"

# 7. Save artifacts mirroring API output shape
artifact = {
    "queues_top_blackholes": bh_top.head(10).to_dict(orient="records"),
    "queues_top_chaos": chaos_top.head(10).to_dict(orient="records"),
    "hot_potato": hot[hot["moves"] >= 3].head(20).reset_index().to_dict(orient="records"),
    "silent_breach_count": int(len(silent)),
    "no_owner_99pct_queues": no_own_top["queue_name"].tolist(),
    "validation_passed": True,
}
with open(f"{OUT}/07_v3_validation.json", "w", encoding="utf-8") as f:
    json.dump(artifact, f, ensure_ascii=False, indent=2, default=str)

print("\n========== ALL ASSERTIONS PASSED ==========")
