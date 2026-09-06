#!/usr/bin/env python3
"""Deterministic, read-only contract checks for the Codex Action Ring package."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable, Sequence


PLUGIN_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = PLUGIN_ROOT.parent
ARTIFACT = PLUGIN_ROOT / "artifacts" / "CodexActionRing_0_1_5.lplug4"
PACKAGE_REPORT = PLUGIN_ROOT / "artifacts" / "CodexActionRing_0_1_5.report.json"
PACKAGE_ROOT = PLUGIN_ROOT / "src" / "package"
ACTION_MAP = PLUGIN_ROOT / "tools" / "package" / "action-map.json"
PASS = "PASS"
FAIL = "FAIL"

PRIMARY_ORDER = (
    "NextAttention",
    "ViewActivity",
    "NewChat",
    "QuickChat",
    "SideChat",
    "RecentlyViewed",
    "CopyDeepLink",
    "Dictation",
)
ACTION_IDS = PRIMARY_ORDER
DISPATCH_RESULTS = (
    "NotDispatched",
    "DispatchRequested",
    "DispatchFailed",
    "OutcomeUnknown",
)
ACTION_FRAGMENTS = (
    'Shortcut(RingActionId.NextAttention, "next_attention", "Next Attention", Command | Option, DesktopKey.A)',
    'Shortcut(RingActionId.ViewActivity, "view_activity", "View Activity", Command | Option, DesktopKey.U)',
    'DeepLink(RingActionId.NewChat, "new_chat", "New Chat", "codex://threads/new")',
    'Shortcut(RingActionId.QuickChat, "quick_chat", "Quick Chat", Command | Option, DesktopKey.N)',
    'Shortcut(RingActionId.SideChat, "side_chat", "Side Chat", Command | Option, DesktopKey.S)',
    'Shortcut(RingActionId.RecentlyViewed, "recently_viewed", "Recently Viewed", Control, DesktopKey.Tab)',
    'Shortcut(RingActionId.CopyDeepLink, "copy_deep_link", "Copy Deep Link", Command | Option, DesktopKey.L)',
    'Shortcut(RingActionId.Dictation, "dictation", "Start Dictation", Control | Shift, DesktopKey.D)',
)
EXPECTED_HAPTICS = {"DispatchRequested", "DispatchFailed", "SelectionRejected"}


class ContractError(RuntimeError):
    pass


@dataclass(frozen=True)
class Gate:
    gate_id: str
    stage: str
    status: str
    summary: str
    evidence: str

    def to_dict(self) -> dict[str, str]:
        data = asdict(self)
        data["id"] = data.pop("gate_id")
        return data


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _source_files() -> Iterable[Path]:
    roots = (
        PLUGIN_ROOT / "src",
        PLUGIN_ROOT / "assets",
        PLUGIN_ROOT / "tools" / "icons",
        PLUGIN_ROOT / "tools" / "package",
        PLUGIN_ROOT / "tools" / "validate",
        PLUGIN_ROOT / "tests",
        PLUGIN_ROOT / "artifacts",
    )
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            relative_parts = path.relative_to(PLUGIN_ROOT).parts
            if any(part in {"bin", "obj", "__pycache__"} for part in relative_parts):
                continue
            if path.suffix in {".pyc", ".pyo"} or path.name == ".DS_Store":
                continue
            yield path
    yield PLUGIN_ROOT / "CodexActionRingPlugin.sln"


def input_manifest() -> dict[str, object]:
    files = []
    for path in sorted(set(_source_files())):
        if not path.is_file():
            raise ContractError(
                f"missing validation input: {path.relative_to(PROJECT_ROOT)}"
            )
        files.append(
            {
                "path": path.relative_to(PROJECT_ROOT).as_posix(),
                "byteSize": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    digest = sha256_bytes(canonical_json(files))
    return {"sha256": digest, "fileCount": len(files), "files": files}


def _enum_members(path: Path, enum_name: str) -> tuple[str, ...]:
    text = path.read_text()
    match = re.search(
        rf"\benum\s+{re.escape(enum_name)}\s*\{{(?P<body>.*?)\}}", text, re.DOTALL
    )
    if not match:
        raise ContractError(f"missing enum {enum_name}")
    return tuple(
        re.findall(
            r"^\s*([A-Za-z][A-Za-z0-9]*)\s*,\s*$", match.group("body"), re.MULTILINE
        )
    )


def _catalog_order(text: str, field_name: str) -> tuple[str, ...]:
    match = re.search(
        rf"{re.escape(field_name)}\s*=\s*Array\.AsReadOnly\(new\[\]\s*\{{(?P<body>.*?)\}}\);",
        text,
        re.DOTALL,
    )
    if not match:
        raise ContractError(f"missing Catalog order {field_name}")
    return tuple(re.findall(r"RingActionId\.([A-Za-z0-9]+)", match.group("body")))


def check_catalog() -> dict[str, object]:
    source = (PLUGIN_ROOT / "src" / "Core" / "RingActionCatalog.cs").read_text()
    compact = re.sub(r"\s+", " ", source)
    if (
        _enum_members(PLUGIN_ROOT / "src" / "Core" / "RingActionId.cs", "RingActionId")
        != ACTION_IDS
    ):
        raise ContractError(
            "RingActionId must contain exactly the eight product IDs in order"
        )
    if len(re.findall(r"\b(?:Shortcut|DeepLink)\(RingActionId\.", source)) != 8:
        raise ContractError("Catalog must define exactly eight actions")
    missing = [fragment for fragment in ACTION_FRAGMENTS if fragment not in compact]
    if missing:
        raise ContractError(f"Catalog mapping mismatch: {missing[0]}")
    if _catalog_order(source, "_primaryOrder") != PRIMARY_ORDER:
        raise ContractError("Primary Ring order does not match the locked contract")
    if (
        _enum_members(
            PLUGIN_ROOT / "src" / "Core" / "DispatchResult.cs", "DispatchResult"
        )
        != DISPATCH_RESULTS
    ):
        raise ContractError(
            "DispatchResult must contain exactly the locked four states"
        )
    return {
        "actionCount": 8,
        "primaryOrder": list(PRIMARY_ORDER),
        "dispatchResults": list(DISPATCH_RESULTS),
        "deliveryCount": {"shortcut": 7, "deepLink": 1},
    }


def check_source_boundaries() -> dict[str, object]:
    csproj_files = sorted((PLUGIN_ROOT / "src").rglob("*.csproj"))
    if csproj_files != [PLUGIN_ROOT / "src" / "CodexActionRingPlugin.csproj"]:
        raise ContractError("production must contain exactly one C# project")
    csproj = csproj_files[0].read_text()
    if "<TargetFramework>net10.0</TargetFramework>" not in csproj:
        raise ContractError("production target framework must be net10.0")

    application = (PLUGIN_ROOT / "src" / "CodexActionRingApplication.cs").read_text()
    if (
        'GetProcessName() => "ChatGPT"' not in application
        or 'GetBundleName() => "com.openai.codex"' not in application
    ):
        raise ContractError("Codex application binding mismatch")

    source_paths = [
        path
        for path in (PLUGIN_ROOT / "src").rglob("*.cs")
        if not any(
            part in {"bin", "obj"}
            for part in path.relative_to(PLUGIN_ROOT / "src").parts
        )
    ]
    source_text = "\n".join(
        path.read_text(errors="replace") for path in sorted(source_paths)
    )
    forbidden_apis = {
        "process-launch": r"\bProcess\.Start\b",
        "shell-open": r"/usr/bin/open|\bosascript\b",
        "ui-input": r"\bCGEvent\b|\bAXIsProcessTrusted\b",
        "network-listener": r"\b(?:HttpListener|TcpListener|UdpClient|WebSocketListener)\b",
        "http-client": r"\bHttpClient\b",
    }
    hits = [
        name
        for name, pattern in forbidden_apis.items()
        if re.search(pattern, source_text)
    ]
    if hits:
        raise ContractError(f"forbidden production capability: {', '.join(hits)}")

    log_contracts = (
        PLUGIN_ROOT / "src" / "DesktopBridge" / "DesktopBridgeContracts.cs"
    ).read_text()
    log_adapter = (
        PLUGIN_ROOT / "src" / "Composition" / "LogitechAdapters.cs"
    ).read_text()
    if "String PluginVersion,\n        String ErrorCategory" not in log_contracts:
        raise ContractError(
            "runtime log entry must contain only version and anonymous category"
        )
    if '=> $"{entry.PluginVersion} {entry.ErrorCategory}";' not in re.sub(
        r"\s+", " ", log_adapter
    ):
        raise ContractError(
            "production log formatting exceeds the locked two-field contract"
        )
    plugin_log_calls = re.findall(r"PluginLog\.([A-Za-z]+)\((.*?)\);", source_text)
    unsafe_calls = [
        call
        for call in plugin_log_calls
        if call[0] != "Init" and "Format(entry)" not in call[1]
    ]
    if unsafe_calls:
        raise ContractError(
            "production contains a log call outside the privacy-safe adapter"
        )

    if re.search(r"\b(?:Approve|Decline)\b", source_text, re.IGNORECASE):
        raise ContractError("Approve/Decline must be absent from production source")

    retired_symbols = (
        "PluginDynamicFolder",
        "MoreRing",
        "OpenModelSelector",
        "ToggleSidebar",
        "ToggleFileTree",
        "ToggleBottomPanel",
        "HistoryForward",
        "HistoryBack",
        "OpenSettings",
        "ReturnPrimary",
        "LocalTransition",
        "NextTask", "PreviousTask", "OpenReview", "ToggleTerminal",
    )
    present_retired = [symbol for symbol in retired_symbols if symbol in source_text]
    if present_retired:
        raise ContractError(
            f"retired More Ring production symbols remain: {', '.join(present_retired)}"
        )

    return {
        "productionProjectCount": 1,
        "assembly": "CodexActionRingPlugin.dll",
        "targetFramework": "net10.0",
        "application": {"process": "ChatGPT", "bundleId": "com.openai.codex"},
        "forbiddenCapabilityHits": [],
        "runtimeLogFields": ["PluginVersion", "ErrorCategory"],
    }


def check_feedback_icons_haptics() -> dict[str, object]:
    feedback = (PLUGIN_ROOT / "src" / "Feedback" / "FeedbackPolicy.cs").read_text()
    required_feedback = (
        "DispatchResult.NotDispatched when context == FeedbackPresentationContext.PreDisabled",
        "FeedbackCue.SelectionRejected",
        "FeedbackCue.DispatchRequested",
        "FeedbackCue.DispatchFailed",
        "DispatchResult.OutcomeUnknown",
        "UntilNextRingInvocation",
        "UnavailableOpacityPercent = 38",
    )
    if any(fragment not in feedback for fragment in required_feedback):
        raise ContractError("four-state feedback source is incomplete")

    master_names = {
        path.stem
        for path in (PLUGIN_ROOT / "assets" / "icons" / "masters").glob("*.svg")
    }
    expected_keys = {entry.split('"')[1] for entry in ACTION_FRAGMENTS}
    if master_names != expected_keys:
        raise ContractError("icon masters must match exactly the eight stable IDs")
    generated_dirs = (
        PLUGIN_ROOT / "assets" / "icons" / "generated" / "ring" / "normal",
        PLUGIN_ROOT / "assets" / "icons" / "generated" / "ring" / "unavailable",
        PLUGIN_ROOT / "assets" / "icons" / "generated" / "picker",
    )
    for directory in generated_dirs:
        if {path.stem for path in directory.glob("*.svg")} != expected_keys:
            raise ContractError(f"incomplete icon projection set: {directory.name}")

    action_map = json.loads(ACTION_MAP.read_text())
    mappings = action_map.get("mappings", [])
    if (
        len(mappings) != 8
        or {entry["semanticKey"] for entry in mappings} != expected_keys
    ):
        raise ContractError("package action map must contain the eight stable IDs")
    for entry in mappings:
        key = entry["semanticKey"]
        filename = entry["packageFilename"]
        pairs = (
            (
                PLUGIN_ROOT
                / "assets"
                / "icons"
                / "generated"
                / "ring"
                / "normal"
                / f"{key}.svg",
                PACKAGE_ROOT / "actionicons" / filename,
            ),
            (
                PLUGIN_ROOT
                / "assets"
                / "icons"
                / "generated"
                / "picker"
                / f"{key}.svg",
                PACKAGE_ROOT / "actionsymbols" / filename,
            ),
        )
        for source, packaged in pairs:
            if not packaged.is_file() or source.read_bytes() != packaged.read_bytes():
                raise ContractError(f"package icon projection mismatch: {filename}")

    plugin_icon_source = (
        PLUGIN_ROOT / "assets" / "icons" / "generated" / "plugin" / "Icon256x256.png"
    )
    plugin_icon_package = PACKAGE_ROOT / "metadata" / "Icon256x256.png"
    if plugin_icon_source.read_bytes() != plugin_icon_package.read_bytes():
        raise ContractError("package plugin icon differs from the generated source")
    png = plugin_icon_package.read_bytes()
    if (
        png[:8] != b"\x89PNG\r\n\x1a\n"
        or int.from_bytes(png[16:20], "big") != 256
        or int.from_bytes(png[20:24], "big") != 256
    ):
        raise ContractError("plugin icon must be a 256x256 PNG")

    source_event = PLUGIN_ROOT / "assets" / "haptics" / "DefaultEventSource.yaml"
    source_mapping = PLUGIN_ROOT / "assets" / "haptics" / "extra" / "eventMapping.yaml"
    package_event = PACKAGE_ROOT / "events" / "DefaultEventSource.yaml"
    package_mapping = PACKAGE_ROOT / "events" / "extra" / "eventMapping.yaml"
    if (
        source_event.read_bytes() != package_event.read_bytes()
        or source_mapping.read_bytes() != package_mapping.read_bytes()
    ):
        raise ContractError("packaged haptic files differ from their source assets")
    event_names = set(
        re.findall(
            r"^\s+- name: ([A-Za-z_][A-Za-z0-9_]*)$",
            source_event.read_text(),
            re.MULTILINE,
        )
    )
    mapping_text = source_mapping.read_text()
    mapping_names = set(
        re.findall(r"^  ([A-Za-z_][A-Za-z0-9_]*):$", mapping_text, re.MULTILINE)
    )
    if (
        event_names != EXPECTED_HAPTICS
        or mapping_names != EXPECTED_HAPTICS
        or mapping_text.count("DEFAULT:") != 3
    ):
        raise ContractError(
            "haptic source/mapping must contain the exact three paired events"
        )

    return {
        "masterCount": 8,
        "ringIconCount": 8,
        "pickerSymbolCount": 8,
        "pluginIcon": {"width": 256, "height": 256},
        "hapticEvents": sorted(EXPECTED_HAPTICS),
        "feedbackStates": list(DISPATCH_RESULTS),
    }


def _expected_package_paths() -> set[str]:
    action_map = json.loads(ACTION_MAP.read_text())
    names = {entry["packageFilename"] for entry in action_map.get("mappings", [])}
    if len(names) != 8:
        raise ContractError("package action map must provide eight unique filenames")
    return {
        "bin/CodexActionRingPlugin.dll",
        "metadata/LoupedeckPackage.yaml",
        "metadata/Icon256x256.png",
        "events/DefaultEventSource.yaml",
        "events/extra/eventMapping.yaml",
        *(f"actionicons/{name}" for name in names),
        *(f"actionsymbols/{name}" for name in names),
    }


def privacy_categories(payload: bytes) -> list[str]:
    lowered = payload.lower()
    literals = {
        str(Path.home()).encode().lower(),
        os.environ.get("USER", "").encode().lower(),
        platform.node().encode().lower(),
    }
    literals.discard(b"")
    categories = set()
    if any(literal in lowered for literal in literals) or re.search(
        rb"/users/[^/]+/(?:projects|\.codex)/", lowered
    ):
        categories.add("private-path-or-user")
    patterns = {
        "email": rb"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}",
        "credential": rb"(?:sk-(?:proj-)?[a-z0-9_-]{12,}|api[_-]?key[\s\"':=]+|access[_-]?token[\s\"':=]+|bearer[\s\"':=]+)",
        "retired-actions": rb"(?:\b(?:approve|decline)\b|moreringdynamicfolder|openmodelselector|togglesidebar|togglefiletree|togglebottompanel|historyforward|historyback|opensettings|returnprimary|nexttask|previoustask|openreview|toggleterminal)",
    }
    categories.update(
        name for name, pattern in patterns.items() if re.search(pattern, lowered)
    )
    return sorted(categories)


def check_package() -> dict[str, object]:
    if not ARTIFACT.is_file() or not PACKAGE_REPORT.is_file():
        raise ContractError("exact eight-action artifact/report is missing")
    expected = _expected_package_paths()
    source_expected = expected - {"bin/CodexActionRingPlugin.dll"}
    source_actual = {
        path.relative_to(PACKAGE_ROOT).as_posix()
        for path in PACKAGE_ROOT.rglob("*")
        if path.is_file() and path.name != ".DS_Store"
    }
    if source_actual != source_expected:
        raise ContractError(
            f"package source allowlist mismatch: extras={sorted(source_actual - source_expected)}, "
            f"missing={sorted(source_expected - source_actual)}"
        )

    manifest = (PACKAGE_ROOT / "metadata" / "LoupedeckPackage.yaml").read_text()
    required_manifest = (
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
    if any(line not in manifest for line in required_manifest) or re.search(
        r"^pluginFolderWin:", manifest, re.MULTILINE
    ):
        raise ContractError("manifest identity/device/capability contract mismatch")

    with zipfile.ZipFile(ARTIFACT) as archive:
        infos = [info for info in archive.infolist() if not info.is_dir()]
        names = {info.filename for info in infos}
        official_expected = expected | {"metadata/PackageHash.bin"}
        if names != official_expected:
            raise ContractError(
                f"artifact allowlist mismatch: extras={sorted(names - official_expected)}, "
                f"missing={sorted(official_expected - names)}"
            )
        if sum(name.lower().endswith(".dll") for name in names) != 1:
            raise ContractError("artifact must contain exactly one assembly")
        for info in infos:
            member = PurePosixPath(info.filename)
            if member.is_absolute() or ".." in member.parts:
                raise ContractError("artifact contains an unsafe path")
            lowered = info.filename.lower()
            if any(
                token in lowered
                for token in (
                    "debug",
                    ".link",
                    "fixture",
                    "temp",
                    "windows",
                    ".pdb",
                    ".deps.json",
                )
            ):
                raise ContractError(
                    f"artifact contains forbidden path category: {info.filename}"
                )
        artifact_payload = b"\n".join(
            archive.read(name) for name in sorted(names)
        )
    artifact_privacy = privacy_categories(artifact_payload)
    if artifact_privacy:
        raise ContractError(f"artifact privacy categories: {artifact_privacy}")

    report = json.loads(PACKAGE_REPORT.read_text())
    artifact_report = report.get("artifact", {})
    artifact_size = ARTIFACT.stat().st_size
    artifact_sha = sha256(ARTIFACT)
    if report.get("identity") != "CodexActionRing" or report.get("version") != "0.1.5":
        raise ContractError("release report identity/version mismatch")
    if report.get("officialPack") != "OK" or report.get("officialVerify") != "OK":
        raise ContractError("I09 pack/verify report is not OK")
    if (
        artifact_report.get("byteSize") != artifact_size
        or artifact_report.get("sha256") != artifact_sha
    ):
        raise ContractError("artifact bytes do not match the I09 report")
    if (
        artifact_report.get("fileCount") != len(names)
        or artifact_report.get("allowlistAudit") != PASS
    ):
        raise ContractError("artifact report allowlist facts mismatch")
    return {
        "artifact": ARTIFACT.name,
        "artifactByteSize": artifact_size,
        "artifactSha256": artifact_sha,
        "artifactFileCount": len(names),
        "assemblyCount": 1,
        "packageSourceFileCount": len(source_actual),
        "manifest": {
            "identity": "CodexActionRing",
            "displayName": "Codex Action Ring",
            "version": "0.1.5",
            "device": "LoupedeckExtendedFamily",
            "capabilities": ["HasApplication", "HasHapticMapping"],
        },
        "privacyCategories": [],
    }


def gate_fact_vector(
    gates: Sequence[Gate] | Sequence[dict[str, object]],
) -> dict[str, str]:
    facts: dict[str, str] = {}
    for gate in gates:
        if isinstance(gate, Gate):
            facts[gate.gate_id] = gate.status
        else:
            facts[str(gate["id"])] = str(gate["status"])
    return dict(sorted(facts.items()))


def machine_pass(gates: Sequence[Gate]) -> bool:
    return not any(gate.status == FAIL for gate in gates)
