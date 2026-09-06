from __future__ import annotations

import importlib.util
import sys
import unittest
import zipfile
from pathlib import Path


CONTRACT_PATH = (
    Path(__file__).resolve().parents[2] / "tools" / "validate" / "contract.py"
)
SPEC = importlib.util.spec_from_file_location(
    "codex_action_ring_validation_contract", CONTRACT_PATH
)
assert SPEC is not None and SPEC.loader is not None
contract = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = contract
SPEC.loader.exec_module(contract)


class ValidatorContractTests(unittest.TestCase):
    def test_catalog_has_exact_ids_orders_commands_and_four_results(self) -> None:
        facts = contract.check_catalog()
        self.assertEqual(9, facts["actionCount"])
        self.assertEqual(8, len(facts["primaryOrder"]))
        self.assertNotIn("moreOrder", facts)
        self.assertEqual(
            ["NotDispatched", "DispatchRequested", "DispatchFailed", "OutcomeUnknown"],
            facts["dispatchResults"],
        )
        self.assertEqual({"shortcut": 8, "deepLink": 1}, facts["deliveryCount"])

    def test_source_is_one_macos_assembly_with_private_safe_logs(self) -> None:
        facts = contract.check_source_boundaries()
        self.assertEqual(1, facts["productionProjectCount"])
        self.assertEqual("net10.0", facts["targetFramework"])
        self.assertEqual(["PluginVersion", "ErrorCategory"], facts["runtimeLogFields"])
        self.assertEqual([], facts["forbiddenCapabilityHits"])

    def test_feedback_icons_and_haptics_are_complete(self) -> None:
        facts = contract.check_feedback_icons_haptics()
        self.assertEqual(9, facts["masterCount"])
        self.assertEqual(9, facts["ringIconCount"])
        self.assertEqual(9, facts["pickerSymbolCount"])
        self.assertEqual(3, len(facts["hapticEvents"]))

    def test_exact_package_matches_allowlist_report_and_privacy_contract(self) -> None:
        facts = contract.check_package()
        self.assertEqual(24, facts["artifactFileCount"])
        self.assertEqual(1, facts["assemblyCount"])
        self.assertEqual("0.1.7", facts["manifest"]["version"])
        with zipfile.ZipFile(contract.ARTIFACT) as archive:
            metadata = archive.read("metadata/LoupedeckPackage.yaml").decode()
        self.assertIn("author: xianwei zhang", metadata)
        self.assertIn("copyright: Copyright © 2026 xianwei zhang.", metadata)
        source_metadata = (contract.PACKAGE_ROOT / "metadata/LoupedeckPackage.yaml").read_text()
        self.assertNotIn("mailto:", source_metadata)
        self.assertNotIn("profileByteSize", facts)
        self.assertEqual([], facts["privacyCategories"])

    def test_input_manifest_is_stable_and_excludes_generated_outputs(self) -> None:
        first = contract.input_manifest()
        second = contract.input_manifest()
        self.assertEqual(first["sha256"], second["sha256"])
        self.assertEqual(first["files"], second["files"])
        for entry in first["files"]:
            parts = Path(entry["path"]).parts
            self.assertNotIn("bin", parts)
            self.assertNotIn("obj", parts)
            self.assertNotIn("__pycache__", parts)

    def test_privacy_scan_reports_categories_not_secret_values(self) -> None:
        payload = (
            b"/Users/private/Projects/work a@example.com sk-proj-abcdefghijkl approve"
        )
        self.assertEqual(
            ["credential", "email", "private-path-or-user", "retired-actions"],
            contract.privacy_categories(payload),
        )

    def test_support_email_is_not_exempt_from_privacy_scan(self) -> None:
        line = b"\nsupportPageUrl: mailto:developer@example.com\n"
        self.assertIn("email", contract.privacy_categories(line))

    def test_machine_failure_blocks_release_result(self) -> None:
        gates = [contract.Gate("MACHINE", "build", contract.FAIL, "failed", "evidence")]
        self.assertFalse(contract.machine_pass(gates))

    def test_gate_fact_vector_ignores_summaries_and_evidence_paths(self) -> None:
        first = [contract.Gate("A", "build", contract.PASS, "one", "one.json")]
        second = [contract.Gate("A", "build", contract.PASS, "two", "two.json")]
        self.assertEqual(
            contract.gate_fact_vector(first), contract.gate_fact_vector(second)
        )


if __name__ == "__main__":
    unittest.main()
