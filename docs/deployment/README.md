# Развёртывание

## Production Docker Compose

### Требования

- Linux сервер (Ubuntu 22.04+ / Debian 12+)
- Docker 24+ и Docker Compose v2+
- Минимум 2 GB RAM, 10 GB диска
- Домен и SSL сертификат (рекомендуется)

### 1. Установка Docker

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Выйдите и зайдите заново
```

### 2. Клонирование и настройка

```bash
git clone <repository-url> /opt/sla-platform
cd /opt/sla-platform

# Настройка окружения
cp .env.example .env
nano .env
# Обязательно измените:
# - SECRET_KEY (сгенерируйте: openssl rand -hex 32)
# - POSTGRES_PASSWORD
```

### 3. Production docker-compose

Создайте `docker-compose.prod.yml`:

```yaml
services:
  postgres:
    image: postgres:16-alpine
    env_file: .env
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    networks:
      - sla_network

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    networks:
      - sla_network

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    env_file: .env
    environment:
      - PYTHONPATH=/app
    volumes:
      - ./data:/data
    restart: unless-stopped
    depends_on:
      - postgres
      - redis
    command: >
      sh -c "alembic upgrade head &&
             uvicorn app.main:app --host 0.0.0.0 --port 8000"
    networks:
      - sla_network

  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    env_file: .env
    environment:
      - PYTHONPATH=/app
    volumes:
      - ./data:/data
    restart: unless-stopped
    depends_on:
      - postgres
      - redis
    command: celery -A app.core.celery_app worker -l info -Q import,report,default
    networks:
      - sla_network

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    restart: unless-stopped
    depends_on:
      - backend
    networks:
      - sla_network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./docker/nginx/default.conf:/etc/nginx/conf.d/default.conf
      - /etc/letsencrypt:/etc/letsencrypt:ro
    depends_on:
      - frontend
      - backend
    restart: unless-stopped
    networks:
      - sla_network

volumes:
  postgres_data:

networks:
  sla_network:
    driver: bridge
```

### 4. Nginx конфигурация

Файл `docker/nginx/default.conf`:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    client_max_body_size 100M;

    location / {
        proxy_pass http://frontend:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 5. Запуск

```bash
docker compose -f docker-compose.prod.yml up -d

# Проверка
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f
```

### 6. SSL сертификат (Let's Encrypt)

```bash
docker compose -f docker-compose.prod.yml run --rm nginx \
  certbot certonly --webroot -w /var/www/html -d your-domain.com
```

## Бэкапы

### PostgreSQL

```bash
# Ежедневный бэкап
docker compose exec -T postgres pg_dump -U sla_user sla_platform > backup_$(date +%Y%m%d).sql

# Восстановление
cat backup.sql | docker compose exec -T postgres psql -U sla_user sla_platform
```

### Файлы данных

```bash
# Бэкап загруженных файлов
tar czf data_backup_$(date +%Y%m%d).tar.gz data/
```

## Обновление

```bash
git pull origin main
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

## Мониторинг

```bash
# Логи
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f worker

# Статистика
docker stats
```

## Переменные окружения

| Переменная | Описание | Пример |
|-----------|----------|--------|
| `DATABASE_URL` | URL подключения к PostgreSQL | `postgresql+asyncpg://user:pass@host:5432/db` |
| `CELERY_BROKER_URL` | URL Redis для Celery | `redis://redis:6379/0` |
| `CELERY_RESULT_BACKEND` | URL Redis для результатов | `redis://redis:6379/1` |
| `SECRET_KEY` | Ключ для JWT (изменить в production) | `openssl rand -hex 32` |
| `CORS_ORIGINS` | Разрешённые CORS origin | `["https://your-domain.com"]` |
| `DATA_DIR` | Директория данных | `/data` |
