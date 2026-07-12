import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/s22plus_fyg8_r3c1_live_gate.py"
)


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("s22plus_fyg8_r3c1_live_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusFyg8R3C1LiveGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_exact_candidate_and_rollback_pins(self):
        self.assertEqual(
            self.module.EXPECTED_CANDIDATE_BOOT_SHA256,
            "e1f0be9933e9c76d881a2cc39c0431bf54930ee0f216f55de4d7a166a60d120c",
        )
        self.assertEqual(
            self.module.EXPECTED_CANDIDATE_AP_SHA256,
            "023d7780e11363bd152900e28279233a0fd66ce8dd8902417d23eb781f613fb4",
        )
        self.assertEqual(
            self.module.common.EXPECTED_MAGISK_AP_SHA256,
            "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
        )
        self.assertEqual(
            self.module.common.EXPECTED_STOCK_AP_SHA256,
            "2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94",
        )

    def test_real_manifest_matches_live_gate_contract(self):
        root = Path.cwd()
        data = self.module.verify_manifest(root / self.module.DEFAULT_MANIFEST)
        self.assertEqual(data["verdict"], "PASS_R3C1_ARTIFACT_BUILT_HOST_ONLY")
        self.assertEqual(
            data["construction"]["difference"]["outside_kernel_changed_byte_count"],
            0,
        )

    def test_timeline_has_only_standard_events_shape(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "timeline.json"
            events = []
            for name in self.module.TIMELINE_NAMES:
                self.module.append_event(path, events, name)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(set(payload), {"events"})
            self.assertEqual(
                [event["name"] for event in payload["events"]],
                list(self.module.TIMELINE_NAMES),
            )
            self.assertTrue(
                all(set(event) == {"name", "timestamp_utc"} for event in payload["events"])
            )

    def test_offline_check_never_contacts_device_or_requires_active_policy(self):
        with mock.patch.object(
            self.module, "verify_artifacts", return_value={"candidate": "pinned"}
        ), mock.patch.object(
            self.module, "verify_policy_draft", return_value={"active": False}
        ), mock.patch.object(
            self.module.common,
            "current_android",
            side_effect=AssertionError("device contact"),
        ), mock.patch.object(
            self.module.common,
            "odin_devices",
            side_effect=AssertionError("device contact"),
        ), mock.patch.object(
            self.module, "policy_active", side_effect=AssertionError("active policy check")
        ), mock.patch("builtins.print"):
            self.assertEqual(self.module.main(["--offline-check"]), 0)

    def test_connected_dry_run_is_read_only_while_policy_inactive(self):
        baseline = {"boot_sha256": self.module.common.EXPECTED_MAGISK_BOOT_SHA256}
        with mock.patch.object(
            self.module, "verify_artifacts", return_value={"candidate": "pinned"}
        ), mock.patch.object(
            self.module, "verify_policy_draft", return_value={"active": False}
        ), mock.patch.object(
            self.module.common, "current_android", return_value=("serial", baseline)
        ), mock.patch.object(
            self.module.common, "odin_devices", return_value=[]
        ), mock.patch.object(
            self.module, "policy_active", side_effect=AssertionError("active policy check")
        ), mock.patch.object(
            self.module.common, "flash_exact", side_effect=AssertionError("device write")
        ), mock.patch("builtins.print"):
            self.assertEqual(self.module.main(["--connected-dry-run"]), 0)

    def test_inactive_policy_blocks_live_modes_before_device_contact(self):
        for mode, token in (
            ("--live", self.module.LIVE_ACK_TOKEN),
            ("--rollback-from-download", self.module.ROLLBACK_ACK_TOKEN),
        ):
            with self.subTest(mode=mode), mock.patch.object(
                self.module, "verify_artifacts", return_value={"candidate": "pinned"}
            ), mock.patch.object(
                self.module, "verify_policy_draft", return_value={"active": False}
            ), mock.patch.object(
                self.module, "policy_active", return_value=False
            ), mock.patch.object(
                self.module.common,
                "current_android",
                side_effect=AssertionError("device contact"),
            ), mock.patch.object(
                self.module.common,
                "odin_devices",
                side_effect=AssertionError("device contact"),
            ):
                self.assertEqual(self.module.main([mode, "--ack", token]), 2)

    def test_real_policy_is_pending_and_not_active(self):
        root = Path.cwd()
        agents = (root / "AGENTS.md").read_text(encoding="utf-8")
        active_line = self.module.re.compile(
            rf"(?m)^\s*`?{self.module.re.escape(self.module.ACTIVE_SENTINEL)}`?\s*$"
        )
        self.assertIn(self.module.PENDING_SENTINEL, agents)
        self.assertIsNone(active_line.search(agents))
        self.assertFalse(self.module.policy_active(root))

    def test_live_verdict_matrix(self):
        cases = (
            (
                "magisk",
                "PASS_MAGISK_ROLLBACK",
                0,
                True,
                [{"boot_completed": "1"}],
                "PASS_R3C1_UNPATCHED_REBUILT_KERNEL_VIABLE_AND_ROLLED_BACK",
                0,
            ),
            (
                "magisk",
                "PASS_MAGISK_ROLLBACK",
                0,
                False,
                [],
                "NO_PROOF_R3C1_CANDIDATE_TRANSFER_FAILED_MAGISK_ROLLED_BACK",
                31,
            ),
            (
                "magisk",
                "PASS_MAGISK_ROLLBACK",
                0,
                True,
                [],
                "NO_PROOF_NO_R3C1_CANDIDATE_ANDROID_MILESTONE_MAGISK_ROLLED_BACK",
                32,
            ),
            (
                "stock",
                "STOCK_CLEANUP_MAGISK_BASELINE_NOT_RESTORED",
                30,
                True,
                [{"boot_completed": "1"}],
                "STOCK_CLEANUP_MAGISK_BASELINE_NOT_RESTORED",
                30,
            ),
        )
        for target, rollback_verdict, rollback_rc, transferred, samples, verdict, rc in cases:
            with self.subTest(verdict=verdict):
                self.assertEqual(
                    self.module.classify_live_verdict(
                        target, rollback_verdict, rollback_rc, transferred, samples
                    ),
                    (verdict, rc),
                )

    def test_one_shot_consumption_is_separate_from_r3c0(self):
        self.assertNotEqual(
            self.module.CONSUMED_STATE, self.module.common.CONSUMED_STATE
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "workspace/private/runs/run"
            run_dir.mkdir(parents=True)
            self.module.ensure_not_consumed(root)
            self.module.consume_exception(root, run_dir)
            state = json.loads(
                self.module.consumed_state_path(root).read_text(encoding="utf-8")
            )
            self.assertEqual(state["reason"], "candidate_flash_start")
            with self.assertRaises(self.module.GateError):
                self.module.ensure_not_consumed(root)

    def test_recovery_entrypoint_propagates_stock_cleanup_exit_code(self):
        recovery = {
            "verdict": "STOCK_CLEANUP_MAGISK_BASELINE_NOT_RESTORED",
            "exit_code": 30,
        }
        with mock.patch.object(
            self.module, "verify_artifacts", return_value={"candidate": "pinned"}
        ), mock.patch.object(
            self.module, "verify_policy_draft", return_value={"active": True}
        ), mock.patch.object(
            self.module, "policy_active", return_value=True
        ), mock.patch.object(
            self.module, "rollback_from_download", return_value=recovery
        ), mock.patch.object(Path, "mkdir"), mock.patch("builtins.print"):
            self.assertEqual(
                self.module.main(
                    ["--rollback-from-download", "--ack", self.module.ROLLBACK_ACK_TOKEN]
                ),
                30,
            )

    def test_source_has_no_nonboot_or_debug_transport_actions(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in (
            "--repartition",
            "fastboot",
            "/proc/sysrq-trigger",
            "PrEaMbLe",
            "DaTaXfEr",
            "vendor_boot.img",
            "recovery.img",
            "dtbo.img",
            "vbmeta.img",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn("common.flash_exact", source)
        self.assertIn("common.flash_rollback", source)


if __name__ == "__main__":
    unittest.main()
