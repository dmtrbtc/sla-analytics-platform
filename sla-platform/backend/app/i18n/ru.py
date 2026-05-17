"""Centralized Russian translations for backend API messages, report headers, audit labels."""

REPORT_SHEET_NAMES = {
    "sla_metrics": "Метрики SLA",
    "queues": "Очереди",
    "breaches": "Нарушения SLA",
    "summary": "Сводка",
    "teams": "Команды",
    "lifecycle": "Жизненный цикл",
    "imports": "Импорты",
}

REPORT_HEADERS = {
    "sla_metrics": [
        "ID заявки",
        "Номер заявки",
        "Метрика",
        "Время (сек)",
        "Время (мин)",
        "Время (час)",
        "Нарушение SLA",
        "Очередь",
        "Путь по очередям",
        "Время входа в очередь",
        "Время выхода из очереди",
        "Ответственный",
        "Время владения (сек)",
        "Время владения (мин)",
        "Время владения (час)",
        "Достоверность",
        "Создано",
        "Закрыто",
        "Definition ID",
        "Вычислено",
    ],
    "queue_periods": [
        "ID заявки",
        "Очередь",
        "Команда",
        "Время входа",
        "Время выхода",
        "Секунды",
        "Минуты",
        "Часы",
        "Ответственных",
    ],
    "breaches": [
        "ID заявки",
        "Номер заявки",
        "Метрика",
        "Время (сек)",
        "Время (мин)",
        "Время (час)",
        "Очередь",
        "Ответственный",
        "Путь по очередям",
        "Создано",
        "Вычислено",
    ],
    "summary": [
        "Показатель",
        "Значение",
    ],
    "team_performance": [
        "ID заявки",
        "Ответственный",
        "Очередь",
        "Команда",
        "Начало",
        "Окончание",
        "Секунды",
        "Минуты",
        "Часы",
        "Активен",
    ],
    "ticket_lifecycle": [
        "ID заявки",
        "Номер заявки",
        "Название",
        "Очередь",
        "Состояние",
        "Ответственный",
        "Создано",
        "Обновлено",
        "Первый ответ",
        "Решение",
        "Закрыт",
        "Достоверность",
    ],
    "imports_summary": [
        "ID сессии",
        "Статус",
        "Файл backlog",
        "Файл history",
        "Строк backlog",
        "Строк history",
        "Создано",
        "Завершено",
        "Ошибок",
        "Статистика",
    ],
}

ANALYTICS_LABELS = {
    "total_tickets": "Всего тикетов",
    "open_tickets": "Открытых тикетов",
    "closed_tickets": "Закрытых тикетов",
    "sla_breach_pct": "Нарушений SLA %",
    "avg_response_time": "Среднее время отклика",
    "avg_resolution_time": "Среднее время решения",
    "tickets_at_risk": "Тикеты с риском SLA",
    "overloaded_queues": "Очереди с перегрузкой",
    "avg_wait_time": "Среднее время ожидания",
    "avg_reassignments": "Среднее число переназначений",
    "most_problematic_queue": "Самая проблемная очередь",
    "unowned_tickets": "Тикеты без владельца",
    "queue": "Очередь",
    "avg_wait_minutes": "Среднее ожидание (мин)",
    "avg_resolution_hours": "Среднее решение (ч)",
    "sla_pct": "SLA %",
    "breached_tickets": "Пробитые тикеты",
    "risk_score": "Риск",
    "ticket": "Тикет",
    "queue_name": "Очередь",
    "sla_usage_pct": "Использование SLA %",
    "remaining_time": "Оставшееся время",
    "risk_level": "Уровень риска",
}

RISK_LEVELS = {
    "low": "Низкий",
    "medium": "Средний",
    "high": "Высокий",
    "critical": "Критический",
}

AUDIT_ACTIONS = {
    "sla_definition_created": "Определение SLA создано",
    "sla_definition_updated": "Определение SLA обновлено",
    "sla_definition_deleted": "Определение SLA удалено",
    "queue_rule_created": "Правило очереди SLA создано",
    "queue_rule_updated": "Правило очереди SLA обновлено",
    "queue_rule_deleted": "Правило очереди SLA удалено",
    "user_created": "Пользователь создан",
    "user_deactivated": "Пользователь деактивирован",
    "import_started": "Импорт запущен",
    "import_completed": "Импорт завершён",
    "report_generated": "Отчёт сгенерирован",
}

VALIDATION_MESSAGES = {
    "queue_pattern_required": "Шаблон очереди обязателен",
    "response_time_positive": "Время отклика должно быть больше 0",
    "resolution_exceeds_response": "Время решения должно превышать время отклика",
    "name_required": "Название обязательно",
    "invalid_role": "Недопустимая роль",
}

SUMMARY_LABELS = {
    "total_tickets": "Всего тикетов",
    "total_metrics": "Всего метрик SLA",
    "total_breaches": "Нарушений SLA",
    "breach_pct": "Процент нарушений",
    "total_queue_periods": "Всего периодов в очередях",
    "response_count": "Количество откликов",
    "resolution_count": "Количество решений",
    "response_breached": "Нарушено откликов",
    "resolution_breached": "Нарушено решений",
}


def translate_audit_action(action: str) -> str:
    return AUDIT_ACTIONS.get(action, action)


def translate_risk_level(level: str) -> str:
    return RISK_LEVELS.get(level.lower(), level)


def translate_metric_name(name: str) -> str:
    names = {
        "response_time": "Время отклика",
        "resolution_time": "Время решения",
        "queue_time": "Время в очереди",
        "owner_time": "Время владения",
    }
    return names.get(name, name)
