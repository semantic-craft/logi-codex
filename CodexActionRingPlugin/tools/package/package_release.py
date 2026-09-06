#!/usr/bin/env python3
"""Create an allowlisted eight-action stage and run official pack/verify."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "src" / "package"
ARTIFACTS = ROOT / "artifacts"
ARTIFACT = ARTIFACTS / "CodexActionRing_0_1_5.lplug4"
REPORT = ARTIFACTS / "CodexActionRing_0_1_5.report.json"
ACTION_CLASS_PREFIX = "Loupedeck.CodexActionRingPlugin."


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def expected_package_paths() -> set[str]:
    action_names = {path.name for path in (PACKAGE / "actionicons").glob("*.svg")}
    symbol_names = {path.name for path in (PACKAGE / "actionsymbols").glob("*.svg")}
    if len(action_names) != 8 or action_names != symbol_names:
        raise SystemExit("expected exactly eight matching actionicons/actionsymbols")
    for filename in action_names:
        if not filename.startswith(ACTION_CLASS_PREFIX) or not filename.endswith(
            ".svg"
        ):
            raise SystemExit(f"not a class-named SVG: {filename}")
    return {
        "bin/CodexActionRingPlugin.dll",
        "metadata/LoupedeckPackage.yaml",
        "metadata/Icon256x256.png",
        "events/DefaultEventSource.yaml",
        "events/extra/eventMapping.yaml",
        *(f"actionicons/{name}" for name in action_names),
        *(f"actionsymbols/{name}" for name in symbol_names),
    }


def copy_allowlisted_stage(stage: Path, release_dir: Path) -> set[str]:
    expected = expected_package_paths()
    for relative in sorted(expected):
        source = (
            release_dir / relative
            if relative.startswith("bin/")
            else PACKAGE / relative
        )
        if not source.is_file():
            raise SystemExit(f"missing allowlisted package input: {source}")
        target = stage / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    actual = {
        path.relative_to(stage).as_posix()
        for path in stage.rglob("*")
        if path.is_file()
    }
    if actual != expected:
        raise SystemExit("staged package content differs from the exact allowlist")
    return expected


def audit_artifact(expected: set[str]) -> dict[str, object]:
    with zipfile.ZipFile(ARTIFACT) as archive:
        names = {info.filename for info in archive.infolist() if not info.is_dir()}
        official_names = expected | {"metadata/PackageHash.bin"}
        if names != official_names:
            extras = sorted(names - official_names)
            missing = sorted(official_names - names)
            raise SystemExit(
                f"artifact allowlist failed; extras={extras}, missing={missing}"
            )
        for info in archive.infolist():
            lowered = info.filename.lower()
            if any(
                token in lowered
                for token in ("debug", ".link", "fixture", "temp", "windows", ".pdb")
            ):
                raise SystemExit(f"forbidden artifact path: {info.filename}")
        payload = b"\n".join(archive.read(name) for name in sorted(names))
        lowered_payload = payload.lower()
        forbidden_payload_tokens = {
            "workspace-path": b"/users/",
            "credential": b"sk-proj-",
            "retired-actions": b"moreringdynamicfolder",
        }
        hits = [
            label
            for label, token in forbidden_payload_tokens.items()
            if token in lowered_payload
        ]
        retired_tokens = (
            b"openmodelselector",
            b"togglesidebar",
            b"togglefiletree",
            b"togglebottompanel",
            b"historyforward",
            b"historyback",
            b"opensettings",
            b"returnprimary",
        )
        if any(token in lowered_payload for token in retired_tokens):
            hits.append("retired-actions")
        if hits:
            raise SystemExit(
                f"artifact privacy/contract scan failed; categories={hits}"
            )
    return {
        "filename": ARTIFACT.name,
        "byteSize": ARTIFACT.stat().st_size,
        "sha256": sha256(ARTIFACT),
        "fileCount": len(names),
        "allowlistAudit": "PASS",
        "officialPackageHashPresent": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tool", type=Path, required=True)
    parser.add_argument("--release-dir", type=Path, required=True)
    args = parser.parse_args()
    tool = args.tool.resolve()
    release_dir = args.release_dir.resolve()
    if not tool.is_file():
        raise SystemExit(f"official LogiPluginTool not found: {tool}")

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    for target in (ARTIFACT, REPORT):
        if os.path.lexists(target):
            raise SystemExit(f"refusing to overwrite frozen output: {target}")
    # A permanent exclusive reservation also preserves failed attempts. Use a new
    # version after any pack attempt; concurrent invocations cannot both pack.
    reservation = ARTIFACTS / (ARTIFACT.name + ".attempt")
    try:
        reservation.mkdir()
    except FileExistsError:
        raise SystemExit(f"pack already attempted for this version: {reservation}")
    for target in (ARTIFACT, REPORT):
        if os.path.lexists(target):
            raise SystemExit(f"output appeared during reservation: {target}")
    environment = os.environ.copy()
    with tempfile.TemporaryDirectory(prefix=".i09-stage-", dir=ARTIFACTS) as temporary:
        stage = Path(temporary)
        expected = copy_allowlisted_stage(stage, release_dir)
        subprocess.run(
            [str(tool), "pack", str(stage), str(ARTIFACT)], check=True, env=environment
        )
    subprocess.run([str(tool), "verify", str(ARTIFACT)], check=True, env=environment)
    artifact_report = audit_artifact(expected)
    report = {
        "identity": "CodexActionRing",
        "version": "0.1.5",
        "artifact": artifact_report,
        "officialPack": "OK",
        "officialVerify": "OK",
    }
    with REPORT.open("x") as output:
        output.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
