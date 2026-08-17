import hashlib
import importlib.util
import json
import stat
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p257_stock_pivot_d0.py"
)
REVALIDATION = SCRIPT.parent
PROFILE = (
    ROOT / "workspace/public/src/device-action/profiles/s22plus_fyg8.json"
)


def load_module():
    sys.path.insert(0, str(REVALIDATION))
    try:
        spec = importlib.util.spec_from_file_location(
            "s22plus_fyg8_p257_stock_pivot_d0", SCRIPT
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(REVALIDATION))


class FakeClient:
    def __init__(self, profile):
        target = profile["target"]
        health = profile["start_health"]
        self.serials = ["fixture-serial", "fixture-serial"]
        self.topologies = ["usb:3-1", "usb:3-1"]
        self.properties_values = [
            {
                "model": target["model"],
                "device": target["device"],
                "bootloader": target["firmware_incremental"],
                "incremental": target["firmware_incremental"],
                "boot_completed": "1",
                "bootanim": "stopped",
                "verified_boot_state": health["verified_boot_state"],
                "boot_id": "00000000-0000-0000-0000-000000000001",
                "kernel_release": "5.10-fixture",
            }
        ] * 2
        self.root_values = {
            "root": "uid=0(root) gid=0(root)",
            "boot": health["boot_sha256"],
            **health["supporting_partition_sha256"],
        }

    def receipt(self):
        return {
            "path": "/fixture/adb",
            "size": 1,
            "sha256": "1" * 64,
            "version_output_sha256": "2" * 64,
        }

    def one_serial(self):
        return self.serials.pop(0)

    def topology(self, _serial):
        return self.topologies.pop(0)

    def properties(self, _serial):
        return self.properties_values.pop(0)

    def root_health(self, _serial):
        return self.root_values


class S22PlusFyg8P257StockPivotD0Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.profile = json.loads(PROFILE.read_text(encoding="utf-8"))
        cls.profile_receipt = {
            "path": str(PROFILE),
            "size": PROFILE.stat().st_size,
            "sha256": hashlib.sha256(PROFILE.read_bytes()).hexdigest(),
        }

    def test_exact_polarity_vectors(self):
        enabled = self.module.evaluate_reads((b"0x0\n", b"0x0\n"), (b"0\n", b"0\n"))
        self.assertEqual(enabled["source_decision"], "DISPLAY_ENABLED_VERIFIED")
        self.assertEqual(enabled["verdict"], self.module.ENABLED_VERDICT)
        self.assertTrue(enabled["promotion_eligible"])

        disabled = self.module.evaluate_reads(
            (b"0x1\n", b"0x1\n"), (b"10\n", b"10\n")
        )
        self.assertEqual(
            disabled["source_decision"], "NO_DISPLAY_SUBSET_VERIFIED"
        )
        self.assertEqual(disabled["target_sanity"], "TARGET_CONTRADICTION")
        self.assertEqual(disabled["verdict"], self.module.CONTRADICTION_VERDICT)
        self.assertFalse(disabled["promotion_eligible"])

    def test_crossed_polarity_vectors_are_inconsistent(self):
        for display, subset in ((b"0x0\n", b"10\n"), (b"0x1\n", b"0\n")):
            with self.subTest(display=display, subset=subset):
                result = self.module.evaluate_reads(
                    (display, display), (subset, subset)
                )
                self.assertEqual(result["source_decision"], "INCONSISTENT")
                self.assertFalse(result["promotion_eligible"])

    def test_parsers_reject_non_source_shapes(self):
        bad_display = (
            b"0X0\n",
            b"0x000000000\n",
            b"0x0",
            b"0x0 \n",
            b"0x0\n0x0\n",
            b"\n",
        )
        bad_subset = (
            b"0x10\n",
            b"000000000\n",
            b"10",
            b"10 \n",
            b"10\n10\n",
            b"\n",
        )
        for payload in bad_display:
            with self.subTest(display=payload):
                with self.assertRaises(self.module.PivotError):
                    self.module.parse_display(payload)
        for payload in bad_subset:
            with self.subTest(subset=payload):
                with self.assertRaises(self.module.PivotError):
                    self.module.parse_subset_parts(payload)

    def test_changed_or_malformed_reads_are_inconclusive(self):
        changed = self.module.evaluate_reads(
            (b"0x0\n", b"0x1\n"), (b"0\n", b"0\n")
        )
        malformed = self.module.evaluate_reads(
            (b"0x0\n", b"0x0\n"), (b"0x0\n", b"0x0\n")
        )
        self.assertEqual(changed["reason"], "display-read-changed")
        self.assertEqual(malformed["reason"], "subset-parts-malformed")
        self.assertEqual(changed["verdict"], self.module.INCONCLUSIVE_VERDICT)
        self.assertEqual(malformed["verdict"], self.module.INCONCLUSIVE_VERDICT)

    def test_remote_reader_is_allowlisted_and_bounded(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary, self.assertRaises(
            module.PivotError
        ):
            module.read_remote_exact(
                Path("/fixture/adb"),
                "serial",
                "/proc/version",
                Path(temporary),
                "invalid",
            )

    def _raw_reader(self, reads):
        module = self.module

        def read(_serial, _source, capture_dir, name):
            return module.raw_capture.publish_captured_bytes(
                capture_dir,
                name,
                stdout=next(reads),
                stdout_name=f"{name}.bin",
                stderr_name=f"{name}.bin.stderr",
            )

        return read

    def _usb_root(self, root):
        device = root / "1-1"
        device.mkdir(parents=True)
        (device / "idVendor").write_text("18d1\n", encoding="ascii")
        (device / "idProduct").write_text("4ee7\n", encoding="ascii")
        return root

    def test_connected_enabled_result_is_private_sealed_and_non_authorizing(self):
        module = self.module
        reads = iter((b"0x0\n", b"0x0\n", b"0\n", b"0\n"))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "run"
            run_dir.mkdir()
            usb_root = self._usb_root(root / "usb")
            result = module.collect_connected(
                self.profile,
                self.profile_receipt,
                run_dir,
                FakeClient(self.profile),
                usb_root,
                self._raw_reader(reads),
            )
            self.assertEqual(result["verdict"], module.ENABLED_VERDICT)
            self.assertTrue(result["measurement"]["promotion_eligible"])
            for name in ("display", "subset_parts"):
                for receipt in result["measurement"]["raw_receipts"][name]:
                    path = Path(receipt["path"])
                    self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o400)
            result_path = run_dir / "result.json"
            self.assertEqual(stat.S_IMODE(result_path.stat().st_mode), 0o400)
            self.assertFalse(result["device_writes"])
            self.assertFalse(result["root_used_for_pivot_reads"])
            self.assertFalse(result["reboot_requested"])
            self.assertFalse(result["odin_invoked"])
            self.assertFalse(result["partition_transfer"])
            self.assertFalse(result["f1_authorized"])

    def test_connected_no_display_result_is_not_promotion_eligible(self):
        module = self.module
        reads = iter((b"0x1\n", b"0x1\n", b"10\n", b"10\n"))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "run"
            run_dir.mkdir()
            result = module.collect_connected(
                self.profile,
                self.profile_receipt,
                run_dir,
                FakeClient(self.profile),
                self._usb_root(root / "usb"),
                self._raw_reader(reads),
            )
        self.assertEqual(result["verdict"], module.CONTRADICTION_VERDICT)
        self.assertFalse(result["measurement"]["promotion_eligible"])

    def test_target_change_stops_before_result(self):
        module = self.module
        client = FakeClient(self.profile)
        client.serials[-1] = "changed"
        reads = iter((b"0x0\n", b"0x0\n", b"0\n", b"0\n"))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "run"
            run_dir.mkdir()
            with self.assertRaises(module.PivotError):
                module.collect_connected(
                    self.profile,
                    self.profile_receipt,
                    run_dir,
                    client,
                    self._usb_root(root / "usb"),
                    self._raw_reader(reads),
                )
            self.assertFalse((run_dir / "result.json").exists())

    def test_source_has_no_device_mutation_or_f1_surface(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in (
            "adb reboot",
            "odin4",
            "flash_exact(",
            "approval_binding(",
            "ready-for-f1-approval",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
