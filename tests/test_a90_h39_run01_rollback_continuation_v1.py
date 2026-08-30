"""Host-only constraints for the fixed H39 run-01 rollback continuation."""

import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/server-distro/a90_h39_run01_rollback_continuation_v1.py"


def load_module():
    sys.path.insert(0, str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("a90_h39_run01_recovery", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class H39Run01RollbackContinuationTests(unittest.TestCase):
    def test_exact_consumed_incident_is_bound(self) -> None:
        module = load_module()
        self.assertEqual(module.RUN_ID, "a90-h39-f1-20260830-01")
        self.assertEqual(len(module.RECORD_HASHES), 13)
        with (
            mock.patch.object(module.engine, "_review", return_value=("1" * 64, "2" * 64)),
            mock.patch.object(module.engine, "_require_guards"),
        ):
            manifest, _review, _closure, token = module.engine._fixed_context()
        self.assertEqual(
            manifest["candidate"]["sha256"],
            "5e74175c40d252cc9c38a2c918adad0d91d4b116eda8859142f2ea053064f796",
        )
        self.assertTrue(token.startswith(module.engine.APPROVAL_PREFIX))

    def test_surface_is_rollback_only_and_requires_existing_recovery(self) -> None:
        module = load_module()
        source = module.ENGINE_PATH.read_text(encoding="utf-8")
        execute = source[source.index("def execute(") : source.index("def main()")]
        self.assertIn("rollback=True", execute)
        self.assertNotIn("rollback=False", execute)
        self.assertNotIn('manifest["candidate"]', execute)
        self.assertIn("role != adapter.ADB_ROLE_RECOVERY", execute)

    def test_original_rollback_is_exact_pre_write_failure(self) -> None:
        module = load_module()
        stdout = (module.engine.OLD_LOG_DIR / "047-flash-rollback.stdout").read_bytes()
        stderr = (module.engine.OLD_LOG_DIR / "047-flash-rollback.stderr").read_bytes()
        receipt = module.owner.parse_canonical(stdout, "old rollback receipt")
        self.assertEqual(receipt["outcome"], "PRE_WRITE_FAILURE")
        self.assertIs(receipt["writeStarted"], False)
        self.assertIs(receipt["bootWrittenReadbackExact"], False)
        self.assertIs(receipt["systemReturnAttempted"], False)
        self.assertIn(module.engine.OLD_ROLLBACK_REQUIRED_STDERR, stderr)
        for forbidden in (
            b"phase.native_init_flash.adb_push.",
            b"phase.native_init_flash.boot_dd_write.",
            b"phase.native_init_flash.boot_readback_sha256.",
        ):
            self.assertNotIn(forbidden, stderr)

    def test_bad_approval_stops_before_live_adapter(self) -> None:
        module = load_module()
        with (
            mock.patch.object(
                module.engine,
                "_fixed_context",
                return_value=({}, "1" * 64, "2" * 64, "expected-token"),
            ),
            mock.patch.object(module.engine.adapter, "HostRunner") as runner,
        ):
            with self.assertRaisesRegex(module.engine.RecoveryError, "approval mismatch"):
                module.execute("wrong-token")
        runner.assert_not_called()

    def test_consumed_continuation_proves_confirmed_v2321_return(self) -> None:
        module = load_module()
        result = module.consumed_rollback()
        self.assertTrue(result["completed"])
        self.assertEqual(
            result["outcome"],
            "BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_CONFIRMED",
        )

    def test_menu_health_finalizer_has_no_flash_or_recovery_surface(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        phase = source[source.index("def finalize_menu_health(") : source.index("def main(")]
        self.assertIn("MenuHideObserver", phase)
        self.assertIn('"rollbackReplay": False', source)
        self.assertIn("owner._require_candidate_guard(manifest)", phase)
        for forbidden in (
            "engine.execute(",
            "fixed.flash(",
            "native_init_flash",
            "/usr/bin/adb",
            "recovery\n",
        ):
            self.assertNotIn(forbidden, phase)

    def test_menu_health_finalizer_publishes_before_active_only_release(self) -> None:
        module = load_module()
        snapshot = module.owner.Snapshot(
            target_evidence_sha256="0" * 64,
            boot_id="01234567-89ab-cdef-0123-456789abcdef",
            version=module.owner.V2321_ROLLBACK_VERSION,
            build=module.owner.V2321_ROLLBACK_BUILD,
            healthy=True,
            recovery_available=True,
            recovery_evidence_sha256="1" * 64,
            fresh_state_observed=False,
            fresh_state_absent=False,
            other_targets_untouched=True,
            receipt_sha256="2" * 64,
        )
        observation = SimpleNamespace(
            hide_receipt_sha256="3" * 64,
            same_boot=True,
            final_boot_id=snapshot.boot_id,
            snapshot=snapshot,
        )
        manifest = {
            "qualification": {"recoveryIdentity": {"adbSerialSha256": "4" * 64}},
            "rollback": {
                "version": module.owner.V2321_ROLLBACK_VERSION,
                "build": module.owner.V2321_ROLLBACK_BUILD,
            },
            "timeouts": {"healthSec": 90},
        }
        published = {}

        def publish(path, value):
            published[path] = module.owner.canonical_json(value)

        def read(path):
            if path == module.engine.REVIEW_PATH:
                return b"review"
            return published[path]

        observer = mock.Mock()
        observer.observe.return_value = observation
        with (
            mock.patch.object(
                module.engine,
                "_fixed_context",
                return_value=(manifest, "5" * 64, "6" * 64, "unused"),
            ),
            mock.patch.object(module, "consumed_rollback", return_value={"outcome": "confirmed"}),
            mock.patch.object(module, "prepare_finalize", return_value="approval"),
            mock.patch.object(module, "revalidate_finalize", return_value="7" * 64),
            mock.patch.object(module.engine, "_publish", side_effect=publish),
            mock.patch.object(module.engine, "_read", side_effect=read),
            mock.patch.object(module.engine.h28_menu.adapter, "HostRunner"),
            mock.patch.object(module.engine.h28_menu, "MenuHideObserver", return_value=observer),
            mock.patch.object(module.engine.h28_menu, "_validate_observation"),
            mock.patch.object(module.owner, "_release_active_guard") as release,
            mock.patch.object(module.owner, "_require_candidate_guard") as candidate,
        ):
            final = module.finalize_menu_health("approval")
        self.assertEqual(final["decision"], "V2321_HEALTHY_H39_RUN01_AFTER_CONFIRMED_ROLLBACK")
        self.assertIn(module.FINALIZE_INTENT, published)
        self.assertIn(module.engine.FINAL_PATH, published)
        release.assert_called_once_with(manifest)
        candidate.assert_called_once_with(manifest)

    def test_consumed_hide_is_exact_and_post_hide_has_no_second_send(self) -> None:
        module = load_module()
        module.consumed_menu_hide(allow_final=True)
        source = SCRIPT.read_text(encoding="utf-8")
        phase = source[source.index("def post_hide_finalize(") : source.index("def main(")]
        self.assertIn("observe_post_hide", phase)
        self.assertIn('"postHideAdditionalSendCount": 0', phase)
        self.assertNotIn("MenuHideObserver", phase)
        self.assertNotIn("finalize_menu_health", phase)
        self.assertNotIn("fixed.flash", phase)
        self.assertNotIn("hide\\n", phase)

    def test_closure_binds_wrapper_engine_test_and_contact_machinery(self) -> None:
        module = load_module()
        self.assertIn(module.SELF_PATH, module.engine.CLOSURE_PATHS)
        self.assertIn(module.TEST_PATH, module.engine.CLOSURE_PATHS)
        self.assertIn(module.ENGINE_PATH, module.engine.CLOSURE_PATHS)
        self.assertIn(module.ROOT / "docs/operations/targets/A90_TARGET_CONTRACT.md", module.engine.CLOSURE_PATHS)
        self.assertIn(
            module.ROOT / "workspace/public/src/scripts/revalidation/native_init_flash.py",
            module.engine.CLOSURE_PATHS,
        )
        self.assertEqual(len(module.execution_closure_sha256()), 64)

    def test_final_payload_uses_h39_schema_and_decision(self) -> None:
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
        self.assertEqual(final["schema"], "a90-h39-run01-rollback-continuation-final-v1")
        self.assertEqual(final["decision"], "V2321_HEALTHY_H39_RUN01_RECOVERED")


if __name__ == "__main__":
    unittest.main()
