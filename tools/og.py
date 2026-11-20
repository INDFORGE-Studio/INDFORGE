"""Social preview image (Open Graph, 1200x630) in the site's HUD style.

    python tools/og.py

Needs Pillow and the Windows fonts Bahnschrift and Consolas (close stand-ins for
Oswald and JetBrains Mono). Writes assets/img/og.jpg; the output is committed.
"""
import math
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
W, H = 1200, 630
BG = (6, 8, 10)
AMBER = (255, 176, 0)
GREEN = (70, 240, 140)
MUTE = (138, 148, 158)
WHITE = (240, 244, 246)


def font(name, size, variation=None):
    f = ImageFont.truetype(os.path.join(FONTS, name), size)
    if variation:
        f.set_variation_by_name(variation)
    return f


def rgba(c, a):
    return c + (a,)


def main():
    img = Image.new("RGB", (W, H), BG)

    # grid
    grid = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g = ImageDraw.Draw(grid)
    for x in range(0, W, 40):
        g.line([(x, 0), (x, H)], fill=rgba(AMBER, 14 if x % 200 else 26))
    for y in range(0, H, 40):
        g.line([(0, y), (W, y)], fill=rgba(AMBER, 14 if y % 200 else 26))
    img.paste(grid, (0, 0), grid)

    # radar behind the logo
    cx, cy, R = 300, 315, 250
    radar = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    r = ImageDraw.Draw(radar)
    sweep = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    s = ImageDraw.Draw(sweep)
    for i in range(60):
        a0 = -150 + i
        s.pieslice([cx - R, cy - R, cx + R, cy + R], a0, a0 + 1.2, fill=rgba(GREEN, int(i * 1.3)))
    radar = Image.alpha_composite(radar, sweep)
    r = ImageDraw.Draw(radar)
    lead = math.radians(-90)
    r.line([(cx, cy), (cx + R * math.cos(lead), cy + R * math.sin(lead))], fill=rgba(GREEN, 170), width=2)
    for k in (1, 2, 3, 4):
        rr = R * k / 4
        r.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=rgba(GREEN, 70 if k == 4 else 38), width=2 if k == 4 else 1)
    r.line([(cx - R, cy), (cx + R, cy)], fill=rgba(GREEN, 30))
    r.line([(cx, cy - R), (cx, cy + R)], fill=rgba(GREEN, 30))
    for deg in range(0, 360, 10):
        a = math.radians(deg)
        l = 14 if deg % 30 == 0 else 7
        r.line([(cx + (R - l) * math.cos(a), cy + (R - l) * math.sin(a)), (cx + R * math.cos(a), cy + R * math.sin(a))],
               fill=rgba(GREEN, 90))
    for bx, by in ((cx + 150, cy - 95), (cx - 175, cy + 60), (cx + 60, cy + 180)):
        r.ellipse([bx - 4, by - 4, bx + 4, by + 4], fill=rgba(GREEN, 200))
    img.paste(radar, (0, 0), radar)

    # logo with an amber glow
    logo = Image.open(os.path.join(ROOT, "assets", "img", "logo-1024.png")).convert("RGBA")
    size = 300
    logo = logo.resize((size, size), Image.LANCZOS)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    mask = logo.split()[3].point(lambda v: 150 if v > 0 else 0)
    glow.paste(Image.new("RGBA", logo.size, rgba(AMBER, 255)), (cx - size // 2, cy - size // 2), mask)
    glow = glow.filter(ImageFilter.GaussianBlur(28))
    img.paste(glow, (0, 0), glow)
    img.paste(logo, (cx - size // 2, cy - size // 2), logo)

    d = ImageDraw.Draw(img)

    # title block
    tx = 600
    title = font("bahnschrift.ttf", 132, "Bold Condensed")
    d.text((tx - 4, 168), "INDFORGE", font=title, fill=WHITE)
    tb = d.textbbox((tx - 4, 168), "INDFORGE", font=title)
    tw = tb[2] - tb[0]
    # ARMA REFORGER spread over the exact width of the title
    sub = font("consolab.ttf", 30)
    letters = list("ARMA REFORGER")
    widths = [d.textlength(c, font=sub) if c != " " else 0 for c in letters]
    gap = (tw - sum(widths)) / (len(letters) - 1)
    x = tb[0]
    for c, w in zip(letters, widths):
        if c != " ":
            d.text((x, tb[3] + 18), c, font=sub, fill=AMBER)
        x += w + gap
    y = tb[3] + 78
    d.line([(tb[0], y), (tb[2], y)], fill=rgba(AMBER, 255)[:3], width=2)
    small = font("consola.ttf", 24)
    lines = ["WORKSHOP MODS  //  ADMIN SETTINGS", "COMMANDS  //  DEPENDENCIES"]
    for i, line in enumerate(lines):
        d.text((tb[0], y + 22 + i * 36), line, font=small, fill=MUTE)

    # HUD frame: corner brackets, header and footer strips
    m, L = 26, 46
    for (x0, y0, sx, sy) in ((m, m, 1, 1), (W - m, m, -1, 1), (m, H - m, 1, -1), (W - m, H - m, -1, -1)):
        d.line([(x0, y0), (x0 + sx * L, y0)], fill=AMBER, width=4)
        d.line([(x0, y0), (x0, y0 + sy * L)], fill=AMBER, width=4)
    tag = font("consolab.ttf", 18)
    d.rectangle([m + 30, m + 14, m + 30 + d.textlength("CON-01", font=tag) + 18, m + 42], fill=AMBER)
    d.text((m + 39, m + 17), "CON-01", font=tag, fill=BG)
    d.text((m + 30 + d.textlength("CON-01", font=tag) + 34, m + 17), "INDFORGE - STUDIO  //  SECURE CHANNEL", font=tag, fill=AMBER)
    foot = "INDFORGE-STUDIO.GITHUB.IO/INDFORGE"
    d.text((W - m - 30 - d.textlength(foot, font=tag), H - m - 40), foot, font=tag, fill=MUTE)
    d.ellipse([m + 32, H - m - 35, m + 44, H - m - 23], fill=GREEN)
    d.text((m + 54, H - m - 40), "ONLINE", font=tag, fill=GREEN)

    # scanlines and vignette
    over = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    o = ImageDraw.Draw(over)
    for yy in range(0, H, 3):
        o.line([(0, yy), (W, yy)], fill=(0, 0, 0, 34))
    vig = Image.new("L", (W, H), 0)
    v = ImageDraw.Draw(vig)
    for i in range(60):
        v.rectangle([i * 4, i * 3, W - i * 4, H - i * 3], outline=int(150 * (1 - i / 60)))
    vig = vig.filter(ImageFilter.GaussianBlur(40))
    over.paste((0, 0, 0, 255), (0, 0), vig.point(lambda p: int(p * 0.8)))
    img.paste(over, (0, 0), over)

    out = os.path.join(ROOT, "assets", "img", "og.jpg")
    img.save(out, "JPEG", quality=88, optimize=True, progressive=True)
    print("wrote", out, os.path.getsize(out), "bytes")


if __name__ == "__main__":
    main()
