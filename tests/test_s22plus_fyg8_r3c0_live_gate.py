import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/s22plus_fyg8_r3c0_live_gate.py"
)


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("s22plus_fyg8_r3c0_live_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusFyg8R3C0LiveGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_exact_candidate_and_rollback_pins(self):
        self.assertEqual(
            self.module.EXPECTED_CANDIDATE_BOOT_SHA256,
            "384efeb0f81534cbfaf3643f42e34fb6e01fe6f0b6bf80139a047a1f9a71f29f",
        )
        self.assertEqual(
            self.module.EXPECTED_CANDIDATE_AP_SHA256,
            "8f2b16d3ee8932ff927e06fee8956f975ec3f9e5cc0ef16337e00ad5108d3c00",
        )
        self.assertEqual(
            self.module.EXPECTED_MAGISK_AP_SHA256,
            "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
        )
        self.assertEqual(
            self.module.EXPECTED_STOCK_AP_SHA256,
            "2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94",
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

    def test_duplicate_and_unknown_timeline_events_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "timeline.json"
            events = []
            self.module.append_event(path, events, "live_session_start")
            with self.assertRaises(self.module.GateError):
                self.module.append_event(path, events, "live_session_start")
            with self.assertRaises(self.module.GateError):
                self.module.append_event(path, events, "not-a-phase")

    def test_offline_check_never_contacts_device_or_requires_active_policy(self):
        with mock.patch.object(
            self.module, "verify_artifacts", return_value={"candidate": "pinned"}
        ), mock.patch.object(
            self.module, "verify_policy_draft", return_value={"active": False}
        ), mock.patch.object(
            self.module, "current_android", side_effect=AssertionError("device contact")
        ), mock.patch.object(
            self.module, "odin_devices", side_effect=AssertionError("device contact")
        ), mock.patch.object(
            self.module, "policy_active", side_effect=AssertionError("active policy check")
        ), mock.patch("builtins.print"):
            self.assertEqual(self.module.main(["--offline-check"]), 0)

    def test_connected_dry_run_is_read_only_while_policy_inactive(self):
        baseline = {"boot_sha256": self.module.EXPECTED_MAGISK_BOOT_SHA256}
        with mock.patch.object(
            self.module, "verify_artifacts", return_value={"candidate": "pinned"}
        ), mock.patch.object(
            self.module, "verify_policy_draft", return_value={"active": False}
        ), mock.patch.object(
            self.module, "current_android", return_value=("serial", baseline)
        ), mock.patch.object(
            self.module, "odin_devices", return_value=[]
        ), mock.patch.object(
            self.module, "policy_active", side_effect=AssertionError("active policy check")
        ), mock.patch.object(
            self.module, "flash_exact", side_effect=AssertionError("device write")
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
                self.module, "current_android", side_effect=AssertionError("device contact")
            ), mock.patch.object(
                self.module, "odin_devices", side_effect=AssertionError("device contact")
            ):
                self.assertEqual(self.module.main([mode, "--ack", token]), 2)

    def test_real_policy_is_retired_and_not_active(self):
        root = Path.cwd()
        agents = (root / "AGENTS.md").read_text(encoding="utf-8")
        active_line = self.module.re.compile(
            rf"(?m)^\s*`?{self.module.re.escape(self.module.ACTIVE_SENTINEL)}`?\s*$"
        )
        self.assertIn("S22PLUS_FYG8_R3C0_POLICY_STATE=RETIRED", agents)
        self.assertIsNone(active_line.search(agents))
        self.assertFalse(self.module.policy_active(root))

    def test_empty_or_malformed_sha256_output_fails_closed(self):
        for value in ("", "not-a-hash  /dev/block/by-name/boot"):
            with self.subTest(value=value), self.assertRaises(self.module.GateError):
                self.module.sha256_output(value, "boot")
        valid = self.module.EXPECTED_MAGISK_BOOT_SHA256 + "  /dev/block/by-name/boot"
        self.assertEqual(
            self.module.sha256_output(valid, "boot"),
            self.module.EXPECTED_MAGISK_BOOT_SHA256,
        )

    def test_candidate_state_does_not_require_root(self):
        commands = []

        def fake_shell(_serial, command, *, root=False, timeout=30.0):
            commands.append((command, root, timeout))
            values = {
                "getprop ro.product.model": "SM-S906N",
                "getprop ro.product.device": "g0q",
                "getprop ro.boot.bootloader": "S906NKSS7FYG8",
                "getprop ro.build.version.incremental": "S906NKSS7FYG8",
                "getprop sys.boot_completed": "1",
                "getprop init.svc.bootanim": "stopped",
                "getprop ro.boot.verifiedbootstate": "orange",
                "uname -r": self.module.EXPECTED_RELEASE,
                "cat /proc/version": self.module.EXPECTED_PROC_VERSION,
            }
            return values[command]

        with mock.patch.object(self.module, "adb_serial", return_value="serial"), mock.patch.object(
            self.module, "adb_shell", side_effect=fake_shell
        ):
            _, state = self.module.candidate_android_once()
        self.assertEqual(state["boot_completed"], "1")
        self.assertFalse(any(root for _, root, _ in commands))

    def test_candidate_sampling_requires_stable_serial(self):
        state = {"boot_completed": "1"}
        with mock.patch.object(
            self.module,
            "candidate_android_once",
            side_effect=[("serial-a", state), ("serial-b", state)],
        ), mock.patch.object(self.module.time, "sleep"), mock.patch.object(
            self.module.time, "monotonic", side_effect=[0.0, 0.0, 1.0]
        ):
            serial, samples, error = self.module.wait_candidate_android(0.01, 2, 0)
        self.assertIsNone(serial)
        self.assertEqual(samples, [])
        self.assertIn("serial changed", error)

    def test_recovery_only_rollback_has_complete_timeline(self):
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            self.module, "odin_devices", return_value=["/dev/fake-odin"]
        ), mock.patch.object(
            self.module, "flash_rollback", return_value="magisk"
        ), mock.patch.object(
            self.module,
            "wait_final_android",
            return_value=({"boot": "magisk"}, "PASS_MAGISK_ROLLBACK", 0),
        ):
            run_dir = Path(temporary)
            result = self.module.rollback_from_download(
                Path.cwd(), Path("/fake/odin4"), run_dir
            )
            timeline = json.loads((run_dir / "timeline.json").read_text(encoding="utf-8"))
            self.assertEqual(
                [event["name"] for event in timeline["events"]],
                list(self.module.TIMELINE_NAMES),
            )
            self.assertEqual(result["verdict"], "PASS_MAGISK_ROLLBACK_FROM_DOWNLOAD")

    def test_stock_cleanup_is_non_pass(self):
        with mock.patch.object(
            self.module, "wait_stock_android", return_value={"boot": "stock"}
        ), mock.patch.object(self.module, "odin_devices", return_value=[]):
            _, verdict, rc = self.module.wait_final_android(
                "stock", 1, Path("/fake/odin4"), Path("/dev/null")
            )
        self.assertNotEqual(rc, 0)
        self.assertIn("STOCK_CLEANUP", verdict)

    def test_final_android_rejects_remaining_odin_endpoint(self):
        with mock.patch.object(
            self.module, "wait_android", return_value=("serial", {"boot": "magisk"})
        ), mock.patch.object(
            self.module, "odin_devices", return_value=["/dev/fake-odin"]
        ):
            with self.assertRaises(self.module.GateError):
                self.module.wait_final_android(
                    "magisk", 1, Path("/fake/odin4"), Path("/dev/null")
                )

    def test_magisk_flash_failure_uses_stock_only_with_one_odin(self):
        with mock.patch.object(
            self.module,
            "flash_exact",
            side_effect=[self.module.GateError("magisk failed"), None],
        ) as flash, mock.patch.object(
            self.module, "odin_devices", return_value=["/dev/fake-odin"]
        ):
            target = self.module.flash_rollback(
                Path.cwd(), Path("/fake/odin4"), "/dev/fake-odin", Path("/dev/null")
            )
        self.assertEqual(target, "stock")
        self.assertEqual(flash.call_count, 2)

    def test_live_verdict_matrix(self):
        cases = (
            (
                "magisk",
                "PASS_MAGISK_ROLLBACK",
                0,
                True,
                [{"boot_completed": "1"}],
                "PASS_R3C0_NORMALIZED_STOCK_CARRIER_AND_ROLLED_BACK",
                0,
            ),
            (
                "magisk",
                "PASS_MAGISK_ROLLBACK",
                0,
                False,
                [],
                "NO_PROOF_CANDIDATE_TRANSFER_FAILED_MAGISK_ROLLED_BACK",
                31,
            ),
            (
                "magisk",
                "PASS_MAGISK_ROLLBACK",
                0,
                True,
                [],
                "NO_PROOF_NO_CANDIDATE_ANDROID_MILESTONE_MAGISK_ROLLED_BACK",
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

    def test_one_shot_consumption_is_durable_and_blocks_reuse(self):
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
        recovery = {"verdict": "STOCK_CLEANUP_MAGISK_BASELINE_NOT_RESTORED", "exit_code": 30}
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

    def test_live_source_orders_policy_before_baseline(self):
        source = SCRIPT.read_text(encoding="utf-8")
        live = source.split("def live_run(", 1)[1].split("def build_parser(", 1)[0]
        self.assertLess(live.index("policy_active(root)"), live.index("current_android()"))
        main = source.split("def main(", 1)[1]
        self.assertLess(
            main.index("if not policy_active(root):"),
            main.index("if args.rollback_from_download:"),
        )
        self.assertNotIn("--repartition", source)


if __name__ == "__main__":
    unittest.main()
