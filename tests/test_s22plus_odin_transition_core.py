import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/s22plus_odin_transition_core.py"
)


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
            result = self.module.wait_for_no_live_endpoint(
                Path("odin4"),
                Path(temporary),
                timeout_sec=1,
                runner=SequenceRunner(["/dev/bus/usb/002/007"]),
                device_identity=lambda _path: None,
                timestamp=lambda: "2026-07-20T00:00:00.000000Z",
            )
            self.assertTrue(result.absent)
            self.assertFalse(result.timed_out)
            receipts = self.module.list_snapshot_receipts(Path(temporary))
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

        with tempfile.TemporaryDirectory() as temporary:
            result = self.module.wait_for_single_live_endpoint(
                Path("odin4"),
                Path(temporary),
                timeout_sec=2,
                poll_sec=0.1,
                runner=wrapped_runner,
                device_identity=device_identity,
                timestamp=lambda: "2026-07-20T00:00:00.000000Z",
                monotonic=clock.monotonic,
                sleep=clock.sleep,
            )
            self.assertFalse(result.timed_out)
            self.assertEqual(result.ticket.device, "/dev/bus/usb/002/008")
            self.assertEqual(result.ticket.generation, 1)
            self.assertEqual(result.next_sequence, 2)
            index = self.module.read_transaction_index(
                Path(temporary) / "transaction.jsonl"
            )
            self.assertTrue(index["complete"])
            self.assertEqual(len(index["records"]), 2)

    def test_generation_resumes_across_live_absent_live_calls(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            first = module.wait_for_single_live_endpoint(
                Path("odin4"),
                run_dir,
                timeout_sec=0,
                runner=SequenceRunner(["/dev/bus/usb/002/008"]),
                device_identity=lambda _path: "first-node",
            )
            absent = module.wait_for_no_live_endpoint(
                Path("odin4"),
                run_dir,
                timeout_sec=0,
                sequence_start=first.next_sequence,
                runner=SequenceRunner(["/dev/bus/usb/002/008"]),
                device_identity=lambda _path: None,
            )
            second = module.wait_for_single_live_endpoint(
                Path("odin4"),
                run_dir,
                timeout_sec=0,
                sequence_start=absent.next_sequence,
                runner=SequenceRunner(["/dev/bus/usb/002/008"]),
                device_identity=lambda _path: "replacement-node",
            )
            self.assertEqual(first.ticket.generation, 1)
            self.assertEqual(second.ticket.generation, 2)
            self.assertEqual(second.ticket.snapshot_sequence, 2)

    def test_sequence_resume_must_match_contiguous_receipts(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            module.wait_for_no_live_endpoint(
                Path("odin4"),
                run_dir,
                timeout_sec=0,
                runner=SequenceRunner([""]),
                device_identity=lambda _path: None,
            )
            with self.assertRaises(module.OdinTransitionError):
                module.wait_for_single_live_endpoint(
                    Path("odin4"),
                    run_dir,
                    timeout_sec=0,
                    sequence_start=0,
                    runner=SequenceRunner(["/dev/bus/usb/002/008"]),
                    device_identity=lambda _path: "node",
                )

    def test_ambiguous_live_endpoints_are_fatal(self):
        with tempfile.TemporaryDirectory() as temporary, self.assertRaises(
            self.module.OdinTransitionError
        ):
            self.module.wait_for_single_live_endpoint(
                Path("odin4"),
                Path(temporary),
                timeout_sec=0,
                runner=SequenceRunner(
                    ["/dev/bus/usb/002/008 /dev/bus/usb/003/009"]
                ),
                device_identity=lambda path: f"node:{path}",
            )

    def test_revalidation_requires_same_single_live_endpoint(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            wait = module.wait_for_single_live_endpoint(
                Path("odin4"),
                run_dir,
                timeout_sec=0,
                runner=SequenceRunner(["/dev/bus/usb/002/008"]),
                device_identity=lambda _path: "node-008",
            )
            revalidated = module.revalidate_endpoint_ticket(
                Path("odin4"),
                run_dir,
                wait.ticket,
                sequence=wait.next_sequence,
                runner=SequenceRunner(
                    ["/dev/bus/usb/002/007 /dev/bus/usb/002/008"]
                ),
                device_identity=lambda path: "node-008" if path.endswith("/008") else None,
            )
            self.assertEqual(revalidated["device"], "/dev/bus/usb/002/008")
            self.assertEqual(revalidated["generation"], 1)

        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            wait = module.wait_for_single_live_endpoint(
                Path("odin4"),
                run_dir,
                timeout_sec=0,
                runner=SequenceRunner(["/dev/bus/usb/002/008"]),
                device_identity=lambda _path: "node-008",
            )
            with self.assertRaises(module.OdinTransitionError):
                module.revalidate_endpoint_ticket(
                    Path("odin4"),
                    run_dir,
                    wait.ticket,
                    sequence=wait.next_sequence,
                    runner=SequenceRunner(["/dev/bus/usb/002/009"]),
                    device_identity=lambda _path: "node-009",
                )

        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            wait = module.wait_for_single_live_endpoint(
                Path("odin4"),
                run_dir,
                timeout_sec=0,
                runner=SequenceRunner(["/dev/bus/usb/002/008"]),
                device_identity=lambda _path: "original-node",
            )
            with self.assertRaises(module.OdinTransitionError):
                module.revalidate_endpoint_ticket(
                    Path("odin4"),
                    run_dir,
                    wait.ticket,
                    sequence=wait.next_sequence,
                    runner=SequenceRunner(["/dev/bus/usb/002/008"]),
                    device_identity=lambda _path: "replacement-node",
                )

    def test_phase_receipts_are_immutable_and_indexed(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            first = module.create_phase_receipt(
                run_dir, "prepared", {"device": "test"}
            )
            self.assertEqual(first["record"], "phase_receipt")
            with self.assertRaises(module.OdinTransitionError):
                module.create_phase_receipt(
                    run_dir, "prepared", {"device": "changed"}
                )
            index = module.read_transaction_index(run_dir / "transaction.jsonl")
            self.assertEqual(len(index["records"]), 1)

    def test_receipts_recover_when_index_is_missing_or_partial(self):
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
            module.persist_snapshot(run_dir, 0, snapshot)
            (run_dir / "transaction.jsonl").unlink()
            receipts = module.list_snapshot_receipts(run_dir)
            self.assertEqual(len(receipts), 1)
            self.assertEqual(receipts[0]["sequence"], 0)

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
            module.persist_snapshot(run_dir, 0, snapshot)
            with (run_dir / "transaction.jsonl").open("ab") as stream:
                stream.write(b'{"schema":"s22plus_odin_transaction_index_v1"')
            module.create_phase_receipt(run_dir, "prepared", {"ready": True})
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
            with self.assertRaises(module.OdinTransitionError):
                module.create_phase_receipt(
                    run_dir, "candidate_transfer_started", {"attempt": 1}
                )
            module.create_phase_receipt(run_dir, "prepared", {"ready": True})
            module.create_phase_receipt(
                run_dir, "candidate_transfer_started", {"attempt": 1}
            )
            with self.assertRaises(module.OdinTransitionError):
                module.create_phase_receipt(
                    run_dir, "rollback_confirmed", {"confirmed": True}
                )

    def test_receipt_scans_reject_path_payload_mismatch(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            receipt_dir = run_dir / "receipts"
            receipt_dir.mkdir()
            (receipt_dir / "odin-snapshot-000001.json").write_text(
                json.dumps({"schema": module.SNAPSHOT_SCHEMA, "sequence": 2}),
                encoding="utf-8",
            )
            with self.assertRaises(module.OdinTransitionError):
                module.list_snapshot_receipts(run_dir)

        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            receipt_dir = run_dir / "receipts"
            receipt_dir.mkdir()
            (receipt_dir / "phase-prepared.json").write_text(
                json.dumps(
                    {
                        "schema": module.PHASE_SCHEMA,
                        "phase": "candidate_transfer_started",
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(module.OdinTransitionError):
                module.create_phase_receipt(run_dir, "prepared", {"ready": True})

    def test_index_rejects_symlink(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target"
            target.write_text("", encoding="ascii")
            link = root / "transaction.jsonl"
            link.symlink_to(target)
            with self.assertRaises(module.OdinTransitionError):
                module.durable_append_jsonl(
                    link,
                    {
                        "schema": module.INDEX_SCHEMA,
                        "record": "test",
                    },
                )

    def test_index_rejects_resume_without_base(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            (run_dir / "transaction-resume-000001.jsonl").write_text(
                "", encoding="ascii"
            )
            with self.assertRaises(module.OdinTransitionError):
                module.read_transaction_segments(run_dir)


if __name__ == "__main__":
    unittest.main()
