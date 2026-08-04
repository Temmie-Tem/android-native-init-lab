"""Host-only tests for preserved source/work A90 resident installation."""

from __future__ import annotations

import tempfile
import unittest
import datetime as dt
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _loader import load_script


install = load_script(
    "workspace/public/src/scripts/server-distro/"
    "a90_resident_existing_rootfs_install_v1.py"
)


class ExistingRootfsInstallTests(unittest.TestCase):
    def protected_spec(self) -> SimpleNamespace:
        source = (
            "/mnt/sdext/a90/runtime/"
            "debian-bookworm-arm64-phase2-display-v3406-keyed-20260804-02.img"
        )
        stage = (
            "/mnt/sdext/a90/runtime/.a90-stage-"
            "a90-v3406-debian-display-f1-20260804-03"
        )
        return SimpleNamespace(
            manifest={
                "protected_rootfs": {
                    "source": {
                        "device_path": source,
                        "size": install.IMAGE_SIZE,
                        "mode": install.FILE_MODE,
                        "nlink": install.FILE_NLINK,
                        "sha256": "1" * 64,
                        "device_identity": "123:456",
                    },
                    "work": {
                        "device_path": install.WORK_PATH,
                        "size": install.IMAGE_SIZE,
                        "mode": install.FILE_MODE,
                        "nlink": install.FILE_NLINK,
                        "sha256": "2" * 64,
                        "device_identity": "123:789",
                    },
                    "stage_path": stage,
                }
            },
            stage=SimpleNamespace(remote_stage_dir=stage),
        )

    def receipts(
        self,
        *,
        same_identity: bool = False,
        phase: str = "pre-candidate",
    ) -> list[dict]:
        source_identity = "123:456"
        work_identity = source_identity if same_identity else "123:789"
        source = self.protected_spec().manifest["protected_rootfs"]["source"][
            "device_path"
        ]
        commands = install._protected_commands(
            self.protected_spec(), phase=phase
        )
        lines = [
            f"regular file|2147483648|600|1|{source_identity}",
            f"regular file|2147483648|600|1|{work_identity}",
            f"{'1' * 64}  {source}",
            f"{'2' * 64}  {install.WORK_PATH}",
            "stage=absent",
            "mount_namespace_use=none",
            "loop_use=none",
            "open_fd_use=none current_root_use=none",
        ]
        return [
            {
                "command": command,
                "rc": 0,
                "status": "ok",
                "trust": "A90P1_V1_STRUCTURAL_ONLY",
                "begin": {
                    "argc": str(len(command)),
                    "cmd": command[0],
                    "flags": "0x2",
                    "seq": "1",
                },
                "end": {
                    "cmd": command[0],
                    "duration_ms": "1",
                    "errno": "0",
                    "flags": "0x2",
                    "rc": "0",
                    "seq": "1",
                    "status": "ok",
                },
                "text": line + "\n",
                "wire_bytes": install._wire_bytes(command),
            }
            for command, line in zip(commands.values(), lines, strict=True)
        ]

    def test_protected_paths_use_eight_bounded_read_only_frames(self) -> None:
        with mock.patch.object(install, "_remote", side_effect=self.receipts()) as remote:
            result = install.protected_paths_preflight(
                self.protected_spec(),
                SimpleNamespace(),
                phase="pre-candidate",
            )
        self.assertEqual(remote.call_count, 8)
        self.assertTrue(result["source_work_distinct"])
        self.assertEqual(result["staging_attempt_count"], 0)
        self.assertEqual(result["rootfs_copy_count"], 0)
        self.assertEqual(result["cleanup_dispatch_count"], 0)
        self.assertEqual(result["handoff_attempt_count"], 0)
        flattened = repr([call.args[1] for call in remote.call_args_list])
        for forbidden in (" rm ", " cp ", " mv ", " mount ", " switch_root "):
            self.assertNotIn(forbidden, flattened)

    def test_protected_paths_reject_same_device_inode(self) -> None:
        with mock.patch.object(
            install,
            "_remote",
            side_effect=self.receipts(same_identity=True),
        ):
            with self.assertRaisesRegex(install.ContractError, "identity"):
                install.protected_paths_preflight(
                    self.protected_spec(),
                    SimpleNamespace(),
                    phase="pre-candidate",
                )

    def test_remote_rejects_oversized_frame_before_backend(self) -> None:
        with mock.patch.object(
            install.base,
            "run_f1_cmd",
            side_effect=AssertionError("oversized frame reached backend"),
        ):
            with self.assertRaisesRegex(install.ContractError, "bounded cmdv1x frame"):
                install._remote(
                    SimpleNamespace(),
                    ["run", "x" * install.MAX_CMDV1X_WIRE_BYTES],
                    "oversized",
                )

    def test_protected_proof_rejects_changed_bound_inode(self) -> None:
        with mock.patch.object(
            install,
            "_remote",
            side_effect=self.receipts(phase="post-candidate"),
        ):
            proof = install.protected_paths_preflight(
                self.protected_spec(),
                SimpleNamespace(),
                phase="post-candidate",
            )
        proof["work_identity"] = "999:999"
        with self.assertRaisesRegex(install.ContractError, "identities changed"):
            install._validate_protected_proof(
                self.protected_spec(),
                proof,
                phase="post-candidate",
            )

    def test_protected_proof_rejects_malformed_framing_fields(self) -> None:
        with mock.patch.object(
            install,
            "_remote",
            side_effect=self.receipts(),
        ):
            proof = install.protected_paths_preflight(
                self.protected_spec(),
                SimpleNamespace(),
                phase="pre-candidate",
            )
        receipt = proof["receipts"]["source_stat"]
        receipt["begin"].update({"argc": "not-decimal", "seq": "evil", "flags": "bad"})
        receipt["end"].update(
            {"seq": "evil", "duration_ms": "not-decimal", "flags": "other"}
        )
        with self.assertRaisesRegex(install.ContractError, "receipt is not exact"):
            install._validate_protected_proof(
                self.protected_spec(),
                proof,
                phase="pre-candidate",
            )

    def test_success_result_rejects_forged_health(self) -> None:
        spec = self.protected_spec()
        spec.stage.run_id = "a90-v3406-debian-display-f1-20260804-03"
        spec.stage.manifest_sha256 = "a" * 64
        result = {
            "schema": install.RESULT_SCHEMA,
            "run_id": spec.stage.run_id,
            "status": install.SUCCESS_STATUS,
            "manifest_sha256": spec.stage.manifest_sha256,
            "candidate_sha256": install.CANDIDATE_SHA256,
            "candidate_transfer_count": 1,
            "candidate_replay": False,
            "rollback_transfer_count": 0,
            "rollback_required": False,
            "device_safety_state": "RESIDENT_HEALTHY",
            "handoff_eligible": False,
            "staging_attempt_count": 0,
            "rootfs_copy_count": 0,
            "cleanup_dispatch_count": 0,
            "candidate_health_check_count": 1,
            "health": {},
            "protected_paths": {},
            "timeline_events": list(install.INSTALL_EVENTS),
        }
        with self.assertRaisesRegex(install.ContractError, "health keys"):
            install._validate_success_result(spec, result)

    def test_terminal_repair_rejects_closed_only_journal(self) -> None:
        spec = self.protected_spec()
        spec.stage.run_id = "a90-v3406-debian-display-f1-20260804-03"
        spec.stage.manifest_sha256 = "a" * 64
        with self.assertRaisesRegex(install.ContractError, "success sequence"):
            install._validate_success_journal(
                spec,
                Path("/tmp/never-used"),
                [{"action": "closed", "state": install.TERMINAL_STATE}],
            )

    def test_recovery_rejects_duplicate_candidate_intent(self) -> None:
        actions = [
            "preflight",
            "approved",
            "protected-paths-pre-verified",
            "resident-promotion-guard-armed",
            "candidate-transfer-started",
            "candidate-transfer-started",
        ]
        records = [
            {"action": action, "state": "APPROVED"}
            for action in actions
        ]
        with self.assertRaisesRegex(install.ContractError, "intent count"):
            install._validate_recovery_journal(
                self.protected_spec(),
                Path("/tmp/never-used"),
                records,
                closed=False,
            )

    def test_recovery_accepts_crash_after_protected_rollback_proof(self) -> None:
        spec = self.protected_spec()
        spec.candidate = SimpleNamespace(sha256=install.CANDIDATE_SHA256)
        spec.rollback = SimpleNamespace(sha256=install.ROLLBACK_SHA256)
        spec.rollback_version = install.ROLLBACK_VERSION
        spec.rollback_build = install.ROLLBACK_BUILD
        actions = [
            "preflight", "approved", "protected-paths-pre-verified",
            "resident-promotion-guard-armed", "candidate-transfer-started",
            "rollback-transfer-started", "rollback-flashed",
            "rollback-boot-ready", "health-verified",
            "protected-paths-post-rollback-verified",
        ]
        records = [{"action": action, "state": "APPROVED"} for action in actions]
        records[0].update({"device_write": False, "candidate_attempted": False})
        records[1].update(
            {"approval_consumed": True, "rollback_pre_authorized": True}
        )
        records[2].update(
            {
                "staging_attempt_count": 0,
                "rootfs_copy_count": 0,
                "cleanup_dispatch_count": 0,
                "record": {},
            }
        )
        records[3].update(
            {"candidate_attempted": False, "candidate_replay": False}
        )
        records[4].update(
            {
                "candidate_sha256": install.CANDIDATE_SHA256,
                "candidate_transfer_count_max": 1,
                "candidate_replay": False,
                "rollback_required": True,
            }
        )
        records[5].update(
            {
                "state": "RECOVERY_ROLLBACK",
                "rollback_sha256": install.ROLLBACK_SHA256,
                "rollback_attempt_limit": 1,
                "rollback_process_started": None,
                "candidate_replay": False,
                "recovery_mode": "from-native",
            }
        )
        records[6].update(
            {
                "state": "ROLLBACK_FLASHED",
                "rollback_sha256": install.ROLLBACK_SHA256,
                "rollback_transfer_count": 1,
                "candidate_replay": False,
            }
        )
        records[7].update(
            {
                "state": "ROLLBACK_FLASHED",
                "rollback_version": install.ROLLBACK_VERSION,
                "rollback_build": install.ROLLBACK_BUILD,
                "selftest_fail_zero": True,
            }
        )
        records[8]["state"] = "HEALTH_VERIFIED"
        records[9].update(
            {
                "state": "HEALTH_VERIFIED",
                "staging_attempt_count": 0,
                "rootfs_copy_count": 0,
                "cleanup_dispatch_count": 0,
                "record": {},
            }
        )
        with (
            mock.patch.object(install, "_journal_keyset"),
            mock.patch.object(install, "_validate_protected_proof"),
            mock.patch.object(install, "_validate_final_health"),
        ):
            self.assertIsNone(
                install._validate_recovery_journal(
                    spec,
                    Path("/tmp/never-used"),
                    records,
                    closed=False,
                )
            )

    def test_recovery_repairs_result_before_closed_without_device_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            transaction_dir = Path(temporary)
            exact_result = {
                "schema": install.base.ORCHESTRATOR_SCHEMA,
                "run_id": "a90-v3406-debian-display-f1-20260804-04",
            }
            install.base.write_private_json_exclusive(
                transaction_dir / "result.json",
                exact_result,
            )
            spec = SimpleNamespace(
                stage=SimpleNamespace(
                    run_id=exact_result["run_id"],
                    manifest_sha256="a" * 64,
                )
            )
            records = [
                {"action": "candidate-transfer-started"},
                {"action": "protected-paths-post-rollback-verified"},
            ]
            closed_records = [*records, {"action": "closed", "state": "CLOSED"}]
            args = SimpleNamespace(transaction_dir=transaction_dir)
            with (
                mock.patch.object(
                    install.base,
                    "exact_transaction_dir",
                    return_value=transaction_dir,
                ),
                mock.patch.object(
                    install.base,
                    "read_journal",
                    side_effect=[records, closed_records],
                ),
                mock.patch.object(install.base, "approved_bindings", return_value={}),
                mock.patch.object(install.base, "verify_local_closure"),
                mock.patch.object(install.base, "require_consumed_approval"),
                mock.patch.object(install.base, "require_private_regular"),
                mock.patch.object(
                    install,
                    "_validate_recovery_journal",
                    side_effect=[None, exact_result],
                ) as validate_journal,
                mock.patch.object(
                    install,
                    "_validate_rollback_result",
                    return_value=exact_result,
                ),
                mock.patch.object(install.base, "append_record") as append_record,
                mock.patch.object(
                    install.resident,
                    "_next_rollback_guard_corridor",
                    side_effect=AssertionError("close-only repair reached device recovery"),
                ),
            ):
                self.assertEqual(install.recover_or_repair(spec, args), exact_result)
            self.assertEqual(validate_journal.call_count, 2)
            append_record.assert_called_once()
            self.assertEqual(append_record.call_args.args[1:3], ("CLOSED", "closed"))

    def test_execution_closure_rejects_mutated_common_support(self) -> None:
        closure = install._current_execution_closure()
        closure["support_run_d1_chroot_mvp"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(install.ContractError, "size/hash changed"):
            install._execution_bounds(closure)

    def test_connected_d0_rejects_future_path_timestamp(self) -> None:
        now = dt.datetime.now(dt.UTC).replace(microsecond=0)
        connected_time = now + dt.timedelta(seconds=30)
        paths_time = now + dt.timedelta(seconds=31)
        cleanup_time = now - dt.timedelta(seconds=1)
        fmt = lambda value: value.isoformat().replace("+00:00", "Z")
        connected_value = {
            "schema": install.CONNECTED_D0_SCHEMA,
            "timestamp_utc": fmt(connected_time),
            "run_id": "a90-v3406-debian-display-f1-20260804-03",
            "predecessor_run_id": "a90-v3406-debian-display-f1-20260804-02",
            "device_ip": "192.0.2.2",
            "target": {
                "profile": install.staging.TARGET_PROFILE,
                "matching_a90_usb_devices": 1,
                "bridge_device": "by-id",
                "bridge_selected_realpath": "/dev/ttyACM0",
            },
            "host_ncm": {},
            "health": {
                "version": install.ROLLBACK_VERSION,
                "version_build": install.ROLLBACK_BUILD,
                "selftest": {"fail": 0},
                "pstore_entries": 0,
            },
            "artifacts": {
                "candidate_boot": {"sha256": install.CANDIDATE_SHA256},
                "rollback_boot": {"sha256": install.ROLLBACK_SHA256},
            },
            "predecessor_manifest": {},
            "cleanup_result": {},
            "safety": {
                "device_write": False,
                "flash": False,
                "payload_sent": False,
                "reboot_requested": False,
                "rootfs_staged": False,
                "userdata_touched": False,
            },
        }
        paths_value = {
            "schema": install.PATH_PREFLIGHT_SCHEMA,
            "timestamp_utc": fmt(paths_time),
            "run_id": connected_value["run_id"],
            "connected_d0_sha256": "c" * 64,
            "cleanup_result_sha256": "e" * 64,
            "proof": {},
            "safety": {},
        }
        cleanup_value = {"created_utc": fmt(cleanup_time)}
        bounds = [
            install.Bound(Path("/tmp/connected"), 1, "c" * 64),
            install.Bound(Path("/tmp/paths"), 1, "d" * 64),
        ]
        candidate = install.Bound(Path("/tmp/candidate"), 1, install.CANDIDATE_SHA256)
        rollback = install.Bound(Path("/tmp/rollback"), 1, install.ROLLBACK_SHA256)
        cleanup_result = install.Bound(Path("/tmp/cleanup"), 1, "e" * 64)
        with (
            mock.patch.object(install, "_load_bound", side_effect=bounds),
            mock.patch.object(
                install,
                "_read_json",
                side_effect=[connected_value, paths_value, cleanup_value],
            ),
        ):
            with self.assertRaisesRegex(install.ContractError, "fresh exact"):
                install._validate_connected_evidence(
                    {
                        "connected_d0_result": {},
                        "connected_path_preflight": {},
                        "bridge_device": "by-id",
                        "bridge_selected_realpath": "/dev/ttyACM0",
                    },
                    run_id=connected_value["run_id"],
                    candidate=candidate,
                    rollback=rollback,
                    proof_spec=self.protected_spec(),
                    cleanup_result=cleanup_result,
                    require_fresh=True,
                )

    def test_preserved_branch_aborts_without_staging_calls(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_id = "a90-v3406-debian-display-f1-20260804-03"
            run_root = root / run_id
            run_root.mkdir()
            spec = SimpleNamespace(
                manifest={
                    "schema": install.MANIFEST_SCHEMA,
                    "resident_promotion": {
                        "mode": install.MODE,
                        "runner": {},
                    },
                },
                stage=SimpleNamespace(
                    run_id=run_id,
                    manifest_sha256="a" * 64,
                    local_sha256="b" * 64,
                ),
                candidate=SimpleNamespace(sha256="c" * 64),
                rollback=SimpleNamespace(sha256="d" * 64),
                orchestrator_sha256="e" * 64,
            )
            args = SimpleNamespace(
                approval="approval",
                transaction_dir=run_root / "f1-live",
                staging_command_timeout=1.0,
            )
            with (
                mock.patch.object(install.base, "PRIVATE_RUN_BASE", root),
                mock.patch.object(install.base, "approved_bindings", return_value={
                    "approval_binding_sha256": "f" * 64
                }),
                mock.patch.object(install.base, "verify_local_closure"),
                mock.patch.object(install.base, "require_exact_promotion_tail"),
                mock.patch.object(install.staging, "require_exact_bridge"),
                mock.patch.object(install.base, "require_f1_starting_health"),
                mock.patch.object(
                    install,
                    "protected_paths_preflight",
                    side_effect=install.ContractError("preflight stop"),
                ),
                mock.patch.object(install.base, "stage_command") as stage_command,
                mock.patch.object(install.base, "validate_stage_result") as stage_result,
                mock.patch.object(install.base, "run_logged") as run_logged,
            ):
                with self.assertRaisesRegex(install.ContractError, "preflight stop"):
                    install.base.execute_approved_f1(
                        spec,
                        args,
                        promotion_tail=install.promotion_tail,
                    )
            stage_command.assert_not_called()
            stage_result.assert_not_called()
            run_logged.assert_not_called()

    def test_preserved_approval_binding_has_zero_handoff_authority(self) -> None:
        spec = SimpleNamespace(
            manifest={"schema": install.MANIFEST_SCHEMA},
            stage=SimpleNamespace(
                run_id="a90-v3406-debian-display-f1-20260804-05",
                manifest_sha256="1" * 64,
                adapter_sha256="2" * 64,
                local_sha256="3" * 64,
            ),
            flash_runner=SimpleNamespace(sha256="4" * 64),
            candidate=SimpleNamespace(sha256="5" * 64),
            rollback=SimpleNamespace(sha256="6" * 64),
            recovery_serial_sha256="7" * 64,
            observation_mode=install.base.UNATTENDED_OBSERVATION_MODE,
            attended_window_sec=0,
            pre_handoff_attempt_limit=0,
            handoff_attempt_limit=0,
        )
        with mock.patch.object(
            install.base,
            "bound_by_label",
            side_effect=[SimpleNamespace(sha256="8" * 64), SimpleNamespace(sha256="9" * 64)],
        ):
            binding = install.base.approval_binding(spec)
        self.assertEqual(
            binding["schema"],
            "a90_resident_existing_rootfs_approval_binding_v1",
        )
        self.assertEqual(binding["pre_handoff_attempt_limit"], 0)
        self.assertEqual(binding["handoff_attempt_limit"], 0)
        self.assertTrue(binding["rootfs_payload_forbidden"])
        self.assertTrue(binding["handoff_forbidden"])
        for field, invalid in (
            ("attended_window_sec", False),
            ("pre_handoff_attempt_limit", False),
            ("handoff_attempt_limit", False),
            ("handoff_attempt_limit", 1),
        ):
            original = getattr(spec, field)
            setattr(spec, field, invalid)
            with (
                mock.patch.object(
                    install.base,
                    "bound_by_label",
                    side_effect=[
                        SimpleNamespace(sha256="8" * 64),
                        SimpleNamespace(sha256="9" * 64),
                    ],
                ),
                self.assertRaisesRegex(install.base.ContractError, "zero handoff"),
            ):
                install.base.approval_binding(spec)
            setattr(spec, field, original)
        spec.stage.run_id = "bad-run"
        with (
            mock.patch.object(
                install.base,
                "bound_by_label",
                side_effect=[
                    SimpleNamespace(sha256="8" * 64),
                    SimpleNamespace(sha256="9" * 64),
                ],
            ),
            self.assertRaisesRegex(install.base.ContractError, "run_id"),
        ):
            install.base.approval_binding(spec)
        spec.stage.run_id = "a90-v3406-debian-display-f1-20260804-05"
        spec.candidate.sha256 = "bad"
        with (
            mock.patch.object(
                install.base,
                "bound_by_label",
                side_effect=[
                    SimpleNamespace(sha256="8" * 64),
                    SimpleNamespace(sha256="9" * 64),
                ],
            ),
            self.assertRaises(install.staging.ContractError),
        ):
            install.base.approval_binding(spec)

    def test_audit_closes_no_stage_no_handoff_source_contract(self) -> None:
        result = install.audit()
        self.assertTrue(result["ready_for_review"])
        self.assertEqual(result["contract_issues"], [])
        self.assertEqual(result["protected_read_frame_count"], 8)
        self.assertLessEqual(
            result["max_protected_wire_bytes"],
            install.MAX_CMDV1X_WIRE_BYTES,
        )
        source = Path(install.__file__).read_text(encoding="utf-8")
        self.assertIn(install.SUCCESS_STATUS, source)
        self.assertIn('"handoff_eligible": False', source)
        self.assertIn('"staging_attempt_count": 0', source)


if __name__ == "__main__":
    unittest.main()
