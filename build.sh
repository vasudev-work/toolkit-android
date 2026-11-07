#!/usr/bin/env bash
# Builds every APK in this repository without Gradle:
#   aapt2 (resources) -> ecj (javac) -> d8 (dex) -> zipalign -> apksigner
#
# Requirements: JDK 17+, Android SDK build-tools 34 + platform android-34,
# and tools/ecj.jar (run tools/fetch-deps.sh once).
#
#   export JAVA_HOME=/path/to/jdk
#   export ANDROID_HOME=/path/to/android-sdk
#   ./build.sh                 # all apps
#   ./build.sh calculator qr   # just these
set -euo pipefail

cd "$(dirname "$0")"

: "${JAVA_HOME:?set JAVA_HOME to a JDK 17 or newer}"
: "${ANDROID_HOME:?set ANDROID_HOME to your Android SDK}"

if [ ! -f tools/ecj.jar ]; then
  echo "tools/ecj.jar is missing - run tools/fetch-deps.sh first" >&2
  exit 1
fi

apps=("$@")
if [ ${#apps[@]} -eq 0 ]; then
  apps=(calculator clock notes qr files)
fi

mkdir -p dist
for app in "${apps[@]}"; do
  python3 tools/build_app.py "$app"
done
echo
echo "APKs in dist/:"
ls -1sh dist/*.apk
