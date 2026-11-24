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
LIVE = ("en", "fr", "de", "es", "it", "pl", "uk")
LANGS = [x for x in ALL_LANGS if x[0] in LIVE]

# Display modes ("optics"): code, menu tag.
# All but the first carry an ambient effect layer (site.js, "fx").
OPTICS = [
    ("arma", "ARM"),
    ("nvg", "NVG"),
    ("thermal", "THM"),
    ("arctic", "ARC"),
    ("desert", "DST"),
    ("forest", "FOR"),
    ("red", "RED"),
    ("day", "DAY"),
]
# National colour schemes: colours only, no ambient effect. Code, menu tag.
NATIONS = [
    ("fra", "FRA"),
    ("gbr", "GBR"),
    ("deu", "DEU"),
    ("esp", "ESP"),
    ("ita", "ITA"),
    ("pol", "POL"),
    ("ukr", "UKR"),
    ("usa", "USA"),
    ("can", "CAN"),
    ("bel", "BEL"),
    ("che", "CHE"),
]

CATS = [
    ("indforge", ["conflict-pve", "forest", "ai-framework", "enhanced-compositions"]),
    ("auc", ["auc-factions", "auc-vehicles", "auc-conflict"]),
    ("ctrp", ["cherchetoi-rp-clothing", "cherchetoi-rp-props", "cherchetoi-rp-vehicles"]),
    ("gear", ["modern-fia", "rcd-rhs", "rcd-wcs", "talibanmod-red-side-v2"]),
    ("vehicles", ["lav-25-desert", "solo-push-pull"]),
    ("standby", ["off-road-vehicles", "uaz-452-offroad"]),
]
ORDER = [s for _, slugs in CATS for s in slugs]
CAT_OF = {s: c for c, slugs in CATS for s in slugs}
# Workshop page: filter by family (one choice) and by the official Workshop main tags.
FAMILIES = [
    ("indforge", "fam.indforge", dict(CATS)["indforge"]),
    ("auc", "fam.auc", dict(CATS)["auc"]),
    ("ctrp", "fam.ctrp", dict(CATS)["ctrp"]),
    ("manw", "fam.manw", ["off-road-vehicles"]),
    ("gear", "cat.gear", dict(CATS)["gear"]),
    ("vehicles", "cat.vehicles", dict(CATS)["vehicles"]),
    ("standby", "cat.standby", dict(CATS)["standby"]),
]
FAM_OF = {s: [f for f, _, slugs in FAMILIES if s in slugs] for s in ORDER}
# The Workshop's own main categories, in its order (reforger.armaplatform.com/workshop).
WS_TAGS = ["VEHICLES", "WEAPONS", "STRUCTURES", "CHARACTERS", "ANIMALS", "VEGETATION", "PROPS", "COMPOSITIONS",
           "SCENARIOS_SP", "SCENARIOS_MP", "TERRAINS", "SYSTEMS", "EFFECTS", "MISC"]

STATUS = {
    "conflict-pve": ["operational", "dev"],
    "ai-framework": ["dev", "unreleased"],
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
CFG_INCOMING = {"INDFORGE_Weather", "INDFORGE_NightGear", "INDFORGE_DroneTeam", "INDFORGE_MavicLight", "INDFORGE_RadioAlerts", "INDFORGE_Movement"}

# Doctrine levels, read from $profile:INDFORGE_AIDoctrine/config.json (Levels block).
DOCTRINE = [
    ("Boot", "intel.lvl.boot", (275, 165, 90), 0),
    ("Grunt", "intel.lvl.grunt", (330, 220, 130), 1),
    ("Operator", "intel.lvl.operator", (440, 275, 165), 2),
    ("Overwatch", "intel.lvl.overwatch", (385, 275, 165), 2),
]
# Drone sight ranges, read from $profile:INDFORGE_DroneSight/config.json.
DRONE_RANGES = [("intel.drone_stand", 300), ("intel.drone_crouch", 180), ("intel.drone_prone", 100)]

# Tips page: how to use each feature, mod by mod.
# (tip id, role, state, link): role p = player, a = server admin, m = Game Master / mission maker;
# state "in" = in the Workshop release, "inc" = merged after it (shown as Incoming).
# Texts: tools/i18n/tips/<lang>.json, keys tips.<id>.h (title), .s (steps), .x (optional hint).
TIPS = [
    ("conflict-pve", [
        ("cp-base", "p", "in", "news/#base"), ("cp-fuel", "p", "in", None), ("cp-sabot", "p", "in", None),
        ("cp-hesco", "p", "in", None), ("cp-drone", "p", "in", "news/#drones"), ("cp-jam", "p", "in", None),
        ("cp-hq", "p", "in", "news/#hq"), ("cp-mortar", "p", "in", "news/#fires"), ("cp-spread", "p", "in", None),
        ("cp-doct", "p", "in", "news/#doctrine"), ("cp-mark", "p", "in", None), ("cp-shovel", "p", "in", None),
        ("cp-rank", "p", "in", None), ("cp-cram", "p", "in", None),
        ("cp-mavic", "p", "inc", "news/#light"), ("cp-wx", "p", "inc", "news/#weather"),
        ("cp-ambush", "p", "inc", "news/#ambush"), ("cp-air", "p", "inc", "news/#air"),
        ("cp-radio", "p", "inc", "news/#radio"), ("cp-vol", "p", "inc", None), ("cp-night", "p", "inc", "news/#night"),
        ("cp-cmd", "a", "in", "admins/#cmds"), ("cp-cfg", "a", "in", "admins/#cfg"), ("cp-logs", "a", "in", "admins/#logs"),
    ]),
    ("forest", [
        ("fo-same", "p", "in", "#conflict-pve"), ("fo-base", "p", "in", None), ("fo-snipe", "p", "in", None),
        ("fo-road", "p", "in", None), ("fo-adm", "a", "in", "workshop/forest/#deps"),
    ]),
    ("enhanced-compositions", [
        ("ec-gen", "p", "in", None), ("ec-cmd", "p", "in", None), ("ec-gar", "p", "in", None), ("ec-svc", "p", "in", None),
        ("ec-gold", "p", "in", None), ("ec-gm", "m", "in", None), ("ec-adm", "a", "in", None),
    ]),
    ("rcd-wcs", [("rw-rank", "p", "in", None), ("rw-tpn", "p", "in", None), ("rw-iff", "p", "in", None), ("rw-kit", "p", "in", None)]),
    ("rcd-rhs", [("rr-where", "p", "in", None)]),
    ("solo-push-pull", [("sp-push", "p", "in", None)]),
    ("off-road-vehicles", [("or-torque", "p", "in", None), ("or-gm", "m", "in", None)]),
    ("packs", [
        ("auf-side", "p", "in", "workshop/auc-factions/"), ("auv-rank", "p", "in", "workshop/auc-vehicles/"),
        ("auc-scen", "p", "in", "workshop/auc-conflict/"), ("ctrp", "p", "in", "workshop/cherchetoi-rp-vehicles/"),
        ("mfia", "p", "in", "workshop/modern-fia/"), ("tal", "p", "in", "workshop/talibanmod-red-side-v2/"),
        ("lav", "p", "in", "workshop/lav-25-desert/"), ("uaz", "p", "in", "workshop/uaz-452-offroad/"),
    ]),
]
TIP_ROLES = [("p", "tips.r.p"), ("a", "tips.r.a"), ("m", "tips.r.m")]

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
# Tips texts live apart: written in French first, the other languages get the French text
# until their own tools/i18n/tips/<lang>.json exists.
_TIPS_DIR = os.path.join(TOOLS, "i18n", "tips")
TIPS_FR_ONLY = not os.path.exists(os.path.join(_TIPS_DIR, "en.json"))
for _l in SRC:
    _p = os.path.join(_TIPS_DIR, _l + ".json")
    SRC[_l].update(load(_p if os.path.exists(_p) else os.path.join(_TIPS_DIR, "fr.json")))
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
        _m.pop("stats", None)
GENERATED = load(os.path.join(TOOLS, "data", "mods.json"))["generated"]
STATS_DATE = load(os.path.join(TOOLS, "data", "mods.json")).get("stats_date")
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
# Development builds whose complete changelog (admin notes included) lives on the mod page under a
# permanent anchor, #build-<id>: the short Workshop changelog links there, so the anchor never changes.
# Text: tools/data/builds/<slug>-<id>.txt, quoted as written (English). Entry: (build, version it follows,
# version it was published as, or None). The build stays "Incoming" while the Workshop still shows the
# version it follows; the published version is set by hand once the Workshop page shows it.
BUILDS = {"conflict-pve": [("77bd6c4", "2.0.6", "2.1.0")], "forest": [("b2e7e63", "0.0.2", "0.0.3")]}
# Build notes that send server admins to another build's notes (the settings files they share).
BUILD_SEE = {("forest", "b2e7e63"): ("conflict-pve", "77bd6c4")}
# Mods that need RHS - Status Quo and link its EULA in their credits.
RHS_EULA_MODS = ("conflict-pve", "forest")
RHS_EULA = "https://docs.rhsmods.org/rhs-status-quo-user-documentation/arma-reforger/rhs-status-quo/eula"
# Required sound credit, shown word for word in every language.
SOUND_CREDIT = "Additional sounds: Joseph SARDIN - LaSonotheque.org"


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


def _aperture():
    # Lens iris: a hexagonal opening, each edge carried on to the barrel as a blade.
    import math
    r, R, c = 3.6, 9.0, 12.0
    v = [(c + r * math.cos(math.radians(60 * i - 90)), c + r * math.sin(math.radians(60 * i - 90))) for i in range(6)]
    blades = []
    for i in range(6):
        (ax, ay), (bx, by) = v[i], v[(i + 1) % 6]
        dx, dy = bx - ax, by - ay
        n = math.hypot(dx, dy)
        dx, dy = dx / n, dy / n
        px, py = bx - c, by - c
        k = -(px * dx + py * dy) + math.sqrt((px * dx + py * dy) ** 2 - (px * px + py * py - R * R))
        blades.append("M%.2f %.2fL%.2f %.2f" % (bx, by, bx + k * dx, by + k * dy))
    hexa = "M" + "L".join("%.2f %.2f" % p for p in v) + "Z"
    return '<circle cx="12" cy="12" r="9"/><path class="lens" d="%s"/><path d="%s"/>' % (hexa, "".join(blades))


def icon(name):
    paths = {
        "search": '<circle cx="11" cy="11" r="6.5"/><path d="M16 16l5 5"/>',
        "menu": '<path d="M3 6h18M3 12h18M3 18h12"/>',
        "ext": '<path d="M14 4h6v6M20 4l-9 9M18 14v6H4V6h6"/>',
        "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
        "back": '<path d="M19 12H5M11 6l-6 6 6 6"/>',
        "optic": _aperture(),
        "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3.5 3 14.5 0 18M12 3c-3 3.5-3 14.5 0 18"/>',
        "cfg": '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
        "rating": '<path d="M7 11v9H4v-9zM7 11l4-7c1.6 0 2.4 1 2 2.6L12.4 10H19c1.2 0 2 1 1.8 2.2l-1.3 6.2c-.2 1-1 1.6-2 1.6H7"/>',
        "subs": '<circle cx="12" cy="8" r="3.6"/><path d="M4.5 20c.8-4 3.8-6 7.5-6s6.7 2 7.5 6"/>',
        "dl": '<path d="M12 4v11M7 10l5 5 5-5M5 20h14"/>',
    }
    return '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true" focusable="false">%s</svg>' % paths[name]


# ---------------------------------------------------------------- shell
NAV = [
    ("", "nav.home", "home"), ("workshop/", "nav.mods", "mods"), ("tips/", "nav.tips", "tips"), ("admins/", "nav.admins", "admins"),
    ("news/", "nav.intel", "intel"), ("changelog/", "nav.log", "log"), ("roadmap/", "nav.status", "status"),
    ("about/", "nav.about", "about"),
]

HEAD_JS = (
    "(function(d){var h=d.documentElement,L=%s,O=%s,l='';h.className+=' js';"
    "try{l=localStorage.getItem('ifg-lang')||''}catch(e){}"
    "if(L.indexOf(l)<0){l='en';var n=navigator.languages||[navigator.language||'en'];"
    "for(var i=0;i<n.length;i++){var c=String(n[i]).slice(0,2).toLowerCase();if(L.indexOf(c)>=0){l=c;break}}}"
    "h.setAttribute('data-lang',l);try{var o=localStorage.getItem('ifg-optic');if(O.indexOf(o)>0)h.setAttribute('data-theme',o);"
    "var f=localStorage.getItem('ifg-fx');if(f==='off'||(!f&&matchMedia('(prefers-reduced-motion: reduce)').matches))h.className+=' fx-off'}catch(e){}"
    "if(l!=='en'){h.className+=' i18n-wait';"
    "setTimeout(function(){h.classList.remove('i18n-wait')},1500)}"
    # a page change cut short (fast clicks, prerendered page) only skips its animation: no console error
    "addEventListener('pagereveal',function(e){var v=e.viewTransition,n=function(){};"
    "if(v){v.ready.catch(n);v.finished.catch(n);v.updateCallbackDone.catch(n)}})})(document);"
) % (json.dumps([l for l, _ in LANGS]), json.dumps([o[0] for o in OPTICS] + [n[0] for n in NATIONS]))

SPEC = json.dumps({"prerender": [{"where": {"href_matches": BASE + "*"}, "eagerness": "moderate"}]})


# Header mark inlined so it takes the colours of the chosen optic (accent and dark fill).
def _brand_mark():
    svg = open(os.path.join(ROOT, "assets", "img", "logo.svg"), encoding="utf-8").read().strip()
    assert svg.count('fill="#ffb000"') == 1 and svg.count('fill="#0a0e10"') == 1, "logo.svg colours changed"
    svg = svg.replace('fill="#ffb000"', 'class="lm-a"').replace('fill="#0a0e10"', 'class="lm-b"')
    return svg.replace("<svg ", '<svg class="brand-mark" width="36" height="36" aria-hidden="true" focusable="false" ', 1)


BRAND_MARK = _brand_mark()


def header(active):
    links = []
    for i, (p, key, pid) in enumerate(NAV):
        cur = ' aria-current="page"' if pid == active else ""
        links.append('<a href="%s"%s><span class="nav-n" aria-hidden="true">%02d</span>%s</a>' % (url(p), cur, i + 1, t(key)))
    langs = "".join(
        '<li role="none"><button type="button" role="menuitemradio" aria-checked="false" data-lang="%s" lang="%s"><b>%s</b><span>%s</span></button></li>'
        % (l, l, l.upper(), H(n)) for l, n in LANGS)
    wip = [(l, n) for l, n in ALL_LANGS if l not in LIVE]
    if wip:
        # Paused languages: listed, but classified until their translation is back.
        langs += '<li role="separator" class="lang-sep"></li>' + "".join(
            '<li role="none"><span class="lang-wip" role="menuitem" aria-disabled="true"><b>%s</b>%s<em>W.I.P</em></span></li>'
            % (l.upper(), redact(len(n))) for l, n in wip)
    def abc(rows):
        # alphabetical by English name, the default optic first; site.js re-sorts for the chosen language
        return sorted(rows, key=lambda r: (r[0] != "arma", E["optic." + r[0]].lower()))
    def opt_em(o):
        # the optic's own shield emblem (tools/emblems.py) stands for it in the menu
        # data-src: site.js loads the 19 emblems the first time the menu opens, not with every page
        return '<img class="opt-em" data-src="%sassets/img/fs/%s.svg" alt="" width="22" height="26" decoding="async">' % (BASE, o)
    optics = "".join(
        '<li role="none"><button type="button" role="menuitemradio" aria-checked="false" data-optic="%s">'
        '%s<b class="opt-k">%s</b>%s</button></li>'
        % (o, opt_em(o), k, t("optic." + o)) for o, k in abc(OPTICS))
    optics += '<li role="presentation" class="opt-h">%s</li>' % t("optic.nat") + "".join(
        '<li role="none"><button type="button" role="menuitemradio" aria-checked="false" data-optic="%s">'
        '%s<b class="opt-k">%s</b>%s</button></li>'
        % (o, opt_em(o), k, t("optic." + o)) for o, k in abc(NATIONS))
    optics += ('<li role="separator" class="lang-sep"></li><li role="none"><button type="button" role="menuitemcheckbox" '
               'aria-checked="true" class="opt-fx" data-fx><b class="opt-k">FX</b>%s<i class="opt-tg" aria-hidden="true"></i></button></li>'
               % t("optic.fx"))
    return """<a class="skip" href="#main" data-i18n="nav.skip">%s</a>
<header class="hud" id="top">
  <div class="hud-bar">
    <a class="brand" href="%s" aria-label="INDFORGE - Studio">
      %s
      <span class="brand-txt"><b>INDFORGE</b><small aria-hidden="true">%s</small></span>
    </a>
    <span class="mradar" aria-hidden="true"><canvas width="34" height="34"></canvas></span>
    <nav class="nav" id="nav" %s>%s</nav>
    <div class="hud-tools">
      <span class="fsb" aria-hidden="true"></span>
      <button type="button" class="clock csign js-only" %s>%s<b class="csign-v">-----</b></button>
      <span class="sig" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></span>
      <button type="button" class="tool search-btn" data-search %s>%s<kbd>/</kbd></button>
      <div class="lang">
        <button type="button" class="tool lang-btn" aria-haspopup="menu" aria-expanded="false" aria-controls="lang-menu" %s>%s<span class="lang-cur">EN</span></button>
        <ul class="lang-menu" id="lang-menu" role="menu" hidden>%s</ul>
      </div>
      <div class="lang opt">
        <button type="button" class="tool opt-btn" aria-haspopup="menu" aria-expanded="false" aria-controls="opt-menu" %s>%s<span class="opt-cur">ARM</span></button>
        <ul class="lang-menu opt-menu" id="opt-menu" role="menu" hidden><li role="presentation" class="opt-h">%s</li>%s</ul>
      </div>
      <button type="button" class="tool menu-btn" aria-expanded="false" aria-controls="nav" %s>%s</button>
    </div>
  </div>
  <div class="hud-line" aria-hidden="true"></div>
</header>""" % (H(E["nav.skip"]), url(), BRAND_MARK, "".join("<i>%s</i>" % H(c) if c != " " else "<i></i>" for c in E["site.division"].upper()), ta("aria-label", "nav.menu"), "".join(links),
                 ta("title", "ui.callsign_new"), t("ui.callsign", "span", "clock-l"),
                 ta("aria-label", "nav.search"), icon("search"), ta("aria-label", "nav.lang"), icon("globe"), langs,
                 ta("aria-label", "nav.optic"), icon("optic"), t("optic.h"), optics,
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


# Link-preview text of the home page (Discord, X, Slack...): the share card, not the search snippet.
OG_DESC = ("Secure channel open. Field-tested PvE mods for Arma Reforger: every setting, every command, "
           "every dependency list. Declassified.")


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
<meta property="og:description" content="%(ogdesc)s">
<meta property="og:url" content="%(canon)s">
<meta property="og:image" content="%(img)s">%(imgmeta)s
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="%(img)s">
<meta name="theme-color" content="#ffb000">
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
<button type="button" class="totop js-only" tabindex="-1" aria-hidden="true" %(totop)s>%(arrow)s</button>
%(footer)s
</body>
</html>
""" % {"ver": VER, "cfgv": (' data-i18n-cfg="%s"' % CFG_VER) if cfg_i18n else "", "iv": ICON_VER, "base": BASE, "active": active, "title": title, "desc": H(desc), "ogdesc": H(OG_DESC if title_key == "home.title" else desc), "canon": SITE + path,
       "ogt": H(og_title), "img": img, "imgmeta": img_meta, "headjs": HEAD_JS, "spec": SPEC, "cls": cls,
       "totop": ta("aria-label", "ui.totop"), "arrow": icon("arrow"), "header": header(active), "body": body, "footer": "" if active == "home" else footer()}
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


def sec(id_, title_key, body, code="", cls="", note="", targs=None, badge=""):
    return """<section class="sec %s" id="%s" aria-labelledby="h-%s">
  <h2 id="h-%s"><span class="sec-code" aria-hidden="true">%s</span>%s%s</h2>%s
  %s
</section>""" % (cls, id_, id_, id_, H(code), t(title_key, args=targs), badge, note, body)


def num(n):
    """Thousands split by a narrow no-break space: reads the same in English and French."""
    return "{:,}".format(n).replace(",", "\u202f")


def stat_items(m):
    """Rating, subscribers and downloads as the Workshop shows them; classified for unlisted mods."""
    st = m.get("stats")
    vals = [("st.rating", "rating", st and "%d%%" % st["rating"]),
            ("st.subs", "subs", st and num(st["subs"])),
            ("st.downloads", "dl", st and num(st["downloads"]))]
    return "".join('<span class="cstat" %s>%s%s<b>%s</b></span>' % (
        ta("title", key), icon(ico), t(key, "span", "sr"), H(v) if v else redact(3)) for key, ico, v in vals)


def wip_block(id_, code):
    """Projects still in development: not merged, not on the Workshop. Kept apart from Incoming on purpose."""
    # "Written" group: code not compiled yet; hidden while empty
    written = ('<h4>%s</h4><ul class="feat feat-plan">%s</ul>\n  ' % (t("ew.written_h"), tl("ew.written"))
               if SRC["en"]["ew.written"] else "")
    body = """<article class="proj">
  <h3>%s %s</h3>
  %s
  <h4>%s</h4><ul class="feat">%s</ul>
  %s<h4>%s</h4><ul class="feat feat-plan">%s</ul>
  %s
</article>""" % (t("ew.name"), t("ui.wip", "span", "chip chip-dev"), t("ew.p", "p"), t("ew.done_h"), tl("ew.done"),
                 written, t("ew.next_h"), tl("ew.next"), t("ew.insp", "p", "dim"))
    # Other work on Conflict PvE: no figures, no dates (Commandant's order)
    body += """
<div class="proj-row">
  <article class="proj proj-s"><h3>%s %s %s</h3>%s</article>
  <article class="proj proj-s"><h3>%s %s</h3>%s</article>
</div>""" % (t("wip.perf"), t("ui.wip", "span", "chip chip-dev"), t("wip.prio", "span", "chip chip-cur"), t("wip.perf_p", "p"),
             t("wip.wx"), t("wip.later", "span", "chip chip-standby"), t("wip.wx_p", "p"))
    return sec(id_, "wip.h", body, code, "sec-wip", t("wip.d", "p", "dim"))


def badge_inc():
    return t("ui.incoming", "span", "chip chip-inc")


# ---------------------------------------------------------------- components
def card(slug, lazy=True):
    m = MODS[slug]
    ver = H("v" + m["version"]) if m["version"] else redact(5)
    return """<a class="card" href="%s" data-cat="%s" data-fam="%s" data-tags="%s">
  <span class="card-img"><img src="%sassets/img/thumbs/%s.webp" width="480" height="270" alt=""%s decoding="async"><span class="card-scan" aria-hidden="true"></span></span>
  <span class="card-body">
    <span class="card-meta">%s<span class="mono dim">%s</span></span>
    <span class="card-title">%s</span>
    %s
    <span class="card-stats mono">%s</span>
    <span class="card-id mono" aria-hidden="true">ID %s</span>
  </span>
</a>""" % (url("workshop/%s/" % slug), CAT_OF[slug], " ".join(FAM_OF[slug]), H(" ".join(m["tags"])), BASE, slug, ' loading="lazy"' if lazy else "", chips(slug), ver,
           H(name(m)), t("m.%s.tag" % slug, "span", "card-tag"), stat_items(m), m["guid"] or redact(16))


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
    if slug in BUILDS:
        intro += t("deps.order", "p", "dim", {"b": BUILDS[slug][-1][0]})
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


_LOG_HEAD = re.compile(r"^[A-Z][A-Z /&-]*[A-Z](\s*\([^)]*\))?$")


def build_sec(m, bid, after, pub, code):
    """Complete changelog of one development build, under its permanent anchor #build-<id>."""
    slug = m["slug"]
    with open(os.path.join(TOOLS, "data", "builds", "%s-%s.txt" % (slug, bid)), encoding="utf-8") as f:
        txt = f.read()
    log, _, tail = txt.partition("=== SERVER MOD LIST")
    mods = tail[tail.index('"mods": ['):tail.index("\n]") + 2]
    # The server mod list of the build must be exactly the dependency list shown on the page.
    listed = re.findall(r'\{"modId": "([0-9A-F]{16})", "name": "([^"]*)"\}', mods)
    entries = dep_lists(m)[0]
    assert listed == [(e["id"], e["name"]) for e in entries], "build %s: mod list differs from mods.json deps" % bid
    assert ("Build: %s" % bid) in tail, "build %s: build line missing" % bid
    out, items = [], []
    def flush():
        if items:
            out.append("<ul>%s</ul>" % "".join("<li>%s</li>" % H(x) for x in items))
            del items[:]
    lines = log.strip().split("\n")
    if not lines[0].startswith("- "):
        out.append('<p class="mono dim">%s</p>' % H(lines[0]))  # title line, when the text has one
        lines = lines[1:]
    for line in lines:
        line = line.strip()
        if line.startswith("- "):
            items.append(line[2:])
            continue
        flush()
        if not line:
            continue
        out.append("<h3>%s</h3>" % H(line) if _LOG_HEAD.match(line) else "<p>%s</p>" % H(line))
    flush()
    pending = m["version"] == after
    if not pending:
        # Published: the version it went out as must be in the Workshop history of the mod.
        assert pub and pub in [v for v, _ in m["versions"]], "build %s: published version %s not in the history" % (bid, pub)
    see = ""
    if (slug, bid) in BUILD_SEE:
        s2, b2 = BUILD_SEE[(slug, bid)]
        see = '<p><a href="%s">%s</a></p>' % (url("workshop/%s/#build-%s" % (s2, b2)),
                                              t("log.see_cfg", "span", "", {"m": name(MODS[s2]), "b": b2}))
    body = """<blockquote class="quote-log" lang="en"><div class="log-txt log-full">%s</div></blockquote>
<details class="deps-table">
  <summary>%s</summary>
  <pre class="code" tabindex="0" lang="en"><code>%s</code></pre>
</details>
%s<p class="mono dim">Build: %s · <a href="#deps">%s</a></p>""" % (
        "".join(out), t("log.modlist", "span", "", {"n": len(listed)}), H(mods), see, H(bid), t("sec.deps"))
    note = (t("log.build_note", "p", "dim", {"b": bid, "v": after}) if pending
            else t("log.build_note_pub", "p", "dim", {"b": bid, "v": pub}))
    return sec("build-" + bid, "log.build_h", body, code, "sec-build", note, {"b": bid}, " " + badge_inc() if pending else "")


def credits_body(m):
    k = "m.%s." % m["slug"]
    body = t(k + "credits", "p")
    if (k + "adapted") not in SRC["en"] and m["slug"] in RHS_EULA_MODS:
        body += '\n<ul class="feat"><li><b>RHS - Status Quo</b> (Red Hammer Studios) — %s</li></ul>' % ext(RHS_EULA, "EULA")
    if (k + "adapted") in SRC["en"]:
        body += """
<h3>%s</h3>%s
<ul class="feat">%s<li><b>RHS - Status Quo</b> (Red Hammer Studios) — %s</li><li class="credit-req" lang="en">%s</li></ul>
<h3>%s</h3>
<ul class="feat">%s</ul>""" % (t(k + "adapted_h"), t(k + "adapted_p", "p"), tl(k + "adapted"), ext(RHS_EULA, "EULA"), H(SOUND_CREDIT),
                               t(k + "builtin_h"), tl(k + "builtin"))
    return body


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
        row("st.rating", m.get("stats") and "%d%% %s" % (m["stats"]["rating"], t("st.votes", "span", "dim", {"n": num(m["stats"]["votes"])})), True),
        row("st.subs", m.get("stats") and num(m["stats"]["subs"])),
        row("st.downloads", m.get("stats") and num(m["stats"]["downloads"])),
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
    build = BUILDS.get(slug, [None])[-1]
    pending = bool(build) and m["version"] == build[1]
    new_id = "incoming" if pending else "new"
    if build:
        # What's new in the latest build (the mod's own description), with a link to its full changelog.
        link = '<p><a href="#build-%s">%s</a></p>' % (build[0], t("log.build_link", "span", "", {"b": build[0]}))
        if pending:
            parts.append(sec("incoming", "sec.incoming", '<ul class="feat feat-inc">%s</ul>%s' % (tl(k + "new"), link), "02B", "sec-inc",
                             t("sec.incoming.d", "p", "dim", {"v": m["version"]})))
        else:
            note = t(k + "new_note", "p", "dim") if has("new_note") else ""
            parts.append(sec("new", "sec.new", '<ul class="feat">%s</ul>%s%s' % (tl(k + "new"), note, link), "02B"))
    elif has("inc"):
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
    if build:
        parts.append(build_sec(m, build[0], build[1], build[2], "06"))
    if m["changelog"]:
        parts.append(sec("changelog", "sec.changelog",
                         '%s<blockquote class="quote-log" lang="en"><p class="mono dim">v%s // %s</p><div class="log-txt">%s</div></blockquote>' % (
                             t("log.workshop_note", "p", "dim"), H(m["version"]), H(m["updated"]), H(m["changelog"].strip())), "06B" if build else "06"))
    if m["versions"]:
        lis = "".join('<li><span class="mono">v%s</span><span class="dim mono">%s</span>%s</li>' % (
            H(v), H(d), t("ui.current", "span", "chip chip-cur") if j == 0 else "") for j, (v, d) in enumerate(m["versions"]))
        parts.append(sec("versions", "sec.versions", '<ol class="vlist">%s</ol><p><a href="%schangelog/">%s</a></p>' % (lis, BASE, t("logp.h1")), "07"))
    if has("credits"):
        parts.append(sec("credits", "sec.credits", credits_body(m), "08"))

    toc = "".join('<a href="#%s">%s</a>' % (a, t(kk)) for a, kk in [
        ("overview", "sec.overview"), ("features", "sec.features")]
        + ([(new_id, "sec.incoming" if pending else "sec.new")] if build else [("incoming", "sec.incoming")] if has("inc") else [])
        + ([("setup", "sec.setup")] if has("setup") else []) + ([("admin", "sec.admin")] if has("admin") else [])
        + ([("commands", "sec.commands")] if slug in ("conflict-pve", "forest") else [])
        + [("deps", "sec.deps")] + ([("build-" + build[0], "log.build_toc")] if build else [])
        + ([("changelog", "sec.changelog")] if m["changelog"] else [])
        + ([("versions", "sec.versions")] if m["versions"] else [])
        + ([("credits", "sec.credits")] if has("adapted") else []))
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


# Home backdrop, same iconography as the link-preview card: combat feed (tools/homebg.py), radar sweep,
# track box on the lead helicopter, target reticle, viewfinder corners. Decorative only.
HOME_FX = """<div class="hfx" aria-hidden="true">
  <div class="hfx-radar"><i></i><b></b><b></b><b></b></div>
  <div class="hfx-scene">
    <div class="hfx-trk"><span>TRK 02 // HOSTILE AIR</span></div>
    <div class="hfx-tgt"><svg viewBox="-60 -60 120 120"><circle r="34"/><circle class="hfx-spin" r="46" stroke-dasharray="10 8"/>
      <path d="M0-58v18M0 40v18M-58 0h18M40 0h18M-4 0h8M0-4v8"/></svg><span>TGT LOCK<br>AZ 274<br>RNG 1.2K</span></div>
  </div>
  <div class="hfx-frame"><span class="hfx-rec"><i></i>REC</span><span class="hfx-ch">CON-01 // SECURE CHANNEL</span></div>
</div>
"""


# Public test server: its name as the in-game server browser shows it. Never an address or a port.
# LIVE_ID is its public listing on gamemonitoring.net (free, keyless, CORS open): site.js reads
# only online/offline, players and the reading time from it.
TEST_SERVER = "[EU] ARMA UKRAINE | PvE 1pp                   INDFORGE Forest Conflict (Belleau Wood)"
LIVE_ID = 17976932


def srv_strip():
    """Home strip in place of the old action buttons: the open public test server.
    Its name is plain text (readable without JS); the button copies the full in-game name, exact spacing kept."""
    short = " ".join(re.split(r"\s{2,}", TEST_SERVER)[0].split())
    return """<div class="srv" data-live="%s">
    <span class="srv-l"><span class="srv-ping" aria-hidden="true"><i></i><i></i></span>%s</span>
    <span class="srv-mid"><span class="srv-name">%s</span>%s</span>
    <button type="button" class="srv-copy js-only" data-copy-text="%s" data-copy-msg="srv.copied"><span class="copy-ico" aria-hidden="true"></span>%s</button>
  </div>""" % (LIVE_ID, t("srv.h", "span", "srv-k"), H(short), t("srv.meta", "span", "srv-meta"), H(TEST_SERVER), t("ui.copy", "span", "copy-lbl"))


def home():
    def row(d, sl, v):
        return '<li><a href="%s"><span class="mono amber">%s</span><span class="lt-name" title="%s">%s</span><span class="mono dim">v%s</span></a></li>' % (
            url("workshop/%s/" % sl), d, H(name(MODS[sl])), H(name(MODS[sl])), H(v))  # title: full name when the row cuts it with an ellipsis
    latest = "".join(row(d, sl, MODS[sl]["version"]) for d, sl in latest_updates(12))
    # Workshop telemetry: public figures of every listed mod (unlisted mods carry no stats)
    measured = [sl for sl in ORDER if MODS[sl].get("stats")]
    dl = sum(MODS[sl]["stats"]["downloads"] for sl in measured)
    votes = sum(MODS[sl]["stats"]["votes"] for sl in measured)
    rating = round(sum(MODS[sl]["stats"]["rating"] * MODS[sl]["stats"]["votes"] for sl in measured) / votes) if votes else 0
    top = sorted(measured, key=lambda sl: -MODS[sl]["stats"]["downloads"])
    peak = max(MODS[top[0]]["stats"]["downloads"], 1) if top else 1
    tele_rows = "".join(
        '<li><a href="%s"><span class="lt-name" title="%s">%s</span><span class="mono dim">%s</span><i class="tele-bar" style="--w:%.3f" aria-hidden="true"></i></a></li>' % (
            url("workshop/%s/" % sl), H(name(MODS[sl])), H(name(MODS[sl])), num(MODS[sl]["stats"]["downloads"]), MODS[sl]["stats"]["downloads"] / peak)
        for sl in top)
    kpi = "".join('<div><b class="mono">%s</b>%s</div>' % (v, t(k, "span")) for v, k in (
        (num(dl), "st.downloads"), (num(votes), "tele.votes"), ("%d %%" % rating, "st.rating")))
    stats = [
        (len(MODS), "home.stat_mods"), (len(THIRD_PARTY), "home.stat_deps"),
        (CFG_KEYS, "home.stat_keys"), (len(COMMANDS), "home.stat_cmds"),
    ]
    stat_html = "".join('<div class="stat"><b class="mono" data-count="%d">%d</b>%s</div>' % (n, n, t(k)) for n, k in stats)
    body = HOME_FX + """<div class="home wrap">
<section class="home-top">
  <div class="home-title">
    <h1 class="home-h1" data-scramble>INDFORGE<span> - Studio</span></h1>
    <p class="home-sub"><span class="sr">Arma Reforger</span><span class="home-sub-l" aria-hidden="true">%s</span></p>
  </div>
  %s
</section>
<div class="home-grid">
  <section class="panel hl tele" aria-labelledby="h-tele">
    <h2 class="panel-h" id="h-tele">%s</h2>%s
    <div class="tele-kpi">%s</div>
    <ol class="lt hl-list tele-list">%s</ol>
    <a class="more" href="%sworkshop/">%s%s</a>
  </section>
  <article class="dossier-card home-news" aria-labelledby="h-news">
    %s
    <p class="kicker"><span class="kicker-code" id="h-news">%s</span><span class="mono">%s</span></p>
    %s
    %s
    <p class="mono dim home-ref">%s %s · %s %s</p>
    <a class="btn btn-primary" href="%snews/">%s%s</a>
  </article>
  <section class="panel hl" aria-labelledby="h-latest">
    <h2 class="panel-h" id="h-latest">%s</h2>%s
    <ol class="lt hl-list">%s</ol>
    <a class="more" href="%sroadmap/">%s%s</a>
  </section>
</div>
<section class="stats home-stats" aria-label="Stats">%s</section>
</div>""" % (
        "".join("<i>%s</i>" % H(c) if c != " " else "<i></i>" for c in "ARMA REFORGER"),
        srv_strip(),
        t("tele.h"), t("tele.d", "p", "dim", {"d": STATS_DATE or ""}), kpi, tele_rows, BASE, t("tele.more"), icon("arrow"),
        t("ui.declassified", "span", "stamp", None, 'aria-hidden="true"'), t("home.news"), H(MODS["conflict-pve"]["updated"]),
        t("home.featured_t", "h2"), t("home.featured_p", "p"),
        t("intel.ref"), "IFG/HQ-" + redact(4) + "-26", t("ui.classified"), redact(12),
        BASE, t("home.featured_cta"), icon("arrow"),
        t("home.latest"), t("home.latest_d", "p", "dim"), latest, BASE, t("home.latest_more"), icon("arrow"),
        stat_html)
    page("", "home.title", body, "home", cls="p-home")


def ws_filters():
    def fam(value, key, n, checked=False):
        return ('<label class="wsf-fam"><input type="radio" name="wsf-fam" value="%s"%s>'
                '<span class="wsf-lbl">%s</span><i class="mono">%d</i></label>') % (value, " checked" if checked else "", t(key), n)
    fams = fam("all", "ui.all", len(ORDER), True) + "".join(fam(f, k, len(s)) for f, k, s in FAMILIES)
    tags = "".join(('<label class="wsf-tag"><input type="checkbox" value="%s"><span class="wsf-box" aria-hidden="true"></span>'
                    '<span class="wsf-lbl">%s</span><i class="mono">%d</i></label>') % (
        tg, t("tag." + tg), sum(tg in MODS[s]["tags"] for s in ORDER)) for tg in WS_TAGS)
    date = t("wsf.stats_date", "span", "dim", {"d": STATS_DATE}) if STATS_DATE else ""
    return """<div class="wsf js-only" id="wsf">
  <fieldset class="wsf-set"><legend class="wsf-leg mono">%s</legend><div class="wsf-fams">%s</div></fieldset>
  <fieldset class="wsf-set"><legend class="wsf-leg mono">%s <span class="dim">%s</span></legend><div class="wsf-tags">%s</div></fieldset>
  <div class="wsf-foot mono"><span aria-live="polite">%s</span>%s<button type="button" class="wsf-reset" disabled>%s</button></div>
</div>
<p class="wsf-empty mono" hidden>%s</p>""" % (
        t("wsf.family"), fams, t("wsf.tags"), t("wsf.tags_d"), tags,
        t("wsf.result", "span", "", {"n": len(ORDER), "t": len(ORDER)}, 'id="wsf-n"'), date, t("wsf.reset"), t("wsf.empty"))


def mods_index():
    body = phead("FILE-02", "mods.kicker", "mods.h1", "mods.lead", {"n": len(MODS)}) + \
        '<section class="wrap sec orbat">%s%s</section>' % (ws_filters(), orbat())
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
    if not mod["workshop"]:
        inc += " " + chips(f["mod"])
    return """<details class="cfg" id="%s">
  <summary><code>%s</code><span class="cfg-meta"><a href="%s">%s</a>%s%s</span></summary>
  %s
  <div class="tbl"><table class="table cfgt">
  <thead><tr><th scope="col">%s</th><th scope="col">%s</th><th scope="col">%s</th></tr></thead>
  <tbody>%s</tbody></table></div>
</details>""" % (cfg_anchor(f["profile"]), H(f["profile"]), url("workshop/%s/" % f["mod"]), H(name(mod)),
                 t("ui.rows1" if len(f["rows"]) == 1 else "ui.rows", "span", "mono dim", {"n": len(f["rows"])},
                   'data-i18n-plural="ui.rows"'), inc, notes,
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
%s
<article class="dossier">
  <header class="dossier-h">
    %s
    <p class="news-mod mono"><span>%s</span>%s</p>
    <p class="kicker"><span class="kicker-code">NEWS</span><span class="mono">%s</span></p>
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
        wip_block("wip", "EW"),
        t("intel.stamp", "span", "stamp", None, 'aria-hidden="true"'), t("news.mod"),
        "".join('<a class="news-chip" href="%s">%s%s</a>' % (url("workshop/%s/" % sl), H(name(MODS[sl])), icon("arrow")) for sl in ("conflict-pve", "forest")),
        H(MODS["conflict-pve"]["updated"]), t("intel.h1"), t("intel.lead", "p", "lead"),
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
    page("news/", "intel.title", body, "intel", cls="p-intel")


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
                     for k in ("operational", "standby", "unreleased", "restricted") if any(k in STATUS.get(s, ["operational"]) for s in ORDER))
    body = phead("SIT-06", "statusp.kicker", "statusp.h1", "statusp.lead") + """<div class="wrap">
%s
%s
%s
%s
</div>""" % (sec("pipeline", "statusp.pipeline", t("statusp.pipeline_p", "p", "", {"v": CPVE_VER}) +
                 '<ul class="feat feat-inc">%s</ul><p><a href="%sworkshop/conflict-pve/#incoming">INDFORGE - Conflict PvE</a></p>' % (tl("m.conflict-pve.inc"), BASE), "01", "sec-inc"),
             wip_block("wip", "01B"),
             sec("board", "statusp.board", t("statusp.game_now", "p", "dim", {"v": LATEST_GAME}) + """<div class="tbl"><table class="table board">
<thead><tr><th scope="col">%s</th><th scope="col">%s</th><th scope="col">%s</th><th scope="col">%s</th><th scope="col">%s</th></tr></thead>
<tbody>%s</tbody></table></div>""" % (t("statusp.col_mod"), t("statusp.col_state"), t("statusp.col_ver"), t("statusp.col_upd"),
                                      t("statusp.col_game"), "".join(rows)), "02"),
             sec("legend", "statusp.col_state", '<dl class="legend">%s</dl>' % legend, "03"))
    page("roadmap/", "statusp.title", body, "status")


def tips():
    total = sum(len(x[1]) for x in TIPS)

    def card(sec_n, i, tid, role, state, link):
        k = "tips.%s." % tid
        tags = t("tips.r." + role, "span", "trole trole-" + role,
                 attrs=ta("title", "tips.r.m_d") if role == "m" else "")
        if state == "inc":
            tags += badge_inc()
        x = '<p class="tip-x"><b>%s</b>%s</p>' % (t("tips.tip"), t(k + "x")) if (k + "x") in E else ""
        more = '<a class="tip-more mono" href="%s">%s%s</a>' % (url(link) if not link.startswith("#") else link, t("tips.more"), icon("arrow")) if link else ""
        return """<article class="tip" id="t-%s" data-role="%s">
  <header class="tip-h"><span class="tip-code mono" aria-hidden="true">T%02d.%02d</span><span class="tip-tags">%s</span></header>
  %s
  <ol class="tip-s">%s</ol>
  %s
  <footer class="tip-f">%s<label class="tip-ok js-only"><input type="checkbox" value="%s"><span class="tip-box" aria-hidden="true"></span>%s</label></footer>
</article>""" % (tid, role, sec_n, i, tags, t(k + "h", "h3"), tl(k + "s"), x, more, tid, t("tips.got"))

    secs, links = [], []
    for n, (sid, rows) in enumerate(TIPS, 1):
        cards = "".join(card(n, i, *r) for i, r in enumerate(rows, 1))
        if sid == "packs":
            img = '<span class="tsec-img tsec-ico" aria-hidden="true">%s</span>' % icon("subs")
            title, sub, page_a = t("tips.packs"), t("tips.packs_d", "p", "dim"), ""
            thumb = '<span class="tn-ico" aria-hidden="true">%s</span>' % icon("subs")
        else:
            m = MODS[sid]
            img = '<img class="tsec-img" src="%sassets/img/thumbs/%s.webp" width="480" height="270" alt="" loading="lazy" decoding="async">' % (BASE, sid)
            title, sub = H(name(m)), t("m.%s.tag" % sid, "p", "dim")
            page_a = '<a class="tsec-link mono" href="%s">%s%s</a>' % (url("workshop/%s/" % sid), t("tips.page"), icon("arrow"))
            thumb = '<img src="%sassets/img/thumbs/%s.webp" width="48" height="27" alt="" loading="lazy" decoding="async">' % (BASE, sid)
        # each mod opens like a new file: a dashed cut line, then a banner over the mod's own picture
        sep = '<div class="tsep" aria-hidden="true"><span class="tsep-cut">&#9986;&#xFE0E;</span><b class="mono">T%02d / %02d</b></div>' % (n, len(TIPS)) if n > 1 else ""
        bg = ' style="--tbg:url(\'%sassets/img/thumbs/%s.webp\')"' % (BASE, sid) if sid != "packs" else ""
        secs.append("""<section class="tsec" id="%s" aria-labelledby="h-%s">%s
  <header class="tsec-h"%s>
    <span class="tsec-fig">%s</span>
    <div class="tsec-t"><p class="tsec-k mono" aria-hidden="true"><span class="sec-code">T%02d</span>MOD %02d / %02d</p><h2 id="h-%s">%s</h2>%s</div>
    <div class="tsec-side"><span class="tsec-p js-only" aria-hidden="true"><span class="tsec-n mono"><b>0</b> / %d</span><span class="tsec-meter"><i></i></span></span>%s</div>
  </header>
  <div class="tips">%s</div>
</section>""" % (sid, sid, sep, bg, img, n, n, len(TIPS), sid, title, sub, len(rows), page_a, cards))
        links.append('<a href="#%s" data-tsec="%s">%s<span class="tn-name">%s</span><i class="mono">%d</i></a>' % (sid, sid, thumb, title, len(rows)))

    roles = ('<label class="seg"><input type="radio" name="tip-role" value="all" checked><span>%s</span></label>' % t("tips.r.all")
             + "".join('<label class="seg"><input type="radio" name="tip-role" value="%s"><span>%s</span></label>' % (r, t(k)) for r, k in TIP_ROLES))
    bar = """<div class="tipbar js-only" id="tipbar">
  <div class="tip-cur" aria-hidden="true"><span class="tip-cur-img"></span><span class="sec-code"></span><b></b></div>
  <fieldset class="tip-roles"><legend class="mono">%s</legend><div class="segs">%s</div></fieldset>
  <div class="tip-prog">
    <span class="tip-rank"><small class="mono">%s</small>%s</span>
    <span class="tip-meter" aria-hidden="true"><i id="tip-bar"></i></span>
    <span class="mono" aria-live="polite">%s</span>
  </div>
  <div class="tip-act"><label class="tip-hide"><input type="checkbox" id="tip-hide"><span class="tip-box" aria-hidden="true"></span>%s</label><button type="button" class="wsf-reset" id="tip-reset" disabled>%s</button></div>
</div>""" % (t("tips.role"), roles, t("tips.rank_l"), t("tips.rank.0", "b", "", None, 'id="tip-rank"'),
             t("tips.prog", "span", "", {"n": 0, "t": total}, 'id="tip-n"'), t("tips.hide"), t("tips.reset"))
    body = """<div class="tips-page"%s>%s
<div class="wrap tipgrid">
  <nav class="tipnav" aria-label="Mods"><h2 class="panel-h">%s</h2>%s</nav>
  <div class="tipmain">%s%s%s<p class="tip-empty mono" hidden>%s</p></div>
</div></div>""" % (' lang="fr"' if TIPS_FR_ONLY else "", phead("TIP-03", "tips.kicker", "tips.h1", "tips.lead"),
                   t("tips.mods"), "".join(links), bar, t("tips.note", "p", "note"), "".join(secs), t("tips.empty"))
    page("tips/", "tips.title", body, "tips", cls="p-tips")


def about():
    roster = [("Volmog_0", "about.r_volmog"), ("Unknown Soldiers", "about.r_soldiers"),
              ("Captain Valaaks", "about.r_valaaks")]
    ros = "".join('<li class="op"><span><b>%s</b>%s<span class="mono dim">CLR %s</span></span></li>' % (
        H(n), t(k, "span", "op-role"), redact(5)) for n, k in roster)
    body = phead("PER-07", "about.kicker", "about.h1", "about.lead").replace('class="phead wrap"', 'class="phead wrap phead-c"') + """<div class="wrap docgrid nogrid">
<div class="docmain">
%s %s %s %s %s
</div></div>""" % (
        sec("unit", "about.unit", t("about.unit_p", "p", "lead2") + t("about.giants", "p"), "01"),
        sec("roster", "about.roster", t("about.roster_d", "p", "dim") + '<ul class="roster">%s</ul>' % ros, "02"),
        sec("doctrine", "about.doctrine", '<ul class="feat">%s</ul>' % tl("about.d"), "03"),
        sec("theatres", "about.theatres", '<ul class="feat">%s</ul>' % tl("about.th"), "04"),
        sec("communities", "about.communities", '<ul class="feat">%s</ul>' % tl("about.c"), "05"))
    page("about/", "about.title", body, "about")


def e404():
    body = """<section class="wrap e404">
  <div class="noise" aria-hidden="true"></div>
  <p class="kicker"><span class="kicker-code">ERR-404</span>%s</p>
  <h1 data-scramble>%s</h1>
  %s
  <p class="mono dim e404-freq" aria-hidden="true">FREQ <span class="e404-fv">███.███</span> MHz // <span class="e404-car">NO CARRIER</span></p>
  <a class="btn btn-primary" href="%s">%s%s</a>
  <div class="scan js-only" data-state="search">
    <div class="scan-h"><span class="scan-t">%s</span><span class="scan-band">%s</span></div>
    <div class="scan-scope"><canvas class="scan-cv" aria-hidden="true"></canvas><span class="scan-lock" aria-hidden="true">LOCK</span></div>
    <div class="scan-row">
      <span class="scan-f"><b>--.---</b> MHz</span>
      <span class="scan-m" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i><i></i></span>
      <span class="scan-st" role="status" aria-live="polite">%s</span>
    </div>
    <div class="scan-dial">
      <button type="button" class="scan-b" data-step="-1" %s>&#9664;</button>
      <input type="range" class="scan-r" min="0" max="2319" step="1" value="0" %s>
      <button type="button" class="scan-b" data-step="1" %s>&#9654;</button>
    </div>
    <div class="scan-foot">%s<button type="button" class="scan-snd" aria-pressed="false">%s<b class="scan-snd-v">OFF</b></button></div>
    <div class="scan-msg" hidden></div>
  </div>
</section>""" % (t("e404.title"), t("e404.h1"), t("e404.p", "p", "lead"), BASE, icon("back"), t("e404.cta"),
                 t("e404.scan"), t("e404.band"), t("e404.st_search"), ta("aria-label", "e404.down"), ta("aria-label", "e404.dial"),
                 ta("aria-label", "e404.up"), t("e404.hint", "span", "scan-hint"), t("e404.sound"))
    page("404.html", "e404.title", body, "404")


def search_index():
    items = [{"k": "page", "t": key, "tk": 1, "u": url(p)} for p, key, _ in NAV]
    for s in ORDER:
        m = MODS[s]
        it = {"k": "mod", "t": name(m), "s": "m.%s.tag" % s, "x": "%s %s %s" % (m["guid"] or "", s, " ".join(m["tags"])), "u": url("workshop/%s/" % s),
              "c": CAT_OF[s]}  # c: family, read by the SPARKS assistant (site.js)
        if m["guid"]:
            it["w"] = WORKSHOP + m["guid"]  # official Workshop page (none for an unlisted mod)
        items.append(it)
    for s, builds in BUILDS.items():
        for bid, _after, _pub in builds:
            items.append({"k": "page", "t": "%s · build %s" % (name(MODS[s]), bid), "s": "log.build_toc",
                          "x": "%s changelog %s" % (bid, s), "u": url("workshop/%s/#build-%s" % (s, bid))})
    for cmd, key, _ in COMMANDS:
        items.append({"k": "cmd", "t": cmd.split("\n")[0], "s": key, "u": url("admins/#cmds")})
    for f in CONFIGS:
        items.append({"k": "cfg", "t": f["profile"], "x": " ".join(r["key"] for r in f["rows"]), "u": url("admins/#" + cfg_anchor(f["profile"]))})
    for a in ("hq", "doctrine", "fires", "drones", "light", "plans", "ambush", "air", "weather", "night", "radio", "base", "guide"):
        items.append({"k": "page", "t": "intel." + a, "tk": 1, "s": "intel.title", "u": url("news/#" + a)})
    for _sid, rows in TIPS:
        for tid, _r, _s, _l in rows:
            items.append({"k": "page", "t": "tips.%s.h" % tid, "tk": 1, "s": "tips.title", "u": url("tips/#t-" + tid), "m": _sid})
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
    """Pages that moved keep their old address: /mods/ -> /workshop/, /intel/ -> /news/, /status/ -> /roadmap/."""
    tpl = ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><title>INDFORGE - Studio</title>\n'
           '<meta name="robots" content="noindex"><link rel="canonical" href="%(abs)s">\n'
           '<meta http-equiv="refresh" content="0; url=%(rel)s">\n'
           '<script>location.replace("%(rel)s" + location.hash)</script></head>\n'
           '<body style="background:#06080a;color:#ffb000;font-family:monospace"><p><a href="%(rel)s" style="color:#ffb000">%(rel)s</a></p></body></html>\n')
    for old, new in [("mods/", "workshop/"), ("intel/", "news/"), ("status/", "roadmap/")] + [("mods/%s/" % s_, "workshop/%s/" % s_) for s_ in ORDER]:
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
            {"name": E["nav.intel"], "url": BASE + "news/", "icons": icon192},
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
    tips()
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
