from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET

from PIL import Image


PLUGIN_ROOT = Path(__file__).resolve().parents[2]
ICON_ROOT = PLUGIN_ROOT / "assets" / "icons"
MASTER_ROOT = ICON_ROOT / "masters"
OVERLAY_ROOT = ICON_ROOT / "state-overlays"
GENERATED_ROOT = ICON_ROOT / "generated"
GENERATOR_PATH = PLUGIN_ROOT / "tools" / "icons" / "generate_icons.py"

SPEC = importlib.util.spec_from_file_location("generate_icons", GENERATOR_PATH)
assert SPEC is not None and SPEC.loader is not None
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)

SVG = "{http://www.w3.org/2000/svg}"
EXPECTED_KEYS = set(GENERATOR.ACTION_KEYS)


def file_names(path: Path) -> set[str]:
    return {item.stem for item in path.glob("*.svg")}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def child_geometry(root: ET.Element) -> tuple[bytes, ...]:
    container = root[0] if len(root) == 1 and root[0].tag == f"{SVG}g" else root
    return tuple(ET.tostring(child) for child in container)


class IconMasterContracts(unittest.TestCase):
    def test_exactly_nine_semantic_masters_exist(self) -> None:
        self.assertEqual(file_names(MASTER_ROOT), EXPECTED_KEYS)

    def test_masters_are_current_color_64_square_monoline_svg(self) -> None:
        allowed_elements = {f"{SVG}svg", f"{SVG}path", f"{SVG}rect", f"{SVG}circle"}
        forbidden_attributes = {"style", "class", "id", "href"}
        for key in GENERATOR.ACTION_KEYS:
            with self.subTest(key=key):
                root = ET.parse(MASTER_ROOT / f"{key}.svg").getroot()
                self.assertEqual(root.tag, f"{SVG}svg")
                self.assertEqual(root.attrib["width"], "64")
                self.assertEqual(root.attrib["height"], "64")
                self.assertEqual(root.attrib["viewBox"], "0 0 64 64")
                self.assertEqual(root.attrib["fill"], "none")
                self.assertEqual(root.attrib["stroke"], "currentColor")
                self.assertEqual(root.attrib["stroke-width"], "3.6")
                self.assertEqual(root.attrib["stroke-linecap"], "round")
                self.assertEqual(root.attrib["stroke-linejoin"], "round")
                self.assertTrue(
                    all(element.tag in allowed_elements for element in root.iter())
                )
                self.assertFalse(
                    any(
                        forbidden_attributes & element.attrib.keys()
                        for element in root.iter()
                    )
                )
                text = (MASTER_ROOT / f"{key}.svg").read_text(encoding="utf-8")
                self.assertNotIn("<text", text)
                self.assertNotIn("opacity=", text)
                self.assertNotIn("#", text)

    def test_every_master_has_unique_geometry(self) -> None:
        hashes = {sha256(path) for path in MASTER_ROOT.glob("*.svg")}
        self.assertEqual(len(hashes), len(GENERATOR.ACTION_KEYS))


class ProjectionContracts(unittest.TestCase):
    def test_all_semantic_export_sets_are_complete(self) -> None:
        self.assertEqual(file_names(GENERATED_ROOT / "ring" / "normal"), EXPECTED_KEYS)
        self.assertEqual(
            file_names(GENERATED_ROOT / "ring" / "unavailable"), EXPECTED_KEYS
        )
        self.assertEqual(file_names(GENERATED_ROOT / "picker"), EXPECTED_KEYS)

    def test_ring_exports_are_black_and_geometry_preserving(self) -> None:
        for key in GENERATOR.ACTION_KEYS:
            with self.subTest(key=key):
                normal = ET.parse(
                    GENERATED_ROOT / "ring" / "normal" / f"{key}.svg"
                ).getroot()
                unavailable = ET.parse(
                    GENERATED_ROOT / "ring" / "unavailable" / f"{key}.svg"
                ).getroot()
                self.assertEqual(normal.attrib["stroke"], "#171717")
                self.assertEqual(unavailable.attrib["stroke"], "#171717")
                self.assertEqual(normal[0].attrib, {"opacity": "1"})
                self.assertEqual(unavailable[0].attrib, {"opacity": "0.38"})
                self.assertEqual(child_geometry(normal), child_geometry(unavailable))

    def test_picker_exports_are_transparent_single_black(self) -> None:
        for key in GENERATOR.ACTION_KEYS:
            with self.subTest(key=key):
                root = ET.parse(GENERATED_ROOT / "picker" / f"{key}.svg").getroot()
                self.assertEqual(root.attrib["fill"], "none")
                self.assertEqual(root.attrib["stroke"], "#000000")
                self.assertNotIn("opacity", root.attrib)
                self.assertNotIn("#FFFFFF", ET.tostring(root, encoding="unicode"))

    def test_state_projection_inputs_are_explicit_and_separate(self) -> None:
        projection = json.loads(
            (ICON_ROOT / "state-projections.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            projection,
            {
                "normal": {"opacity": 1.0, "overlay": None, "transient": False},
                "persistent_unavailable": {
                    "opacity": 0.38,
                    "overlay": None,
                    "transient": False,
                },
                "selection_race_not_dispatched": {
                    "opacity": 0.38,
                    "overlay": "not_dispatched_race",
                    "transient": True,
                },
                "dispatch_requested": {
                    "opacity": 1.0,
                    "overlay": "dispatch_requested",
                    "transient": True,
                },
                "dispatch_failed": {
                    "opacity": 1.0,
                    "overlay": "dispatch_failed",
                    "transient": True,
                },
                "outcome_unknown": {
                    "opacity": 1.0,
                    "overlay": "outcome_unknown",
                    "transient": True,
                },
            },
        )
        expected_overlays = {
            value["overlay"]
            for value in projection.values()
            if value["overlay"] is not None
        }
        self.assertEqual(file_names(OVERLAY_ROOT), expected_overlays)
        for path in OVERLAY_ROOT.glob("*.svg"):
            root = ET.parse(path).getroot()
            self.assertEqual(root.attrib["viewBox"], "0 0 64 64")
            self.assertEqual(root.attrib["stroke"], "currentColor")
            self.assertNotIn("<text", path.read_text(encoding="utf-8"))

    def test_approve_and_decline_are_absent(self) -> None:
        for path in ICON_ROOT.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".svg", ".json"}:
                continue
            text = path.read_text(encoding="utf-8").lower()
            self.assertNotIn("approve", text, path)
            self.assertNotIn("decline", text, path)


class RasterAndReviewContracts(unittest.TestCase):
    def test_plugin_icon_is_rgba_256_and_inside_safe_area(self) -> None:
        path = GENERATED_ROOT / "plugin" / "Icon256x256.png"
        with Image.open(path) as image:
            self.assertEqual(image.size, (256, 256))
            self.assertEqual(image.mode, "RGBA")
            alpha = image.getchannel("A")
            bounds = alpha.getbbox()
            self.assertIsNotNone(bounds)
            assert bounds is not None
            self.assertGreaterEqual(bounds[0], 32)
            self.assertGreaterEqual(bounds[1], 32)
            self.assertLessEqual(bounds[2], 224)
            self.assertLessEqual(bounds[3], 224)
            self.assertEqual(image.getpixel((0, 0))[3], 0)
            self.assertEqual(image.getpixel((128, 50))[:3], (255, 255, 255))
            self.assertTrue(
                any(
                    r < 30 and g < 30 and b < 30 and a > 245
                    for r, g, b, a in image.get_flattened_data()
                )
            )

    def test_plugin_icon_uses_independent_codexr_brand_master(self) -> None:
        brand = (GENERATOR.ICON_ROOT / "brand" / "codexr.svg").read_text()
        generated = (GENERATED_ROOT / "plugin" / "Icon256x256.svg").read_text()
        self.assertEqual(brand, generated)
        manifest = json.loads((GENERATED_ROOT / "generation-manifest.json").read_text())
        self.assertEqual(
            GENERATOR.sha256(GENERATOR.ICON_ROOT / "brand" / "codexr.svg"),
            manifest["sourceSha256"]["brand/codexr.svg"],
        )
        self.assertNotIn("<text", generated)
        self.assertNotEqual(
            GENERATOR.svg_inner(MASTER_ROOT / "new_chat.svg"),
            GENERATOR.svg_inner(GENERATOR.ICON_ROOT / "brand" / "codexr.svg"),
        )

    def test_review_sheets_have_locked_actual_density(self) -> None:
        expected_sizes = {
            "ring-light": (1600, 500),
            "ring-dark": (1600, 500),
            "picker": (1600, 390),
            "state-projections": (1200, 245),
        }
        for name, size in expected_sizes.items():
            with self.subTest(name=name):
                svg_text = (GENERATED_ROOT / "review" / f"{name}.svg").read_text(
                    encoding="utf-8"
                )
                with Image.open(GENERATED_ROOT / "review" / f"{name}.png") as image:
                    self.assertEqual(image.size, size)
                if name.startswith("ring-"):
                    self.assertIn("82 px slot / 54 px glyph", svg_text)
                    self.assertEqual(svg_text.count('r="41"'), 18)
                elif name == "picker":
                    self.assertIn("46 px glyph", svg_text)

    def test_manifest_covers_every_generated_output(self) -> None:
        manifest_path = GENERATED_ROOT / "generation-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["actionKeys"], list(GENERATOR.ACTION_KEYS))
        output_files = {
            str(path.relative_to(GENERATED_ROOT))
            for path in GENERATED_ROOT.rglob("*")
            if path.is_file() and path != manifest_path
        }
        self.assertEqual(set(manifest["outputSha256"]), output_files)
        for relative, expected_hash in manifest["outputSha256"].items():
            self.assertEqual(sha256(GENERATED_ROOT / relative), expected_hash)

    def test_checked_in_outputs_are_deterministic(self) -> None:
        result = subprocess.run(
            [sys.executable, str(GENERATOR_PATH), "--check"],
            cwd=PLUGIN_ROOT.parent,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Icon outputs are deterministic", result.stdout)


if __name__ == "__main__":
    unittest.main()
