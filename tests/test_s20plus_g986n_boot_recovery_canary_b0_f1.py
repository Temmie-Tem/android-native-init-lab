from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
from contextlib import contextmanager


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import s20plus_g986n_boot_recovery_canary_b0_f1 as b0


BOOT_ID = "12345678-1234-1234-9234-123456789abc"


def ordered(values: dict[str, str], keys: tuple[str, ...]) -> bytes:
    return "".join(f"{key}={values[key]}\n" for key in keys).encode()


class S20PlusG986NBootRecoveryCanaryB0F1Tests(unittest.TestCase):
    def test_plan_is_active_boot_only_and_mandatory_rollback(self) -> None:
        plan = b0.render_plan()
        self.assertTrue(plan["active"])
        self.assertTrue(plan["live_authority"])
        self.assertEqual(plan["status"], "BINDING_ATTENDED_BOOT_ONLY_F1_ACTIVE")
        self.assertEqual(plan["candidate"]["partition"], "boot")
        self.assertEqual(plan["rollback"]["partition"], "boot")
        self.assertTrue(plan["rollback"]["mandatory"])
        self.assertTrue(plan["forbidden"]["recovery_partition_read"])
        self.assertTrue(plan["forbidden"]["recovery_partition_write"])
        self.assertTrue(plan["forbidden"]["recovery_partition_transfer"])
        self.assertTrue(plan["forbidden"]["candidate_replay"])
        self.assertTrue(plan["forbidden"]["rollback_replay"])

    def test_active_cli_dispatches_only_to_the_owned_prepare_entrypoint(self) -> None:
        run_dir = Path("/tmp/b0-active-cli-fixture")
        with mock.patch.object(
            b0.base,
            "bounded_command",
            side_effect=AssertionError("device command reached"),
        ), mock.patch.object(b0, "prepare", return_value=run_dir) as prepare, mock.patch.object(
            b0,
            "read_prepared",
            return_value={"approval_token": "fixture-approval"},
        ):
            self.assertEqual(b0.main(["--prepare"]), 0)
        prepare.assert_called_once_with(None)

    def test_self_normalized_identity_is_exact(self) -> None:
        self.assertEqual(
            b0.normalized_self_sha256(), b0.EXPECTED_REVIEWED_NORMALIZED_SHA256
        )
        receipt = b0.self_receipt()
        self.assertEqual(receipt["normalized_sha256"], b0.EXPECTED_REVIEWED_NORMALIZED_SHA256)
        self.assertEqual(receipt["sha256"], hashlib.sha256(b0.SCRIPT.read_bytes()).hexdigest())

    def test_independent_source_closure_is_exact_and_excludes_bootstrap(self) -> None:
        source = b0.SCRIPT.read_text()
        self.assertNotIn("s20plus_g986n_magisk_bootstrap_f1", source)
        self.assertNotIn("bootstrap.", source)
        receipts = b0.source_closure_receipts()
        self.assertEqual(
            set(receipts),
            {
                "inventory",
                "transport",
                "boot_verify",
                "raw_capture",
                "adb",
                "odin",
                "cage_shell",
                "cage_sleep",
            },
        )
        self.assertEqual(receipts["transport"]["sha256"], b0.SOURCE_CLOSURE["transport"][2])
        self.assertEqual(receipts["raw_capture"]["sha256"], b0.SOURCE_CLOSURE["raw_capture"][2])

    def test_module_and_api_substitution_are_rejected(self) -> None:
        original = b0.base.bounded_command
        try:
            b0.base.bounded_command = lambda *_args, **_kwargs: (0, b"", b"")
            with self.assertRaisesRegex(b0.B0F1Error, "rebound"):
                b0.source_closure_receipts()
        finally:
            b0.base.bounded_command = original
        with mock.patch.object(b0.base, "__file__", "/tmp/foreign.py"):
            with self.assertRaisesRegex(b0.B0F1Error, "module path"):
                b0.source_closure_receipts()
        original_member_reader = b0.transport.read_boot_only_member
        try:
            b0.transport.read_boot_only_member = lambda *_args, **_kwargs: b""
            with self.assertRaisesRegex(b0.B0F1Error, "rebound"):
                b0.source_closure_receipts()
        finally:
            b0.transport.read_boot_only_member = original_member_reader

    def test_host_artifact_closure_passes_exactly(self) -> None:
        closure = b0.validate_host_closure()
        self.assertEqual(closure["candidate"]["ap"]["sha256"], b0.CANDIDATE_AP_SHA256)
        self.assertEqual(closure["candidate"]["member"]["sha256"], b0.CANDIDATE_MEMBER_SHA256)
        self.assertEqual(closure["candidate"]["decoded_boot"]["sha256"], b0.CANDIDATE_BOOT_SHA256)
        self.assertEqual(closure["rollback"]["ap"]["sha256"], b0.ROLLBACK_AP_SHA256)
        self.assertEqual(closure["rollback"]["decoded_boot"]["sha256"], b0.ROLLBACK_BOOT_SHA256)

    def test_health_and_rollback_closures_are_branch_scoped(self) -> None:
        health = b0.health_source_closure_receipts()
        self.assertEqual(set(health), {"inventory", "raw_capture", "adb"})
        self.assertNotIn("odin", health)
        with mock.patch.object(
            b0, "self_receipt", return_value={"normalized_sha256": "1" * 64}
        ):
            rollback = b0.validate_rollback_closure()
        self.assertEqual(set(rollback), {"runner", "sources", "rollback"})
        self.assertNotIn("candidate", rollback)
        self.assertNotIn("physical_recovery", rollback)
        self.assertNotIn("manifest", rollback)

    def test_manifest_binds_zero_recovery_partition_access(self) -> None:
        receipt = b0.validate_manifest()
        self.assertEqual(receipt["sha256"], b0.MANIFEST_SHA256)
        value = json.loads(b0.MANIFEST.read_text())
        self.assertFalse(value["safety"]["recovery_partition_read"])
        self.assertFalse(value["safety"]["recovery_partition_write"])
        self.assertFalse(value["safety"]["recovery_partition_transfer"])
        self.assertTrue(value["boot_carrier_safety_delta"]["recovery_service_disabled"])

    def test_ap_audit_rejects_non_boot_member_identity(self) -> None:
        with self.assertRaises(b0.B0F1Error):
            b0.audit_boot_ap(
                b0.CANDIDATE_AP,
                b0.CANDIDATE_AP_SIZE,
                b0.CANDIDATE_AP_SHA256,
                b0.CANDIDATE_MEMBER_SIZE,
                "0" * 64,
                b0.CANDIDATE_BOOT_SIZE,
                b0.CANDIDATE_BOOT_SHA256,
                "candidate",
            )

    def test_public_and_root_parsers_are_exact(self) -> None:
        public = {
            "model": "SM-G986N",
            "device": "y2q",
            "product_name": "y2qksx",
            "incremental": "G986NKSS8IYC2",
            "boot_completed": "1",
            "bootanim": "stopped",
            "selinux": "Enforcing",
            "boot_id": BOOT_ID,
        }
        self.assertEqual(
            b0.parse_public_snapshot((0, ordered(public, b0.PUBLIC_SNAPSHOT_KEYS), b"")),
            public,
        )
        root = {"boot_id": BOOT_ID, **b0.EXPECTED_ROOT_OUTPUT}
        root_stdout = ordered(root, b0.ROOT_OUTPUT_KEYS)
        self.assertEqual(b0.parse_root_output((0, root_stdout, b"")), root)
        wrong = root_stdout.replace(b"u:r:magisk:s0", b"u:r:su:s0")
        with self.assertRaises(b0.B0F1Error):
            b0.parse_root_output((0, wrong, b""))

    def test_root_capture_is_bound_to_current_boot_and_stale_capture_is_not_reused(self) -> None:
        boot_a = BOOT_ID
        boot_b = "abcdef12-3456-4789-abcd-0123456789ab"
        row = {
            "serial": "SERIAL",
            "state": "device",
            "metadata": b0.EXPECTED_ADB_METADATA,
        }
        public_b = {
            "model": b0.TARGET["model"],
            "device": b0.TARGET["device"],
            "product_name": b0.TARGET["product"],
            "incremental": b0.TARGET["incremental"],
            "boot_completed": "1",
            "bootanim": "stopped",
            "selinux": "Enforcing",
            "boot_id": boot_b,
        }
        root_a = {"boot_id": boot_a, **b0.EXPECTED_ROOT_OUTPUT}
        with tempfile.TemporaryDirectory() as temporary:
            capture_dir = Path(temporary)
            b0.raw_capture.publish_captured_bytes(
                capture_dir,
                "final-root",
                stdout=ordered(root_a, b0.ROOT_OUTPUT_KEYS),
            )
            with mock.patch.object(
                b0, "health_source_closure_receipts", return_value={"fixed": True}
            ), mock.patch.object(
                b0, "adb_inventory", return_value=(row,)
            ), mock.patch.object(
                b0, "adb_devpath", return_value="usb:test"
            ), mock.patch.object(
                b0.base,
                "bounded_command",
                return_value=(0, ordered(public_b, b0.PUBLIC_SNAPSHOT_KEYS), b""),
            ), mock.patch.object(
                b0.raw_capture,
                "acquire_command",
                side_effect=b0.B0F1Error("root unavailable on boot B"),
            ) as acquire:
                with self.assertRaisesRegex(b0.B0F1Error, "root unavailable"):
                    b0.resident_health_once(capture_dir, "final-root")
                self.assertEqual(acquire.call_args.args[2], "final-root-resume-0001")

    def test_completed_failed_root_capture_rotates_to_a_new_ordinal(self) -> None:
        boot_b = "abcdef12-3456-4789-abcd-0123456789ab"
        row = {
            "serial": "SERIAL",
            "state": "device",
            "metadata": b0.EXPECTED_ADB_METADATA,
        }
        public_b = {
            "model": b0.TARGET["model"],
            "device": b0.TARGET["device"],
            "product_name": b0.TARGET["product"],
            "incremental": b0.TARGET["incremental"],
            "boot_completed": "1",
            "bootanim": "stopped",
            "selinux": "Enforcing",
            "boot_id": boot_b,
        }
        root_b = {"boot_id": boot_b, **b0.EXPECTED_ROOT_OUTPUT}
        with tempfile.TemporaryDirectory() as temporary:
            capture_dir = Path(temporary)
            b0.raw_capture.publish_captured_bytes(
                capture_dir, "final-root", stdout=b"not-root\n", returncode=1
            )

            def acquire(_argv, directory, name, **kwargs):
                return b0.raw_capture.publish_captured_bytes(
                    directory,
                    name,
                    stdout=ordered(root_b, b0.ROOT_OUTPUT_KEYS),
                    stdout_name=kwargs["stdout_name"],
                    stderr_name=kwargs["stderr_name"],
                )

            with mock.patch.object(
                b0, "health_source_closure_receipts", return_value={"fixed": True}
            ), mock.patch.object(
                b0, "adb_inventory", return_value=(row,)
            ), mock.patch.object(
                b0, "adb_devpath", return_value="usb:test"
            ), mock.patch.object(
                b0.base,
                "bounded_command",
                return_value=(0, ordered(public_b, b0.PUBLIC_SNAPSHOT_KEYS), b""),
            ), mock.patch.object(
                b0.raw_capture, "acquire_command", side_effect=acquire
            ):
                health, serial = b0.resident_health_once(capture_dir, "final-root")
            self.assertEqual(serial, "SERIAL")
            self.assertEqual(
                health["boot_id_sha256"], hashlib.sha256(boot_b.encode()).hexdigest()
            )
            self.assertTrue(
                health["root_capture"]["path"].endswith(
                    "final-root-resume-0001.capture.json"
                )
            )

    def test_recovery_transport_requires_exact_root_banner_and_target(self) -> None:
        values = {
            "model": "SM-G986N",
            "device": "y2q",
            "product_name": "y2qksx",
            "incremental": "G986NKSS8IYC2",
            "boot_id": BOOT_ID,
            "uid": "0",
            "gid": "0",
            "service_adb_root": "1",
            "usb_config": "adb",
            "adbd_state": "running",
        }
        self.assertEqual(
            b0.parse_recovery_transport(
                (0, ordered(values, b0.RECOVERY_TRANSPORT_KEYS), b"")
            ),
            values,
        )
        values["service_adb_root"] = "0"
        with self.assertRaises(b0.B0F1Error):
            b0.parse_recovery_transport(
                (0, ordered(values, b0.RECOVERY_TRANSPORT_KEYS), b"")
            )

    def test_health_validator_rejects_forged_boot_digest_and_wrong_capture_family(self) -> None:
        boot_b = "abcdef12-3456-4789-abcd-0123456789ab"
        root_a = {"boot_id": BOOT_ID, **b0.EXPECTED_ROOT_OUTPUT}
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            handle = b0.raw_capture.publish_captured_bytes(
                run_dir,
                "final-root",
                stdout=ordered(root_a, b0.ROOT_OUTPUT_KEYS),
            )
            health = {
                "target": dict(b0.TARGET),
                "serial_sha256": "1" * 64,
                "topology_sha256": b0.EXPECTED_ANDROID_TOPOLOGY_SHA256,
                "boot_id_sha256": hashlib.sha256(boot_b.encode()).hexdigest(),
                "public_health": {
                    "model": b0.TARGET["model"],
                    "device": b0.TARGET["device"],
                    "product_name": b0.TARGET["product"],
                    "incremental": b0.TARGET["incremental"],
                    "boot_completed": "1",
                    "bootanim": "stopped",
                    "selinux": "Enforcing",
                },
                "root_health": dict(b0.EXPECTED_ROOT_OUTPUT),
                "inventory_sha256": "2" * 64,
                "root_capture": {
                    "path": str(handle.receipt_path),
                    "size": handle.receipt_path.stat().st_size,
                    "sha256": hashlib.sha256(
                        handle.receipt_path.read_bytes()
                    ).hexdigest(),
                },
            }
            with self.assertRaisesRegex(b0.B0F1Error, "boot identity"):
                b0._validate_resident_health_receipt(
                    run_dir, health, "final resident health", "final-root"
                )
            health["boot_id_sha256"] = hashlib.sha256(BOOT_ID.encode()).hexdigest()
            with self.assertRaisesRegex(b0.B0F1Error, "escaped"):
                b0._validate_resident_health_receipt(
                    run_dir, health, "candidate resident health", "candidate-android-root"
                )

    def test_terminal_publisher_rejects_final_boot_reused_from_resident_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            b0.durable_json(
                run_dir / "candidate-observation.json",
                {
                    "claim_verdict": "NO_PROOF",
                    "resident_health": {"boot_id_sha256": "2" * 64},
                },
            )
            prepared = {
                "binding_sha256": "3" * 64,
                "binding": {"preflight": {"boot_id_sha256": "1" * 64}},
            }
            final = {
                "health": {"boot_id_sha256": "2" * 64},
                "rollback_transfer_completed": False,
            }
            with self.assertRaisesRegex(b0.B0F1Error, "not fresh"):
                b0.publish_terminal_from_final(run_dir, prepared, final)

    def test_recovery_claim_proved_refuted_and_no_proof(self) -> None:
        exact = {
            "marker_state": "regular",
            "marker_meta": "444:0:0:1:159",
            "marker_sha256": b0.MARKER_SHA256,
            "pid1_exe": "/system/bin/init",
            "pid1_cmdline_hex": "2f696e697400",
            "pid1_context": "u:r:init:s0",
            "ueventd_count": "1",
            "ueventd_exe": "/system/bin/init",
            "ueventd_cmdline_hex": "756576656e746400",
            "recovery_state": "stopped",
            "recovery_pid_count": "0",
        }
        verdict, parsed = b0.parse_recovery_claim(
            (0, ordered(exact, b0.RECOVERY_CLAIM_KEYS), b"")
        )
        self.assertEqual(verdict, "PROVED")
        self.assertEqual(parsed, exact)
        exact["marker_state"] = "absent"
        verdict, _ = b0.parse_recovery_claim(
            (0, ordered(exact, b0.RECOVERY_CLAIM_KEYS), b"")
        )
        self.assertEqual(verdict, "REFUTED")
        verdict, parsed = b0.parse_recovery_claim((1, b"", b"failed"))
        self.assertEqual((verdict, parsed), ("NO_PROOF", {}))

    def test_terminal_taxonomy_separates_experiment_and_recovery(self) -> None:
        self.assertEqual(
            b0.derive_terminal_verdict("odin_transfer_completed", "PROVED", True),
            ("PROVED_B0_RETURNED_RESIDENT_HEALTHY", True),
        )
        self.assertEqual(
            b0.derive_terminal_verdict("odin_transfer_completed", "REFUTED", True),
            ("REFUTED_B0_RETURNED_RESIDENT_HEALTHY", False),
        )
        self.assertEqual(
            b0.derive_terminal_verdict(
                "odin_device_session_failure_or_unknown", "PROVED", True
            ),
            ("NO_PROOF_B0_RETURNED_RESIDENT_HEALTHY", False),
        )
        self.assertEqual(
            b0.derive_terminal_verdict("odin_transfer_completed", "PROVED", False),
            ("NO_PROOF_B0_RETURNED_RESIDENT_HEALTHY", False),
        )
        self.assertEqual(
            b0.derive_terminal_verdict(
                "odin_device_session_failure_or_unknown", "REFUTED", True
            ),
            ("NO_PROOF_B0_RETURNED_RESIDENT_HEALTHY", False),
        )

    def test_odin_classifier_is_conservative(self) -> None:
        complete = b"Setup Connection Upload Binaries boot.img.lz4 100% Close Connection"
        self.assertEqual(b0.classify_odin_output(0, complete, b""), "odin_transfer_completed")
        self.assertEqual(b0.classify_odin_output(1, complete, b""), "odin_device_session_failure_or_unknown")
        self.assertEqual(b0.classify_odin_output(1, b"Fail parse", b""), "odin_local_parse_failure")
        self.assertEqual(
            b0.classify_odin_output(1, b"Fail parse Setup Connection", b""),
            "odin_device_session_failure_or_unknown",
        )

    def test_raw_capture_faults_override_success_markers(self) -> None:
        complete = b"Setup Connection Upload Binaries boot.img.lz4 100% Close Connection"
        handle = SimpleNamespace(
            returncode=0,
            producer_error_type=None,
            timed_out=False,
            output_exceeded=True,
        )
        self.assertEqual(
            b0.classify_odin_capture(handle, complete, b""),
            "odin_device_session_failure_or_unknown",
        )
        self.assertFalse(b0.raw_dispatch_proved(handle, b""))
        handle.output_exceeded = False
        self.assertFalse(b0.raw_dispatch_proved(handle, b"warning"))

    def test_failure_shape_cannot_forge_completed_candidate(self) -> None:
        forged = {
            "schema": "s20plus_g986n_b0_transfer_result_v1",
            "version": b0.VERSION,
            "kind": "candidate",
            "binding_sha256": "1" * 64,
            "classification": "odin_transfer_completed",
            "failure_class": "InjectedFailure",
            "possible_partition_effect": True,
            "host_process_quiescence_proved": False,
            "replay_permitted": False,
            "at": "2026-08-31T00:00:00+00:00",
        }
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(b0.B0F1Error, "failure result"):
                b0._validate_transfer_outcome(
                    Path(temporary), forged, "candidate", "1" * 64
                )

    def test_download_listing_rejects_duplicates_and_foreign_grammar(self) -> None:
        self.assertEqual(
            b0.parse_download_listing("/dev/bus/usb/001/002\n"),
            ["/dev/bus/usb/001/002"],
        )
        with self.assertRaises(b0.B0F1Error):
            b0.parse_download_listing("/dev/bus/usb/001/002\n/dev/bus/usb/001/002\n")
        with self.assertRaises(b0.B0F1Error):
            b0.parse_download_listing("serial-device\n")

    def test_download_session_ignores_only_ctime(self) -> None:
        left = {
            "device": "/dev/bus/usb/001/002",
            "endpoint_sha256": "1" * 64,
            "endpoint_identity": [1, 2, 3, 4],
            "topology_sha256": "2" * 64,
            "usb": {**b0.DOWNLOAD_USB, "serial_absent": True},
        }
        right = json.loads(json.dumps(left))
        right["endpoint_identity"][3] = 9
        self.assertTrue(b0.same_download_session(left, right))
        right["endpoint_identity"][2] = 10
        self.assertFalse(b0.same_download_session(left, right))

    def test_endpoint_replacement_stops_before_raw_odin_backend(self) -> None:
        endpoint = {
            "device": "/dev/bus/usb/001/002",
            "endpoint_identity": [1, 2, 3, 4],
            "endpoint_sha256": hashlib.sha256(b"/dev/bus/usb/001/002").hexdigest(),
            "topology_sha256": next(iter(b0.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)),
            "usb": {**b0.DOWNLOAD_USB, "serial_absent": True},
        }

        @contextmanager
        def pinned(path: Path, **_kwargs):
            class Item:
                def __init__(self, item_path: Path) -> None:
                    self.path = item_path

                def receipt(self):
                    return {"path": str(self.path), "size": 1, "sha256": "0" * 64}

            yield Item(path)

        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            b0.transport, "pin_regular_file", pinned
        ), mock.patch.object(b0.transport, "pin_boot_only_ap", pinned), mock.patch.object(
            b0.transport, "revalidate_pinned_path"
        ), mock.patch.object(
            b0.transport,
            "build_odin_boot_only_command",
            return_value=["odin4", "--reboot"],
        ), mock.patch.object(
            b0, "endpoint_stat", return_value=(1, 2, 99, 4)
        ), mock.patch.object(
            b0.raw_capture, "acquire_command"
        ) as acquire:
            with self.assertRaisesRegex(b0.B0F1Error, "dispatch boundary"):
                b0.execute_odin_exact(
                    Path(temporary),
                    "candidate",
                    b0.CANDIDATE_AP,
                    b0.CANDIDATE_AP_SIZE,
                    b0.CANDIDATE_AP_SHA256,
                    endpoint,
                    "1" * 64,
                )
            acquire.assert_not_called()

    def test_abort_return_rechecks_endpoint_after_intent_before_backend(self) -> None:
        endpoint = {
            "device": "/dev/bus/usb/001/002",
            "endpoint_identity": [1, 2, 3, 4],
            "endpoint_sha256": hashlib.sha256(
                b"/dev/bus/usb/001/002"
            ).hexdigest(),
            "topology_sha256": next(iter(b0.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)),
            "usb": {**b0.DOWNLOAD_USB, "serial_absent": True},
        }

        @contextmanager
        def pinned(path: Path, **_kwargs):
            yield SimpleNamespace(path=path)

        cage_binding = {
            "schema": "fixture",
            "binding_sha256": "1" * 64,
            "cage": "/sys/fs/cgroup/fixture",
            "cage_identity": [1, 2, 3, 4, 5],
        }
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            b0.transport, "pin_regular_file", pinned
        ), mock.patch.object(
            b0.transport, "revalidate_pinned_path"
        ), mock.patch.object(
            b0,
            "prepare_process_cage",
            return_value=(Path("/sys/fs/cgroup/fixture"), cage_binding),
        ), mock.patch.object(
            b0, "endpoint_stat", side_effect=[(1, 2, 3, 4), (1, 2, 99, 4)]
        ), mock.patch.object(
            b0, "quiesce_process_cage"
        ) as quiesce, mock.patch.object(
            b0.raw_capture, "acquire_command"
        ) as acquire:
            with self.assertRaisesRegex(b0.B0F1Error, "dispatch boundary"):
                b0.payload_free_return(Path(temporary), endpoint)
            acquire.assert_not_called()
            quiesce.assert_called_once()

    def test_stable_endpoint_change_is_conservative(self) -> None:
        receipt = {
            "endpoint_post_state": "changed",
            "endpoint_pre_identity": [1, 2, 3, 4],
            "endpoint_post_identity": [1, 2, 9, 5],
        }
        self.assertFalse(b0.endpoint_ctime_only_change(receipt))
        receipt["endpoint_post_identity"] = [1, 2, 3, 5]
        self.assertTrue(b0.endpoint_ctime_only_change(receipt))

    def test_strict_json_rejects_duplicate_noncanonical_and_indirect(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            good = root / "good.json"
            b0.durable_json(good, {"schema": "x", "value": 1})
            self.assertEqual(b0.read_json(good, "good"), {"schema": "x", "value": 1})
            duplicate = root / "duplicate.json"
            duplicate.write_bytes(b'{"x":1,"x":2}\n')
            with self.assertRaises(b0.B0F1Error):
                b0.read_json(duplicate, "duplicate")
            noncanonical = root / "noncanonical.json"
            noncanonical.write_bytes(b'{"value": 1}\n')
            with self.assertRaises(b0.B0F1Error):
                b0.read_json(noncanonical, "noncanonical")
            link = root / "link.json"
            link.symlink_to(good)
            with self.assertRaises(b0.B0F1Error):
                b0.read_json(link, "link")

    def test_atomic_journal_publication_never_exposes_partial_final_name(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            interrupted = root / "interrupted.json"
            with mock.patch.object(
                b0.os, "write", side_effect=OSError("injected short write")
            ):
                with self.assertRaises(OSError):
                    b0.durable_json(interrupted, {"value": "complete"})
            self.assertFalse(interrupted.exists())
            final = root / "final.json"
            b0.durable_json(final, {"value": 1})
            with self.assertRaises(FileExistsError):
                b0.durable_json(final, {"value": 2})
            self.assertEqual(b0.read_json(final, "final"), {"value": 1})

    def test_namespace_rejects_unknown_indirect_and_impossible_order(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "foreign").write_text("x")
            with self.assertRaisesRegex(b0.B0F1Error, "unknown"):
                b0.validate_namespace(root)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "preflight.json"
            target.write_text("x")
            os.link(target, root / "prepared.json")
            with self.assertRaisesRegex(b0.B0F1Error, "indirect"):
                b0.validate_namespace(root)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            b0.durable_json(root / "prepared.json", {"x": 1})
            with self.assertRaisesRegex(b0.B0F1Error, "dependency"):
                b0.validate_namespace(root)

    def test_repeatable_health_partial_ordinals_are_bounded_by_grammar(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "final-root.stdout").write_bytes(b"partial")
            (root / "final-root-resume-0001.stdout").write_bytes(b"partial")
            b0.validate_namespace(root)
            (root / "final-root-resume-10000.stdout").write_bytes(b"bad")
            with self.assertRaisesRegex(b0.B0F1Error, "unknown"):
                b0.validate_namespace(root)

    def test_global_candidate_claim_is_cross_run_one_shot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_root = root / "runs"
            claim_root = run_root / "claims"
            run = root / "run"
            run.mkdir()
            with mock.patch.object(b0, "RUN_ROOT", run_root), mock.patch.object(
                b0, "CLAIM_ROOT", claim_root
            ):
                value = b0.consume_candidate_globally(run, "1" * 64)
                self.assertFalse(value["candidate_replay_permitted"])
                self.assertEqual(
                    b0.require_candidate_claim(run, "1" * 64), value
                )
                with self.assertRaises(FileExistsError):
                    b0.consume_candidate_globally(run, "1" * 64)

    def test_guard_uses_exact_dirfd_and_never_deletes_foreign_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            current = root / "guard-parent"
            current.mkdir()
            guard = current / "active-action.json"
            run = root / "run"
            run.mkdir()
            with mock.patch.object(b0, "SHARED_GUARD", guard):
                b0.acquire_guard(run)
                with self.assertRaisesRegex(b0.B0F1Error, "unresolved"):
                    b0.acquire_guard(run)
                old = root / "old-parent"
                current.rename(old)
                current.mkdir()
                foreign = current / "active-action.json"
                b0.durable_json(foreign, {"schema": "foreign"})
                with self.assertRaisesRegex(b0.B0F1Error, "foreign"):
                    b0.release_guard(run)
                self.assertTrue(foreign.exists())
                self.assertTrue((old / "active-action.json").exists())

    def test_direct_directory_chain_rejects_intermediate_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            direct = root / "direct"
            direct.mkdir()
            link = root / "link"
            link.symlink_to(direct, target_is_directory=True)
            with self.assertRaises(OSError):
                descriptor = b0.open_direct_directory(link)
                os.close(descriptor)

    def test_source_orders_claim_intent_backend_and_terminal_guard_release(self) -> None:
        source = b0.SCRIPT.read_text()
        execute_block = source[source.index("def execute(") : source.index("def resume_run(")]
        self.assertLess(
            execute_block.index("consume_candidate_globally"),
            execute_block.index('transfer_boot(run_dir, "candidate"'),
        )
        transfer_block = source[source.index("def transfer_boot(") : source.index("def recovery_probe(")]
        self.assertLess(
            transfer_block.index("preflight_odin_dispatch"),
            transfer_block.index('durable_json(run_dir / f"{kind}-intent.json"'),
        )
        self.assertLess(
            transfer_block.index('durable_json(run_dir / f"{kind}-intent.json"'),
            transfer_block.index("receipt, handle = execute_odin_exact"),
        )
        resume_block = source[source.index("def resume_run(") : source.index("def arm_physical_rollback(")]
        self.assertLess(
            resume_block.index("require_all_transfer_processes_quiescent"),
            resume_block.index("observe_candidate"),
        )
        terminal_block = source[
            source.index("def publish_terminal_from_final(") : source.index("def final_health_and_terminal(")
        ]
        self.assertLess(
            terminal_block.index('durable_json(run_dir / "terminal.json"'),
            terminal_block.index("release_guard(run_dir)"),
        )

    def test_recovery_scripts_are_fixed_read_only_and_service_stays_disabled(self) -> None:
        combined = b0.RECOVERY_TRANSPORT_SCRIPT + b0.RECOVERY_CLAIM_SCRIPT
        for forbidden in (
            "setprop ",
            "start recovery",
            "enable recovery",
            "restart recovery",
            " mount ",
            " remount ",
            " rm ",
            " dd ",
            ">/",
        ):
            self.assertNotIn(forbidden, combined)
        self.assertIn("init.svc.recovery", b0.RECOVERY_CLAIM_SCRIPT)
        self.assertIn("pidof recovery", b0.RECOVERY_CLAIM_SCRIPT)
        self.assertIn("/proc/1/cmdline", b0.RECOVERY_CLAIM_SCRIPT)
        self.assertIn("pidof ueventd", b0.RECOVERY_CLAIM_SCRIPT)

    def test_no_caller_selectable_artifact_or_command_arguments(self) -> None:
        actions = {action.dest for action in b0.build_parser()._actions}
        self.assertNotIn("candidate", actions)
        self.assertNotIn("rollback", actions)
        self.assertNotIn("command", actions)
        self.assertNotIn("endpoint", actions)
        self.assertNotIn("serial", actions)
        self.assertNotIn("adb", actions)
        self.assertNotIn("odin", actions)

    def test_physical_recovery_evidence_is_hash_bound_but_not_standing_authority(self) -> None:
        receipts = b0.physical_recovery_receipts()
        self.assertTrue(receipts["live_fallback_still_attended"])
        self.assertIn("historical", receipts["scope"])
        self.assertEqual(
            receipts["resident_report"]["sha256"],
            b0.PHYSICAL_RECOVERY_EVIDENCE["resident_report"]["sha256"],
        )

    def test_exact_namespace_contains_no_recovery_partition_transfer_artifact(self) -> None:
        source = b0.SCRIPT.read_text()
        self.assertNotIn("recovery.img.lz4", source)
        self.assertNotRegex(source, r"\[.*(?:-a|--AP).*recovery")
        self.assertEqual(b0.CANDIDATE_AP.parent.name, "candidate")
        self.assertEqual(b0.ROLLBACK_AP.parent.name, "rollback")

    def test_physical_reporting_cut_gets_one_current_read_then_durable_miss(self) -> None:
        binding_sha256 = "1" * 64
        expires = int(b0.time.time()) + 600
        arm_core = {
            "schema": "s20plus_g986n_b0_physical_rollback_intent_v1",
            "version": b0.VERSION,
            "binding_sha256": binding_sha256,
            "branch": "attended-entry-required",
            "baseline": {
                "schema": "s20plus_g986n_b0_download_baseline_v1",
                "endpoint_count": 0,
                "listing_sha256": "2" * 64,
                "at": "2026-08-31T00:00:00+00:00",
            },
            "baseline_sha256": "",
            "action": "one-attended-physical-download-entry-if-not-already-present",
            "action_attempt_maximum": 1,
            "rollback_replay_permitted": False,
            "expires_unix": expires,
            "at": "2026-08-31T00:00:00+00:00",
        }
        arm_core["baseline_sha256"] = b0.digest(arm_core["baseline"])
        confirmation = b0.PHYSICAL_CONFIRM_PREFIX + b0.digest(arm_core)
        arm = {**arm_core, "confirmation_token": confirmation}
        prepared = {"binding_sha256": binding_sha256}
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            b0.durable_json(run_dir / "physical-rollback-intent.json", arm)
            b0.durable_json(
                run_dir / "physical-observation-intent.json",
                {
                    "schema": "s20plus_g986n_b0_physical_observation_intent_v1",
                    "version": b0.VERSION,
                    "binding_sha256": binding_sha256,
                    "baseline_sha256": arm["baseline_sha256"],
                    "attempt": 1,
                    "no_replay": True,
                    "at": "2026-08-31T00:00:00+00:00",
                },
            )
            with mock.patch.object(b0, "require_active"), mock.patch.object(
                b0, "read_prepared", return_value=prepared
            ), mock.patch.object(
                b0, "require_all_transfer_processes_quiescent"
            ), mock.patch.object(
                b0,
                "enumerate_download",
                side_effect=[([], "3" * 64), (["/dev/bus/usb/001/002"], "4" * 64)],
            ) as enumerate_download, mock.patch.object(
                b0, "identify_download"
            ) as identify_download:
                with self.assertRaises(b0.B0F1Error):
                    b0.confirm_physical_rollback(run_dir, confirmation)
                with self.assertRaisesRegex(b0.B0F1Error, "already consumed"):
                    b0.confirm_physical_rollback(run_dir, confirmation)
            self.assertEqual(enumerate_download.call_count, 1)
            identify_download.assert_not_called()
            self.assertTrue((run_dir / "physical-observation-miss.json").exists())

    def test_stale_already_download_confirmation_never_dispatches(self) -> None:
        binding_sha256 = "1" * 64
        endpoint = {
            "device": "/dev/bus/usb/001/002",
            "endpoint_identity": [1, 2, 3, 4],
            "endpoint_sha256": hashlib.sha256(
                b"/dev/bus/usb/001/002"
            ).hexdigest(),
            "topology_sha256": next(iter(b0.EXPECTED_DOWNLOAD_TOPOLOGY_SHA256)),
            "usb": {**b0.DOWNLOAD_USB, "serial_absent": True},
        }
        arm_core = {
            "schema": "s20plus_g986n_b0_physical_rollback_intent_v1",
            "version": b0.VERSION,
            "binding_sha256": binding_sha256,
            "branch": "already-download",
            "baseline": None,
            "baseline_sha256": None,
            "action": "one-attended-physical-download-entry-if-not-already-present",
            "action_attempt_maximum": 1,
            "rollback_replay_permitted": False,
            "expires_unix": 1,
            "at": "2026-08-31T00:00:00+00:00",
        }
        confirmation = b0.PHYSICAL_CONFIRM_PREFIX + b0.digest(arm_core)
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            b0.durable_json(
                run_dir / "physical-rollback-intent.json",
                {**arm_core, "confirmation_token": confirmation},
            )
            b0.durable_json(
                run_dir / "physical-rollback-arrival.json",
                {
                    "schema": "s20plus_g986n_b0_physical_rollback_arrival_v1",
                    "version": b0.VERSION,
                    "binding_sha256": binding_sha256,
                    "branch": "already-download-at-arm",
                    "endpoint": endpoint,
                    "baseline_sha256": None,
                    "arrival_listing_sha256": "2" * 64,
                    "observed_unix": 1,
                    "at": "2026-08-31T00:00:00+00:00",
                },
            )
            with mock.patch.object(b0, "require_active"), mock.patch.object(
                b0, "read_prepared", return_value={"binding_sha256": binding_sha256}
            ), mock.patch.object(
                b0, "require_all_transfer_processes_quiescent"
            ), mock.patch.object(
                b0.time, "time", return_value=2
            ), mock.patch.object(
                b0, "identify_download"
            ) as identify_download, mock.patch.object(
                b0, "rollback_from_arrival"
            ) as rollback:
                with self.assertRaisesRegex(b0.B0F1Error, "confirmation expired"):
                    b0.confirm_physical_rollback(run_dir, confirmation)
            identify_download.assert_not_called()
            rollback.assert_not_called()

    def test_partial_global_claim_is_consumed_but_preserves_bound_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_root = root / "runs"
            claim_root = run_root / "claims"
            run_root.mkdir()
            claim_root.mkdir()
            run = run_root / "run"
            run.mkdir()
            with mock.patch.object(b0, "RUN_ROOT", run_root), mock.patch.object(
                b0, "CLAIM_ROOT", claim_root
            ):
                _intent, claim = b0._candidate_claim_intent(run, "1" * 64)
                path = b0.claim_path()
                path.write_bytes(b0.canonical_bytes(claim)[:37])
                path.chmod(0o400)
                recovered = b0.require_candidate_claim(run, "1" * 64)
            self.assertEqual(recovered["state"], "uncertain-partial-global-claim")
            self.assertFalse(recovered["candidate_replay_permitted"])

    def test_process_cage_capability_kills_a_surviving_descendant(self) -> None:
        receipt = b0.validate_process_cage_capability()
        self.assertTrue(receipt["descendant_survived_direct_parent_timeout"])
        self.assertTrue(receipt["cgroup_kill_emptied_descendants"])
        self.assertTrue(receipt["cgroup_removed"])

    def test_preintent_empty_cage_cut_is_safely_recreated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "run"
            run_dir.mkdir()
            parent = root / "cgroup"
            parent.mkdir()
            with mock.patch.object(
                b0, "_current_cgroup_parent", return_value=parent
            ), mock.patch.object(
                b0, "_cgroup_populated", return_value=False
            ), mock.patch.object(
                b0, "_host_boot_id", return_value=BOOT_ID
            ):
                first_path, first = b0.prepare_process_cage(
                    run_dir, "rollback", "1" * 64
                )
                second_path, second = b0.prepare_process_cage(
                    run_dir, "rollback", "1" * 64
                )
            self.assertEqual(first_path, second_path)
            self.assertTrue(second_path.is_dir())
            self.assertEqual(second["binding_sha256"], "1" * 64)
            second_path.rmdir()

    def test_owner_dead_bounded_listing_cage_waits_empty_then_removes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            cage = Path(temporary) / "s20plus-b0-odin-list"
            cage.mkdir()
            with mock.patch.object(
                b0, "_cgroup_populated", side_effect=[True, False, False]
            ), mock.patch.object(b0.time, "sleep"):
                b0._remove_stale_bounded_cgroup(
                    cage, 11, "earlier Odin listing cgroup"
                )
            self.assertFalse(cage.exists())

    def test_all_odin_paths_use_the_fixed_environment_and_cage(self) -> None:
        source = b0.SCRIPT.read_text()
        self.assertEqual(
            b0.ODIN_FIXED_ENV,
            {"LANG": "C", "LC_ALL": "C", "PATH": "/usr/bin:/bin"},
        )
        for injected in ("LD_PRELOAD", "LD_LIBRARY_PATH", "LD_AUDIT", "GLIBC_TUNABLES"):
            self.assertNotIn(injected, b0.ODIN_FIXED_ENV)
        self.assertNotIn(
            'base.bounded_command([str(odin.path), "-l"]', source
        )
        self.assertIn("def _bounded_odin_listing", source)
        self.assertIn("def quiesce_process_cage", source)
        self.assertGreaterEqual(source.count("env=ODIN_FIXED_ENV"), 3)

    def test_rollback_preflight_failure_does_not_consume_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            b0,
            "preflight_odin_dispatch",
            side_effect=b0.ProcessCageError("cgroup unavailable"),
        ):
            run_dir = Path(temporary)
            with self.assertRaisesRegex(b0.ProcessCageError, "cgroup unavailable"):
                b0.transfer_boot(
                    run_dir,
                    "rollback",
                    {"endpoint": "fixture"},
                    "1" * 64,
                )
            self.assertFalse((run_dir / "rollback-intent.json").exists())
            self.assertFalse((run_dir / "rollback-result.json").exists())

    def test_resume_stops_before_observation_when_cage_quiescence_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            b0, "require_active"
        ), mock.patch.object(
            b0, "validate_run_dir", side_effect=lambda value: value
        ), mock.patch.object(
            b0,
            "read_prepared",
            return_value={"binding_sha256": "1" * 64},
        ), mock.patch.object(
            b0,
            "require_all_transfer_processes_quiescent",
            side_effect=b0.ProcessCageError("cage still populated"),
        ), mock.patch.object(
            b0, "observe_candidate"
        ) as observe, mock.patch.object(
            b0, "rollback_from_arrival"
        ) as rollback:
            with self.assertRaisesRegex(b0.ProcessCageError, "still populated"):
                b0.resume_run(Path(temporary))
            observe.assert_not_called()
            rollback.assert_not_called()

    def test_old_physical_baseline_never_adopts_a_preexisting_endpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            b0.durable_json(
                run_dir / "physical-rollback-baseline.json",
                {
                    "schema": "s20plus_g986n_b0_download_baseline_v1",
                    "endpoint_count": 0,
                    "listing_sha256": "2" * 64,
                    "at": "2026-08-31T00:00:00+00:00",
                },
            )
            b0.durable_json(
                run_dir / "candidate-observation.json", {"environment": "no-arrival"}
            )
            with mock.patch.object(b0, "require_active"), mock.patch.object(
                b0,
                "read_prepared",
                return_value={"binding_sha256": "1" * 64},
            ), mock.patch.object(b0, "require_candidate_claim"), mock.patch.object(
                b0, "require_all_transfer_processes_quiescent"
            ), mock.patch.object(
                b0,
                "download_baseline",
                side_effect=b0.B0F1Error("Download baseline is not empty"),
            ):
                with self.assertRaisesRegex(b0.B0F1Error, "not empty"):
                    b0.arm_physical_rollback(run_dir)
            self.assertFalse((run_dir / "physical-rollback-intent.json").exists())

    def test_rollback_effect_baseline_cut_never_waits_for_or_adopts_arrival(self) -> None:
        serial = "SERIAL"
        serial_sha256 = hashlib.sha256(serial.encode()).hexdigest()
        prepared = {
            "binding_sha256": "1" * 64,
            "binding": {"preflight": {"serial_sha256": serial_sha256}},
        }
        observation = {
            "environment": "resident-android",
            "resident_health": {"boot_id_sha256": "2" * 64},
        }
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            b0.durable_json(
                run_dir / "rollback-download-baseline.json",
                {
                    "schema": "s20plus_g986n_b0_download_baseline_v1",
                    "endpoint_count": 0,
                    "listing_sha256": "3" * 64,
                    "at": "2026-08-31T00:00:00+00:00",
                },
            )
            with mock.patch.object(
                b0, "revalidate_rollback_source", return_value={"fixed": True}
            ), mock.patch.object(
                b0,
                "download_baseline",
                side_effect=b0.B0F1Error("Download baseline is not empty"),
            ), mock.patch.object(
                b0, "adb_reboot_download_capture"
            ) as reboot, mock.patch.object(b0, "wait_download") as wait:
                with self.assertRaisesRegex(b0.B0F1Error, "not empty"):
                    b0.enter_rollback_download(
                        run_dir, prepared, observation, serial
                    )
            self.assertTrue((run_dir / "rollback-download-intent.json").exists())
            self.assertFalse(
                (run_dir / "rollback-download-effect-baseline.json").exists()
            )
            reboot.assert_not_called()
            wait.assert_not_called()


if __name__ == "__main__":
    unittest.main()
