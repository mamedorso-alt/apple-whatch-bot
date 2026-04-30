# CI/CD Automation Setup

This project now includes automatic release workflow: `.github/workflows/release-cd.yml`.

## What becomes automatic

- Backend changes (`apps/backend/**`):
  - auto deploy to production server via SSH
  - restart docker services
  - run Alembic migrations
  - health-check endpoint

- iOS changes (`apps/ios/**`):
  - auto build and upload to TestFlight via fastlane
  - available to update on iPhone from TestFlight app

## Required GitHub Secrets

### Backend deploy secrets
- `PROD_SSH_HOST` (example: `applewhatchbotforrustam.website`)
- `PROD_SSH_USER` (example: `root`)
- `PROD_SSH_PRIVATE_KEY` (private key content for server SSH access)
- `PROD_APP_BASE_URL` (example: `https://applewhatchbotforrustam.website`)

### iOS TestFlight secrets
- `APP_STORE_CONNECT_API_KEY_ID`
- `APP_STORE_CONNECT_ISSUER_ID`
- `APP_STORE_CONNECT_API_KEY_BASE64` (content of `.p8` key, base64-encoded)
- `IOS_BUNDLE_IDENTIFIER` (example: `com.rustam.productivityassistant`)
- `IOS_TEAM_ID` (your Apple Team ID)

## Apple-side prerequisites (one-time)

1. App exists in App Store Connect with the same bundle identifier.
2. Your account has permissions for TestFlight upload.
3. App Signing / Certificates are configured for automatic signing.
4. TestFlight app installed on your iPhone with your Apple ID.

## How updates will arrive on iPhone

1. Push to `main`.
2. GitHub Actions uploads new build to TestFlight.
3. In TestFlight app on iPhone, tap `Update`.

This is the closest practical "automatic update after development" flow outside App Store production releases.
