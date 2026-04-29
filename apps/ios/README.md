# iOS MVP (SwiftUI + HealthKit)

## Что уже реализовано
- SwiftUI экраны:
  - `OnboardingView`
  - `HealthAccessView`
  - `TelegramLinkView`
  - `SyncStatusView`
  - `ReportsView` (`/v1/reports/today`, `/v1/reports/week`)
- Сервисы:
  - `HealthKitService` (read permissions + day-level aggregates)
  - `ApiClient` (`/v1/auth/device`, `/v1/telegram/link-code`, `/v1/health/daily`)
  - `SyncManager` (auth + sync + link code)
- Состояние:
  - `api_token` и `last_sync_at` сохраняются в `UserDefaults`
  - `SyncStatusView` показывает backend статус через `/v1/reports/status`

## Быстрый запуск через XcodeGen
1. Установите XcodeGen:
   - `brew install xcodegen`
2. В папке `apps/ios` выполните:
   - `xcodegen generate`
3. Откройте `ProductivityAssistant.xcodeproj` и выберите target `ProductivityAssistant`.
4. Включите ваш Team для code signing.
5. Для устройства/реального сервера смените `API_BASE_URL` в:
   - `ProductivityAssistant/Info.plist`
   - или в `project.yml` -> `info.properties.API_BASE_URL`

## Ограничения текущего MVP-этапа
- Нет отдельного watchOS клиента.
- Авто-синк по расписанию пока минимальный (ручной sync + первичный sync).
- UI локализация текстов пока не вынесена в `Localizable.strings`.
