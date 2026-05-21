# ServiceDesk Forensics — v1.6

How the platform analyzes the ServiceDesk routing-hub pathology, with live numbers from the running stack.

---

## 1. Real shape (verified live)

```
queues:                 1   (MBR-137-ServiceDesk)
tickets:                255 total / 87 still open
ROUTING_QUALITY_SCORE:  79.81 / 100   ← medium-poor
```

Endpoint: `GET /api/v1/operations/intelligence/servicedesk`

---

## 2. Outbound routing — top 5 destinations

| destination queue | transition count | distinct tickets |
|---|---:|---:|
| `MBR-137-1C-Alfa-Auto` | **516** | **86** |
| `MBR-137-Network` | 138 | 23 |
| `MBR-137-Workplace-Veshki` | 138 | 23 |
| `MBR-137-Workplace-Plaza` | 120 | 20 |
| `MBR-137-Security` | 102 | 17 |

ServiceDesk sends 516 transitions to 1C-Alfa-Auto on 86 distinct tickets — meaning the average ticket is moved there ~6 times. That is **the** routing loop signature.

---

## 3. Inbound — who sends back to ServiceDesk

| source queue | back-edges |
|---|---:|
| `MBR-137-Security` | **126** |
| `MBR-137-DC-WintelOperations` | 30 |
| `MBR-137-OfficeAutomation` | 30 |
| `MBR-137-AMS_L2` | 18 |
| `ATL-763-ServiceDesk` | 12 |

ServiceDesk sends Security 102 tickets and gets 126 back. **Net flow is inverted** — Security is bouncing tickets back to ServiceDesk more than ServiceDesk dispatches to them. Operationally this is a ping-pong escalation pattern, not L1→L2 escalation.

---

## 4. Routing loops (live)

10 distinct tickets revisited ServiceDesk ≥2 times (i.e. were sent out, came back, possibly multiple times). Each is a measurable failure of triage stability.

The hottest hot-potato sits in this set: `2026042711001301` made 72 queue moves across 4 queues with 36 owner changes — re-entry pattern.

---

## 5. Ownership acquisition

```
tickets_with_real_owner:    54
avg_acquisition_hours:      1.21
median_acquisition_hours:   0.0   ← when ServiceDesk owns it, it's instant
p90_acquisition_hours:      0.0
tickets_never_owned:        1 (0.4%)
```

So ownership isn't slow in ServiceDesk — when it happens it's immediate. The failure mode is the **routing** decision afterwards, not the pickup.

---

## 6. Routing-quality score formula

```python
routing_quality_score = 100 × (
    1
    - 0.5 × min(1, bounce_factor)            # re-entries / total entries
    - 0.3 × min(1, loops / tickets_total)    # tickets with ≥2 visits / total
    - 0.2 × min(1, never_owned_ratio)
)
```

Current live numbers:
```
bounce_factor:            0.3786
loop_ratio:               10 / 255 = 0.0392
never_owned_ratio:        1 / 255 = 0.004
→ score = 100 × (1 - 0.189 - 0.012 - 0.001) = 79.81
```

A score above ~85 would mean clean routing; below ~70 would mean systemic loops.

---

## 7. Operational reading

- **The single biggest leak** is the `ServiceDesk → 1C-Alfa-Auto` channel: 516 transitions on only 86 tickets means each ticket cycles through there about 6 times. Combined with `1C-Alfa-Auto`'s 86% no-owner share (see `REAL_QUEUE_FINDINGS.md`), this is the dominant operational waste source in the dataset.
- **Security ping-pong**: ServiceDesk dispatches 102, gets 126 back. Need a clear routing rule that prevents Security from re-dispatching to ServiceDesk.
- **Ownership is fine**: 0.4% never-owned rate, instant median pickup. Don't waste effort on L1 staffing — the cost is downstream.

---

## 8. Reproducibility

```bash
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -d '{"email":"admin","password":"admin123"}' \
  -H 'Content-Type: application/json' | jq -r .access_token)
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/operations/intelligence/servicedesk
```
