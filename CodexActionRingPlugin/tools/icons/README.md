# Icon generation

`generate_icons.py` treats the nine SVG files in `assets/icons/masters/` as the geometry source of truth. It deterministically creates black Ring projections on the package’s white Ring background, 38% unavailable projections, black picker symbols, the plugin icon, and review sheets under `assets/icons/generated/`.

Run from any directory:

```sh
python3 CodexActionRingPlugin/tools/icons/generate_icons.py
python3 CodexActionRingPlugin/tools/icons/generate_icons.py --check
python3 -m unittest discover -s CodexActionRingPlugin/tests/IconSystem -v
```

PNG rendering requires `rsvg-convert`. Tests additionally use Pillow to inspect RGBA dimensions and the plugin-icon safe area. Package class-name mapping and copying remain the responsibility of I09.

Paper-white theme (variant A): `#FFFFFF` Ring background, `#171717` action strokes, and a white rounded-square terminal mark with a light gray border. Options+ owns Ring outlines, floating labels, and hover treatment; the review sheets show package-controlled colors only.
