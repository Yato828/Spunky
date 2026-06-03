from collections import deque
from pathlib import Path

from PIL import Image, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "Spunky6.jpg"
DEST = ROOT / "assets" / "spunky-king-contour.png"


def is_background(pixel):
    r, g, b = pixel[:3]
    return max(r, g, b) < 38


def main():
    im = Image.open(SRC).convert("RGBA")
    w, h = im.size
    px = im.load()

    outside = Image.new("L", (w, h), 0)
    out_px = outside.load()
    q = deque()

    def push(x, y):
        if 0 <= x < w and 0 <= y < h and not out_px[x, y] and is_background(px[x, y]):
            out_px[x, y] = 255
            q.append((x, y))

    for x in range(w):
        push(x, 0)
        push(x, h - 1)
    for y in range(h):
        push(0, y)
        push(w - 1, y)

    while q:
        x, y = q.popleft()
        push(x + 1, y)
        push(x - 1, y)
        push(x, y + 1)
        push(x, y - 1)

    soft_outside = outside.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(0.55))
    alpha = Image.new("L", (w, h), 255)
    alpha_px = alpha.load()
    soft_px = soft_outside.load()

    for y in range(h):
        for x in range(w):
            alpha_px[x, y] = 255 - soft_px[x, y]

    out = im.copy()
    out.putalpha(alpha)
    bbox = out.getbbox()
    if bbox:
        pad = 14
        left = max(0, bbox[0] - pad)
        top = max(0, bbox[1] - pad)
        right = min(w, bbox[2] + pad)
        bottom = min(h, bbox[3] + pad)
        out = out.crop((left, top, right, bottom))

    out.save(DEST)
    print(DEST)


if __name__ == "__main__":
    main()
