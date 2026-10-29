"""Browser (pygbag / emscripten) helpers. On desktop everything here is a harmless no-op.

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


# Injected into the page at start-up (works with pygbag's stock template, no custom template needed):
# fit the 16:9 canvas into the window WITHOUT stretching (the stock page squashed it), scale it smoothly
# (not pixelated), keep the page background dark, and stop the right-click menu / page scrolling.
_PAGE_JS = """
(function () {
  if (document.getElementById('ptd-style')) return;
  var s = document.createElement('style');
  s.id = 'ptd-style';
  s.textContent =
    'html,body{margin:0!important;padding:0!important;width:100%!important;height:100%!important;' +
    'overflow:hidden!important;background:#0c160e!important;overscroll-behavior:none!important;}' +
    'canvas#canvas,body>canvas{position:fixed!important;left:50%!important;top:50%!important;' +
    'transform:translate(-50%,-50%)!important;margin:0!important;border:0!important;padding:0!important;' +
    'width:min(100vw,calc(100vh * 16 / 9))!important;height:min(100vh,calc(100vw * 9 / 16))!important;' +
    'max-width:none!important;max-height:none!important;image-rendering:auto!important;' +
    'touch-action:none;outline:none;}';
  document.head.appendChild(s);
  document.addEventListener('contextmenu', function (e) { e.preventDefault(); });
  window.addEventListener('keydown', function (e) {
    if ([32, 37, 38, 39, 40].indexOf(e.keyCode) >= 0) e.preventDefault();
  }, { passive: false });
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
