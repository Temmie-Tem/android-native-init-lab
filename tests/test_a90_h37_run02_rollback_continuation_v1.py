"""Host-only tests for the fixed H37 run-02 rollback continuation."""

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/server-distro/a90_h37_run02_rollback_continuation_v1.py"


def load_module():
    sys.path.insert(0, str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("a90_h37_run02_recovery", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class H37Run02RollbackContinuationTests(unittest.TestCase):
    def test_fixed_incident_context_accepts_only_retained_bytes(self) -> None:
        module = load_module()
        with (
            mock.patch.object(module, "_review", return_value=("1" * 64, "2" * 64)),
            mock.patch.object(module, "_require_guards"),
        ):
            manifest, review_sha, closure, token = module._fixed_context()
        self.assertEqual(manifest["runId"], module.RUN_ID)
        self.assertEqual(review_sha, "1" * 64)
        self.assertEqual(closure, "2" * 64)
        self.assertTrue(token.startswith(module.APPROVAL_PREFIX))

    def test_execution_surface_is_rollback_only(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        execute = source[source.index("def execute(") : source.index("def main()")]
        self.assertIn("rollback=True", execute)
        self.assertNotIn("rollback=False", execute)
        self.assertNotIn("manifest[\"candidate\"]", execute)
        self.assertIn("originalRollbackReplay\": False", execute)
        self.assertIn("role != adapter.ADB_ROLE_RECOVERY", execute)
        self.assertIn("owner_adb_role=role", execute)

    def test_closure_binds_contact_machinery_and_contract(self) -> None:
        module = load_module()
        names = {path.name for path in module.CLOSURE_PATHS}
        self.assertIn("A90_TARGET_CONTRACT.md", names)
        self.assertIn("native_init_flash.py", names)
        self.assertIn("a90_boot_only_f1_adapter_v1.py", names)
        self.assertIn("a90_h28_menu_hide_health_reconcile_v1.py", names)
        self.assertIn("a90_controller.c", names)
        self.assertIn("40_menu_apps.inc.c", names)
        self.assertIn("80_shell_dispatch.inc.c", names)
        self.assertIn("a90_serial_redaction_v1.py", names)
        self.assertIn("_workspace_bootstrap.py", names)
        self.assertEqual(len(module.execution_closure_sha256()), 64)

    def test_native_role_stops_before_sidecar_intent(self) -> None:
        module = load_module()
        manifest = {"qualification": {}}

        class FakeFixed:
            def __init__(self, *_args, **_kwargs):
                pass

            def _effect_inventory(self, *, rollback):
                return module.adapter.ADB_ROLE_NATIVE, "a" * 64, None

        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            with (
                mock.patch.object(module, "CONT_DIR", root / "cont"),
                mock.patch.object(module, "LIVE_LOG_DIR", root / "logs"),
                mock.patch.object(module, "_fixed_context", return_value=(manifest, "1" * 64, "2" * 64, "ok")),
                mock.patch.object(module.adapter, "HostRunner", return_value=object()),
                mock.patch.object(module.adapter, "FixedA90Adapter", FakeFixed),
            ):
                with self.assertRaisesRegex(module.RecoveryError, "TWRP Recovery"):
                    module.execute("ok")
            self.assertFalse((root / "cont").exists())

    def test_guard_drift_after_recovery_inventory_stops_before_intent(self) -> None:
        module = load_module()
        manifest = {"qualification": {}}

        class FakeFixed:
            def __init__(self, *_args, **_kwargs):
                pass

            def _effect_inventory(self, *, rollback):
                return module.adapter.ADB_ROLE_RECOVERY, "a" * 64, "b" * 64

        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            with (
                mock.patch.object(module, "CONT_DIR", root / "cont"),
                mock.patch.object(module, "LIVE_LOG_DIR", root / "logs"),
                mock.patch.object(module, "_fixed_context", return_value=(manifest, "1" * 64, "2" * 64, "ok")),
                mock.patch.object(module, "_verify_historical_qualification"),
                mock.patch.object(module, "_require_guards", side_effect=module.RecoveryError("guard drift")),
                mock.patch.object(module.adapter, "HostRunner", return_value=object()),
                mock.patch.object(module.adapter, "FixedA90Adapter", FakeFixed),
            ):
                with self.assertRaisesRegex(module.RecoveryError, "guard drift"):
                    module.execute("ok")
            self.assertFalse((root / "cont").exists())

    def test_physical_return_phase_is_health_only_and_keeps_helper_unproved(self) -> None:
        module = load_module()
        source = SCRIPT.read_text(encoding="utf-8")
        phase = source[
            source.index("def finalize_physical_return(") : source.index("def _finalize(")
        ]
        self.assertIn("fixed.observe(", phase)
        self.assertNotIn("fixed.flash(", phase)
        self.assertIn('"helperOutcomePromoted": False', phase)
        self.assertIn('"physicalButtonActionHostProved": False', phase)
        self.assertIn("owner._require_candidate_guard(manifest)", phase)

    def test_consumed_uncertain_receipt_proves_exact_write_without_return(self) -> None:
        module = load_module()
        result = module._consumed_uncertain_effect()
        self.assertFalse(result["completed"])
        self.assertEqual(
            result["outcome"],
            "BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_UNCERTAIN",
        )

    def test_consumed_health_attempt_is_exact_menu_busy_before_health(self) -> None:
        module = load_module()
        module._consumed_finalize_busy()
        self.assertEqual(
            set(module.FINALIZE_BUSY_LOG_HASHES),
            {
                "001-usb-inventory.stdout", "001-usb-inventory.stderr",
                "002-bridge-preflight.stdout", "002-bridge-preflight.stderr",
                "003-boot-id-start.stdout", "003-boot-id-start.stderr",
            },
        )

    def test_menu_hide_phase_is_one_shot_health_only(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        phase = source[
            source.index("def menu_hide_finalize(") : source.index("def _finalize(")
        ]
        self.assertIn("h28_menu.MenuHideObserver", phase)
        self.assertIn("MENU_FINALIZE_INTENT_PATH", phase)
        self.assertIn('"menuHideSendCount": 1', phase)
        self.assertIn('"helperOutcomePromoted": False', phase)
        self.assertIn('"physicalButtonActionHostProved": False', phase)
        self.assertIn("owner._require_candidate_guard(manifest)", phase)
        for forbidden in ("fixed.flash(", "subprocess", "os.system", "native_init_flash"):
            self.assertNotIn(forbidden, phase)

    def test_menu_hide_prepare_rejects_consumed_namespace(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            intent = root / "intent.json"
            intent.write_text("consumed", encoding="utf-8")
            with (
                mock.patch.object(module, "MENU_FINALIZE_INTENT_PATH", intent),
                mock.patch.object(module, "MENU_FINALIZE_RECEIPT_PATH", root / "receipt.json"),
                mock.patch.object(module, "MENU_FINALIZE_LOG_DIR", root / "logs"),
                mock.patch.object(module, "FINAL_PATH", root / "final.json"),
                mock.patch.object(module, "_fixed_context", return_value=({}, "1" * 64, "2" * 64, "unused")),
                mock.patch.object(module, "_consumed_uncertain_effect"),
                mock.patch.object(module, "_consumed_finalize_busy"),
            ):
                with self.assertRaisesRegex(module.RecoveryError, "already consumed"):
                    module.prepare_menu_finalize()

    def test_closure_binds_reviewed_h28_menu_hide_engine(self) -> None:
        module = load_module()
        self.assertIn(module.H28_MENU_PATH, module.CLOSURE_PATHS)
        self.assertEqual(module.h28_menu.MENU_SETTLE_SEC, 3.0)
        self.assertEqual(module.MENU_HIDE_WIRE_SHA256, module._sha(b"hide\n"))
        self.assertEqual(len(module.execution_closure_sha256()), 64)

    def test_consumed_hide_is_exact_fixed_accepted_response(self) -> None:
        module = load_module()
        module._consumed_menu_hide_request(allow_final=True)
        raw = (module.MENU_FINALIZE_LOG_DIR / "003-menu-hide.stdout").read_bytes()
        self.assertEqual(
            raw, b"hide\r\n[busy] auto menu active; hide requested\r\n"
        )

    def test_consumed_hide_allows_final_only_for_post_readback_recheck(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as name:
            final = Path(name) / "20-final.json"
            final.write_text("published", encoding="utf-8")
            with mock.patch.object(module, "FINAL_PATH", final):
                with self.assertRaisesRegex(module.RecoveryError, "unexpectedly published"):
                    module._consumed_menu_hide_request()
                module._consumed_menu_hide_request(allow_final=True)

    def test_post_hide_last_recheck_explicitly_allows_readback_final(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        phase = source[
            source.index("def post_hide_finalize(") : source.index("def _finalize(")
        ]
        publish = phase.index("_publish(FINAL_PATH, final)")
        readback = phase.index("_read(FINAL_PATH) != expected_raw")
        allow = phase.index("allow_final=True")
        release = phase.index("owner._release_active_guard(manifest)")
        self.assertLess(publish, readback)
        self.assertLess(readback, allow)
        self.assertLess(allow, release)

    def test_post_hide_phase_cannot_send_hide_or_other_effect(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        phase = source[
            source.index("def post_hide_finalize(") : source.index("def _finalize(")
        ]
        self.assertIn("observe_post_hide", phase)
        self.assertIn('"postHideAdditionalSendCount": 0', phase)
        self.assertIn("owner._require_candidate_guard(manifest)", phase)
        for forbidden in (
            "MenuHideObserver.observe(", "_raw_hide(", "sendall(", "fixed.flash(",
            "subprocess", "os.system", "native_init_flash",
        ):
            self.assertNotIn(forbidden, phase)

    def test_post_hide_observer_command_order_has_no_hide(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        observer = source[
            source.index("class PostHideObserver(") : source.index("def prepare_post_hide(")
        ]
        expected = '("boot-id", "version", "selftest", "status", "boot-id-final")'
        self.assertIn(expected, observer)
        self.assertNotIn('b"hide\\n"', observer)
        self.assertNotIn("_raw_hide", observer)


if __name__ == "__main__":
    unittest.main()
