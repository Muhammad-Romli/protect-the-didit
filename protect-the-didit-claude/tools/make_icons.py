"""Draws the app icons (pure Pillow, no assets): python tools/make_icons.py  -> mobile/icons/*.png"""
import os
from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mobile", "icons")


def draw(size: int, maskable: bool) -> Image.Image:
    S = size * 4
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    bg = Image.new("RGBA", (S, S), (62, 128, 44, 255))
    bd = ImageDraw.Draw(bg)
    for i in range(0, S, S // 8):      # soft stripes of grass
        bd.rectangle((i, 0, i + S // 16, S), fill=(70, 140, 50))
    mask = Image.new("L", (S, S), 255 if maskable else 0)
    if not maskable:
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, S - 1, S - 1), S // 5, fill=255)
    img.paste(bg, (0, 0), mask)
    k = 0.62 if maskable else 0.78    # maskable icons keep the art in the safe zone
    c = S / 2
    def e(cx, cy, rx, ry, fill, outline=None, w=0):
        d.ellipse((c + cx * S * k - rx * S * k, c + cy * S * k - ry * S * k, c + cx * S * k + rx * S * k, c + cy * S * k + ry * S * k), fill=fill, outline=outline, width=w)
    ink = (38, 24, 18)
    for sx in (-1, 1):                  # ears
        e(sx * 0.30, -0.34, 0.15, 0.15, ink); e(sx * 0.30, -0.34, 0.12, 0.12, (255, 190, 170))
    e(0, 0.02, 0.46, 0.42, ink); e(0, 0.02, 0.43, 0.39, (255, 250, 240))   # face
    for sx in (-1, 1):
        e(sx * 0.16, -0.06, 0.055, 0.07, ink); e(sx * 0.14, -0.09, 0.02, 0.02, (255, 255, 255))   # eyes
        e(sx * 0.27, 0.10, 0.07, 0.05, (255, 170, 160))                                           # cheeks
    e(0, 0.06, 0.04, 0.03, (240, 120, 130))                                                        # nose
    e(0, 0.22, 0.12, 0.07, (255, 214, 70), ink, S // 90)                                           # snack in the teeth
    return img.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for size in (192, 512):
        draw(size, False).save(os.path.join(OUT, f"icon-{size}.png"))
        draw(size, True).save(os.path.join(OUT, f"icon-maskable-{size}.png"))
    draw(180, True).convert("RGB").save(os.path.join(OUT, "apple-touch-icon.png"))
    print("icons written to", OUT)
