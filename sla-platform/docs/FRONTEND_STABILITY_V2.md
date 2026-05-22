# Frontend Stability V2 — v2.0.0 status

State of the runtime-stability guarantees the platform offers after v2.0.

---

## What is structurally guaranteed

| Guarantee | Mechanism | How to verify |
|---|---|---|
| No hook-order violation in any `.ts/.tsx` file | `react-hooks/rules-of-hooks` set to ERROR in `.eslintrc.cjs` | `npm run lint:hooks` exits 0 |
| No `jsx-key` warning that crashes lists | `react/jsx-key` ERROR | same lint pass |
| No direct state mutation in class components | `react/no-direct-mutation-state` ERROR | same |
| A crash inside any lazy-loaded route shows a contained `<Result/>` instead of a white screen | `<RuntimeErrorBoundary resetKey={pathname}/>` wraps the `<Suspense/>` inside the `SuspenseWrapper` in `App.tsx` | grep `App.tsx` |
| Each per-queue widget has its own boundary | `QueueCommandView` and `ForensicTimelineVisual` are wrapped by their own boundaries keyed on `queueName` / `ticketId` | grep |
| Per-route auto-reset of an old error state on navigation | `RuntimeErrorBoundary.componentDidUpdate` watches `resetKey` | code inspection |

---

## v2.0 new pages — stability checklist (all PASS)

| page | useQuery? | useMemo? | hooks-first? | wrapped in boundary? |
|---|---|---|---|---|
| `SLAReviewMode` | ✓ | ✓ (1) | ✓ | ✓ outer + own inner |
| `WallboardOps` | ✓ | ✓ (1) | ✓ | ✓ |
| `TicketTimelinePage` | (none — leaf) | (none) | n/a | ✓ |
| `ForensicTimelineVisual` | ✓ | ✓ (2) | ✓ | ✓ |
| `QueueCommandView` (v1.9) | ✓ | ✓ (2) | ✓ | ✓ |
| `WorkplaceCommandCenter` (v1.9) | (none — composite) | (none) | n/a | inherits via children |
| `AssetCommandCenter` (v1.9) | same | same | n/a | inherits |
| `SLALossCenter` (v1.8) | ✓ | ✓ (2) | ✓ (fixed) | ✓ |
| `SLAForensicCommandCenter` (v1.5 + v1.8.1 fix) | ✓ | ✓ (3) | ✓ (fixed) | ✓ |

`npm run lint:hooks` exits 0 across all of the above.

---

## What is NOT yet guaranteed

| Hole | Reason | Suggested fix |
|---|---|---|
| Errors thrown inside event handlers / async callbacks | React's `componentDidCatch` only catches render-phase errors | Wrap mutation handlers in `try/catch` + show `message.error` |
| Errors inside `useEffect` cleanups | Same | Limit cleanups to defensive sync code |
| WebSocket disconnect UX | Not built | Add a "WS offline" badge in `AppLayout` reading `websocket_manager` count |
| Stale-data indicator | Not built | TanStack Query has `isStale` — surface it as a small grey dot |
| Failed-query retry button | Boundary fallback has its own "Перезагрузить блок" — but `SafeQueryBoundary` doesn't yet | Add retry button to SafeQueryBoundary's error state |
| Loading skeleton consistency | Currently uses `<Spin/>`; some pages use Antd's `<Skeleton/>` | A `<SkeletonBlock/>` helper would unify |
| Frontend telemetry panel | Not built | A small admin-only `/system/frontend-telemetry` page reading `window.performance` + recent boundary catches |

---

## Bug class history (post-v1.8.1)

| Bug class | Last seen | How prevented |
|---|---|---|
| Hooks after conditional return | v1.8.0 (`SLALossCenter`, `SLAForensicCommandCenter`) — found & fixed in v1.8.1 | `react-hooks/rules-of-hooks` ERROR; new pages must follow the pattern |
| Undefined-access after early-data render | v1.8.0 (same pages) — fixed by optional chaining in deps | New code uses `d?.field` consistently |
| Backend-frontend route 404 (double-prefix) | v1.3.0 (`attachments`) — fixed in v1.3.1 | Route registration walk runs in deploy smoke |
| Wrong metric_name filter | v1.3.0 (`response_time` vs `first_response_time`) — fixed in v1.3.1 | The dashboard service now uses `.in_(...)` with both names |

---

## VERIFIED at v2.0 release

```
lint:hooks                     exit 0
npm run build                  ✓ built clean (~17s, 0 TS errors)
pytest backend                 285 passed
docker compose ps              backend + frontend + worker + postgres + redis all Up
backend /health                {"status":"healthy", "version":"2.0.0"}
endpoint count                 219 paths
SPA routes via nginx           8/8 verified routes return HTTP 200
chunks present in /assets/     SLAReviewMode, WallboardOps, TicketTimelinePage,
                               SLALossCenter, SLAForensicCommandCenter,
                               QueueForensics, Favorites, WorkplaceCommandCenter,
                               AssetCommandCenter, Dashboard
```

---

## NOT VERIFIED at v2.0 release

- Browser DOM rendering of the 4 new pages (`/review`, `/wallboard-ops/workplace`, `/wallboard-ops/asset`, `/tickets/:id/timeline`)
- Real TV / external-monitor rendering of WallboardOps
- 30-second auto-refresh long-running stability
- Tooltip alignment on tiny timeline segments at small viewport widths
- 108 lint warnings (exhaustive-deps + unused-vars) — hygiene, not crashes
