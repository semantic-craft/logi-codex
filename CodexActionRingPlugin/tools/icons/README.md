# Icon generation

`generate_icons.py` treats the eleven SVG files in `assets/icons/masters/` as the geometry source of truth. It deterministically creates white Ring projections on the package’s neutral-gray Ring background, 38% unavailable projections, black picker symbols, the plugin icon, and review sheets under `assets/icons/generated/`.

Run from any directory:

```sh
python3 CodexActionRingPlugin/tools/icons/generate_icons.py
python3 CodexActionRingPlugin/tools/icons/generate_icons.py --check
python3 -m unittest discover -s CodexActionRingPlugin/tests/IconSystem -v
```

PNG rendering requires `rsvg-convert`. Tests additionally use Pillow to inspect RGBA dimensions and the plugin-icon safe area. Package class-name mapping and copying remain the responsibility of I09.

Neutral-gray theme: `#767676` Ring background and `#FFFFFF` action strokes. The plugin mark remains a white rounded-square terminal icon. Options+ owns Ring outlines, floating labels, and hover treatment; the review sheets show package-controlled colors only.

Options+ defaults SVG tint to white, independently of packaged strokes. The gray package background keeps new assignments visible. For existing overrides, set Background Color to `767676` and Icon Color to `FFFFFF` in Edit icon, then Apply to multiple with only Background Color and Icon Color selected.

Read-only regression check for a saved profile (does not replace visual verification):

```sh
python3 CodexActionRingPlugin/tools/icons/check_profile_visibility.py /path/to/ProfileInfo.json
```

This checks assigned Codex actions for visible images with at least 3:1 color contrast. Actions without saved overrides use the v0.1.11 gray package background and the observed white Options+ default tint.
