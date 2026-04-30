# Apple Watch -> Productivity -> Telegram (MVP)

Monorepo structure:
- `apps/backend` - FastAPI backend, Telegram webhook, scoring, scheduler
- `apps/ios` - SwiftUI iOS MVP app
- `docs` - API contract and E2E scenarios

## Quick start
1. Backend:
   - `cd apps/backend`
   - `cp .env.example .env`
   - configure env values
   - `docker compose up --build -d`
   - `docker compose exec api alembic upgrade head`
2. iOS:
   - open Xcode and create/load iOS app target
   - copy `apps/ios/ProductivityAssistant/*` into project
   - enable HealthKit capability

## Current status
- MVP backend core implemented
- Telegram link and commands implemented
- Scoring and daily/weekly reports implemented
- iOS SwiftUI flow implemented (onboarding, permissions, link code, sync)
- Optional CD automation added for backend deploy + iOS TestFlight (`docs/CD_AUTOMATION.md`)
