"""Original INDFORGE emblems for the national optics.

A plain heraldic shield in the national colours, edged in gold, with an upright
steel sword. Drawn from scratch: no real unit insignia and no state emblem is
reproduced. Output: assets/img/fs/<nation>.svg (run once, the files are committed).
"""
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


def usa():
    h = (BOT - TOP) / 13
    s = ['<rect width="40" height="48" fill="#fff"/>']
    for i in range(13):
        if i % 2 == 0:
            s.append('<rect x="0" y="%.2f" width="40" height="%.2f" fill="#b31942"/>' % (TOP + i * h, h + .05))
    s.append('<rect x="0" y="0" width="40" height="3" fill="#b31942"/>')
    s.append('<rect x="0" y="0" width="19" height="%.2f" fill="#0a3161"/>' % (TOP + 7 * h))
    for r in range(4):
        for c in range(4):
            s.append('<circle cx="%.1f" cy="%.1f" r=".75" fill="#fff"/>' % (5.2 + c * 3.4 + (1.7 if r % 2 else 0), 5.6 + r * 3.6))
    return "".join(s)


FIELDS = {
    "fra": vbands("#000091", "#ffffff", "#e1000f"),
    "ita": vbands("#009246", "#f4f5f0", "#ce2b37"),
    "deu": hbands([("#000000", 1), ("#dd0000", 1), ("#ffce00", 1)]),
    "esp": hbands([("#aa151b", 1), ("#f1bf00", 2), ("#aa151b", 1)]),
    "pol": hbands([("#f4f4f4", 1), ("#dc143c", 1)]),
    "ukr": hbands([("#0057b7", 1), ("#ffd700", 1)]),
    "gbr": gbr(),
    "usa": usa(),
}

TEMPLATE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 48" width="40" height="48">
<defs>
<clipPath id="c"><path d="{shield}"/></clipPath>
<linearGradient id="l" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".2"/><stop offset=".45" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".32"/></linearGradient>
<linearGradient id="s" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff"/><stop offset=".5" stop-color="#cfd6dd"/><stop offset="1" stop-color="#7f8a95"/></linearGradient>
<linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f3d77a"/><stop offset="1" stop-color="#a8841f"/></linearGradient>
</defs>
<g clip-path="url(#c)">{field}<rect width="40" height="48" fill="url(#l)"/></g>
<path d="{shield}" fill="none" stroke="#0b0f14" stroke-width="3.4" stroke-linejoin="round"/>
<path d="{shield}" fill="none" stroke="url(#g)" stroke-width="1.8" stroke-linejoin="round"/>
<path d="M20 8L21.6 11.2V33H18.4V11.2Z" fill="none" stroke="#000" stroke-opacity=".35" stroke-width="2.6" stroke-linejoin="round"/>
<path d="M20 8L21.6 11.2V33H18.4V11.2Z" fill="url(#s)" stroke="#0b0f14" stroke-width=".9" stroke-linejoin="round"/>
<path d="M20 11.8V32" stroke="#0b0f14" stroke-opacity=".35" stroke-width=".6"/>
<rect x="13" y="32.8" width="14" height="2.7" rx="1.35" fill="url(#g)" stroke="#0b0f14" stroke-width=".8"/>
<rect x="18.9" y="35.5" width="2.2" height="4.9" fill="#3b2b1b" stroke="#0b0f14" stroke-width=".6"/>
<circle cx="20" cy="41.8" r="1.7" fill="url(#g)" stroke="#0b0f14" stroke-width=".7"/>
</svg>
"""

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for k, field in FIELDS.items():
        with open(os.path.join(OUT, k + ".svg"), "w", encoding="utf-8", newline="\n") as f:
            f.write(TEMPLATE.format(shield=SHIELD, field=field))
    print("wrote %d emblems to %s" % (len(FIELDS), OUT))
