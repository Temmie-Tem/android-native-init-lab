"""Host-only constraints for the fixed H38 run-02 rollback continuation."""

import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/server-distro/a90_h38_run02_rollback_continuation_v1.py"


def load_module():
    sys.path.insert(0, str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("a90_h38_run02_recovery", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class H38Run02RollbackContinuationTests(unittest.TestCase):
    def test_exact_consumed_incident_is_bound(self) -> None:
        module = load_module()
        self.assertEqual(module.RUN_ID, "a90-h38-f1-20260830-02")
        self.assertEqual(len(module.RECORD_HASHES), 13)
        with (
            mock.patch.object(module.engine, "_review", return_value=("1" * 64, "2" * 64)),
            mock.patch.object(module.engine, "_require_guards"),
        ):
            manifest, _review, _closure, token = module.engine._fixed_context()
        self.assertEqual(manifest["candidate"]["sha256"], "d96468eb429d7d64c94787cab4bd423136e60a480e73d19c8046e33b6b2606e9")
        self.assertTrue(token.startswith(module.engine.APPROVAL_PREFIX))

    def test_surface_is_rollback_only(self) -> None:
        module = load_module()
        source = module.ENGINE_PATH.read_text(encoding="utf-8")
        execute = source[source.index("def execute(") : source.index("def main(")]
        self.assertIn("rollback=True", execute)
        self.assertNotIn("rollback=False", execute)
        self.assertNotIn('manifest["candidate"]', execute)
        self.assertIn("role != adapter.ADB_ROLE_RECOVERY", execute)

    def test_closure_binds_wrapper_engine_test_and_contact_machinery(self) -> None:
        module = load_module()
        self.assertIn(module.SELF_PATH, module.engine.CLOSURE_PATHS)
        self.assertIn(module.TEST_PATH, module.engine.CLOSURE_PATHS)
        self.assertIn(module.ENGINE_PATH, module.engine.CLOSURE_PATHS)
        self.assertEqual(len(module.execution_closure_sha256()), 64)

    def test_final_payload_uses_h38_schema_and_decision(self) -> None:
        module = load_module()
        engine = module.engine
        manifest = {
            "rollback": {
                "version": engine.owner.V2321_ROLLBACK_VERSION,
                "build": engine.owner.V2321_ROLLBACK_BUILD,
            },
            "qualification": {"freshState": {}},
            "timeouts": {"healthSec": 90},
        }
        snapshot = engine.owner.Snapshot(
            target_evidence_sha256="0" * 64,
            boot_id="01234567-89ab-cdef-0123-456789abcdef",
            version=engine.owner.V2321_ROLLBACK_VERSION,
            build=engine.owner.V2321_ROLLBACK_BUILD,
            healthy=True,
            recovery_available=True,
            recovery_evidence_sha256="1" * 64,
            fresh_state_observed=False,
            fresh_state_absent=False,
            other_targets_untouched=True,
            receipt_sha256="2" * 64,
        )

        class Fixed:
            def __init__(self, *_args, **_kwargs):
                pass

            def observe(self, *_args, **_kwargs):
                return snapshot

        effect = SimpleNamespace(
            completed=True,
            returncode=0,
            quiescent=True,
            outcome="BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_CONFIRMED",
            payload=lambda: {"outcome": "exact-v2321"},
        )
        published = {}

        def publish(path, value):
            published[path] = engine.owner.canonical_json(value)

        with (
            mock.patch.object(engine, "_require_guards"),
            mock.patch.object(engine.adapter, "FixedA90Adapter", Fixed),
            mock.patch.object(engine, "_publish", side_effect=publish),
            mock.patch.object(engine, "_read", side_effect=lambda path: published[path]),
            mock.patch.object(engine.owner, "_release_active_guard"),
            mock.patch.object(engine.owner, "_require_candidate_guard"),
        ):
            final = engine._finalize(manifest, object(), effect)
        self.assertEqual(final["schema"], "a90-h38-run02-rollback-continuation-final-v1")
        self.assertEqual(final["decision"], "V2321_HEALTHY_H38_RUN02_RECOVERED")

    def test_consumed_continuation_proves_exact_write_uncertain_return(self) -> None:
        module = load_module()
        result = module.consumed_rollback()
        self.assertFalse(result["completed"])
        self.assertEqual(
            result["outcome"],
            "BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_UNCERTAIN",
        )

    def test_physical_return_finalizer_is_menu_health_only(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        phase = source[
            source.index("def finalize_physical_return(") : source.index("def main(")
        ]
        self.assertIn("MenuHideObserver", phase)
        self.assertIn('"helperOutcomePromoted": False', phase)
        self.assertIn('"physicalButtonActionHostProved": False', phase)
        self.assertIn("owner._require_candidate_guard(manifest)", phase)
        for forbidden in ("engine.execute(", "fixed.flash(", "native_init_flash", "/usr/bin/adb"):
            self.assertNotIn(forbidden, phase)


if __name__ == "__main__":
    unittest.main()
