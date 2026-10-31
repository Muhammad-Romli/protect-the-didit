"""Post-build step: turns pygbag's build/web into an installable phone web app (PWA).

    pygbag --build .
    python tools/make_mobile_web.py          # patches build/web/index.html, adds manifest + service worker + icons

Then upload build/web anywhere that serves HTTPS (itch.io, GitHub Pages, Netlify ...). On a phone: open the link,
menu -> "Add to Home screen" / "Install app": it starts fullscreen in landscape with its own icon.
"""
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "build", "web")
MARK = "<!-- ptd-mobile -->"

HEAD = MARK + """
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover">
<meta name="theme-color" content="#0c160e">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Protect The Didit">
<link rel="manifest" href="manifest.webmanifest">
<link rel="apple-touch-icon" href="icons/apple-touch-icon.png">
"""
BODY = """<script>
if ('serviceWorker' in navigator) {
  window.addEventListener('load', function () { navigator.serviceWorker.register('sw.js').catch(function () {}); });
}
</script>
"""

MANIFEST = {
    "name": "Protect The Didit", "short_name": "Didit TD", "start_url": ".", "scope": ".",
    "display": "fullscreen", "orientation": "landscape", "background_color": "#0c160e", "theme_color": "#0c160e",
    "icons": [
        {"src": "icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
        {"src": "icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
        {"src": "icons/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
    ],
}


def main() -> int:
    index = os.path.join(WEB, "index.html")
    if not os.path.isfile(index):
        print("build/web/index.html not found: run `pygbag --build .` first")
        return 1
    html = open(index, encoding="utf-8").read()
    if MARK not in html:
        html = re.sub(r"<meta[^>]+name=[\"']viewport[\"'][^>]*>", "", html, flags=re.I)   # ours replaces it
        if "</head>" in html:
            html = html.replace("</head>", HEAD + "</head>", 1)
        else:
            html = HEAD + html
        html = html.replace("</body>", BODY + "</body>", 1) if "</body>" in html else html + BODY
        open(index, "w", encoding="utf-8").write(html)
    with open(os.path.join(WEB, "manifest.webmanifest"), "w") as f:
        json.dump(MANIFEST, f, indent=1)
    shutil.copy(os.path.join(ROOT, "mobile", "sw.js"), os.path.join(WEB, "sw.js"))
    shutil.copytree(os.path.join(ROOT, "mobile", "icons"), os.path.join(WEB, "icons"), dirs_exist_ok=True)
    print("build/web is now an installable phone web app")
    return 0


if __name__ == "__main__":
    sys.exit(main())
