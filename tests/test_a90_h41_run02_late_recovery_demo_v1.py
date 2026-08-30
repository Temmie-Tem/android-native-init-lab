"""Host-only safety surface for the exact H41 late-Recovery demo transaction."""

import importlib.util
from pathlib import Path
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/server-distro/a90_h41_run02_late_recovery_demo_v1.py"


def load_module():
    sys.path.insert(0, str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("a90_h41_late_demo", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class H41LateRecoveryDemoTests(unittest.TestCase):
    def test_exact_run_manifest_and_consumed_prefix(self) -> None:
        module = load_module()
        self.assertEqual(module.RUN_ID, "a90-h41-f1-20260830-02")
        self.assertEqual(
            module.MANIFEST_SHA256,
            "eacd2090683e842314dcdfe9e4a1ae16bdb5eb35af5ede0a4b917653e0c6fe40",
        )
        self.assertEqual(len(module.ORIGINAL_RECORD_HASHES), 4)
        self.assertEqual(len(module.ORIGINAL_LOG_HASHES), 22)
        self.assertEqual(
            tuple(module.ORIGINAL_RECORD_HASHES),
            (
                "00-prepared.json", "10-approved.json",
                "11-recovery-transition-intent.json",
                "13-recovery-transition-parked.json",
            ),
        )

    def test_candidate_and_rollback_are_distinct_one_shot_phases(self) -> None:
        module = load_module()
        self.assertEqual(module.INSTALL_PATH[-1], "23-demo-window.json")
        self.assertEqual(module.ROLLBACK_PATH[: len(module.INSTALL_PATH)], module.INSTALL_PATH)
        self.assertEqual(module.ROLLBACK_PATH[-1], "40-final.json")
        source = SCRIPT.read_text(encoding="utf-8")
        install = source[source.index("def install(") : source.index("def _effect_result(")]
        rollback = source[source.index("def rollback(") : source.index("def main(")]
        self.assertLess(install.index('"00-transaction-intent.json"'), install.index("_publish_candidate_guard"))
        self.assertLess(install.index('"20-candidate-intent.json"'), install.index('"21-candidate-launched.json"'))
        self.assertLess(install.index('"21-candidate-launched.json"'), install.index("live.flash("))
        self.assertIn("recovery_binding=binding", install)
        self.assertLess(rollback.index('"30-rollback-intent.json"'), rollback.index('"31-rollback-launched.json"'))
        self.assertLess(rollback.index('"31-rollback-launched.json"'), rollback.index("live.flash("))
        self.assertNotIn("_publish_candidate_guard", rollback)

    def test_late_recovery_never_replays_transition(self) -> None:
        module = load_module()
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("prepare_candidate_recovery", source)
        self.assertNotIn("fixed_recovery_transition_argv", source)
        self.assertIn("recoveryTransitionReplay\": False", source)
        self.assertIn('request_outcome="UNCERTAIN_RESPONSE"', source)
        self.assertIn("adapter.ADB_ROLE_RECOVERY", source)

    def test_demo_is_unproved_and_final_release_requires_healthy_rollback(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("H41_MANUAL_DEMO_WINDOW_UNPROVED", source)
        self.assertIn('"runtimeProved": False', source)
        self.assertIn('"h41RuntimeProved": False', source)
        self.assertIn("_validate_install_prefix", source)
        final_block = source[source.index("healthy = (") : source.index("return final", source.index("healthy = ("))]
        self.assertIn("BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_CONFIRMED", final_block)
        self.assertIn("_validate_final", source)
        self.assertIn("owner._release_active_guard", final_block)
        self.assertIn("owner._require_candidate_guard", final_block)

    def test_review_is_outside_exact_execution_closure(self) -> None:
        module = load_module()
        self.assertRegex(module.execution_closure_sha256(), r"^[0-9a-f]{64}$")
        source = SCRIPT.read_text(encoding="utf-8")
        closure = source[source.index("def execution_closure_sha256") : source.index("def _review_lease")]
        self.assertNotIn("REVIEW", closure)

    def test_manual_rollback_requires_both_confirmations_before_any_effect(self) -> None:
        module = load_module()
        for attended, closed in ((False, False), (True, False), (False, True)):
            with (
                mock.patch.object(module, "_original_context") as context,
                mock.patch.object(module, "_publish") as publish,
                mock.patch.object(module, "_adapter") as live_adapter,
            ):
                with self.assertRaisesRegex(
                    module.DemoError,
                    "manual rollback requires attended exact menu-close confirmation",
                ):
                    module.rollback(
                        "token",
                        operator_attended=attended,
                        menu_closed_confirmed=closed,
                    )
                context.assert_not_called()
                publish.assert_not_called()
                live_adapter.assert_not_called()

    def test_automatic_rollback_does_not_forge_manual_confirmation(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"operatorAttended": operator_attended', source)
        self.assertIn('"menuClosedConfirmed": menu_closed_confirmed', source)
        self.assertIn("_validate_rollback_prefix", source)
        self.assertIn('rollback(approval, automatic=True)', source)


if __name__ == "__main__":
    unittest.main()
