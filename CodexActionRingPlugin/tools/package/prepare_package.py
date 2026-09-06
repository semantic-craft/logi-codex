#!/usr/bin/env python3
"""Project semantic assets into the generated Logitech package structure."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "src" / "package"
ICON_ROOT = ROOT / "assets" / "icons" / "generated"
HAPTIC_ROOT = ROOT / "assets" / "haptics"
PRIMARY_NAMESPACE = "Loupedeck.CodexActionRingPlugin.Logitech.Primary"

MAPPINGS = (
    ("next_attention", f"{PRIMARY_NAMESPACE}.NextAttentionCommand", None),
    ("view_activity", f"{PRIMARY_NAMESPACE}.ViewActivityCommand", None),
    ("new_chat", f"{PRIMARY_NAMESPACE}.NewChatCommand", None),
    ("quick_chat", f"{PRIMARY_NAMESPACE}.QuickChatCommand", None),
    ("side_chat", f"{PRIMARY_NAMESPACE}.SideChatCommand", None),
    ("recently_viewed", f"{PRIMARY_NAMESPACE}.RecentlyViewedCommand", None),
    ("copy_deep_link", f"{PRIMARY_NAMESPACE}.CopyDeepLinkCommand", None),
    ("dictation", f"{PRIMARY_NAMESPACE}.DictationCommand", None),
)


def target_name(action_class: str, parameter: str | None) -> str:
    suffix = f"___{parameter}" if parameter else ""
    return f"{action_class}{suffix}.svg"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_contract() -> None:
    semantic_keys = [entry[0] for entry in MAPPINGS]
    expected_keys = {
        "next_attention",
        "view_activity",
        "new_chat",
        "quick_chat",
        "side_chat",
        "recently_viewed",
        "copy_deep_link",
        "dictation",
    }
    if len(semantic_keys) != 8 or set(semantic_keys) != expected_keys:
        raise SystemExit(
            "action mapping must contain exactly the eight product actions"
        )

    primary_source = (
        ROOT / "src" / "Logitech" / "Primary" / "PrimaryActions.cs"
    ).read_text()
    for _, action_class, _ in MAPPINGS:
        class_name = action_class.rsplit(".", 1)[-1]
        if not re.search(
            rf"public\s+sealed\s+class\s+{re.escape(class_name)}\b", primary_source
        ):
            raise SystemExit(f"mapped SDK action class is missing: {action_class}")

    for semantic_key, _, _ in MAPPINGS:
        for source in (
            ICON_ROOT / "ring" / "normal" / f"{semantic_key}.svg",
            ICON_ROOT / "picker" / f"{semantic_key}.svg",
        ):
            if not source.is_file():
                raise SystemExit(f"missing semantic icon source: {source}")

    manifest = (PACKAGE / "metadata" / "LoupedeckPackage.yaml").read_text()
    required_manifest_lines = (
        "type: plugin4",
        "name: CodexActionRing",
        "displayName: Codex Action Ring",
        "pluginFileName: CodexActionRingPlugin.dll",
        "version: 0.1.5",
        "pluginFolderMac: bin",
        "    - LoupedeckExtendedFamily",
        "    - HasApplication",
        "    - HasHapticMapping",
        "backgroundColor: 4294967295",
    )
    missing = [line for line in required_manifest_lines if line not in manifest]
    if missing:
        raise SystemExit(f"manifest is missing locked lines: {missing}")
    if re.search(r"^pluginFolderWin:", manifest, re.MULTILINE):
        raise SystemExit("Windows package output must stay disabled")


def project_assets() -> dict[str, object]:
    validate_contract()
    for directory_name in ("actionicons", "actionsymbols", "events"):
        directory = PACKAGE / directory_name
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True)

    (PACKAGE / "events" / "extra").mkdir(parents=True)
    mapped: list[dict[str, str | None]] = []
    for semantic_key, action_class, parameter in MAPPINGS:
        filename = target_name(action_class, parameter)
        ring_source = ICON_ROOT / "ring" / "normal" / f"{semantic_key}.svg"
        picker_source = ICON_ROOT / "picker" / f"{semantic_key}.svg"
        shutil.copyfile(ring_source, PACKAGE / "actionicons" / filename)
        shutil.copyfile(picker_source, PACKAGE / "actionsymbols" / filename)
        mapped.append(
            {
                "semanticKey": semantic_key,
                "actionClass": action_class,
                "parameter": parameter,
                "packageFilename": filename,
                "ringSha256": sha256(ring_source),
                "pickerSha256": sha256(picker_source),
            }
        )

    shutil.copyfile(
        ICON_ROOT / "plugin" / "Icon256x256.png",
        PACKAGE / "metadata" / "Icon256x256.png",
    )
    shutil.copyfile(
        HAPTIC_ROOT / "DefaultEventSource.yaml",
        PACKAGE / "events" / "DefaultEventSource.yaml",
    )
    shutil.copyfile(
        HAPTIC_ROOT / "extra" / "eventMapping.yaml",
        PACKAGE / "events" / "extra" / "eventMapping.yaml",
    )

    report = {
        "mappingCount": len(mapped),
        "actionIconCount": len(list((PACKAGE / "actionicons").glob("*.svg"))),
        "actionSymbolCount": len(list((PACKAGE / "actionsymbols").glob("*.svg"))),
        "mappings": mapped,
        "pluginIconSha256": sha256(PACKAGE / "metadata" / "Icon256x256.png"),
        "eventSourceSha256": sha256(PACKAGE / "events" / "DefaultEventSource.yaml"),
        "eventMappingSha256": sha256(
            PACKAGE / "events" / "extra" / "eventMapping.yaml"
        ),
    }
    (Path(__file__).with_name("action-map.json")).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    return report


def check_projected() -> dict[str, object]:
    validate_contract()
    expected_names = {
        target_name(action_class, parameter) for _, action_class, parameter in MAPPINGS
    }
    for directory_name, source_parts in (
        ("actionicons", ("ring", "normal")),
        ("actionsymbols", ("picker",)),
    ):
        directory = PACKAGE / directory_name
        actual_names = {path.name for path in directory.glob("*.svg")}
        if actual_names != expected_names:
            raise SystemExit(
                f"{directory_name} class-name set does not match the eight-action contract"
            )
        for semantic_key, action_class, parameter in MAPPINGS:
            source = ICON_ROOT.joinpath(*source_parts, f"{semantic_key}.svg")
            target = directory / target_name(action_class, parameter)
            if source.read_bytes() != target.read_bytes():
                raise SystemExit(
                    f"projected icon differs from semantic source: {target}"
                )

    expected_copies = (
        (
            ICON_ROOT / "plugin" / "Icon256x256.png",
            PACKAGE / "metadata" / "Icon256x256.png",
        ),
        (
            HAPTIC_ROOT / "DefaultEventSource.yaml",
            PACKAGE / "events" / "DefaultEventSource.yaml",
        ),
        (
            HAPTIC_ROOT / "extra" / "eventMapping.yaml",
            PACKAGE / "events" / "extra" / "eventMapping.yaml",
        ),
    )
    for source, target in expected_copies:
        if not target.is_file() or source.read_bytes() != target.read_bytes():
            raise SystemExit(f"package projection differs from source: {target}")

    event_source = (PACKAGE / "events" / "DefaultEventSource.yaml").read_text()
    event_mapping = (PACKAGE / "events" / "extra" / "eventMapping.yaml").read_text()
    source_names = set(
        re.findall(r"^\s+- name: ([A-Za-z_][A-Za-z0-9_]*)$", event_source, re.MULTILINE)
    )
    mapping_names = set(
        re.findall(r"^  ([A-Za-z_][A-Za-z0-9_]*):$", event_mapping, re.MULTILINE)
    )
    expected_events = {"DispatchRequested", "DispatchFailed", "SelectionRejected"}
    if source_names != expected_events or mapping_names != expected_events:
        raise SystemExit(
            "haptic source and mapping names must match the three locked events"
        )
    if event_mapping.count("DEFAULT:") != 3:
        raise SystemExit("every haptic event must have one DEFAULT mapping")

    return {
        "mappingCount": 8,
        "actionIconCount": 8,
        "actionSymbolCount": 8,
        "hapticEvents": sorted(expected_events),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = check_projected() if args.check else project_assets()
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
