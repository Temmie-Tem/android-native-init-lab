import hashlib
import importlib.util
import json
import os
import pty
import shutil
import subprocess
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


class LostGuard(HealthyGuard):
    def healthy(self, *, recheck=False):
        return False


class ExpiringGuard(HealthyGuard):
    def __init__(self, healthy_calls):
        self.healthy_calls = healthy_calls
        self.calls = 0

    def healthy(self, *, recheck=False):
        self.calls += 1
        return self.calls <= self.healthy_calls


class FinalPropertyLossGuard(HealthyGuard):
    def __init__(self):
        self.match_calls = 0

    def matches_node(self, _node):
        self.match_calls += 1
        return self.match_calls == 1


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
                "status": "armed",
                "spec_sha256": self.module.digest(self.spec()),
                "topology_sha256": hashlib.sha256(b"1-1").hexdigest(),
                "rule_sha256": hashlib.sha256(
                    self.module._guard_rule(self.spec(), "usb:1-1")
                ).hexdigest(),
                "instance_sha256": "5" * 64,
                "output_sha256": "4" * 64,
                "child_alive": True,
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

    def test_guard_loss_preempts_endpoint_timeout(self):
        temporary, master, slave, class_tty, dev_root, run_dir = self.fixture()
        self.addCleanup(temporary.cleanup)
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        session = self.session(class_tty, dev_root, run_dir)
        session.guard = LostGuard()
        receipt = session.observe(
            timeout_sec=1,
            download_departure=self.departure(),
        )
        self.assertEqual(receipt["classification"], "guard-lost")
        self.assertFalse(receipt["accepted"])
        reopened = self.module.validate_receipt(
            run_dir / "candidate-observer.json",
            spec=self.spec(),
            binding=session.binding,
            topology="usb:1-1",
        )
        self.assertFalse(reopened["accepted"])

    def test_exact_banner_survives_guard_loss_after_open(self):
        temporary, master, slave, class_tty, dev_root, run_dir = self.fixture()
        self.addCleanup(temporary.cleanup)
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        os.write(master, bytes.fromhex(self.spec()["banner_hex"]))
        session = self.session(class_tty, dev_root, run_dir)
        session.guard = ExpiringGuard(healthy_calls=3)
        receipt = session.observe(
            timeout_sec=2,
            download_departure=self.departure(),
        )
        self.assertEqual(receipt["classification"], "accepted")
        self.assertTrue(receipt["accepted"])
        self.assertGreater(session.guard.calls, 3)
        reopened = self.module.validate_receipt(
            run_dir / "candidate-observer.json",
            spec=self.spec(),
            binding=session.binding,
            topology="usb:1-1",
        )
        self.assertTrue(reopened["accepted"])

    def test_exact_banner_survives_final_guard_property_loss(self):
        temporary, master, slave, class_tty, dev_root, run_dir = self.fixture()
        self.addCleanup(temporary.cleanup)
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        os.write(master, bytes.fromhex(self.spec()["banner_hex"]))
        session = self.session(class_tty, dev_root, run_dir)
        session.guard = FinalPropertyLossGuard()
        receipt = session.observe(
            timeout_sec=2,
            download_departure=self.departure(),
        )
        self.assertEqual(receipt["classification"], "accepted")
        self.assertTrue(receipt["accepted"])
        self.assertEqual(session.guard.match_calls, 2)

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

    def test_guard_semantics_remain_bound_after_receipt_rehash(self):
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
        guard_path = run_dir / "candidate-observer-guard.json"
        guard = json.loads(guard_path.read_text(encoding="utf-8"))
        guard["spec_sha256"] = "0" * 64
        guard_payload = (
            json.dumps(guard, indent=2, sort_keys=True).encode() + b"\n"
        )
        guard_path.chmod(0o600)
        guard_path.write_bytes(guard_payload)
        receipt_path = run_dir / "candidate-observer.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["guard_sha256"] = hashlib.sha256(guard_payload).hexdigest()
        receipt_path.chmod(0o600)
        receipt_path.write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(
            self.module.ObserverError, "guard semantics"
        ):
            self.module.validate_receipt(
                receipt_path,
                spec=self.spec(),
                binding=session.binding,
                topology="usb:1-1",
            )

    def test_active_modemmanager_refusal_fails_closed(self):
        process = mock.Mock()
        process.stdin = mock.Mock()
        process.stdout = mock.Mock()
        process.stdout.fileno.return_value = 9
        process.poll.return_value = 1
        process.pid = 123
        process.returncode = 1
        with tempfile.TemporaryDirectory() as temporary:
            evidence_dir = Path(temporary)
            with (
                mock.patch.object(
                    self.module.subprocess, "Popen", return_value=process
                ) as popen,
                mock.patch.object(
                    self.module.ModemManagerGuard, "release", return_value={}
                ),
            ):
                with self.assertRaises(self.module.ObserverError):
                    self.module.ModemManagerGuard.arm(
                        self.spec(), "usb:1-1", evidence_dir=evidence_dir
                    )
            failure = json.loads(
                (
                    evidence_dir
                    / "candidate-observer-guard-arm-failure.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(failure["status"], "guard-arm-failed")
            self.assertEqual(failure["returncode"], 1)
            self.assertFalse(failure["truncated"])
            self.assertEqual(
                (
                    evidence_dir / "candidate-observer-guard-arm.raw"
                ).read_bytes(),
                b"",
            )
        command = popen.call_args.args[0]
        self.assertEqual(
            command[:9],
            [
                "/usr/bin/pkexec",
                "/usr/bin/setpriv",
                "--pdeathsig",
                "SIGTERM",
                "/usr/bin/python3",
                "-I",
                "-B",
                "-c",
                self.module.ROOT_UDEV_GUARD_CODE,
            ],
        )
        payload = self.module.base64.b64decode(command[9], validate=True)
        self.assertEqual(
            payload, self.module._guard_rule(self.spec(), "usb:1-1")
        )
        self.assertEqual(command[10], hashlib.sha256(payload).hexdigest())
        self.assertEqual(len(command), 11)

    def test_active_modemmanager_success_requires_line_and_live_child(self):
        read_fd, write_fd = os.pipe()
        self.addCleanup(os.close, write_fd)
        stream = os.fdopen(read_fd, "rb", buffering=0)
        self.addCleanup(stream.close)
        rule_sha256 = hashlib.sha256(
            self.module._guard_rule(self.spec(), "usb:1-1")
        ).hexdigest()
        os.write(
            write_fd,
            (
                self.module.GUARD_ARM_PREFIX + rule_sha256 + "\n"
            ).encode(),
        )
        process = mock.Mock()
        process.stdin = mock.Mock()
        process.stdout = stream
        process.poll.return_value = None
        process.pid = 123
        with mock.patch.object(
            self.module.subprocess, "Popen", return_value=process
        ):
            guard = self.module.ModemManagerGuard.arm(
                self.spec(), "usb:1-1"
            )
        self.assertEqual(guard.arm_receipt["status"], "armed")
        self.assertEqual(guard.arm_receipt["rule_sha256"], rule_sha256)
        self.assertTrue(guard.arm_receipt["child_alive"])
        self.assertTrue(guard.healthy())

    def test_modemmanager_release_uses_control_pipe(self):
        process = mock.Mock()
        process.stdin = mock.Mock()
        process.poll.return_value = None
        process.wait.return_value = 0
        process.returncode = 0
        guard = self.module.ModemManagerGuard(self.spec(), "usb:1-1")
        guard.process = process
        result = guard.release()
        process.stdin.write.assert_called_once_with(b"release\n")
        process.stdin.flush.assert_called_once_with()
        process.stdin.close.assert_called_once_with()
        process.wait.assert_called_once_with(timeout=10)
        self.assertEqual(result["status"], "released")
        self.assertTrue(result["released"])

    def test_modemmanager_expiry_before_release_is_not_success(self):
        process = mock.Mock()
        process.poll.return_value = self.module.GUARD_EXPIRED_EXIT
        process.returncode = self.module.GUARD_EXPIRED_EXIT
        guard = self.module.ModemManagerGuard(self.spec(), "usb:1-1")
        guard.process = process
        result = guard.release()
        process.stdin.write.assert_not_called()
        self.assertEqual(result["status"], "guard-expired")
        self.assertEqual(
            result["returncode"], self.module.GUARD_EXPIRED_EXIT
        )
        self.assertFalse(result["released"])

    def test_modemmanager_uncommanded_zero_exit_is_not_success(self):
        process = mock.Mock()
        process.poll.return_value = 0
        process.returncode = 0
        guard = self.module.ModemManagerGuard(self.spec(), "usb:1-1")
        guard.process = process
        result = guard.release()
        process.stdin.write.assert_not_called()
        self.assertEqual(result["status"], "guard-exited-uncommanded")
        self.assertEqual(result["returncode"], 0)
        self.assertFalse(result["released"])

    def test_modemmanager_release_pipe_failure_is_fail_closed(self):
        process = mock.Mock()
        process.stdin = mock.Mock()
        process.stdin.write.side_effect = BrokenPipeError("fixture")
        process.poll.return_value = None
        guard = self.module.ModemManagerGuard(self.spec(), "usb:1-1")
        guard.process = process
        result = guard.release()
        self.assertEqual(result["status"], "release-failed")
        self.assertEqual(result["error_type"], "BrokenPipeError")
        self.assertFalse(result["released"])

    def test_modemmanager_release_pipe_expiry_race_is_classified(self):
        process = mock.Mock()
        process.stdin = mock.Mock()
        process.stdin.write.side_effect = BrokenPipeError("fixture")
        process.poll.side_effect = [None, self.module.GUARD_EXPIRED_EXIT]
        process.returncode = self.module.GUARD_EXPIRED_EXIT
        guard = self.module.ModemManagerGuard(self.spec(), "usb:1-1")
        guard.process = process
        result = guard.release()
        self.assertEqual(result["status"], "guard-expired")
        self.assertEqual(
            result["returncode"], self.module.GUARD_EXPIRED_EXIT
        )
        self.assertFalse(result["released"])

    def test_modemmanager_release_pipe_uncommanded_race_is_classified(self):
        process = mock.Mock()
        process.stdin = mock.Mock()
        process.stdin.write.side_effect = BrokenPipeError("fixture")
        process.poll.side_effect = [
            None,
            self.module.GUARD_UNCOMMANDED_EXIT,
        ]
        process.returncode = self.module.GUARD_UNCOMMANDED_EXIT
        guard = self.module.ModemManagerGuard(self.spec(), "usb:1-1")
        guard.process = process
        result = guard.release()
        self.assertEqual(result["status"], "guard-exited-uncommanded")
        self.assertEqual(
            result["returncode"], self.module.GUARD_UNCOMMANDED_EXIT
        )
        self.assertFalse(result["released"])

    def test_modemmanager_release_wait_expiry_race_is_classified(self):
        process = mock.Mock()
        process.stdin = mock.Mock()
        process.poll.return_value = None
        process.returncode = None

        def expire(*, timeout):
            self.assertEqual(timeout, 10)
            process.returncode = self.module.GUARD_EXPIRED_EXIT
            return process.returncode

        process.wait.side_effect = expire
        guard = self.module.ModemManagerGuard(self.spec(), "usb:1-1")
        guard.process = process
        result = guard.release()
        self.assertEqual(result["status"], "guard-expired")
        self.assertEqual(
            result["returncode"], self.module.GUARD_EXPIRED_EXIT
        )
        self.assertFalse(result["released"])

    def test_modemmanager_release_wait_uncommanded_race_is_classified(self):
        process = mock.Mock()
        process.stdin = mock.Mock()
        process.poll.return_value = None
        process.returncode = None

        def exit_uncommanded(*, timeout):
            self.assertEqual(timeout, 10)
            process.returncode = self.module.GUARD_UNCOMMANDED_EXIT
            return process.returncode

        process.wait.side_effect = exit_uncommanded
        guard = self.module.ModemManagerGuard(self.spec(), "usb:1-1")
        guard.process = process
        result = guard.release()
        self.assertEqual(result["status"], "guard-exited-uncommanded")
        self.assertEqual(
            result["returncode"], self.module.GUARD_UNCOMMANDED_EXIT
        )
        self.assertFalse(result["released"])

    def test_modemmanager_release_timeout_is_fail_closed(self):
        process = mock.Mock()
        process.stdin = mock.Mock()
        process.poll.return_value = None
        process.wait.side_effect = subprocess.TimeoutExpired("guard", 10)
        guard = self.module.ModemManagerGuard(self.spec(), "usb:1-1")
        guard.process = process
        result = guard.release()
        self.assertEqual(result["status"], "release-failed")
        self.assertEqual(result["error_type"], "TimeoutExpired")
        self.assertFalse(result["released"])

    def test_transient_rule_is_exact_and_valid_udev_syntax(self):
        payload = self.module._guard_rule(self.spec(), "usb:1-1")
        text = payload.decode("ascii")
        self.assertIn('SUBSYSTEM=="usb"', text)
        self.assertIn('KERNEL=="1-1"', text)
        self.assertIn('ATTR{idVendor}=="04e8"', text)
        self.assertIn('ATTR{idProduct}=="6861"', text)
        self.assertIn(
            f'ATTR{{serial}}=="{self.spec()["usb_serial"]}"', text
        )
        self.assertIn('ENV{ID_USB_INTERFACE_NUM}=="00"', text)
        self.assertIn('ENV{ID_MM_DEVICE_IGNORE}="1"', text)
        self.assertIn('ENV{ID_MM_PORT_IGNORE}="1"', text)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "guard.rules"
            path.write_bytes(payload)
            completed = subprocess.run(
                ["/usr/bin/udevadm", "verify", str(path)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(
                completed.returncode,
                0,
                completed.stderr.decode("utf-8", "replace"),
            )

    def test_root_udev_guard_embedded_source_compiles(self):
        compile(
            self.module.ROOT_UDEV_GUARD_CODE,
            "<device-action-root-udev-guard>",
            "exec",
        )

    def test_root_udev_guard_lifecycle_in_user_namespace(self):
        bwrap = shutil.which("bwrap")
        if bwrap is None:
            self.skipTest("bubblewrap is unavailable")
        payload = self.module._guard_rule(self.spec(), "usb:1-1")
        payload_sha256 = hashlib.sha256(payload).hexdigest()
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary)
            fake_udevadm = evidence / "udevadm"
            fake_udevadm.write_text(
                "#!/bin/sh\n"
                "printf '%s\\n' \"$*\" >> /tmp/evidence/udevadm.log\n",
                encoding="ascii",
            )
            fake_udevadm.chmod(0o700)
            command = [
                bwrap,
                "--unshare-user",
                "--uid",
                "0",
                "--gid",
                "0",
                "--unshare-pid",
                "--ro-bind",
                "/",
                "/",
                "--dev",
                "/dev",
                "--tmpfs",
                "/run",
                "--dir",
                "/run/udev",
                "--dir",
                "/run/udev/rules.d",
                "--tmpfs",
                "/tmp",
                "--dir",
                "/tmp/evidence",
                "--bind",
                str(evidence),
                "/tmp/evidence",
                "--ro-bind",
                str(fake_udevadm),
                "/usr/bin/udevadm",
                "--",
                "/usr/bin/python3",
                "-I",
                "-B",
                "-c",
                self.module.ROOT_UDEV_GUARD_CODE,
                self.module.base64.b64encode(payload).decode("ascii"),
                payload_sha256,
            ]
            completed = subprocess.run(
                command,
                input=b"release\n",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=15,
                check=False,
                env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"},
            )
            if (
                completed.returncode == 1
                and b"new namespace" in completed.stderr
            ):
                self.skipTest("unprivileged user namespace is unavailable")
            self.assertEqual(
                completed.returncode,
                0,
                completed.stderr.decode("utf-8", "replace"),
            )
            self.assertEqual(
                completed.stdout,
                (
                    self.module.GUARD_ARM_PREFIX
                    + payload_sha256
                    + "\n"
                ).encode(),
            )
            self.assertEqual(
                (evidence / "udevadm.log").read_text(
                    encoding="ascii"
                ).splitlines(),
                [
                    "verify /run/udev/rules.d/"
                    "79-device-action-f1-cdc-acm-guard.rules",
                    "control --reload",
                    "control --reload",
                ],
            )
            uncommanded = subprocess.run(
                command,
                input=b"",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=15,
                check=False,
                env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"},
            )
            self.assertEqual(
                uncommanded.returncode,
                self.module.GUARD_UNCOMMANDED_EXIT,
                uncommanded.stderr.decode("utf-8", "replace"),
            )
            self.assertEqual(
                len(
                    (evidence / "udevadm.log").read_text(
                        encoding="ascii"
                    ).splitlines()
                ),
                6,
            )
            expiry_code = self.module.ROOT_UDEV_GUARD_CODE.replace(
                "MAX_SEC = 360.0", "MAX_SEC = 0.0"
            )
            self.assertNotEqual(
                expiry_code, self.module.ROOT_UDEV_GUARD_CODE
            )
            expiry_command = list(command)
            expiry_command[expiry_command.index("-c") + 1] = expiry_code
            expired = subprocess.run(
                expiry_command,
                input=b"",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=15,
                check=False,
                env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"},
            )
            self.assertEqual(
                expired.returncode,
                self.module.GUARD_EXPIRED_EXIT,
                expired.stderr.decode("utf-8", "replace"),
            )
            self.assertEqual(
                (evidence / "udevadm.log").read_text(
                    encoding="ascii"
                ).splitlines(),
                [
                    "verify /run/udev/rules.d/"
                    "79-device-action-f1-cdc-acm-guard.rules",
                    "control --reload",
                    "control --reload",
                    "verify /run/udev/rules.d/"
                    "79-device-action-f1-cdc-acm-guard.rules",
                    "control --reload",
                    "control --reload",
                    "verify /run/udev/rules.d/"
                    "79-device-action-f1-cdc-acm-guard.rules",
                    "control --reload",
                    "control --reload",
                ],
            )
            select_block = (
                "            readable, _, _ = select.select(\n"
                "                [sys.stdin.buffer], [], [], "
                "min(0.2, remaining)\n"
                "            )\n"
            )
            post_select_expiry = (
                self.module.ROOT_UDEV_GUARD_CODE.replace(
                    "MAX_SEC = 360.0", "MAX_SEC = 0.02"
                ).replace(
                    select_block,
                    "            time.sleep(0.05)\n"
                    "            readable = [sys.stdin.buffer]\n",
                )
            )
            self.assertNotEqual(
                post_select_expiry, self.module.ROOT_UDEV_GUARD_CODE
            )
            expiry_race_command = list(command)
            expiry_race_command[
                expiry_race_command.index("-c") + 1
            ] = post_select_expiry
            expiry_race = subprocess.run(
                expiry_race_command,
                input=b"release\n",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=15,
                check=False,
                env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"},
            )
            self.assertEqual(
                expiry_race.returncode,
                self.module.GUARD_EXPIRED_EXIT,
                expiry_race.stderr.decode("utf-8", "replace"),
            )
            post_select_signal = self.module.ROOT_UDEV_GUARD_CODE.replace(
                select_block,
                "            request_stop(signal.SIGTERM, None)\n"
                "            readable = [sys.stdin.buffer]\n",
            )
            self.assertNotEqual(
                post_select_signal, self.module.ROOT_UDEV_GUARD_CODE
            )
            signal_race_command = list(command)
            signal_race_command[
                signal_race_command.index("-c") + 1
            ] = post_select_signal
            signal_race = subprocess.run(
                signal_race_command,
                input=b"release\n",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=15,
                check=False,
                env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"},
            )
            self.assertEqual(
                signal_race.returncode,
                self.module.GUARD_UNCOMMANDED_EXIT,
                signal_race.stderr.decode("utf-8", "replace"),
            )
            read_block = (
                "            command = sys.stdin.buffer.readline()\n"
            )
            post_read_expiry = (
                self.module.ROOT_UDEV_GUARD_CODE.replace(
                    "MAX_SEC = 360.0", "MAX_SEC = 0.02"
                ).replace(
                    read_block,
                    read_block + "            time.sleep(0.05)\n",
                )
            )
            self.assertNotEqual(
                post_read_expiry, self.module.ROOT_UDEV_GUARD_CODE
            )
            post_read_expiry_command = list(command)
            post_read_expiry_command[
                post_read_expiry_command.index("-c") + 1
            ] = post_read_expiry
            post_read_expired = subprocess.run(
                post_read_expiry_command,
                input=b"release\n",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=15,
                check=False,
                env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"},
            )
            self.assertEqual(
                post_read_expired.returncode,
                self.module.GUARD_EXPIRED_EXIT,
                post_read_expired.stderr.decode("utf-8", "replace"),
            )
            post_read_signal = self.module.ROOT_UDEV_GUARD_CODE.replace(
                read_block,
                read_block
                + "            request_stop(signal.SIGTERM, None)\n",
            )
            self.assertNotEqual(
                post_read_signal, self.module.ROOT_UDEV_GUARD_CODE
            )
            post_read_signal_command = list(command)
            post_read_signal_command[
                post_read_signal_command.index("-c") + 1
            ] = post_read_signal
            post_read_signaled = subprocess.run(
                post_read_signal_command,
                input=b"release\n",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=15,
                check=False,
                env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"},
            )
            self.assertEqual(
                post_read_signaled.returncode,
                self.module.GUARD_UNCOMMANDED_EXIT,
                post_read_signaled.stderr.decode("utf-8", "replace"),
            )
            self.assertEqual(
                len(
                    (evidence / "udevadm.log").read_text(
                        encoding="ascii"
                    ).splitlines()
                ),
                21,
            )

    def test_active_guard_requires_udev_ignore_properties_on_tty(self):
        guard = self.module.ModemManagerGuard(self.spec(), "usb:1-1")
        with mock.patch.object(
            self.module,
            "_udev_properties",
            return_value={
                "ID_MM_DEVICE_IGNORE": "1",
                "ID_MM_PORT_IGNORE": "1",
            },
        ):
            self.assertTrue(guard.matches_node(Path("/")))
        with mock.patch.object(
            self.module,
            "_udev_properties",
            return_value={"ID_MM_DEVICE_IGNORE": "1"},
        ):
            self.assertFalse(guard.matches_node(Path("/")))

    def test_modemmanager_launch_failure_is_durable(self):
        with tempfile.TemporaryDirectory() as temporary:
            evidence_dir = Path(temporary)
            with mock.patch.object(
                self.module.subprocess,
                "Popen",
                side_effect=FileNotFoundError("fixture"),
            ):
                with self.assertRaisesRegex(
                    self.module.ObserverError, "launch failed"
                ):
                    self.module.ModemManagerGuard.arm(
                        self.spec(), "usb:1-1", evidence_dir=evidence_dir
                    )
            failure = json.loads(
                (
                    evidence_dir
                    / "candidate-observer-guard-arm-failure.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(failure["status"], "launch-failed")
            self.assertIsNone(failure["returncode"])
            self.assertTrue(failure["bounded"])
            self.assertFalse(failure["truncated"])

    def test_modemmanager_failure_evidence_is_bounded(self):
        with tempfile.TemporaryDirectory() as temporary:
            evidence_dir = Path(temporary)
            payload = b"x" * (20 * 1024)
            self.module._persist_guard_arm_failure(
                evidence_dir, payload, 1, "guard-arm-failed"
            )
            raw = (
                evidence_dir / "candidate-observer-guard-arm.raw"
            ).read_bytes()
            failure = json.loads(
                (
                    evidence_dir
                    / "candidate-observer-guard-arm-failure.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(len(raw), 16 * 1024)
            self.assertTrue(failure["bounded"])
            self.assertTrue(failure["truncated"])

    def test_failure_evidence_collision_does_not_mask_launch_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            evidence_dir = Path(temporary)
            (
                evidence_dir / "candidate-observer-guard-arm.raw"
            ).write_bytes(b"collision")
            with mock.patch.object(
                self.module.subprocess,
                "Popen",
                side_effect=FileNotFoundError("fixture"),
            ):
                with self.assertRaisesRegex(
                    self.module.ObserverError, "guard launch failed"
                ):
                    self.module.ModemManagerGuard.arm(
                        self.spec(), "usb:1-1", evidence_dir=evidence_dir
                    )

    def test_active_modemmanager_handshake_fault_releases_child(self):
        process = mock.Mock()
        process.stdout = mock.Mock()
        process.stdout.fileno.return_value = 9
        process.poll.return_value = None
        process.pid = 123
        with (
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
                self.module.ModemManagerGuard.arm(
                    self.spec(), "usb:1-1"
                )
        release.assert_called_once()

    def test_modemmanager_release_nonzero_exit_is_fail_closed(self):
        process = mock.Mock()
        process.poll.return_value = 1
        process.returncode = 1
        guard = self.module.ModemManagerGuard(self.spec(), "usb:1-1")
        guard.process = process
        result = guard.release()
        self.assertEqual(result["status"], "release-failed")
        self.assertEqual(result["returncode"], 1)
        self.assertFalse(result["released"])

    def test_guard_release_validator_accepts_only_exact_success(self):
        valid = {
            "schema": self.module.GUARD_SCHEMA,
            "status": "released",
            "instance_sha256": "5" * 64,
            "returncode": 0,
            "released": True,
        }
        mutations = (
            {**valid, "schema": "wrong"},
            {**valid, "status": "release-failed"},
            {**valid, "returncode": 1},
            {**valid, "returncode": False},
            {**valid, "returncode": 0.0},
            {**valid, "instance_sha256": "6" * 64},
            {**valid, "released": False},
            {**valid, "extra": True},
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "release.json"
            arm_path = Path(temporary) / "arm.json"
            arm_path.write_text(
                json.dumps(
                    {
                        "schema": self.module.GUARD_SCHEMA,
                        "status": "armed",
                        "spec_sha256": "1" * 64,
                        "topology_sha256": "2" * 64,
                        "rule_sha256": "3" * 64,
                        "instance_sha256": "5" * 64,
                        "output_sha256": "4" * 64,
                        "child_alive": True,
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            path.write_text(
                json.dumps(valid, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            self.assertEqual(
                self.module.validate_guard_release(path, arm_path), valid
            )
            for mutation in mutations:
                with self.subTest(mutation=mutation):
                    path.write_text(
                        json.dumps(mutation, sort_keys=True) + "\n",
                        encoding="utf-8",
                    )
                    with self.assertRaises(self.module.ObserverError):
                        self.module.validate_guard_release(path, arm_path)
            path.unlink()
            with self.assertRaises(self.module.ObserverError):
                self.module.validate_guard_release(path, arm_path)

    def test_guard_release_reader_preserves_expiry_but_validator_rejects_it(
        self,
    ):
        expired = {
            "schema": self.module.GUARD_SCHEMA,
            "status": "guard-expired",
            "instance_sha256": "5" * 64,
            "returncode": self.module.GUARD_EXPIRED_EXIT,
            "released": False,
        }
        arm = {
            "schema": self.module.GUARD_SCHEMA,
            "status": "armed",
            "spec_sha256": "1" * 64,
            "topology_sha256": "2" * 64,
            "rule_sha256": "3" * 64,
            "instance_sha256": "5" * 64,
            "output_sha256": "4" * 64,
            "child_alive": True,
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "release.json"
            arm_path = Path(temporary) / "arm.json"
            path.write_text(
                json.dumps(expired, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            arm_path.write_text(
                json.dumps(arm, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            self.assertEqual(
                self.module.read_guard_release(path, arm_path), expired
            )
            with self.assertRaisesRegex(
                self.module.ObserverError, "was not commanded"
            ):
                self.module.validate_guard_release(path, arm_path)
            for mutation in (
                {**expired, "returncode": 0},
                {**expired, "released": True},
                {**expired, "status": "released"},
            ):
                path.write_text(
                    json.dumps(mutation, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                with self.assertRaises(self.module.ObserverError):
                    self.module.read_guard_release(path, arm_path)

    def test_guard_release_reader_rejects_uncommanded_cleanup_failure(self):
        arm = {
            "schema": self.module.GUARD_SCHEMA,
            "status": "armed",
            "spec_sha256": "1" * 64,
            "topology_sha256": "2" * 64,
            "rule_sha256": "3" * 64,
            "instance_sha256": "5" * 64,
            "output_sha256": "4" * 64,
            "child_alive": True,
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "release.json"
            arm_path = Path(temporary) / "arm.json"
            arm_path.write_text(
                json.dumps(arm, sort_keys=True) + "\n", encoding="utf-8"
            )
            for returncode in (0, self.module.GUARD_UNCOMMANDED_EXIT):
                value = {
                    "schema": self.module.GUARD_SCHEMA,
                    "status": "guard-exited-uncommanded",
                    "instance_sha256": "5" * 64,
                    "returncode": returncode,
                    "released": False,
                }
                path.write_text(
                    json.dumps(value, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                self.assertEqual(
                    self.module.read_guard_release(path, arm_path), value
                )
            value["returncode"] = 1
            path.write_text(
                json.dumps(value, sort_keys=True) + "\n", encoding="utf-8"
            )
            with self.assertRaises(self.module.ObserverError):
                self.module.read_guard_release(path, arm_path)
            failed = {
                **value,
                "status": "release-failed",
                "returncode": self.module.GUARD_UNCOMMANDED_EXIT,
            }
            path.write_text(
                json.dumps(failed, sort_keys=True) + "\n", encoding="utf-8"
            )
            with self.assertRaises(self.module.ObserverError):
                self.module.read_guard_release(path, arm_path)

    def test_stale_guard_release_stops_before_guard_arm(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            (run_dir / "candidate-observer-guard-release.json").write_text(
                "{}\n", encoding="utf-8"
            )
            with mock.patch.object(
                self.module.ModemManagerGuard, "arm"
            ) as arm:
                with self.assertRaisesRegex(
                    self.module.ObserverError, "already exists"
                ):
                    with self.module.observer_session(
                        self.spec(),
                        "usb:1-1",
                        run_dir,
                        {"binding": "fixture"},
                    ):
                        pass
            arm.assert_not_called()

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
                "spec_sha256": "1" * 64,
                "topology_sha256": "2" * 64,
                "rule_sha256": "3" * 64,
                "instance_sha256": "5" * 64,
                "output_sha256": "4" * 64,
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
