# SLA Platform — Design Handoff

Три полностью рабочих варианта дизайна SLA Operations / Monitoring. Каждый — самостоятельный self-contained прототип на React + Babel inline (без сборки).

## Структура

```
SLA Monitor/              ← v1: Ant Design light (плотный, под текущий стек)
├── index.html
├── styles.css
├── data.js               ← mock data
├── utils.jsx
├── views.jsx             ← Matrix / Split / Feed
├── drawer.jsx
├── app.jsx
└── tweaks-panel.jsx

SLA Operations Center/    ← v2: Dark NOC (Datadog / Opsgenie стиль)
├── index.html
├── ops.css
├── ops-data.js
├── ops-utils.jsx
├── ops-widgets.jsx       ← KPI strip, Dual metric, Queue map, At-risk, Stream, Bottleneck, Agents
├── ops-drawer.jsx
├── ops-app.jsx
└── tweaks-panel.jsx

SLA Executive/            ← v3: Clean light B2B (Linear / Atlassian Cloud стиль)
├── index.html
├── exec.css
├── exec-data.js
├── exec-utils.jsx
├── exec-app.jsx          ← KPI row, Trends chart, Breaches table, Queue health, Simulator
└── tweaks-panel.jsx
```

## Как открыть

Любой `index.html` открывается напрямую в браузере — JS / CSS / шрифты Inter+JetBrains Mono подгружаются с CDN. Никакого `npm install` не нужно для просмотра.

## Подключение к боевому проекту

Проект использует **React + Ant Design 5 + ECharts + react-query + react-router** (см. `sla-platform/frontend/package.json`).

### Подход 1 — встроить v1 (`SLA Monitor`) почти как есть

`SLA Monitor` уже использует визуальную систему Ant Design (цвета, тени, токены `--color-primary: #1677ff` совпадают с темой по умолчанию). Достаточно:

1. Создать страницу `frontend/src/pages/SLAMonitor.tsx`.
2. Перенести логику из `app.jsx` + `views.jsx` (Matrix / Split / Feed).
3. Заменить mock `data.js` на вызовы существующих API:
   - `slaApi.listQueueRules()` + `slaApi.getQueueBreaches({ days })` → `queueMetrics`
   - `slaApi.listBreaches({ days })` → `tickets`
   - `analyticsApi.overview({ days })` → `KPIS`
4. Заменить кастомные таблицы на `<Table>` Ant Design — поля совпадают (`reaction.breached`, `resolution.breached`, `pct_ok`, `tickets`, `target_response`, `target_resolution`, `calendar`, `priority`).
5. Добавить роут в `App.tsx`: `<Route path="/sla/monitor" element={<SLAMonitor/>}/>` и пункт в `Sidebar.tsx`.

### Подход 2 — v2 (`SLA Operations Center`) как отдельный режим «NOC wall»

Тёмная тема внедряется через CSS-переменные. В Ant Design нужно завернуть в `ConfigProvider` с `theme={{ algorithm: theme.darkAlgorithm }}` или применить отдельный layout вне общей темы (отдельный полноэкранный режим для NOC-стены).

### Подход 3 — v3 (`SLA Executive`) для коммерческих скриншотов / экспортов

Inter + JetBrains Mono, чистая B2B-палитра. Хорошо ложится на отчёты / PDF.

## API соответствие

Все три прототипа спроектированы под уже существующие endpoints из `sla-platform/backend/app/api/sla.py`:

| Виджет | Endpoint |
|---|---|
| KPI strip | `GET /sla/summary?days=N` |
| Queue matrix / health | `GET /sla/queue-breaches?days=N` |
| Breaches table / Feed | `GET /sla/breaches?state=open&days=N` |
| Trend chart | `GET /analytics/overview?days=N` + `GET /analytics/queue-heatmap` |
| Simulator | `POST /sla/simulate` |
| Agent workload (NOC) | `GET /dashboards/agent-workload` |
| Event stream (NOC) | WebSocket `/ws/dashboard` |

## Структура mock-данных (для справки разработчику)

```ts
// Очередь
type Queue = {
  id: string;
  name: string;                           // "Support::L1"
  priority: 0 | 5 | 10 | 20;
  target_response: number;                // sec
  target_resolution: number;              // sec
  calendar: "RU 9-18" | "24×7";
  agents_on?: number;                     // только NOC
  tickets: number;
  open: number;
  at_risk: number;
  avg_wait_min: number;
  health: number;                         // 0-100
  tier: "ok" | "warn" | "high" | "crit";
  reaction:   { in_time, breached, pct_ok, avg_sec, trend: number[] };
  resolution: { in_time, breached, pct_ok, avg_sec, trend: number[] };
};

// Тикет с риском пробития
type AtRiskTicket = {
  id: number;
  ticket_number: string;                  // "T-2024100214"
  title: string;
  queue: string; queue_id: string;
  owner: string;
  priority: "Высокий" | "Средний" | "Низкий";
  created_at: string;
  r_used: number; s_used: number;         // 0-200+ (>100 = breach)
  r_over: boolean; s_over: boolean;
  r_remain_min: number; s_remain_min: number;
  breach_eta_min: number;
  tier: "warn" | "high" | "crit";
};
```

## Что точно нужно учесть при интеграции

- **Локализация:** строки уже в `frontend/src/i18n/locales/ru/common.json` — переиспользовать `slaConfig.responseTime`, `slaConfig.resolutionTime`, `analytics.breachedResponse`, `analytics.breachedResolution` и т.д. Захардкоженные строки в прототипах заменить на `t("...")`.
- **WebSocket для live-режима:** `useWebSocket` хук уже есть в проекте (`src/api/websocket.ts`). Для NOC-варианта подписаться на события `sla_breach`, `ticket_updated`, `queue_overloaded`, `risk_changed`.
- **Тренды:** трендовые массивы в прототипах генерируются клиентом. На бэке нужен endpoint типа `GET /sla/trend?days=N&granularity=day` возвращающий `{ daily: [{ date, reaction_breaches, resolution_breaches, total_tickets }] }`.
- **Severity цвета:** в Executive/Monitor — оранжевый = Реакция (`#d97706` / `#fa8c16`), фиолетовый = Решение (`#7c3aed` / `#722ed1`). Использовать как единую визуальную пару во всех новых виджетах.

## Вопросы Большому Огурцу

1. Какой из трёх вариантов берём за основу? (Рекомендую v1 для быстрой интеграции, v3 для презентаций.)
2. NOC-режим — отдельная страница `/sla/noc` для большого монитора или встроить в `/dashboard/ops`?
3. Симулятор — выносить в отдельную страницу `/sla/simulator` или оставить блоком на главной?
4. Поддерживать light/dark переключение или фиксировать тему?
