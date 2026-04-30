# Backend MVP (FastAPI)

## Реализовано
- FastAPI backend + webhook Telegram
- PostgreSQL + Alembic миграции
- Таблицы: `users`, `link_codes`, `daily_metrics`, `daily_scores`, `message_log`
- API:
  - `GET /health`
  - `POST /v1/auth/device`
  - `POST /v1/telegram/link-code`
  - `POST /v1/health/daily` (idempotent upsert)
  - `GET /v1/reports/today`
  - `GET /v1/reports/week`
  - `GET /v1/reports/coach` (AI coach, fallback если LLM недоступен)
  - `GET /v1/reports/status`
  - `POST /v1/telegram/webhook` (`/start`, `/help`, `/link CODE`, `/lang`, `/today`, `/week`, `/coach`)
  - `POST /internal/run-scheduled` (manual scheduler trigger)
- APScheduler worker (interval-based auto trigger)
- Scoring v1:
  - baseline 14 дней
  - mode `deep_work|normal|recovery`
  - soft mode для неполной истории

## Запуск через Docker Compose
1. Создайте `.env`:
   - `cp .env.example .env`
2. Обновите минимум:
   - `DATABASE_URL`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_WEBHOOK_SECRET`
   - `JWT_SECRET`
  - `ANTHROPIC_API_KEY` (опционально; без него работает rule-based fallback коуч)
3. Поднимите сервисы:
   - `docker compose up --build -d`
4. Прогоните миграции:
   - `docker compose exec api alembic upgrade head`
5. Проверьте:
   - `GET http://localhost:8000/health`
   - `http://localhost:8000/docs`

## Локальный запуск без Docker
1. `python -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. Подготовьте `.env`
4. `alembic upgrade head`
5. `uvicorn app.main:app --reload`

## Тесты
- Запуск:
  - `pytest -q`
- Docker one-shot:
  - `docker compose -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from test_runner`
- Покрытые сценарии:
  - link flow
  - webhook command parsing
  - ingest partial data (без сна/HRV)
  - scoring penalties + mode
  - API integration flow (auth -> link-code -> webhook /link -> ingest -> webhook /today)
  - scheduler dedup + timezone window behavior

## Scheduler (auto reports)
- Управление через env:
  - `SCHEDULER_ENABLED=true|false`
  - `SCHEDULER_INTERVAL_MIN=30`
- Когда включен, backend автоматически вызывает scheduled отправки по интервалу.

## Команды (Makefile)
- `make up` - поднять backend + db
- `make migrate` - применить миграции
- `make test` - локальные тесты
- `make test-docker` - тесты в docker-контуре
- `make down` - остановить окружение

## CI
- GitHub Actions workflow: `.github/workflows/backend-ci.yml`
- На push/PR по `apps/backend/**`:
  - поднимает Postgres service
  - ставит зависимости
  - выполняет Alembic migrations
  - запускает `pytest -q`

## Деплой (production checklist)
1. Поднимите PostgreSQL (managed или VM).
2. Разверните backend за `nginx`/`caddy` с HTTPS.
3. Укажите домен, например `api.yourdomain.com`.
4. Заполните production env:
   - `APP_ENV=prod`
   - `APP_BASE_URL=https://api.yourdomain.com`
   - `DATABASE_URL=postgresql+psycopg://...`
   - `TELEGRAM_BOT_TOKEN=...`
   - `TELEGRAM_WEBHOOK_SECRET=...`
   - `JWT_SECRET=...`
   - `DEFAULT_TIMEZONE=Asia/Baku`
5. Примените миграции:
   - `alembic upgrade head`
6. Настройте webhook Telegram:
   - `https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://api.yourdomain.com/v1/telegram/webhook&secret_token=<TELEGRAM_WEBHOOK_SECRET>`
7. Проверьте e2e:
   - `/start` -> ok
   - `/link CODE` -> user linked
   - `/today`, `/week` -> report text
   - `/internal/run-scheduled` -> no duplicates in `message_log`
