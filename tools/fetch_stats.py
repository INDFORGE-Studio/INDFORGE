"""Refresh the public Workshop statistics of every listed mod in tools/data/mods.json.

Reads each mod's public Workshop page (no sign-in) and stores subscribers, downloads,
rating and vote count. Unlisted mods are never fetched: their statistics stay classified.
Run: python tools/fetch_stats.py, then python tools/build.py.
"""
import datetime
import json
import os
import re
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data", "mods.json")
URL = "https://reforger.armaplatform.com/workshop/%s"
NEXT = re.compile(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)


def page_data(guid):
    req = urllib.request.Request(URL % guid, headers={"User-Agent": "Mozilla/5.0 (site-stats)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode("utf-8")
    return json.loads(NEXT.search(html).group(1))["props"]["pageProps"]


def main():
    with open(DATA, encoding="utf-8") as f:
        data = json.load(f)
    for m in data["mods"]:
        if m.get("unlisted") or not m.get("guid"):
            m.pop("stats", None)
            continue
        pp = page_data(m["guid"])
        a = pp["asset"]
        m["stats"] = {
            "subs": int(a.get("subscriberCount") or 0),
            "downloads": int((pp.get("getAssetDownloadTotal") or {}).get("total") or 0),
            "rating": round(float(a.get("averageRating") or 0) * 100),
            "votes": int(a.get("ratingCount") or 0),
        }
        print(m["slug"], m["stats"])
    data["stats_date"] = datetime.date.today().isoformat()
    with open(DATA, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")


if __name__ == "__main__":
    main()
