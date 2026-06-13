from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from _loader import load_script


probe = load_script("workspace/public/src/scripts/revalidation/native_wifi_supplicant_dependency_probe.py")


class FileAndScriptHelpers(unittest.TestCase):
    def test_sha256_file_hashes_large_file_in_chunks(self) -> None:
        data = (b"A90-supplicant-probe" * 100_000) + b"tail"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "payload.bin"
            path.write_bytes(data)

            self.assertEqual(probe.sha256_file(path), hashlib.sha256(data).hexdigest())

    def test_remote_probe_script_contains_no_connect_connect_and_cleanup_contracts(self) -> None:
        script = probe.remote_probe_script()

        self.assertIn('MODE="${1:-no-connect}"', script)
        self.assertIn("write_no_connect_config", script)
        self.assertIn("DRIVER COUNTRY KR", script)
        self.assertIn("ENABLE_NETWORK 0", script)
        self.assertIn("REASSOCIATE", script)
        self.assertIn("cleanup_pid", script)
        self.assertIn("candidate.$label.alive_after_cleanup", script)
        self.assertIn("supplicant_probe.done=1", script)
        self.assertIn("run_candidate vendor_hw /vendor/bin/hw/wpa_supplicant native", script)
        self.assertIn("run_candidate vendor /vendor/bin/wpa_supplicant halctx", script)


class CandidateParsing(unittest.TestCase):
    def test_parse_candidate_results_sorts_labels_and_coerces_booleans_with_defaults(self) -> None:
        fields = {
            "candidate.vendor_native.base": "vendor",
            "candidate.vendor_native.context_mode": "native",
            "candidate.vendor_native.path": "/vendor/bin/wpa_supplicant",
            "candidate.vendor_native.present": "1",
            "candidate.vendor_native.executable": "1",
            "candidate.vendor_native.socket_present": "1",
            "candidate.vendor_native.ping_ok": "1",
            "candidate.vendor_native.carrier_up": "0",
            "candidate.vendor_native.result": "no-connect-ctrl-ready",
            "candidate.vendor_native.log_bytes": "123",
            "candidate.vendor_native.log_nl80211": "2",
            "candidate.vendor_native.log_fail": "0",
            "candidate.vendor_native.log_permission": "1",
            "candidate.vendor_native.log_avc": "0",
            "candidate.vendor_native.alive_after_cleanup": "0",
            "candidate.standalone_halctx.base": "standalone",
            "candidate.standalone_halctx.context_mode": "halctx",
            "candidate.standalone_halctx.present": "0",
            "candidate.standalone_halctx.ping_ok": "0",
            "candidate.standalone_halctx.alive_after_cleanup": "1",
            "candidate": "ignored",
            "candidate.too_short": "ignored",
        }

        parsed = probe.parse_candidate_results(fields)

        self.assertEqual([item["label"] for item in parsed], ["standalone_halctx", "vendor_native"])
        standalone = parsed[0]
        self.assertEqual(standalone["base"], "standalone")
        self.assertEqual(standalone["context_mode"], "halctx")
        self.assertFalse(standalone["present"])
        self.assertFalse(standalone["executable"])
        self.assertFalse(standalone["ping_ok"])
        self.assertTrue(standalone["alive_after_cleanup"])
        self.assertEqual(standalone["result"], "missing")
        self.assertEqual(standalone["log_bytes"], "0")

        vendor = parsed[1]
        self.assertTrue(vendor["present"])
        self.assertTrue(vendor["executable"])
        self.assertTrue(vendor["socket_present"])
        self.assertTrue(vendor["ping_ok"])
        self.assertFalse(vendor["carrier_up"])
        self.assertEqual(vendor["path"], "/vendor/bin/wpa_supplicant")
        self.assertEqual(vendor["log_nl80211"], "2")
        self.assertEqual(vendor["log_permission"], "1")


class DecisionMatrix(unittest.TestCase):
    def test_pick_decision_preconditions_override_candidates(self) -> None:
        candidate = [{"base": "vendor_hw", "ping_ok": True, "carrier_up": True}]

        self.assertEqual(
            probe.pick_decision("connect", {"supplicant_probe.wlan0_present": "0"}, candidate),
            "supplicant-dependency-precondition-wlan0-missing",
        )
        self.assertEqual(
            probe.pick_decision("connect", {"supplicant_probe.helper_present": "0"}, candidate),
            "supplicant-dependency-precondition-helper-missing",
        )

    def test_pick_decision_connect_prioritizes_vendor_hw_vendor_then_standalone(self) -> None:
        self.assertEqual(
            probe.pick_decision("connect", {}, [
                {"base": "standalone", "ping_ok": True, "carrier_up": True},
                {"base": "vendor_hw", "ping_ok": True, "carrier_up": True},
            ]),
            "supplicant-dependency-vendor-hw-connects",
        )
        self.assertEqual(
            probe.pick_decision("connect", {}, [
                {"base": "vendor", "ping_ok": True, "carrier_up": True},
                {"base": "standalone", "ping_ok": True, "carrier_up": True},
            ]),
            "supplicant-dependency-vendor-connects",
        )
        self.assertEqual(
            probe.pick_decision("connect", {}, [{"base": "standalone", "ping_ok": True, "carrier_up": True}]),
            "supplicant-dependency-standalone-connects",
        )
        self.assertEqual(
            probe.pick_decision("connect", {}, [{"base": "vendor_hw", "ping_ok": True, "carrier_up": False}]),
            "supplicant-dependency-ctrl-ready-but-no-carrier",
        )
        self.assertEqual(
            probe.pick_decision("connect", {}, [{"base": "vendor_hw", "ping_ok": False, "carrier_up": False}]),
            "supplicant-dependency-no-connectable-candidate",
        )

    def test_pick_decision_no_connect_prefers_vendor_ctrl_ready_then_standalone(self) -> None:
        self.assertEqual(
            probe.pick_decision("no-connect", {}, [
                {"base": "standalone", "ping_ok": True},
                {"base": "vendor", "ping_ok": True},
            ]),
            "supplicant-dependency-vendor-direct-ctrl-ready",
        )
        self.assertEqual(
            probe.pick_decision("no-connect", {}, [{"base": "standalone", "ping_ok": True}]),
            "supplicant-dependency-standalone-only-ctrl-ready",
        )
        self.assertEqual(
            probe.pick_decision("no-connect", {}, [{"base": "vendor_hw", "ping_ok": False}]),
            "supplicant-dependency-no-ctrl-ready-candidate",
        )

    def test_transfer_ok_requires_ok_without_sha_mismatch(self) -> None:
        self.assertTrue(probe.transfer_ok({"ok": True}))
        self.assertFalse(probe.transfer_ok({"ok": True, "sha256_mismatch": True}))
        self.assertFalse(probe.transfer_ok({"ok": False}))
        self.assertFalse(probe.transfer_ok({}))


if __name__ == "__main__":
    unittest.main()
