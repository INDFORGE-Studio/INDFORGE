"""Original INDFORGE emblems for the national optics.

A plain heraldic shield edged in gold: the national flag for the national optics,
a simple symbol for the other optics. Drawn from scratch: no real unit insignia
and no state emblem is reproduced. Output: assets/img/fs/<optic>.svg (run once,
the files are committed).
"""
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "img", "fs")

SHIELD = "M3 3H37V21.5C37 33.5 29.5 40.8 20 45.5C10.5 40.8 3 33.5 3 21.5Z"
TOP, BOT = 3, 45.5


def vbands(*cols):
    w = 40 / len(cols)
    return "".join('<rect x="%.2f" y="0" width="%.2f" height="48" fill="%s"/>' % (i * w, w + .05, c) for i, c in enumerate(cols))


def hbands(parts):
    """parts: [(colour, weight), ...] from top to bottom of the shield."""
    total, y, out = sum(p[1] for p in parts), TOP, []
    for c, wgt in parts:
        h = (BOT - TOP) * wgt / total
        out.append('<rect x="0" y="%.2f" width="40" height="%.2f" fill="%s"/>' % (y, h + .05, c))
        y += h
    return '<rect x="0" y="0" width="40" height="3" fill="%s"/>' % parts[0][0] + "".join(out)


def gbr():
    return ('<rect width="40" height="48" fill="#012169"/>'
            '<path d="M0 0L40 48M40 0L0 48" stroke="#fff" stroke-width="7"/>'
            '<path d="M0 0L40 48M40 0L0 48" stroke="#c8102e" stroke-width="2.2"/>'
            '<path d="M20 0V48M0 22H40" stroke="#fff" stroke-width="9"/>'
            '<path d="M20 0V48M0 22H40" stroke="#c8102e" stroke-width="5"/>')


def star(cx, cy, r):
    pts = []
    for i in range(10):
        rr = r if i % 2 == 0 else r * .382
        a = math.radians(-90 + i * 36)
        pts.append("%.2f,%.2f" % (cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return '<polygon points="%s"/>' % " ".join(pts)


CAN_RED = "#ff0000"  # FIP red, RGB 255-0-0
CAN_LEAF = ("M4890 4430l-45-863a95 95 0 0 1 111-98l859 151-116-320a65 65 0 0 1 20-73l941-762-212-99a65 65 0 0 1-34-79l186-572-542 115a65 65 0 0 1-73-38l-105-247-423 454a65 65 0 0 1-111-57l204-1052-327 189a65 65 0 0 1-91-27l-332-652-332 652a65 65 0 0 1-91 27l-327-189 204 1052a65 65 0 0 1-111 57l-423-454-105 247a65 65 0 0 1-73 38l-542-115 186 572a65 65 0 0 1-34 79l-212 99 941 762a65 65 0 0 1 20 73l-116 320 859-151a95 95 0 0 1 111 98l-45 863z")


def can():
    """Canadian pale: red, white, red in 1:2:1, the official 11-point maple leaf in the white pale."""
    # 1:2:1 measured on the visible inside of the shield (x 4.7 to 35.3, inside the gold edge)
    x0, x1 = 4.7, 35.3
    q = (x1 - x0) / 4
    k = 2 * q / 4800  # the leaf keeps its place in the flag's white square
    return ('<rect width="40" height="48" fill="%s"/><rect x="%.2f" y="0" width="%.2f" height="48" fill="#ffffff"/>' % (CAN_RED, x0 + q, 2 * q)
            + '<path fill="%s" transform="translate(%.3f %.3f) scale(%.6f) translate(-2400 0)" d="%s"/>'
            % (CAN_RED, x0 + q, 23 - q, k, CAN_LEAF))


def usa():
    """13 stripes, canton over 7 of them, 50 stars in 9 rows of 6 and 5 (US flag layout)."""
    h = (BOT - TOP) / 13
    s = ['<rect width="40" height="48" fill="#fff"/>']
    for i in range(13):
        if i % 2 == 0:
            s.append('<rect x="0" y="%.2f" width="40" height="%.2f" fill="#b31942"/>' % (TOP + i * h, h + .05))
    s.append('<rect x="0" y="0" width="40" height="3" fill="#b31942"/>')
    x0, w, y0, ch = 3, 18, TOP, 7 * h
    s.append('<rect x="0" y="0" width="%.2f" height="%.2f" fill="#0a3161"/>' % (x0 + w, y0 + ch))
    n, g = 0, ['<g fill="#fff">']
    for row in range(9):
        for c in (range(1, 12, 2) if row % 2 == 0 else range(2, 11, 2)):
            g.append(star(x0 + w * c / 12, y0 + ch * (row + 1) / 10, .8)); n += 1
    assert n == 50
    s.append("".join(g) + "</g>")
    return "".join(s)


FIELDS = {
    "fra": vbands("#000091", "#ffffff", "#e1000f"),
    "ita": vbands("#009246", "#f4f5f0", "#ce2b37"),
    "deu": hbands([("#000000", 1), ("#dd0000", 1), ("#ffce00", 1)]),
    "esp": hbands([("#aa151b", 1), ("#f1bf00", 2), ("#aa151b", 1)]),
    "pol": hbands([("#f4f4f4", 1), ("#dc143c", 1)]),
    "ukr": hbands([("#0057b7", 1), ("#ffd700", 1)]),
    "gbr": gbr(),
    "can": can(),
    "usa": usa(),
}

def grad(id_, stops, vertical=True):
    xy = 'x1="0" y1="0" x2="0" y2="1"' if vertical else 'x1="0" y1="0" x2="1" y2="0"'
    return '<linearGradient id="%s" %s>%s</linearGradient>' % (id_, xy, "".join('<stop offset="%s" stop-color="%s"/>' % st for st in stops))


def radial(id_, stops):
    return '<radialGradient id="%s">%s</radialGradient>' % (id_, "".join('<stop offset="%s" stop-color="%s" stop-opacity="%s"/>' % st for st in stops))


def snowflake():
    arms = []
    for ang in (0, 60, 120, 180, 240, 300):
        arms.append('<g transform="rotate(%d 20 23)"><path d="M20 23V12.5M20 15.5L17.4 13M20 15.5L22.6 13M20 19L18 17.2M20 19L22 17.2"/></g>' % ang)
    return '<g stroke="#fff" stroke-width="1.5" stroke-linecap="round" fill="none">%s</g>' % "".join(arms)


SYMBOLS = {
    # Arma Reforger: an anvil in the forge glow, sparks flying (to reforge; also our own name, INDFORGE)
    "arma": '<defs>' + radial("fg", [("0", "#ff8a1f", .45), (".6", "#ff8a1f", .08), ("1", "#ff8a1f", 0)])
            + grad("av", [("0", "#ffd36b"), ("1", "#c98400")]) + '</defs>'
            '<rect width="40" height="48" fill="#0d1114"/><ellipse cx="20" cy="25" rx="17" ry="15" fill="url(#fg)"/>'
            '<path d="M5 19.4L12 18.5H31V22.5H26.5C25 24 24 25.5 24 27.2C24 28.8 25.6 30 27.8 30.6V33.6H12.6V30.6C14.8 30 16.4 28.8 16.4 27.2'
            'C16.4 25.5 15.4 24 13.8 22.5H12Z" fill="url(#av)" stroke="#0b0f14" stroke-width=".9" stroke-linejoin="round"/>'
            '<path d="M12.5 19.6H30.2" stroke="#fff1c2" stroke-opacity=".7" stroke-width=".7"/>'
            '<g fill="#ffe08a"><path d="M24 9.5L24.7 12.3L27.5 13L24.7 13.7L24 16.5L23.3 13.7L20.5 13L23.3 12.3Z"/>'
            '<path d="M29.5 7.5L29.9 9.1L31.5 9.5L29.9 9.9L29.5 11.5L29.1 9.9L27.5 9.5L29.1 9.1Z"/>'
            '<path d="M18 8L18.4 9.6L20 10L18.4 10.4L18 12L17.6 10.4L16 10L17.6 9.6Z"/></g>',
    # night vision: phosphor field and a reticle
    "nvg": '<defs>' + radial("nv", [("0", "#2f8a1a", 1), ("1", "#021003", 1)]) + '</defs><rect width="40" height="48" fill="url(#nv)"/>'
           '<g stroke="#b8ff5c" stroke-width="1.3" fill="none"><circle cx="20" cy="23" r="9"/><path d="M20 10V18M20 28V36M7 23H15M25 23H33"/></g>'
           '<circle cx="20" cy="23" r="1.4" fill="#b8ff5c"/>',
    # thermal: ironbow palette and a white-hot core
    "thermal": '<defs>' + grad("ib", [("0", "#12052b"), (".35", "#7a1a8c"), (".62", "#ff3d8b"), (".82", "#ff8a1f"), ("1", "#ffd36b")])
               + radial("hot", [("0", "#ffffff", 1), (".35", "#ffe680", .95), (".7", "#ff8a1f", .5), ("1", "#ff8a1f", 0)]) + '</defs>'
               '<rect width="40" height="48" fill="url(#ib)"/><ellipse cx="20" cy="23" rx="10" ry="12" fill="url(#hot)"/>',
    # arctic: ice field and a snowflake
    "arctic": '<defs>' + grad("ic", [("0", "#0b2a44"), ("1", "#2f9fd6")]) + '</defs><rect width="40" height="48" fill="url(#ic)"/>' + snowflake(),
    # desert: dunes under the sun
    "desert": '<defs>' + grad("sk", [("0", "#f0913a"), ("1", "#f6d39a")]) + '</defs><rect width="40" height="48" fill="url(#sk)"/>'
              '<circle cx="20" cy="17" r="5.5" fill="#fff4cf"/>'
              '<path d="M0 30C8 25 15 26 22 29S34 31 40 27V48H0Z" fill="#c98a45"/>'
              '<path d="M0 37C9 32 17 34 25 37S35 38 40 35V48H0Z" fill="#9a6230"/>',
    # forest: three pines
    "forest": '<defs>' + grad("fo", [("0", "#1f4a1c"), ("1", "#08180a")]) + '</defs><rect width="40" height="48" fill="url(#fo)"/>'
              '<path d="M20 9L27 21H24L29.5 30H23V35H17V30H10.5L16 21H13Z" fill="#93c24f"/>'
              '<path d="M9.5 18L13.5 25H12L15 31H11V34.5H8V31H4L7 25H5.5Z" fill="#5f8a2e"/>'
              '<path d="M30.5 18L34.5 25H33L36 31H32V34.5H29V31H25L28 25H26.5Z" fill="#5f8a2e"/>',
    # red light: a red lens glowing in the dark
    "red": '<defs>' + radial("rl", [("0", "#ffd0c8", 1), (".25", "#ff3b2f", 1), (".75", "#8a0b06", 1), ("1", "#3a0302", 1)]) + '</defs>'
           '<rect width="40" height="48" fill="#120202"/><circle cx="20" cy="23" r="10" fill="url(#rl)"/>'
           '<circle cx="20" cy="23" r="11.5" fill="none" stroke="#ff3b2f" stroke-opacity=".55" stroke-width="1.2"/>',
    # daylight: a sun on paper
    "day": '<rect width="40" height="48" fill="#e9e1c8"/>'
           '<g stroke="#7a4200" stroke-width="1.8" stroke-linecap="round"><path d="M20 9.5V13M20 33V36.5M6.5 23H10M30 23H33.5M10.5 13.5L13 16M27 30L29.5 32.5M10.5 32.5L13 30M27 16L29.5 13.5"/></g>'
           '<circle cx="20" cy="23" r="6.5" fill="#c47a00" stroke="#7a4200" stroke-width="1.2"/>',
}
FIELDS.update(SYMBOLS)


TEMPLATE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 48" width="40" height="48">
<defs>
<clipPath id="c"><path d="{shield}"/></clipPath>
<linearGradient id="l" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".2"/><stop offset=".45" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".32"/></linearGradient>
<linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f3d77a"/><stop offset="1" stop-color="#a8841f"/></linearGradient>
</defs>
<g clip-path="url(#c)">{field}<rect width="40" height="48" fill="url(#l)"/></g>
<path d="{shield}" fill="none" stroke="#0b0f14" stroke-width="3.4" stroke-linejoin="round"/>
<path d="{shield}" fill="none" stroke="url(#g)" stroke-width="1.8" stroke-linejoin="round"/>
</svg>
"""

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for k, field in FIELDS.items():
        with open(os.path.join(OUT, k + ".svg"), "w", encoding="utf-8", newline="\n") as f:
            f.write(TEMPLATE.format(shield=SHIELD, field=field))
    print("wrote %d emblems to %s" % (len(FIELDS), OUT))
