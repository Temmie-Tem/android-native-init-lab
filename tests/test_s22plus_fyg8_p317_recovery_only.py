import importlib.util
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p317_recovery_only.py"
)
CLOSE_AUDIT_SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p317_recovery_close_audit.py"
)
USB_A = "/dev/bus/usb/002/007"
USB_B = "/dev/bus/usb/002/008"
USB_C = "/dev/bus/usb/002/009"


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location(
        "s22plus_fyg8_p317_recovery_only", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_close_audit_module():
    script_dir = str(CLOSE_AUDIT_SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location(
        "s22plus_fyg8_p317_recovery_close_audit", CLOSE_AUDIT_SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class SequenceRunner:
    def __init__(self, *outputs):
        self.outputs = list(outputs)
        self.index = 0

    def __call__(self, _argv, _timeout):
        output = self.outputs[min(self.index, len(self.outputs) - 1)]
        self.index += 1
        return SimpleNamespace(returncode=0, stdout=output, stderr=None)


class P317RecoveryOnlyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.core = cls.module.odin_core
        cls.close_audit = load_close_audit_module()

    def _snapshot(self, identities):
        return self.core.OdinSnapshot(
            timestamp_utc="2026-08-14T00:00:00.000000Z",
            returncode=0,
            raw_devices=tuple(path for path, _identity in identities),
            live_devices=tuple(path for path, _identity in identities),
            stale_devices=(),
            live_device_identities=tuple(identities),
            stdout=" ".join(path for path, _identity in identities),
            stderr="",
        )

    def _history(self, run_dir):
        snapshots = (
            self._snapshot(()),
            self._snapshot(((USB_A, "node-a"),)),
            self._snapshot(()),
            self._snapshot(((USB_A, "node-a2"), (USB_B, "node-b"))),
        )
        with self.core.transaction_session(run_dir) as lease:
            for sequence, snapshot in enumerate(snapshots):
                self.core.persist_snapshot(run_dir, sequence, snapshot, lease=lease)
        records = self.core.list_snapshot_receipts(run_dir)
        return records, self.module.HistoricalAmbiguityPatch(
            run_dir, 3, records[3]["sha256"]
        )

    def test_authority_binds_adapter_and_recovery_only_constraints(self):
        authority = self.module.load_authority()
        self.assertEqual(
            authority["approval_token"],
            self.module.APPROVAL_PREFIX + authority["approval_binding_sha256"],
        )
        self.assertEqual(
            authority["binding"]["constraints"],
            {
                "candidate_transfer_allowed": False,
                "rollback_transfer_maximum": 1,
                "fresh_multi_endpoint_allowed": False,
                "historical_receipt_preserved": True,
                "partition_payload": "boot-only-exact-rollback",
            },
        )

    def test_authority_token_mutation_fails_closed(self):
        authority = json.loads(self.module.DEFAULT_AUTHORITY.read_text())
        authority["approval_token"] = self.module.APPROVAL_PREFIX + "0" * 64
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "authority.json"
            path.write_text(json.dumps(authority), encoding="utf-8")
            with self.assertRaisesRegex(
                self.module.RecoveryOnlyError, "approval binding differs"
            ):
                self.module.load_authority(path)

    def test_live_recovery_rejects_noncanonical_authority_path_first(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "authority.json"
            path.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(
                self.module.RecoveryOnlyError, "canonical authority path"
            ):
                self.module.recover(path, "not-approved", Path("/usr/bin/adb"))

    def test_host_arm_is_exclusive_and_idempotent(self):
        authority = self.module.load_authority()
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with mock.patch.object(self.module, "_initial_inputs_match"):
                first = self.module.arm_recovery(authority, run_dir)
                second = self.module.arm_recovery(authority, run_dir)
            self.assertEqual(first, second)
            self.assertFalse(first["candidate_transfer_allowed"])
            arm = run_dir / self.module.ARM_FILENAME
            value = json.loads(arm.read_text())
            value["rollback_transfer_maximum"] = 2
            arm.chmod(0o600)
            arm.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(
                self.module.RecoveryOnlyError, "recovery arm changed"
            ):
                self.module.arm_recovery(authority, run_dir)

    def test_partial_temporary_arm_never_reaches_final_name(self):
        authority = self.module.load_authority()
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)

            def fail_after_partial(path, _value):
                path.write_bytes(b"partial")
                raise self.module.live.F1LiveError("fixture interruption")

            with (
                mock.patch.object(self.module, "_initial_inputs_match"),
                mock.patch.object(
                    self.module.live,
                    "_write_exclusive",
                    side_effect=fail_after_partial,
                ),
            ):
                with self.assertRaisesRegex(
                    self.module.RecoveryOnlyError, "could not be published"
                ):
                    self.module.arm_recovery(authority, run_dir)
            self.assertFalse((run_dir / self.module.ARM_FILENAME).exists())
            self.assertEqual(list(run_dir.iterdir()), [])

    def test_loaded_authority_identity_uses_the_parsed_bytes(self):
        authority = self.module.load_authority()
        payload = self.module.DEFAULT_AUTHORITY.read_bytes()
        self.assertEqual(
            authority[self.module.LOADED_AUTHORITY_IDENTITY],
            {
                "path": str(self.module.DEFAULT_AUTHORITY.relative_to(self.module.ROOT)),
                "size": len(payload),
                "sha256": self.module._sha256_bytes(payload),
            },
        )

    def test_original_resume_reproduces_historical_ambiguity_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            _records, patch = self._history(run_dir)
            with self.core.transaction_session(run_dir) as lease:
                with self.assertRaisesRegex(
                    self.core.OdinTransitionError, "ambiguous live Odin endpoints"
                ):
                    patch._original_resume(run_dir, 4, lease=lease)

    def test_exact_historical_barrier_allows_fresh_single_and_ticket_revalidation(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            _records, patch = self._history(run_dir)
            inventory = lambda: {USB_C: "node-c"}
            with patch.installed(), self.core.transaction_session(run_dir) as lease:
                wait = self.core.wait_for_single_live_endpoint(
                    Path("odin4"),
                    run_dir,
                    timeout_sec=1,
                    lease=lease,
                    sequence_start=4,
                    runner=SequenceRunner(USB_C),
                    device_identity=lambda path: "node-c" if path == USB_C else None,
                    device_inventory=inventory,
                )
                self.assertFalse(wait.timed_out)
                self.assertEqual(wait.ticket.generation, 2)
                result = self.core.revalidate_endpoint_ticket(
                    Path("odin4"),
                    run_dir,
                    wait.ticket,
                    sequence=wait.next_sequence,
                    lease=lease,
                    timeout_sec=1,
                    runner=SequenceRunner(USB_C),
                    device_identity=lambda path: "node-c" if path == USB_C else None,
                    device_inventory=inventory,
                )
            self.assertEqual(result["generation"], 2)
            self.assertEqual(result["original_snapshot_sequence"], 4)
            self.assertEqual(result["revalidation_snapshot_sequence"], 5)

    def test_altered_historical_barrier_hash_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            _records, _patch = self._history(run_dir)
            patch = self.module.HistoricalAmbiguityPatch(run_dir, 3, "0" * 64)
            with self.core.transaction_session(run_dir) as lease:
                with self.assertRaisesRegex(
                    self.core.OdinTransitionError,
                    "unapproved historical endpoint ambiguity",
                ):
                    patch.resume(run_dir, 4, lease=lease)

    def test_second_historical_ambiguity_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            _records, patch = self._history(run_dir)
            with self.core.transaction_session(run_dir) as lease:
                self.core.persist_snapshot(
                    run_dir,
                    4,
                    self._snapshot(((USB_B, "node-b2"), (USB_C, "node-c"))),
                    lease=lease,
                )
            with self.core.transaction_session(run_dir) as lease:
                with self.assertRaisesRegex(
                    self.core.OdinTransitionError,
                    "unapproved historical endpoint ambiguity",
                ):
                    patch.resume(run_dir, 5, lease=lease)

    def test_fresh_multi_endpoint_observation_remains_fatal(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            _records, patch = self._history(run_dir)
            tracker = patch._replay(self.core.list_snapshot_receipts(run_dir))
            with self.assertRaisesRegex(
                self.core.OdinTransitionError, "ambiguous live Odin endpoints"
            ):
                tracker.observe(((USB_B, "node-b"), (USB_C, "node-c")))

    def test_close_audit_accepts_only_unambiguous_post_barrier_receipts(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            endpoint_dir = base / "odin-endpoints"
            records, _patch = self._history(endpoint_dir)
            tail = (
                self._snapshot(((USB_C, "node-c"),)),
                self._snapshot(((USB_C, "node-c"),)),
                self._snapshot(()),
            )
            with self.core.transaction_session(endpoint_dir) as lease:
                for sequence, snapshot in enumerate(tail, len(records)):
                    self.core.persist_snapshot(
                        endpoint_dir, sequence, snapshot, lease=lease
                    )
            records = self.core.list_snapshot_receipts(endpoint_dir)
            expected_post_barrier = self.close_audit._post_barrier_closure(
                records, 3
            )
            authority = {
                "binding": {
                    "incident": {
                        "historical_ambiguity_sequence": 3,
                        "historical_ambiguity_identity_count": 2,
                        "run_dir": str(base),
                    },
                    "immutable_inputs": {
                        "historical_ambiguity_receipt": {
                            "sha256": records[3]["sha256"]
                        }
                    },
                }
            }
            result = self.close_audit.audit_receipt_history(
                authority,
                records,
                endpoint_dir=endpoint_dir,
                expected_post_barrier=expected_post_barrier,
            )
            self.assertEqual(result["snapshot_receipt_count"], 7)
            self.assertEqual(result["post_barrier_identity_counts"], [1, 1, 0])
            self.assertEqual(result["historical_generation"], 1)
            self.assertEqual(result["closed_generation"], 2)
            self.assertTrue(result["fresh_multi_fixture_rejected"])

            all_empty = copy.deepcopy(records)
            for record in all_empty[4:]:
                record["live_device_identities"] = []
            with self.assertRaisesRegex(
                self.close_audit.CloseAuditError,
                "generation semantics differ",
            ):
                self.close_audit.audit_receipt_history(
                    authority,
                    all_empty,
                    endpoint_dir=endpoint_dir,
                    expected_post_barrier=expected_post_barrier,
                )

            two_distinct = copy.deepcopy(records)
            two_distinct[5]["live_device_identities"] = [[USB_B, "node-b"]]
            with self.assertRaisesRegex(
                self.close_audit.CloseAuditError,
                "generation semantics differ",
            ):
                self.close_audit.audit_receipt_history(
                    authority,
                    two_distinct,
                    endpoint_dir=endpoint_dir,
                    expected_post_barrier=expected_post_barrier,
                )

            ambiguous = copy.deepcopy(records)
            ambiguous[5]["live_device_identities"] = [
                [USB_B, "node-b"],
                [USB_C, "node-c"],
            ]
            with self.assertRaisesRegex(
                self.close_audit.CloseAuditError,
                "post-barrier snapshot is ambiguous",
            ):
                self.close_audit.audit_receipt_history(
                    authority,
                    ambiguous,
                    endpoint_dir=endpoint_dir,
                    expected_post_barrier=expected_post_barrier,
                )

            missing = copy.deepcopy(records[:-1])
            with self.assertRaisesRegex(
                self.close_audit.CloseAuditError,
                "post-barrier receipt closure differs",
            ):
                self.close_audit.audit_receipt_history(
                    authority,
                    missing,
                    endpoint_dir=endpoint_dir,
                    expected_post_barrier=expected_post_barrier,
                )

            extra = copy.deepcopy(records)
            extra_record = copy.deepcopy(extra[-1])
            extra_record["sequence"] = len(extra)
            extra_record["sha256"] = "f" * 64
            extra.append(extra_record)
            with self.assertRaisesRegex(
                self.close_audit.CloseAuditError,
                "post-barrier receipt closure differs",
            ):
                self.close_audit.audit_receipt_history(
                    authority,
                    extra,
                    endpoint_dir=endpoint_dir,
                    expected_post_barrier=expected_post_barrier,
                )

            same_generation_drift = copy.deepcopy(records)
            for record in same_generation_drift[4:6]:
                record["live_device_identities"] = [[USB_B, "node-b"]]
            with self.assertRaisesRegex(
                self.close_audit.CloseAuditError,
                "post-barrier receipt closure differs",
            ):
                self.close_audit.audit_receipt_history(
                    authority,
                    same_generation_drift,
                    endpoint_dir=endpoint_dir,
                    expected_post_barrier=expected_post_barrier,
                )

    def test_backend_rejects_candidate_and_nonexact_rollback_before_super(self):
        backend = object.__new__(self.module.ExactRollbackBackend)
        backend.rollback_transfer_calls = 0
        backend.authority = {}
        with self.assertRaisesRegex(
            self.module.RecoveryOnlyError, "not the exact rollback"
        ):
            backend.transfer(None, None, "candidate", Path("."), 1, "candidate-attempt-01")
        with self.assertRaisesRegex(
            self.module.RecoveryOnlyError, "not the exact rollback"
        ):
            backend.transfer(None, None, "rollback", Path("."), 2, "rollback-attempt-02")

    def test_backend_allows_exact_rollback_once_then_blocks_second_call(self):
        rollback = {
            "path": "workspace/private/exact-rollback/AP.tar.md5",
            "size": 123,
            "sha256": "a" * 64,
        }
        backend = object.__new__(self.module.ExactRollbackBackend)
        backend.rollback_transfer_calls = 0
        backend.authority = {
            "binding": {"immutable_inputs": {"rollback_ap": rollback}}
        }
        prepared = SimpleNamespace(
            bundle=SimpleNamespace(manifest={"rollback_ap": dict(rollback)})
        )
        outcome = self.module.live.TransferOutcome(
            classification="odin_transfer_completed",
            completed=True,
            possible_device_session=True,
            receipt={"fixture": True},
        )
        with mock.patch.object(
            self.module.live.SamsungOdinBackend,
            "transfer",
            autospec=True,
            return_value=outcome,
        ) as inherited:
            actual = backend.transfer(
                prepared,
                SimpleNamespace(),
                "rollback",
                Path("."),
                1,
                "rollback-attempt-01",
            )
            self.assertEqual(actual, outcome)
            inherited.assert_called_once()
            with self.assertRaisesRegex(
                self.module.RecoveryOnlyError, "not the exact rollback"
            ):
                backend.transfer(
                    prepared,
                    SimpleNamespace(),
                    "rollback",
                    Path("."),
                    1,
                    "rollback-attempt-01",
                )

    def test_attempt_start_patch_blocks_attempt_two_before_common_writer(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            (run_dir / "rollback-attempt-01.start.json").write_text("{}\n")
            attempt_patch = self.module.SingleRollbackAttemptPatch()
            attempt_patch._original_begin = mock.Mock()
            with self.assertRaisesRegex(
                self.module.RecoveryOnlyError, "retry is forbidden"
            ):
                attempt_patch.begin(
                    SimpleNamespace(run_dir=run_dir), SimpleNamespace(), "rollback"
                )
            attempt_patch._original_begin.assert_not_called()
            self.assertFalse((run_dir / "rollback-attempt-02.start.json").exists())

    def test_consumed_attempt_without_result_blocks_reentry(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            (run_dir / "candidate-attempt-01.start.json").write_text("{}\n")
            (run_dir / "candidate-attempt-01.result.json").write_text("{}\n")
            (run_dir / "rollback-attempt-01.start.json").write_text("{}\n")
            with self.assertRaisesRegex(
                self.module.RecoveryOnlyError,
                "consumed without a durable result",
            ):
                self.module._rollback_resume_disposition(
                    SimpleNamespace(run_dir=run_dir),
                    "RECOVERY_DOWNLOAD",
                    {
                        "rollback_classification": None,
                        "rollback_completed": False,
                    },
                )
            self.assertFalse((run_dir / "rollback-attempt-02.start.json").exists())

    def test_closed_reentry_revalidates_live_result(self):
        authority = self.module.load_authority()
        prepared = SimpleNamespace(run_dir=Path("/host-only-fixture"))
        journal = SimpleNamespace(state=lambda: "CLOSED")
        result = {"recovery_required": False}
        with (
            mock.patch.object(
                self.module, "load_authority", return_value=authority
            ),
            mock.patch.object(
                self.module, "verify_incident", return_value=(prepared, journal)
            ),
            mock.patch.object(self.module, "_load_json", return_value=result),
            mock.patch.object(
                self.module.live, "validate_live_result", return_value=result
            ) as validate,
        ):
            actual = self.module.recover(
                self.module.DEFAULT_AUTHORITY,
                authority["approval_token"],
                Path("/usr/bin/adb"),
            )
        self.assertEqual(actual, result)
        validate.assert_called_once_with(result, prepared)

    def test_backend_cannot_request_download(self):
        backend = object.__new__(self.module.ExactRollbackBackend)
        with self.assertRaisesRegex(
            self.module.RecoveryOnlyError, "cannot request Download mode"
        ):
            backend.request_download(None)


if __name__ == "__main__":
    unittest.main()
