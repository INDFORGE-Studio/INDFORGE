# INDFORGE - Studio — Arma Reforger

Public documentation site of the INDFORGE - Studio mods for Arma Reforger:
<https://indforge-studio.github.io/INDFORGE/>

Every mod has a permanent page at `/INDFORGE/workshop/<slug>/` (old `/mods/<slug>/` links redirect there) with its features,
admin settings and a ready-to-paste dependency list (`server.json` block and
`Name - ID` list).

## Layout

| Path | Content |
|---|---|
| `index.html`, `about/`, `workshop/`, `tips/`, `admins/`, `news/`, `changelog/`, `roadmap/`, `404.html`, `manifest.webmanifest`, `sitemap.xml` | Generated pages (committed, served as is by GitHub Pages) |
| `mods/`, `intel/`, `status/` | Redirects from old addresses to `workshop/`, `news/` and `roadmap/` |
| `assets/css/site.css`, `assets/js/site.js` | Hand-written style and interactive layer (no framework) |
| `assets/i18n/*.json`, `assets/search.json` | Generated translation dictionaries and search index |
| `assets/img/` | Mod images (WebP), icons, style emblems (`fs/`), preview image |
| `tools/build.py` | Generator |
| `tools/emblems.py`, `tools/logo.py`, `tools/og.py`, `tools/fetch_stats.py` | Style emblems, logo and icons, preview image, Workshop figures |
| `tools/data/*.json` | Mod data (Workshop pages and project files) and server settings reference |
| `tools/i18n/*.json` | Source texts: `en` (source), `fr`, `de`, `es`, `it`, `pl`, `uk` |
| `tools/i18n/tips/*.json` | Texts of the Tips page (how to use each feature). Written in French first: a language without its own file shows the French text |
| `tools/i18n/cfg/*.json` | Translations of the config help texts shown on the admin page. `en.json` is regenerated from `configs.json`; the config files themselves stay English |

## Build

```
python tools/build.py
```

Python 3.8+, standard library only. Pages work without JavaScript; the script
only adds language switching, search, copy buttons and the HUD effects.

Fan-made community mods for Arma Reforger. Arma Reforger is a trademark of its
owner; this site is not affiliated with or endorsed by Bohemia Interactive.
