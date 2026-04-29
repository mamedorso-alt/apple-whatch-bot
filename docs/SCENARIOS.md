# E2E Scenarios (MVP)

## Scenario 1: New user onboarding
1. User installs iOS app and opens it.
2. App requests HealthKit read permissions.
3. App calls `POST /v1/auth/device`, stores `api_token`.
4. App sends `POST /v1/health/daily`.
5. User taps "Get link code" -> `POST /v1/telegram/link-code`.
6. User sends `/link CODE` to Telegram bot.
7. Backend links `telegram_user_id` with app user.

Expected result:
- User linked, `/today` and `/week` return data.

## Scenario 2: Partial Health data access
1. User denies HRV or sleep access.
2. App still sends payload with available fields and `null`/`0` for missing values.
3. Backend accepts payload and computes score without crashing.

Expected result:
- Ingest returns `status=ok`.
- Score computed with soft fallback where possible.

## Scenario 3: Scheduler deduplication
1. Scheduler runs at configured local time (morning/evening).
2. Backend writes `message_log` before sending.
3. If trigger repeats, unique constraint prevents duplicate send.

Expected result:
- One message per type per day.

## Scenario 4: Language switch
1. Linked user sends `/lang en`.
2. Backend updates user language.
3. Next `/today` and `/week` responses are in English.

Expected result:
- Language persisted in `users.language`.
