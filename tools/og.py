"""Social preview image (Open Graph, 1200x630): a targeting-terminal still over a combat scene.

    python tools/og.py

Needs Pillow and the Windows fonts Bahnschrift and Consolas (close stand-ins for
Oswald and JetBrains Mono). Writes assets/img/og.jpg; the output is committed.
Chat apps show this card at about 400 px wide: every word on it must stay readable there.
"""
import json
import math
import os
import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
W, H = 1200, 630
BG = (6, 8, 10)
AMBER = (255, 176, 0)
GREEN = (70, 240, 140)
RED = (226, 38, 38)
MUTE = (150, 160, 168)
WHITE = (244, 246, 248)
RND = random.Random(1944)


def font(name, size, variation=None):
    f = ImageFont.truetype(os.path.join(FONTS, name), size)
    if variation:
        f.set_variation_by_name(variation)
    return f


def layer():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def over(base, top):
    return Image.alpha_composite(base, top)


def scene():
    """Conflict PvE battle still (helicopters, smoke, impact; its badge left out), in an amber/black duotone."""
    src = Image.open(os.path.join(ROOT, "assets", "img", "mods", "conflict-pve.webp")).convert("RGB")
    src = src.crop((612, 30, 960, 291)).resize((840, 630), Image.LANCZOS)
    canvas = Image.new("RGB", (W, H), BG)
    canvas.paste(src, (W - 840, 0))
    lum = ImageOps.autocontrast(canvas.convert("L"), cutoff=1)
    duo = ImageOps.colorize(lum, black=(4, 6, 8), mid=(96, 60, 14), white=(255, 196, 92), midpoint=150)
    # keep a little of the real fire colour
    duo = Image.blend(duo, canvas, 0.18)
    out = duo.convert("RGBA")
    # darkness: the left half carries the title, the right half the reticle
    shade = Image.new("L", (W, H), 0)
    px = shade.load()
    for x in range(W):
        a = 245 if x < 360 else max(70, int(245 - (x - 360) * 0.42))
        for y in range(H):
            px[x, y] = a
    out = Image.composite(Image.new("RGBA", (W, H), BG + (255,)), out, shade)
    return out


def chroma_text(img, xy, text, f, shift=5):
    """Big title with a red/cyan split, like a feed that is about to break up."""
    for dx, col in ((-shift, (255, 40, 60, 120)), (shift, (40, 220, 255, 110))):
        l = layer()
        ImageDraw.Draw(l).text((xy[0] + dx, xy[1]), text, font=f, fill=col)
        img = over(img, l)
    glow = layer()
    ImageDraw.Draw(glow).text(xy, text, font=f, fill=AMBER + (170,))
    img = over(img, glow.filter(ImageFilter.GaussianBlur(18)))
    l = layer()
    ImageDraw.Draw(l).text(xy, text, font=f, fill=WHITE + (255,))
    # glitch: two thin slices of the title slid sideways
    for y0, h, dx in ((xy[1] + 58, 9, 16), (xy[1] + 118, 5, -11)):
        band = l.crop((0, y0, W, y0 + h))
        l.paste((0, 0, 0, 0), (0, y0, W, y0 + h))
        l.paste(band, (dx, y0), band)
    return over(img, l)


def stamp(text, f):
    """Rubber stamp: red, double frame, worn ink."""
    d0 = ImageDraw.Draw(Image.new("L", (1, 1)))
    tw = int(d0.textlength(text, font=f))
    pad = 26
    s = Image.new("RGBA", (tw + pad * 2, 132), (0, 0, 0, 0))
    d = ImageDraw.Draw(s)
    d.rectangle([3, 3, s.width - 4, s.height - 4], outline=RED + (255,), width=6)
    d.rectangle([14, 14, s.width - 15, s.height - 15], outline=RED + (255,), width=2)
    d.text((pad, 22), text, font=f, fill=RED + (255,))
    wear = Image.new("L", s.size, 255)
    wd = ImageDraw.Draw(wear)
    for _ in range(900):
        x, y = RND.randrange(s.width), RND.randrange(s.height)
        r = RND.choice((1, 1, 2, 3))
        wd.ellipse([x - r, y - r, x + r, y + r], fill=RND.randrange(0, 120))
    alpha = ImageChops.multiply(s.split()[3], wear.filter(ImageFilter.GaussianBlur(0.6)))
    s.putalpha(alpha.point(lambda v: int(v * 0.88)))
    return s.rotate(9, resample=Image.BICUBIC, expand=True)


def reticle(img, cx, cy):
    l = layer()
    d = ImageDraw.Draw(l)
    R = 188
    # outer ring with ticks, broken at the four axes
    for a0 in range(0, 360, 90):
        d.arc([cx - R, cy - R, cx + R, cy + R], a0 + 12, a0 + 78, fill=AMBER + (230,), width=3)
    for deg in range(0, 360, 5):
        a = math.radians(deg)
        n = 16 if deg % 45 == 0 else (9 if deg % 15 == 0 else 4)
        d.line([(cx + (R + 6) * math.cos(a), cy + (R + 6) * math.sin(a)),
                (cx + (R + 6 + n) * math.cos(a), cy + (R + 6 + n) * math.sin(a))], fill=AMBER + (200,), width=2)
    # inner dashed ring
    r2 = 150
    for a0 in range(0, 360, 12):
        d.arc([cx - r2, cy - r2, cx + r2, cy + r2], a0, a0 + 6, fill=GREEN + (150,), width=2)
    # cross hairs with a gap around the emblem
    for (x0, y0, x1, y1) in ((cx - R - 60, cy, cx - 170, cy), (cx + 170, cy, cx + R + 60, cy),
                             (cx, cy - R - 40, cx, cy - 170), (cx, cy + 170, cx, cy + R + 40)):
        d.line([(x0, y0), (x1, y1)], fill=AMBER + (230,), width=3)
    # lock brackets
    b, L = 128, 34
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        x0, y0 = cx + sx * b, cy + sy * b
        d.line([(x0, y0), (x0 - sx * L, y0)], fill=RED + (255,), width=4)
        d.line([(x0, y0), (x0, y0 - sy * L)], fill=RED + (255,), width=4)
    tag = font("consolab.ttf", 22)
    lab = "TGT LOCK"
    lw = d.textlength(lab, font=tag)
    d.rectangle([cx + b - lw - 14, cy - b - 44, cx + b + 4, cy - b - 14], fill=RED + (255,))
    d.text((cx + b - lw - 5, cy - b - 42), lab, font=tag, fill=WHITE + (255,))
    small = font("consolab.ttf", 20)
    d.text((cx + R + 18, cy - 34), "AZ 274", font=small, fill=AMBER + (235,))
    d.text((cx + R + 18, cy + 10), "RNG 1.2K", font=small, fill=AMBER + (235,))
    # sweep wedge
    sw = layer()
    s = ImageDraw.Draw(sw)
    for i in range(50):
        a0 = -128 + i
        s.pieslice([cx - r2, cy - r2, cx + r2, cy + r2], a0, a0 + 1.3, fill=GREEN + (int(i * 1.5),))
    img = over(img, sw)
    glow = l.filter(ImageFilter.GaussianBlur(6))
    return over(over(img, glow), l)


def emblem(img, cx, cy, size):
    logo = Image.open(os.path.join(ROOT, "assets", "img", "logo-1024.png")).convert("RGBA").resize((size, size), Image.LANCZOS)
    x, y = cx - size // 2, cy - size // 2
    plate = layer()
    ImageDraw.Draw(plate).ellipse([cx - 138, cy - 138, cx + 138, cy + 138], fill=(4, 6, 8, 215))
    img = over(img, plate.filter(ImageFilter.GaussianBlur(10)))
    glow = layer()
    glow.paste(Image.new("RGBA", logo.size, AMBER + (255,)), (x, y), logo.split()[3].point(lambda v: 190 if v > 0 else 0))
    img = over(img, glow.filter(ImageFilter.GaussianBlur(26)))
    l = layer()
    l.paste(logo, (x, y), logo)
    return over(img, l)


def main():
    mods = json.load(open(os.path.join(ROOT, "tools", "data", "mods.json"), encoding="utf-8"))["mods"]
    released = sum(1 for m in mods if m["workshop"])

    img = scene()

    # faint tactical grid on the dark side only
    g = layer()
    gd = ImageDraw.Draw(g)
    for x in range(0, W, 48):
        gd.line([(x, 0), (x, H)], fill=AMBER + (10,))
    for y in range(0, H, 48):
        gd.line([(0, y), (W, y)], fill=AMBER + (10,))
    img = over(img, g)

    # track box on the lead helicopter of the background still
    t = layer()
    td = ImageDraw.Draw(t)
    hb, hl = (632, 30, 872, 150), 22
    for (x0, y0, sx, sy) in ((hb[0], hb[1], 1, 1), (hb[2], hb[1], -1, 1), (hb[0], hb[3], 1, -1), (hb[2], hb[3], -1, -1)):
        td.line([(x0, y0), (x0 + sx * hl, y0)], fill=RED + (230,), width=3)
        td.line([(x0, y0), (x0, y0 + sy * hl)], fill=RED + (230,), width=3)
    tf = font("consolab.ttf", 18)
    lab = "TRK 02 // HOSTILE AIR"
    td.rectangle([hb[2] + 8, hb[1], hb[2] + 22 + td.textlength(lab, font=tf), hb[1] + 26], fill=RED + (235,))
    td.text((hb[2] + 15, hb[1] + 3), lab, font=tf, fill=WHITE + (255,))
    img = over(img, t)

    cx, cy = 880, 330
    img = reticle(img, cx, cy)
    img = emblem(img, cx, cy, 236)

    # title block
    tx = 62
    title = font("bahnschrift.ttf", 176, "Bold Condensed")
    img = chroma_text(img, (tx - 6, 118), "INDFORGE", title)
    d = ImageDraw.Draw(img)
    tb = d.textbbox((tx - 6, 118), "INDFORGE", font=title)
    sub = font("consolab.ttf", 34)
    letters = list("ARMA REFORGER")
    widths = [d.textlength(c, font=sub) if c != " " else 0 for c in letters]
    gap = (tb[2] - tb[0] - sum(widths)) / (len(letters) - 1)
    x = tb[0]
    for c, w in zip(letters, widths):
        if c != " ":
            d.text((x, tb[3] + 16), c, font=sub, fill=AMBER)
        x += w + gap
    y = tb[3] + 72
    d.rectangle([tb[0], y, tb[2], y + 3], fill=AMBER)
    d.rectangle([tb[0], y + 9, tb[0] + 120, y + 12], fill=RED)

    big = font("bahnschrift.ttf", 34, "SemiBold Condensed")
    d.text((tb[0], y + 30), "PVE OPS  //  SERVER INTEL  //  ARSENAL", font=big, fill=WHITE)
    mono = font("consolab.ttf", 24)
    # a classified line: the bar is a decoy, nothing is hidden under it
    d.text((tb[0], y + 84), "OPERATION:", font=mono, fill=MUTE)
    ox = int(tb[0] + d.textlength("OPERATION: ", font=mono))
    bar = [ox, y + 84, ox + 250, y + 112]
    d.rectangle(bar, fill=(0, 0, 0))
    for hx in range(bar[0] - 28, bar[2], 14):
        d.line([(max(hx, bar[0]), bar[1] + max(0, bar[0] - hx)), (min(hx + 28, bar[2]), bar[3] - max(0, hx + 28 - bar[2]))],
               fill=(30, 32, 34), width=4)
    d.rectangle(bar, outline=RED, width=2)

    st = stamp("TOP SECRET", font("bahnschrift.ttf", 72, "Bold Condensed"))
    img.alpha_composite(st, (430, 400))

    d = ImageDraw.Draw(img)
    # HUD frame
    m, L = 22, 54
    for (x0, y0, sx, sy) in ((m, m, 1, 1), (W - m, m, -1, 1), (m, H - m, 1, -1), (W - m, H - m, -1, -1)):
        d.line([(x0, y0), (x0 + sx * L, y0)], fill=AMBER, width=5)
        d.line([(x0, y0), (x0, y0 + sy * L)], fill=AMBER, width=5)
    tag = font("consolab.ttf", 22)
    d.ellipse([m + 34, m + 22, m + 50, m + 38], fill=RED)
    d.text((m + 60, m + 17), "REC", font=tag, fill=RED)
    d.text((m + 122, m + 17), "CON-01 // SECURE CHANNEL", font=tag, fill=AMBER)

    foot = font("consolab.ttf", 24)
    d.rectangle([0, H - 74, W, H], fill=(0, 0, 0, 150))
    d.line([(0, H - 74), (W, H - 74)], fill=AMBER, width=2)
    d.ellipse([m + 36, H - 49, m + 52, H - 33], fill=GREEN)
    d.text((m + 64, H - 54), "ONLINE  //  %d MODS  //  7 LANGUAGES" % released, font=foot, fill=GREEN)
    url = "INDFORGE-STUDIO.GITHUB.IO/INDFORGE"
    d.text((W - m - 34 - d.textlength(url, font=foot), H - 54), url, font=foot, fill=WHITE)

    # scanlines, grain, vignette
    fx = layer()
    o = ImageDraw.Draw(fx)
    for yy in range(0, H, 3):
        o.line([(0, yy), (W, yy)], fill=(0, 0, 0, 40))
    img = over(img, fx)
    noise = Image.effect_noise((W, H), 26).point(lambda v: v)
    grain = Image.merge("RGBA", (noise, noise, noise, Image.new("L", (W, H), 16)))
    img = over(img, grain)
    vig = Image.new("L", (W, H), 0)
    v = ImageDraw.Draw(vig)
    for i in range(50):
        v.rectangle([i * 5, i * 3, W - i * 5, H - i * 3], outline=int(170 * (1 - i / 50)))
    vig = vig.filter(ImageFilter.GaussianBlur(36))
    dark = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    dark.putalpha(vig.point(lambda p: int(p * 0.75)))
    img = over(img, dark)

    out = os.path.join(ROOT, "assets", "img", "og.jpg")
    img.convert("RGB").save(out, "JPEG", quality=88, optimize=True, progressive=True)
    print("wrote", out, os.path.getsize(out), "bytes")


if __name__ == "__main__":
    main()
