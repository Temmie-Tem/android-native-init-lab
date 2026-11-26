from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workspace/public/src/scripts/revalidation"))
import s20plus_g986n_stock_direct_readback_d0 as owner


class FirstReturnTest(unittest.TestCase):
    def test_only_a_unique_complete_prebranch_is_positive(self):
        for output, state in [
            (b"y2q_early_v2=2097136,1,0,0\n", "prebranch_only"),
            (b"y2q_early_v2=2097136,0,0,0\n", "no_record"),
            (b"y2q_early_v2=0,0,0,0\n", "empty_snapshot"),
            (b"y2q_early_v2=512,2,0,0\n", "ambiguous"),
            (b"y2q_early_v2=512,0,1,0\n", "ambiguous"),
            (b"y2q_early_v2=512,1,1,1\n", "ambiguous"),
            (b"y2q_log_unreadable\n", "unreadable"),
            (b"y2q_log_missing\n", "missing"),
        ]:
            with self.subTest(state=state):
                self.assertEqual(owner.classify(0, output, b"")["state"], state)
        for result in [(0, b"abc", b""), (0, b"y2q_early_v2=127,1,0,0\n", b""),
                       (0, b"x" * 97, b""), (1, b"", b"x")]:
            with self.assertRaises(ValueError):
                owner.classify(*result)

    def test_closed_run_brackets_and_nonce(self):
        restored, script = owner.closure()
        self.assertEqual(script.count(restored["boot_id_sha256"]), 1)
        self.assertEqual(script.count("same_boot || exit 4"), 2)
        self.assertIn("node=/proc/last_kmsg", script)
        self.assertIn("-N 2097137", script)
        self.assertNotIn("reboot", script)

    def test_changed_boot_and_port_precede_root(self):
        h = owner.health
        expected = {k: owner.io.sha(v.encode()) for k, v in [
            ("serial_sha256", "example"), ("topology_sha256", "usb:fixture"), ("boot_id_sha256", "original")]}
        for port in ("usb:changed", "usb:fixture"):
            values = [(0, b"List of devices attached\n", b""), (0, port.encode()+b"\n", b""), (0, b"", b"")]
            with patch.object(h.base, "bounded_command", side_effect=values), patch.object(h, "select_exact_target",
                 return_value={"serial": "example", "metadata": [port]}), patch.object(h, "_parse_devpath", return_value=port), \
                 patch.object(h, "parse_public_snapshot", return_value={"boot_id":"changed"}), \
                 patch.object(h, "_validate_snapshot_binding"), patch.object(h, "parse_root_result") as root:
                with self.assertRaisesRegex(ValueError, "port changed|boot changed"):
                    owner.bracket("fixture", expected)
                root.assert_not_called()

    def test_boot_change_after_root_is_rejected(self):
        h = owner.health
        expected = {k: owner.io.sha(v.encode()) for k, v in [
            ("serial_sha256", "example"), ("topology_sha256", "usb:fixture"), ("boot_id_sha256", "old")]}
        expected["root_health"] = h.EXPECTED_ROOT_OUTPUT
        with patch.object(h.base, "bounded_command", return_value=(0, b"", b"")), \
                patch.object(h, "_decode_inventory", return_value=""), patch.object(h, "select_exact_target",
                return_value={"serial": "example", "metadata": ["usb:fixture"]}), \
                patch.object(h, "_parse_devpath", return_value="usb:fixture"), \
                patch.object(h, "parse_public_snapshot", side_effect=[{"boot_id":"old"}, {"boot_id":"new"}]), \
                patch.object(h, "_validate_snapshot_binding"), patch.object(h, "parse_root_result",
                return_value=h.EXPECTED_ROOT_OUTPUT):
            with self.assertRaisesRegex(ValueError, "boot changed during root health"):
                owner.bracket("fixture", expected)

    def test_no_second_dispatch_and_no_dispatch_after_initial_binding_failure(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(owner, "admit"), \
                patch.object(owner, "PARENT", Path(temp)), patch.object(owner.health.base, "tool_receipt"), \
                patch.object(owner.health, "_validate_adb_receipt", return_value={"path":"fixture"}), \
                patch.object(owner, "bracket", side_effect=ValueError("boot changed")), \
                patch.object(owner.io, "root_capture") as capture:
            with self.assertRaisesRegex(ValueError, "boot changed"):
                owner.observe({}, {}, "fixture")
            self.assertTrue((Path(temp) / "observation/failure.json").is_file())
            with self.assertRaises(FileExistsError):
                owner.observe({}, {}, "fixture")
            capture.assert_not_called()


if __name__ == "__main__":
    unittest.main()
