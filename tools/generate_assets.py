#!/usr/bin/env python3
"""
Generate the raster assets for the Kut GRUB theme.

Everything is drawn at 2x and downsampled with Lanczos, which keeps the HUD
lines crisp while staying compatible with GRUB's plain PNG loader (no SVG,
no alpha blending tricks, no runtime effects).

Usage:
    python3 tools/generate_assets.py

The generated files are committed to the repository, so end users only need
GRUB + the install script.  Re-run this script after changing the artwork.
"""

from __future__ import annotations

import math
import os
import random
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
THEME = ROOT / "kut"
ICONS = THEME / "icons"
FONTS = ROOT / "assets" / "fonts"
LOGOS = ROOT / "assets" / "logos"

W, H = 1920, 1080
S = 2  # supersampling factor

CYAN = (61, 196, 246)
CYAN_SOFT = (52, 151, 195)
CYAN_DIM = (30, 92, 126)
AMBER = (255, 184, 77)
WHITE_BLUE = (224, 247, 255)
DEEP = (3, 7, 17)

FONT_TITLE = FONTS / "Rajdhani-Bold.ttf"
FONT_MED = FONTS / "Rajdhani-Medium.ttf"
FONT_MONO = FONTS / "ShareTechMono-Regular.ttf"


# ---------------------------------------------------------------------------
# generic helpers
# ---------------------------------------------------------------------------

def smoothstep(edge0: float, edge1: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def rgba(color, alpha=255):
    if len(color) == 4:
        return color
    return (*color, alpha)


def draw_arc(draw, box, start, end, fill, width=1):
    draw.arc(box, start=start, end=end, fill=fill, width=width)


def dashed_circle(draw, cx, cy, radius, color, width=1, dash_deg=2.0, gap_deg=1.4, offset=0.0):
    angle = offset
    while angle < 360 + offset:
        draw_arc(
            draw,
            (cx - radius, cy - radius, cx + radius, cy + radius),
            angle,
            angle + dash_deg,
            color,
            width,
        )
        angle += dash_deg + gap_deg


def ring_glow(size, cx, cy, radius, color, blur, width=2, alpha=120):
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), outline=rgba(color, alpha), width=width)
    return layer.filter(ImageFilter.GaussianBlur(blur))


def diamond(draw, cx, cy, r, fill):
    draw.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=fill)


def text(draw, xy, s, font, fill, anchor="la"):
    draw.text(xy, s, font=font, fill=fill, anchor=anchor)


# ---------------------------------------------------------------------------
# background
# ---------------------------------------------------------------------------

def build_background() -> Image.Image:
    w, h = W * S, H * S
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = w / 2.0, h / 2.0

    # Normalised elliptical distance, so the glow matches a 16:9 canvas.
    nx = (xx - cx) / (w * 0.56)
    ny = (yy - cy) / (h * 0.56)
    r = np.sqrt(nx * nx + ny * ny)

    # Deep navy base radial gradient.
    t = np.clip(r, 0.0, 1.0)
    t = t * t * (3.0 - 2.0 * t)
    inner = np.array([8, 31, 53], dtype=np.float32)
    middle = np.array([4, 15, 30], dtype=np.float32)
    outer = np.array([2, 5, 12], dtype=np.float32)
    t1 = np.clip(t / 0.55, 0.0, 1.0)
    t2 = np.clip((t - 0.55) / 0.45, 0.0, 1.0)
    base = inner[None, None, :] * (1 - t1[..., None]) + middle[None, None, :] * t1[..., None]
    base = base * (1 - t2[..., None]) + outer[None, None, :] * t2[..., None]

    # A soft pool of light around the reactor.
    glow = np.exp(-((r / 0.62) ** 2) * 2.0)
    base += glow[..., None] * np.array([0, 16, 26], dtype=np.float32)

    # Vignette.
    vig = 1.0 - 0.55 * smoothstep(0.55, 1.15, r)
    base *= vig[..., None]

    base = np.clip(base, 0, 255).astype(np.uint8)
    img = Image.fromarray(base, "RGB").convert("RGBA")

    # ------------------------------------------------------------------
    # hex grid (very subtle)
    # ------------------------------------------------------------------
    grid = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grid)
    hs = 36 * S  # hex radius
    hx = math.sqrt(3) * hs
    hy = 1.5 * hs
    cols = int(w / hx) + 3
    rows = int(h / hy) + 3
    for row in range(-2, rows):
        for col in range(-2, cols):
            x = col * hx + (hx / 2 if row % 2 else 0)
            y = row * hy
            pts = [
                (x + hs * math.cos(math.radians(60 * k - 30)),
                 y + hs * math.sin(math.radians(60 * k - 30)))
                for k in range(6)
            ]
            gd.line(pts + [pts[0]], fill=(21, 64, 94, 20), width=1 * S)
    # Fade the grid towards the edges.
    arr = np.asarray(grid).astype(np.float32)
    gx = (xx - cx) / (w * 0.55)
    gy = (yy - cy) / (h * 0.55)
    gr = np.sqrt(gx * gx + gy * gy)
    fade = np.clip(1.15 - gr * 1.25, 0.15, 1.0)
    arr[..., 3] *= fade
    grid = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
    img = Image.alpha_composite(img, grid)

    cx = W * S / 2
    cy = H * S / 2

    # ------------------------------------------------------------------
    # reactor glow behind the menu
    # ------------------------------------------------------------------
    glow_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gg = ImageDraw.Draw(glow_layer)
    gg.ellipse((cx - 320 * S, cy - 210 * S, cx + 320 * S, cy + 210 * S),
               fill=(0, 96, 150, 44))
    gg.ellipse((cx - 250 * S, cy - 150 * S, cx + 250 * S, cy + 150 * S),
               fill=(0, 128, 190, 40))
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(52 * S))
    img = Image.alpha_composite(img, glow_layer)

    # ------------------------------------------------------------------
    # HUD rings
    # ------------------------------------------------------------------
    hud = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(hud)

    # Soft outer halos.
    for radius, width, alpha, blur in [
        (560, 2, 100, 10),
        (520, 2, 130, 8),
        (470, 3, 130, 8),
        (420, 2, 120, 7),
    ]:
        img = Image.alpha_composite(
            img, ring_glow((w, h), cx, cy, radius * S, CYAN_SOFT, blur * S, width * S, alpha)
        )

    # Outer dotted orbit.
    dashed_circle(d, cx, cy, 560 * S, (45, 139, 180, 100), width=1 * S,
                  dash_deg=1.4, gap_deg=2.2, offset=0)

    # Fine orbit + cardinal gaps.
    for start, end in [(4, 86), (94, 176), (184, 266), (274, 356)]:
        draw_arc(d, (cx - 524 * S, cy - 524 * S, cx + 524 * S, cy + 524 * S),
                 start, end, (54, 158, 198, 125), width=1 * S)
    draw_arc(d, (cx - 470 * S, cy - 470 * S, cx + 470 * S, cy + 470 * S),
             0, 360, (42, 111, 145, 86), width=1 * S)

    # Major tick ring.
    for i in range(120):
        ang = math.radians(i * 3 - 90)
        major = i % 10 == 0
        medium = i % 5 == 0
        r1 = (492 if major else 500 if medium else 504) * S
        r2 = 516 * S
        col = (91, 211, 247, 190 if major else 130 if medium else 75)
        wdt = 3 * S if major else 2 * S if medium else 1 * S
        d.line((cx + math.cos(ang) * r1, cy + math.sin(ang) * r1,
                cx + math.cos(ang) * r2, cy + math.sin(ang) * r2), fill=col, width=wdt)

    # Inner segmented arcs.
    for i in range(8):
        start = i * 45 + 4
        end = start + 31
        draw_arc(d, (cx - 452 * S, cy - 452 * S, cx + 452 * S, cy + 452 * S),
                 start, end, (46, 148, 188, 112), width=3 * S)
    for i in range(3):
        start = i * 120 + 20
        end = start + 72
        draw_arc(d, (cx - 430 * S, cy - 430 * S, cx + 430 * S, cy + 430 * S),
                 start, end, (67, 196, 235, 180), width=4 * S)
    # Amber seal/status arc at the top.
    draw_arc(d, (cx - 430 * S, cy - 430 * S, cx + 430 * S, cy + 430 * S),
             250, 290, (255, 184, 77, 210), width=4 * S)

    # Radial connectors and nodes.
    for i in range(24):
        ang = math.radians(i * 15 - 90)
        if i % 3 == 0:
            r1, r2 = 470 * S, 492 * S
            col = (78, 191, 231, 140)
        else:
            r1, r2 = 478 * S, 488 * S
            col = (54, 130, 165, 75)
        d.line((cx + math.cos(ang) * r1, cy + math.sin(ang) * r1,
                cx + math.cos(ang) * r2, cy + math.sin(ang) * r2), fill=col, width=1 * S)
    for i in range(16):
        ang = math.radians(i * 22.5 - 90)
        x = cx + math.cos(ang) * 540 * S
        y = cy + math.sin(ang) * 540 * S
        r = 5 * S if i % 4 == 0 else 3 * S
        diamond(d, x, y, r, (104, 221, 250, 210 if i % 4 == 0 else 140))

    # Cardinal crosshair marks, outside the tick ring.
    for ang_deg in (0, 90, 180, 270):
        ang = math.radians(ang_deg - 90)
        for off in (-7, 0, 7):
            aa = math.radians(ang_deg + off - 90)
            r1, r2 = 570 * S, 586 * S
            d.line((cx + math.cos(aa) * r1, cy + math.sin(aa) * r1,
                    cx + math.cos(aa) * r2, cy + math.sin(aa) * r2),
                   fill=(64, 175, 214, 100), width=1 * S)

    img = Image.alpha_composite(img, hud)

    # ------------------------------------------------------------------
    # side readouts
    # ------------------------------------------------------------------
    side = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(side)
    f_tiny = ImageFont.truetype(str(FONT_MONO), 12 * S)

    def bracket(x, y, w_, h_, flip_x=False, flip_y=False):
        sx = -1 if flip_x else 1
        sy = -1 if flip_y else 1
        x2, y2 = x + w_ * sx, y + h_ * sy
        sd.line((x, y2, x, y, x2, y), fill=(49, 152, 190, 105), width=1 * S)
        sd.line((x, y, x + 24 * S * sx, y), fill=(78, 201, 235, 150), width=2 * S)
        sd.line((x, y, x, y + 24 * S * sy), fill=(78, 201, 235, 150), width=2 * S)

    rng = random.Random(2077)

    def data_stream(x, y, width, rows=16, right=False):
        """Abstract telemetry traces.

        No numbers or fabricated status values are baked into the artwork:
        everything that looks like a reading is rendered live by GRUB or by
        the install-time information labels.
        """
        for i in range(rows):
            yy = y + i * 20
            frac = rng.uniform(0.12, 0.98)
            length = width * frac
            x0 = x - length if right else x
            alpha = rng.randint(30, 100) if i % 5 else rng.randint(90, 150)
            sd.line((x0 * S, yy * S, (x0 + length) * S, yy * S),
                    fill=(50, 157, 194, alpha), width=1 * S)
            sd.rectangle(((x - 2) * S, (yy - 2) * S, (x + 3) * S, (yy + 3) * S),
                         outline=(78, 201, 235, min(210, alpha + 60)), width=1 * S)
            if i % 4 == 0:
                diamond(sd, (x0 + length) * S, yy * S, 3 * S,
                        (104, 221, 250, min(200, alpha + 50)))

    data_stream(126, 340, 170)
    data_stream(1794, 340, 170, right=True)

    # Small vertical scales next to the telemetry traces.
    for x in (104, 1816):
        for i in range(17):
            yy = 290 + i * 18
            length = 9 if i % 4 else 16
            alpha = 85 if i % 4 else 145
            sd.line((x * S, yy * S, (x + (length if x < 500 else -length)) * S, yy * S),
                    fill=(50, 157, 194, alpha), width=1 * S)

    bracket(92 * S, 300 * S, 300 * S, 360 * S)
    bracket(1828 * S, 300 * S, 300 * S, 360 * S, flip_x=True)
    bracket(92 * S, 810 * S, 300 * S, 150 * S, flip_y=True)
    bracket(1828 * S, 810 * S, 300 * S, 150 * S, flip_x=True, flip_y=True)

    # Top branding (no runtime status claims).
    text(sd, (92 * S, 58 * S), "KUT // HUD 04.2", f_tiny, (64, 157, 190, 125))
    text(sd, (1828 * S, 58 * S), "KUT // UI CORE", f_tiny, (64, 157, 190, 125), anchor="ra")
    text(sd, (92 * S, 74 * S), "TURKIC-INSPIRED INTERFACE", f_tiny, (42, 104, 130, 85))
    text(sd, (1828 * S, 74 * S), "KUT BOOT SYSTEM", f_tiny, (42, 104, 130, 85), anchor="ra")

    # Bottom strip.
    sd.line((120 * S, 1005 * S, 1800 * S, 1005 * S), fill=(29, 98, 126, 90), width=1 * S)
    for i in range(32):
        x = 130 + i * 53
        sd.line((x * S, 1001 * S, (x + 22) * S, 1001 * S), fill=(43, 132, 166, 80), width=1 * S)
    text(sd, (cx, 1025 * S), "KUT  //  BOOT INTERFACE",
         f_tiny, (48, 125, 153, 110), anchor="ma")

    # Screen corner brackets.
    margin = 64 * S
    arm = 88 * S
    for x, y, sx, sy in [
        (margin, margin, 1, 1),
        (w - margin, margin, -1, 1),
        (margin, h - margin, 1, -1),
        (w - margin, h - margin, -1, -1),
    ]:
        sd.line((x, y + arm * sy, x, y, x + arm * sx, y),
                fill=(45, 142, 177, 90), width=1 * S)
        sd.line((x, y, x + 22 * S * sx, y), fill=(66, 185, 220, 140), width=2 * S)
        sd.line((x, y, x, y + 22 * S * sy), fill=(66, 185, 220, 140), width=2 * S)

    img = Image.alpha_composite(img, side)

    # ------------------------------------------------------------------
    # tiny particles / stars
    # ------------------------------------------------------------------
    rng = random.Random(7419)
    dust = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dd = ImageDraw.Draw(dust)
    for _ in range(170):
        x = rng.uniform(0, w)
        y = rng.uniform(0, h)
        # keep the centre calm
        if ((x - cx) ** 2 / (w * 0.23) ** 2 + (y - cy) ** 2 / (h * 0.23) ** 2) < 1:
            continue
        a = rng.randint(18, 62)
        rr = rng.choice([1, 1, 1, 2]) * S
        dd.ellipse((x - rr, y - rr, x + rr, y + rr), fill=(112, 203, 235, a))
    img = Image.alpha_composite(img, dust)

    # Final downsample and a touch of contrast.
    img = img.convert("RGB").resize((W, H), Image.LANCZOS)
    arr = np.asarray(img).astype(np.float32)
    # Keep the extreme corners aligned with desktop-color for crop/padding.
    arr = np.clip((arr - 128) * 1.025 + 128, 0, 255)
    img = Image.fromarray(arr.astype(np.uint8), "RGB")

    # Put the exact desktop colour into the four corners (helps with padding mode).
    px = img.load()
    for x, y in [(0, 0), (W - 1, 0), (0, H - 1), (W - 1, H - 1)]:
        px[x, y] = DEEP
    return img


# ---------------------------------------------------------------------------
# 9-slice boxes
# ---------------------------------------------------------------------------

def save_slices(name: str, image: Image.Image, slice_size: int):
    size = image.size
    s = slice_size
    boxes = {
        "nw": (0, 0, s, s),
        "n": (s, 0, size[0] - s, s),
        "ne": (size[0] - s, 0, size[0], s),
        "w": (0, s, s, size[1] - s),
        "c": (s, s, size[0] - s, size[1] - s),
        "e": (size[0] - s, s, size[0], size[1] - s),
        "sw": (0, size[1] - s, s, size[1]),
        "s": (s, size[1] - s, size[0] - s, size[1]),
        "se": (size[0] - s, size[1] - s, size[0], size[1]),
    }
    for suffix, box in boxes.items():
        image.crop(box).save(THEME / f"{name}_{suffix}.png", optimize=True)


def make_menu_box():
    w, h = 1200, 560
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    radius = 22

    # Vertical glass gradient, clipped to a rounded rectangle.
    grad = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for y in range(h):
        t = y / (h - 1)
        r = int(6 + (3 - 6) * t)
        g = int(24 + (10 - 24) * t)
        b = int(42 + (20 - 42) * t)
        a = int(226 + (244 - 226) * t)
        gd.line((0, y, w, y), fill=(r, g, b, a))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=255)
    img.paste(grad, (0, 0), mask)

    # Outer and inner keylines.
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, outline=(80, 205, 247, 128), width=2)
    d.rounded_rectangle((3, 3, w - 4, h - 4), radius=radius - 3, outline=(12, 66, 96, 145), width=1)
    d.rounded_rectangle((7, 7, w - 8, h - 8), radius=radius - 6, outline=(47, 142, 180, 38), width=1)

    # Very subtle horizontal scan lines.
    for y in range(14, h - 14, 6):
        d.line((10, y, w - 10, y), fill=(38, 122, 158, 10), width=1)

    # Top highlight/energy line, fading at the ends.
    line = Image.new("RGBA", (w, 4), (0, 0, 0, 0))
    ld = ImageDraw.Draw(line)
    for x in range(w):
        edge = min(x, w - 1 - x) / (w * 0.22)
        a = int(170 * max(0.0, min(1.0, edge)))
        ld.line((x, 0, x, 2), fill=(92, 217, 250, a))
    img.alpha_composite(line, (0, 1))

    # Save at 1x; the drawing already uses native pixels.
    save_slices("menu", img, 22)


def make_select_box():
    w, h = 900, 56
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    radius = 11

    grad = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for x in range(w):
        t = x / (w - 1)
        r = int(10 + (4 - 10) * t)
        g = int(58 + (21 - 58) * t)
        b = int(85 + (38 - 85) * t)
        a = int(238 + (176 - 238) * t)
        gd.line((x, 0, x, h), fill=(r, g, b, a))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=255)
    img.paste(grad, (0, 0), mask)

    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, outline=(91, 218, 250, 190), width=1)
    d.rounded_rectangle((2, 2, w - 3, h - 3), radius=radius - 2, outline=(29, 108, 143, 110), width=1)

    # Bright left energy bar.
    d.rounded_rectangle((1, 5, 5, h - 6), radius=2, fill=(112, 231, 255, 255))
    d.rectangle((2, 10, 4, h - 11), fill=(255, 255, 255, 190))

    # Chevron on the right.
    cy = h // 2
    d.line((w - 22, cy - 7, w - 15, cy, w - 22, cy + 7), fill=(126, 231, 255, 220), width=2)
    d.line((w - 28, cy - 7, w - 21, cy, w - 28, cy + 7), fill=(76, 180, 215, 110), width=1)

    # Sparse micro-ticks.
    for x in range(24, w - 40, 26):
        d.line((x, h - 5, x + 8, h - 5), fill=(76, 185, 220, 45), width=1)

    save_slices("select", img, 14)


def make_progress_boxes():
    # Frame: dark glass with a thin cyan keyline.
    w, h = 64, 24
    frame = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(frame)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=6, fill=(4, 18, 32, 220),
                        outline=(43, 136, 172, 150), width=1)
    d.rounded_rectangle((2, 2, w - 3, h - 3), radius=5, outline=(8, 36, 54, 160), width=1)
    save_slices("progress_bar", frame, 7)

    # Highlight: cyan energy fill with a brighter leading edge.
    hl = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hl)
    for x in range(w):
        t = x / (w - 1)
        r = int(38 + 45 * t)
        g = int(186 + 45 * t)
        b = int(228 + 22 * t)
        a = int(235 - 30 * t)
        hd.line((x, 0, x, h), fill=(r, g, b, a))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=6, fill=255)
    hl.putalpha(Image.composite(hl.getchannel("A"), Image.new("L", (w, h), 0), mask))
    hd.rounded_rectangle((0, 0, w - 1, h - 1), radius=6, outline=(153, 244, 255, 230), width=1)
    for x in range(4, w - 4, 9):
        hd.line((x, 3, x, h - 4), fill=(220, 252, 255, 55), width=1)
    save_slices("progress_highlight", hl, 7)


# ---------------------------------------------------------------------------
# icons
# ---------------------------------------------------------------------------

def render_svg(svg: Path, out: Path, width=512):
    inkscape = shutil.which("inkscape")
    if not inkscape:
        raise RuntimeError("inkscape is required to render the source SVG logos")
    subprocess.run(
        [inkscape, str(svg), "--export-type=png", "--export-filename=" + str(out),
         "--export-width=" + str(width), "--export-background-opacity=0"],
        check=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
    )


def icon_canvas(im: Image.Image, size=96, pad=7, glow=True) -> Image.Image:
    im = im.convert("RGBA")
    im.thumbnail((size - 2 * pad, size - 2 * pad), Image.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    x = (size - im.width) // 2
    y = (size - im.height) // 2

    if glow:
        alpha = im.getchannel("A").point(lambda a: int(a * 0.38))
        halo = Image.new("RGBA", im.size, (70, 208, 255, 0))
        halo.putalpha(alpha)
        halo = halo.filter(ImageFilter.GaussianBlur(4))
        canvas.alpha_composite(halo, (x, y))

    canvas.alpha_composite(im, (x, y))
    return canvas


def make_logo_icons(tmp: Path):
    # Keep this as a list of pairs: several GRUB icon names intentionally
    # share one source SVG (linux, apple), which a dict would silently drop.
    mapping = [
        ("ubuntu.svg", "ubuntu.png"),
        ("pardus.svg", "pardus.png"),
        ("windows.svg", "windows.png"),
        ("debian.svg", "debian.png"),
        ("fedora.svg", "fedora.png"),
        ("archlinux.svg", "archlinux.png"),
        ("linuxmint.svg", "linuxmint.png"),
        ("manjaro.svg", "manjaro.png"),
        ("opensuse.svg", "opensuse.png"),
        ("kalilinux.svg", "kali.png"),
        ("popos.svg", "pop.png"),
        ("zorin.svg", "zorin.png"),
        ("linux.svg", "gnu-linux.png"),
        ("linux.svg", "linux.png"),
        ("freebsd.svg", "freebsd.png"),
        ("android.svg", "android.png"),
        ("apple.svg", "apple.png"),
        ("apple.svg", "macos.png"),
        ("apple.svg", "osx.png"),
        ("apple.svg", "darwin.png"),
        ("linux.svg", "gnu.png"),
    ]
    # Some Simple Icons marks use near-black brand colours that disappear on
    # the dark HUD background. Recolour those while keeping the exact shape.
    recolor = {
        "apple.png": (234, 249, 255),   # white Apple mark
        "macos.png": (234, 249, 255),
        "osx.png": (234, 249, 255),
        "darwin.png": (234, 249, 255),
        "kali.png": (143, 203, 232),    # brighter Kali blue-grey
    }
    for svg_name, png_name in mapping:
        src = LOGOS / svg_name
        rendered = tmp / (svg_name.replace(".svg", ".png"))
        if not rendered.exists():
            render_svg(src, rendered)
        im = Image.open(rendered).convert("RGBA")
        if png_name in recolor:
            tint = Image.new("RGBA", im.size, (*recolor[png_name], 255))
            im = Image.composite(tint, Image.new("RGBA", im.size, (0, 0, 0, 0)),
                                 im.getchannel("A"))
        icon_canvas(im).save(ICONS / png_name, optimize=True)


def make_os_icon(tmp: Path):
    """Generic HUD globe/ring for entries without a distro class."""
    scale = 4
    size = 96 * scale
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = size / 2
    col = (88, 208, 244, 230)
    dim = (49, 136, 171, 170)
    for r, a, w in [(33, 190, 2), (25, 120, 2), (17, 90, 1)]:
        d.ellipse((c - r * scale, c - r * scale, c + r * scale, c + r * scale),
                  outline=(col[0], col[1], col[2], a), width=w * scale)
    # latitude/longitude arcs
    d.arc((c - 33 * scale, c - 14 * scale, c + 33 * scale, c + 14 * scale), 0, 360,
          fill=dim, width=1 * scale)
    d.line((c, c - 33 * scale, c, c + 33 * scale), fill=dim, width=1 * scale)
    d.line((c - 33 * scale, c, c + 33 * scale, c), fill=dim, width=1 * scale)
    diamond(d, c, c - 40 * scale, 4 * scale, (255, 184, 77, 230))
    diamond(d, c, c + 40 * scale, 3 * scale, (88, 208, 244, 210))
    img = img.resize((96, 96), Image.LANCZOS)
    icon_canvas(img, pad=0, glow=True).save(ICONS / "os.png", optimize=True)


def make_chip_icon(name: str, label: str, color=(88, 208, 244)):
    scale = 4
    size = 96 * scale
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    body = (12, 36, 56, 230)
    line = (*color, 225)
    dim = (*color, 110)
    # pins
    for i in range(4):
        off = (20 + i * 15) * scale
        for x1, x2 in [((10) * scale, (20) * scale), ((76) * scale, (86) * scale)]:
            d.rectangle((x1, off, x2, off + 5 * scale), fill=line)
        for y1, y2 in [((10) * scale, (20) * scale), ((76) * scale, (86) * scale)]:
            d.rectangle((off, y1, off + 5 * scale, y2), fill=line)
    d.rounded_rectangle((20 * scale, 20 * scale, 76 * scale, 76 * scale),
                        radius=7 * scale, fill=body, outline=line, width=2 * scale)
    d.rounded_rectangle((27 * scale, 27 * scale, 69 * scale, 69 * scale),
                        radius=4 * scale, outline=dim, width=1 * scale)
    if label:
        f = ImageFont.truetype(str(FONT_MONO), 15 * scale)
        text(d, (48 * scale, 47 * scale), label, f, (*color, 240), anchor="ma")
    img = img.resize((96, 96), Image.LANCZOS)
    icon_canvas(img, pad=0, glow=True).save(ICONS / name, optimize=True)


def make_recovery_icon():
    scale = 4
    size = 96 * scale
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    col = (255, 184, 77, 230)
    dim = (255, 184, 77, 120)
    c = 48 * scale
    # gear
    for i in range(8):
        ang = math.radians(i * 45)
        x = c + math.cos(ang) * 29 * scale
        y = c + math.sin(ang) * 29 * scale
        d.ellipse((x - 6 * scale, y - 6 * scale, x + 6 * scale, y + 6 * scale), fill=col)
    d.ellipse((c - 26 * scale, c - 26 * scale, c + 26 * scale, c + 26 * scale),
              outline=col, width=3 * scale)
    d.ellipse((c - 9 * scale, c - 9 * scale, c + 9 * scale, c + 9 * scale),
              outline=dim, width=2 * scale)
    # wrench cut-out
    d.line((c - 13 * scale, c + 13 * scale, c + 13 * scale, c - 13 * scale),
           fill=(5, 15, 26, 255), width=7 * scale)
    d.line((c - 13 * scale, c + 13 * scale, c + 13 * scale, c - 13 * scale),
           fill=dim, width=2 * scale)
    img = img.resize((96, 96), Image.LANCZOS)
    icon_canvas(img, pad=0, glow=True).save(ICONS / "recovery.png", optimize=True)


def make_memtest_icon():
    scale = 4
    size = 96 * scale
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    col = (115, 224, 196, 230)
    dim = (115, 224, 196, 100)
    d.rounded_rectangle((18 * scale, 24 * scale, 78 * scale, 72 * scale), radius=5 * scale,
                        fill=(7, 28, 38, 230), outline=col, width=2 * scale)
    for i in range(4):
        x = 28 + i * 14
        d.rectangle((x * scale, 32 * scale, (x + 8) * scale, 64 * scale), outline=dim, width=1 * scale)
    for i in range(5):
        x = 24 + i * 12
        d.rectangle((x * scale, 16 * scale, (x + 5) * scale, 24 * scale), fill=col)
        d.rectangle((x * scale, 72 * scale, (x + 5) * scale, 80 * scale), fill=col)
    img = img.resize((96, 96), Image.LANCZOS)
    icon_canvas(img, pad=0, glow=True).save(ICONS / "memtest.png", optimize=True)


def make_simple_icons():
    make_os_icon(Path(tempfile.gettempdir()))
    make_chip_icon("efi.png", "EFI")
    make_chip_icon("uefi.png", "UEFI")
    make_recovery_icon()
    make_memtest_icon()


# ---------------------------------------------------------------------------
# preview helpers
# ---------------------------------------------------------------------------

def main():
    THEME.mkdir(exist_ok=True)
    ICONS.mkdir(exist_ok=True)

    print("background ...")
    bg = build_background()
    bg.save(THEME / "background.png", optimize=True)

    print("styled boxes ...")
    make_menu_box()
    make_select_box()
    make_progress_boxes()

    print("icons ...")
    with tempfile.TemporaryDirectory() as td:
        make_logo_icons(Path(td))
    make_simple_icons()

    # Drop the legacy hand-drawn logo placeholders. The real brand marks are
    # rendered into icons/ from the SVG sources instead.
    for legacy in ("pardus_logo.png", "ubuntu_logo.png"):
        p = THEME / legacy
        if p.exists():
            p.unlink()

    print("done")


if __name__ == "__main__":
    main()
