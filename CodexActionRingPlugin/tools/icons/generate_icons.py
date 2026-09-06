#!/usr/bin/env python3
"""Generate deterministic Codex Action Ring icon projections and review sheets."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


PLUGIN_ROOT = Path(__file__).resolve().parents[2]
ICON_ROOT = PLUGIN_ROOT / "assets" / "icons"
MASTER_ROOT = ICON_ROOT / "masters"
OVERLAY_ROOT = ICON_ROOT / "state-overlays"
DEFAULT_OUTPUT = ICON_ROOT / "generated"

ACTION_KEYS = (
    "next_attention",
    "view_activity",
    "new_chat",
    "quick_chat",
    "side_chat",
    "recently_viewed",
    "copy_deep_link",
    "dictation",
)

DISPLAY_NAMES = {
    "next_attention": "Next Attention",
    "view_activity": "View Activity",
    "new_chat": "New Chat",
    "quick_chat": "Quick Chat",
    "side_chat": "Side Chat",
    "recently_viewed": "Recently Viewed",
    "copy_deep_link": "Copy Deep Link",
    "dictation": "Start Dictation",
}

SVG_INNER = re.compile(r"<svg\b[^>]*>(.*)</svg>\s*$", re.DOTALL)
ROOT_ATTRIBUTES = (
    'xmlns="http://www.w3.org/2000/svg" width="64" height="64" '
    'viewBox="0 0 64 64" fill="none" stroke="{color}" stroke-width="3.6" '
    'stroke-linecap="round" stroke-linejoin="round"'
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def svg_inner(path: Path) -> str:
    match = SVG_INNER.search(path.read_text(encoding="utf-8"))
    if match is None:
        raise ValueError(f"Cannot extract SVG geometry from {path}")
    return match.group(1).strip()


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8", newline="\n")


def projected_svg(inner: str, color: str, opacity: str | None = None) -> str:
    root = ROOT_ATTRIBUTES.format(color=color)
    if opacity is None:
        body = inner.replace("currentColor", color)
    else:
        indented = "\n".join(f"    {line}" for line in inner.splitlines())
        body = f'  <g opacity="{opacity}">\n{indented}\n  </g>'
    return f"<svg {root}>\n{body}\n</svg>\n"


def convert_svg(svg_path: Path, png_path: Path, width: int, height: int) -> None:
    executable = shutil.which("rsvg-convert")
    if executable is None:
        raise RuntimeError("rsvg-convert is required for deterministic PNG rendering")
    png_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            executable,
            "--width",
            str(width),
            "--height",
            str(height),
            "--keep-aspect-ratio",
            "--output",
            str(png_path),
            str(svg_path),
        ],
        check=True,
    )


def transformed_geometry(
    key: str, *, size: float, x: float, y: float, color: str, opacity: str = "1"
) -> str:
    scale = size / 64
    inner = svg_inner(MASTER_ROOT / f"{key}.svg").replace("currentColor", color)
    return (
        f'<g transform="translate({x:g} {y:g}) scale({scale:g})" fill="none" '
        f'stroke="{color}" stroke-width="3.6" stroke-linecap="round" '
        f'stroke-linejoin="round" opacity="{opacity}">{inner}</g>'
    )


def make_ring_sheet(theme: str) -> str:
    if theme == "light":
        host, ink, muted = "#FAFAFA", "#171717", "#696D70"
    else:
        host, ink, muted = "#111315", "#F3F3EF", "#A4A8AB"
    width, height = 1600, 500
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="{host}"/>',
        f'<text x="40" y="47" fill="{ink}" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="24" font-weight="700">Ring projections · {theme} host · 82 px slot / 54 px glyph</text>',
        f'<text x="1560" y="47" fill="{muted}" text-anchor="end" font-family="ui-monospace, monospace" font-size="13">NORMAL 100% · UNAVAILABLE 38%</text>',
    ]
    for index, key in enumerate(ACTION_KEYS):
        col, row = index % 8, index // 8
        cell_x, cell_y = 20 + col * 197, 76 + row * 205
        normal_x, unavailable_x, center_y = cell_x + 52, cell_x + 145, cell_y + 58
        for center_x, opacity in ((normal_x, "1"), (unavailable_x, "0.38")):
            parts.append(
                f'<circle cx="{center_x}" cy="{center_y}" r="41" fill="#FFFFFF" opacity="{opacity}"/>'
            )
            parts.append(
                transformed_geometry(
                    key,
                    size=54,
                    x=center_x - 27,
                    y=center_y - 27,
                    color="#171717",
                    opacity=opacity,
                )
            )
        label = html.escape(DISPLAY_NAMES[key])
        parts.extend(
            [
                f'<text x="{cell_x + 98}" y="{cell_y + 120}" fill="{ink}" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="14" font-weight="650">{label}</text>',
                f'<text x="{normal_x}" y="{cell_y + 145}" fill="{muted}" text-anchor="middle" font-family="ui-monospace, monospace" font-size="10">100%</text>',
                f'<text x="{unavailable_x}" y="{cell_y + 145}" fill="{muted}" text-anchor="middle" font-family="ui-monospace, monospace" font-size="10">38%</text>',
            ]
        )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def make_picker_sheet() -> str:
    width, height = 1600, 390
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="#F5F4F0"/>',
        '<text x="40" y="47" fill="#17191A" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="24" font-weight="700">Picker symbols · transparent single-black · 46 px glyph</text>',
    ]
    for index, key in enumerate(ACTION_KEYS):
        col, row = index % 8, index // 8
        cell_x, cell_y = 20 + col * 197, 75 + row * 150
        parts.append(
            f'<rect x="{cell_x + 37}" y="{cell_y}" width="122" height="92" rx="14" fill="#FFFFFF" stroke="#D7D2C8"/>'
        )
        parts.append(
            transformed_geometry(
                key, size=46, x=cell_x + 75, y=cell_y + 13, color="#000000"
            )
        )
        label = html.escape(DISPLAY_NAMES[key])
        parts.append(
            f'<text x="{cell_x + 98}" y="{cell_y + 119}" fill="#36393B" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="13" font-weight="650">{label}</text>'
        )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def make_state_sheet() -> str:
    states = (
        ("normal", "1", None),
        ("persistent unavailable", "0.38", None),
        ("race rejection", "0.38", "not_dispatched_race"),
        ("dispatch requested", "1", "dispatch_requested"),
        ("dispatch failed", "1", "dispatch_failed"),
        ("outcome unknown", "1", "outcome_unknown"),
    )
    width, height = 1200, 245
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="#F7F6F2"/>',
        '<text x="40" y="43" fill="#17191A" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="22" font-weight="700">Projection inputs · overlays remain separate from semantic masters</text>',
    ]
    for index, (label, opacity, overlay) in enumerate(states):
        center_x, center_y = 100 + index * 195, 115
        parts.append(f'<circle cx="{center_x}" cy="{center_y}" r="41" fill="#FFFFFF"/>')
        parts.append(
            transformed_geometry(
                "new_chat",
                size=54,
                x=center_x - 27,
                y=center_y - 27,
                color="#171717",
                opacity=opacity,
            )
        )
        if overlay is not None:
            overlay_inner = svg_inner(OVERLAY_ROOT / f"{overlay}.svg").replace(
                "currentColor", "#171717"
            )
            parts.append(
                f'<g transform="translate({center_x - 27:g} {center_y - 27:g}) scale({54 / 64:g})" fill="none" stroke="#171717" stroke-width="4" stroke-linecap="round" stroke-linejoin="round">{overlay_inner}</g>'
            )
        parts.append(
            f'<text x="{center_x}" y="185" fill="#36393B" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="13" font-weight="650">{html.escape(label)}</text>'
        )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def generate(output: Path) -> None:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    for key in ACTION_KEYS:
        inner = svg_inner(MASTER_ROOT / f"{key}.svg")
        write_text(
            output / "ring" / "normal" / f"{key}.svg",
            projected_svg(inner, "#171717", "1"),
        )
        write_text(
            output / "ring" / "unavailable" / f"{key}.svg",
            projected_svg(inner, "#171717", "0.38"),
        )
        write_text(output / "picker" / f"{key}.svg", projected_svg(inner, "#000000"))

    plugin_svg = (ICON_ROOT / "brand" / "codexr.svg").read_text(encoding="utf-8")
    plugin_svg_path = output / "plugin" / "Icon256x256.svg"
    write_text(plugin_svg_path, plugin_svg)
    convert_svg(plugin_svg_path, output / "plugin" / "Icon256x256.png", 256, 256)

    review_svgs = {
        "ring-light": make_ring_sheet("light"),
        "ring-dark": make_ring_sheet("dark"),
        "picker": make_picker_sheet(),
        "state-projections": make_state_sheet(),
    }
    review_sizes = {
        "ring-light": (1600, 500),
        "ring-dark": (1600, 500),
        "picker": (1600, 390),
        "state-projections": (1200, 245),
    }
    for name, svg in review_svgs.items():
        svg_path = output / "review" / f"{name}.svg"
        write_text(svg_path, svg)
        convert_svg(svg_path, output / "review" / f"{name}.png", *review_sizes[name])

    source_files = (
        sorted(MASTER_ROOT.glob("*.svg"))
        + sorted(OVERLAY_ROOT.glob("*.svg"))
        + [ICON_ROOT / "state-projections.json", ICON_ROOT / "brand" / "codexr.svg"]
    )
    output_files = sorted(path for path in output.rglob("*") if path.is_file())
    manifest = {
        "schemaVersion": 1,
        "actionKeys": list(ACTION_KEYS),
        "semanticExports": {
            "ringNormal": [f"ring/normal/{key}.svg" for key in ACTION_KEYS],
            "ringUnavailable": [f"ring/unavailable/{key}.svg" for key in ACTION_KEYS],
            "picker": [f"picker/{key}.svg" for key in ACTION_KEYS],
        },
        "stateProjectionInput": "state-projections.json",
        "pluginIcon": "plugin/Icon256x256.png",
        "reviewAssets": [f"review/{name}.png" for name in review_svgs],
        "sourceSha256": {
            str(path.relative_to(ICON_ROOT)): sha256(path) for path in source_files
        },
        "outputSha256": {
            str(path.relative_to(output)): sha256(path) for path in output_files
        },
    }
    write_text(
        output / "generation-manifest.json",
        json.dumps(manifest, indent=2, sort_keys=True),
    )


def compare_trees(expected: Path, actual: Path) -> list[str]:
    expected_files = {
        str(path.relative_to(expected)): sha256(path)
        for path in expected.rglob("*")
        if path.is_file()
    }
    actual_files = {
        str(path.relative_to(actual)): sha256(path)
        for path in actual.rglob("*")
        if path.is_file()
    }
    differences = []
    for relative in sorted(expected_files.keys() | actual_files.keys()):
        if expected_files.get(relative) != actual_files.get(relative):
            differences.append(relative)
    return differences


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify checked-in outputs are reproducible",
    )
    args = parser.parse_args()

    output = args.output.resolve()
    if args.check:
        if not output.exists():
            raise SystemExit(f"Missing generated output: {output}")
        with tempfile.TemporaryDirectory(prefix="codex-action-ring-icons-") as temp_dir:
            candidate = Path(temp_dir) / "generated"
            generate(candidate)
            differences = compare_trees(output, candidate)
        if differences:
            raise SystemExit("Generated icon outputs differ: " + ", ".join(differences))
        print(f"Icon outputs are deterministic ({len(ACTION_KEYS)} semantic keys).")
        return 0

    generate(output)
    print(f"Generated {len(ACTION_KEYS)} semantic icon sets in {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
