"""Browser (pygbag / emscripten) helpers, including the phone page setup (viewport, rotate prompt, auto fullscreen). On desktop everything here is a harmless no-op.

UNTESTED in a real browser (written without pygbag available): the `platform.window` calls are wrapped in
try/except so a wrong guess degrades to "feature missing" instead of a crash.
"""
from __future__ import annotations

import sys

IS_WEB = sys.platform == "emscripten"


def _local_storage():
    try:
        import platform  # pygbag patches this module with `window` (the JS global object)
        return platform.window.localStorage
    except Exception:
        return None


def storage_get(key: str) -> str | None:
    ls = _local_storage()
    if ls is None:
        return None
    try:
        value = ls.getItem(key)
        return None if value is None else str(value)
    except Exception:
        return None


def storage_set(key: str, value: str) -> bool:
    ls = _local_storage()
    if ls is None:
        return False
    try:
        ls.setItem(key, value)
        return True
    except Exception:
        return False


def storage_remove(key: str) -> None:
    ls = _local_storage()
    if ls is None:
        return
    try:
        ls.removeItem(key)
    except Exception:
        pass


def _eval(js: str) -> None:
    if not IS_WEB:
        return
    try:
        import platform
        platform.window.eval(js)
    except Exception:
        pass


def is_coarse_pointer() -> bool:
    """Browser only: True on phones / tablets (the main pointer is a finger). Desktop: always False."""
    if not IS_WEB:
        return False
    try:
        import platform
        return bool(platform.window.matchMedia("(pointer: coarse)").matches)
    except Exception:
        return False


# Injected into the page at start-up (works with pygbag's stock template, no custom template needed):
# fit the 16:9 canvas into the window WITHOUT stretching (the stock page squashed it), scale it smoothly
# (not pixelated), keep the page background dark, and stop the right-click menu / page scrolling.
_PAGE_JS = """
(function () {
  if (document.getElementById('ptd-style')) return;
  var vp = document.querySelector('meta[name=viewport]');
  if (!vp) { vp = document.createElement('meta'); vp.name = 'viewport'; document.head.appendChild(vp); }
  vp.content = 'width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover';
  var s = document.createElement('style');
  s.id = 'ptd-style';
  s.textContent =
    'html,body{margin:0!important;padding:0!important;width:100%!important;height:100%!important;' +
    'overflow:hidden!important;background:#0c160e!important;overscroll-behavior:none!important;' +
    '-webkit-user-select:none;user-select:none;-webkit-touch-callout:none;-webkit-tap-highlight-color:transparent;}' +
    'canvas#canvas,body>canvas{position:fixed!important;left:50%!important;top:50%!important;' +
    'transform:translate(-50%,-50%)!important;margin:0!important;border:0!important;padding:0!important;' +
    'width:min(100vw,calc(100vh * 16 / 9))!important;height:min(100vh,calc(100vw * 9 / 16))!important;' +
    'max-width:none!important;max-height:none!important;image-rendering:auto!important;' +
    'touch-action:none;outline:none;}' +
    '@supports (height:100dvh){canvas#canvas,body>canvas{' +
    'width:min(100vw,calc(100dvh * 16 / 9))!important;height:min(100dvh,calc(100vw * 9 / 16))!important;}}' +
    '#ptd-rotate{display:none;position:fixed;inset:0;z-index:99999;background:#0c160e;color:#ffd646;' +
    'font:700 22px/1.4 sans-serif;text-align:center;align-items:center;justify-content:center;flex-direction:column;}' +
    '@media (orientation:portrait) and (pointer:coarse){#ptd-rotate{display:flex;}}';
  document.head.appendChild(s);
  var r = document.createElement('div');
  r.id = 'ptd-rotate';
  r.innerHTML = '<div style="font-size:64px;transform:rotate(90deg)">&#128241;</div><div>Rotate your phone<br>to landscape to play</div>';
  document.body.appendChild(r);
  document.addEventListener('contextmenu', function (e) { e.preventDefault(); });
  window.addEventListener('keydown', function (e) {
    if ([32, 37, 38, 39, 40].indexOf(e.keyCode) >= 0) e.preventDefault();
  }, { passive: false });
  document.addEventListener('gesturestart', function (e) { e.preventDefault(); });
  // phones: the first tap (a user gesture, so the browser allows it) goes fullscreen and locks landscape
  if (window.matchMedia && window.matchMedia('(pointer: coarse)').matches) {
    var once = function () {
      document.removeEventListener('touchend', once, true);
      document.removeEventListener('click', once, true);
      try {
        var d = document, e = d.documentElement;
        if (!d.fullscreenElement && !d.webkitFullscreenElement) {
          var rq = e.requestFullscreen || e.webkitRequestFullscreen;
          if (rq) { var p = rq.call(e); if (p && p.catch) p.catch(function () {}); }
        }
        if (screen.orientation && screen.orientation.lock) {
          var q = screen.orientation.lock('landscape'); if (q && q.catch) q.catch(function () {});
        }
      } catch (err) {}
    };
    document.addEventListener('touchend', once, true);
    document.addEventListener('click', once, true);
  }
})();
"""

_FULLSCREEN_JS = """
(function () {
  var d = document, e = d.documentElement;
  if (d.fullscreenElement || d.webkitFullscreenElement) {
    (d.exitFullscreen || d.webkitExitFullscreen).call(d);
  } else {
    (e.requestFullscreen || e.webkitRequestFullscreen).call(e);
  }
})();
"""


def setup_page() -> None:
    """Browser only: fit/scale the canvas, block the context menu and page scrolling keys."""
    _eval(_PAGE_JS)


def toggle_fullscreen() -> None:
    """Browser only: page fullscreen. Browsers only allow it shortly after a click / key press, so call it
    straight from a button handler (the loop runs right after the event, well inside that window)."""
    _eval(_FULLSCREEN_JS)
