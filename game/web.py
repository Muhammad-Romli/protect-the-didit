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


def storage_set(key: str, value: str) -> None:
    ls = _local_storage()
    if ls is None:
        return
    try:
        ls.setItem(key, value)
    except Exception:
        pass


def suppress_context_menu() -> None:
    """Right-click cancels placing/aiming in the game: keep the browser's context menu away."""
    if not IS_WEB:
        return
    try:
        import platform
        platform.window.eval("document.addEventListener('contextmenu', function (e) { e.preventDefault(); });")
    except Exception:
        pass
