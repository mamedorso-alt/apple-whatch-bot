#!/usr/bin/env bash
# Xcode/Swift driver mishandles absolute paths that contain spaces (e.g. "Documents — …").
# Build/install on a device from a short path, then use Product → Run (⌘R).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${IOS_BUILD_ROOT:-/tmp/PANoSpaces}"
rsync -a --delete \
  --exclude '.derivedData' \
  --exclude 'build' \
  "$ROOT/apps/ios/" "$DEST/"
exec open -a Xcode "$DEST/ProductivityAssistant.xcodeproj"
