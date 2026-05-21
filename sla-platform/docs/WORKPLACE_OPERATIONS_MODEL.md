# Workplace Operations Model — v1.6

Engineer-load and site-hotspot intelligence for Workplace queues. All numbers verified live.

Endpoint: `GET /api/v1/operations/intelligence/workplace`

---

## 1. Real shape (verified live)

```
queues:   4    (Veshki, Plaza, Esipovo, base "MBR-137-Workplace")
tickets:  134 total / 22 still open
```

---

## 2. Engineer load — overload detected

| engineer | tickets held | hours owned | overload ratio* |
|---|---:|---:|---:|
| **AANOSOV** | **19** | **1,105.7** | **6.91×** |
| **MIKORLO** | 10 | 425.5 | **2.66×** |
| **ARYISKI** | 6 | 437.3 | **2.73×** |
| e137_s_zabbix (bot) | 8 | 3.3 | 0.02× |
| VFOMINF | 3 | 162.1 | 1.01× |

*\* overload_ratio = hours_owned / 160. 1.0 = one FTE-month worth of carry. ≥2.0 flagged as overloaded.*

**3 engineers are operationally overloaded.** AANOSOV alone holds nearly **7× a normal monthly load** — equivalent to 7 FTE-months of cumulative carry. This is a real staffing-distribution problem that the platform surfaces as soon as the dataset is loaded.

---

## 3. Site hotspots

| site | tickets | open now |
|---|---:|---:|
| **Veshki** | 60 | 7 |
| Plaza | 47 | 4 |
| **Esipovo** | 19 | **11** |
| Other | 8 | 0 |

**Esipovo has 11 of 19 still open** (58% open rate). That's the live operational pressure point right now. Veshki has the most total volume but its closure rate is healthier.

---

## 4. Site MTTA / MTTR

| site | MTTA | MTTR | breaches |
|---|---:|---:|---:|
| Veshki | 18,013 s (5.0 h) | 295,318 s (82.0 h) | **64** |
| Esipovo | 23,261 s (6.5 h) | 238,177 s (66.2 h) | 24 |
| Plaza | **1,609 s (0.45 h)** | 115,089 s (32.0 h) | 26 |
| Other | — | — | 0 |

- **Plaza acknowledges fast** (median 27 minutes) — best MTTA in the dataset.
- **Veshki has worst MTTR** (82 h average) and most breaches (64).
- **Esipovo's MTTA is slowest** (6.5 h) and 11 of 19 tickets are still open — Esipovo needs more engineers or shorter triage time.

---

## 5. Repeat customers

```
repeat_customers (≥3 tickets in scope): 0
```

No customer has filed ≥3 Workplace tickets in the observed window. Either truly no repeats, or each ticket is a one-off incident. The detector is live and ready to surface them as soon as the dataset grows.

---

## 6. Operational reading

1. **Rebalance AANOSOV's load**. 19 tickets / 1105 hours is unsustainable. Either redistribute or escalate to staffing.
2. **Esipovo is the live hotspot** — 11 open tickets of 19, slowest MTTA. Either staff it or route Esipovo tickets to Plaza-rated engineers during peak hours.
3. **Veshki has the worst MTTR** — investigate. Either the work is genuinely longer there, or there's a process-stall pattern not yet visible in events.

---

## 7. Reproducibility

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/operations/intelligence/workplace | jq

# Cross-check engineer load via psql
docker exec sla-platform-postgres-1 psql -U sla_user -d sla_platform -c "
SELECT owner, COUNT(DISTINCT ticket_id) AS tickets,
       ROUND(SUM(EXTRACT(EPOCH FROM (COALESCE(end_time, NOW()) - start_time)))/3600, 1) AS hours
FROM ownership_periods
WHERE queue_name ILIKE '%workplace%'
  AND LOWER(owner) NOT IN ('root@localhost','otrs admin (root@localhost)','')
GROUP BY owner ORDER BY tickets DESC LIMIT 5;
"
```
