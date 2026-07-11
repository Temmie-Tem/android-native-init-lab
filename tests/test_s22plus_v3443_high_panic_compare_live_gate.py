import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_v3443_high_panic_compare_live_gate.py"
)


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("s22plus_v3443_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class V3443HighPanicCompareTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_pinned_mid_control_is_exact_and_complete(self):
        control = self.module.verify_mid_control(Path("."))
        self.assertEqual(control["preamble"]["classification"], "NEGATIVE_ACK")
        counts = control["last_kmsg"]["signature_counts"]
        for name in (
            "run_marker",
            "sysrq_panic",
            "rdx_locked",
            "upload_cause_kernel_panic",
        ):
            self.assertGreater(counts[name], 0)

    def test_preamble_classifier_never_authorizes_probe(self):
        self.assertEqual(
            self.module.classify_preamble(self.module.NEGATIVE_ACK), "NEGATIVE_ACK"
        )
        self.assertEqual(
            self.module.classify_preamble(self.module.POSITIVE_ACK),
            "POSITIVE_ACK_STOPPED_BEFORE_PROBE",
        )
        self.assertEqual(
            self.module.classify_preamble(b"unknown"),
            "UNEXPECTED_RESPONSE_STOPPED",
        )

    def test_source_contains_only_preamble_command_payload(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('PREAMBLE = b"PrEaMbLe\\0"', source)
        self.assertNotIn('b"PrObE\\0"', source)
        self.assertNotIn('b"DaTaXfEr\\0"', source)
        self.assertNotIn("parse_probe_table", source)
        self.assertNotIn("sboot_two_command_probe", source)

    def test_clean_sysrq_return_waits_for_delayed_adb_loss(self):
        connected = iter((True, True, False))
        with mock.patch.object(
            self.module.high,
            "run",
            return_value=mock.Mock(returncode=0, stdout=""),
        ), mock.patch.object(
            self.module,
            "adb_connected",
            side_effect=lambda serial: next(connected),
        ), mock.patch.object(self.module.time, "sleep", return_value=None):
            self.module.trigger_one_sysrq_panic("SERIAL", "a" * 32)

    def test_compound_root_command_is_one_quoted_remote_shell_argument(self):
        output = "\n".join(
            (
                "uid=0(root) gid=0(root) context=u:r:magisk:s0",
                "uid=0(root) gid=0(root) context=u:r:magisk:s0",
            )
        )
        with mock.patch.object(
            self.module.high,
            "run",
            return_value=mock.Mock(returncode=0, stdout=output),
        ) as run:
            result = self.module.verify_root_compound_shell("SERIAL")
            self.assertEqual(result["root_line_count"], 2)
            command = run.call_args.args[0]
            self.assertEqual(command[:5], ["adb", "-s", "SERIAL", "shell", "su -c 'id; id'"])
            self.assertEqual(len(command), 5)

    def test_compound_root_control_rejects_split_scope(self):
        output = "\n".join(
            (
                "uid=0(root) gid=0(root) context=u:r:magisk:s0",
                "uid=2000(shell) gid=2000(shell) context=u:r:shell:s0",
            )
        )
        with mock.patch.object(
            self.module.high,
            "run",
            return_value=mock.Mock(returncode=0, stdout=output),
        ):
            with self.assertRaisesRegex(self.module.GateError, "root-shell control"):
                self.module.verify_root_compound_shell("SERIAL")

    def test_panic_rejects_persistently_connected_adb(self):
        ticks = iter((0.0, 0.0, 21.0))
        with mock.patch.object(
            self.module.high,
            "run",
            return_value=mock.Mock(returncode=0, stdout=""),
        ), mock.patch.object(
            self.module, "adb_connected", return_value=True
        ), mock.patch.object(
            self.module.time, "monotonic", side_effect=lambda: next(ticks)
        ), mock.patch.object(self.module.time, "sleep", return_value=None):
            with self.assertRaisesRegex(self.module.GateError, "ADB remained"):
                self.module.trigger_one_sysrq_panic("SERIAL", "b" * 32)

    def test_comparison_reports_ack_and_metric_deltas(self):
        mid = {
            "preamble": {"classification": "NEGATIVE_ACK"},
            "last_kmsg": {
                "bytes": 100,
                "lines": 10,
                "signature_counts": {
                    "run_marker": 1,
                    "sysrq_panic": 1,
                    "rdx_locked": 1,
                    "upload_cause_kernel_panic": 1,
                    "ramdump": 2,
                    "minidump": 3,
                    "sec_debug": 4,
                    "rst_exinfo": 0,
                },
            },
        }
        high_result = {
            "preamble": {"classification": "POSITIVE_ACK_STOPPED_BEFORE_PROBE"},
            "last_kmsg": {
                "bytes": 120,
                "lines": 12,
                "signature_counts": {
                    "run_marker": 1,
                    "sysrq_panic": 1,
                    "rdx_locked": 0,
                    "upload_cause_kernel_panic": 1,
                    "ramdump": 4,
                    "minidump": 3,
                    "sec_debug": 5,
                    "rst_exinfo": 1,
                },
            },
        }
        result = self.module.compare_evidence(mid, high_result)
        self.assertTrue(result["preamble_changed"])
        self.assertEqual(result["last_kmsg_bytes_delta"], 20)
        self.assertEqual(result["signature_count_delta"]["ramdump"], 2)
        self.assertFalse(result["core_evidence_present"])

    def test_timeline_is_exact_single_events_schema(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "timeline.json"
            events = []
            for name in self.module.TIMELINE_NAMES:
                self.module.append_event(path, events, name)
            value = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(set(value), {"events"})
            self.assertEqual(
                [event["name"] for event in value["events"]],
                list(self.module.TIMELINE_NAMES),
            )

    def test_inactive_policy_blocks_before_device_contact(self):
        with mock.patch.object(
            self.module, "policy_active", return_value=False
        ), mock.patch.object(
            self.module, "verify_mid_control", side_effect=AssertionError("device")
        ):
            self.assertEqual(self.module.main(["--dry-run"]), 2)

    def test_emergency_mode_verifies_artifacts_before_recovery(self):
        with mock.patch.object(
            self.module, "policy_active", return_value=True
        ), mock.patch.object(
            self.module.high,
            "verify_setter",
            side_effect=self.module.high.GateError("artifact mismatch"),
        ) as verify, mock.patch.object(
            self.module, "emergency_recovery", side_effect=AssertionError("recovery reached")
        ):
            self.assertEqual(
                self.module.main(
                    [
                        "--recover-high-from-download",
                        "--recovery-ack",
                        self.module.RECOVERY_ACK_TOKEN,
                    ]
                ),
                2,
            )
            verify.assert_called_once()


if __name__ == "__main__":
    unittest.main()
