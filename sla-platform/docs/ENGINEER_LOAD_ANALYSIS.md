# Engineer Load & SPOF Analysis — v2.0.0

New `/operations/engineer-load/overload-risk` endpoint surfaces operational human-risk at three angles: overload, single-point-of-failure (SPOF), reassignment pressure.

---

## VERIFIED (live, paste-from-curl + psql)

### Endpoint live

```
$ curl -H "Authorization: Bearer $TOKEN" \
    "http://localhost:8000/api/v1/operations/engineer-load/overload-risk?threshold_ratio=2.0"
HTTP 200, 11,564 bytes
```

Returns 36 engineers, **13 flagged** (overloaded OR SPOF OR both).

### Top 5 by overload_ratio (live, real OTRS data)

| owner | tickets | hours | overload | SPOF queues | flags |
|---|---:|---:|---:|---:|---|
| **TEC721** | — | — | **12.14×** | 0 | OVERLOAD |
| **AANOSOV** | — | — | **9.74×** | 0 | OVERLOAD |
| **ANTOSMI** | — | — | **6.65×** | 0 | OVERLOAD |
| **RSVETOV** | — | — | **5.08×** | 0 | OVERLOAD |
| **ARYISKI** | — | — | **4.54×** | 0 | OVERLOAD |

### Single-point-of-failure detection — psql cross-check

```sql
WITH per_q AS (
  SELECT queue_name,
         COUNT(DISTINCT owner) FILTER (...) AS unique_owners,
         MAX(owner) FILTER (...) AS sole_owner
  FROM ownership_periods GROUP BY queue_name
  HAVING COUNT(DISTINCT owner) FILTER (...) = 1
)
SELECT sole_owner, COUNT(*) AS spof_queues, ARRAY_AGG(queue_name) FROM per_q
GROUP BY sole_owner ORDER BY spof_queues DESC;
```

Live result:

| sole_owner | SPOF queues | queues |
|---|---:|---|
| **VARTAMO** | **2** | `MBR-137-AssetManagement_L2`, `MBR-137-Security` |
| MIKORLO | 1 | `MBR-137-1C-Alfa-Auto` ← known black-hole queue |
| MSTEPAN | 1 | `MBR-137-DC-MonitoringSupport` |
| KICHERE | 1 | `MBR-137-AMS_L2` |
| VFOMINF | 1 | `MBR-137-Telecom` |
| VSILANT | 1 | `MBR-137-Security-SupportL1` |
| RBURHAN | 1 | `MBM_RU_Diasoft` |

API output matches psql exactly:
```
VARTAMO  overload=0.90x  spof_queues=2  load_balance=0.66  flags=[SPOF]
MIKORLO  overload=4.29x  spof_queues=1  load_balance=0.52  flags=[OVERLOAD,SPOF]
VSILANT  overload=2.34x  spof_queues=1  load_balance=0.68  flags=[OVERLOAD,SPOF]
```

### Real operational findings

1. **MIKORLO is the worst single risk**: overloaded 4.3× monthly FTE **and** sole owner of MBR-137-1C-Alfa-Auto (one of the top-3 black-hole queues from the v1.5 forensic audit). If MIKORLO is out, that queue has nobody.
2. **VARTAMO** holds 2 SPOF queues (`AssetManagement_L2`, `Security`). Two-queue dependency.
3. **VSILANT**: overloaded 2.3× AND sole owner of `Security-SupportL1`. Critical risk.
4. **TEC721 at 12.14× monthly FTE** is the most overloaded individual in the dataset — even higher than AANOSOV (9.74×).
5. **13 of 36 engineers are flagged** — 36% of the engineering pool is operationally at risk by overload or SPOF.

---

## Composite metrics

```python
overload_ratio       = hours_owned / 160      # 1.0 = one FTE-month carry
spof_risk_queues     = count of queues where this person is the sole non-system owner
reassign_pressure    = times this person was reassigned-FROM (lost ownership)
load_balance_score   = 1 - (0.4 * min(1, overload/5) + 0.4 * min(1, spof/3))
                       (0 = lone carrier under siege, 1 = healthy distribution)
```

A score `< 0.6` combined with either OVERLOAD or SPOF flag is a real risk.

---

## NOT VERIFIED

| Item | Why |
|---|---|
| Frontend UI for this data | Not yet wired into a page in this release. API client `operationsReviewApi.engineerLoad()` is shipped, so the next iteration can render it without backend changes. |
| Burnout-risk score (the prompt requested it) | Burnout requires a temporal signal (load_ratio trend over time). Current implementation reports instantaneous load only; the trend table needs `ownership_periods_history` snapshots to build properly. Not built in v2.0. |
| Predicted overload trajectory | Same — needs time-series history per engineer. |

---

## Reproducibility

```bash
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -d '{"email":"admin","password":"admin123"}' \
  -H 'Content-Type: application/json' | jq -r .access_token)

curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/operations/engineer-load/overload-risk?threshold_ratio=2.0" \
  | jq '.flagged_count, .flagged_engineers[0:5][] | {owner,overload_ratio,spof_risk_queues,spof_queue_names,flag_overloaded,flag_spof}'

# psql cross-check SPOF:
docker exec sla-platform-postgres-1 psql -U sla_user -d sla_platform -c "
WITH per_q AS (...same SQL as above...)
SELECT sole_owner, COUNT(*) FROM per_q GROUP BY sole_owner ORDER BY 2 DESC;"
```
