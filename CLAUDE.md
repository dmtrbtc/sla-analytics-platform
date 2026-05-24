# CLAUDE.md

> Этот файл читается Claude Code в начале каждого чата.
> Здесь зафиксированы правила дизайна и продуктовых решений проекта SLA_Otrs.
> Любая работа над UI обязана следовать этим правилам.

## Проект

`sla-platform` — Enterprise SLA Operations Center на базе OTRS.

**Стек:**
- Backend: FastAPI + Celery + PostgreSQL + Redis
- Frontend: React 18 + TypeScript + Vite + Ant Design 5 + ECharts (через `echarts-for-react`) + @tanstack/react-query + react-router-dom + i18next (ru/en)
- WebSocket: `/ws/dashboard` для live-обновлений

## Канонический дизайн

Эталонный дизайн зафиксирован в папке **`SLA Portal/`** (на корне репозитория). При любых сомнениях о визуале — смотрите туда.

Параллельно сохранены варианты `SLA Monitor/`, `SLA Operations Center/`, `SLA Executive/`, `SLA Premium/` — это **архивные** изыскания, для интеграции не использовать.

## Правила дизайна

Полная спецификация в `DESIGN_SYSTEM.md`. Краткие правила, которые ВСЕГДА действуют:

### 1. Двухцветная идентичность метрик
- **Реакция** = оранжевый `#f59e0b` (CSS-переменная `--reaction`)
- **Решение** = фиолетовый `#8b5cf6` (CSS-переменная `--resolution`)

Эта пара цветов используется во ВСЕХ виджетах, графиках, легендах, барах прогресса. Не вводить новые цвета для этих сущностей.

### 2. Color discipline
- Цвет применяется ТОЛЬКО для severity / breach signal.
- Текст и интерфейс — оттенки серого (`--ink`, `--ink-2`, `--ink-3`, `--ink-4`).
- Brand-индиго `#4f46e5` — только для active state, ссылок, primary-кнопок.
- Severity:
  - Norma → нейтральный
  - Warning (85–92%) → `#f59e0b`
  - High risk (75–85%) → `#f97316`
  - Critical (<75% или breach) → `#ef4444`
  - Healthy (≥92%) → `#10b981`

### 3. Типографика
- Семейство UI: **Inter** (400 / 500 / 600 / 700)
- Цифры/моно: **JetBrains Mono** (для номеров тикетов, имён очередей в OTRS-формате, цифр в KPI)
- Все числа: `font-variant-numeric: tabular-nums`
- Иерархия:
  - H1 страницы — 20px / 700 / letter-spacing -0.4px
  - Карточка заголовок — 14.5px / 600 / -0.2px
  - KPI value — 30px / 700 / -0.8px
  - UPPERCASE labels — 11px / 600 / letter-spacing 0.5px

### 4. Структура страницы
Стандартная композиция аналитической страницы:
1. **Topbar с глобальными фильтрами** (period, scope chips, calendar, search)
2. **KPI row** (4 карточки одинаковой высоты)
3. **Двухколонник графиков** (главный chart + дополнительный)
4. **Tabs с основной аналитикой** (центральная таблица — главное на странице)
5. **Drawer** для drill-down (открывается справа, ширина 640px)

### 5. Таблицы — центр UX
- Sticky header
- Все колонки sortable, индикатор сортировки `↑ ↓ ↕`
- Inline bars для процентных метрик, inline sparklines для трендов
- Цвет в ячейке — только при breach или high-risk
- Hover row: `var(--surface-2)`
- Selected row: `var(--brand-soft)`

### 6. Графики
- ECharts с кастомной темой (см. `DESIGN_SYSTEM.md` → ECharts Theme)
- Тонкие линии (2px), мягкая сетка (`#eef0f3`)
- Hover crosshair + tooltip на тёмном фоне (`var(--ink)`)
- Легенда внизу или в углу, текст 12px / `var(--ink-3)`
- Реакция и Решение — всегда в фирменных цветах

### 7. Локализация
- ВСЕ строки → `t("...")`, никаких hardcoded русских в JSX
- Ключи в `frontend/src/i18n/locales/ru/common.json` + `en/common.json`
- Уже существующие переиспользовать: `slaConfig.responseTime`, `analytics.breachedResponse`, etc.

### 8. Не делать
- ❌ Не использовать emoji в UI (исключение — placeholder/empty state)
- ❌ Не использовать heavy shadows, gradient backgrounds
- ❌ Не добавлять иконки ради иконок — только функциональные
- ❌ Не вводить новые цветовые акценты без обновления `DESIGN_SYSTEM.md`
- ❌ Не дублировать KPI / счётчики — одна метрика появляется на странице один раз
- ❌ Не использовать кастомные таблицы где есть Ant Design `<Table>` — расширять её через `components` / `cellStyle`

## Структура кода

Дизайн-система живёт в:
```
frontend/src/design/
├── tokens.css            # CSS-переменные (источник истины для цветов/шрифтов)
├── theme.ts              # AntD ConfigProvider theme override
├── echarts-theme.ts      # ECharts theme registered globally
└── components/
    ├── KpiCard.tsx
    ├── SortableTable.tsx
    ├── HealthPip.tsx
    ├── MetricBar.tsx     # двухполосный progress (R/S)
    ├── Sparkline.tsx
    ├── ChipFilter.tsx
    ├── ScopeChips.tsx
    └── DetailDrawer.tsx
```

Любая новая страница начинается с `import { ... } from "@/design"`. Если нужного компонента нет — добавляем в design system, а не пишем локально.

## Workflow для новых задач

1. Прочитать `DESIGN_SYSTEM.md` (полный спек).
2. Открыть `SLA Portal/index.html` — посмотреть эталон в браузере.
3. Использовать компоненты из `frontend/src/design/components/`.
4. Если новый компонент — сначала добавить в design system с историей в Storybook (если есть), потом импортировать.
5. ВСЕ строки через i18n. ВСЕ числа через `tabular-nums`. ВСЕ цвета через CSS-переменные / theme tokens.
6. После любого UI-изменения — скриншот при ширине 1440px и при 1280px, проверить overflow.
