#!/usr/bin/env python3
"""Read-only check for Options+ white-on-white Codex action overrides."""

import argparse
import json
from pathlib import Path


PREFIX = "$CodexActionRing___"
WHITE = 0xFFFFFFFF


def assigned_actions(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "pressAction" and isinstance(child, str) and child.startswith(PREFIX):
                yield child
            else:
                yield from assigned_actions(child)
    elif isinstance(value, list):
        for child in value:
            yield from assigned_actions(child)


def luminance(color):
    channels = [(color >> shift & 255) / 255 for shift in (16, 8, 0)]
    linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in channels]
    return sum(v * weight for v, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


def check_profile(profile, default_background=0xFF767676):
    actions = sorted(set(assigned_actions(json.loads(profile.read_text()))))
    failures = []
    for action in actions:
        icon_path = profile.parent / "ActionIcons" / (action + ".ict")
        # Options+ defaults SVG tint to white, regardless of the SVG's stroke.
        icon = json.loads(icon_path.read_text()) if icon_path.exists() else {}
        background = icon.get("backgroundColor", default_background)
        images = [item for item in icon.get("items", []) if item.get("itemType") == "Image"]
        if not icon_path.exists():
            images = [{"imageColor": WHITE, "isVisible": True}]
        visible = False
        for item in images:
            foreground = item.get("imageColor", WHITE)
            hi, lo = sorted((luminance(foreground), luminance(background)), reverse=True)
            if item.get("isVisible", True) and foreground >> 24 and (hi + 0.05) / (lo + 0.05) >= 3:
                visible = True
        if not visible:
            failures.append(action.split(".")[-1])
    return len(actions), failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path, help="Options+ ProfileInfo.json")
    args = parser.parse_args()
    count, failures = check_profile(args.profile)
    print(json.dumps({"assignedCodexActions": count, "lowContrastActions": failures}))
    return 1 if failures or count == 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
