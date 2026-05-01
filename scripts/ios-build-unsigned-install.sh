#!/usr/bin/env bash
# Builds ProductivityAssistant for iphoneos without Xcode account (no code sign),
# re-signs using your Apple Development cert + embedded.mobileprovision from a
# previous Xcode device build, then installs via devicectl.
#
# Requires: same Mac keychain cert, a prior Debug-iphoneos .app with
# embedded.mobileprovision (same bundle id), iPhone unlocked & trusted.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC_IOS="$ROOT/apps/ios"
WORK="${IOS_WORK_DIR:-/tmp/PANoSpaces}"
DERIVED="${IOS_DERIVED:-/tmp/pa-unsigned}"
INSTALL_APP="${IOS_INSTALL_APP:-/tmp/ProductivityAssistant-install.app}"
DEVICE_ID="${IOS_DEVICE_ID:-}"

if [[ -z "$DEVICE_ID" ]]; then
  DEVICE_ID="$(xcrun xctrace list devices 2>/dev/null | grep 'iPhone (Rustam)' | grep -oE '[0-9A-F]{8}-[0-9A-F]{16}' | tail -1 || true)"
fi
if [[ -z "$DEVICE_ID" ]]; then
  echo "Set IOS_DEVICE_ID to your iPhone UDID (Xcode → Window → Devices)." >&2
  exit 1
fi

OLD_SIGNED="$(find "$HOME/Library/Developer/Xcode/DerivedData" \
  -path '*/Debug-iphoneos/ProductivityAssistant.app/embedded.mobileprovision' \
  ! -path '*iphonesimulator*' 2>/dev/null | head -1 || true)"
if [[ -z "$OLD_SIGNED" ]]; then
  echo "No previous signed ProductivityAssistant.app with provisioning found in DerivedData." >&2
  echo "Run ⌘R once from Xcode on the phone, then re-run this script." >&2
  exit 1
fi
OLD_APP="$(dirname "$OLD_SIGNED")"

rsync -a --delete --exclude '.derivedData' --exclude 'build' --exclude 'DerivedData' \
  "$SRC_IOS/" "$WORK/"

rm -rf "$DERIVED"
(cd "$WORK" && xcodebuild -scheme ProductivityAssistant -configuration Debug \
  -sdk iphoneos -destination 'generic/platform=iOS' \
  CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO \
  -derivedDataPath "$DERIVED" build)

BUILT="$DERIVED/Build/Products/Debug-iphoneos/ProductivityAssistant.app"
ENT="$(mktemp /tmp/pa-entitlements.XXXXXX.plist)"
codesign -d --entitlements "$ENT" "$OLD_APP" >/dev/null 2>&1

rm -rf "$INSTALL_APP"
ditto "$BUILT" "$INSTALL_APP"
cp "$OLD_APP/embedded.mobileprovision" "$INSTALL_APP/"
codesign --remove-signature "$INSTALL_APP" 2>/dev/null || true
codesign --entitlements "$ENT" --sign "Apple Development" --force --generate-entitlement-der "$INSTALL_APP"
rm -f "$ENT"

xcrun devicectl device install app --device "$DEVICE_ID" "$INSTALL_APP"
echo "Installed. Check Profile tab footer for CFBundle version."
