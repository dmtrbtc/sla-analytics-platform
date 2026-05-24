# Интеграция SLA Portal в sla-platform/frontend

Этот документ — пошаговый план для Claude Code.
Канонический дизайн: **`SLA Portal/`** в корне репозитория.
Правила дизайна на будущее: **`CLAUDE.md`** + **`DESIGN_SYSTEM.md`**.

---

## Цели

1. Добавить страницу `/sla/portal` с дизайном из `SLA Portal/index.html`.
2. Создать переиспользуемые компоненты дизайн-системы под `frontend/src/design/`.
3. Прописать AntD theme + ECharts theme через токены дизайн-системы.
4. На будущие задачи Claude Code обязан использовать эту систему.

## Шаги

### Шаг 1 — Дизайн-токены

Создать `frontend/src/design/tokens.css` — скопировать `:root { ... }` блок из `DESIGN_SYSTEM.md` (раздел 1).

В `frontend/src/main.tsx` добавить импорт:
```tsx
import "@/design/tokens.css";
```

### Шаг 2 — AntD theme

Создать `frontend/src/design/theme.ts` со значениями из `DESIGN_SYSTEM.md` (раздел 2).

В `App.tsx`:
```tsx
import { ConfigProvider } from "antd";
import { theme } from "@/design/theme";

return <ConfigProvider theme={theme}>...</ConfigProvider>;
```

### Шаг 3 — ECharts theme

Создать `frontend/src/design/echarts-theme.ts` из `DESIGN_SYSTEM.md` (раздел 3).
Регистрируется один раз в `main.tsx`. Все ECharts-чарты подключают `theme="sla"`.

Существующие графики в проекте (`DashboardOps.tsx::buildHeatmapOption`, `DashboardTeam.tsx`, etc.) — перевести на theme="sla" и убрать жёстко заданные цвета.

### Шаг 4 — Дизайн-компоненты

Создать под `frontend/src/design/components/`:

- `KpiCard.tsx` — карточка с label/value/icon/delta/foot (см. `.kpi` в `SLA Portal/portal.css`)
- `HealthPip.tsx` — цветной кружок 0–100 (`.hp` в CSS)
- `MetricBar.tsx` — двухсегментный бар (`.bar-cell` в CSS)
- `Sparkline.tsx` — inline SVG sparkline
- `ScopeChips.tsx` — фильтр-чипы из topbar
- `SortableHeader.tsx` — wrapper над AntD Table `column.sorter` с фирменной стрелочкой
- `DetailDrawer.tsx` — общий drawer 640px (см. `.drawer` в CSS)
- `LivePill.tsx` — зелёная пульсирующая точка «live»

Каждый компонент — TypeScript, props задокументированы, использует только токены из `tokens.css`.

### Шаг 5 — Страница SLA Portal

Создать `frontend/src/pages/SLAPortal.tsx`. Структурно — `SLA Portal/portal-app.jsx`, но:

- Импорт компонентов из `@/design/components/`
- Графики через `<ReactECharts theme="sla" />` (StackedArea / HorizontalBar / Heatmap / HourBar)
- Mock-данные заменить на `useQuery`:

```ts
const { data: queues } = useQuery({
  queryKey: ["sla-queue-breaches", period, scope, calendar],
  queryFn: async () => (await slaApi.getQueueBreaches({ days: period, scope, calendar })).data.queues,
  refetchInterval: 30_000,
});

const { data: dailyTotal } = useQuery({
  queryKey: ["sla-daily-trend", period, scope, calendar],
  queryFn: async () => (await analyticsApi.dailyTrend({ days: period, scope, calendar })).data.daily,
});

const { data: kpis } = useQuery({
  queryKey: ["sla-summary", period, scope, calendar],
  queryFn: async () => (await slaApi.getSummary({ days: period, scope, calendar })).data,
});

const { data: atRisk } = useQuery({
  queryKey: ["sla-risks", scope],
  queryFn: async () => (await analyticsApi.slaRisks({ scope })).data.risks,
  refetchInterval: 30_000,
});

const { data: heatmap } = useQuery({
  queryKey: ["sla-heatmap", scope, period],
  queryFn: async () => (await analyticsApi.queueHeatmap({ days: period, scope })).data.heatmap,
});

const { data: agents } = useQuery({
  queryKey: ["sla-agents"],
  queryFn: async () => (await dashboardsApi.agentWorkload()).data.agents,
});
```

Live-обновления через `useWebSocket` (см. `DESIGN_SYSTEM.md` раздел 10).

### Шаг 6 — API endpoints

Маппинг к существующему backend (`sla-platform/backend/app/api/`):

| Виджет | Endpoint | Параметры |
|---|---|---|
| KPI summary | `GET /sla/summary` | `days`, `scope?`, `calendar?` |
| Queue breaches table | `GET /sla/queue-breaches` | `days`, `scope?`, `calendar?` |
| Daily trend chart | `GET /analytics/trend` (новый, см. ниже) | `days`, `scope?`, `granularity=day` |
| Heatmap | `GET /analytics/queue-heatmap` | `days`, `scope?` |
| At-risk tickets | `GET /analytics/sla-risks` | `scope?` |
| Agent workload | `GET /dashboards/agent-workload` | — |

**Новые endpoints, которые нужно добавить на бэке (если их ещё нет):**

```python
# backend/app/api/analytics.py
@router.get("/trend")
def daily_trend(days: int = 30, scope: str | None = None, calendar: str | None = None):
    """
    Returns: { daily: [{ date, total, reaction, resolution }, ...] }
    """
    ...

@router.get("/queue-heatmap")
def queue_heatmap(days: int = 30, scope: str | None = None):
    """
    Returns: { heatmap: [{ queue_id, name, hours: [int × 24] }, ...] }
    """
    ...
```

Если endpoints уже есть, но форма ответа отличается — написать тонкий маппер в `frontend/src/api/sla.ts` / `analytics.ts`. UI не менять.

### Шаг 7 — Роут + сайдбар

В `App.tsx`:
```tsx
<Route path="/sla/portal" element={<SLAPortal />} />
```

В `frontend/src/components/layout/Sidebar.tsx`:
```tsx
{ key: "/sla/portal", icon: <BarChartOutlined />, label: t("nav.slaPortal") }
```

После строки с `/dashboard`. Это становится главным аналитическим разделом.

В `frontend/src/i18n/locales/ru/common.json` + `en/common.json`:
```json
"nav": {
  "slaPortal": "Портал SLA"
},
"slaPortal": {
  "title": "Обзор SLA",
  "subtitle": "Соблюдение реакции и решения по очередям",
  "tabs": {
    "queues": "Очереди",
    "tickets": "Тикеты в риске",
    "heat": "Тепловая карта",
    "team": "Команда"
  },
  "filters": {
    "period": "Период",
    "scope": "Сегмент",
    "calendar": "Календарь",
    "search": "Поиск очереди или тикета"
  },
  "kpi": {
    "reaction": "SLA по реакции",
    "resolution": "SLA по решению",
    "atRisk": "Тикеты в зоне риска",
    "avgWait": "Среднее время ожидания"
  },
  "charts": {
    "trend": "Тренд нарушений SLA",
    "topQueues": "Топ очередей по нарушениям",
    "hourly": "Распределение по часам суток",
    "modeStack": "Стек",
    "modeSplit": "Раздельно"
  },
  "columns": {
    "queue": "Очередь",
    "priority": "Приоритет",
    "tickets": "Тикетов",
    "slaReact": "SLA реакц.",
    "slaResolve": "SLA реш.",
    "breachReact": "Наруш. реакц.",
    "breachResolve": "Наруш. реш.",
    "atRisk": "В риске",
    "avgWait": "⌀ Ожидание",
    "trend": "Тренд",
    "health": "Health"
  }
}
```

### Шаг 8 — Проверка

- [ ] `npm run dev` — открыть `/sla/portal`, увидеть полный портал
- [ ] Глобальные фильтры (period / scope / calendar / search) фильтруют ВСЕ виджеты на странице
- [ ] Тренд chart переключается между Стек / Раздельно
- [ ] Hover на чарте показывает crosshair + tooltip с датой и значениями
- [ ] Клик по любому заголовку таблицы → сортировка, второй клик — обратный порядок
- [ ] Клик по строке очереди → drawer справа с детальной аналитикой (3 metric tile + 2 чарта + owners)
- [ ] Клик по тикету → drawer тикета с SLA usage прогрессом
- [ ] Live-пилл в шапке пульсирует и срабатывает через WebSocket
- [ ] `npm run typecheck` + `npm run lint` без ошибок
- [ ] `npm run build` без новых warnings
- [ ] Локаль en заполнена (можно машинным переводом)

### Шаг 9 — Удалить старые SLA-папки из репозитория

После успешной интеграции:
```bash
git rm -r "SLA Monitor" "SLA Operations Center" "SLA Executive" "SLA Premium"
# SLA Portal оставляем — он эталон, на него ссылается CLAUDE.md
```

`SLA Portal/` остаётся как **canonical reference** для будущих изменений дизайна. Если потребуется обновить дизайн — сначала меняем в `SLA Portal/` (он же self-contained прототип), убеждаемся что выглядит как надо, потом переносим в `frontend/src/design/`.

## После интеграции

На любые будущие задачи Claude Code:
1. Читает `CLAUDE.md` (правила) и `DESIGN_SYSTEM.md` (спек).
2. Использует компоненты из `frontend/src/design/components/`.
3. Если нужного компонента нет — добавляет в design system, не пишет локально.
4. Меняет токены только в `tokens.css` — это распространится на весь продукт.

## Acceptance Criteria

- Страница `/sla/portal` запускается с реальными данными бэка (не mock).
- Дизайн визуально идентичен `SLA Portal/index.html`.
- AntD `<ConfigProvider>` использует кастомную тему.
- ECharts theme `sla` зарегистрирован и применяется ко всем графикам в проекте.
- В `frontend/src/design/` лежит 8 компонентов с типами и JSDoc.
- `CLAUDE.md` и `DESIGN_SYSTEM.md` лежат в корне репозитория.
- Все строки UI переведены через i18n (ru + en).
