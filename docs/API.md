# API Contract (MVP)

## Auth / device
### `POST /v1/auth/device`
Creates anonymous app user and returns API token.

Response:
```json
{
  "user_id": "uuid",
  "api_token": "string"
}
```

## Telegram link code
### `POST /v1/telegram/link-code`
Headers: `Authorization: Bearer <api_token>`

Response:
```json
{
  "code": "ABC123",
  "expires_at": "2026-04-28T12:00:00Z"
}
```

## Ingest daily HealthKit aggregates
### `POST /v1/health/daily`
Headers: `Authorization: Bearer <api_token>`

Payload:
```json
{
  "date": "2026-04-28",
  "timezone": "Asia/Baku",
  "steps": 8200,
  "active_kcal": 320.5,
  "sleep_min": 415,
  "sleep_start": "2026-04-27T22:55:00Z",
  "sleep_end": "2026-04-28T05:50:00Z",
  "resting_hr": 57.2,
  "hrv_sdnn": 38.8,
  "workouts_count": 1
}
```

Response:
```json
{
  "status": "ok"
}
```

## Telegram webhook
### `POST /v1/telegram/webhook`
Header: `X-Telegram-Bot-Api-Secret-Token: <TELEGRAM_WEBHOOK_SECRET>`

Supported commands:
- `/start`
- `/help`
- `/link CODE`
- `/lang ru|en`
- `/today`
- `/week`
- `/coach`

## Reports API (for iOS app)
### `GET /v1/reports/today`
Headers: `Authorization: Bearer <api_token>`

Response:
```json
{
  "date": "2026-04-28",
  "report": "Сегодня\\nFocus score: 72/100\\n..."
}
```

### `GET /v1/reports/week`
Headers: `Authorization: Bearer <api_token>`

Response:
```json
{
  "end_date": "2026-04-28",
  "report": "Итоги недели\\nСредний focus score: 68/100\\n..."
}
```

### `GET /v1/reports/status`
Headers: `Authorization: Bearer <api_token>`

Response:
```json
{
  "is_linked": true,
  "language": "ru",
  "timezone": "Asia/Baku",
  "last_sync_date": "2026-04-28",
  "has_today_score": true
}
```

### `GET /v1/reports/coach`
Headers: `Authorization: Bearer <api_token>`

Response:
```json
{
  "date": "2026-04-29",
  "report": "AI Coach ... personalized recommendation text ..."
}
```

## Internal trigger
### `POST /internal/run-scheduled`
Header: `X-Internal-Secret: <JWT_SECRET>`

Response:
```json
{
  "sent": 2,
  "skipped": 10
}
```
