import dataclasses
import importlib.util
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


SCRIPT_DIR = Path("workspace/public/src/scripts/revalidation")
IDENTITY_SCRIPT = SCRIPT_DIR / "s22plus_odin_usbfs_identity.py"
CORE_SCRIPT = SCRIPT_DIR / "s22plus_odin_transition_core.py"
USB_008 = "/dev/bus/usb/002/008"


def load_module(name, path):
    script_dir = str(SCRIPT_DIR.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def node(module, **changes):
    values = {
        "path": USB_008,
        "st_dev": 6,
        "st_ino": 101,
        "st_rdev": os.makedev(189, 135),
        "st_nlink": 1,
        "st_file_type": stat.S_IFCHR,
        "st_mode": 0o660,
        "st_uid": 0,
        "st_gid": 46,
        "birth_time_ns": 1_721_234_567_123_456_789,
        "device_major": 189,
        "device_minor": 135,
        "st_atime_ns": 100,
        "st_ctime_ns": 200,
        "st_mtime_ns": 300,
    }
    values.update(changes)
    return module.UsbfsNodeSnapshot(**values)


def sequence_inventory(*inventories):
    values = iter(inventories)
    return lambda: dict(next(values))


class S22PlusOdinUsbfsIdentityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module("s22plus_odin_usbfs_identity", IDENTITY_SCRIPT)
        cls.core = load_module("s22plus_odin_transition_core_measured_test", CORE_SCRIPT)

    def test_birth_time_parser_is_exact(self):
        module = self.module
        self.assertIsNone(module.parse_birth_time_ns("-"))
        value = module.parse_birth_time_ns("2026-07-20 14:52:39.123456789 +0000")
        self.assertEqual(value % 1_000_000_000, 123_456_789)
        for malformed in (
            "",
            "2026-07-20T14:52:39.123456789Z",
            "2026-07-20 14:52:39 +0000",
            "2026-07-20 14:52:39.123456789 UTC",
        ):
            with self.subTest(malformed=malformed):
                with self.assertRaises(module.UsbfsIdentityError):
                    module.parse_birth_time_ns(malformed)

    def test_birth_time_reader_invokes_only_exact_bounded_stat(self):
        module = self.module
        completed = SimpleNamespace(
            returncode=0,
            stdout=b"2026-07-20 14:52:39.123456789 +0000",
            stderr=b"",
        )
        metadata = SimpleNamespace(
            st_dev=1,
            st_ino=2,
            st_mode=stat.S_IFREG | 0o755,
            st_nlink=1,
            st_uid=0,
            st_gid=0,
            st_size=100,
            st_mtime_ns=10,
            st_ctime_ns=20,
        )
        with mock.patch.object(module.os, "open", return_value=42), mock.patch.object(
            module.os, "fstat", return_value=metadata
        ), mock.patch.object(module.os, "close") as close, mock.patch.object(
            module.subprocess, "run", return_value=completed
        ) as run:
            result = module.read_birth_time_ns(USB_008)
        self.assertEqual(result % 1_000_000_000, 123_456_789)
        run.assert_called_once_with(
            ["stat", "--printf=%w", "--", USB_008],
            executable="/proc/self/fd/42",
            pass_fds=(42,),
            stdout=module.subprocess.PIPE,
            stderr=module.subprocess.PIPE,
            timeout=5.0,
            check=False,
        )
        close.assert_called_once_with(42)

    def test_source_has_no_device_mutation_or_transfer_surface(self):
        source = IDENTITY_SCRIPT.read_text(encoding="utf-8")
        for forbidden in (
            '"adb"',
            "'adb'",
            '"odin4"',
            "'odin4'",
            "os.write(",
            "os.unlink(",
            "os.chmod(",
            "os.chown(",
            "os.O_WRONLY",
            "os.O_RDWR",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def test_exact_three_timestamp_changes_are_allowed_and_recorded(self):
        module = self.module
        before = node(module)
        after = dataclasses.replace(
            before,
            st_atime_ns=101,
            st_ctime_ns=201,
            st_mtime_ns=301,
        )
        evidence = module.transition_evidence(before, after)
        self.assertEqual(evidence["immutable_changes"], [])
        self.assertEqual(
            evidence["metadata_changes"],
            ["st_atime_ns", "st_ctime_ns", "st_mtime_ns"],
        )
        self.assertEqual(
            evidence["allowed_metadata_fields"],
            ["st_atime_ns", "st_ctime_ns", "st_mtime_ns"],
        )
        self.assertEqual(
            module.immutable_identity(before), module.immutable_identity(after)
        )

    def test_every_immutable_field_change_is_rejected(self):
        module = self.module
        before = node(module)
        mutations = {
            "st_dev": 7,
            "st_ino": 102,
            "st_rdev": os.makedev(189, 136),
            "st_nlink": 2,
            "st_file_type": stat.S_IFREG,
            "st_mode": 0o600,
            "st_uid": 1000,
            "st_gid": 1000,
            "birth_time_ns": before.birth_time_ns + 1,
            "device_major": 188,
            "device_minor": 136,
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                after = dataclasses.replace(before, **{field: value})
                with self.assertRaises(module.UsbfsIdentityError):
                    module.transition_evidence(before, after)
        moved = dataclasses.replace(
            before,
            path="/dev/bus/usb/002/009",
            st_rdev=os.makedev(189, 136),
            device_minor=136,
        )
        with self.assertRaises(module.UsbfsIdentityError):
            module.transition_evidence(before, moved)
        with self.assertRaises(module.UsbfsIdentityError):
            module.immutable_identity(dataclasses.replace(before, birth_time_ns=None))

    def test_evidence_tampering_is_rejected(self):
        module = self.module
        before = node(module)
        after = dataclasses.replace(before, st_ctime_ns=201)
        evidence = module.transition_evidence(before, after)
        cases = []
        changed_identity = dict(evidence)
        changed_identity["identity"] = module.IDENTITY_PREFIX + "0" * 64
        cases.append(changed_identity)
        widened_policy = dict(evidence)
        widened_policy["allowed_metadata_fields"] = list(
            module.MUTABLE_METADATA_FIELDS
        ) + ["st_uid"]
        cases.append(widened_policy)
        hidden_diff = dict(evidence)
        hidden_diff["metadata_changes"] = []
        cases.append(hidden_diff)
        for value in cases:
            with self.assertRaises(module.UsbfsIdentityError):
                module.validate_transition_evidence(value)

    def test_observer_is_single_enumeration_and_fail_closed(self):
        module = self.module
        before = node(module)
        after = dataclasses.replace(before, st_ctime_ns=201)
        observer = module.MeasuredUsbfsIdentityObserver(
            inventory_reader=sequence_inventory(
                {USB_008: before},
                {USB_008: after},
            ),
        )
        inventory = observer.inventory()
        self.assertEqual(inventory[USB_008], module.immutable_identity(before))
        self.assertEqual(observer.identity(USB_008), inventory[USB_008])
        evidence = observer.evidence((USB_008,))
        self.assertEqual(
            evidence["node_transitions"][0]["metadata_changes"],
            ["st_ctime_ns"],
        )
        with self.assertRaises(module.UsbfsIdentityError):
            observer.inventory()

        replaced = dataclasses.replace(before, st_ino=102)
        observer = module.MeasuredUsbfsIdentityObserver(
            inventory_reader=sequence_inventory(
                {USB_008: before},
                {USB_008: replaced},
            ),
        )
        observer.inventory()
        with self.assertRaises(module.UsbfsIdentityError):
            observer.identity(USB_008)

    def test_inventory_membership_and_unrelated_replacement_are_rejected(self):
        module = self.module
        before = node(module)
        other_path = "/dev/bus/usb/001/001"
        other = node(
            module,
            path=other_path,
            st_ino=55,
            st_rdev=os.makedev(189, 0),
            device_minor=0,
        )
        with self.assertRaises(module.UsbfsIdentityError):
            module.enumeration_evidence(
                {USB_008: before},
                {USB_008: before, other_path: other},
                (USB_008,),
            )
        with self.assertRaises(module.UsbfsIdentityError):
            module.enumeration_evidence(
                {USB_008: before, other_path: other},
                {
                    USB_008: before,
                    other_path: dataclasses.replace(other, st_ino=56),
                },
                (USB_008,),
            )

    def test_inventory_race_is_fail_closed(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            endpoint = root / "002" / "008"
            endpoint.parent.mkdir()
            endpoint.touch()
            with self.assertRaises(module.UsbfsIdentityError):
                module.capture_inventory(
                    root=root,
                    snapshotter=lambda _path: (_ for _ in ()).throw(
                        FileNotFoundError("raced")
                    ),
                )

    def test_core_opt_in_persists_evidence_and_keeps_generation_stable(self):
        module = self.module
        core = self.core
        before = node(module)
        observations = iter(
            (
                {USB_008: before},
                {
                    USB_008: dataclasses.replace(
                        before, st_atime_ns=101, st_ctime_ns=201
                    )
                },
                {
                    USB_008: dataclasses.replace(
                        before,
                        st_atime_ns=102,
                        st_ctime_ns=202,
                        st_mtime_ns=301,
                    )
                },
            )
        )

        def factory():
            return module.MeasuredUsbfsIdentityObserver(
                inventory_reader=lambda: dict(next(observations)),
            )

        runner = lambda _argv, _timeout: SimpleNamespace(
            returncode=0,
            stdout=USB_008 + "\n",
            stderr=b"",
        )
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with core.transaction_session(run_dir) as lease:
                waited = core.wait_for_single_live_endpoint(
                    Path("odin4"),
                    run_dir,
                    timeout_sec=1,
                    lease=lease,
                    runner=runner,
                    endpoint_observer_factory=factory,
                )
            self.assertFalse(waited.timed_out)
            self.assertTrue(
                waited.ticket.device_identity.startswith(module.IDENTITY_PREFIX)
            )
            receipts = core.list_snapshot_receipts(run_dir)
            evidence = receipts[0]["endpoint_transition_evidence"]
            self.assertEqual(evidence["inventory_paths"], [USB_008])
            self.assertEqual(
                evidence["node_transitions"][0]["metadata_changes"],
                ["st_atime_ns", "st_ctime_ns"],
            )
            payload = Path(receipts[0]["path"]).read_text(encoding="ascii")
            self.assertIn(core.SNAPSHOT_SCHEMA, payload)

    def test_core_rejects_mixed_legacy_and_measured_identity_modes(self):
        core = self.core
        called = []
        with self.assertRaises(core.OdinTransitionError):
            core.enumerate_odin(
                Path("odin4"),
                runner=lambda _argv, _timeout: called.append(True),
                device_identity=lambda _path: "legacy",
                endpoint_observer_factory=core.measured_usbfs_observer,
            )
        self.assertEqual(called, [])
        with self.assertRaises(core.OdinTransitionError):
            core.enumerate_odin(
                Path("odin4"),
                runner=lambda _argv, _timeout: called.append(True),
                endpoint_observer_factory=lambda: object(),
            )
        self.assertEqual(called, [])

    def test_legacy_v1_snapshot_receipt_remains_readable(self):
        core = self.core
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with core.transaction_session(run_dir):
                receipt_dir = core._receipt_directory(run_dir, create=True)
                payload = {
                    "schema": core.SNAPSHOT_SCHEMA_V1,
                    "sequence": 0,
                    "timestamp_utc": "2026-07-20T00:00:00.000000Z",
                    "returncode": 0,
                    "raw_devices": [USB_008],
                    "live_devices": [USB_008],
                    "stale_devices": [],
                    "live_device_identities": [[USB_008, "legacy-node"]],
                    "stdout": USB_008,
                    "stderr": "",
                }
                core._create_sealed_receipt(
                    receipt_dir / "odin-snapshot-000000.json", payload
                )
            receipts = core.list_snapshot_receipts(run_dir)
            self.assertEqual(receipts[0]["live_device_identities"], [[USB_008, "legacy-node"]])
            self.assertNotIn("endpoint_transition_evidence", receipts[0])

    def test_post_receipt_immutable_replacement_is_rejected(self):
        module = self.module
        core = self.core
        before = node(module)
        after = dataclasses.replace(before, st_ctime_ns=201)
        replacement = dataclasses.replace(before, st_ino=102)
        observations = iter(
            (
                {USB_008: before},
                {USB_008: after},
                {USB_008: replacement},
            )
        )

        def factory():
            return module.MeasuredUsbfsIdentityObserver(
                inventory_reader=lambda: dict(next(observations)),
            )

        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with core.transaction_session(run_dir) as lease:
                with self.assertRaises(core.OdinTransitionError):
                    core.wait_for_single_live_endpoint(
                        Path("odin4"),
                        run_dir,
                        timeout_sec=1,
                        lease=lease,
                        runner=lambda _argv, _timeout: SimpleNamespace(
                            returncode=0, stdout=USB_008, stderr=""
                        ),
                        endpoint_observer_factory=factory,
                    )
            receipts = core.list_snapshot_receipts(run_dir)
            self.assertEqual(len(receipts), 1)
            self.assertEqual(
                receipts[0]["endpoint_transition_evidence"]["node_transitions"][0][
                    "metadata_changes"
                ],
                ["st_ctime_ns"],
            )


if __name__ == "__main__":
    unittest.main()
