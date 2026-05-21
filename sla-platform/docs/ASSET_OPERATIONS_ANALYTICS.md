# Asset Management Operations Analytics — v1.6

Long-lifecycle queue analytics specific to AssetManagement. All numbers verified live.

Endpoint: `GET /api/v1/operations/intelligence/assetmanagement`

---

## 1. Real shape (verified live)

```
queues:        5
tickets:       161 total / 27 still open
```

| queue | tickets touching | mean stay (h) | no-owner % | resol breaches |
|---|---:|---:|---:|---:|
| `MBR-137-AssetManagement_L2` | 1 | 19.2 | **99.7%** | 12 / 24 |
| `AZM-717-AssetManagement_Esipovo_L2` | 12 | 44.9 | 5.6% | **46 / 48** |
| `MBR-137-AssetManagement-Veshki` | 9 | 36.9 | 0.0% | 26 / 28 |
| `MBR-137-AssetManagement-Plaza` | 7 | 56.2 | 0.0% | 18 / 28 |
| `AZM-717-AssetManagement_Esipovo` | — | 38.1 | 0% | 4 / 4 |

---

## 2. Two real defects surfaced

### Defect A — `MBR-137-AssetManagement_L2`: 99.7% no-owner
Only one ticket has ever visited but ownership periods show 99.7% of holding time recorded against `root@localhost`. The queue effectively has **no human owner**. The platform flags it via `no_owner_pct` in `per_queue_pathology`.

### Defect B — `AZM-717-AssetManagement_Esipovo_L2`: 96% breach rate
46 of 48 resolution metrics breach. Either the SLA target is wrong for this queue, or the team can't service it at current capacity. Both are operational decisions — the platform surfaces the signal.

---

## 3. Dormant ticket detection

Tickets currently **open** with no non-system events in 30+ days:

```
dormant_count: 16
sample (top 5 by dormancy):
  #2026040211000607  MBR-137-AssetManagement_L2          owner=None  49 days dormant
  #2026041411000381  AZM-717-AssetManagement_Esipovo_L2  owner=None  37 days dormant
  #2026042211000687  MBR-137-AssetManagement_L2          owner=None  29 days dormant
  #2026042711000427  AZM-717-AssetManagement_Esipovo_L2  owner=None  24 days dormant
  #2026042911000218  AZM-717-AssetManagement_Esipovo_L2  owner=None  22 days dormant
```

All five have `owner=None` (root). These are the "forgotten approvals / warehouse black holes" the user's prompt describes — and they're real.

---

## 4. Pending-state behavior

Pending state hits across Asset queues (proxy for waiting on vendor / logistics):

| state | hits |
|---|---:|
| `pending reminder` | **1596** |
| `pending auto close+` | 738 |

Asset queues are heavily pending-driven. The current V2 SLA engine subtracts pending time from active-time SLA — meaning even though wall-clock breaches mount, active-time SLA reports look healthier. The V3 wall-clock metric exposes this gap directly. For Asset queues specifically, a logistics-aware SLA policy that distinguishes "waiting for vendor" from "agent idle" would improve accuracy.

---

## 5. Reopens

```
reopen_events:       0
distinct_reopened:   0
```

Live data shows zero reopens across Asset queues — the historical export doesn't capture reopen events. This is either an export limitation or a real signal that closed Asset tickets stay closed. The platform passes it through honestly.

---

## 6. Operational reading

1. **`MBR-137-AssetManagement_L2` needs a permanent owner**, not root@localhost. The queue has zero human accountability today.
2. **`AZM-717-AssetManagement_Esipovo_L2` SLA is unrealistic** at 96% breach — either renegotiate or split into sub-queues by category.
3. **16 dormant tickets need an aging policy** — 30-day stale-without-events should auto-escalate or auto-close-with-warning.
4. **Pending-state usage is heavy** — when a customer reports "my Asset SLA is wrong", it's almost certainly the pause-subtraction divergence. Always show wall-clock SLA alongside active-time SLA in Asset reports.

---

## 7. Reproducibility

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/operations/intelligence/assetmanagement | jq
```
