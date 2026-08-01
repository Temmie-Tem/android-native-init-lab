"""Host-only tests for the A90 transition-v2 adapter route table."""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
REVAL_DIR = REPO_ROOT / "workspace/public/src/scripts/revalidation"
SERVER_DIR = REPO_ROOT / "workspace/public/src/scripts/server-distro"
for path in (REVAL_DIR, SERVER_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import a90_transition_adapter_blueprint_v2 as adapter  # noqa: E402
import a90_transition_manifest_v2 as manifest  # noqa: E402


class A90TransitionAdapterBlueprintV2Tests(unittest.TestCase):
    def copy_inventory(self, root: Path) -> None:
        for item in manifest.SOURCE_INVENTORY.values():
            source = REPO_ROOT / item["path"]
            target = root / item["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    def test_route_table_is_non_live_and_inventory_is_honest(self) -> None:
        result = adapter.audit_blueprint(manifest.expected_blueprint())

        self.assertEqual(result["decision"], "PASS_HOST_DESIGN_ONLY_LIVE_BLOCKED")
        self.assertIs(result["host_only"], True)
        self.assertIs(result["live_ready"], False)
        self.assertIs(result["device_authority"], False)
        self.assertIs(result["approval_preparation"], False)
        self.assertIs(result["device_contact"], False)
        self.assertIs(result["device_write"], False)
        self.assertIs(result["source_identity_bound"], False)
        self.assertIs(result["symbol_inventory_semantic_proof"], False)
        self.assertIn(
            "IMMUTABLE_SOURCE_BINDING_DEFERRED_TO_ACTIVATION_MANIFEST",
            result["blockers"],
        )

    def test_f1_is_whole_delegate_and_d1_has_no_payload(self) -> None:
        value = manifest.expected_blueprint()
        f1 = value["workflows"][manifest.F1_WORKFLOW]
        d1 = value["workflows"][manifest.D1_WORKFLOW]
        routes = {route["phase"]: route for route in d1["routes"]}

        self.assertEqual(f1["execution_model"], "delegate_whole_transaction")
        self.assertEqual(f1["delegated_owner"], "resident_promotion.main")
        self.assertEqual(f1["phases_owned_by_adapter"], [])
        self.assertEqual(manifest.F1_WORKFLOW, "A90_F1_RESIDENT_INSTALL_V1")
        self.assertIn("F1_RESIDENT_TERMINAL_ADAPTER_UNIMPLEMENTED", f1["blockers"])
        self.assertEqual(manifest.D1_WORKFLOW, "A90_D1_ATTENDED_SESSION_V1")
        self.assertEqual(
            d1["execution_model"],
            "bounded_attended_session_injected_effects",
        )
        self.assertEqual(
            d1["session_limits"],
            {
                "max_duration_sec": 8 * 60 * 60,
                "max_actions": 32,
            },
        )
        self.assertEqual(d1["action_allowlist"], ["SWITCHROOT_EXPERIMENT"])
        self.assertEqual(d1["journal_owner"], manifest.UNBOUND)
        self.assertEqual(d1["approval_consumer"], manifest.UNBOUND)
        self.assertIn("D1_DURABLE_SESSION_JOURNAL_OWNER_ABSENT", d1["blockers"])
        self.assertIn("D1_DURABLE_REFUTATION_HISTORY_ABSENT", d1["blockers"])
        self.assertIn("D1_OBSERVER_REPAIR_RECORD_OWNER_ABSENT", d1["blockers"])
        self.assertIn("D1_SESSION_APPROVAL_CONSUMER_ABSENT", d1["blockers"])
        self.assertIn("D1_SESSION_EFFECTS_BACKEND_UNIMPLEMENTED", d1["blockers"])
        self.assertFalse(
            {route["effect_kind"] for route in routes.values()}
            & {"flash", "payload_transfer", "partition_write"}
        )
        self.assertEqual(
            routes["NATIVE_RETURNED"]["callable"],
            "wait_for_candidate_return_attended_once",
        )
        self.assertEqual(
            routes["HEALTH_VERIFIED"]["callable"],
            "verify_candidate_health",
        )

    def test_cleanup_legacy_contract_cannot_be_reinterpreted(self) -> None:
        d1 = manifest.expected_blueprint()["workflows"][manifest.D1_WORKFLOW]
        cleanup = next(route for route in d1["routes"] if route["phase"] == "WORK_CLEANED")

        self.assertEqual(
            cleanup["status"],
            "BLOCKED_LEGACY_APPROVAL_AND_BASELINE_CONTRACT",
        )
        self.assertEqual(cleanup["approval_scope"], manifest.LEGACY_CLEANUP_SCOPE)
        self.assertNotEqual(cleanup["approval_scope"], d1["approval_scope"])
        self.assertIn("D1_CLEANUP_APPROVAL_SCOPE_MISMATCH", d1["blockers"])
        self.assertIn("D1_CLEANUP_BASELINE_IDENTITY_MISMATCH", d1["blockers"])

    def test_validator_rejects_readiness_f1_phase_and_d1_flash(self) -> None:
        live = manifest.expected_blueprint()
        live["live_ready"] = True
        with self.assertRaisesRegex(manifest.ManifestError, "H0 design posture"):
            manifest.validate_blueprint(live)

        f1_phase = manifest.expected_blueprint()
        f1_phase["workflows"][manifest.F1_WORKFLOW]["phases_owned_by_adapter"] = [
            "CANDIDATE_FLASH"
        ]
        with self.assertRaisesRegex(manifest.ManifestError, "whole-owner"):
            manifest.validate_blueprint(f1_phase)

        d1_flash = manifest.expected_blueprint()
        d1_flash["workflows"][manifest.D1_WORKFLOW]["routes"][3][
            "effect_kind"
        ] = "flash"
        with self.assertRaisesRegex(manifest.ManifestError, "payload or flash"):
            manifest.validate_blueprint(d1_flash)

    def test_validator_rejects_owner_claim_and_cleanup_scope_change(self) -> None:
        owner = manifest.expected_blueprint()
        d1 = owner["workflows"][manifest.D1_WORKFLOW]
        d1["journal_owner"] = "transition_engine"
        with self.assertRaisesRegex(manifest.ManifestError, "exact H0 route"):
            manifest.validate_blueprint(owner)

        cleanup = manifest.expected_blueprint()
        route = cleanup["workflows"][manifest.D1_WORKFLOW]["routes"][7]
        self.assertEqual(route["phase"], "WORK_CLEANED")
        route["approval_scope"] = manifest.D1_APPROVAL_SCOPE
        route["status"] = "READY_FOR_ADAPTER"
        with self.assertRaisesRegex(manifest.ManifestError, "exact H0 route"):
            manifest.validate_blueprint(cleanup)

    def test_validator_rejects_session_limit_allowlist_and_scope_changes(self) -> None:
        for label, mutate in (
            (
                "duration",
                lambda d1: d1["session_limits"].__setitem__(
                    "max_duration_sec",
                    8 * 60 * 60 + 1,
                ),
            ),
            (
                "budget",
                lambda d1: d1["session_limits"].__setitem__("max_actions", 33),
            ),
            (
                "allowlist",
                lambda d1: d1["action_allowlist"].append("ARBITRARY_SHELL"),
            ),
            (
                "scope",
                lambda d1: d1.__setitem__("approval_scope", "UNBOUNDED"),
            ),
        ):
            with self.subTest(label=label):
                value = manifest.expected_blueprint()
                mutate(value["workflows"][manifest.D1_WORKFLOW])
                with self.assertRaisesRegex(
                    manifest.ManifestError,
                    "exact H0 route",
                ):
                    manifest.validate_blueprint(value)

    def test_inventory_rejects_missing_and_duplicate_symbol(self) -> None:
        with tempfile.TemporaryDirectory(prefix="a90-route-symbol-") as raw:
            root = Path(raw)
            self.copy_inventory(root)
            cleanup_path = root / manifest.SOURCE_INVENTORY["legacy_cleanup"]["path"]
            source = cleanup_path.read_text(encoding="utf-8")
            cleanup_path.write_text(
                source.replace("def execute_cleanup(", "def execute_cleanup_removed(", 1),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(manifest.ManifestError, "callables are missing"):
                adapter.audit_blueprint(manifest.expected_blueprint(), root)

        with tempfile.TemporaryDirectory(prefix="a90-route-shadow-") as raw:
            root = Path(raw)
            self.copy_inventory(root)
            cleanup_path = root / manifest.SOURCE_INVENTORY["legacy_cleanup"]["path"]
            cleanup_path.write_text(
                cleanup_path.read_text(encoding="utf-8")
                + "\n\ndef execute_cleanup(*args, **kwargs):\n    return None\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(manifest.ManifestError, "duplicate top-level"):
                adapter.audit_blueprint(manifest.expected_blueprint(), root)

    def test_inventory_rejects_intermediate_symlink(self) -> None:
        with tempfile.TemporaryDirectory(prefix="a90-route-link-") as raw:
            base = Path(raw)
            real = base / "real"
            repo = base / "repo"
            self.copy_inventory(real)
            repo.mkdir()
            (repo / "workspace").symlink_to(real / "workspace", target_is_directory=True)
            with self.assertRaisesRegex(manifest.ManifestError, "hierarchy is symlinked"):
                adapter.audit_blueprint(manifest.expected_blueprint(), repo)

    def test_cli_has_only_audit_and_imports_do_not_write(self) -> None:
        script = SERVER_DIR / "a90_transition_adapter_blueprint_v2.py"
        completed = subprocess.run(
            [sys.executable, str(script), "--audit"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertFalse(json.loads(completed.stdout)["source_identity_bound"])
        help_result = subprocess.run(
            [sys.executable, str(script), "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotIn("--execute", help_result.stdout)
        self.assertNotIn("--prepare-approval", help_result.stdout)
        self.assertNotIn("--device", help_result.stdout)

        if shutil.which("bwrap") is None:
            return
        with tempfile.TemporaryDirectory(prefix="a90-route-import-") as raw:
            root = Path(raw)
            reval = root / "workspace/public/src/scripts/revalidation"
            server = root / "workspace/public/src/scripts/server-distro"
            reval.mkdir(parents=True)
            server.mkdir(parents=True)
            shutil.copy2(REVAL_DIR / "a90_transition_manifest_v2.py", reval)
            shutil.copy2(script, server)
            code = (
                "import sys;"
                "sys.path[:0]=['/repo/workspace/public/src/scripts/revalidation',"
                "'/repo/workspace/public/src/scripts/server-distro'];"
                "import a90_transition_manifest_v2;"
                "import a90_transition_adapter_blueprint_v2"
            )
            result = subprocess.run(
                [
                    "bwrap", "--ro-bind", "/usr", "/usr",
                    "--ro-bind", "/lib", "/lib",
                    "--ro-bind", "/lib64", "/lib64",
                    "--ro-bind", str(root), "/repo",
                    "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
                    "/usr/bin/python3", "-I", "-c", code,
                ],
                check=False,
                capture_output=True,
                text=True,
                env={"PYTHONDONTWRITEBYTECODE": "1"},
            )
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
