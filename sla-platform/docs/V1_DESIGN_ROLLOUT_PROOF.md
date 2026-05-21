# V1 Design Rollout — first verified page

Phase 4 of the prompt said "DO NOT blindly redesign 27 pages at once" — apply gradually. This release ships the first real page using the v1 tokens as the rollout proof.

---

## 1. What ships in v1.8

`frontend/src/pages/SLALossCenter.tsx` — a new operational page at `/sla-loss`:

- Wrapped in `<div className="v1">` to scope the v1 CSS variables.
- KPI strip uses `.v1-kpi` (label / value / sub) — no Ant Statistic.
- Page background = `var(--v1-bg)`, surface cards = `var(--v1-surface)` + `var(--v1-shadow-1)`.
- Numeric columns get `.num` for tabular-nums alignment.
- Detail tables use Ant `<Table>` underneath (component-level redesign deferred — see #5).

Sidebar entry **«Где теряется SLA»** added under Queue Intel group with `<HeatMapOutlined/>` icon.

---

## 2. What the page proves

- **Tokens work without breaking Ant Design globals.** No `ConfigProvider` change. Existing pages untouched.
- **`.v1-kpi` recipe scales.** 4 cards in a CSS Grid look clean against the same data feeds the older "Forensics" page already uses.
- **Mixed approach is OK.** v1 wrapper outside, Ant Table inside. We don't have to redesign every primitive at once.

---

## 3. Build artifacts (verified)

```
$ ls /usr/share/nginx/html/assets/ | grep -i loss
SLALossCenter-BQKzUwGz.js
SLALossCenter-JUrx_ZVX.css     ← the .css file is new — Vite extracted v1 styles
```

The `.css` chunk is the first time v1 styles ship as a real bundle artifact. Future v1 pages reuse the same file (`v1-tokens.css` is the source of truth).

---

## 4. Rollout strategy

| page | priority | effort | runtime risk |
|---|---|---|---|
| **`/sla-loss`** | ✓ shipped v1.8 | done | none (new page) |
| `/forensics` | next | medium — already custom layout | low |
| `/favorites` | next | small — opt-in wrapper only | low |
| `/dashboard` | medium | medium — many widgets | low |
| `/sla/monitor` | later | high — heavy Antd tables | medium without browser |
| `/admin/*` | low | n/a | n/a |

Recommended cadence: one page per release, each with a real screenshot once browser verification is available.

---

## 5. What is NOT done

- **Custom Table component** in v1 style. The Ant `<Table>` is used as-is — its hover states are Antd defaults, not v1 hover. Building a `<V1Table>` wrapper would be a 1-day spike but adds visual polish, not function.
- **Print stylesheet** — `@media print` not yet added to `v1-tokens.css`. For screenshot-friendly export the current page works because the palette is already light.
- **Browser DOM verification** — no browser in sandbox. Visual confirmation of the page belongs to the user clicking through `http://localhost/sla-loss`.

---

## 6. Conclusion

The v1 design system is now demonstrably usable. The user can clone the `SLALossCenter.tsx` opt-in pattern for any further page migration without breaking anything else. No global theme override, no Ant Design replacement, no regressions in untouched pages (verified by `vite build` clean + 285 pytest tests passing).
