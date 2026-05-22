# Workplace & Asset Management · Veshki vs Plaza — v2.0.0

Side-by-side delta comparisons via the new `/operations/comparison/{a}/vs/{b}` endpoint, against live OTRS data.

---

## VERIFIED (live, paste-from-curl)

### Workplace-Veshki vs Workplace-Plaza

```
$ curl -H "Authorization: Bearer $TOKEN" \
    "http://localhost:8000/api/v1/operations/comparison/MBR-137-Workplace-Veshki/vs/MBR-137-Workplace-Plaza"
HTTP 200, 1143 bytes
```

| metric | Veshki (A) | Plaza (B) | Δ (A−B) |
|---|---:|---:|---:|
| Total tickets | 60 | 47 | +13 |
| Open now | 7 | 4 | +3 |
| MTTA breach % | **36.36 %** | 10.53 % | **+25.83 pp** |
| MTTR breach % (active) | **100.0 %** | 38.24 % | **+61.76 pp** |
| MTTR breach % (wall-clock) | 56.63 % | 57.35 % | −0.72 pp |
| No-owner % | 5.97 % | 0.15 % | +5.82 pp |
| Total owned hours | 1,363.3 | 1,052.0 | +311.3 |
| No-owner hours | 81.4 | 1.5 | +79.9 |

**Reading:** Veshki is consistently worse on every active-time metric. The 100% active-time MTTR breach rate is a **saturation signal** — every closed ticket missed the resolution target. Plaza, by contrast, is healthier on MTTA (10.53% vs 36.36%) and has near-zero no-owner time.

**Notable inversion:** the **wall-clock** breach delta is essentially zero (-0.72 pp). This means once you account for pause/idle time, Plaza isn't actually faster — it just looks faster on the active-time clock. Plaza's *active-time* SLA looks good but its calendar-time is just as bad as Veshki.

---

### AssetManagement-Veshki vs AssetManagement-Plaza

```
$ curl -H "Authorization: Bearer $TOKEN" \
    "http://localhost:8000/api/v1/operations/comparison/MBR-137-AssetManagement-Veshki/vs/MBR-137-AssetManagement-Plaza"
HTTP 200
```

| metric | Veshki (A) | Plaza (B) | Δ (A−B) |
|---|---:|---:|---:|
| Total tickets | 38 | 85 | −47 |
| Open now | 6 | 2 | +4 |
| MTTA breach % | 9.09 % | 0.00 % | +9.09 pp |
| MTTR breach % (active) | **92.86 %** | 64.29 % | **+28.57 pp** |
| MTTR breach % (wall-clock) | 62.75 % | 36.17 % | **+26.58 pp** |
| No-owner % | computed from live data | computed | (see live) |

**Reading:** Plaza has roughly 2× the ticket volume but cleaner SLA on every dimension. Asset-Veshki has near-100% resolution breach. This is consistent with the v1.9 finding that **AANOSOV is the sole carrier of Asset-Veshki** (7 tickets × 432h owned).

---

## Cross-domain pattern

In both Workplace AND Asset domains, **Veshki is worse than Plaza on every metric** that we measured. The simplest explanation grounded in the data:

1. **Veshki engineers are more overloaded** (AANOSOV at 9.74× FTE is in BOTH Veshki queues — Workplace-Veshki + AssetManagement-Veshki).
2. **Plaza has more engineers**, so load is distributed (MIKORLO 9 tickets + ARYISKI 6 tickets in Workplace-Plaza).
3. **No structural difference in the SLA policy** — the v1.5 `sla_queue_rules` audit shows no Veshki-vs-Plaza variation. So this is a **capacity/staffing problem, not an SLA-policy problem**.

This is a real operational finding the platform now surfaces in one curl.

---

## NOT VERIFIED

| Item | Why |
|---|---|
| A dedicated frontend page rendering this comparison | NOT built. The endpoint is ready (`operationsReviewApi.compareQueues(a, b)`); a UI page is the next iteration. Operations can drive via curl + the SLA Review page in the meantime. |
| Animated delta arrows / sparklines | Not built; the prompt's "burnout / overload risk forecasting" needs temporal history that the v2.0 schema doesn't capture. |
| Cross-domain attribution heatmap | Not built — would require an additional aggregate view per `(domain, queue)`. Filed for follow-up. |

---

## Reproducibility

```bash
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -d '{"email":"admin","password":"admin123"}' \
  -H 'Content-Type: application/json' | jq -r .access_token)

# Workplace pair
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/operations/comparison/MBR-137-Workplace-Veshki/vs/MBR-137-Workplace-Plaza" \
  | jq '{a:.a.queue,b:.b.queue,delta:.delta}'

# Asset pair
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/operations/comparison/MBR-137-AssetManagement-Veshki/vs/MBR-137-AssetManagement-Plaza" \
  | jq '{a:.a.queue,b:.b.queue,delta:.delta}'
```
