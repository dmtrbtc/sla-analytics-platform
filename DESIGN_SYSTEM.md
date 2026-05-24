# Design System — SLA_Otrs

Спецификация дизайн-системы для проекта SLA_Otrs. Эталон — `SLA Portal/`.

---

## 1. Дизайн-токены

Источник истины — `frontend/src/design/tokens.css`. Все компоненты, ECharts theme и AntD ConfigProvider тянут значения отсюда.

```css
:root {
  /* Surfaces */
  --bg:           #f6f7f9;     /* основной фон страницы */
  --surface:      #ffffff;     /* карточки, drawer, modals */
  --surface-2:    #f9fafb;     /* hover row, secondary */
  --surface-3:    #f3f4f6;     /* progress track, soft background */

  /* Lines */
  --line:         #e4e7ec;     /* основной border */
  --line-2:       #eef0f3;     /* divider в таблицах */
  --line-strong:  #d0d5dd;     /* border полей форм */

  /* Ink (text) */
  --ink:          #101828;     /* основной текст */
  --ink-2:        #344054;     /* secondary text */
  --ink-3:        #667085;     /* muted */
  --ink-4:        #98a2b3;     /* placeholder, axis labels */
  --ink-5:        #d0d5dd;     /* disabled */

  /* Brand (только active state, links, primary CTA) */
  --brand:        #4f46e5;
  --brand-hover:  #4338ca;
  --brand-soft:   #eef2ff;
  --brand-border: #c7d2fe;

  /* Identity colors — две метрики */
  --reaction:        #f59e0b;
  --reaction-soft:   #fef3c7;
  --resolution:      #8b5cf6;
  --resolution-soft: #ede9fe;

  /* Severity (используется ТОЛЬКО для breach/risk signals) */
  --ok:           #10b981;      /* ≥92% */
  --ok-soft:      #d1fae5;
  --warn:         #f59e0b;      /* 85-92% */
  --warn-soft:    #fef3c7;
  --high:         #f97316;      /* 75-85% */
  --high-soft:    #ffedd5;
  --crit:         #ef4444;      /* <75% или breach */
  --crit-soft:    #fee2e2;

  /* Radii */
  --radius-sm: 4px;
  --radius:    6px;
  --radius-lg: 10px;
  --radius-xl: 14px;

  /* Shadows */
  --shadow-card: 0 1px 2px rgba(16,24,40,0.04), 0 0 0 1px var(--line);
  --shadow-pop:  0 12px 24px rgba(16,24,40,0.08), 0 4px 8px rgba(16,24,40,0.04);

  /* Fonts */
  --font:      "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-mono: "JetBrains Mono", "SF Mono", Menlo, monospace;
}
```

## 2. AntD ConfigProvider theme

`frontend/src/design/theme.ts`:

```ts
import type { ThemeConfig } from "antd";

export const theme: ThemeConfig = {
  token: {
    colorPrimary: "#4f46e5",
    colorSuccess: "#10b981",
    colorWarning: "#f59e0b",
    colorError: "#ef4444",
    colorTextBase: "#101828",
    colorBgBase: "#ffffff",
    colorBgLayout: "#f6f7f9",
    colorBorder: "#e4e7ec",
    colorBorderSecondary: "#eef0f3",
    borderRadius: 6,
    borderRadiusLG: 10,
    fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    fontSize: 14,
    fontSizeHeading1: 20,
    fontSizeHeading2: 18,
    controlHeight: 34,
    controlHeightSM: 28,
    boxShadow: "0 1px 2px rgba(16,24,40,0.04)",
    boxShadowSecondary: "0 12px 24px rgba(16,24,40,0.08)",
  },
  components: {
    Table: {
      headerBg: "#ffffff",
      headerColor: "#667085",
      headerSplitColor: "transparent",
      rowHoverBg: "#f9fafb",
      borderColor: "#eef0f3",
    },
    Card: {
      headerBg: "#ffffff",
      headerHeight: 56,
    },
    Button: {
      fontWeight: 500,
      controlHeight: 34,
    },
    Tabs: {
      itemColor: "#667085",
      itemActiveColor: "#101828",
      itemSelectedColor: "#101828",
      inkBarColor: "#4f46e5",
    },
  },
};
```

В `main.tsx`:
```tsx
import { ConfigProvider } from "antd";
import { theme } from "@/design/theme";
import "@/design/tokens.css";

<ConfigProvider theme={theme}>...</ConfigProvider>
```

## 3. ECharts theme

`frontend/src/design/echarts-theme.ts` регистрируется один раз в `main.tsx`:

```ts
import * as echarts from "echarts/core";

echarts.registerTheme("sla", {
  color: ["#f59e0b", "#8b5cf6", "#4f46e5", "#10b981", "#f97316", "#ef4444"],
  backgroundColor: "transparent",
  textStyle: {
    fontFamily: '"Inter", -apple-system, sans-serif',
    color: "#344054",
  },
  title: {
    textStyle: { color: "#101828", fontWeight: 600, fontSize: 14 },
    subtextStyle: { color: "#667085", fontSize: 12 },
  },
  line: {
    smooth: false,
    symbol: "circle",
    symbolSize: 5,
    lineStyle: { width: 2 },
    itemStyle: { borderWidth: 0 },
  },
  bar: { itemStyle: { borderRadius: [3, 3, 0, 0] } },
  categoryAxis: {
    axisLine: { lineStyle: { color: "#e4e7ec" } },
    axisTick: { show: false },
    splitLine: { show: false },
    axisLabel: { color: "#98a2b3", fontFamily: "JetBrains Mono", fontSize: 10.5 },
  },
  valueAxis: {
    axisLine: { show: false },
    splitLine: { lineStyle: { color: "#eef0f3", type: "solid" } },
    axisLabel: { color: "#98a2b3", fontFamily: "JetBrains Mono", fontSize: 10.5 },
  },
  legend: { textStyle: { color: "#667085", fontSize: 12 }, icon: "roundRect" },
  tooltip: {
    backgroundColor: "#101828",
    borderColor: "#101828",
    borderRadius: 8,
    textStyle: { color: "#ffffff", fontSize: 12, fontFamily: '"Inter", sans-serif' },
    padding: [10, 12],
    extraCssText: "box-shadow: 0 8px 16px rgba(16,24,40,0.18); font-feature-settings: 'tnum';",
  },
});

echarts.use([/* ... line, bar, heatmap modules ... */]);
```

Использование:
```tsx
<ReactECharts option={opts} theme="sla" style={{ height: 280 }}/>
```

## 4. Layout patterns

### Стандартная страница аналитики

```
┌─────────────────────────────────────────────────────────┐
│ Topbar — H1 + actions (period/scope/search/export)      │
├─────────────────────────────────────────────────────────┤
│ [KPI 1] [KPI 2] [KPI 3] [KPI 4]                         │
├─────────────────────────────────────────────────────────┤
│ ┌─────────── Main chart ──────────┐ ┌─ Side chart ────┐ │
│ │                                  │ │                 │ │
│ └──────────────────────────────────┘ └─────────────────┘ │
├─────────────────────────────────────────────────────────┤
│ [Tab 1] [Tab 2] [Tab 3] [Tab 4]                         │
│ Главная таблица — центр страницы                        │
└─────────────────────────────────────────────────────────┘
```

Drawer (drill-down) — 640px, выезжает справа.

### Стандартные размеры
- Sidebar width: 220px
- Topbar height: 56px (одна строка) / 100px (две строки с фильтрами)
- Canvas max-width: 1480px, центрирован
- Canvas padding: 20px / 28px
- Gap между секциями: 20px

## 5. Компоненты

### KpiCard
```tsx
<KpiCard
  label="SLA по реакции"
  value="96.4%"
  icon={<ClockCircleOutlined />}
  accent="react"            // brand | react | resolve | crit | ""
  foot="234 нарушений / 12 540 тикетов"
  delta={0.4}                // % изменения
  deltaBad={false}           // true если рост = плохо
/>
```

### SortableTable
Расширение AntD `<Table>` с дизайн-токенами:
- Sticky header
- Inline `MetricBar` для процентных колонок
- Inline `Sparkline` для тренда
- `HealthPip` для health-показателя
- onClick row → открыть DetailDrawer

### MetricBar
Двухсегментный progress bar для одной строки:
```tsx
<MetricBar
  kind="reaction"           // reaction | resolution
  pct={95.2}
  severity="warn"           // ok | warn | high | crit
  showValue
/>
```

### HealthPip
Цветной кружок 40×40px с числом 0–100:
```tsx
<HealthPip value={87} />     // автоопределение цвета по value
```

### ScopeChips
Фирменный фильтр сегментов:
```tsx
<ScopeChips
  value={scope}
  onChange={setScope}
  items={[
    { value: "all",     label: "Все",            count: 12 },
    { value: "support", label: "Support",         count: 4 },
    ...
  ]}
/>
```

### DetailDrawer
640px-drawer для drill-down:
```tsx
<DetailDrawer open={open} onClose={...} title={...} kind="queue|ticket">
  <DrawerMetricRow tiles={[...]} />
  <DrawerSection title="..."> ... </DrawerSection>
</DetailDrawer>
```

## 6. Цветовая логика severity

Везде, где отображается метрика SLA% или health-показатель, применяется одна шкала:

| Диапазон | Семантика | Токен | Когда применить цвет |
|---|---|---|---|
| ≥ 92% | OK | `var(--ok)` или `var(--ink)` | Только если есть warn/crit рядом — иначе нейтральный |
| 85 — 92% | Warning | `var(--warn)` | Применить цвет |
| 75 — 85% | High risk | `var(--high)` | Применить цвет |
| < 75% или breach | Critical | `var(--crit)` | Применить цвет |

Реализация в утилите:
```ts
export const slaSeverity = (pct: number): "ok" | "warn" | "high" | "crit" =>
  pct >= 92 ? "ok" : pct >= 85 ? "warn" : pct >= 75 ? "high" : "crit";
```

## 7. Чарты — паттерны

### Stacked Area Chart (тренд breaches)
- xAxis: дни (DD.MM)
- yAxis: количество
- Две серии: Реакция (оранжевый) + Решение (фиолетовый)
- Stack mode: stack | split (toggle)
- Tooltip: crosshair + дата + 2 значения + сумма

### Horizontal Bars (топ очередей)
- Один бар — две сегмента (реакция + решение) в общей шкале
- Сортировка по сумме нарушений ↓
- Click on bar → open queue drawer

### Heatmap (queue × hour)
- Строки — очереди
- Колонки — 24 часа
- Цветовая шкала: `#fff7ed → #ea580c`
- Tooltip: очередь · час · значение
- Click on cell → open queue drawer

### Inline Sparkline
- 14–16 точек, 56×20px
- Цвет в зависимости от серии (реакция или решение)
- Без axis, без grid, только линия и опционально последняя точка

## 8. Что НЕ делать

- ❌ Не использовать ECharts grayscale цвета — только из `--reaction`/`--resolution`/`--brand`/severity
- ❌ Не добавлять border на чартах, не использовать `boxShadow` на тултипах кроме предусмотренного
- ❌ Не использовать `animation: { duration > 500 }` — операционный UI не должен «играть»
- ❌ Не использовать gradient fills в чартах (кроме легкого opacity 0.18 для area)
- ❌ Не использовать 3D, polar, sunburst и прочую визуальную перегруженность

## 9. Локализация

Все строки → i18n. Существующие ключи:
- `nav.dashboard`, `nav.tickets`, `nav.slaConfig`, `nav.imports`, `nav.reports`, `nav.teams`
- `slaConfig.responseTime` → «Время реакции»
- `slaConfig.resolutionTime` → «Время решения»
- `analytics.breachedResponse` → «Нарушения реакции»
- `analytics.breachedResolution` → «Нарушения решения»
- `analytics.riskLevel_critical|high|medium|low`
- `common.created|saved|deleted|active|inactive|all`

Новые ключи добавляются в обе локали (ru + en) и группируются по странице:
```json
"slaPortal": {
  "title": "Обзор SLA",
  "tabs": { "queues": "Очереди", "tickets": "Тикеты в риске", "heat": "Тепловая карта", "team": "Команда" },
  "filters": { "period": "Период", "scope": "Сегмент", "calendar": "Календарь" }
}
```

## 10. WebSocket для live-обновлений

В компонентах с live-данными — используем существующий `useWebSocket`:
```tsx
useWebSocket({
  url: `${wsBase}/ws/dashboard`,
  onEvent: (event) => {
    if (["sla_breach", "ticket_updated", "queue_overloaded"].includes(event.type)) {
      queryClient.invalidateQueries({ queryKey: ["sla-..."] });
    }
  },
});
```

Live-индикатор в шапке (зелёная пульсирующая точка + «обновлено только что») — обязательный паттерн для аналитических страниц.
