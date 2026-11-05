# Protect The Didit on phones

Status: written WITHOUT pygame or a phone in the session (only syntax-checked, the touch logic was unit-tested against a
stub, the page JS was checked in headless Chromium). Run `python tests/test_touch.py` on your PC first, then try a phone.

## Controls on a touchscreen (switches on by itself at the first touch)
- Tower card, then tap (or drag) on the map: a ghost with its range ring appears. While dragging it floats above your finger.
  Press the green OK to build, the red X to cancel. You can also drag a card straight onto the map. A red OK means the spot is invalid.
- Aimed abilities (Bima cube / sphere) work the same way: tap the map, then OK.
- Tap a tower to select it (the tap area is larger than on a PC). Upgrade / sell / activities / target arrows are in the side panel.
- START and speed buttons are in the bar. The gear (top right) opens Options and freezes the game = pause. After the app was in the
  background the game is paused: tap to resume. On the win / lose screen tap PLAY AGAIN.
- Bima Graph: tap the formula box, a keypad opens (digits, x, + - * / ^, pi, abs, sqrt, sin cos tan ln exp, DEL, CLR, DONE). Then tap FIRE.
  Function keys that your tier has not unlocked are greyed out.
- Portrait shows "Rotate your phone". The first tap switches to fullscreen and tries to lock landscape.

## 1. Test on your phone right now (same Wi-Fi)
```
pip install pygbag
pygbag --bind 0.0.0.0 .        # check `pygbag --help` if the option is named differently in your version
```
Open `http://<your PC's IP>:8000` on the phone. (Some browsers only allow fullscreen / install on HTTPS; localhost counts as secure, a LAN IP does not.)

## 2. Install-like web app (PWA), no store needed
```
pygbag --build .
python tools/make_mobile_web.py     # adds manifest, service worker, icons, phone meta tags to build/web
```
Upload `build/web` to any HTTPS host (itch.io HTML5, GitHub Pages, Netlify). The repo also has `.github/workflows/pages.yml`: every push to `main` builds this and deploys it to GitHub Pages (enable Pages with source "GitHub Actions" in the repo settings). On the phone: browser menu -> Add to Home screen.
It then starts fullscreen, landscape, with the hamster icon. After one full online run the service worker caches the files, so it also
starts offline (the pygbag runtime is fetched from pygame-web.github.io the first time).

## 3. APK (Android)
Not built in the session (no Android SDK, no network). The project is a WebView wrapper (Capacitor) around the web version.
- Easiest: push the project folder to a GitHub repo, tab Actions -> "Build Android APK" -> Run workflow. Download `app-debug.apk`
  from the run's artifacts, copy it to the phone, allow "install unknown apps".
- Local (Linux / macOS / WSL with JDK 17, Node 20, Android SDK): `bash mobile/android/build_apk.sh`
- It is a debug-signed APK: fine for your own phone and friends, not for the Play Store (that needs a release keystore).
- Limit: the game runtime still loads from the pygbag CDN on the first start, so the first launch needs internet.
- If you want a fully native, offline Android build with better speed, the alternative is Buildozer / python-for-android; that is a
  different build chain and was not set up here.

## Performance
WebAssembly is slower than native. The existing governor drops to light effects below 25 fps. On a weak phone set Options: Particles Low,
Danger glow off, Screen shake off.
