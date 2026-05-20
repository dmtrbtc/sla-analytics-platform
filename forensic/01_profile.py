"""Stage 1: Load + profile all 4 production data files."""
import pandas as pd
import json, sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SRC = r"D:/SLA_test"
OUT = r"D:/Otrs_SLA/.claude/worktrees/sad-shockley-d10f2d/forensic"

backlog = pd.read_csv(f"{SRC}/backlog_2026-05-11_07-00-26.csv", encoding="utf-8-sig")
history = pd.read_csv(f"{SRC}/history_2026-05-11_07-00-28.csv", encoding="utf-8-sig")
open_xl = pd.read_excel(f"{SRC}/List_of_open_tickets_sorted_by_time_left_until_solution_deadline.xlsx")
closed  = pd.read_csv(f"{SRC}/List_of_tickets_closed_sorted_by_solution_time_Created_2026_05_20.csv",
                     sep=";", encoding="utf-8-sig", on_bad_lines="skip", low_memory=False)

print("=== BACKLOG ===")
print("rows:", len(backlog), "cols:", list(backlog.columns))
print(backlog["current_state_name"].value_counts().head(20).to_string())
print()
print("=== HISTORY ===")
print("rows:", len(history), "cols:", list(history.columns))
print("unique tickets:", history["ticket_id"].nunique())
print("event_name top:")
print(history["event_name"].value_counts().head(30).to_string())
print()
print("=== OPEN (xlsx) ===")
print("rows:", len(open_xl), "cols(first 25):", list(open_xl.columns)[:25])
print("total cols:", len(open_xl.columns))
print()
print("=== CLOSED ===")
print("rows:", len(closed), "cols(first 25):", list(closed.columns)[:25])

# Time bounds
history["event_time"] = pd.to_datetime(history["event_time"], errors="coerce")
print("\nhistory event_time:", history["event_time"].min(), "->", history["event_time"].max())
backlog["ticket_created_time"] = pd.to_datetime(backlog["ticket_created_time"], errors="coerce")
print("backlog created:", backlog["ticket_created_time"].min(), "->", backlog["ticket_created_time"].max())

# Save quick profile
prof = {
    "backlog_rows": int(len(backlog)),
    "history_rows": int(len(history)),
    "history_tickets": int(history["ticket_id"].nunique()),
    "open_xl_rows": int(len(open_xl)),
    "closed_rows": int(len(closed)),
    "backlog_state_dist": backlog["current_state_name"].value_counts().to_dict(),
    "backlog_queue_dist_top20": backlog["current_queue_name"].value_counts().head(20).to_dict(),
    "history_event_top": history["event_name"].value_counts().head(40).to_dict(),
    "history_time_min": str(history["event_time"].min()),
    "history_time_max": str(history["event_time"].max()),
}
with open(f"{OUT}/01_profile.json", "w", encoding="utf-8") as f:
    json.dump(prof, f, ensure_ascii=False, indent=2, default=str)
print("\nProfile saved.")
