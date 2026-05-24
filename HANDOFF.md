# SLA Platform Design — Handoff

> Полный пакет для интеграции дизайна SLA Portal в проект sla-platform.

## Что внутри

- **`SLA Portal/`** — эталонный прототип с интерактивными графиками, sortable таблицей, drill-down drawer. Открыть `index.html` в браузере.
- **`CLAUDE.md`** — правила дизайна для Claude Code. Читается на каждой сессии.
- **`DESIGN_SYSTEM.md`** — полная спецификация: токены, AntD theme, ECharts theme, компоненты, паттерны.
- **`INTEGRATION.md`** — пошаговый план интеграции в `sla-platform/frontend/`.

## Архивные варианты

В архиве также лежат другие исследования дизайна (`SLA Monitor/`, `SLA Operations Center/`, `SLA Executive/`, `SLA Premium/`). **Не использовать** для интеграции — оставлены как референсы.

## Quickstart для Claude Code

1. Прочитать `CLAUDE.md` (правила).
2. Прочитать `DESIGN_SYSTEM.md` (спек).
3. Выполнить `INTEGRATION.md` пошагово.
4. Эталон визуала — открыть `SLA Portal/index.html`.

## Что станет результатом

- Страница `/sla/portal` в проекте, подключённая к реальному API.
- Дизайн-система в `frontend/src/design/` — токены, AntD theme, ECharts theme, 8 переиспользуемых компонентов.
- Любые будущие страницы — на этой же основе.
