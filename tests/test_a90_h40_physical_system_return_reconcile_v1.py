"""Host-only binding tests for the fixed H40 physical-return continuation."""

import importlib.util
from pathlib import Path
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/server-distro/a90_h40_physical_system_return_reconcile_v1.py"


def load_module():
    spec = importlib.util.spec_from_file_location("a90_h40_physical_return", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class H40PhysicalReturnBindingTests(unittest.TestCase):
    def test_exact_incident_and_no_replay_binding(self) -> None:
        module = load_module()
        engine = module.engine
        self.assertEqual(module.RUN_ID, "a90-h40-f1-20260830-01")
        self.assertEqual(
            module.MANIFEST_SHA256,
            "a6c101fb2dfa0ad85bba1b73d1ebf9fcf973d46aaaf1e0f11981aba8fcf61ceb",
        )
        self.assertEqual(
            module.CANDIDATE_SHA256,
            "68e12101e151f9515f2cf519f2749a8c1218e6c79a49aa4c9fcadd96b0728db0",
        )
        self.assertEqual(
            tuple(module.RECORD_HASHES),
            tuple(module.owner.CURRENT_ROLLBACK_WITH_FAILED_BOOT_EVIDENCE_PATH),
        )
        self.assertEqual(engine.INCIDENT_RECORD_SHA256, module.RECORD_HASHES)
        self.assertEqual(engine.ACTIVE_GUARD_SHA256, module.ACTIVE_GUARD_SHA256)
        self.assertEqual(engine.CANDIDATE_GUARD_SHA256, module.CANDIDATE_GUARD_SHA256)

    def test_only_physical_return_and_read_only_health_are_exposed(self) -> None:
        module = load_module()
        self.assertIn("already showing TWRP", module.engine.INSTRUCTION)
        self.assertIn("Reboot -> System once", module.engine.INSTRUCTION)
        self.assertIs(module.authorize, module.engine.authorize)
        self.assertIs(module.finalize, module.engine.finalize)
        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in (
            "adb reboot", "fastboot", "heimdall", "odin4", "dd if=",
            "flash(" , "rollback(", "candidate(",
        ):
            self.assertNotIn(forbidden, source)

    def test_closure_binds_engine_policy_goal_incident_and_tests(self) -> None:
        module = load_module()
        paths = set(module.engine.EXECUTION_SOURCE_RELS)
        required = {
            "AGENTS.md",
            "GOAL_A90.md",
            "docs/operations/targets/A90_TARGET_CONTRACT.md",
            "docs/reports/A90_H40_ROLLBACK_HEALTH_UNPROVED_INCIDENT_2026-08-30.md",
            "tests/test_a90_h28_physical_system_return_reconcile_v1.py",
            "tests/test_a90_h40_physical_system_return_reconcile_v1.py",
            "workspace/public/src/scripts/server-distro/a90_h28_physical_system_return_reconcile_v1.py",
            "workspace/public/src/scripts/server-distro/a90_h40_physical_system_return_reconcile_v1.py",
        }
        self.assertTrue(required <= paths)
        self.assertNotIn(
            "docs/reports/A90_H40_PHYSICAL_SYSTEM_RETURN_RECOVERY_REVIEW_2026-08-30.json",
            paths,
        )
        self.assertRegex(module.execution_closure_sha256(), r"^[0-9a-f]{64}$")

    def test_historical_qualification_is_pinned_but_never_current_authority(self) -> None:
        module = load_module()
        engine = module.engine
        self.assertEqual(engine.HISTORICAL_H28_MANIFEST_SHA256, "0" * 64)
        self.assertEqual(
            engine.HISTORICAL_QUALIFICATION_REVIEW_SHA256,
            module.QUALIFICATION_REVIEW_SHA256,
        )
        self.assertEqual(
            engine.HISTORICAL_QUALIFICATION_CLOSURE_SHA256,
            module.QUALIFICATION_CLOSURE_SHA256,
        )
        self.assertEqual(
            engine.CURRENT_REVIEW_PATH.name,
            "A90_H40_PHYSICAL_SYSTEM_RETURN_RECOVERY_REVIEW_2026-08-30.json",
        )

    def test_dynamic_manifest_accepts_only_configured_h40_candidate(self) -> None:
        module = load_module()
        engine = module.engine
        manifest = {
            "runId": module.RUN_ID,
            "candidate": {"sha256": module.CANDIDATE_SHA256},
            "rollback": {"sha256": module.owner.V2321_ROLLBACK_SHA256},
        }
        raw = module.owner.canonical_json(manifest)
        old_manifest_sha = engine.MANIFEST_SHA256
        try:
            engine.MANIFEST_SHA256 = engine._sha(raw)
            with (
                mock.patch.object(engine, "_read_json", return_value=(raw, manifest)),
                mock.patch.object(module.owner, "validate_manifest", return_value=manifest),
                mock.patch.object(engine, "_verify_historical_qualification_binding"),
            ):
                self.assertEqual(engine._load_manifest(), (raw, manifest))
                manifest["candidate"]["sha256"] = (
                    "aea34a96464affd2f7e6c30d237e2175940eef511e69c1452c9deab4833a521b"
                )
                with self.assertRaisesRegex(
                    engine.ContractError, "fixed H28 manifest identity changed"
                ):
                    engine._load_manifest()
        finally:
            engine.MANIFEST_SHA256 = old_manifest_sha


if __name__ == "__main__":
    unittest.main()
