"""Host-only tests for the exact A90 H5 published-source install lane."""

from __future__ import annotations

import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _loader import load_script


install = load_script(
    "workspace/public/src/scripts/server-distro/"
    "a90_h5_existing_source_install_v1.py"
)


class Guard:
    def healthy(self, *, recheck: bool) -> bool:
        return recheck


class H5ExistingSourceInstallTests(unittest.TestCase):
    def spec(self) -> SimpleNamespace:
        stage = str(
            install.staging.derive_stage_dir(
                "a90-v3406-debian-display-f1-20991231-99"
            )
        )
        candidate_first_boot = {
            "enable_path": install.H5_ENABLE,
            "latch_path": install.H5_LATCH,
        }
        return SimpleNamespace(
            manifest={
                "protected_rootfs": {
                    "disposition": install.DISPOSITION,
                    "source": {
                        "device_path": install.H5_SOURCE_PATH,
                        "size": install.IMAGE_SIZE,
                        "sha256": install.H5_SOURCE_SHA256,
                        "mode": install.FILE_MODE,
                        "nlink": install.FILE_NLINK,
                        "device_identity": "45825:1054074",
                    },
                    "work_path": install.WORK_PATH,
                    "stage_path": stage,
                    "enable_path": install.H5_ENABLE,
                    "latch_path": install.H5_LATCH,
                }
            },
            stage=SimpleNamespace(
                run_id="a90-v3406-debian-display-f1-20991231-99",
                manifest_sha256="1" * 64,
                remote_stage_dir=stage,
            ),
            candidate=SimpleNamespace(sha256=install.H5_CANDIDATE_SHA256),
            rollback=SimpleNamespace(sha256=install.ROLLBACK_SHA256),
            orchestrator_sha256="6" * 64,
            candidate_first_boot=candidate_first_boot,
        )

    def receipt(self, command: list[str], line: str) -> dict:
        return {
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

    def receipts(self) -> list[dict]:
        commands = install._protected_commands(self.spec())
        lines = {
            "source_stat": (
                f"regular file|{install.IMAGE_SIZE}|{install.FILE_MODE}|"
                f"{install.FILE_NLINK}|45825:1054074"
            ),
            "source_hash": (
                f"{install.H5_SOURCE_SHA256}  {install.H5_SOURCE_PATH}"
            ),
            "absences": "work=absent stage=absent enable=absent latch=absent",
            "mounts": "mount_namespace_use=none",
            "loops": "loop_use=none",
            "opens": "open_fd_use=none current_root_use=none",
        }
        return [
            self.receipt(command, lines[label])
            for label, command in commands.items()
        ]

    def proof(self, phase: str = "pre-candidate") -> dict:
        script = install.base.candidate_first_boot_state_absence_script(
            self.spec().candidate_first_boot
        )
        command = ["run", "/bin/busybox", "sh", "-c", script]
        first_boot_record = self.receipt(
            command,
            "A90AUTO_F1_PRE enable_absent=1 latch_absent=1",
        )
        first_boot_record.pop("wire_bytes")
        first_boot = {
            "proof": True,
            "enable_path": install.H5_ENABLE,
            "latch_path": install.H5_LATCH,
            "record": first_boot_record,
        }
        with (
            mock.patch.object(install, "_remote", side_effect=self.receipts()),
            mock.patch.object(
                install.base,
                "require_candidate_first_boot_state_absent",
                return_value=first_boot,
            ),
        ):
            return install.protected_paths_preflight(
                self.spec(),
                SimpleNamespace(),
                phase=phase,
            )

    def test_audit_closes_every_imported_execution_helper(self) -> None:
        result = install.audit()
        self.assertTrue(result["ready_for_review"])
        self.assertEqual(result["contract_issues"], [])
        self.assertEqual(result["protected_read_frame_count"], 7)
        self.assertLessEqual(result["max_protected_wire_bytes"], 3800)
        self.assertIn("preserved_recovery_helpers", result["review_closure"])
        self.assertFalse(result["rootfs_staged"])
        self.assertFalse(result["flash"])

    def test_protected_preflight_is_seven_bounded_reads_only(self) -> None:
        proof = self.proof()
        self.assertEqual(proof["source_identity"], "45825:1054074")
        self.assertEqual(proof["staging_attempt_count"], 0)
        self.assertEqual(proof["rootfs_copy_count"], 0)
        self.assertEqual(proof["cleanup_dispatch_count"], 0)
        self.assertEqual(proof["handoff_attempt_count"], 0)
        flattened = repr(install._protected_commands(self.spec()))
        for forbidden in (" rm ", " cp ", " mv ", " mount ", "switch-root"):
            self.assertNotIn(forbidden, flattened)

    def test_proof_rejects_identity_and_effect_counter_drift(self) -> None:
        proof = self.proof()
        for field, replacement in (
            ("source_identity", "45825:1054075"),
            ("staging_attempt_count", 1),
            ("rootfs_copy_count", 1),
            ("handoff_attempt_count", 1),
        ):
            changed = dict(proof)
            changed[field] = replacement
            with self.subTest(field=field), self.assertRaises(install.ContractError):
                install._validate_proof(
                    self.spec(),
                    changed,
                    phase="pre-candidate",
                )

    def test_embedded_bound_passes_only_path_size_and_hash(self) -> None:
        value = {
            "path": "/private/candidate.img",
            "size": 1,
            "sha256": "1" * 64,
            "partition": "boot",
        }
        expected = install.Bound(Path(value["path"]), 1, "1" * 64)
        with mock.patch.object(install, "_load_bound", return_value=expected) as load:
            self.assertEqual(
                install._load_embedded_bound(value, "candidate"),
                expected,
            )
        self.assertEqual(
            load.call_args.args[0],
            {"path": value["path"], "size": 1, "sha256": "1" * 64},
        )

    def test_promotion_manifest_is_source_only_and_authority_free(self) -> None:
        runner = install._bound_dict(
            install._bound(Path(install.__file__).resolve(), private=False)
        )
        spec = SimpleNamespace(
            manifest={
                "resident_promotion": {
                    "mode": install.MODE,
                    "runner": runner,
                    "rootfs_preflight_disposition": install.DISPOSITION,
                    "success_terminal": install.resident.INSTALL_STATUS,
                    "candidate_health_checks": 1,
                    "rollback_on_post_attempt_failure": True,
                    "handoff_eligible": True,
                    "staging_attempt_count": 0,
                    "rootfs_copy_count": 0,
                    "cleanup_dispatch_count": 0,
                }
            }
        )
        result = install.validate_promotion_manifest(spec)
        self.assertEqual(result["runner"], runner)
        self.assertEqual(result["mode"], install.MODE)

    def test_common_approval_binding_accepts_both_d0_labels(self) -> None:
        d0 = install.staging.BoundFile(
            "target.connected_d0_result",
            Path("/private/d0.json"),
            1,
            "1" * 64,
        )
        paths = install.staging.BoundFile(
            "target.connected_path_preflight",
            Path("/private/d0.json"),
            1,
            "1" * 64,
        )
        spec = SimpleNamespace(
            manifest={"schema": install.MANIFEST_SCHEMA},
            stage=SimpleNamespace(
                run_id="a90-v3406-debian-display-f1-20991231-99",
                manifest_sha256="2" * 64,
                adapter_sha256="3" * 64,
                local_sha256=install.H5_SOURCE_SHA256,
                bound_files=(d0, paths),
            ),
            flash_runner=SimpleNamespace(sha256="4" * 64),
            candidate=SimpleNamespace(sha256=install.H5_CANDIDATE_SHA256),
            rollback=SimpleNamespace(sha256=install.ROLLBACK_SHA256),
            recovery_serial_sha256="5" * 64,
            observation_mode=install.base.UNATTENDED_OBSERVATION_MODE,
            attended_window_sec=0,
            pre_handoff_attempt_limit=0,
            handoff_attempt_limit=0,
        )
        binding = install.base.approval_binding(spec)
        self.assertEqual(
            binding["schema"],
            "a90_resident_existing_rootfs_approval_binding_v1",
        )
        self.assertEqual(binding["connected_d0_sha256"], "1" * 64)
        self.assertEqual(binding["connected_path_preflight_sha256"], "1" * 64)
        with (
            mock.patch.object(install.base, "verify_local_closure"),
            mock.patch.object(install.base, "write_private_json_exclusive") as write,
        ):
            prepared = install.base.prepare_approval(spec)
        write.assert_called_once()
        self.assertFalse(prepared["f1_authorized"])
        self.assertFalse(prepared["live_authorized"])

    def installed_spec(self) -> SimpleNamespace:
        spec = self.spec()
        spec.manifest.update(
            schema=install.MANIFEST_SCHEMA,
            resident_promotion={"mode": install.MODE},
        )
        return spec

    def installed_result(self, spec: SimpleNamespace) -> dict:
        return {
            "schema": install.resident.INSTALL_RESULT_SCHEMA,
            "run_id": spec.stage.run_id,
            "status": install.resident.INSTALL_STATUS,
            "manifest_sha256": spec.stage.manifest_sha256,
            "candidate_sha256": spec.candidate.sha256,
            "candidate_transfer_count": 1,
            "candidate_replay": False,
            "resident_reboot_count": 0,
            "candidate_health_check_count": 1,
            "rollback_transfer_count": 0,
            "rollback_required": False,
            "device_safety_state": "RESIDENT_HEALTHY",
            "first_health": {"native": {}},
            "timeline_events": list(install.resident.INSTALL_EVENTS),
        }

    def success_records(self, spec: SimpleNamespace) -> list[dict]:
        records = []
        for sequence, (action, state) in enumerate(
            zip(install.SUCCESS_ACTIONS, install.SUCCESS_STATES, strict=True)
        ):
            records.append(
                {
                    "schema": install.base.JOURNAL_SCHEMA,
                    "sequence": sequence,
                    "timestamp_utc": "2099-12-31T00:00:00Z",
                    "run_id": spec.stage.run_id,
                    "manifest_sha256": spec.stage.manifest_sha256,
                    "state": state,
                    "action": action,
                }
            )
        records[0].update(
            device_write=False,
            candidate_attempted=False,
            candidate_sha256=spec.candidate.sha256,
            rollback_sha256=spec.rollback.sha256,
            rootfs_sha256=install.H5_SOURCE_SHA256,
        )
        records[1].update(
            approval_consumed=True,
            candidate_attempted=False,
            rollback_pre_authorized=True,
            approval_token_sha256="7" * 64,
            approval_binding_sha256="8" * 64,
            orchestrator_sha256=spec.orchestrator_sha256,
        )
        records[2].update(
            candidate_attempted=False,
            staging_attempt_count=0,
            rootfs_copy_count=0,
            cleanup_dispatch_count=0,
            record={},
        )
        records[3].update(
            candidate_attempted=False,
            candidate_replay=False,
            guard={},
        )
        records[4].update(
            candidate_attempted=True,
            candidate_sha256=spec.candidate.sha256,
            candidate_transfer_count_max=1,
            rollback_required=True,
            candidate_replay=False,
        )
        records[5].update(
            candidate_sha256=spec.candidate.sha256,
            candidate_transfer_count=1,
            candidate_replay=False,
            rollback_required=True,
            record={},
        )
        records[6].update(
            candidate_version=install.H5_VERSION,
            candidate_build=install.H5_BUILD,
            selftest_fail_zero=True,
            channel={},
            health={},
            candidate_first_boot_health={"proof": True},
        )
        records[7].update(
            candidate_health_check_count=1,
            native_exact={"native": True},
            health={"exact": True},
        )
        records[8].update(
            handoff_eligible=True,
            staging_attempt_count=0,
            rootfs_copy_count=0,
            cleanup_dispatch_count=0,
            record={},
        )
        result = self.installed_result(spec)
        records[9].update(
            {
                key: value
                for key, value in result.items()
                if key not in {"schema", "run_id", "manifest_sha256"}
            }
        )
        return records

    def test_custom_installed_result_accepts_only_preserved_lane(self) -> None:
        spec = self.installed_spec()
        result = self.installed_result(spec)
        with mock.patch.object(install.resident, "_validate_installed_health"):
            self.assertEqual(install._validate_installed_result(spec, result), result)
            changed = dict(result)
            changed["candidate_replay"] = True
            with self.assertRaisesRegex(install.ContractError, "installed result"):
                install._validate_installed_result(spec, changed)

    def test_terminal_missing_result_is_republished_without_device_effect(self) -> None:
        spec = self.installed_spec()
        result = self.installed_result(spec)
        records = self.success_records(spec)
        with tempfile.TemporaryDirectory(
            dir=install.staging.PRIVATE_ROOT
        ) as temp_dir:
            transaction = Path(temp_dir)

            def publish(_spec, path, value):
                self.assertEqual(value, result)
                output = path / "result.json"
                output.write_text("{}\n", encoding="utf-8")
                output.chmod(0o600)

            proof = {
                "source_identity": "45825:1054074",
                "candidate_first_boot_preflight": {},
            }
            with (
                mock.patch.object(install.base, "read_journal", return_value=records),
                mock.patch.object(install, "_validate_proof", return_value=proof),
                mock.patch.object(
                    install.resident,
                    "_require_exact_native_health",
                    return_value={"native": True},
                ),
                mock.patch.object(
                    install.resident,
                    "_validate_installed_health",
                    return_value={"native": {}},
                ),
                mock.patch.object(
                    install,
                    "_installed_result_from_terminal",
                    return_value=result,
                ),
                mock.patch.object(
                    install.resident,
                    "_validate_candidate_first_boot_journal",
                ),
                mock.patch.object(install.base, "resident_promotion_guard_inputs"),
                mock.patch.object(
                    install,
                    "_publish_exact_installed_result",
                    side_effect=publish,
                ) as publisher,
                mock.patch.object(install, "_read_json", return_value=result),
            ):
                repaired = install._validate_success_journal(
                    spec,
                    transaction,
                    repair_missing_result=True,
                )
        self.assertEqual(repaired, result)
        publisher.assert_called_once()

    def test_success_rejects_started_flashed_or_post_tampering(self) -> None:
        spec = self.installed_spec()
        result = self.installed_result(spec)
        mutations = (
            (4, "candidate_replay", True),
            (5, "candidate_transfer_count", 2),
            (8, "handoff_eligible", False),
        )
        for index, field, replacement in mutations:
            records = self.success_records(spec)
            records[index][field] = replacement
            with tempfile.TemporaryDirectory(
                dir=install.staging.PRIVATE_ROOT
            ) as temp_dir:
                output = Path(temp_dir) / "result.json"
                output.write_text("{}\n", encoding="utf-8")
                output.chmod(0o600)
                proof = {
                    "source_identity": "45825:1054074",
                    "candidate_first_boot_preflight": {},
                }
                with (
                    self.subTest(field=field),
                    mock.patch.object(
                        install.base,
                        "read_journal",
                        return_value=records,
                    ),
                    mock.patch.object(install, "_validate_proof", return_value=proof),
                    mock.patch.object(
                        install.resident,
                        "_require_exact_native_health",
                        return_value={"native": True},
                    ),
                    mock.patch.object(
                        install.resident,
                        "_validate_installed_health",
                        return_value={"native": {}},
                    ),
                    mock.patch.object(
                        install,
                        "_installed_result_from_terminal",
                        return_value=result,
                    ),
                    mock.patch.object(
                        install.resident,
                        "_validate_candidate_first_boot_journal",
                    ),
                    mock.patch.object(
                        install.base,
                        "resident_promotion_guard_inputs",
                    ),
                    mock.patch.object(install, "_read_json", return_value=result),
                ):
                    with self.assertRaises(install.ContractError):
                        install._validate_success_journal(spec, Path(temp_dir))

    def test_recovery_journal_rejects_candidate_replay(self) -> None:
        records = [
            {"action": "preflight"},
            {"action": "approved"},
            {
                "action": "protected-paths-pre-verified",
                "staging_attempt_count": 0,
                "rootfs_copy_count": 0,
                "cleanup_dispatch_count": 0,
                "record": {},
            },
            {"action": "resident-promotion-guard-armed"},
            {
                "action": "candidate-transfer-started",
                "candidate_sha256": install.H5_CANDIDATE_SHA256,
                "candidate_transfer_count_max": 1,
                "candidate_replay": False,
                "rollback_required": True,
            },
            {"action": "candidate-flashed"},
            {"action": "candidate-flashed"},
        ]
        with mock.patch.object(
            install,
            "_validate_proof",
            return_value={"source_identity": "45825:1054074"},
        ):
            with self.assertRaisesRegex(install.ContractError, "candidate|prefix"):
                install._validate_recovery_journal(
                    self.spec(),
                    Path("/private/transaction"),
                    records,
                    closed=False,
                )

    def test_recovery_rejects_started_flashed_or_post_tampering(self) -> None:
        spec = self.installed_spec()
        cases = (
            (5, 4, "candidate_replay", True),
            (6, 5, "candidate_transfer_count", 2),
            (9, 8, "handoff_eligible", False),
        )
        for length, index, field, replacement in cases:
            records = self.success_records(spec)[:length]
            records[index][field] = replacement
            proof = {
                "source_identity": "45825:1054074",
                "candidate_first_boot_preflight": {},
            }
            with (
                self.subTest(field=field),
                mock.patch.object(install, "_validate_proof", return_value=proof),
                mock.patch.object(
                    install.base,
                    "resident_promotion_guard_inputs",
                ),
                mock.patch.object(
                    install.resident,
                    "_require_exact_native_health",
                    return_value={"native": True},
                ),
                mock.patch.object(
                    install.resident,
                    "_validate_installed_health",
                    return_value={"native": {}},
                ),
                mock.patch.object(
                    install.resident,
                    "_validate_candidate_first_boot_journal",
                ),
            ):
                with self.assertRaises(install.ContractError):
                    install._validate_recovery_journal(
                        spec,
                        Path("/private/transaction"),
                        records,
                        closed=False,
                    )

    def test_recovery_rejects_candidate_state_tampering(self) -> None:
        spec = self.installed_spec()
        for length, index in ((5, 4), (6, 5), (9, 8)):
            records = self.success_records(spec)[:length]
            records[index]["state"] = "TAMPERED"
            with self.subTest(action=records[index]["action"]):
                with self.assertRaisesRegex(install.ContractError, "state|prefix"):
                    install._validate_recovery_journal(
                        spec,
                        Path("/private/transaction"),
                        records,
                        closed=False,
                    )

    def test_recovery_rejects_post_rollback_state_tampering(self) -> None:
        spec = self.installed_spec()
        records = self.success_records(spec)[:5]
        tail = (
            ("RECOVERY_ROLLBACK", "rollback-transfer-started"),
            ("ROLLBACK_FLASHED", "rollback-flashed"),
            ("ROLLBACK_FLASHED", "rollback-boot-ready"),
            ("HEALTH_VERIFIED", "health-verified"),
            ("TAMPERED", "protected-paths-post-rollback-verified"),
        )
        for state, action in tail:
            sequence = len(records)
            records.append(
                {
                    "schema": install.base.JOURNAL_SCHEMA,
                    "sequence": sequence,
                    "timestamp_utc": "2099-12-31T00:00:00Z",
                    "run_id": spec.stage.run_id,
                    "manifest_sha256": spec.stage.manifest_sha256,
                    "state": state,
                    "action": action,
                }
            )
        with (
            mock.patch.object(install, "_journal_keyset"),
            mock.patch.object(install.base, "resident_promotion_guard_inputs"),
            mock.patch.object(
                install,
                "_validate_proof",
                return_value={"source_identity": "45825:1054074"},
            ),
        ):
            with self.assertRaisesRegex(install.ContractError, "state"):
                install._validate_recovery_journal(
                    spec,
                    Path("/private/transaction"),
                    records,
                    closed=False,
                )

    def test_recovery_arms_guard_and_never_routes_candidate(self) -> None:
        spec = self.spec()
        records = [
            {"action": "preflight"},
            {"action": "approved"},
            {"action": "protected-paths-pre-verified"},
            {"action": "resident-promotion-guard-armed"},
            {"action": "candidate-transfer-started"},
        ]
        args = SimpleNamespace(transaction_dir=Path("/private/transaction"))
        guard = Guard()
        release = {"released": True}

        def recover(_spec, _args, *, return_guard, before_close):
            self.assertIs(return_guard, guard)
            before_close()
            return {"status": "recovered"}

        with (
            mock.patch.object(
                install.base,
                "exact_transaction_dir",
                return_value=args.transaction_dir,
            ),
            mock.patch.object(install.base, "read_journal", return_value=records),
            mock.patch.object(install.base, "approved_bindings", return_value={}),
            mock.patch.object(install.base, "verify_local_closure"),
            mock.patch.object(install.base, "require_consumed_approval"),
            mock.patch.object(
                install,
                "_validate_recovery_journal",
                side_effect=[None, {"status": "recovered"}],
            ),
            mock.patch.object(
                install.resident,
                "_next_rollback_guard_corridor",
                return_value="rollback-recovery-1",
            ),
            mock.patch.object(
                install.base,
                "resident_promotion_guard_inputs",
                return_value=({"guard": "spec"}, "topology"),
            ),
            mock.patch.object(
                install.base,
                "arm_candidate_return_modemmanager_guard",
                return_value=guard,
            ) as arm,
            mock.patch.object(install.base, "modemmanager_guard_arm_evidence"),
            mock.patch.object(
                install,
                "protected_paths_preflight",
                return_value={"source_identity": "45825:1054074"},
            ),
            mock.patch.object(install.base, "append_record"),
            mock.patch.object(
                install.base,
                "release_candidate_return_modemmanager_guard",
                return_value=release,
            ) as release_guard,
            mock.patch.object(
                install.base,
                "recover_approved_rollback",
                side_effect=recover,
            ) as rollback,
        ):
            result = install.recover_or_repair(spec, args)
        self.assertEqual(result, {"status": "recovered"})
        arm.assert_called_once()
        rollback.assert_called_once()
        release_guard.assert_called_once()

    def test_unknown_run_id_is_rejected_before_d0(self) -> None:
        args = SimpleNamespace(
            run_id="s22plus-not-a90",
            evidence_sequence="01",
        )
        with self.assertRaisesRegex(install.ContractError, "run ID"):
            install.execute_connected_d0(args)


if __name__ == "__main__":
    unittest.main()
