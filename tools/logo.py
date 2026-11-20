"""Builds every site logo and icon from the INDFORGE mod logo (tools/data/logo-source.png).

The source has two inks on a transparent background: white line art (shield border, gear, anvil,
chevrons) and a green fill. Both are traced to vector paths (potrace), so the SVGs keep the exact
shapes at any size; the PNGs are the source itself, recoloured, then downscaled.

Requires: pip install pillow numpy potracer
Run: python tools/logo.py
"""
import io
import os

import numpy as np
import potrace
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "tools", "data", "logo-source.png")
OUT = os.path.join(ROOT, "assets", "img")

# Site palette (assets/css/site.css): amber line art on the dark panel colour
LINE = (0xFF, 0xB0, 0x00)
FILL = (0x0A, 0x0E, 0x10)
BG = (0x06, 0x08, 0x0A)

PNG_SIZES = {
    "favicon-16.png": 16,
    "favicon-32.png": 32,
    "favicon-48.png": 48,
    "apple-touch-icon.png": 180,
    "icon-192.png": 192,
    "icon-512.png": 512,
    "logo-1024.png": 1024,
}


def hexc(c):
    return "#%02x%02x%02x" % c


def trace(mask):
    # potracer traces the False pixels: hand it the inverted mask
    plist = potrace.Bitmap(~mask).trace(turdsize=4, alphamax=1.0, opticurve=True, opttolerance=0.2)
    parts = []
    for curve in plist:
        s = curve.start_point
        d = ["M%.1f %.1f" % (s.x, s.y)]
        for seg in curve.segments:
            if seg.is_corner:
                d.append("L%.1f %.1f %.1f %.1f" % (seg.c.x, seg.c.y, seg.end_point.x, seg.end_point.y))
            else:
                d.append("C%.1f %.1f %.1f %.1f %.1f %.1f" % (seg.c1.x, seg.c1.y, seg.c2.x, seg.c2.y,
                                                               seg.end_point.x, seg.end_point.y))
        d.append("Z")
        parts.append("".join(d))
    return "".join(parts)


def svg(size, shield, fill, line_css, fill_css, bg=None):
    rect = '<rect width="%d" height="%d" rx="%d" fill="%s"/>' % (size, size, size // 8, bg) if bg else ""
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d">%s'
            '<path fill="%s" fill-rule="evenodd" d="%s"/>'
            '<path fill="%s" fill-rule="evenodd" d="%s"/></svg>\n') % (size, size, rect, line_css, shield, fill_css, fill)


def recolour(rgba):
    a = rgba[..., 3:4].astype(np.float32) / 255.0
    lum = rgba[..., :3].astype(np.float32).mean(axis=2, keepdims=True) / 255.0
    # 0 on the green fill, 1 on the white line art
    t = np.clip((lum - 0.27) / (1.0 - 0.27), 0.0, 1.0)
    rgb = np.array(FILL, np.float32) * (1 - t) + np.array(LINE, np.float32) * t
    return np.concatenate([rgb, a * 255.0], axis=2).round().astype(np.uint8)


def main():
    src = np.array(Image.open(SRC).convert("RGBA"))
    size = src.shape[0]
    opaque = src[..., 3] >= 128
    green = opaque & (src[..., :3].astype(np.int32).mean(axis=2) < 128)

    shield_d = trace(opaque)
    fill_d = trace(green)
    with open(os.path.join(OUT, "logo.svg"), "w", encoding="utf-8", newline="\n") as f:
        f.write(svg(size, shield_d, fill_d, hexc(LINE), hexc(FILL)))
    # Two-ink version for inline use: colours come from the page (CSS currentColor / --logo-fill)
    with open(os.path.join(OUT, "logo-ink.svg"), "w", encoding="utf-8", newline="\n") as f:
        f.write(svg(size, shield_d, fill_d, "currentColor", "var(--logo-fill,%s)" % hexc(FILL)))
    with open(os.path.join(OUT, "favicon.svg"), "w", encoding="utf-8", newline="\n") as f:
        f.write(svg(size, shield_d, fill_d, hexc(LINE), hexc(FILL)))

    img = Image.fromarray(recolour(src), "RGBA")
    for name, px in PNG_SIZES.items():
        out = img.resize((px, px), Image.LANCZOS)
        if name in ("apple-touch-icon.png", "icon-192.png", "icon-512.png"):
            # Home screen icons need an opaque background and a margin
            canvas = Image.new("RGBA", (px, px), BG + (255,))
            inner = int(px * 0.84)
            logo = img.resize((inner, inner), Image.LANCZOS)
            canvas.alpha_composite(logo, ((px - inner) // 2, (px - inner) // 2))
            out = canvas
        out.save(os.path.join(OUT, name), optimize=True)

    ico = io.BytesIO()
    img.save(ico, format="ICO", sizes=[(16, 16), (32, 32), (48, 48)])
    with open(os.path.join(OUT, "favicon.ico"), "wb") as f:
        f.write(ico.getvalue())
    print("logo: %d + %d path chars, %d PNG, favicon.ico" % (len(shield_d), len(fill_d), len(PNG_SIZES)))


if __name__ == "__main__":
    main()
