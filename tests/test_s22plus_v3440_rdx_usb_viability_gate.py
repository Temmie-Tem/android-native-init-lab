import importlib.util
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_v3440_rdx_usb_viability_gate.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("s22plus_v3440_rdx", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class V3440RdxUsbViabilityGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_classification_prefers_exact_samsung_rdx(self):
        snapshot = [
            {"vid": "04e8", "pid": "685d"},
            {"vid": "05c6", "pid": "900e"},
        ]
        self.assertEqual(
            self.module.classify_snapshot(snapshot),
            "SAMSUNG_SBOOT_RDX_04E8_685D",
        )

    def test_android_mtp_is_not_rdx(self):
        snapshot = [{"vid": "04e8", "pid": "6860"}]
        self.assertEqual(
            self.module.classify_snapshot(snapshot), "NO_SUPPORTED_RDX_ENDPOINT"
        )

    def test_only_two_discovery_commands_are_allowed(self):
        for command in self.module.ALLOWED_SBOOT_COMMANDS:
            self.module.validate_sboot_command(command)
        for forbidden in (b"DaTaXfEr\0", b"PoWeRdOwN\0", b"AcKnOwLeDgMeNt\0"):
            with self.assertRaisesRegex(self.module.GateError, "forbidden"):
                self.module.validate_sboot_command(forbidden)

    def test_negative_ack_stops_before_probe(self):
        with self.assertRaisesRegex(self.module.GateError, "NegativeAck"):
            self.module.validate_preamble_ack(self.module.NEGATIVE_ACK)
        self.module.validate_preamble_ack(self.module.POSITIVE_ACK)

    def test_panic_transport_timeout_is_expected(self):
        with mock.patch.object(
            self.module,
            "run",
            side_effect=subprocess.TimeoutExpired(["adb"], 20),
        ):
            self.module.trigger_one_sysrq_panic("SERIAL", "a" * 32)

    def test_parse_64_bit_probe_table(self):
        header = bytearray(16)
        header[:6] = b"+g0q\0\0"
        entry = bytearray(0x28)
        struct.pack_into("<I", entry, 0, 1)
        entry[4:8] = b"DDR0"
        struct.pack_into("<QQ", entry, 24, 0x80000000, 0x80000FFF)
        terminator = bytes(0x28)
        parsed = self.module.parse_probe_table(bytes(header + entry + terminator))
        self.assertEqual(parsed["mode"], 64)
        self.assertEqual(parsed["device_name"], "g0q")
        self.assertEqual(parsed["areas"][0]["length"], 0x1000)

    def test_probe_parser_rejects_empty_and_reversed_ranges(self):
        with self.assertRaises(self.module.GateError):
            self.module.parse_probe_table(b"short")
        header = bytearray(16)
        header[:5] = b"+g0q\0"
        entry = bytearray(0x28)
        struct.pack_into("<QQ", entry, 24, 0x9000, 0x8000)
        with self.assertRaisesRegex(self.module.GateError, "malformed"):
            self.module.parse_probe_table(bytes(header + entry))

    def test_timeline_uses_single_events_schema(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "timeline.json"
            timeline = self.module.Timeline.create(path)
            timeline.append("live_session_start")
            value = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(set(value), {"events"})
            self.assertEqual(value["events"][0]["name"], "live_session_start")
            with self.assertRaisesRegex(self.module.GateError, "duplicate"):
                timeline.append("live_session_start")
            with self.assertRaisesRegex(self.module.GateError, "unknown"):
                timeline.append("ad_hoc")

    def test_live_fails_before_android_or_usb_contact_when_policy_inactive(self):
        args = self.module.build_parser().parse_args(
            [
                "--live",
                "--panic-ack",
                self.module.PANIC_ACK_TOKEN,
                "--probe-ack",
                self.module.PROBE_ACK_TOKEN,
            ]
        )
        with mock.patch.object(self.module, "agents_policy_active", return_value=False), mock.patch.object(
            self.module, "android_preflight", side_effect=AssertionError("device contact")
        ):
            with self.assertRaisesRegex(self.module.GateError, "inactive"):
                self.module.live_run(Path("."), args)

    def test_offline_and_plan_do_not_import_pyusb_or_contact_device(self):
        with mock.patch.object(self.module, "verify_policy_draft", return_value={"active": False}), mock.patch.object(
            self.module, "agents_policy_active", return_value=False
        ), mock.patch.object(
            self.module, "android_preflight", side_effect=AssertionError("device")
        ):
            result = self.module.offline_check(Path("."))
            self.assertFalse(result["device_contact"])
            self.assertFalse(result["memory_transfer"])

    def test_wait_for_endpoint_is_bounded_and_flushes_samples(self):
        samples = iter(
            [
                [{"vid": "04e8", "pid": "6860"}],
                [{"vid": "04e8", "pid": "685d"}],
            ]
        )
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(
            self.module.time, "sleep", return_value=None
        ):
            classification, _ = self.module.wait_for_rdx_endpoint(
                Path(temp), 5, sampler=lambda: next(samples)
            )
            self.assertEqual(classification, "SAMSUNG_SBOOT_RDX_04E8_685D")
            self.assertTrue((Path(temp) / "usb_samples.json").is_file())


if __name__ == "__main__":
    unittest.main()
