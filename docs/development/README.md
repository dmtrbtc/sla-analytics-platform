# Настройка окружения разработчика

## Предварительные требования

- Python 3.12+
- Node.js 20+
- Docker 24+ (для PostgreSQL и Redis)
- Git

## Быстрый старт

### 1. Клонирование

```bash
git clone <repository-url>
cd sla-analytics-platform
```

### 2. Запуск инфраструктуры

```bash
# Запуск PostgreSQL и Redis
docker compose up -d postgres redis

# Проверка
docker compose ps
```

### 3. Backend

```bash
cd sla-platform/backend

# Виртуальное окружение
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# или
.venv\Scripts\activate  # Windows

# Установка зависимостей
pip install -r requirements.txt

# Переменные окружения
cp ../.env.example ../.env
# Отредактируйте .env при необходимости

# Миграции БД
alembic upgrade head

# Запуск
uvicorn app.main:app --reload --port 8000
```

Документация API: http://localhost:8000/api/docs

### 4. Celery Worker

```bash
# В отдельном терминале
cd sla-platform/backend
source .venv/bin/activate
celery -A app.core.celery_app worker -l info -Q import,report,default
```

### 5. Frontend

```bash
cd sla-platform/frontend

# Установка зависимостей
npm install

# Запуск dev-сервера
npm run dev
```

Frontend: http://localhost:5173

## Тестирование

### Backend тесты

```bash
cd sla-platform/backend
pytest                          # Все тесты
pytest tests/unit/              # Unit тесты
pytest tests/integration/       # Интеграционные тесты
pytest -v --cov=app             # С покрытием
```

### Frontend сборка

```bash
cd sla-platform/frontend
npm run build                   # production сборка
npx tsc --noEmit                # проверка типов
```

## Импорт тестовых данных

Документация API эндпоинтов для импорта:

1. Создайте сессию импорта с backlog и history CSV
2. Запустите пайплайн
3. Отслеживайте статус

```bash
# Через curl
curl -X POST http://localhost:8000/api/v1/imports/sessions \
  -F "backlog=@path/to/backlog.csv" \
  -F "history=@path/to/history.csv"
```

## Структура проекта

```
sla-platform/
├── backend/
│   ├── app/
│   │   ├── api/v1/           # REST API эндпоинты
│   │   ├── core/             # Конфигурация, БД, Celery, безопасность
│   │   ├── domain/           # Модели, схемы, перечисления
│   │   ├── services/         # Бизнес-логика
│   │   │   └── sla/          # SLA Engine
│   │   ├── tasks/            # Celery задачи
│   │   └── utils/            # Утилиты
│   ├── alembic/              # Миграции БД
│   └── tests/                # Тесты
├── frontend/
│   ├── src/
│   │   ├── api/              # API клиенты
│   │   ├── pages/            # Страницы
│   │   ├── components/       # Компоненты
│   │   └── ...
│   └── ...
├── docker/                   # Docker configs
└── docker-compose.yml
```

## Common Issues

### PostgreSQL connection refused
Убедитесь, что Docker контейнер работает:
```bash
docker compose ps
docker compose logs postgres
```

### Alembic migration fails
Проверьте DATABASE_URL в `.env`:
```bash
echo $DATABASE_URL
```

### Frontend proxy не работает
Проверьте `vite.config.ts`. Для standalone frontend:
```ts
server: {
  proxy: { "/api": "http://localhost:8000" }
}
```
