from collections import deque
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ASSETS.mkdir(exist_ok=True)


def edge_remove_background(src: Path, dest: Path, tolerance=58, feather=1, pad=22):
    im = Image.open(src).convert("RGBA")
    w, h = im.size
    px = im.load()
    bg = [[False] * w for _ in range(h)]
    q = deque()
    samples = []

    corner = max(8, min(w, h) // 18)
    corner_points = (
        (0, 0, corner, corner),
        (w - corner, 0, w, corner),
        (0, h - corner, corner, h),
        (w - corner, h - corner, w, h),
    )
    for left, top, right, bottom in corner_points:
        for x in range(left, right, max(1, corner // 4)):
            for y in range(top, bottom, max(1, corner // 4)):
                samples.append(px[x, y])

    def push(x, y):
        if 0 <= x < w and 0 <= y < h and not bg[y][x]:
            bg[y][x] = True
            q.append((x, y))

    for x in range(w):
        push(x, 0)
        push(x, h - 1)
    for y in range(h):
        push(0, y)
        push(w - 1, y)

    def close(a, b):
        return max(abs(a[0] - b[0]), abs(a[1] - b[1]), abs(a[2] - b[2])) <= tolerance

    def looks_like_edge(pixel):
        return any(close(pixel, sample) for sample in samples)

    while q:
        x, y = q.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and not bg[ny][nx] and looks_like_edge(px[nx, ny]):
                bg[ny][nx] = True
                q.append((nx, ny))

    alpha = Image.new("L", (w, h), 255)
    ap = alpha.load()
    for y in range(h):
        for x in range(w):
            if bg[y][x]:
                ap[x, y] = 0

    alpha = alpha.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(feather))
    out = im.copy()
    out.putalpha(alpha)
    bbox = out.getbbox()
    if bbox:
        left = max(0, bbox[0] - pad)
        top = max(0, bbox[1] - pad)
        right = min(w, bbox[2] + pad)
        bottom = min(h, bbox[3] + pad)
        out = out.crop((left, top, right, bottom))
    out.save(dest)


def remove_checkerboard(src: Path, dest: Path):
    im = Image.open(src).convert("RGBA")
    w, h = im.size
    px = im.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if r > 214 and g > 214 and b > 214 and max(r, g, b) - min(r, g, b) < 12:
                px[x, y] = (r, g, b, 0)
    im = im.filter(ImageFilter.GaussianBlur(0.15))
    bbox = im.getbbox()
    if bbox:
        im = im.crop(bbox)
    im.save(dest)


def cut_solana_coin(src: Path, dest: Path, pad=10):
    im = Image.open(src).convert("RGBA")
    w, h = im.size
    px = im.load()
    mask = Image.new("L", (w, h), 255)
    mask_px = mask.load()

    for y in range(h):
        for x in range(w):
            r, g, b, _ = px[x, y]
            neutral = max(r, g, b) - min(r, g, b) < 18
            light_tile = neutral and r > 218 and g > 218 and b > 218
            if light_tile:
                mask_px[x, y] = 0

    # Remove only the background connected to the image edges. Bright highlights
    # inside the coin stay untouched because they are not connected to the edge.
    outside = Image.new("L", (w, h), 0)
    out_px = outside.load()
    q = deque()

    def push(x, y):
        if 0 <= x < w and 0 <= y < h and not out_px[x, y] and not mask_px[x, y]:
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
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            push(nx, ny)

    alpha = Image.new("L", (w, h), 255)
    alpha_px = alpha.load()
    for y in range(h):
        for x in range(w):
            if out_px[x, y]:
                alpha_px[x, y] = 0

    out = im.copy()
    out.putalpha(alpha)
    bbox = out.getbbox()
    if bbox:
        left = max(0, bbox[0] - pad)
        top = max(0, bbox[1] - pad)
        right = min(w, bbox[2] + pad)
        bottom = min(h, bbox[3] + pad)
        out = out.crop((left, top, right, bottom))

    cw, ch = out.size
    size = max(cw, ch)
    squared = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    squared.alpha_composite(out, ((size - cw) // 2, (size - ch) // 2))
    out = squared
    cw, ch = out.size

    circle = Image.new("L", (cw, ch), 0)
    d = ImageDraw.Draw(circle)
    inset = max(2, int(cw * 0.012))
    d.ellipse((inset, inset, cw - inset, ch - inset), fill=255)
    circle = circle.filter(ImageFilter.GaussianBlur(0.6))
    alpha = out.getchannel("A")
    clipped = Image.new("L", (cw, ch), 0)
    clipped_px = clipped.load()
    alpha_px = alpha.load()
    circle_px = circle.load()
    for y in range(ch):
        for x in range(cw):
            clipped_px[x, y] = min(alpha_px[x, y], circle_px[x, y])
    out.putalpha(clipped)
    out_px = out.load()
    for y in range(ch):
        for x in range(cw):
            if clipped_px[x, y] == 0:
                out_px[x, y] = (0, 0, 0, 0)
    out.save(dest)


def cut_character(src: Path, dest: Path, feather=0.9, pad=18):
    im = Image.open(src).convert("RGBA")
    w, h = im.size
    src_px = im.load()
    seed = Image.new("L", (w, h), 0)
    seed_px = seed.load()

    for y in range(h):
        for x in range(w):
            r, g, b, _ = src_px[x, y]
            light_body = min(r, g, b) > 125 and max(r, g, b) - min(r, g, b) < 105 and not (g > r + 28 and g > b + 20)
            cool_shadow = r > 112 and g > 125 and b > 132 and b >= r - 8
            if light_body or cool_shadow:
                seed_px[x, y] = 255

    visited = bytearray(w * h)
    best = []
    best_score = -1
    target_x = w * 0.5
    target_y = h * 0.55
    for y in range(h):
        for x in range(w):
            idx = y * w + x
            if visited[idx] or seed_px[x, y] == 0:
                continue
            q = deque([(x, y)])
            visited[idx] = 1
            comp = []
            while q:
                cx, cy = q.popleft()
                comp.append((cx, cy))
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < w and 0 <= ny < h:
                        nidx = ny * w + nx
                        if not visited[nidx] and seed_px[nx, ny]:
                            visited[nidx] = 1
                            q.append((nx, ny))
            xs = [point[0] for point in comp]
            ys = [point[1] for point in comp]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            center_x = (min_x + max_x) / 2
            center_y = (min_y + max_y) / 2
            dist = ((center_x - target_x) ** 2 + (center_y - target_y) ** 2) ** 0.5
            centered = min_x < target_x < max_x and min_y < target_y < max_y
            touches_edge = min_x <= 1 or min_y <= 1 or max_x >= w - 2 or max_y >= h - 2
            score = len(comp) / (1 + dist / max(1, min(w, h) * 0.35))
            if centered:
                score *= 2.5
            if touches_edge:
                score *= 0.08
            if score > best_score:
                best_score = score
                best = comp

    silhouette = Image.new("L", (w, h), 0)
    sil_px = silhouette.load()
    for x, y in best:
        sil_px[x, y] = 255

    outside = Image.new("L", (w, h), 0)
    out_px = outside.load()
    q = deque()

    def push_outside(x, y):
        if 0 <= x < w and 0 <= y < h and not out_px[x, y] and not sil_px[x, y]:
            out_px[x, y] = 255
            q.append((x, y))

    for x in range(w):
        push_outside(x, 0)
        push_outside(x, h - 1)
    for y in range(h):
        push_outside(0, y)
        push_outside(w - 1, y)

    while q:
        x, y = q.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            push_outside(nx, ny)

    filled = Image.new("L", (w, h), 255)
    filled_px = filled.load()
    for y in range(h):
        for x in range(w):
            if out_px[x, y]:
                filled_px[x, y] = 0

    nearby = filled.filter(ImageFilter.MaxFilter(63))
    near_px = nearby.load()
    final = filled.copy()
    final_px = final.load()
    for y in range(h):
        for x in range(w):
            if not near_px[x, y]:
                continue
            r, g, b, _ = src_px[x, y]
            red_mouth = r > 115 and g < 95 and b < 95
            pink_tongue = r > 145 and g < 145 and b > 95
            dark_face = max(r, g, b) < 80
            gold_crown = r > 145 and g > 95 and b < 110
            if red_mouth or pink_tongue or dark_face or gold_crown:
                final_px[x, y] = 255

    final = final.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(feather))
    out = im.copy()
    out.putalpha(final)
    bbox = out.getbbox()
    if bbox:
        left = max(0, bbox[0] - pad)
        top = max(0, bbox[1] - pad)
        right = min(w, bbox[2] + pad)
        bottom = min(h, bbox[3] + pad)
        out = out.crop((left, top, right, bottom))
    out.save(dest)


def make_coin(dest: Path):
    size = 512
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((32, 32, size - 32, size - 32), fill=(11, 17, 31, 255), outline=(132, 226, 255, 255), width=12)
    d.ellipse((54, 54, size - 54, size - 54), outline=(139, 92, 246, 220), width=9)
    bars = [
        (145, 163, 366, 207, (34, 211, 238), (20, 241, 149)),
        (145, 236, 366, 280, (167, 139, 250), (34, 211, 238)),
        (145, 309, 366, 353, (192, 132, 252), (96, 165, 250)),
    ]
    for x1, y1, x2, y2, c1, c2 in bars:
        d.rounded_rectangle((x1, y1, x2, y2), radius=18, fill=c1 + (255,))
        d.polygon([(x1, y1), (x1 - 42, y2), (x1 + 18, y2), (x1 + 60, y1)], fill=c2 + (255,))
        d.rounded_rectangle((x1, y1, x2, y2), radius=18, outline=(198, 244, 255, 210), width=3)
    im.save(dest)


cut_character(ROOT / "Spunky1.jpg", ASSETS / "spunky-sad.png")
edge_remove_background(ROOT / "Spunky2.jpg", ASSETS / "spunky-sleepy-tongue.png", tolerance=50)
cut_character(ROOT / "Spunky3.jpg", ASSETS / "spunky-front.png")
cut_character(ROOT / "Spunky4.png", ASSETS / "spunky-pixel.png", feather=0.2, pad=8)
cut_character(ROOT / "Spunky5.jpg", ASSETS / "spunky-tongue.png")
cut_character(ROOT / "Spunky6.jpg", ASSETS / "spunky-king.png")
cut_solana_coin(ROOT / "solana-coin-original.png", ASSETS / "solana-coin.png")
