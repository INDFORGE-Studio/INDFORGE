# INDFORGE - Studio — Arma Reforger

Public documentation site of the INDFORGE - Studio mods for Arma Reforger:
<https://indforge-studio.github.io/INDFORGE/>

Every mod has a permanent page at `/INDFORGE/mods/<slug>/` with its features,
admin settings and a ready-to-paste dependency list (`server.json` block and
`Name - ID` list).

## Layout

| Path | Content |
|---|---|
| `index.html`, `about/`, `mods/`, `admins/`, `intel/`, `changelog/`, `status/`, `404.html`, `manifest.webmanifest`, `sitemap.xml` | Generated pages (committed, served as is by GitHub Pages) |
| `assets/css/site.css`, `assets/js/site.js` | Hand-written style and interactive layer (no framework) |
| `assets/i18n/*.json` | Generated translation dictionaries |
| `assets/img/` | WebP images |
| `tools/build.py` | Generator |
| `tools/data/*.json` | Mod data (Workshop pages and project files) and server settings reference |
| `tools/i18n/*.json` | Source texts: `en` (source), `fr`, `de`, `es`, `it`, `pl`, `uk` |

## Build

```
python tools/build.py
```

Python 3.8+, standard library only. Pages work without JavaScript; the script
only adds language switching, search, copy buttons and the HUD effects.

Fan-made community mods for Arma Reforger. Arma Reforger is a trademark of its
owner; this site is not affiliated with or endorsed by Bohemia Interactive.
