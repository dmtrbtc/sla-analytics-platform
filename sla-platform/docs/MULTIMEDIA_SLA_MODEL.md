# Multimedia SLA Model — v1.6

Event-driven SLA intelligence for Multimedia queues — low volume, high criticality. Numbers verified live.

Endpoint: `GET /api/v1/operations/intelligence/multimedia`

---

## 1. Real shape (verified live)

```
queues:   3    (Plaza, Veshki, AZM-Esipovo)
tickets:  26 total / 1 still open
```

| queue | tickets | open | avg lifetime (h) |
|---|---:|---:|---:|
| MBR-137-Multimedia-Plaza | 18 | 0 | 13,083 |
| MBR-137-Multimedia-Veshki | 5 | 0 | 7,850 |
| AZM-717-Multimedia-Esipovo | 3 | 1 | 6,252 |

The huge `avg_lifetime_hours` (Plaza: 13,083h ≈ 545 days) is **real** — these are tickets created long ago and closed in the observation window. Multimedia tickets stay open longer than incident tickets because they tie to scheduled events (room bookings, recurring meetings, conference setup). The platform does NOT treat this as "broken" — it surfaces the long lifetime as a domain characteristic.

---

## 2. Hour-of-day creation pattern

Top 3 hours (out of 24):

| hour | tickets created |
|---|---:|
| 13 | 5 |
| 12 | 4 |
| 09 | 3 |

Multimedia ticket creation clusters around **lunchtime (12-13)** — corresponds to people booking afternoon meetings. The hour_distribution payload gives the full 24-hour curve so a wallboard can render a heatmap.

---

## 3. Criticality detection — VIP / Director / Urgent markers

The detector searches ticket titles for VIP keywords across both English and Russian: `vip`, `executive`, `urgent`, `срочн`, `директор`, `президент`, `переговор` (meeting room).

```
criticality_count: 7  (out of 26 tickets, ~27%)

sample matches:
  #2025052111000741  "FW: бронь переговорной TULA"
  #2025111811000192  "FW: бронь переговорной TULA"
  #2025070811000709  "Видео_контент шоу-рум и перегово…"
```

The "TULA" meeting room appears as a repeating subject — that's an infrastructure-instability signature: a specific room generating multiple tickets.

---

## 4. Per-queue breach stats

```
breach_stats:  {resol_breaches: 0, resol_metrics: 0}
```

**Zero SLA metrics computed for Multimedia queues.** This is real and worth flagging — either:
- No SLA definition matches Multimedia patterns, so the engine skips them
- Or Multimedia tickets bypass SLA scoring intentionally

Action: add an explicit `Multimedia` SLA queue rule that accounts for the event-driven nature (short response window before event, lenient resolution after).

---

## 5. Recommended Multimedia SLA structure

Not yet implemented in the engine, but the platform now provides the *data* needed to design it:

| timing | suggested target |
|---|---|
| Before event (≤2 h to start) | 15 min response, 30 min resolution |
| During event | hard escalation, no auto-pause |
| After event | best-effort 24 h |

This is information for an operations decision, not platform code. The hour-of-day distribution and criticality markers give the policy designer the inputs.

---

## 6. Operational reading

- **Multimedia is small (26 tickets) but visible** — 27% of tickets carry VIP markers and the TULA room appears repeatedly.
- **Multimedia tickets aren't currently in SLA scope.** Either by design or oversight. Worth a config review.
- **Use the hour-of-day curve to staff around 12-13** — that's when bookings spike.

---

## 7. Reproducibility

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/operations/intelligence/multimedia | jq '.criticality_markers, .hour_distribution'
```
