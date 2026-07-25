import hashlib
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
    "device_action_cdc_acm_observer_v1.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "device_action_cdc_acm_observer_v1_tested", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class HealthyGuard:
    def healthy(self, *, recheck=False):
        return True

    def matches_node(self, _node):
        return True


class MismatchedGuard(HealthyGuard):
    def matches_node(self, _node):
        return False


class CdcAcmObserverV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def spec(self):
        return {
            "kind": "exact_cdc_acm_banner_v1",
            "usb_vendor_id": "04e8",
            "usb_product_id": "6861",
            "usb_serial": "S22E3" + "1" * 32,
            "usb_driver": "cdc_acm",
            "usb_interface_number": "00",
            "banner_hex": (
                b"S22PLUS-FYG8-E3:" + b"1" * 32 + b"\n"
            ).hex(),
        }

    def departure(self, absent=True):
        return {
            "download_endpoint_absent": absent,
            "absence_timed_out": not absent,
            "sequence": 1,
        }

    def fixture(self):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        class_tty = root / "sys/class/tty"
        class_tty.mkdir(parents=True)
        drivers = root / "sys/drivers/cdc_acm"
        drivers.mkdir(parents=True)
        usb = root / "sys/devices/platform/usb1/1-1"
        interface = usb / "1-1:1.0"
        tty_device = interface / "tty/ttyACM0"
        tty_device.mkdir(parents=True)
        (usb / "idVendor").write_text("04e8\n", encoding="ascii")
        (usb / "idProduct").write_text("6861\n", encoding="ascii")
        (usb / "serial").write_text(
            "S22E3" + "1" * 32 + "\n", encoding="ascii"
        )
        (interface / "bInterfaceNumber").write_text("00\n", encoding="ascii")
        (interface / "driver").symlink_to(drivers)
        master, slave = pty.openpty()
        slave_path = Path(os.ttyname(slave))
        info = slave_path.stat()
        tty_class = class_tty / "ttyACM0"
        tty_class.mkdir()
        (tty_class / "device").symlink_to(tty_device)
        (tty_class / "dev").write_text(
            f"{os.major(info.st_rdev)}:{os.minor(info.st_rdev)}\n",
            encoding="ascii",
        )
        dev_root = root / "dev"
        dev_root.mkdir()
        (dev_root / "ttyACM0").symlink_to(slave_path)
        run_dir = root / "run"
        run_dir.mkdir()
        return temporary, master, slave, class_tty, dev_root, run_dir

    def session(self, class_tty, dev_root, run_dir):
        baseline = {
            "schema": self.module.BASELINE_SCHEMA,
            "spec_sha256": self.module.digest(self.spec()),
            "topology_sha256": hashlib.sha256(b"1-1").hexdigest(),
            "identity_sha256": [],
            "exact_candidate_absent": True,
        }
        baseline_receipt = self.module.persist_json(
            run_dir / "candidate-observer-baseline.json", baseline
        )
        guard_receipt = self.module.persist_json(
            run_dir / "candidate-observer-guard.json",
            {
                "schema": self.module.GUARD_SCHEMA,
                "status": "not-required",
                "uid_sha256": "4" * 64,
                "active_rechecked": True,
            },
        )
        return self.module.ObserverSession(
            self.spec(),
            "usb:1-1",
            run_dir,
            {
                "approval_binding_sha256": "a" * 64,
                "bundle_sha256": "b" * 64,
                "manifest_id": "fixture-manifest",
                "candidate_ap_sha256": "c" * 64,
            },
            baseline,
            baseline_receipt,
            HealthyGuard(),
            guard_receipt,
            class_tty,
            dev_root,
        )

    def test_spec_is_exact_and_bounded(self):
        self.assertEqual(
            self.module.validate_spec(self.spec())["kind"], self.module.KIND
        )
        for mutation in (
            {**self.spec(), "extra": "x"},
            {**self.spec(), "usb_vendor_id": "4e8"},
            {**self.spec(), "banner_hex": ""},
            {**self.spec(), "usb_serial": "bad serial"},
        ):
            with self.assertRaises(self.module.ObserverError):
                self.module.validate_spec(mutation)

    def test_prequeued_banner_survives_raw_mode_without_flush(self):
        temporary, master, slave, class_tty, dev_root, run_dir = self.fixture()
        self.addCleanup(temporary.cleanup)
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        banner = bytes.fromhex(self.spec()["banner_hex"])
        os.write(master, banner)
        session = self.session(class_tty, dev_root, run_dir)
        receipt = session.observe(
            timeout_sec=2,
            download_departure=self.departure(),
        )
        self.assertEqual(receipt["classification"], "accepted")
        self.assertEqual(
            (run_dir / "candidate-observer.raw").read_bytes(), banner
        )
        reopened = self.module.validate_receipt(
            run_dir / "candidate-observer.json",
            spec=self.spec(),
            binding=session.binding,
            topology="usb:1-1",
        )
        self.assertTrue(reopened["accepted"])

    def test_split_delayed_banner_is_reassembled_exactly(self):
        temporary, master, slave, class_tty, dev_root, run_dir = self.fixture()
        self.addCleanup(temporary.cleanup)
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        banner = bytes.fromhex(self.spec()["banner_hex"])
        os.write(master, banner[:17])

        def finish():
            time.sleep(0.05)
            os.write(master, banner[17:])

        writer = threading.Thread(target=finish)
        writer.start()
        receipt = self.session(class_tty, dev_root, run_dir).observe(
            timeout_sec=2,
            download_departure=self.departure(),
        )
        writer.join(timeout=1)
        self.assertFalse(writer.is_alive())
        self.assertEqual(receipt["classification"], "accepted")

    def test_extra_byte_is_not_accepted(self):
        temporary, master, slave, class_tty, dev_root, run_dir = self.fixture()
        self.addCleanup(temporary.cleanup)
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        os.write(master, bytes.fromhex(self.spec()["banner_hex"]) + b"X")
        receipt = self.session(class_tty, dev_root, run_dir).observe(
            timeout_sec=2,
            download_departure=self.departure(),
        )
        self.assertEqual(receipt["classification"], "extra-byte")
        self.assertFalse(receipt["accepted"])

    def test_uid_mismatch_stops_before_tty_open(self):
        temporary, master, slave, class_tty, dev_root, run_dir = self.fixture()
        self.addCleanup(temporary.cleanup)
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        session = self.session(class_tty, dev_root, run_dir)
        session.guard = MismatchedGuard()
        endpoint = self.module.scan_endpoints(class_tty)[0][1]
        with mock.patch.object(
            self.module.os,
            "open",
            side_effect=AssertionError("TTY open must not occur"),
        ):
            classification, payload = session._read_endpoint(
                endpoint, self.module.time.monotonic() + 1
            )
        self.assertEqual(classification, "identity-mismatch")
        self.assertEqual(payload, b"")

    def test_unrelated_and_malformed_acm_entries_do_not_block_selection(self):
        temporary, master, slave, class_tty, dev_root, run_dir = self.fixture()
        self.addCleanup(temporary.cleanup)
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        (class_tty / "ttyACM9").mkdir()
        endpoints = self.module.scan_endpoints(class_tty)
        self.assertEqual(len(endpoints), 1)
        session = self.session(class_tty, dev_root, run_dir)
        unrelated_spec = {
            **self.spec(),
            "usb_vendor_id": "1234",
            "usb_product_id": "5678",
        }
        session.spec = unrelated_spec
        classification, endpoint = session._select()
        self.assertEqual(classification, "endpoint-timeout")
        self.assertIsNone(endpoint)

    def test_candidate_like_wrong_serial_is_identity_mismatch(self):
        temporary, master, slave, class_tty, dev_root, run_dir = self.fixture()
        self.addCleanup(temporary.cleanup)
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        session = self.session(class_tty, dev_root, run_dir)
        session.spec = {**self.spec(), "usb_serial": "S22E3" + "2" * 32}
        classification, endpoint = session._select()
        self.assertEqual(classification, "identity-mismatch")
        self.assertIsNone(endpoint)

    def test_tiocexcl_failure_is_diagnostic_and_does_not_accept(self):
        temporary, master, slave, class_tty, dev_root, run_dir = self.fixture()
        self.addCleanup(temporary.cleanup)
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        os.write(master, bytes.fromhex(self.spec()["banner_hex"]))
        with mock.patch.object(
            self.module.fcntl, "ioctl", side_effect=OSError("busy")
        ):
            receipt = self.session(class_tty, dev_root, run_dir).observe(
                timeout_sec=2,
                download_departure=self.departure(),
            )
        self.assertEqual(receipt["classification"], "exclusive-failed")
        self.assertFalse(receipt["accepted"])

    def test_download_departure_is_required_for_acceptance(self):
        temporary, master, slave, class_tty, dev_root, run_dir = self.fixture()
        self.addCleanup(temporary.cleanup)
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        os.write(master, bytes.fromhex(self.spec()["banner_hex"]))
        receipt = self.session(class_tty, dev_root, run_dir).observe(
            timeout_sec=1,
            download_departure=self.departure(False),
        )
        self.assertEqual(receipt["classification"], "endpoint-timeout")
        self.assertFalse(receipt["accepted"])

    def test_receipt_rejects_raw_tampering_and_path_rebinding(self):
        temporary, master, slave, class_tty, dev_root, run_dir = self.fixture()
        self.addCleanup(temporary.cleanup)
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        os.write(master, bytes.fromhex(self.spec()["banner_hex"]))
        session = self.session(class_tty, dev_root, run_dir)
        session.observe(
            timeout_sec=2,
            download_departure=self.departure(),
        )
        raw = run_dir / "candidate-observer.raw"
        raw.chmod(0o600)
        raw.write_bytes(b"tampered")
        with self.assertRaises(self.module.ObserverError):
            self.module.validate_receipt(
                run_dir / "candidate-observer.json",
                spec=self.spec(),
                binding=session.binding,
                topology="usb:1-1",
            )

    def test_receipt_rejects_self_consistent_false_baseline(self):
        temporary, master, slave, class_tty, dev_root, run_dir = self.fixture()
        self.addCleanup(temporary.cleanup)
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        os.write(master, bytes.fromhex(self.spec()["banner_hex"]))
        session = self.session(class_tty, dev_root, run_dir)
        session.observe(
            timeout_sec=2,
            download_departure=self.departure(),
        )
        baseline_path = run_dir / "candidate-observer-baseline.json"
        baseline_path.chmod(0o600)
        false_baseline = {
            "schema": self.module.BASELINE_SCHEMA,
            "spec_sha256": self.module.digest(self.spec()),
            "topology_sha256": "0" * 64,
            "identity_sha256": [],
            "exact_candidate_absent": True,
        }
        baseline_payload = (
            json.dumps(false_baseline, indent=2, sort_keys=True).encode()
            + b"\n"
        )
        baseline_path.write_bytes(baseline_payload)
        receipt_path = run_dir / "candidate-observer.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["baseline_sha256"] = hashlib.sha256(
            baseline_payload
        ).hexdigest()
        receipt_path.chmod(0o600)
        receipt_path.write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(
            self.module.ObserverError, "baseline semantics"
        ):
            self.module.validate_receipt(
                receipt_path,
                spec=self.spec(),
                binding=session.binding,
                topology="usb:1-1",
            )

    def test_inactive_modemmanager_is_rechecked_before_open(self):
        with (
            mock.patch.object(
                self.module, "_modemmanager_active", return_value=False
            ) as active,
            mock.patch.object(
                self.module, "modemmanager_uid", return_value="/sys/device"
            ),
        ):
            guard = self.module.ModemManagerGuard.arm("usb:1-1")
            self.assertEqual(guard.arm_receipt["status"], "not-required")
            self.assertTrue(guard.healthy())
            self.assertEqual(active.call_count, 2)

    def test_active_modemmanager_refusal_fails_closed(self):
        process = mock.Mock()
        process.stdout = mock.Mock()
        process.stdout.fileno.return_value = 9
        process.poll.return_value = 1
        process.pid = 123
        process.returncode = 1
        with (
            mock.patch.object(
                self.module, "_modemmanager_active", return_value=True
            ),
            mock.patch.object(
                self.module, "modemmanager_uid", return_value="/sys/device"
            ),
            mock.patch.object(
                self.module.subprocess, "Popen", return_value=process
            ) as popen,
            mock.patch.object(
                self.module.ModemManagerGuard, "release", return_value={}
            ),
        ):
            with self.assertRaises(self.module.ObserverError):
                self.module.ModemManagerGuard.arm("usb:1-1")
        command = popen.call_args.args[0]
        self.assertEqual(command[:3], ["setpriv", "--pdeathsig", "SIGKILL"])

    def test_active_modemmanager_success_requires_line_and_live_child(self):
        read_fd, write_fd = os.pipe()
        self.addCleanup(os.close, write_fd)
        stream = os.fdopen(read_fd, "rb", buffering=0)
        self.addCleanup(stream.close)
        uid = "/sys/device"
        os.write(
            write_fd,
            f"successfully inhibited device with uid '{uid}'\n".encode(),
        )
        process = mock.Mock()
        process.stdout = stream
        process.poll.return_value = None
        process.pid = 123
        with (
            mock.patch.object(
                self.module, "_modemmanager_active", return_value=True
            ),
            mock.patch.object(
                self.module, "modemmanager_uid", return_value=uid
            ),
            mock.patch.object(
                self.module.subprocess, "Popen", return_value=process
            ),
        ):
            guard = self.module.ModemManagerGuard.arm("usb:1-1")
        self.assertEqual(guard.arm_receipt["status"], "armed")
        self.assertTrue(guard.arm_receipt["child_alive"])
        self.assertTrue(guard.healthy())

    def test_active_modemmanager_handshake_fault_releases_child(self):
        process = mock.Mock()
        process.stdout = mock.Mock()
        process.stdout.fileno.return_value = 9
        process.poll.return_value = None
        process.pid = 123
        with (
            mock.patch.object(
                self.module, "_modemmanager_active", return_value=True
            ),
            mock.patch.object(
                self.module, "modemmanager_uid", return_value="/sys/device"
            ),
            mock.patch.object(
                self.module.subprocess, "Popen", return_value=process
            ),
            mock.patch.object(
                self.module.select, "select", side_effect=OSError("fixture")
            ),
            mock.patch.object(
                self.module.ModemManagerGuard,
                "release",
                return_value={"released": True},
            ) as release,
        ):
            with self.assertRaises(OSError):
                self.module.ModemManagerGuard.arm("usb:1-1")
        release.assert_called_once()

    def test_guard_is_released_when_guard_receipt_persistence_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            guard = mock.Mock()
            guard.release.return_value = {
                "schema": self.module.GUARD_SCHEMA,
                "status": "released",
                "returncode": 0,
                "released": True,
            }
            guard.arm_receipt = {
                "schema": self.module.GUARD_SCHEMA,
                "status": "armed",
                "uid_sha256": "1" * 64,
                "output_sha256": "2" * 64,
                "child_alive": True,
            }
            baseline = {
                "schema": self.module.BASELINE_SCHEMA,
                "spec_sha256": self.module.digest(self.spec()),
                "topology_sha256": hashlib.sha256(b"1-1").hexdigest(),
                "identity_sha256": [],
                "exact_candidate_absent": True,
            }
            original = self.module.persist_json
            calls = 0

            def fail_second(path, value):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("fixture persistence fault")
                return original(path, value)

            with (
                mock.patch.object(
                    self.module, "capture_baseline", return_value=baseline
                ),
                mock.patch.object(
                    self.module.ModemManagerGuard,
                    "arm",
                    return_value=guard,
                ),
                mock.patch.object(
                    self.module, "persist_json", side_effect=fail_second
                ),
            ):
                with self.assertRaises(OSError):
                    with self.module.observer_session(
                        self.spec(),
                        "usb:1-1",
                        run_dir,
                        {},
                    ):
                        self.fail("observer session should not yield")
            guard.release.assert_called_once()

    def test_duplicate_receipt_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "candidate-observer.json"
            path.write_text('{"schema":"x","schema":"y"}', encoding="utf-8")
            with self.assertRaises(self.module.ObserverError):
                self.module.validate_receipt(
                    path,
                    spec=self.spec(),
                    binding={},
                    topology="usb:1-1",
                )


if __name__ == "__main__":
    unittest.main()
