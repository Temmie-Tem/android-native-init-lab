from __future__ import annotations

import hashlib
import os
import pty
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import device_action_cdc_acm_observer_v1 as observer  # noqa: E402
import s22plus_fyg8_p325_cdc_acm_guard_adapter as adapter  # noqa: E402


REQUIRED_FLAGS = set(adapter.REQUIRED_MODEM_MANAGER_PROPERTIES)


def _spec() -> dict[str, str]:
    run_id = "c325f1e0a90b5e6d7c8a9b0c1d2e3f4b"
    return {
        "kind": "exact_cdc_acm_banner_v1",
        "usb_vendor_id": "04e8",
        "usb_product_id": "6861",
        "usb_serial": "S22E3" + run_id,
        "usb_driver": "cdc_acm",
        "usb_interface_number": "00",
        "banner_hex": (
            "S22PLUS-FYG8-E3:" + run_id + "\n"
        ).encode("ascii").hex(),
    }


class RecordingGuard:
    """A host-only stand-in for the v1 guard's two-flag matcher."""

    def __init__(self, tty_class: Path, flags: set[str]):
        self.tty_class = tty_class.resolve()
        self.flags = set(flags)
        self.calls: list[Path] = []

    def healthy(self, *, recheck: bool = False) -> bool:
        return True

    def matches_node(self, node: Path) -> bool:
        resolved = Path(node).resolve()
        self.calls.append(resolved)
        return (
            resolved == self.tty_class
            and REQUIRED_FLAGS.issubset(self.flags)
        )


class ObserverFixture:
    def __init__(self, *, dev_value: str | None = None):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.class_tty = self.root / "sys/class/tty"
        self.class_tty.mkdir(parents=True)
        self.drivers = self.root / "sys/drivers/cdc_acm"
        self.drivers.mkdir(parents=True)
        self.usb = self.root / "sys/devices/3-1.3"
        self.interface = self.usb / "3-1.3:1.0"
        self.interface.mkdir(parents=True)
        (self.usb / "idVendor").write_text("04e8\n", encoding="ascii")
        (self.usb / "idProduct").write_text("6861\n", encoding="ascii")
        (self.usb / "serial").write_text(
            _spec()["usb_serial"] + "\n", encoding="ascii"
        )
        (self.interface / "bInterfaceNumber").write_text(
            "00\n", encoding="ascii"
        )
        (self.interface / "driver").symlink_to(self.drivers)

        self.master, self.slave = pty.openpty()
        slave_path = Path(os.ttyname(self.slave))
        slave_info = slave_path.stat()
        self.tty_class = self.class_tty / "ttyACM0"
        self.tty_class.mkdir()
        (self.tty_class / "device").symlink_to(self.interface)
        (self.tty_class / "dev").write_text(
            dev_value
            if dev_value is not None
            else f"{os.major(slave_info.st_rdev)}:{os.minor(slave_info.st_rdev)}\n",
            encoding="ascii",
        )
        self.dev_root = self.root / "dev"
        self.dev_root.mkdir()
        (self.dev_root / "ttyACM0").symlink_to(slave_path)
        self.run_dir = self.root / "run"
        self.run_dir.mkdir()

    def close(self) -> None:
        for descriptor in (self.master, self.slave):
            try:
                os.close(descriptor)
            except OSError:
                pass
        self.temporary.cleanup()


def _session(
    fixture: ObserverFixture,
    *,
    flags: set[str] | None = None,
    spec: dict[str, str] | None = None,
) -> tuple[observer.ObserverSession, RecordingGuard]:
    selected_spec = spec or _spec()
    guard = RecordingGuard(
        fixture.tty_class,
        REQUIRED_FLAGS if flags is None else flags,
    )
    baseline = {
        "schema": observer.BASELINE_SCHEMA,
        "spec_sha256": observer.digest(selected_spec),
        "topology_sha256": hashlib.sha256(b"3-1.3").hexdigest(),
        "identity_sha256": [],
        "exact_candidate_absent": True,
    }
    baseline_receipt = observer.persist_json(
        fixture.run_dir / "candidate-observer-baseline.json", baseline
    )
    session = observer.ObserverSession(
        selected_spec,
        "usb:3-1.3",
        fixture.run_dir,
        {
            "approval_binding_sha256": "a" * 64,
            "bundle_sha256": "b" * 64,
            "manifest_id": "p325-fixture",
            "candidate_ap_sha256": "c" * 64,
        },
        baseline,
        baseline_receipt,
        guard,
        {"sha256": "d" * 64},
        fixture.class_tty,
        fixture.dev_root,
    )
    return session, guard


def _departure() -> dict[str, object]:
    return {
        "download_endpoint_absent": True,
        "absence_timed_out": False,
        "sequence": 1,
    }


def _open_counter(fixture: ObserverFixture):
    target = (fixture.dev_root / "ttyACM0").absolute()
    real_open = observer.os.open
    calls: list[Path] = []

    def counted(path, *args, **kwargs):
        try:
            if Path(path).absolute() == target:
                calls.append(target)
        except (TypeError, ValueError):
            pass
        return real_open(path, *args, **kwargs)

    return calls, mock.patch.object(observer.os, "open", side_effect=counted)


class P325GuardAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = ObserverFixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def test_tty_only_flags_pass_and_open_once(self) -> None:
        session, guard = _session(self.fixture)
        banner = bytes.fromhex(_spec()["banner_hex"])
        os.write(self.fixture.master, banner)
        calls, counter = _open_counter(self.fixture)
        with counter, adapter.adapt_delegate(session) as audit:
            receipt = session.observe(
                timeout_sec=2, download_departure=_departure()
            )

        self.assertEqual(receipt["classification"], "accepted")
        self.assertTrue(receipt["accepted"])
        self.assertEqual(
            (self.fixture.run_dir / "candidate-observer.raw").read_bytes(),
            banner,
        )
        self.assertEqual(calls, [self.fixture.dev_root / "ttyACM0"])
        self.assertEqual(audit.count, 2)
        self.assertEqual(guard.calls, [self.fixture.tty_class.resolve()] * 2)

    def test_interface_properties_absent_do_not_block_tty_probe(self) -> None:
        session, guard = _session(self.fixture)
        banner = bytes.fromhex(_spec()["banner_hex"])
        os.write(self.fixture.master, banner)
        interface = self.fixture.interface.resolve()
        original = guard.matches_node

        def interface_absent(node: Path) -> bool:
            if Path(node).resolve() == interface:
                guard.calls.append(interface)
                return False
            return original(node)

        guard.matches_node = interface_absent
        with adapter.adapt_delegate(session) as audit:
            receipt = session.observe(
                timeout_sec=2, download_departure=_departure()
            )

        self.assertEqual(receipt["classification"], "accepted")
        self.assertEqual(audit.nodes, [self.fixture.tty_class.resolve()] * 2)
        self.assertNotIn(interface, audit.nodes)

    def test_both_preopen_and_postread_probes_use_tty_class(self) -> None:
        session, guard = _session(self.fixture)
        os.write(self.fixture.master, bytes.fromhex(_spec()["banner_hex"]))
        with adapter.adapt_delegate(session) as audit:
            receipt = session.observe(
                timeout_sec=2, download_departure=_departure()
            )

        self.assertTrue(receipt["accepted"])
        self.assertEqual(audit.count, 2)
        self.assertEqual(audit.nodes, [self.fixture.tty_class.resolve()] * 2)
        self.assertEqual(guard.calls, audit.nodes)

    def test_postread_property_loss_keeps_base_exact_banner_semantics(self) -> None:
        session, guard = _session(self.fixture)
        os.write(self.fixture.master, bytes.fromhex(_spec()["banner_hex"]))
        original = guard.matches_node
        probe = 0

        def lose_after_open(node: Path) -> bool:
            nonlocal probe
            probe += 1
            if probe == 2:
                guard.calls.append(Path(node).resolve())
                return False
            return original(node)

        guard.matches_node = lose_after_open
        with adapter.adapt_delegate(session) as audit:
            receipt = session.observe(
                timeout_sec=2, download_departure=_departure()
            )

        self.assertEqual(receipt["classification"], "accepted")
        self.assertTrue(receipt["accepted"])
        self.assertEqual(audit.nodes, [self.fixture.tty_class.resolve()] * 2)
        self.assertEqual(guard.calls, audit.nodes)

    def test_missing_device_ignore_flag_fails_closed_raw_zero(self) -> None:
        session, guard = _session(
            self.fixture, flags={"ID_MM_PORT_IGNORE"}
        )
        calls, counter = _open_counter(self.fixture)
        with counter, adapter.adapt_delegate(session) as audit:
            receipt = session.observe(
                timeout_sec=2, download_departure=_departure()
            )

        self.assertEqual(receipt["classification"], "identity-mismatch")
        self.assertFalse(receipt["accepted"])
        self.assertEqual(
            (self.fixture.run_dir / "candidate-observer.raw").read_bytes(), b""
        )
        self.assertEqual(calls, [])
        self.assertEqual(audit.nodes, [self.fixture.tty_class.resolve()])
        self.assertEqual(guard.calls, audit.nodes)

    def test_missing_port_ignore_flag_fails_closed_raw_zero(self) -> None:
        session, guard = _session(
            self.fixture, flags={"ID_MM_DEVICE_IGNORE"}
        )
        calls, counter = _open_counter(self.fixture)
        with counter, adapter.adapt_delegate(session) as audit:
            receipt = session.observe(
                timeout_sec=2, download_departure=_departure()
            )

        self.assertEqual(receipt["classification"], "identity-mismatch")
        self.assertFalse(receipt["accepted"])
        self.assertEqual(
            (self.fixture.run_dir / "candidate-observer.raw").read_bytes(), b""
        )
        self.assertEqual(calls, [])
        self.assertEqual(audit.nodes, [self.fixture.tty_class.resolve()])
        self.assertEqual(guard.calls, audit.nodes)

    def test_wrong_identity_fails_closed_before_open_raw_zero(self) -> None:
        wrong_spec = {**_spec(), "usb_serial": "S22E3" + "f" * 32}
        session, guard = _session(self.fixture, spec=wrong_spec)
        calls, counter = _open_counter(self.fixture)
        with counter, adapter.adapt_delegate(session) as audit:
            receipt = session.observe(
                timeout_sec=1, download_departure=_departure()
            )

        self.assertEqual(receipt["classification"], "identity-mismatch")
        self.assertFalse(receipt["accepted"])
        self.assertEqual(
            (self.fixture.run_dir / "candidate-observer.raw").read_bytes(), b""
        )
        self.assertEqual(calls, [])
        self.assertEqual(audit.nodes, [])
        self.assertEqual(guard.calls, [])

    def test_major_minor_drift_fails_closed_before_open_raw_zero(self) -> None:
        fixture = self.fixture
        fixture.close()
        self.fixture = ObserverFixture(dev_value="1:3\n")
        session, guard = _session(self.fixture)
        calls, counter = _open_counter(self.fixture)
        with counter, adapter.adapt_delegate(session) as audit:
            receipt = session.observe(
                timeout_sec=2, download_departure=_departure()
            )

        self.assertEqual(receipt["classification"], "identity-mismatch")
        self.assertFalse(receipt["accepted"])
        self.assertEqual(
            (self.fixture.run_dir / "candidate-observer.raw").read_bytes(), b""
        )
        self.assertEqual(calls, [])
        self.assertEqual(audit.nodes, [self.fixture.tty_class.resolve()])
        self.assertEqual(guard.calls, audit.nodes)

    def test_adapter_restores_delegate_read_and_guard_methods(self) -> None:
        session, _guard = _session(self.fixture)
        original_read = session._read_endpoint
        original_matches = session.guard.matches_node
        with adapter.adapt_delegate(session) as audit:
            self.assertIsNot(session._read_endpoint, original_read)
            self.assertEqual(audit.count, 0)
        self.assertEqual(session._read_endpoint.__func__, original_read.__func__)
        self.assertIs(session._read_endpoint.__self__, original_read.__self__)
        self.assertEqual(session.guard.matches_node.__func__, original_matches.__func__)
        self.assertIs(session.guard.matches_node.__self__, original_matches.__self__)

    def test_p324_selector_contract_remains_the_loaded_base(self) -> None:
        self.assertEqual(
            adapter.BASE_CONTRACT_ID,
            "s22plus-fyg8-p324-cdc-acm-exact-lane-v1",
        )
        self.assertEqual(adapter.p324.CONTRACT_ID, adapter.BASE_CONTRACT_ID)
        self.assertEqual(
            adapter.p324.lane.CANDIDATE_TOPOLOGY,
            "usb:3-1.3",
        )
        self.assertEqual(adapter.p324.lane.SOURCE_TOPOLOGY, "usb:2-1.3")


if __name__ == "__main__":
    unittest.main()
