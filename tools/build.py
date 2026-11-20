#!/usr/bin/env python3
"""Static site generator for the INDFORGE - Studio Arma Reforger site.

Reads tools/data/*.json and tools/i18n/*.json, writes every page as a real
folder with an index.html, plus assets/i18n/<lang>.json and assets/search.json.
Run from anywhere:  python tools/build.py
The output is committed: GitHub Pages serves it as is, no build step there.
"""
import hashlib
import html
import json
import math
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
BASE = "/INDFORGE/"
SITE = "https://indforge-studio.github.io/INDFORGE/"
WORKSHOP = "https://reforger.armaplatform.com/workshop/"
BASE_GAME = "58D0FB3206B6F859"

ALL_LANGS = [
    ("en", "English"), ("fr", "Français"), ("de", "Deutsch"), ("es", "Español"),
    ("it", "Italiano"), ("pl", "Polski"), ("uk", "Українська"),
]
# Languages offered on the site. The others are paused while the texts still change a lot:
# their files stay in tools/i18n/ and come back once the texts are final and re-translated.
LIVE = ("en", "fr")
LANGS = [x for x in ALL_LANGS if x[0] in LIVE]

# Display modes ("optics"): code, menu tag, then swatch colours (background, accent, secondary).
OPTICS = [
    ("tactical", "AMB", "#06080a", "#ffb000", "#46f08c"),
    ("nvg", "NVG", "#010603", "#a6ff3d", "#3dffb4"),
    ("thermal", "THM", "#07030f", "#ff8a1f", "#ff3d8b"),
    ("arctic", "ARC", "#03070d", "#4cc9ff", "#7dffd8"),
    ("red", "RED", "#070101", "#ff3b2f", "#ff8a5c"),
    ("day", "DAY", "#e9e3d1", "#8f4f00", "#2c6a2c"),
]

CATS = [
    ("indforge", ["conflict-pve", "forest", "ai-framework", "enhanced-compositions"]),
    ("auc", ["auc-factions", "auc-vehicles", "auc-conflict"]),
    ("ctrp", ["cherchetoi-rp-clothing", "cherchetoi-rp-props", "cherchetoi-rp-vehicles"]),
    ("gear", ["lav-25-desert", "modern-fia", "rcd-rhs", "rcd-wcs", "solo-push-pull", "talibanmod-red-side-v2"]),
    ("standby", ["off-road-vehicles", "uaz-452-offroad"]),
]
ORDER = [s for _, slugs in CATS for s in slugs]
CAT_OF = {s: c for c, slugs in CATS for s in slugs}

STATUS = {
    "conflict-pve": ["operational", "dev"],
    "ai-framework": ["restricted"],
    "off-road-vehicles": ["standby"],
    "uaz-452-offroad": ["standby"],
}

# Conflict PvE admin commands. state: "in" = in the Workshop release, "inc" = merged after it.
COMMANDS = [
    ("#setrank <player name> <rank>", "cmd.setrank", "in"),
    ("#aidoctrine status | reload | on | off", "cmd.aidoctrine", "in"),
    ("#aidoctrine mod <name> <factor> [seconds]\n#aidoctrine mod <name> off", "cmd.aidoctrine_mod", "in"),
    ("#enemyhq status", "cmd.enemyhq", "in"),
    ("#enemyhq here [drone] [vehicle]", "cmd.enemyhq_here", "in"),
    ("#enemyhq roadblocks [reset]", "cmd.enemyhq_rb", "inc"),
    ("#enemyhq strike glide | missile | flyby | geran2 | geran4", "cmd.enemyhq_strike", "inc"),
    ("#weather status | next [episode] | hold fog= height= rain= wind= dir= | resume | off | on", "cmd.weather", "inc"),
    ("#nightgear status", "cmd.nightgear", "inc"),
]

# Profile folders of features merged after the current Conflict PvE Workshop release.
CFG_INCOMING = {"INDFORGE_Weather", "INDFORGE_NightGear", "INDFORGE_DroneTeam", "INDFORGE_MavicLight", "INDFORGE_RadioAlerts"}

# Doctrine levels, read from $profile:INDFORGE_AIDoctrine/config.json (Levels block).
DOCTRINE = [
    ("Boot", "intel.lvl.boot", (275, 165, 90), 0),
    ("Grunt", "intel.lvl.grunt", (330, 220, 130), 1),
    ("Operator", "intel.lvl.operator", (440, 275, 165), 2),
    ("Overwatch", "intel.lvl.overwatch", (385, 275, 165), 2),
]
# Drone sight ranges, read from $profile:INDFORGE_DroneSight/config.json.
DRONE_RANGES = [("intel.drone_stand", 300), ("intel.drone_crouch", 180), ("intel.drone_prone", 100)]

H = html.escape


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def flatten(d):
    out = {}
    for k, v in d.items():
        if k.startswith("_"):
            continue
        if isinstance(v, list):
            for i, x in enumerate(v):
                out["%s.%d" % (k, i)] = x
        else:
            out[k] = v
    return out


# ---------------------------------------------------------------- i18n
SRC = {l: load(os.path.join(TOOLS, "i18n", l + ".json")) for l, _ in LANGS}
FLAT = {l: flatten(SRC[l]) for l in SRC}
E = FLAT["en"]
for l, d in FLAT.items():
    miss = set(E) - set(d)
    extra = set(d) - set(E)
    if miss or extra:
        sys.exit("i18n %s: missing %s, extra %s" % (l, sorted(miss)[:8], sorted(extra)[:8]))
_h = hashlib.sha1(json.dumps(FLAT, sort_keys=True, ensure_ascii=False).encode("utf-8"))
for _f in ("assets/css/site.css", "assets/js/site.js", "tools/data/mods.json", "tools/data/configs.json"):
    with open(os.path.join(ROOT, _f), "rb") as _fh:
        _h.update(_fh.read())
VER = _h.hexdigest()[:10]
_hi = hashlib.sha1()
for _f in ("favicon.svg", "favicon.ico", "favicon-32.png", "icon-192.png", "icon-512.png", "apple-touch-icon.png"):
    with open(os.path.join(ROOT, "assets", "img", _f), "rb") as _fh:
        _hi.update(_fh.read())
ICON_VER = _hi.hexdigest()[:8]
with open(os.path.join(ROOT, "assets", "img", "og.jpg"), "rb") as _fh:
    OG_VER = hashlib.sha1(_fh.read()).hexdigest()[:8]


def fmt(s, args):
    for k, v in (args or {}).items():
        s = s.replace("{%s}" % k, str(v))
    return s


def t(key, tag="span", cls="", args=None, attrs=""):
    """Element whose content is the EN text of `key`; the JS swaps it for the chosen language."""
    if key not in E:
        sys.exit("missing EN key: " + key)
    a = ' data-i18n="%s"' % key
    if args:
        a += ' data-i18n-args="%s"' % H(json.dumps(args, ensure_ascii=False))
    if cls:
        a += ' class="%s"' % cls
    if attrs:
        a += " " + attrs
    return "<%s%s>%s</%s>" % (tag, a, fmt(E[key], args), tag)


def tl(key, tag="li", cls=""):
    """All items of a list key."""
    n = len(SRC["en"][key])
    return "".join(t("%s.%d" % (key, i), tag, cls) for i in range(n))


def ta(attr, key):
    """Attribute translated by the JS: returns attr="EN" plus the hook."""
    return '%s="%s" data-i18n-attr="%s=%s"' % (attr, H(E[key]), attr, key)


def redact(n=8, decoy=None):
    """Classified-document bar. The text inside is a decoy, never real data."""
    txt = decoy if decoy else "█" * n
    return '<span class="redact" data-deny="%s" title="%s" data-i18n-attr="data-deny=ui.denied;title=ui.redacted">%s</span>' % (
        H(E["ui.denied"]), H(E["ui.redacted"]), H(txt))


# ---------------------------------------------------------------- data
MODS = {m["slug"]: m for m in load(os.path.join(TOOLS, "data", "mods.json"))["mods"]}
# Unlisted mods: release details and the Workshop ID stay classified (anyone holding the ID
# could add the mod to a server and pull its files). They are dropped here, so the pages
# only ever carry redaction bars, never the real values.
for _m in MODS.values():
    if _m["unlisted"]:
        STATUS.setdefault(_m["slug"], [])
        if "restricted" not in STATUS[_m["slug"]]:
            STATUS[_m["slug"]].append("restricted")
        for _k in ("version", "updated", "created", "game", "size", "changelog"):
            _m[_k] = None
        _m["versions"] = []
        _m["guid"] = None
        _m["scenarioIds"] = []
GENERATED = load(os.path.join(TOOLS, "data", "mods.json"))["generated"]
CONFIGS = load(os.path.join(TOOLS, "data", "configs.json"))
# Site-written help for keys whose config file ships none (written from the mod's code).
_SITE_HELP = load(os.path.join(TOOLS, "data", "configs-site-help.json"))
for _f in CONFIGS:
    for _r in _f["rows"]:
        if not _r.get("help") and not _r.get("group"):
            _r["help"] = _SITE_HELP.get(_f["profile"], {}).get(_r["key"])


# Help texts stay English in the config files themselves; the site shows them translated.
# tools/i18n/cfg/en.json is regenerated from configs.json; the other languages map the same ids.
def cfg_id(s):
    return "c." + hashlib.sha1(s.encode("utf-8")).hexdigest()[:10]


CFG_EN = {}
for _f in CONFIGS:
    for _s in [_f.get("readme")] + [_r.get("help") for _r in _f["rows"]]:
        if _s:
            CFG_EN[cfg_id(_s)] = _s
CFG_DIR = os.path.join(TOOLS, "i18n", "cfg")
os.makedirs(CFG_DIR, exist_ok=True)
with open(os.path.join(CFG_DIR, "en.json"), "w", encoding="utf-8", newline="\n") as _fh:
    json.dump(CFG_EN, _fh, ensure_ascii=False, indent=1)
    _fh.write("\n")
CFG_TR = {"en": CFG_EN}
for _l, _ in LANGS[1:]:
    _p = os.path.join(CFG_DIR, _l + ".json")
    _d = load(_p) if os.path.exists(_p) else {}
    _miss = [k for k in CFG_EN if not _d.get(k)]
    if _miss and "--draft" not in sys.argv:
        sys.exit("cfg i18n %s: %d help texts missing (e.g. %s)" % (_l, len(_miss), _miss[:3]))
    _extra = set(_d) - set(CFG_EN)
    if _extra:
        print("cfg i18n %s: %d stale entries ignored" % (_l, len(_extra)))
    CFG_TR[_l] = {k: _d.get(k) or CFG_EN[k] for k in CFG_EN}
CFG_VER = hashlib.sha1(json.dumps(CFG_TR, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:10]
_FLOAT = re.compile(r"-?\d+\.\d{7,}")


def tidy_float(m):
    """Shortest decimal that reads back as the same 32-bit float (0.699999988079071 -> 0.7)."""
    v = m.group()
    x = float(v)
    f32 = struct.unpack("f", struct.pack("f", x))[0]
    if f32 != x:
        return v
    for p in range(1, 10):
        out = "%.*g" % (p, x)
        if struct.unpack("f", struct.pack("f", float(out)))[0] == f32:
            return out if ("." in out or "e" in out) else out + ".0"
    return v


def cfg_text(s):
    return '<span data-i18n="%s">%s</span>' % (cfg_id(s), H(s))
assert sorted(MODS) == sorted(ORDER), "slug list mismatch"
OUR_IDS = {m["guid"] for m in MODS.values() if m["guid"]}
LATEST_GAME = max((m["game"] for m in MODS.values() if m["game"]), key=lambda v: [int(x) for x in v.split(".")])
CPVE_VER = MODS["conflict-pve"]["version"]
THIRD_PARTY = {d["id"] for m in MODS.values() for d in m["deps"]} - OUR_IDS - {BASE_GAME}
CFG_KEYS = sum(len(f["rows"]) for f in CONFIGS)


def name(m):
    return m["name"] or m["title"]


def url(path=""):
    return BASE + path


def ext(href, text, cls=""):
    c = ' class="%s"' % cls if cls else ""
    return '<a%s href="%s" target="_blank" rel="noopener noreferrer">%s</a>' % (c, H(href), text)


def size(b):
    if not b:
        return None
    if b >= 1e9:
        return "%.2f GB" % (b / 1e9)
    if b >= 1e6:
        return "%.1f MB" % (b / 1e6)
    return "%d kB" % round(b / 1e3)


def cfg_anchor(profile):
    folder = profile.split(":", 1)[1].split("/")[0]
    return "cfg-" + re.sub(r"[^a-z0-9]+", "-", folder.lower()).strip("-")


def cfg_folder(profile):
    return profile.split(":", 1)[1].split("/")[0]


def chips(slug):
    out = []
    for s in STATUS.get(slug, ["operational"]):
        out.append(t("status." + s, "span", "chip chip-" + s))
    return "".join(out)


def copy_btn(target=None, text=None, small=False):
    if target:
        a = 'data-copy="%s"' % target
    else:
        a = 'data-copy-text="%s"' % H(text)
    cls = "copy copy-sm" if small else "copy"
    return '<button type="button" class="%s" %s><span class="copy-ico" aria-hidden="true"></span>%s</button>' % (cls, a, t("ui.copy", "span", "copy-lbl"))


def icon(name):
    paths = {
        "search": '<circle cx="11" cy="11" r="6.5"/><path d="M16 16l5 5"/>',
        "menu": '<path d="M3 6h18M3 12h18M3 18h12"/>',
        "ext": '<path d="M14 4h6v6M20 4l-9 9M18 14v6H4V6h6"/>',
        "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
        "back": '<path d="M19 12H5M11 6l-6 6 6 6"/>',
        "nvg": '<path d="M9 7.5V6a3 3 0 0 1 6 0v1.5"/><path d="M12 3v0"/><rect x="2.5" y="8" width="8" height="11" rx="2.5"/>'
               '<rect x="13.5" y="8" width="8" height="11" rx="2.5"/><path d="M10.5 12h3"/>'
               '<circle class="lens" cx="6.5" cy="15" r="2.2"/><circle class="lens" cx="17.5" cy="15" r="2.2"/>',
        "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3.5 3 14.5 0 18M12 3c-3 3.5-3 14.5 0 18"/>',
        "cfg": '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
    }
    return '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true" focusable="false">%s</svg>' % paths[name]


# ---------------------------------------------------------------- shell
NAV = [
    ("", "nav.home", "home"), ("workshop/", "nav.mods", "mods"), ("admins/", "nav.admins", "admins"),
    ("intel/", "nav.intel", "intel"), ("changelog/", "nav.log", "log"), ("status/", "nav.status", "status"),
    ("about/", "nav.about", "about"),
]

HEAD_JS = (
    "(function(d){var h=d.documentElement,L=%s,O=%s,l='';h.className+=' js';"
    "try{l=localStorage.getItem('ifg-lang')||''}catch(e){}"
    "if(L.indexOf(l)<0){l='en';var n=navigator.languages||[navigator.language||'en'];"
    "for(var i=0;i<n.length;i++){var c=String(n[i]).slice(0,2).toLowerCase();if(L.indexOf(c)>=0){l=c;break}}}"
    "h.setAttribute('data-lang',l);try{var o=localStorage.getItem('ifg-optic');if(O.indexOf(o)>0)h.setAttribute('data-theme',o)}catch(e){}"
    "if(l!=='en'){h.className+=' i18n-wait';"
    "setTimeout(function(){h.classList.remove('i18n-wait')},1500)}})(document);"
) % (json.dumps([l for l, _ in LANGS]), json.dumps([o[0] for o in OPTICS]))

SPEC = json.dumps({"prerender": [{"where": {"href_matches": BASE + "*"}, "eagerness": "moderate"}]})


# Image filters for the optics: luminance mapped onto each palette (night vision, ironbow...).
def _fx(fid, r, g, b):
    return ('<filter id="%s" color-interpolation-filters="sRGB"><feColorMatrix type="matrix" '
            'values=".3 .59 .11 0 0 .3 .59 .11 0 0 .3 .59 .11 0 0 0 0 0 1 0"/><feComponentTransfer>'
            '<feFuncR type="table" tableValues="%s"/><feFuncG type="table" tableValues="%s"/>'
            '<feFuncB type="table" tableValues="%s"/></feComponentTransfer></filter>') % (fid, r, g, b)


FX_DEFS = '<svg class="fx-defs" aria-hidden="true" focusable="false">%s</svg>' % "".join([
    _fx("fx-nvg", "0 .04 .3 .7", "0 .42 .88 1", "0 .07 .28 .6"),
    _fx("fx-thermal", "0 .22 .68 .95 1 1", "0 0 .05 .38 .78 1", ".1 .45 .55 .15 .05 .85"),
    _fx("fx-red", "0 .42 .88 1", "0 .02 .14 .5", "0 .02 .1 .42"),
    _fx("fx-arctic", "0 .08 .5 .85", "0 .22 .72 .95", ".03 .38 .9 1"),
])


def header(active):
    links = []
    for i, (p, key, pid) in enumerate(NAV):
        cur = ' aria-current="page"' if pid == active else ""
        hot = ' class="nav-hot"' if pid == "mods" else ""
        links.append('<a href="%s"%s%s><span class="nav-n" aria-hidden="true">%02d</span>%s</a>' % (url(p), hot, cur, i + 1, t(key)))
    langs = "".join(
        '<li role="none"><button type="button" role="menuitemradio" aria-checked="false" data-lang="%s" lang="%s"><b>%s</b><span>%s</span></button></li>'
        % (l, l, l.upper(), H(n)) for l, n in LANGS)
    wip = [(l, n) for l, n in ALL_LANGS if l not in LIVE]
    if wip:
        # Paused languages: listed, but classified until their translation is back.
        langs += '<li role="separator" class="lang-sep"></li>' + "".join(
            '<li role="none"><span class="lang-wip" role="menuitem" aria-disabled="true"><b>%s</b>%s<em>W.I.P</em></span></li>'
            % (l.upper(), redact(len(n))) for l, n in wip)
    optics = "".join(
        '<li role="none"><button type="button" role="menuitemradio" aria-checked="false" data-optic="%s">'
        '<i class="opt-sw" style="--c:%s;--a:%s;--b:%s" aria-hidden="true"></i><b class="opt-k">%s</b>%s</button></li>'
        % (o, c, a, b, k, t("optic." + o)) for o, k, c, a, b in OPTICS)
    return """<a class="skip" href="#main" data-i18n="nav.skip">%s</a>
%s
<header class="hud" id="top">
  <div class="hud-bar">
    <a class="brand" href="%s" aria-label="INDFORGE - Studio">
      <img class="brand-mark" src="%s" width="36" height="36" alt="">
      <span class="brand-txt"><b>INDFORGE</b><small aria-hidden="true">%s</small></span>
    </a>
    <nav class="nav" id="nav" %s>%s</nav>
    <div class="hud-tools">
      <span class="clock" aria-hidden="true"><span class="clock-l">ZULU</span><time id="zulu">--:--:--Z</time></span>
      <span class="sig" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></span>
      <button type="button" class="tool search-btn" data-search %s>%s<kbd>/</kbd></button>
      <div class="lang">
        <button type="button" class="tool lang-btn" aria-haspopup="menu" aria-expanded="false" aria-controls="lang-menu" %s>%s<span class="lang-cur">EN</span></button>
        <ul class="lang-menu" id="lang-menu" role="menu" hidden>%s</ul>
      </div>
      <div class="lang opt">
        <button type="button" class="tool opt-btn" aria-haspopup="menu" aria-expanded="false" aria-controls="opt-menu" %s>%s<span class="opt-cur">AMB</span></button>
        <ul class="lang-menu opt-menu" id="opt-menu" role="menu" hidden><li role="presentation" class="opt-h">%s</li>%s</ul>
      </div>
      <button type="button" class="tool menu-btn" aria-expanded="false" aria-controls="nav" %s>%s</button>
    </div>
  </div>
  <div class="hud-line" aria-hidden="true"></div>
</header>""" % (H(E["nav.skip"]), FX_DEFS, url(), BASE + "assets/img/logo.svg", "".join("<i>%s</i>" % H(c) if c != " " else "<i></i>" for c in E["site.division"].upper()), ta("aria-label", "nav.menu"), "".join(links),
                 ta("aria-label", "nav.search"), icon("search"), ta("aria-label", "nav.lang"), icon("globe"), langs,
                 ta("aria-label", "nav.optic"), icon("nvg"), t("optic.h"), optics,
                 ta("aria-label", "nav.menu"), icon("menu"))


def footer():
    links = "".join('<a href="%s">%s</a>' % (url(p), t(k)) for p, k, _ in NAV)
    return """<footer class="foot">
  <div class="wrap foot-in">
    <div class="foot-brand">
      <p class="foot-name">INDFORGE - Studio <span class="dim">//</span> %s</p>
      %s
    </div>
    <nav class="foot-nav" aria-label="Footer">%s</nav>
    %s
    %s
    <p class="foot-sys mono" aria-hidden="true">SYS.%s // CH-%s // <span class="blink">&#9632;</span> %s</p>
  </div>
</footer>""" % (t("site.division"), t("about.motto", "p", "motto"), links, t("ui.footer_legal", "p", "legal"),
                 t("ui.footer_source", "p", "src", {"date": GENERATED}), VER[:6].upper(), len(MODS), H(E["ui.secure"].upper()))


def page(path, title_key, body, active, desc=None, title_raw=None, image=None, cls="", cfg_i18n=False):
    if title_raw:
        title = '<title>%s · INDFORGE - Studio</title>' % H(title_raw)
        og_title = title_raw
    elif title_key == "home.title":
        title = "<title>INDFORGE - Studio · Arma Reforger</title>"
        og_title = "INDFORGE - Studio · Arma Reforger"
    else:
        title = '<title data-i18n="%s" data-i18n-suffix=" · INDFORGE - Studio">%s · INDFORGE - Studio</title>' % (title_key, H(E[title_key]))
        og_title = E[title_key] + " · INDFORGE - Studio"
    desc = desc or E["site.desc"]
    if image:
        img, img_meta = SITE + image, ""
    else:
        img = SITE + "assets/img/og.jpg?v=" + OG_VER
        img_meta = '\n<meta property="og:image:width" content="1200">\n<meta property="og:image:height" content="630">'
    doc = """<!doctype html>
<html lang="en" data-v="%(ver)s"%(cfgv)s data-base="%(base)s" data-page="%(active)s">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
%(title)s
<meta name="description" content="%(desc)s">
<link rel="canonical" href="%(canon)s">
<meta property="og:type" content="website">
<meta property="og:site_name" content="INDFORGE - Studio">
<meta property="og:title" content="%(ogt)s">
<meta property="og:description" content="%(desc)s">
<meta property="og:url" content="%(canon)s">
<meta property="og:image" content="%(img)s">%(imgmeta)s
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="%(img)s">
<meta name="theme-color" content="#06080a">
<meta name="color-scheme" content="dark">
<link rel="icon" href="%(base)sassets/img/favicon.ico?v=%(iv)s" sizes="48x48">
<link rel="icon" href="%(base)sassets/img/favicon.svg?v=%(iv)s" type="image/svg+xml">
<link rel="icon" href="%(base)sassets/img/favicon-32.png?v=%(iv)s" sizes="32x32" type="image/png">
<link rel="icon" href="%(base)sassets/img/icon-192.png?v=%(iv)s" sizes="192x192" type="image/png">
<link rel="apple-touch-icon" href="%(base)sassets/img/apple-touch-icon.png?v=%(iv)s" sizes="180x180">
<link rel="manifest" href="%(base)smanifest.webmanifest?v=%(iv)s">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&amp;family=JetBrains+Mono:wght@400;600&amp;family=Oswald:wght@500;600;700&amp;display=swap">
<link rel="stylesheet" href="%(base)sassets/css/site.css?v=%(ver)s">
<script>%(headjs)s</script>
<script src="%(base)sassets/js/site.js?v=%(ver)s" defer></script>
<script type="speculationrules">%(spec)s</script>
</head>
<body class="%(cls)s">
%(header)s
<main id="main" class="main" tabindex="-1">
%(body)s
</main>
%(footer)s
</body>
</html>
""" % {"ver": VER, "cfgv": (' data-i18n-cfg="%s"' % CFG_VER) if cfg_i18n else "", "iv": ICON_VER, "base": BASE, "active": active, "title": title, "desc": H(desc), "canon": SITE + path,
       "ogt": H(og_title), "img": img, "imgmeta": img_meta, "headjs": HEAD_JS, "spec": SPEC, "cls": cls,
       "header": header(active), "body": body, "footer": footer()}
    out = os.path.join(ROOT, path, "index.html") if not path.endswith(".html") else os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(doc)
    PAGES.append(path)


PAGES = []


def phead(code, kicker, h1, lead=None, lead_args=None, extra=""):
    return """<section class="phead wrap">
  <p class="kicker"><span class="kicker-code">%s</span>%s</p>
  %s
  %s
  %s
</section>""" % (H(code), t(kicker), t(h1, "h1", "", None, 'data-scramble'),
                 t(lead, "p", "lead", lead_args) if lead else "", extra)


def sec(id_, title_key, body, code="", cls="", note=""):
    return """<section class="sec %s" id="%s" aria-labelledby="h-%s">
  <h2 id="h-%s"><span class="sec-code" aria-hidden="true">%s</span>%s</h2>%s
  %s
</section>""" % (cls, id_, id_, id_, H(code), t(title_key), note, body)


def badge_inc():
    return t("ui.incoming", "span", "chip chip-inc")


# ---------------------------------------------------------------- components
def card(slug, lazy=True):
    m = MODS[slug]
    ver = H("v" + m["version"]) if m["version"] else redact(5)
    return """<a class="card" href="%s" data-cat="%s">
  <span class="card-img"><img src="%sassets/img/thumbs/%s.webp" width="480" height="270" alt=""%s decoding="async"><span class="card-scan" aria-hidden="true"></span></span>
  <span class="card-body">
    <span class="card-meta">%s<span class="mono dim">%s</span></span>
    <span class="card-title">%s</span>
    %s
    <span class="card-id mono" aria-hidden="true">ID %s</span>
  </span>
</a>""" % (url("workshop/%s/" % slug), CAT_OF[slug], BASE, slug, ' loading="lazy"' if lazy else "", chips(slug), ver,
           H(name(m)), t("m.%s.tag" % slug, "span", "card-tag"), m["guid"] or redact(16))


def orbat(lazy=True):
    out = []
    for i, (cat, slugs) in enumerate(CATS):
        out.append("""<div class="orbat-group" data-group="%s">
  <div class="orbat-head"><h3><span class="mono dim">%s</span> %s</h3>%s<span class="mono dim orbat-n">%s</span></div>
  <div class="cards">%s</div>
</div>""" % (cat, "%d/" % (i + 1), t("cat." + cat), t("cat.%s.d" % cat, "p", "dim"),
             t("ui.mods_count", "span", "", {"n": len(slugs)}), "".join(card(s, lazy) for s in slugs)))
    return "".join(out)


def cmd_table(rows=COMMANDS, with_mod=False):
    trs = []
    for cmd, key, state in rows:
        st = t("ui.in_service", "span", "chip chip-operational") if state == "in" else badge_inc()
        code = "<br>".join("<code>%s</code>" % H(c) for c in cmd.split("\n"))
        trs.append("<tr data-state=\"%s\"><td class=\"cmd\">%s</td><td>%s</td>%s<td>%s</td></tr>" % (
            state, code, t(key), "<td>INDFORGE - Conflict PvE</td>" if with_mod else "", st))
    return """<div class="tbl"><table class="table cmds">
<thead><tr><th scope="col">%s</th><th scope="col">%s</th>%s<th scope="col">%s</th></tr></thead>
<tbody>%s</tbody></table></div>""" % (t("admins.col_cmd"), t("admins.col_what"),
                                       '<th scope="col">%s</th>' % t("admins.col_mod") if with_mod else "",
                                       t("admins.col_state"), "".join(trs))


def dep_lists(m):
    entries = [{"id": m["guid"], "name": name(m)}] + [{"id": d["id"], "name": d["name"]} for d in m["deps"]]
    js = '"mods": [\n' + ",\n".join(
        '  { "modId": %s, "name": %s }' % (json.dumps(e["id"]), json.dumps(e["name"], ensure_ascii=False)) for e in entries) + "\n]"
    plain = "\n".join("%s - %s" % (e["name"], e["id"]) for e in entries)
    return entries, js, plain


def deps_section(m):
    slug = m["slug"]
    if not m["workshop"] or not m["guid"]:
        body = """<p>%s</p><div class="classified-box"><p class="mono">"mods": [ %s ]</p><p>%s</p></div>""" % (
            t("deps.unreleased" if not m["workshop"] else "deps.unlisted"), redact(28), redact(0, "████████████████ - ████████████████"))
        return sec("deps", "sec.deps", body, "05")
    entries, js, plain = dep_lists(m)
    intro = t("deps.intro", "p")
    if m["deps"]:
        intro += t("deps.direct", "p", "dim", {"n": len(m["direct"]), "m": len(m["deps"])})
    else:
        intro += t("deps.none", "p", "dim")
    rows = "".join(
        "<tr><td>%d</td><td>%s</td><td><code>%s</code></td><td>%s</td></tr>" % (
            i + 1, ext(WORKSHOP + d["id"], H(d["name"])), d["id"], H(d.get("author") or "—"))
        for i, d in enumerate(m["deps"]))
    table = ""
    if m["deps"]:
        table = """<details class="deps-table">
  <summary>%s <span class="mono dim">(%d)</span></summary>
  <div class="tbl"><table class="table">
  <thead><tr><th scope="col">#</th><th scope="col">%s</th><th scope="col">%s</th><th scope="col">%s</th></tr></thead>
  <tbody>%s</tbody></table></div>
</details>""" % (t("deps.table"), len(m["deps"]), t("deps.col_name"), t("deps.col_id"), t("deps.col_author"), rows)
    body = """%s
<div class="code-grid">
  <figure class="codebox">
    <figcaption><span>%s</span><span class="mono dim">%d</span>%s</figcaption>
    <pre class="code" id="deps-json-%s" tabindex="0"><code>%s</code></pre>
  </figure>
  <figure class="codebox">
    <figcaption><span>%s</span><span class="mono dim">%d</span>%s</figcaption>
    <pre class="code" id="deps-plain-%s" tabindex="0"><code>%s</code></pre>
  </figure>
</div>
%s""" % (intro, t("deps.server_json"), len(entries), copy_btn("#deps-json-" + slug), slug, H(js),
         t("deps.plain"), len(entries), copy_btn("#deps-plain-" + slug), slug, H(plain), table)
    return sec("deps", "sec.deps", body, "05")


def facts(m):
    slug = m["slug"]
    def row(key, val, raw=False):
        v = val if raw else (H(val) if val else None)
        return "<div><dt>%s</dt><dd>%s</dd></div>" % (t(key), v if v else redact(10))
    rows = [
        row("ui.workshop_id", m["guid"] and '<code>%s</code>%s' % (m["guid"], copy_btn(text=m["guid"], small=True)), True),
        row("ui.version", m["version"] and "v" + m["version"]),
        row("ui.updated", m["updated"]),
        row("ui.created", m["created"]),
        row("ui.game", m["game"]),
        row("ui.size", size(m["size"])),
        row("ui.license", m["license"]),
        row("ui.author", m["author"]),
    ]
    if m["contributors"]:
        rows.append(row("ui.contributors", ", ".join(m["contributors"])))
    for sid in m["scenarioIds"]:
        rows.append(row("ui.scenario", '<code class="wrapcode">%s</code>%s' % (H(sid), copy_btn(text=sid, small=True)), True))
    if m["tags"]:
        rows.append(row("ui.tags", " ".join('<span class="tag">%s</span>' % H(x) for x in m["tags"]), True))
    return '<dl class="facts">%s</dl>' % "".join(rows)


def cfg_links(slugs):
    files = [f for f in CONFIGS if f["mod"] in slugs]
    if not files:
        return ""
    lis = "".join('<li><a href="%sadmins/#%s"><code>%s</code></a>%s</li>' % (
        BASE, cfg_anchor(f["profile"]), H(f["profile"]), " " + badge_inc() if cfg_folder(f["profile"]) in CFG_INCOMING else "")
        for f in files)
    return '<ul class="filelist">%s</ul><p><a class="btn btn-ghost" href="%sadmins/#cfg">%s%s</a></p>' % (lis, BASE, icon("cfg"), t("ui.see_cfg"))


def mod_page(slug):
    m = MODS[slug]
    i = ORDER.index(slug)
    prev, nxt = MODS[ORDER[i - 1]], MODS[ORDER[(i + 1) % len(ORDER)]]
    cat = CAT_OF[slug]
    k = "m.%s." % slug
    has = lambda s: (k + s) in SRC["en"]
    ws_btn = ""
    if m["workshop"] and m["guid"]:
        ws_btn = ext(WORKSHOP + m["guid"], icon("ext") + t("ui.open_workshop"), "btn btn-primary")
    hero = """<section class="mhero wrap">
  <nav class="crumbs mono" aria-label="Breadcrumb"><a href="%s">%s</a><span aria-hidden="true">/</span><a href="%sworkshop/">%s</a><span aria-hidden="true">/</span>%s</nav>
  <div class="mhero-grid">
    <div class="mhero-txt">
      <p class="kicker"><span class="kicker-code">MOD-%02d</span>%s</p>
      <h1 data-scramble>%s</h1>
      %s
      <p class="chips">%s<span class="mono dim">%s</span></p>
      <div class="actions">%s<a class="btn btn-ghost" href="#deps">%s</a></div>
    </div>
    <figure class="hero-img">
      <img src="%sassets/img/mods/%s.webp" width="960" height="%d" alt="%s" fetchpriority="high" decoding="async">
      <span class="hud-frame" aria-hidden="true"><i></i><i></i><i></i><i></i></span>
      <figcaption class="mono" aria-hidden="true">IMG // %s // %s</figcaption>
    </figure>
  </div>
</section>""" % (url(), t("nav.home"), BASE, t("nav.mods"), t("cat." + cat), i + 1, t("cat." + cat), H(name(m)),
                 t(k + "tag", "p", "lead"), chips(slug), H("v" + m["version"]) if m["version"] else "",
                 ws_btn, t("sec.deps"), BASE, slug, 540, H(name(m)),
                 slug.upper(), m["guid"] or "████████████████")

    parts = []
    ov = tl(k + "intro", "p")
    parts.append(sec("overview", "sec.overview", '<div class="prose">%s</div>' % ov, "01"))
    parts.append(sec("features", "sec.features", '<ul class="feat">%s</ul>' % tl(k + "f"), "02"))
    if has("inc"):
        parts.append(sec("incoming", "sec.incoming", '<ul class="feat feat-inc">%s</ul>' % tl(k + "inc"), "02B", "sec-inc",
                         t("sec.incoming.d", "p", "dim", {"v": m["version"]})))
    if has("setup"):
        parts.append(sec("setup", "sec.setup", '<ol class="steps">%s</ol>' % tl(k + "setup"), "03"))
    if has("admin"):
        own = {"forest": ["conflict-pve"]}.get(slug, [slug])
        body = '<ul class="feat">%s</ul>%s' % (tl(k + "admin"), cfg_links(own))
        parts.append(sec("admin", "sec.admin", body, "04"))
    if slug == "conflict-pve":
        parts.append(sec("commands", "sec.commands", t("admins.cmds_p", "p") + cmd_table(), "04B"))
    elif slug == "forest":
        parts.append(sec("commands", "sec.commands", t("admins.cmds_p", "p") + cmd_table(), "04B"))
    parts.append(deps_section(m))
    if m["changelog"]:
        parts.append(sec("changelog", "sec.changelog",
                         '%s<blockquote class="quote-log" lang="en"><p class="mono dim">v%s // %s</p><div class="log-txt">%s</div></blockquote>' % (
                             t("log.workshop_note", "p", "dim"), H(m["version"]), H(m["updated"]), H(m["changelog"].strip())), "06"))
    if m["versions"]:
        lis = "".join('<li><span class="mono">v%s</span><span class="dim mono">%s</span>%s</li>' % (
            H(v), H(d), t("ui.current", "span", "chip chip-cur") if j == 0 else "") for j, (v, d) in enumerate(m["versions"]))
        parts.append(sec("versions", "sec.versions", '<ol class="vlist">%s</ol><p><a href="%schangelog/">%s</a></p>' % (lis, BASE, t("logp.h1")), "07"))
    if has("credits"):
        parts.append(sec("credits", "sec.credits", t(k + "credits", "p"), "08"))

    toc = "".join('<a href="#%s">%s</a>' % (a, t(kk)) for a, kk in [
        ("overview", "sec.overview"), ("features", "sec.features")] + ([("incoming", "sec.incoming")] if has("inc") else [])
        + ([("setup", "sec.setup")] if has("setup") else []) + ([("admin", "sec.admin")] if has("admin") else [])
        + ([("commands", "sec.commands")] if slug in ("conflict-pve", "forest") else [])
        + [("deps", "sec.deps")] + ([("changelog", "sec.changelog")] if m["changelog"] else [])
        + ([("versions", "sec.versions")] if m["versions"] else []))
    side = """<aside class="mside">
  <div class="panel">
    <h2 class="panel-h">%s</h2>
    %s
  </div>
  <nav class="panel toc" aria-label="Sections"><h2 class="panel-h">%s</h2>%s</nav>
</aside>""" % (t("sec.facts"), facts(m), t("admins.toc"), toc)
    pn = """<nav class="pn wrap" aria-label="Mods">
  <a class="pn-a" href="%s" rel="prev">%s<span><small>%s</small>%s</span></a>
  <a class="pn-a pn-next" href="%s" rel="next"><span><small>%s</small>%s</span>%s</a>
</nav>""" % (url("workshop/%s/" % prev["slug"]), icon("back"), t("ui.prev"), H(name(prev)),
             url("workshop/%s/" % nxt["slug"]), t("ui.next"), H(name(nxt)), icon("arrow"))
    body = hero + '<div class="mbody wrap">%s<div class="mmain">%s</div></div>' % (side, "".join(parts)) + pn
    page("workshop/%s/" % slug, None, body, "mods", desc=fmt(E[k + "tag"], {}), title_raw=name(m),
         image="assets/img/mods/%s.webp" % slug)


# ---------------------------------------------------------------- pages
def latest_updates(n):
    ups = [(m["updated"], s) for s, m in MODS.items() if m["updated"]]
    ups.sort(reverse=True)
    return ups[:n]


def home():
    radar_blips = []
    for j, s in enumerate(ORDER):
        hsh = int(hashlib.md5(s.encode()).hexdigest(), 16)
        ang = hsh % 360
        r = 9 + (hsh >> 9) % 34
        x = 50 + r * math.cos(math.radians(ang - 90))
        y = 50 + r * math.sin(math.radians(ang - 90))
        radar_blips.append('<i style="left:%.1f%%;top:%.1f%%;--d:%dms" class="blip%s"></i>' % (x, y, ang * 4000 // 360, " blip-hot" if s == "conflict-pve" else ""))
    radar = """<div class="radar" aria-hidden="true">
  <div class="radar-ring"></div><div class="radar-ring r2"></div><div class="radar-ring r3"></div>
  <div class="radar-cross"></div><div class="radar-sweep"></div>%s
  <span class="radar-l mono">AO EVERON // %d CONTACTS</span>
</div>""" % ("".join(radar_blips), len(MODS))
    ticker_items = "".join('<li><span class="mono amber">%s</span> %s <span class="mono">v%s</span></li>' % (
        d, H(name(MODS[s])), H(MODS[s]["version"])) for d, s in latest_updates(10))
    stats = [
        (len(MODS), "home.stat_mods"), (len(THIRD_PARTY), "home.stat_deps"),
        (CFG_KEYS, "home.stat_keys"), (len(COMMANDS), "home.stat_cmds"),
    ]
    stat_html = "".join('<div class="stat"><b class="mono" data-count="%d">%d</b>%s</div>' % (n, n, t(k)) for n, k in stats)
    latest = "".join("""<li><a href="%s"><span class="mono amber">%s</span><span class="lt-name">%s</span><span class="mono dim">v%s</span></a></li>""" % (
        url("workshop/%s/" % s), d, H(name(MODS[s])), H(MODS[s]["version"])) for d, s in latest_updates(6))
    body = """<section class="hero wrap">
  <div class="hero-txt">
    <p class="kicker"><span class="kicker-code">STN-01</span>%s</p>
    <h1 class="hero-h1" data-scramble>INDFORGE<span> - Studio</span></h1>
    %s
    <div class="actions">
      <a class="btn btn-primary" href="%sworkshop/">%s%s</a>
      <a class="btn btn-ghost" href="%sadmins/">%s</a>
      <a class="btn btn-ghost" href="%sabout/">%s</a>
    </div>
    <p class="hint mono">%s</p>
  </div>
  %s
</section>
<section class="feed" aria-label="Feed">
  <div class="feed-in"><span class="feed-l mono">%s</span><div class="feed-track"><ul>%s</ul><ul aria-hidden="true">%s</ul></div></div>
</section>
<section class="wrap stats" aria-label="Stats">%s</section>
<section class="wrap featured">
  <div class="dossier-card">
    %s
    <p class="kicker"><span class="kicker-code">INTSUM</span>%s</p>
    %s
    %s
    <p class="mono dim">%s %s · %s %s</p>
    <a class="btn btn-primary" href="%sintel/">%s%s</a>
  </div>
  <div class="panel latest">
    <h2 class="panel-h">%s</h2>%s
    <ol class="lt">%s</ol>
    <a class="more" href="%schangelog/">%s%s</a>
  </div>
</section>
<section class="wrap sec orbat" id="orbat" aria-labelledby="h-orbat">
  <h2 id="h-orbat"><span class="sec-code" aria-hidden="true">ORBAT</span>%s</h2>
  %s
  %s
</section>
<section class="wrap who">
  <div class="panel who-in">
    <h2 class="panel-h">%s</h2>
    %s
    <a class="btn btn-ghost" href="%sabout/">%s%s</a>
  </div>
</section>""" % (
        t("home.kicker"), t("home.lead", "p", "lead"),
        BASE, t("home.cta_mods"), icon("arrow"), BASE, t("home.cta_admins"), BASE, t("home.cta_about"),
        t("ui.search_open", "span", "js-only"), radar,
        t("home.feed"), ticker_items, ticker_items, stat_html,
        t("ui.declassified", "span", "stamp", None, 'aria-hidden="true"'), t("home.featured"), t("home.featured_t", "h2"), t("home.featured_p", "p"),
        t("intel.ref"), "IFG/HQ-" + redact(4) + "-26", t("ui.classified"), redact(12),
        BASE, t("home.featured_cta"), icon("arrow"),
        t("home.latest"), t("home.latest_d", "p", "dim"), latest, BASE, t("logp.h1"), icon("arrow"),
        t("home.orbat"), t("home.orbat_d", "p", "dim"), orbat(),
        t("home.who"), t("home.who_p", "p"), BASE, t("home.cta_about"), icon("arrow"))
    page("", "home.title", body, "home", cls="p-home")


def mods_index():
    filt = '<div class="filters js-only" role="group" %s><button type="button" class="fbtn" aria-pressed="true" data-filter="all">%s</button>%s</div>' % (
        ta("aria-label", "ui.filter"), t("ui.all"),
        "".join('<button type="button" class="fbtn" aria-pressed="false" data-filter="%s">%s</button>' % (c, t("cat." + c)) for c, _ in CATS))
    body = phead("FILE-02", "mods.kicker", "mods.h1", "mods.lead", {"n": len(MODS)}) + \
        '<section class="wrap sec orbat">%s%s</section>' % (filt, orbat())
    page("workshop/", "mods.title", body, "mods")


def generic_server_json():
    return json.dumps({
        "bindAddress": "",
        "bindPort": 2001,
        "publicAddress": "",
        "publicPort": 2001,
        "a2s": {"address": "", "port": 17777},
        "rcon": {"address": "", "port": 19999, "password": "<your RCON password>", "permission": "admin"},
        "game": {
            "name": "<your server name>",
            "password": "",
            "passwordAdmin": "<your admin password>",
            "admins": [],
            "scenarioId": MODS["conflict-pve"]["scenarioIds"][0],
            "maxPlayers": 32,
            "visible": True,
            "crossPlatform": False,
            "supportedPlatforms": ["PLATFORM_PC"],
            "gameProperties": {
                "serverMaxViewDistance": 2500,
                "serverMinGrassDistance": 50,
                "networkViewDistance": 1500,
                "disableThirdPerson": False,
                "fastValidation": True,
                "battlEye": True,
                "persistence": {"autoSaveInterval": 10},
            },
            "mods": [{"modId": MODS["conflict-pve"]["guid"], "name": name(MODS["conflict-pve"])}],
        },
        "operating": {"lobbyPlayerSynchronise": True, "playerSaveTime": 120, "aiLimit": -1, "slotReservationTimeout": 60},
    }, indent=2, ensure_ascii=False)


def cfg_table(f):
    trs = []
    for r in f["rows"]:
        if r.get("group"):
            trs.append('<tr class="grp"><td colspan="3"><code class="wrapcode">%s</code>%s</td></tr>' % (
                H(r["key"]), cfg_text(r["help"]) if r["help"] else ""))
            continue
        val = _FLOAT.sub(tidy_float, r["value"])
        help_ = cfg_text(r["help"]) if r["help"] else '<span class="dim">—</span>'
        trs.append('<tr><td><code class="wrapcode">%s</code></td><td><code class="wrapcode val">%s</code></td><td>%s</td></tr>' % (
            H(r["key"]), H(val), help_))
    folder = cfg_folder(f["profile"])
    mod = MODS[f["mod"]]
    notes = ""
    if f.get("readme"):
        notes += '<p class="dim">%s</p>' % cfg_text(f["readme"])
    if f["mod"] == "enhanced-compositions":
        notes += t("ui.cfg_cpve", "p", "dim")
    inc = " " + badge_inc() if folder in CFG_INCOMING else ""
    return """<details class="cfg" id="%s">
  <summary><code>%s</code><span class="cfg-meta"><a href="%s">%s</a>%s%s</span></summary>
  %s
  <div class="tbl"><table class="table cfgt">
  <thead><tr><th scope="col">%s</th><th scope="col">%s</th><th scope="col">%s</th></tr></thead>
  <tbody>%s</tbody></table></div>
</details>""" % (cfg_anchor(f["profile"]), H(f["profile"]), url("workshop/%s/" % f["mod"]), H(name(mod)),
                 t("ui.rows", "span", "mono dim", {"n": len(f["rows"])}), inc, notes,
                 t("ui.key"), t("ui.default"), t("ui.help"), "".join(trs))


def admins():
    toc = "".join('<a href="#%s">%s</a>' % (a, t(k)) for a, k in [
        ("install", "admins.install"), ("json", "admins.json"), ("scen", "admins.scen"), ("profile", "admins.profile"),
        ("cmds", "admins.cmds"), ("cfg", "admins.cfg"), ("logs", "admins.logs")])
    sj = generic_server_json()
    scen_rows = "".join('<tr><td><a href="%s">%s</a></td><td>%s</td><td><code class="wrapcode">%s</code></td><td>%s</td></tr>' % (
        url("workshop/%s/" % s), H(name(MODS[s])), H(", ".join(MODS[s]["scenarios"])), H(sid), copy_btn(text=sid, small=True))
        for s in ORDER for sid in MODS[s]["scenarioIds"])
    cfgs = "".join(cfg_table(f) for f in CONFIGS)
    body = phead("CON-03", "admins.kicker", "admins.h1", "admins.lead") + """
<div class="wrap docgrid">
  <nav class="panel toc sticky" aria-label="TOC"><h2 class="panel-h">%s</h2>%s</nav>
  <div class="docmain">
    %s
    %s
    %s
    %s
    %s
    %s
    %s
  </div>
</div>""" % (t("admins.toc"), toc,
             sec("install", "admins.install", '<ol class="steps">%s</ol>' % tl("admins.install_s"), "01"),
             sec("json", "admins.json", t("admins.json_p", "p") + """<figure class="codebox">
  <figcaption><span><code>server.json</code></span>%s</figcaption>
  <pre class="code tall" id="server-json" tabindex="0"><code>%s</code></pre>
</figure>%s""" % (copy_btn("#server-json"), H(sj), t("admins.json_persist", "p", "note")), "02"),
             sec("scen", "admins.scen", t("admins.scen_p", "p") + """<div class="tbl"><table class="table">
<thead><tr><th scope="col">%s</th><th scope="col">Scenario</th><th scope="col">%s</th><th scope="col"><span class="sr">%s</span></th></tr></thead>
<tbody>%s</tbody></table></div>""" % (t("deps.col_name"), t("ui.scenario"), t("ui.copy"), scen_rows), "03"),
             sec("profile", "admins.profile", '<ul class="feat">%s</ul>' % tl("admins.profile_s"), "04"),
             sec("cmds", "admins.cmds", t("admins.cmds_p", "p") + cmd_table(with_mod=True), "05"),
             sec("cfg", "admins.cfg", t("admins.cfg_p", "p") + """<div class="cfg-tools js-only">
  <label class="field">%s<input type="search" id="cfg-filter" autocomplete="off" spellcheck="false" %s></label>
  <span class="mono dim" id="cfg-count" aria-live="polite"></span>
</div>
<div class="cfgs">%s</div>""" % (icon("search"), ta("placeholder", "admins.cfg_filter"), cfgs), "06"),
             sec("logs", "admins.logs", t("admins.logs_p", "p") + '<ul class="feat">%s</ul>' % tl("admins.logs_s"), "07"))
    page("admins/", "admins.title", body, "admins", cfg_i18n=True)


def intel():
    def isec(id_, key, body, code, inc=False):
        note = (" " + badge_inc()) if inc else ""
        return """<section class="dsec" id="%s" aria-labelledby="h-%s">
  <h2 id="h-%s"><span class="sec-code" aria-hidden="true">%s</span>%s%s</h2>
  %s
</section>""" % (id_, id_, id_, code, t(key), note, body)
    lvl = "".join('<tr><th scope="row"><span class="lvl lvl-%s">%s</span></th><td>%s</td><td class="mono">%d / %d / %d m</td><td class="mono">%d</td></tr>' % (
        n.lower(), n, t(k), r[0], r[1], r[2], w) for n, k, r, w in DOCTRINE)
    drone = "".join('<tr><th scope="row">%s</th><td class="mono">%d m</td><td><span class="bar" style="--w:%d%%"></span></td></tr>' % (
        t(k), v, v * 100 // 300) for k, v in DRONE_RANGES)
    lights = "".join('<li><span class="led led-%s" aria-hidden="true"></span>%s</li>' % (c, t("intel.light_" + c)) for c in ("g", "r", "rf", "o"))
    body = """<div class="wrap">
<article class="dossier">
  <header class="dossier-h">
    %s
    <p class="kicker"><span class="kicker-code">INTREP</span>%s</p>
    <h1 data-scramble>%s</h1>
    %s
    <dl class="dossier-meta mono">
      <div><dt>%s</dt><dd>IFG/HQ-%s-26</dd></div>
      <div><dt>AO</dt><dd>EVERON · BELLEAU WOOD</dd></div>
      <div><dt>SRC</dt><dd>%s</dd></div>
      <div><dt>%s</dt><dd>%s</dd></div>
    </dl>
  </header>
  %s
  <div class="dossier-body">
  %s %s %s %s %s %s %s %s %s %s %s %s %s
  </div>
</article>
</div>""" % (
        t("intel.stamp", "span", "stamp", None, 'aria-hidden="true"'), t("intel.kicker"), t("intel.h1"), t("intel.lead", "p", "lead"),
        t("intel.ref"), redact(4), redact(14), t("ui.classified"), t("ui.declassified"),
        t("intel.state_note", "p", "note"),
        isec("summary", "intel.summary", t("intel.summary_p", "p", "lead2"), "00"),
        isec("hq", "intel.hq", '<ul class="feat">%s</ul>' % tl("intel.hq_s"), "01"),
        isec("doctrine", "intel.doctrine", t("intel.doctrine_p", "p") + """<div class="tbl"><table class="table">
<thead><tr><th scope="col">%s</th><th scope="col">%s</th><th scope="col">%s</th><th scope="col">%s</th></tr></thead>
<tbody>%s</tbody></table></div><ul class="feat">%s</ul>""" % (t("intel.lvl_col"), t("intel.lvl_who"), t("intel.lvl_rng"), t("intel.lvl_wd"), lvl, tl("intel.doctrine_s")), "02"),
        isec("fires", "intel.fires", '<ul class="feat">%s</ul>' % tl("intel.fires_s"), "03"),
        isec("drones", "intel.drones", t("intel.drones_p", "p") + """<div class="tbl"><table class="table drones">
<thead><tr><th scope="col">%s</th><th scope="col">%s</th><th scope="col"><span class="sr">%%</span></th></tr></thead>
<tbody>%s</tbody></table></div><ul class="feat">%s</ul>""" % (t("intel.drone_col_pos"), t("intel.drone_col_rng"), drone, tl("intel.drones_s")), "04"),
        isec("light", "intel.light", t("intel.light_p", "p") + '<ul class="leds">%s</ul>' % lights, "05", True),
        isec("plans", "intel.plans", t("intel.plans_p", "p") + '<ol class="steps">%s</ol>' % tl("intel.plan") + t("intel.plans_esc", "p", "note"), "06", True),
        isec("ambush", "intel.ambush", '<ul class="feat">%s</ul>' % tl("intel.ambush_s"), "07", True),
        isec("air", "intel.air", '<ul class="feat">%s</ul>' % tl("intel.air_s"), "08", True),
        isec("weather", "intel.weather", '<ul class="feat">%s</ul>' % tl("intel.weather_s"), "09", True),
        isec("night", "intel.night", '<ul class="feat">%s</ul>' % tl("intel.night_s"), "10", True),
        isec("radio", "intel.radio", t("intel.radio_p", "p"), "11", True),
        isec("base", "intel.base", '<ul class="feat">%s</ul>' % tl("intel.base_s"), "12")
        + isec("guide", "intel.guide", '<ol class="steps guide">%s</ol>' % tl("intel.guide_s"), "13"))
    body += '<div class="wrap pn"><a class="pn-a" href="%sworkshop/conflict-pve/">%s<span><small>MOD</small>INDFORGE - Conflict PvE</span></a><a class="pn-a pn-next" href="%sworkshop/forest/"><span><small>MOD</small>INDFORGE - Forest</span>%s</a></div>' % (
        BASE, icon("back"), BASE, icon("arrow"))
    page("intel/", "intel.title", body, "intel", cls="p-intel")


def changelog():
    rel = [(d, s, v) for s in ORDER for v, d in MODS[s]["versions"]]
    rel.sort(key=lambda x: (x[0], x[1]), reverse=True)
    rows = "".join('<tr><td class="mono">%s</td><td><a href="%s">%s</a></td><td class="mono">v%s</td></tr>' % (
        d, url("workshop/%s/" % s), H(name(MODS[s])), H(v)) for d, s, v in rel)
    logs = "".join("""<details class="cfg"%s><summary><span>%s</span><span class="cfg-meta mono dim">v%s · %s</span></summary>
<blockquote class="quote-log" lang="en"><div class="log-txt">%s</div></blockquote></details>""" % (
        " open" if j == 0 else "", H(name(MODS[s])), H(MODS[s]["version"]), H(MODS[s]["updated"]), H(MODS[s]["changelog"].strip()))
        for j, (_, s) in enumerate(latest_updates(len(MODS))) if MODS[s]["changelog"])
    body = phead("LOG-05", "logp.kicker", "logp.h1", "logp.lead") + """<div class="wrap twocol">
  <div>%s</div>
  <div>%s</div>
</div>""" % (sec("logs", "sec.changelog", t("log.workshop_note", "p", "dim") + logs, "01"),
             sec("recent", "logp.recent", """<div class="tbl tall"><table class="table">
<thead><tr><th scope="col">%s</th><th scope="col">%s</th><th scope="col">%s</th></tr></thead><tbody>%s</tbody></table></div>""" % (
                 t("logp.col_date"), t("logp.col_mod"), t("logp.col_ver"), rows), "02"))
    page("changelog/", "logp.title", body, "log")


def status():
    rows = []
    for s in ORDER:
        m = MODS[s]
        game = H(m["game"]) if m["game"] else redact(6)
        if m["game"] and m["game"] != LATEST_GAME:
            game += " " + t("ui.older", "span", "chip chip-old")
        rows.append('<tr data-cat="%s"><td><a href="%s">%s</a></td><td>%s</td><td class="mono">%s</td><td class="mono">%s</td><td class="mono">%s</td></tr>' % (
            CAT_OF[s], url("workshop/%s/" % s), H(name(m)), chips(s), H("v" + m["version"]) if m["version"] else redact(5),
            H(m["updated"]) if m["updated"] else redact(8), game))
    legend = "".join('<div><dt>%s</dt><dd>%s</dd></div>' % (t("status." + k, "span", "chip chip-" + k), t("status.%s.d" % k))
                     for k in ("operational", "standby", "restricted"))
    body = phead("SIT-06", "statusp.kicker", "statusp.h1", "statusp.lead") + """<div class="wrap">
%s
%s
%s
</div>""" % (sec("board", "statusp.h1", t("statusp.game_now", "p", "dim", {"v": LATEST_GAME}) + """<div class="tbl"><table class="table board">
<thead><tr><th scope="col">%s</th><th scope="col">%s</th><th scope="col">%s</th><th scope="col">%s</th><th scope="col">%s</th></tr></thead>
<tbody>%s</tbody></table></div>""" % (t("statusp.col_mod"), t("statusp.col_state"), t("statusp.col_ver"), t("statusp.col_upd"),
                                      t("statusp.col_game"), "".join(rows)), "01"),
             sec("pipeline", "statusp.pipeline", t("statusp.pipeline_p", "p", "", {"v": CPVE_VER}) +
                 '<ul class="feat feat-inc">%s</ul><p><a href="%sworkshop/conflict-pve/#incoming">INDFORGE - Conflict PvE</a></p>' % (tl("m.conflict-pve.inc"), BASE), "02", "sec-inc"),
             sec("legend", "statusp.col_state", '<dl class="legend">%s</dl>' % legend, "03"))
    page("status/", "statusp.title", body, "status")


def about():
    roster = [("TheUnknownTeam", "about.r_author"), ("Volmog_0", "about.r_volmog"),
              ("Unknown Soldiers", "about.r_soldiers"), ("Captain Valaaks", "about.r_valaaks")]
    def initials(n):
        w = re.findall(r"[A-Za-z0-9]+", n)
        return (w[0][0] + (w[1][0] if len(w) > 1 else w[0][-1])).upper()
    ros = "".join('<li class="op"><span class="op-ico mono" aria-hidden="true">%s</span><span><b>%s</b>%s<span class="mono dim">CLR %s</span></span></li>' % (
        initials(n), H(n), t(k, "span", "op-role"), redact(5)) for n, k in roster)
    body = phead("PER-07", "about.kicker", "about.h1", "about.lead") + """<div class="wrap docgrid nogrid">
<div class="docmain">
%s %s %s %s %s %s
<blockquote class="motto-big">%s<footer class="mono dim">— INDFORGE - Studio</footer></blockquote>
</div></div>""" % (
        sec("unit", "about.unit", t("about.unit_p", "p", "lead2"), "01"),
        sec("roster", "about.roster", t("about.roster_d", "p", "dim") + '<ul class="roster">%s</ul>' % ros, "02"),
        sec("doctrine", "about.doctrine", '<ul class="feat">%s</ul>' % tl("about.d"), "03"),
        sec("theatres", "about.theatres", '<ul class="feat">%s</ul>' % tl("about.th"), "04"),
        sec("communities", "about.communities", '<ul class="feat">%s</ul>' % tl("about.c"), "05"),
        sec("contact", "about.contact", t("about.contact_p", "p"), "06"),
        t("about.motto", "p"))
    page("about/", "about.title", body, "about")


def e404():
    body = """<section class="wrap e404">
  <div class="noise" aria-hidden="true"></div>
  <p class="kicker"><span class="kicker-code">ERR-404</span>%s</p>
  <h1 data-scramble>%s</h1>
  %s
  <p class="mono dim" aria-hidden="true">FREQ ███.███ MHz // NO CARRIER</p>
  <a class="btn btn-primary" href="%s">%s%s</a>
</section>""" % (t("e404.title"), t("e404.h1"), t("e404.p", "p", "lead"), BASE, icon("back"), t("e404.cta"))
    page("404.html", "e404.title", body, "404")


def search_index():
    items = [{"k": "page", "t": key, "tk": 1, "u": url(p)} for p, key, _ in NAV]
    for s in ORDER:
        m = MODS[s]
        items.append({"k": "mod", "t": name(m), "s": "m.%s.tag" % s, "x": "%s %s %s" % (m["guid"] or "", s, " ".join(m["tags"])), "u": url("workshop/%s/" % s)})
    for cmd, key, _ in COMMANDS:
        items.append({"k": "cmd", "t": cmd.split("\n")[0], "s": key, "u": url("admins/#cmds")})
    for f in CONFIGS:
        items.append({"k": "cfg", "t": f["profile"], "x": " ".join(r["key"] for r in f["rows"]), "u": url("admins/#" + cfg_anchor(f["profile"]))})
    for a in ("hq", "doctrine", "fires", "drones", "light", "plans", "ambush", "air", "weather", "night", "radio", "base", "guide"):
        items.append({"k": "page", "t": "intel." + a, "tk": 1, "s": "intel.title", "u": url("intel/#" + a)})
    for a, key in (("install", "admins.install"), ("json", "admins.json"), ("scen", "admins.scen"), ("profile", "admins.profile"), ("logs", "admins.logs")):
        items.append({"k": "page", "t": key, "tk": 1, "s": "admins.title", "u": url("admins/#" + a)})
    with open(os.path.join(ROOT, "assets", "search.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(items, f, ensure_ascii=False, separators=(",", ":"))


def write_i18n():
    d = os.path.join(ROOT, "assets", "i18n")
    os.makedirs(d, exist_ok=True)
    for l, _ in ALL_LANGS:
        if l not in FLAT:
            for f in (l + ".json", "cfg-" + l + ".json"):
                if os.path.exists(os.path.join(d, f)):
                    os.remove(os.path.join(d, f))
    for l in FLAT:
        with open(os.path.join(d, l + ".json"), "w", encoding="utf-8", newline="\n") as f:
            json.dump(FLAT[l], f, ensure_ascii=False, separators=(",", ":"))
        with open(os.path.join(d, "cfg-" + l + ".json"), "w", encoding="utf-8", newline="\n") as f:
            json.dump({k: H(v) for k, v in CFG_TR[l].items()}, f, ensure_ascii=False, separators=(",", ":"))


def legacy_redirects():
    """The mod pages moved from /mods/ to /workshop/: keep the old links working."""
    tpl = ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><title>INDFORGE - Studio</title>\n'
           '<meta name="robots" content="noindex"><link rel="canonical" href="%(abs)s">\n'
           '<meta http-equiv="refresh" content="0; url=%(rel)s">\n'
           '<script>location.replace("%(rel)s" + location.hash)</script></head>\n'
           '<body style="background:#06080a;color:#ffb000;font-family:monospace"><p><a href="%(rel)s" style="color:#ffb000">%(rel)s</a></p></body></html>\n')
    for old, new in [("mods/", "workshop/")] + [("mods/%s/" % s_, "workshop/%s/" % s_) for s_ in ORDER]:
        out = os.path.join(ROOT, old, "index.html")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8", newline="\n") as f:
            f.write(tpl % {"abs": SITE + new, "rel": BASE + new})


def sitemap():
    urls = "".join("<url><loc>%s%s</loc><lastmod>%s</lastmod></url>" % (SITE, p, GENERATED) for p in PAGES if p != "404.html")
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8", newline="\n") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>\n' % urls)
    open(os.path.join(ROOT, ".nojekyll"), "w").close()


def manifest():
    ico = lambda n, s: {"src": "assets/img/%s?v=%s" % (n, ICON_VER), "sizes": s, "type": "image/png"}
    icon192 = [ico("icon-192.png", "192x192")]
    m = {
        "name": "INDFORGE - Studio · Arma Reforger",
        "short_name": "INDFORGE",
        "description": E["site.desc"],
        "id": BASE,
        "start_url": BASE,
        "scope": BASE,
        "display": "standalone",
        "lang": "en",
        "dir": "ltr",
        "categories": ["games", "entertainment"],
        "background_color": "#06080a",
        "theme_color": "#06080a",
        "icons": [ico("icon-192.png", "192x192"), ico("icon-512.png", "512x512")],
        "shortcuts": [
            {"name": E["nav.mods"], "url": BASE + "workshop/", "icons": icon192},
            {"name": E["nav.admins"], "url": BASE + "admins/", "icons": icon192},
            {"name": E["nav.intel"], "url": BASE + "intel/", "icons": icon192},
        ],
    }
    with open(os.path.join(ROOT, "manifest.webmanifest"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(m, f, ensure_ascii=False, indent=2)
        f.write("\n")


if __name__ == "__main__":
    write_i18n()
    home()
    about()
    mods_index()
    for s in ORDER:
        mod_page(s)
    admins()
    intel()
    changelog()
    status()
    e404()
    search_index()
    legacy_redirects()
    sitemap()
    manifest()
    print("built %d pages, %d languages, version %s" % (len(PAGES), len(FLAT), VER))
