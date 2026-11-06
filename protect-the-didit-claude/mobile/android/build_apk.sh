#!/usr/bin/env bash
# Local APK build (Linux / macOS / WSL). Needs: Python 3.12, Node 20, JDK 17, Android SDK (ANDROID_HOME set).
set -euo pipefail
cd "$(dirname "$0")/../.."
pip install pygbag
pygbag --build .
python tools/make_mobile_web.py
cd mobile/android
npm install
rm -rf www && cp -r ../../build/web www
npx cap add android
python patch_android.py
npx cap sync android
cd android && ./gradlew assembleDebug
echo "APK: mobile/android/android/app/build/outputs/apk/debug/app-debug.apk"
