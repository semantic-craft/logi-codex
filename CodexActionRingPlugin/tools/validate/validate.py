#!/usr/bin/env python3
"""Run the deterministic nine-action Codex Action Ring release gate."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from contract import (
    FAIL,
    PASS,
    PROJECT_ROOT,
    ContractError,
    Gate,
    check_catalog,
    check_feedback_icons_haptics,
    check_package,
    check_source_boundaries,
    gate_fact_vector,
    input_manifest,
    machine_pass,
    sha256,
)


PLUGIN_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVIDENCE = (
    PROJECT_ROOT
    / ".scratch"
    / "codex-action-ring-implementation"
    / "evidence"
    / "attention-actions-build"
    / "run-1"
)
TEST_PROJECTS = (
    ("Core", Path("tests/Core/Core.Tests.csproj"), 18),
    ("DesktopBridge", Path("tests/DesktopBridge/DesktopBridge.Tests.csproj"), 29),
    ("Feedback", Path("tests/Feedback/Feedback.Tests.csproj"), 8),
    ("LogitechPrimary", Path("tests/LogitechPrimary/LogitechPrimary.Tests.csproj"), 24),
    ("Integration", Path("tests/Integration/Integration.Tests.csproj"), 8),
)
REQUIRED_TEST_NAME_FRAGMENTS = (
    "CatalogContainsTheExactLockedStaticMetadata",
    "PrimaryOrderIsFixedClockwiseFromTheTop",
    "EveryCodexDirectedActionDispatchesExactlyOnce",
    "EveryShortcutFailsClosedWhenCodexIsNotFrontmost",
    "NewChatUsesOnlyTheDeepLinkWithForegroundPrecondition",
    "ExecuteReturnsEachNormativeBridgeResult",
    "AllShortcutEncodingIsSentExactlyOnceUnchanged",
    "EveryCodexDirectedActionUsesTheSameHonestFourStatePolicy",
    "NoDecisionContainsSuccessLanguageOrCheckmarks",
    "EventSourceAndMappingAreValidYamlWithExactOneToOneNames",
    "EachWrapperDelegatesExactlyOnceAndForwardsUnchangedResult",
    "SdkCanDiscoverEveryPublicWrapperBeforeCompositionAndResolveAtSelectionTime",
    "CompleteNineActionCatalogFlowsThroughTheSingleExecutorWithoutFallback",
    "HostDiscoverySurfaceContainsOnlyNinePrimaryCommands",
    "HapticRegistrationRaisingAndSourceAssetsUseTheSameExactNames",
    "DesktopLogFormattingContainsOnlyVersionAndAnonymousCategory",
)


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def run_command(
    name: str,
    args: list[str],
    logs: Path,
    env: dict[str, str] | None = None,
    cwd: Path = PLUGIN_ROOT,
) -> tuple[int, str]:
    completed = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        check=False,
    )
    logs.mkdir(parents=True, exist_ok=True)
    (logs / f"{name}.log").write_text(completed.stdout)
    return completed.returncode, completed.stdout


def check_gate(
    gate_id: str, stage: str, evidence: Path, function
) -> tuple[Gate, dict[str, object] | None]:
    try:
        detail = function()
        return Gate(
            gate_id, stage, PASS, "Locked contract satisfied", relative(evidence)
        ), detail
    except (
        ContractError,
        OSError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
        zipfile.BadZipFile,
    ) as error:
        write_json(evidence, {"status": FAIL, "error": str(error)})
        return Gate(gate_id, stage, FAIL, str(error), relative(evidence)), None


def build_properties(output: Path) -> list[str]:
    plugin_links = output / "work" / "plugin-links"
    plugin_links.mkdir(parents=True, exist_ok=True)
    return [
        f"-p:PluginDir={plugin_links}/",
        "-p:PluginShortName=CodexActionRingValidationBuild",
        "-p:TreatWarningsAsErrors=true",
        "-p:DebugType=None",
        "-p:DebugSymbols=false",
    ]


def build_environment(output: Path) -> dict[str, str]:
    fake_bin = output / "work" / "fake-bin"
    fake_bin.mkdir(parents=True, exist_ok=True)
    fake_open = fake_bin / "open"
    fake_open.write_text("#!/bin/sh\nexit 0\n")
    fake_open.chmod(fake_open.stat().st_mode | stat.S_IXUSR)
    environment = os.environ.copy()
    environment["PATH"] = f"{fake_bin}{os.pathsep}{environment.get('PATH', '')}"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return environment


def prepare_snapshot(output: Path) -> Path:
    snapshot = output / "work" / "snapshot" / "CodexActionRingPlugin"

    def ignore(_directory: str, names: list[str]) -> set[str]:
        return {
            name
            for name in names
            if name in {"bin", "obj", "__pycache__", ".DS_Store"}
            or name.endswith((".pyc", ".pyo"))
        }

    shutil.copytree(PLUGIN_ROOT, snapshot, ignore=ignore)
    return snapshot


def run_clean_release_build(
    output: Path, logs: Path, build_root: Path
) -> tuple[Gate, dict[str, object]]:
    properties = build_properties(output)
    environment = build_environment(output)
    code, text = run_command(
        "release-build",
        [
            "dotnet",
            "build",
            str(build_root / "CodexActionRingPlugin.sln"),
            "--configuration",
            "Release",
            "--no-incremental",
            "--nologo",
            *properties,
        ],
        logs,
        environment,
        build_root,
    )
    isolated_links = sorted((output / "work" / "plugin-links").glob("*.link"))
    link_facts = [
        {"path": relative(path), "target": path.read_text(errors="replace").strip()}
        for path in isolated_links
    ]
    for path in isolated_links:
        path.unlink()
    warning_match = re.search(r"(?m)^\s*(\d+) Warning\(s\)\s*$", text)
    error_match = re.search(r"(?m)^\s*(\d+) Error\(s\)\s*$", text)
    warning_count = int(warning_match.group(1)) if warning_match else None
    error_count = int(error_match.group(1)) if error_match else None
    detail = {
        "exitCode": code,
        "warningCount": warning_count,
        "errorCount": error_count,
        "isolatedBuildLinksRemoved": link_facts,
        "realOpenSuppressed": True,
    }
    write_json(output / "build.json", detail)
    passed = (
        code == 0
        and warning_count == 0
        and error_count == 0
        and not list((output / "work" / "plugin-links").glob("*.link"))
    )
    summary = (
        "Clean Release build: 0 warnings, 0 errors; isolated post-build link removed"
        if passed
        else "Clean Release build failed; see build.json and log"
    )
    return Gate(
        "B04_RELEASE_BUILD",
        "build",
        PASS if passed else FAIL,
        summary,
        relative(output / "build.json"),
    ), detail


def trx_results(path: Path) -> list[dict[str, str]]:
    root = ET.parse(path).getroot()
    namespace = {"t": "http://microsoft.com/schemas/VisualStudio/TeamTest/2010"}
    return [
        {
            "name": node.attrib.get("testName", ""),
            "outcome": node.attrib.get("outcome", ""),
        }
        for node in root.findall(".//t:UnitTestResult", namespace)
    ]


def run_dotnet_tests(
    output: Path, logs: Path, build_root: Path
) -> tuple[Gate, dict[str, object]]:
    properties = build_properties(output)
    environment = build_environment(output)
    results_dir = output / "dotnet-test-results"
    results_dir.mkdir(parents=True, exist_ok=True)
    projects: list[dict[str, object]] = []
    all_results: list[dict[str, str]] = []
    all_passed = True
    for name, project_relative, expected_count in TEST_PROJECTS:
        project = build_root / project_relative
        trx_name = f"{name}.trx"
        code, _ = run_command(
            f"test-{name}",
            [
                "dotnet",
                "test",
                str(project),
                "--configuration",
                "Release",
                "--no-build",
                "--no-restore",
                "--nologo",
                "--results-directory",
                str(results_dir),
                "--logger",
                f"trx;LogFileName={trx_name}",
                *properties,
            ],
            logs,
            environment,
            build_root,
        )
        trx_path = results_dir / trx_name
        results = trx_results(trx_path) if trx_path.is_file() else []
        passed = (
            code == 0
            and len(results) == expected_count
            and all(result["outcome"] == "Passed" for result in results)
        )
        all_passed = all_passed and passed
        all_results.extend(results)
        projects.append(
            {
                "project": name,
                "expected": expected_count,
                "observed": len(results),
                "passed": sum(result["outcome"] == "Passed" for result in results),
                "failed": sum(result["outcome"] != "Passed" for result in results),
                "exitCode": code,
                "trx": relative(trx_path),
            }
        )
    missing_coverage = [
        fragment
        for fragment in REQUIRED_TEST_NAME_FRAGMENTS
        if not any(
            fragment in result["name"] and result["outcome"] == "Passed"
            for result in all_results
        )
    ]
    all_passed = all_passed and len(all_results) == 87 and not missing_coverage
    detail = {
        "expectedTotal": 87,
        "observedTotal": len(all_results),
        "passedTotal": sum(result["outcome"] == "Passed" for result in all_results),
        "failedTotal": sum(result["outcome"] != "Passed" for result in all_results),
        "missingRequiredCoverage": missing_coverage,
        "projects": projects,
    }
    write_json(output / "dotnet-tests.json", detail)
    summary = (
        "All five .NET suites passed 87/87 with required named coverage"
        if all_passed
        else "Full .NET contract suite failed or required coverage is missing"
    )
    return Gate(
        "B05_DOTNET_CONTRACTS",
        "build",
        PASS if all_passed else FAIL,
        summary,
        relative(output / "dotnet-tests.json"),
    ), detail


def run_python_gate(
    gate_id: str,
    name: str,
    summary: str,
    args: list[str],
    output: Path,
    logs: Path,
    cwd: Path = PLUGIN_ROOT,
) -> Gate:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    code, _ = run_command(name, args, logs, environment, cwd)
    return Gate(
        gate_id,
        "build",
        PASS if code == 0 else FAIL,
        summary if code == 0 else f"{summary} failed",
        relative(logs / f"{name}.log"),
    )


def reusable_gate(report: dict[str, object], gate_id: str, output: Path) -> Gate:
    match = next(
        (gate for gate in report.get("gates", []) if gate.get("id") == gate_id), None
    )
    if match is None:
        return Gate(
            gate_id,
            "build",
            FAIL,
            "Reusable report lacks required gate",
            relative(output),
        )
    return Gate(
        gate_id,
        str(match["stage"]),
        str(match["status"]),
        "Reused immutable full-run fact after exact input-manifest match",
        relative(output),
    )


def tool_version(tool: Path) -> str:
    store = tool.parent / ".store" / "logiplugintool"
    versions = (
        sorted(path.name for path in store.iterdir() if path.is_dir())
        if store.is_dir()
        else []
    )
    if versions != ["6.1.4.22672"]:
        raise ContractError(f"official LogiPluginTool version mismatch: {versions}")
    return versions[0]


def run_official_verify(
    tool: Path, dotnet_root: Path | None, output: Path, logs: Path
) -> tuple[Gate, dict[str, object] | None]:
    evidence = output / "official-verify.json"
    try:
        if not tool.is_file():
            raise ContractError(f"official LogiPluginTool not found: {tool}")
        version = tool_version(tool)
        environment = os.environ.copy()
        if dotnet_root is not None:
            environment["DOTNET_ROOT"] = str(dotnet_root)
            environment["PATH"] = (
                f"{dotnet_root}{os.pathsep}{environment.get('PATH', '')}"
            )
        code, text = run_command(
            "official-verify",
            [
                str(tool),
                "verify",
                str(PLUGIN_ROOT / "artifacts" / "CodexActionRing_0_1_7.lplug4"),
            ],
            logs,
            environment,
        )
        detail = {
            "toolVersion": version,
            "toolSha256": sha256(tool),
            "artifactSha256": sha256(
                PLUGIN_ROOT / "artifacts" / "CodexActionRing_0_1_7.lplug4"
            ),
            "exitCode": code,
            "reportedOk": bool(re.search(r"\bOK\b", text)),
        }
        write_json(evidence, detail)
        passed = code == 0 and detail["reportedOk"]
        return (
            Gate(
                "P04_OFFICIAL_VERIFY",
                "pack / exact verify",
                PASS if passed else FAIL,
                "Official exact-file verify returned OK"
                if passed
                else "Official exact-file verify failed",
                relative(evidence),
            ),
            detail,
        )
    except (ContractError, OSError) as error:
        write_json(evidence, {"error": str(error)})
        return Gate(
            "P04_OFFICIAL_VERIFY",
            "pack / exact verify",
            FAIL,
            str(error),
            relative(evidence),
        ), None


def render_gate_table(gates: list[Gate], path: Path) -> None:
    lines = [
        "# Codex Action Ring nine-action release gate",
        "",
        "| Gate | Stage | Result | Evidence | Summary |",
        "|---|---|---|---|---|",
    ]
    for gate in gates:
        summary = gate.summary.replace("|", "\\|").replace("\n", " ")
        evidence = gate.evidence.replace("|", "\\|")
        lines.append(
            f"| `{gate.gate_id}` | {gate.stage} | **{gate.status}** | `{evidence}` | {summary} |"
        )
    path.write_text("\n".join(lines) + "\n")


def stage_table(gates: list[Gate], output: Path) -> list[dict[str, str]]:
    def aggregate(stage: str) -> str:
        statuses = [gate.status for gate in gates if gate.stage == stage]
        return FAIL if FAIL in statuses else PASS

    return [
        {
            "stage": "build",
            "status": aggregate("build"),
            "evidence": relative(output / "gate-table.md"),
        },
        {
            "stage": "pack / exact verify",
            "status": aggregate("pack / exact verify"),
            "evidence": relative(output / "gate-table.md"),
        },
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--official-tool", type=Path, required=True)
    parser.add_argument("--official-dotnet-root", type=Path)
    parser.add_argument("--reuse-build-from", type=Path)
    args = parser.parse_args()

    output = args.output.resolve()
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    logs = output / "logs"

    manifest = input_manifest()
    write_json(output / "input-manifest.json", manifest)
    baseline_report: dict[str, object] | None = None
    if args.reuse_build_from:
        baseline_report = json.loads(args.reuse_build_from.read_text())
        baseline_manifest = baseline_report.get("inputManifest", {})
        if baseline_manifest.get("sha256") != manifest["sha256"]:
            write_json(
                output / "reproducibility.json",
                {
                    "identical": False,
                    "reason": "input manifest changed",
                    "baseline": baseline_manifest.get("sha256"),
                    "current": manifest["sha256"],
                },
            )
            print(
                "FAIL: input manifest changed; build evidence cannot be reused",
                file=sys.stderr,
            )
            return 2

    gates: list[Gate] = []
    details: dict[str, object] = {}

    if baseline_report is None:
        execution_root = prepare_snapshot(output)
        build_gate, build_detail = run_clean_release_build(output, logs, execution_root)
        tests_gate, tests_detail = run_dotnet_tests(output, logs, execution_root)
        gates.extend((build_gate, tests_gate))
        details[build_gate.gate_id] = build_detail
        details[tests_gate.gate_id] = tests_detail
    else:
        execution_root = PLUGIN_ROOT
        gates.extend(
            (
                reusable_gate(
                    baseline_report, "B04_RELEASE_BUILD", args.reuse_build_from
                ),
                reusable_gate(
                    baseline_report, "B05_DOTNET_CONTRACTS", args.reuse_build_from
                ),
            )
        )

    gates.append(
        run_python_gate(
            "B05_ICON_CONTRACTS",
            "icon-tests",
            "Icon System tests passed",
            [
                "python3",
                "-m",
                "unittest",
                "discover",
                "-s",
                str(execution_root / "tests" / "IconSystem"),
                "-v",
            ],
            output,
            logs,
            execution_root,
        )
    )
    icon_check = run_python_gate(
        "B05_ICON_DETERMINISM",
        "icon-determinism",
        "Icon outputs regenerate byte-for-byte",
        [
            "python3",
            str(execution_root / "tools" / "icons" / "generate_icons.py"),
            "--check",
        ],
        output,
        logs,
        execution_root,
    )
    gates.append(icon_check)
    gates.append(
        run_python_gate(
            "I10_VALIDATOR_TESTS",
            "validator-tests",
            "Validator contract tests passed",
            [
                "python3",
                "-m",
                "unittest",
                "discover",
                "-s",
                str(execution_root / "tests" / "Contracts"),
                "-v",
            ],
            output,
            logs,
            execution_root,
        )
    )

    static_checks = (
        ("S03_CATALOG_COMMANDS", "build", output / "catalog.json", check_catalog),
        (
            "S01_SOURCE_BOUNDARY",
            "build",
            output / "source-boundaries.json",
            check_source_boundaries,
        ),
        (
            "B05_FEEDBACK_ICONS_HAPTICS",
            "build",
            output / "feedback-icons-haptics.json",
            check_feedback_icons_haptics,
        ),
    )
    for gate_id, stage, evidence, function in static_checks:
        gate, detail = check_gate(gate_id, stage, evidence, function)
        gates.append(gate)
        if detail is not None:
            write_json(evidence, detail)
            details[gate_id] = detail

    package_evidence = output / "package.json"
    package_gate, package_detail = check_gate(
        "P02_PACKAGE_ALLOWLIST", "pack / exact verify", package_evidence, check_package
    )
    gates.append(package_gate)
    if package_detail is not None:
        write_json(package_evidence, package_detail)
        details[package_gate.gate_id] = package_detail
        gates.append(
            Gate(
                "P04_ARTIFACT_EXACT",
                "pack / exact verify",
                PASS,
                "Artifact size/SHA and release report match exact bytes",
                relative(package_evidence),
            )
        )
        gates.append(
            Gate(
                "S04_PRIVACY",
                "pack / exact verify",
                PASS,
                "Artifact privacy scan found no forbidden category",
                relative(package_evidence),
            )
        )
    else:
        gates.append(
            Gate(
                "P04_ARTIFACT_EXACT",
                "pack / exact verify",
                FAIL,
                "Exact artifact facts unavailable because package audit failed",
                relative(package_evidence),
            )
        )
        gates.append(
            Gate(
                "S04_PRIVACY",
                "pack / exact verify",
                FAIL,
                "Privacy verdict unavailable because package audit failed",
                relative(package_evidence),
            )
        )

    verify_gate, verify_detail = run_official_verify(
        args.official_tool.resolve(),
        args.official_dotnet_root.resolve() if args.official_dotnet_root else None,
        output,
        logs,
    )
    gates.append(verify_gate)
    if verify_detail is not None:
        details[verify_gate.gate_id] = verify_detail

    gate_table_path = output / "gate-table.md"
    render_gate_table(gates, gate_table_path)
    report = {
        "schemaVersion": 1,
        "kind": "CodexActionRing nine-action release validation",
        "inputManifest": manifest,
        "gates": [gate.to_dict() for gate in gates],
        "gateFacts": gate_fact_vector(gates),
        "machinePass": machine_pass(gates),
        "stageTable": stage_table(gates, output),
        "artifact": package_detail,
    }
    report_path = output / "report.json"
    write_json(report_path, report)

    reproducible = True
    if baseline_report is not None:
        baseline_facts = baseline_report.get("gateFacts", {})
        current_facts = report["gateFacts"]
        reproducible = baseline_facts == current_facts
        write_json(
            output / "reproducibility.json",
            {
                "identical": reproducible,
                "baselineReport": relative(args.reuse_build_from),
                "inputManifestSha256": manifest["sha256"],
                "baselineFacts": baseline_facts,
                "currentFacts": current_facts,
            },
        )

    work = output / "work"
    if work.exists():
        shutil.rmtree(work)
    write_json(output / "cleanup.json", {"evidenceWorkRemoved": not work.exists()})

    print(gate_table_path.read_text(), end="")
    if not reproducible:
        print("FAIL: repeated validation facts differ", file=sys.stderr)
        return 2
    return 0 if report["machinePass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
