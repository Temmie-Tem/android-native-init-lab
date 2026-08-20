import importlib.util
import json
import os
import pty
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s20plus_n3u0_usb_observer.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "s20plus_n3u0_usb_observer_tested", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S20PlusN3U0UsbObserverTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def roots(self):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        usb_root = root / "sys/bus/usb/devices"
        tty_root = root / "sys/class/tty"
        devices = root / "sys/devices/platform/usb1"
        drivers = root / "sys/drivers/cdc_acm"
        for path in (usb_root, tty_root, devices, drivers):
            path.mkdir(parents=True)
        return temporary, usb_root, tty_root, devices, drivers

    def add_candidate(
        self,
        usb_root,
        tty_root,
        devices,
        drivers,
        *,
        usb_node="1-2",
        tty_name="ttyACM7",
        manufacturer="Samsung",
        product_string="S20Plus-N3U0",
        serial=None,
        extra_tty=False,
    ):
        usb = devices / usb_node
        interface = usb / f"{usb_node}:1.0"
        tty_device = interface / "tty" / tty_name
        tty_device.mkdir(parents=True)
        (usb_root / usb_node).symlink_to(usb)
        (usb / "idVendor").write_text("04e8\n", encoding="ascii")
        (usb / "idProduct").write_text("6861\n", encoding="ascii")
        (usb / "manufacturer").write_text(manufacturer + "\n", encoding="ascii")
        (usb / "product").write_text(product_string + "\n", encoding="ascii")
        if serial is not None:
            (usb / "serial").write_text(serial + "\n", encoding="ascii")
        (interface / "bInterfaceNumber").write_text("00\n", encoding="ascii")
        (interface / "driver").symlink_to(drivers)
        master, slave = pty.openpty()
        info = os.fstat(slave)
        tty_class = tty_root / tty_name
        tty_class.mkdir()
        (tty_class / "device").symlink_to(tty_device)
        (tty_class / "dev").write_text(
            f"{os.major(info.st_rdev)}:{os.minor(info.st_rdev)}\n",
            encoding="ascii",
        )
        handles = [(master, slave)]
        if extra_tty:
            second_name = "ttyACM19"
            second_device = interface / "tty" / second_name
            second_device.mkdir()
            second_master, second_slave = pty.openpty()
            second_info = os.fstat(second_slave)
            second_class = tty_root / second_name
            second_class.mkdir()
            (second_class / "device").symlink_to(second_device)
            (second_class / "dev").write_text(
                f"{os.major(second_info.st_rdev)}:{os.minor(second_info.st_rdev)}\n",
                encoding="ascii",
            )
            handles.append((second_master, second_slave))
        return handles

    def cleanup_handles(self, handles):
        for master, slave in handles:
            os.close(master)
            os.close(slave)

    def baseline(self, usb_node="1-2"):
        return {
            "schema": self.module.BASELINE_SCHEMA,
            "observer_schema": self.module.SCHEMA,
            "expected_topology_sha256": self.module._hash_text(usb_node),
            "candidate_absent": True,
            "exact_identity_sha256": [],
            "pending_identity_sha256": [],
            "conflicting_identity_sha256": [],
        }

    def test_plan_is_dormant_and_has_no_device_action_surface(self):
        plan = self.module.render_plan()
        self.assertFalse(plan["active"])
        self.assertFalse(plan["live_authority"])
        self.assertEqual(plan["status"], "REVIEW_PENDING_NOT_ACTIVE")
        self.assertEqual(
            plan["target"],
            {
                "model": "SM-G986N",
                "device": "y2q",
                "product": "y2qksx",
                "build": "G986NKSS8IYC2",
            },
        )
        self.assertEqual(plan["usb"]["product_string"], "S20Plus-N3U0")
        self.assertEqual(bytes.fromhex(plan["banner_hex"]), self.module.BANNER)
        self.assertEqual(plan["device_commands"], [])
        self.assertEqual(plan["partition_transfers"], [])

    def test_dormant_gate_stops_before_any_inventory_read(self):
        with mock.patch.object(
            self.module,
            "scan_inventory",
            side_effect=AssertionError("live sysfs must not be read"),
        ):
            with self.assertRaisesRegex(self.module.ObserverError, "dormant"):
                self.module.observe_attended(self.baseline(), "1-2")

    def test_empty_baseline_is_exact_and_rejects_typed_or_topology_forgery(self):
        temporary, usb_root, tty_root, _devices, _drivers = self.roots()
        self.addCleanup(temporary.cleanup)
        baseline = self.module.capture_baseline(
            "1-2", usb_root=usb_root, tty_root=tty_root
        )
        self.assertEqual(baseline, self.baseline())
        forged = {**baseline, "candidate_absent": 1}
        with self.assertRaises(self.module.ObserverError):
            self.module.validate_baseline(forged, "1-2")
        with self.assertRaises(self.module.ObserverError):
            self.module.validate_baseline(baseline, "1-3")

    def test_candidate_present_at_baseline_is_rejected(self):
        temporary, usb_root, tty_root, devices, drivers = self.roots()
        self.addCleanup(temporary.cleanup)
        handles = self.add_candidate(usb_root, tty_root, devices, drivers)
        self.addCleanup(self.cleanup_handles, handles)
        with self.assertRaisesRegex(self.module.ObserverError, "not absent"):
            self.module.capture_baseline(
                "1-2", usb_root=usb_root, tty_root=tty_root
            )

    def test_dynamic_tty_number_is_selected_without_ttyacm0_assumption(self):
        temporary, usb_root, tty_root, devices, drivers = self.roots()
        self.addCleanup(temporary.cleanup)
        handles = self.add_candidate(
            usb_root, tty_root, devices, drivers, tty_name="ttyACM37"
        )
        self.addCleanup(self.cleanup_handles, handles)
        candidate = self.module.select_arrival(
            self.baseline(),
            "1-2",
            usb_root=usb_root,
            tty_root=tty_root,
        )
        self.assertEqual(candidate.tty_name, "ttyACM37")
        self.assertEqual(candidate.usb_node, "1-2")

    def test_stock_android_same_vid_pid_with_other_product_is_ignored(self):
        temporary, usb_root, tty_root, devices, drivers = self.roots()
        self.addCleanup(temporary.cleanup)
        handles = self.add_candidate(
            usb_root,
            tty_root,
            devices,
            drivers,
            product_string="SAMSUNG_Android",
        )
        self.addCleanup(self.cleanup_handles, handles)
        inventory = self.module.scan_inventory(
            usb_root=usb_root, tty_root=tty_root
        )
        self.assertEqual(inventory.exact, ())
        self.assertEqual(inventory.pending_identity_sha256, ())
        self.assertEqual(inventory.conflicting_identity_sha256, ())

    def test_named_candidate_rejects_serial_wrong_manufacturer_and_missing_tty(self):
        for mutation in ("serial", "manufacturer", "missing-tty"):
            with self.subTest(mutation=mutation):
                temporary, usb_root, tty_root, devices, drivers = self.roots()
                try:
                    handles = self.add_candidate(
                        usb_root,
                        tty_root,
                        devices,
                        drivers,
                        serial="unexpected" if mutation == "serial" else None,
                        manufacturer="Other" if mutation == "manufacturer" else "Samsung",
                    )
                    if mutation == "missing-tty":
                        for path in list(tty_root.iterdir()):
                            path.rename(path.with_name("ignored" + path.name))
                    inventory = self.module.scan_inventory(
                        usb_root=usb_root, tty_root=tty_root
                    )
                    self.assertEqual(inventory.exact, ())
                    if mutation == "missing-tty":
                        self.assertEqual(len(inventory.pending_identity_sha256), 1)
                        self.assertEqual(inventory.conflicting_identity_sha256, ())
                    else:
                        self.assertEqual(inventory.pending_identity_sha256, ())
                        self.assertEqual(len(inventory.conflicting_identity_sha256), 1)
                finally:
                    self.cleanup_handles(handles)
                    temporary.cleanup()

    def test_two_ttys_or_two_candidates_are_ambiguous(self):
        temporary, usb_root, tty_root, devices, drivers = self.roots()
        self.addCleanup(temporary.cleanup)
        handles = self.add_candidate(
            usb_root, tty_root, devices, drivers, extra_tty=True
        )
        self.addCleanup(self.cleanup_handles, handles)
        inventory = self.module.scan_inventory(
            usb_root=usb_root, tty_root=tty_root
        )
        self.assertEqual(inventory.exact, ())
        self.assertEqual(inventory.pending_identity_sha256, ())
        self.assertEqual(len(inventory.conflicting_identity_sha256), 1)

        temporary2, usb_root2, tty_root2, devices2, drivers2 = self.roots()
        self.addCleanup(temporary2.cleanup)
        handles2 = self.add_candidate(
            usb_root2, tty_root2, devices2, drivers2, usb_node="1-2", tty_name="ttyACM4"
        )
        handles2 += self.add_candidate(
            usb_root2, tty_root2, devices2, drivers2, usb_node="1-3", tty_name="ttyACM9"
        )
        self.addCleanup(self.cleanup_handles, handles2)
        with self.assertRaisesRegex(self.module.ObserverError, "ambiguous"):
            self.module.select_arrival(
                self.baseline(), "1-2", usb_root=usb_root2, tty_root=tty_root2
            )

    def test_foreign_topology_is_rejected_even_with_exact_product_and_banner(self):
        temporary, usb_root, tty_root, devices, drivers = self.roots()
        self.addCleanup(temporary.cleanup)
        handles = self.add_candidate(
            usb_root, tty_root, devices, drivers, usb_node="1-3"
        )
        self.addCleanup(self.cleanup_handles, handles)
        with self.assertRaisesRegex(self.module.ObserverError, "foreign topology"):
            self.module.select_arrival(
                self.baseline(), "1-2", usb_root=usb_root, tty_root=tty_root
            )

    def test_fragmented_banner_is_reassembled_and_repeated_banner_does_not_matter(self):
        master, slave = pty.openpty()
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        os.write(master, self.module.BANNER[:5])

        def finish():
            time.sleep(0.03)
            os.write(master, self.module.BANNER[5:] + self.module.BANNER)

        writer = threading.Thread(target=finish)
        writer.start()
        payload = self.module.read_exact_banner(slave)
        writer.join(timeout=1)
        self.assertFalse(writer.is_alive())
        self.assertEqual(payload, self.module.BANNER)

    def test_wrong_or_partial_banner_never_accepts(self):
        master, slave = pty.openpty()
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        os.write(master, b"S20PLUS_N3U0_ACM_V0\n")
        with self.assertRaisesRegex(self.module.ObserverError, "bytes differ"):
            self.module.read_exact_banner(slave)

        master2, slave2 = pty.openpty()
        self.addCleanup(os.close, master2)
        self.addCleanup(os.close, slave2)
        os.write(master2, self.module.BANNER[:4])
        clock = iter((0.0, 12.0))
        with self.assertRaisesRegex(self.module.ObserverError, "timed out"):
            self.module.read_exact_banner(slave2, monotonic=lambda: next(clock))

    def test_complete_fake_observation_revalidates_endpoint_and_redacts_tty(self):
        temporary, usb_root, tty_root, devices, drivers = self.roots()
        self.addCleanup(temporary.cleanup)
        handles = self.add_candidate(
            usb_root, tty_root, devices, drivers, tty_name="ttyACM23"
        )
        self.addCleanup(self.cleanup_handles, handles)
        master, slave = handles[0]
        candidate = self.module.select_arrival(
            self.baseline(), "1-2", usb_root=usb_root, tty_root=tty_root
        )
        os.write(master, self.module.BANNER)
        receipt = self.module.observe_selected(
            self.baseline(),
            "1-2",
            candidate,
            slave,
            usb_root=usb_root,
            tty_root=tty_root,
        )
        self.assertTrue(receipt["accepted"])
        self.assertFalse(receipt["tty_number_stable"])
        self.assertNotIn("ttyACM23", json.dumps(receipt, sort_keys=True))
        self.assertEqual(
            receipt["banner_sha256"],
            self.module.hashlib.sha256(self.module.BANNER).hexdigest(),
        )

    def test_endpoint_change_after_banner_is_rejected(self):
        temporary, usb_root, tty_root, devices, drivers = self.roots()
        self.addCleanup(temporary.cleanup)
        handles = self.add_candidate(usb_root, tty_root, devices, drivers)
        self.addCleanup(self.cleanup_handles, handles)
        master, slave = handles[0]
        candidate = self.module.select_arrival(
            self.baseline(), "1-2", usb_root=usb_root, tty_root=tty_root
        )
        os.write(master, self.module.BANNER)
        with mock.patch.object(
            self.module,
            "select_arrival",
            return_value=self.module.Candidate(
                **{
                    **candidate.__dict__,
                    "identity_sha256": "0" * 64,
                }
            ),
        ):
            with self.assertRaisesRegex(self.module.ObserverError, "changed after banner"):
                self.module.observe_selected(
                    self.baseline(),
                    "1-2",
                    candidate,
                    slave,
                    usb_root=usb_root,
                    tty_root=tty_root,
                )

    def test_source_has_no_connected_command_or_writable_device_surface(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in (
            "subprocess",
            "adb ",
            "su -c",
            "odin",
            "mode=peripheral",
            "ttyACM0",
            "os.O_WRONLY",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn("OBSERVER_ACTIVE = False", source)


if __name__ == "__main__":
    unittest.main()
