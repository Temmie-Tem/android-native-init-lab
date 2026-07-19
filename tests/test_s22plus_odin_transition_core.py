import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/s22plus_odin_transition_core.py"
)
USB_007 = "/dev/bus/usb/002/007"
USB_008 = "/dev/bus/usb/002/008"
USB_009 = "/dev/bus/usb/002/009"


def fixed_inventory(*entries):
    value = dict(entries)
    return lambda: dict(value)


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("s22plus_odin_transition_core", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeClock:
    def __init__(self):
        self.value = 0.0

    def monotonic(self):
        return self.value

    def sleep(self, seconds):
        self.value += max(seconds, 0.01)


class SequenceRunner:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.index = 0

    def __call__(self, argv, timeout):
        if self.index >= len(self.outputs):
            output = self.outputs[-1]
        else:
            output = self.outputs[self.index]
        self.index += 1
        return SimpleNamespace(returncode=0, stdout=output, stderr=None)


class S22PlusOdinTransitionCoreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_stale_endpoint_is_recorded_but_not_live_or_fatal(self):
        snapshot = self.module.enumerate_odin(
            Path("odin4"),
            runner=lambda _argv, _timeout: SimpleNamespace(
                returncode=0,
                stdout="devices=[/dev/bus/usb/002/007]",
                stderr=None,
            ),
            device_identity=lambda _path: None,
            device_inventory=fixed_inventory(),
            timestamp=lambda: "2026-07-20T00:00:00.000000Z",
        )
        self.assertEqual(snapshot.live_devices, ())
        self.assertEqual(snapshot.stale_devices, ("/dev/bus/usb/002/007",))

    def test_source_has_enumeration_only_and_no_device_mutation_surface(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertEqual(source.count('str(odin), "-l"'), 1)
        for forbidden in (
            '"adb"',
            "'adb'",
            "flash_exact(",
            "--reboot",
            "download",
            "exec-out",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def test_default_identity_rejects_non_device_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "regular"
            path.write_text("not a device", encoding="ascii")
            with self.assertRaises(self.module.OdinTransitionError):
                self.module._default_device_identity(str(path))

    def test_nonzero_enumeration_is_fatal(self):
        with self.assertRaises(self.module.OdinTransitionError):
            self.module.enumerate_odin(
                Path("odin4"),
                runner=lambda _argv, _timeout: SimpleNamespace(
                    returncode=1, stdout="", stderr=None
                ),
            )

    def test_enumeration_timeout_is_normalized(self):
        def timeout(_argv, _seconds):
            raise subprocess.TimeoutExpired("odin4", 10)

        with self.assertRaises(self.module.OdinTransitionError):
            self.module.enumerate_odin(Path("odin4"), runner=timeout)

    def test_disconnect_accepts_stale_only_snapshot(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with self.module.transaction_session(run_dir) as lease:
                result = self.module.wait_for_no_live_endpoint(
                    Path("odin4"),
                    run_dir,
                    timeout_sec=1,
                    lease=lease,
                    runner=SequenceRunner(["/dev/bus/usb/002/007"]),
                    device_identity=lambda _path: None,
                    device_inventory=fixed_inventory(),
                    timestamp=lambda: "2026-07-20T00:00:00.000000Z",
                )
            self.assertTrue(result.absent)
            self.assertFalse(result.timed_out)
            receipts = self.module.list_snapshot_receipts(run_dir)
            self.assertEqual(receipts[0]["stale_devices"], ["/dev/bus/usb/002/007"])

    def test_wait_assigns_generation_after_stale_then_live(self):
        clock = FakeClock()
        outputs = ["/dev/bus/usb/002/007", "/dev/bus/usb/002/008"]
        current = {"call": 0}

        def device_identity(path):
            return "node-008" if current["call"] >= 1 and path.endswith("/008") else None

        runner = SequenceRunner(outputs)

        def wrapped_runner(argv, timeout):
            result = runner(argv, timeout)
            current["call"] = runner.index - 1
            return result

        def device_inventory():
            if runner.index >= 1:
                return {USB_008: "node-008"}
            return {}

        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with self.module.transaction_session(run_dir) as lease:
                result = self.module.wait_for_single_live_endpoint(
                    Path("odin4"),
                    run_dir,
                    timeout_sec=2,
                    lease=lease,
                    poll_sec=0.1,
                    runner=wrapped_runner,
                    device_identity=device_identity,
                    device_inventory=device_inventory,
                    timestamp=lambda: "2026-07-20T00:00:00.000000Z",
                    monotonic=clock.monotonic,
                    sleep=clock.sleep,
                )
            self.assertFalse(result.timed_out)
            self.assertEqual(result.ticket.device, "/dev/bus/usb/002/008")
            self.assertEqual(result.ticket.generation, 1)
            self.assertEqual(result.next_sequence, 2)
            index = self.module.read_transaction_index(
                run_dir / "transaction.jsonl"
            )
            self.assertTrue(index["complete"])
            self.assertEqual(len(index["records"]), 2)

    def test_generation_resumes_across_live_absent_live_calls(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with module.transaction_session(run_dir) as lease:
                first = module.wait_for_single_live_endpoint(
                    Path("odin4"),
                    run_dir,
                    timeout_sec=1,
                    lease=lease,
                    runner=SequenceRunner(["/dev/bus/usb/002/008"]),
                    device_identity=lambda _path: "first-node",
                    device_inventory=fixed_inventory((USB_008, "first-node")),
                )
                absent = module.wait_for_no_live_endpoint(
                    Path("odin4"),
                    run_dir,
                    timeout_sec=1,
                    lease=lease,
                    sequence_start=first.next_sequence,
                    runner=SequenceRunner(["/dev/bus/usb/002/008"]),
                    device_identity=lambda _path: None,
                    device_inventory=fixed_inventory(),
                )
                second = module.wait_for_single_live_endpoint(
                    Path("odin4"),
                    run_dir,
                    timeout_sec=1,
                    lease=lease,
                    sequence_start=absent.next_sequence,
                    runner=SequenceRunner(["/dev/bus/usb/002/008"]),
                    device_identity=lambda _path: "replacement-node",
                    device_inventory=fixed_inventory((USB_008, "replacement-node")),
                )
            self.assertEqual(first.ticket.generation, 1)
            self.assertEqual(second.ticket.generation, 2)
            self.assertEqual(second.ticket.snapshot_sequence, 2)

    def test_sequence_resume_must_match_contiguous_receipts(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with module.transaction_session(run_dir) as lease:
                module.wait_for_no_live_endpoint(
                    Path("odin4"),
                    run_dir,
                    timeout_sec=1,
                    lease=lease,
                    runner=SequenceRunner([""]),
                    device_identity=lambda _path: None,
                    device_inventory=fixed_inventory(),
                )
                with self.assertRaises(module.OdinTransitionError):
                    module.wait_for_single_live_endpoint(
                        Path("odin4"),
                        run_dir,
                        timeout_sec=1,
                        lease=lease,
                        sequence_start=0,
                        runner=SequenceRunner(["/dev/bus/usb/002/008"]),
                        device_identity=lambda _path: "node",
                        device_inventory=fixed_inventory((USB_008, "node")),
                    )

    def test_ambiguous_live_endpoints_are_fatal(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with self.module.transaction_session(run_dir) as lease:
                with self.assertRaises(self.module.OdinTransitionError):
                    self.module.wait_for_single_live_endpoint(
                        Path("odin4"),
                        run_dir,
                        timeout_sec=1,
                        lease=lease,
                        runner=SequenceRunner(
                            ["/dev/bus/usb/002/008 /dev/bus/usb/003/009"]
                        ),
                        device_identity=lambda path: f"node:{path}",
                        device_inventory=fixed_inventory(
                            (USB_008, f"node:{USB_008}"),
                            ("/dev/bus/usb/003/009", "node:/dev/bus/usb/003/009"),
                        ),
                    )

    def test_revalidation_requires_same_single_live_endpoint(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with module.transaction_session(run_dir) as lease:
                wait = module.wait_for_single_live_endpoint(
                    Path("odin4"),
                    run_dir,
                    timeout_sec=1,
                    lease=lease,
                    runner=SequenceRunner(["/dev/bus/usb/002/008"]),
                    device_identity=lambda _path: "node-008",
                    device_inventory=fixed_inventory((USB_008, "node-008")),
                )
                revalidated = module.revalidate_endpoint_ticket(
                    Path("odin4"),
                    run_dir,
                    wait.ticket,
                    sequence=wait.next_sequence,
                    lease=lease,
                    timeout_sec=1,
                    runner=SequenceRunner(
                        ["/dev/bus/usb/002/007 /dev/bus/usb/002/008"]
                    ),
                    device_identity=(
                        lambda path: "node-008" if path.endswith("/008") else None
                    ),
                    device_inventory=fixed_inventory((USB_008, "node-008")),
                )
            self.assertEqual(revalidated["device"], "/dev/bus/usb/002/008")
            self.assertEqual(revalidated["generation"], 1)

        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with module.transaction_session(run_dir) as lease:
                wait = module.wait_for_single_live_endpoint(
                    Path("odin4"),
                    run_dir,
                    timeout_sec=1,
                    lease=lease,
                    runner=SequenceRunner(["/dev/bus/usb/002/008"]),
                    device_identity=lambda _path: "node-008",
                    device_inventory=fixed_inventory((USB_008, "node-008")),
                )
                with self.assertRaises(module.OdinTransitionError):
                    module.revalidate_endpoint_ticket(
                        Path("odin4"),
                        run_dir,
                        wait.ticket,
                        sequence=wait.next_sequence,
                        lease=lease,
                        timeout_sec=1,
                        runner=SequenceRunner(["/dev/bus/usb/002/009"]),
                        device_identity=lambda _path: "node-009",
                        device_inventory=fixed_inventory((USB_009, "node-009")),
                    )

        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with module.transaction_session(run_dir) as lease:
                wait = module.wait_for_single_live_endpoint(
                    Path("odin4"),
                    run_dir,
                    timeout_sec=1,
                    lease=lease,
                    runner=SequenceRunner(["/dev/bus/usb/002/008"]),
                    device_identity=lambda _path: "original-node",
                    device_inventory=fixed_inventory((USB_008, "original-node")),
                )
                with self.assertRaises(module.OdinTransitionError):
                    module.revalidate_endpoint_ticket(
                        Path("odin4"),
                        run_dir,
                        wait.ticket,
                        sequence=wait.next_sequence,
                        lease=lease,
                        timeout_sec=1,
                        runner=SequenceRunner(["/dev/bus/usb/002/008"]),
                        device_identity=lambda _path: "replacement-node",
                        device_inventory=fixed_inventory(
                            (USB_008, "replacement-node")
                        ),
                    )

    def test_phase_receipts_are_exclusive_sealed_and_indexed(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with module.transaction_session(run_dir) as lease:
                first = module.create_phase_receipt(
                    run_dir, "prepared", {"device": "test"}, lease=lease
                )
                self.assertEqual(first["record"], "phase_receipt")
                self.assertEqual(Path(first["receipt"]).stat().st_mode & 0o777, 0o400)
                with self.assertRaises(module.OdinTransitionError):
                    module.create_phase_receipt(
                        run_dir, "prepared", {"device": "changed"}, lease=lease
                    )
            index = module.read_transaction_index(run_dir / "transaction.jsonl")
            self.assertEqual(len(index["records"]), 1)

    def test_sealed_receipt_exclusive_create_hits_publish_boundary(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "receipt.json"
            module._create_sealed_receipt(path, {"value": 1})
            self.assertEqual(path.stat().st_mode & 0o777, 0o400)
            with self.assertRaises(module.OdinTransitionError):
                module._create_sealed_receipt(path, {"value": 2})

    def test_failed_receipt_publish_leaves_no_final_or_temporary(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "receipt.json"
            with mock.patch.object(module.os, "link", side_effect=OSError("blocked")):
                with self.assertRaises(module.OdinTransitionError):
                    module._create_sealed_receipt(path, {"value": 1})
            self.assertFalse(path.exists())
            self.assertEqual(list(path.parent.glob(".*.sealed-tmp-*")), [])

    def test_visible_orphan_is_fsynced_before_reconciliation_index(self):
        module = self.module
        snapshot = module.OdinSnapshot(
            timestamp_utc="2026-07-20T00:00:00.000000Z",
            returncode=0,
            raw_devices=(),
            live_devices=(),
            stale_devices=(),
            live_device_identities=(),
            stdout="",
            stderr="",
        )
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            receipt = run_dir / "receipts" / "odin-snapshot-000000.json"
            real_fsync = module._fsync_directory

            def crash_before_receipt_dir_fsync(path):
                if path == receipt.parent:
                    raise OSError("simulated crash boundary")
                return real_fsync(path)

            with mock.patch.object(
                module,
                "_fsync_directory",
                side_effect=crash_before_receipt_dir_fsync,
            ):
                with self.assertRaises(OSError):
                    module._create_sealed_receipt(
                        receipt, module._receipt_payload(snapshot, 0)
                    )
            self.assertTrue(receipt.is_file())
            self.assertEqual(receipt.stat().st_mode & 0o777, 0o400)

            events = []
            real_append = module._append_transaction_record_unlocked

            def record_fsync(path):
                events.append(("fsync", path))
                return real_fsync(path)

            def record_append(path, value):
                events.append(("append", path))
                return real_append(path, value)

            with module.transaction_session(run_dir) as lease:
                with mock.patch.object(
                    module, "_fsync_directory", side_effect=record_fsync
                ), mock.patch.object(
                    module,
                    "_append_transaction_record_unlocked",
                    side_effect=record_append,
                ):
                    module.wait_for_no_live_endpoint(
                        Path("odin4"),
                        run_dir,
                        timeout_sec=1,
                        lease=lease,
                        sequence_start=1,
                        runner=SequenceRunner([""]),
                        device_identity=lambda _path: None,
                        device_inventory=fixed_inventory(),
                    )
            append_index = next(
                index for index, event in enumerate(events) if event[0] == "append"
            )
            self.assertIn(("fsync", receipt.parent), events[:append_index])
            self.assertIn(("fsync", run_dir), events[:append_index])

    def test_unindexed_receipt_is_reconciled_before_next_snapshot(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            snapshot = module.OdinSnapshot(
                timestamp_utc="2026-07-20T00:00:00.000000Z",
                returncode=0,
                raw_devices=("/dev/bus/usb/002/008",),
                live_devices=("/dev/bus/usb/002/008",),
                stale_devices=(),
                live_device_identities=(("/dev/bus/usb/002/008", "node-008"),),
                stdout="/dev/bus/usb/002/008",
                stderr="",
            )
            with module.transaction_session(run_dir) as lease:
                module.persist_snapshot(run_dir, 0, snapshot, lease=lease)
            (run_dir / "transaction.jsonl").unlink()
            receipts = module.list_snapshot_receipts(run_dir)
            self.assertEqual(len(receipts), 1)
            self.assertEqual(receipts[0]["sequence"], 0)
            with module.transaction_session(run_dir) as lease:
                result = module.wait_for_no_live_endpoint(
                    Path("odin4"),
                    run_dir,
                    timeout_sec=1,
                    lease=lease,
                    sequence_start=1,
                    runner=SequenceRunner([""]),
                    device_identity=lambda _path: None,
                    device_inventory=fixed_inventory(),
                )
            self.assertTrue(result.absent)
            recovered = module.read_transaction_segments(run_dir)["records"]
            self.assertEqual(len(recovered), 2)
            self.assertTrue(recovered[0]["recovered_after_receipt_publish"])
            self.assertEqual(recovered[0]["sequence"], 0)
            self.assertEqual(recovered[1]["sequence"], 1)

    def test_partial_index_tail_is_reported(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            index_path = run_dir / "transaction.jsonl"
            index_path.write_bytes(b'{"schema":"s22plus_odin_transaction_index_v1"')
            parsed = module.read_transaction_index(index_path)
            self.assertFalse(parsed["complete"])
            self.assertGreater(parsed["partial_tail_bytes"], 0)

    def test_partial_index_resumes_in_new_append_only_segment(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            snapshot = module.OdinSnapshot(
                timestamp_utc="2026-07-20T00:00:00.000000Z",
                returncode=0,
                raw_devices=(),
                live_devices=(),
                stale_devices=(),
                live_device_identities=(),
                stdout="",
                stderr="",
            )
            with module.transaction_session(run_dir) as lease:
                module.persist_snapshot(run_dir, 0, snapshot, lease=lease)
                with (run_dir / "transaction.jsonl").open("ab") as stream:
                    stream.write(b'{"schema":"s22plus_odin_transaction_index_v1"')
                module.create_phase_receipt(
                    run_dir, "prepared", {"ready": True}, lease=lease
                )
            resume = run_dir / "transaction-resume-000001.jsonl"
            self.assertTrue(resume.is_file())
            combined = module.read_transaction_segments(run_dir)
            self.assertEqual(len(combined["segments"]), 2)
            self.assertFalse(combined["segments"][0]["complete"])
            self.assertTrue(combined["segments"][1]["complete"])
            self.assertEqual(len(combined["records"]), 2)

    def test_phase_receipts_require_forward_only_prefix(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with module.transaction_session(run_dir) as lease:
                with self.assertRaises(module.OdinTransitionError):
                    module.create_phase_receipt(
                        run_dir,
                        "candidate_transfer_started",
                        {"attempt": 1},
                        lease=lease,
                    )
                module.create_phase_receipt(
                    run_dir, "prepared", {"ready": True}, lease=lease
                )
                module.create_phase_receipt(
                    run_dir,
                    "candidate_transfer_started",
                    {"attempt": 1},
                    lease=lease,
                )
                with self.assertRaises(module.OdinTransitionError):
                    module.create_phase_receipt(
                        run_dir,
                        "rollback_confirmed",
                        {"confirmed": True},
                        lease=lease,
                    )

    def test_receipt_scans_reject_path_payload_mismatch(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            receipt_dir = run_dir / "receipts"
            receipt_dir.mkdir()
            snapshot_path = receipt_dir / "odin-snapshot-000001.json"
            snapshot_path.write_text(
                json.dumps({"schema": module.SNAPSHOT_SCHEMA, "sequence": 2}),
                encoding="utf-8",
            )
            snapshot_path.chmod(0o400)
            with self.assertRaises(module.OdinTransitionError):
                module.list_snapshot_receipts(run_dir)

        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            receipt_dir = run_dir / "receipts"
            receipt_dir.mkdir()
            phase_path = receipt_dir / "phase-prepared.json"
            phase_path.write_text(
                json.dumps(
                    {
                        "schema": module.PHASE_SCHEMA,
                        "phase": "candidate_transfer_started",
                    }
                ),
                encoding="utf-8",
            )
            phase_path.chmod(0o400)
            with module.transaction_session(run_dir) as lease:
                with self.assertRaises(module.OdinTransitionError):
                    module.create_phase_receipt(
                        run_dir, "prepared", {"ready": True}, lease=lease
                    )

    def test_index_rejects_symlink(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target"
            target.write_text("", encoding="ascii")
            link = root / "transaction.jsonl"
            link.symlink_to(target)
            snapshot = module.OdinSnapshot(
                timestamp_utc="2026-07-20T00:00:00.000000Z",
                returncode=0,
                raw_devices=(),
                live_devices=(),
                stale_devices=(),
                live_device_identities=(),
                stdout="",
                stderr="",
            )
            with module.transaction_session(root) as lease:
                with self.assertRaises(module.OdinTransitionError):
                    module.persist_snapshot(root, 0, snapshot, lease=lease)

    def test_index_rejects_resume_without_base(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            (run_dir / "transaction-resume-000001.jsonl").write_text(
                "", encoding="ascii"
            )
            with self.assertRaises(module.OdinTransitionError):
                module.read_transaction_segments(run_dir)

    def test_same_path_replacement_gets_new_generation_without_observed_absence(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with module.transaction_session(run_dir) as lease:
                first = module.wait_for_single_live_endpoint(
                    Path("odin4"),
                    run_dir,
                    timeout_sec=1,
                    lease=lease,
                    runner=SequenceRunner(["/dev/bus/usb/002/008"]),
                    device_identity=lambda _path: "first-node",
                    device_inventory=fixed_inventory((USB_008, "first-node")),
                )
                second = module.wait_for_single_live_endpoint(
                    Path("odin4"),
                    run_dir,
                    timeout_sec=1,
                    lease=lease,
                    sequence_start=first.next_sequence,
                    runner=SequenceRunner(["/dev/bus/usb/002/008"]),
                    device_identity=lambda _path: "replacement-node",
                    device_inventory=fixed_inventory((USB_008, "replacement-node")),
                )
            self.assertEqual(first.ticket.generation, 1)
            self.assertEqual(second.ticket.generation, 2)

    def test_identity_change_during_snapshot_recording_is_rejected(self):
        module = self.module
        identities = iter(("first-node", "replacement-node"))
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with module.transaction_session(run_dir) as lease:
                with self.assertRaises(module.OdinTransitionError):
                    module.wait_for_single_live_endpoint(
                        Path("odin4"),
                        run_dir,
                        timeout_sec=1,
                        lease=lease,
                        runner=SequenceRunner(["/dev/bus/usb/002/008"]),
                        device_identity=lambda _path: next(identities),
                        device_inventory=fixed_inventory((USB_008, "first-node")),
                    )
            receipts = module.list_snapshot_receipts(run_dir)
            self.assertEqual(receipts[0]["live_device_identities"][0][1], "first-node")

    def test_stale_ticket_is_rejected_after_absent_then_same_node(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with module.transaction_session(run_dir) as lease:
                first = module.wait_for_single_live_endpoint(
                    Path("odin4"),
                    run_dir,
                    timeout_sec=1,
                    lease=lease,
                    runner=SequenceRunner(["/dev/bus/usb/002/008"]),
                    device_identity=lambda _path: "same-node",
                    device_inventory=fixed_inventory((USB_008, "same-node")),
                )
                absent = module.wait_for_no_live_endpoint(
                    Path("odin4"),
                    run_dir,
                    timeout_sec=1,
                    lease=lease,
                    sequence_start=first.next_sequence,
                    runner=SequenceRunner(["/dev/bus/usb/002/008"]),
                    device_identity=lambda _path: None,
                    device_inventory=fixed_inventory(),
                )
                with self.assertRaises(module.OdinTransitionError):
                    module.revalidate_endpoint_ticket(
                        Path("odin4"),
                        run_dir,
                        first.ticket,
                        sequence=absent.next_sequence,
                        lease=lease,
                        timeout_sec=1,
                        runner=SequenceRunner(["/dev/bus/usb/002/008"]),
                        device_identity=lambda _path: "same-node",
                        device_inventory=fixed_inventory((USB_008, "same-node")),
                    )

    def test_ticket_receipt_hash_is_load_bearing(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with module.transaction_session(run_dir) as lease:
                wait = module.wait_for_single_live_endpoint(
                    Path("odin4"),
                    run_dir,
                    timeout_sec=1,
                    lease=lease,
                    runner=SequenceRunner(["/dev/bus/usb/002/008"]),
                    device_identity=lambda _path: "node",
                    device_inventory=fixed_inventory((USB_008, "node")),
                )
                forged = module.EndpointTicket(
                    device=wait.ticket.device,
                    device_identity=wait.ticket.device_identity,
                    generation=wait.ticket.generation,
                    snapshot_sequence=wait.ticket.snapshot_sequence,
                    snapshot_receipt=wait.ticket.snapshot_receipt,
                    snapshot_receipt_sha256="0" * 64,
                )
                with self.assertRaises(module.OdinTransitionError):
                    module.revalidate_endpoint_ticket(
                        Path("odin4"),
                        run_dir,
                        forged,
                        sequence=wait.next_sequence,
                        lease=lease,
                        timeout_sec=1,
                        runner=SequenceRunner(["/dev/bus/usb/002/008"]),
                        device_identity=lambda _path: "node",
                        device_inventory=fixed_inventory((USB_008, "node")),
                    )

    def test_index_detects_resealed_receipt_mutation(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with module.transaction_session(run_dir) as lease:
                wait = module.wait_for_single_live_endpoint(
                    Path("odin4"),
                    run_dir,
                    timeout_sec=1,
                    lease=lease,
                    runner=SequenceRunner(["/dev/bus/usb/002/008"]),
                    device_identity=lambda _path: "node",
                    device_inventory=fixed_inventory((USB_008, "node")),
                )
                receipt = Path(wait.ticket.snapshot_receipt)
                value = json.loads(receipt.read_text(encoding="utf-8"))
                value["stdout"] = "mutated"
                receipt.chmod(0o600)
                receipt.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
                receipt.chmod(0o400)
                with self.assertRaises(module.OdinTransitionError):
                    module.wait_for_no_live_endpoint(
                        Path("odin4"),
                        run_dir,
                        timeout_sec=1,
                        lease=lease,
                        sequence_start=wait.next_sequence,
                        runner=SequenceRunner([""]),
                        device_identity=lambda _path: None,
                        device_inventory=fixed_inventory(),
                    )

    def test_index_detects_deleted_phase_receipt(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with module.transaction_session(run_dir) as lease:
                first = module.create_phase_receipt(
                    run_dir, "prepared", {"ready": True}, lease=lease
                )
                Path(first["receipt"]).unlink()
                with self.assertRaises(module.OdinTransitionError):
                    module.create_phase_receipt(
                        run_dir,
                        "candidate_transfer_started",
                        {"attempt": 1},
                        lease=lease,
                    )

    def test_concurrent_transaction_writer_is_rejected(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            snapshot = module.OdinSnapshot(
                timestamp_utc="2026-07-20T00:00:00.000000Z",
                returncode=0,
                raw_devices=(),
                live_devices=(),
                stale_devices=(),
                live_device_identities=(),
                stdout="",
                stderr="",
            )
            with module.transaction_session(run_dir) as lease:
                with self.assertRaises(module.OdinTransitionError):
                    with module.transaction_session(run_dir):
                        pass
                module.persist_snapshot(run_dir, 0, snapshot, lease=lease)

    def test_expired_transaction_lease_is_rejected(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            snapshot = module.OdinSnapshot(
                timestamp_utc="2026-07-20T00:00:00.000000Z",
                returncode=0,
                raw_devices=(),
                live_devices=(),
                stale_devices=(),
                live_device_identities=(),
                stdout="",
                stderr="",
            )
            with module.transaction_session(run_dir) as lease:
                pass
            with self.assertRaises(module.OdinTransitionError):
                module.persist_snapshot(run_dir, 0, snapshot, lease=lease)

    def test_constructed_transaction_lease_is_not_registered(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            metadata = run_dir.stat()
            forged = module._TransactionLease(
                run_dir=run_dir,
                run_identity=(metadata.st_dev, metadata.st_ino),
                owner_pid=os.getpid(),
                owner_thread=module.threading.get_ident(),
            )
            snapshot = module.OdinSnapshot(
                timestamp_utc="2026-07-20T00:00:00.000000Z",
                returncode=0,
                raw_devices=(),
                live_devices=(),
                stale_devices=(),
                live_device_identities=(),
                stdout="",
                stderr="",
            )
            with self.assertRaises(module.OdinTransitionError):
                module.persist_snapshot(run_dir, 0, snapshot, lease=forged)

    def test_invalid_snapshot_is_rejected_before_receipt_creation(self):
        module = self.module
        snapshot = module.OdinSnapshot(
            timestamp_utc="2026-07-20T00:00:00.000000Z",
            returncode=0,
            raw_devices=("/dev/bus/usb/002/009", "/dev/bus/usb/002/008"),
            live_devices=("/dev/bus/usb/002/008",),
            stale_devices=("/dev/bus/usb/002/009",),
            live_device_identities=(("/dev/bus/usb/002/008", "node"),),
            stdout="",
            stderr="",
        )
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with module.transaction_session(run_dir) as lease:
                with self.assertRaises(module.OdinTransitionError):
                    module.persist_snapshot(run_dir, 0, snapshot, lease=lease)
            self.assertFalse(
                (run_dir / "receipts" / "odin-snapshot-000000.json").exists()
            )

    def test_malformed_path_superstring_is_not_an_endpoint(self):
        for stdout in (
            "device=/dev/bus/usb/002/008.stale",
            "device=/dev/bus/usb/002/008/child",
        ):
            with self.subTest(stdout=stdout):
                snapshot = self.module.enumerate_odin(
                    Path("odin4"),
                    runner=lambda _argv, _timeout, value=stdout: SimpleNamespace(
                        returncode=0,
                        stdout=value,
                        stderr=None,
                    ),
                    device_identity=lambda _path: "must-not-be-called",
                    device_inventory=fixed_inventory(),
                )
                self.assertEqual(snapshot.raw_devices, ())
                self.assertEqual(snapshot.live_devices, ())

    def test_endpoint_token_cannot_be_synthesized_across_streams(self):
        snapshot = self.module.enumerate_odin(
            Path("odin4"),
            runner=lambda _argv, _timeout: SimpleNamespace(
                returncode=0,
                stdout="/dev/bus/usb/002/",
                stderr="008",
            ),
            device_identity=lambda _path: "must-not-be-called",
            device_inventory=fixed_inventory(),
        )
        self.assertEqual(snapshot.raw_devices, ())

    def test_phase_receipt_size_is_bounded_before_creation(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with module.transaction_session(run_dir) as lease:
                with self.assertRaises(module.OdinTransitionError):
                    module.create_phase_receipt(
                        run_dir,
                        "prepared",
                        {"oversized": "x" * module.MAX_RECEIPT_BYTES},
                        lease=lease,
                    )
            self.assertFalse((run_dir / "receipts" / "phase-prepared.json").exists())

    def test_late_enumeration_cannot_return_a_ticket(self):
        module = self.module
        clock = FakeClock()

        def late_runner(_argv, timeout):
            clock.value += timeout + 0.1
            return SimpleNamespace(
                returncode=0,
                stdout="/dev/bus/usb/002/008",
                stderr=None,
            )

        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with module.transaction_session(run_dir) as lease:
                result = module.wait_for_single_live_endpoint(
                    Path("odin4"),
                    run_dir,
                    timeout_sec=1,
                    lease=lease,
                    runner=late_runner,
                    device_identity=lambda _path: "node",
                    device_inventory=fixed_inventory((USB_008, "node")),
                    monotonic=clock.monotonic,
                    sleep=clock.sleep,
                )
            self.assertTrue(result.timed_out)
            self.assertIsNone(result.ticket)

    def test_exact_deadline_enumeration_cannot_return_a_ticket(self):
        module = self.module
        clock = FakeClock()

        def deadline_runner(_argv, timeout):
            clock.value += timeout
            return SimpleNamespace(
                returncode=0,
                stdout="/dev/bus/usb/002/008",
                stderr=None,
            )

        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with module.transaction_session(run_dir) as lease:
                result = module.wait_for_single_live_endpoint(
                    Path("odin4"),
                    run_dir,
                    timeout_sec=1,
                    lease=lease,
                    runner=deadline_runner,
                    device_identity=lambda _path: "node",
                    device_inventory=fixed_inventory((USB_008, "node")),
                    monotonic=clock.monotonic,
                    sleep=clock.sleep,
                )
            self.assertTrue(result.timed_out)
            self.assertIsNone(result.ticket)

    def test_exact_deadline_revalidation_is_rejected(self):
        module = self.module
        clock = FakeClock()
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with module.transaction_session(run_dir) as lease:
                wait = module.wait_for_single_live_endpoint(
                    Path("odin4"),
                    run_dir,
                    timeout_sec=1,
                    lease=lease,
                    runner=SequenceRunner(["/dev/bus/usb/002/008"]),
                    device_identity=lambda _path: "node",
                    device_inventory=fixed_inventory((USB_008, "node")),
                    monotonic=clock.monotonic,
                    sleep=clock.sleep,
                )

                def deadline_runner(_argv, timeout):
                    clock.value += timeout
                    return SimpleNamespace(
                        returncode=0,
                        stdout="/dev/bus/usb/002/008",
                        stderr=None,
                    )

                with self.assertRaises(module.OdinTransitionError):
                    module.revalidate_endpoint_ticket(
                        Path("odin4"),
                        run_dir,
                        wait.ticket,
                        sequence=wait.next_sequence,
                        lease=lease,
                        timeout_sec=1,
                        runner=deadline_runner,
                        device_identity=lambda _path: "node",
                        device_inventory=fixed_inventory((USB_008, "node")),
                        monotonic=clock.monotonic,
                    )

    def test_revalidation_uses_only_remaining_deadline_budget(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with module.transaction_session(run_dir) as lease:
                wait = module.wait_for_single_live_endpoint(
                    Path("odin4"),
                    run_dir,
                    timeout_sec=1,
                    lease=lease,
                    runner=SequenceRunner(["/dev/bus/usb/002/008"]),
                    device_identity=lambda _path: "node",
                    device_inventory=fixed_inventory((USB_008, "node")),
                )
                clock_values = iter((0.0, 0.75, 0.80))
                observed_timeout = []

                def runner(_argv, timeout):
                    observed_timeout.append(timeout)
                    return SimpleNamespace(
                        returncode=0,
                        stdout="/dev/bus/usb/002/008",
                        stderr=None,
                    )

                module.revalidate_endpoint_ticket(
                    Path("odin4"),
                    run_dir,
                    wait.ticket,
                    sequence=wait.next_sequence,
                    lease=lease,
                    timeout_sec=1,
                    runner=runner,
                    device_identity=lambda _path: "node",
                    device_inventory=fixed_inventory((USB_008, "node")),
                    monotonic=lambda: next(clock_values),
                )
            self.assertEqual(len(observed_timeout), 1)
            self.assertAlmostEqual(observed_timeout[0], 0.25)

    def test_revalidation_stops_if_resume_consumes_deadline(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with module.transaction_session(run_dir) as lease:
                wait = module.wait_for_single_live_endpoint(
                    Path("odin4"),
                    run_dir,
                    timeout_sec=1,
                    lease=lease,
                    runner=SequenceRunner(["/dev/bus/usb/002/008"]),
                    device_identity=lambda _path: "node",
                    device_inventory=fixed_inventory((USB_008, "node")),
                )
                clock_values = iter((0.0, 1.0))
                runner_called = []
                with self.assertRaises(module.OdinTransitionError):
                    module.revalidate_endpoint_ticket(
                        Path("odin4"),
                        run_dir,
                        wait.ticket,
                        sequence=wait.next_sequence,
                        lease=lease,
                        timeout_sec=1,
                        runner=lambda _argv, _timeout: runner_called.append(True),
                        device_identity=lambda _path: "node",
                        device_inventory=fixed_inventory((USB_008, "node")),
                        monotonic=lambda: next(clock_values),
                    )
            self.assertEqual(runner_called, [])

    def test_nonfinite_time_bounds_are_rejected(self):
        module = self.module
        for invalid in (float("nan"), float("inf")):
            with self.subTest(kind="enumeration", invalid=invalid):
                with self.assertRaises(module.OdinTransitionError):
                    module.enumerate_odin(Path("odin4"), timeout_sec=invalid)
            with tempfile.TemporaryDirectory() as temporary:
                run_dir = Path(temporary)
                with module.transaction_session(run_dir) as lease:
                    with self.subTest(kind="wait", invalid=invalid):
                        with self.assertRaises(module.OdinTransitionError):
                            module.wait_for_single_live_endpoint(
                                Path("odin4"),
                                run_dir,
                                timeout_sec=invalid,
                                lease=lease,
                            )
                    with self.subTest(kind="poll", invalid=invalid):
                        with self.assertRaises(module.OdinTransitionError):
                            module.wait_for_no_live_endpoint(
                                Path("odin4"),
                                run_dir,
                                timeout_sec=1,
                                poll_sec=invalid,
                                lease=lease,
                            )
                    with self.subTest(kind="revalidation", invalid=invalid):
                        with self.assertRaises(module.OdinTransitionError):
                            module.revalidate_endpoint_ticket(
                                Path("odin4"),
                                run_dir,
                                None,
                                sequence=0,
                                lease=lease,
                                timeout_sec=invalid,
                            )

    def test_nonfinite_monotonic_clock_is_rejected(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with module.transaction_session(run_dir) as lease:
                with self.assertRaises(module.OdinTransitionError):
                    module.wait_for_no_live_endpoint(
                        Path("odin4"),
                        run_dir,
                        timeout_sec=1,
                        lease=lease,
                        monotonic=lambda: float("nan"),
                    )

    def test_zero_wait_timeout_is_rejected_before_enumeration(self):
        called = {"runner": False}

        def runner(_argv, _timeout):
            called["runner"] = True
            return SimpleNamespace(returncode=0, stdout="", stderr=None)

        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with self.module.transaction_session(run_dir) as lease:
                with self.assertRaises(self.module.OdinTransitionError):
                    self.module.wait_for_single_live_endpoint(
                        Path("odin4"),
                        run_dir,
                        timeout_sec=0,
                        lease=lease,
                        runner=runner,
                    )
        self.assertFalse(called["runner"])

    def test_default_runner_kills_oversized_output(self):
        with self.assertRaises(subprocess.SubprocessError):
            self.module._default_runner(
                [
                    sys.executable,
                    "-c",
                    "import os; os.write(1, b'x' * 70000)",
                ],
                2,
            )

    def test_default_runner_reaps_child_when_selector_setup_fails(self):
        process = mock.Mock()
        process.poll.return_value = None
        process.stdout = mock.Mock()
        process.stderr = mock.Mock()
        with mock.patch.object(
            self.module.subprocess, "Popen", return_value=process
        ), mock.patch.object(
            self.module.selectors,
            "DefaultSelector",
            side_effect=RuntimeError("selector unavailable"),
        ):
            with self.assertRaisesRegex(RuntimeError, "selector unavailable"):
                self.module._default_runner(["odin4", "-l"], 2)
        process.kill.assert_called_once_with()
        process.wait.assert_called_once_with()
        process.stdout.close.assert_called_once_with()
        process.stderr.close.assert_called_once_with()

    def test_index_segment_count_is_bounded(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            (run_dir / "transaction.jsonl").write_text("", encoding="ascii")
            for number in range(1, module.MAX_INDEX_SEGMENTS + 1):
                (run_dir / f"transaction-resume-{number:06d}.jsonl").write_text(
                    "", encoding="ascii"
                )
            with self.assertRaises(module.OdinTransitionError):
                module.read_transaction_segments(run_dir)

    def test_index_aggregate_size_is_bounded(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            (run_dir / "transaction.jsonl").write_text("{}\n", encoding="ascii")
            with mock.patch.object(module, "MAX_INDEX_TOTAL_BYTES", 2):
                with self.assertRaises(module.OdinTransitionError):
                    module.read_transaction_segments(run_dir)

    def test_snapshot_receipt_count_is_bounded(self):
        module = self.module
        snapshot = module.OdinSnapshot(
            timestamp_utc="2026-07-20T00:00:00.000000Z",
            returncode=0,
            raw_devices=(),
            live_devices=(),
            stale_devices=(),
            live_device_identities=(),
            stdout="",
            stderr="",
        )
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            for sequence in range(3):
                module._create_sealed_receipt(
                    run_dir / "receipts" / f"odin-snapshot-{sequence:06d}.json",
                    module._receipt_payload(snapshot, sequence),
                )
            with mock.patch.object(module, "MAX_SNAPSHOT_RECEIPTS", 2):
                with self.assertRaises(module.OdinTransitionError):
                    module.list_snapshot_receipts(run_dir)

    def test_snapshot_capacity_rejects_before_extra_receipt(self):
        module = self.module
        snapshot = module.OdinSnapshot(
            timestamp_utc="2026-07-20T00:00:00.000000Z",
            returncode=0,
            raw_devices=(),
            live_devices=(),
            stale_devices=(),
            live_device_identities=(),
            stdout="",
            stderr="",
        )
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with mock.patch.object(module, "MAX_SNAPSHOT_RECEIPTS", 1):
                with module.transaction_session(run_dir) as lease:
                    module.persist_snapshot(run_dir, 0, snapshot, lease=lease)
                    with self.assertRaises(module.OdinTransitionError):
                        module.persist_snapshot(run_dir, 1, snapshot, lease=lease)
            self.assertFalse(
                (run_dir / "receipts" / "odin-snapshot-000001.json").exists()
            )

    def test_index_segment_capacity_rejects_before_receipt(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            (run_dir / "transaction.jsonl").write_bytes(b"partial")
            with mock.patch.object(module, "MAX_INDEX_SEGMENTS", 1):
                with module.transaction_session(run_dir) as lease:
                    with self.assertRaises(module.OdinTransitionError):
                        module.create_phase_receipt(
                            run_dir, "prepared", {"ready": True}, lease=lease
                        )
            self.assertFalse((run_dir / "receipts" / "phase-prepared.json").exists())

    def test_index_aggregate_capacity_rejects_before_receipt(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with mock.patch.object(
                module, "MAX_INDEX_TOTAL_BYTES", 1
            ):
                with module.transaction_session(run_dir) as lease:
                    with self.assertRaises(module.OdinTransitionError):
                        module.create_phase_receipt(
                            run_dir, "prepared", {"ready": True}, lease=lease
                        )
            self.assertFalse((run_dir / "receipts" / "phase-prepared.json").exists())

    def test_new_index_segment_capacity_rejects_before_receipt(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with mock.patch.object(
                module, "MAX_INDEX_BYTES", 1
            ):
                with module.transaction_session(run_dir) as lease:
                    with self.assertRaises(module.OdinTransitionError):
                        module.create_phase_receipt(
                            run_dir, "prepared", {"ready": True}, lease=lease
                        )
            self.assertFalse((run_dir / "receipts" / "phase-prepared.json").exists())

    def test_symlink_run_directory_is_rejected(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target"
            target.mkdir()
            link = root / "run"
            link.symlink_to(target, target_is_directory=True)
            with self.assertRaises(module.OdinTransitionError):
                with module.transaction_session(link):
                    pass

    def test_created_transaction_directories_fsync_each_parent(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parent = root / "parent"
            run_dir = parent / "run"
            fsynced = []
            real_fsync = module._fsync_directory

            def record_fsync(path):
                fsynced.append(path)
                return real_fsync(path)

            with mock.patch.object(
                module, "_fsync_directory", side_effect=record_fsync
            ):
                with module.transaction_session(run_dir):
                    pass
            self.assertIn(root, fsynced)
            self.assertIn(parent, fsynced)

    def test_endpoint_replaced_during_enumeration_is_rejected(self):
        with self.assertRaisesRegex(
            self.module.OdinTransitionError, "changed during enumeration"
        ):
            self.module.enumerate_odin(
                Path("odin4"),
                runner=SequenceRunner([USB_008]),
                device_identity=lambda _path: "replacement-node",
                device_inventory=fixed_inventory((USB_008, "original-node")),
            )

    def test_new_endpoint_during_enumeration_is_rejected(self):
        with self.assertRaisesRegex(
            self.module.OdinTransitionError, "changed during enumeration"
        ):
            self.module.enumerate_odin(
                Path("odin4"),
                runner=SequenceRunner([USB_008]),
                device_identity=lambda _path: "new-node",
                device_inventory=fixed_inventory(),
            )

    def test_actual_oversized_index_record_is_rejected_before_receipt(self):
        module = self.module
        paths = tuple(f"/dev/bus/usb/002/{number:03d}" for number in range(64))
        snapshot = module.OdinSnapshot(
            timestamp_utc="2026-07-20T00:00:00.000000Z",
            returncode=0,
            raw_devices=paths,
            live_devices=(),
            stale_devices=paths,
            live_device_identities=(),
            stdout="",
            stderr="",
        )
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with mock.patch.object(module, "MAX_INDEX_RECORD_BYTES", 256):
                with module.transaction_session(run_dir) as lease:
                    with self.assertRaises(module.OdinTransitionError):
                        module.persist_snapshot(run_dir, 0, snapshot, lease=lease)
            self.assertFalse(
                (run_dir / "receipts" / "odin-snapshot-000000.json").exists()
            )

    def test_inherited_lease_is_rejected_in_forked_child(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with module.transaction_session(run_dir) as lease:
                read_fd, write_fd = os.pipe()
                child = os.fork()
                if child == 0:
                    os.close(read_fd)
                    try:
                        module.create_phase_receipt(
                            run_dir, "prepared", {"child": True}, lease=lease
                        )
                    except module.OdinTransitionError:
                        os.write(write_fd, b"rejected")
                    else:
                        os.write(write_fd, b"accepted")
                    finally:
                        os.close(write_fd)
                    os._exit(0)
                os.close(write_fd)
                try:
                    outcome = os.read(read_fd, 32)
                finally:
                    os.close(read_fd)
                    waited, status = os.waitpid(child, 0)
                self.assertEqual(waited, child)
                self.assertEqual(status, 0)
                self.assertEqual(outcome, b"rejected")
            self.assertFalse((run_dir / "receipts" / "phase-prepared.json").exists())

    def test_finite_deadline_overflow_is_rejected_before_enumeration(self):
        called = []
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with self.module.transaction_session(run_dir) as lease:
                with self.assertRaisesRegex(
                    self.module.OdinTransitionError, "deadline overflowed"
                ):
                    self.module.wait_for_no_live_endpoint(
                        Path("odin4"),
                        run_dir,
                        timeout_sec=1e308,
                        lease=lease,
                        runner=lambda _argv, _timeout: called.append(True),
                        monotonic=lambda: 1e308,
                    )
        self.assertEqual(called, [])

    def test_losing_directory_create_race_fsyncs_parent(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            run_dir = parent / "run"
            real_mkdir = module.os.mkdir
            real_fsync = module._fsync_directory
            fsynced = []

            def racing_mkdir(path, mode):
                real_mkdir(path, mode)
                raise FileExistsError(path)

            def record_fsync(path):
                fsynced.append(path)
                return real_fsync(path)

            with mock.patch.object(
                module.os, "mkdir", side_effect=racing_mkdir
            ), mock.patch.object(
                module, "_fsync_directory", side_effect=record_fsync
            ):
                module._require_direct_directory(run_dir, create=True)
            self.assertIn(parent, fsynced)

    def test_nonfinite_phase_payload_is_rejected_before_receipt(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with module.transaction_session(run_dir) as lease:
                with self.assertRaises(module.OdinTransitionError):
                    module.create_phase_receipt(
                        run_dir, "prepared", {"invalid": float("nan")}, lease=lease
                    )
            self.assertFalse((run_dir / "receipts" / "phase-prepared.json").exists())


if __name__ == "__main__":
    unittest.main()
