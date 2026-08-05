from __future__ import annotations

import hashlib
import importlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _loader import load_script


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    REPO_ROOT
    / "workspace/public/src/scripts/server-distro/a90_resident_promotion_v1.py"
)
promotion = load_script(SOURCE)
base = promotion.base
fast = __import__("a90_resident_fast_handoff_v1")


class Guard:
    def __init__(self, health: tuple[bool, ...] = ()) -> None:
        self.released = False
        self.health = list(health)

    def healthy(self, *, recheck: bool) -> bool:
        return self.health.pop(0) if self.health else recheck

    def release(self):
        self.released = True
        return {"released": True}


class ResidentPromotionV1Tests(unittest.TestCase):
    def write_json(self, root: Path, name: str, value: dict) -> dict:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
        path.chmod(0o600)
        return {
            "path": str(path),
            "size": path.stat().st_size,
            "sha256": promotion.base.sha256_file(path),
        }

    def rewrite_bound(self, bound: dict, value: dict) -> None:
        path = Path(bound["path"])
        path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
        bound["size"] = path.stat().st_size
        bound["sha256"] = base.sha256_file(path)

    def journal_bound(self, spec, action: str) -> dict:
        prior = spec.manifest["resident_promotion"]["prior_closed_run"]
        return next(
            item
            for item in prior["journal"]
            if Path(item["path"]).name.endswith(f"-{action}.json")
        )

    def fixture(self, root: Path):
        prior_run_id = "a90-v3406-debian-display-f1-20260801-99"
        candidate_sha = "1" * 64
        rollback_sha = "2" * 64
        rootfs_sha = "3" * 64
        materialization = self.write_json(
            root,
            "keyed-rootfs-summary.json",
            {"schema": "a90-phase2d-keyed-rootfs-v1"},
        )
        prior_manifest_value = {
            "schema": base.staging.FINAL_MANIFEST_SCHEMA,
            "status": base.staging.FINAL_MANIFEST_STATUS,
            "run_id": prior_run_id,
            "candidate_boot": {
                "partition": "boot",
                "sha256": candidate_sha,
                "expected_version": "0.10.0",
                "expected_build": "candidate-build",
            },
            "rollback_boot": {
                "partition": "boot",
                "sha256": rollback_sha,
                "expected_version": "0.9.285",
                "expected_build": "v2321",
            },
            "target": {
                "profile": base.staging.TARGET_PROFILE,
                "bridge_device": "/dev/serial/by-id/fake-a90",
                "bridge_selected_realpath": "/dev/ttyACM0",
                "bridge_selected_exact": True,
                "connected_d0_result": {
                    "outcome": "PASS",
                    "path": "/private/connected.json",
                    "size": 1,
                    "sha256": "4" * 64,
                },
                "connected_path_preflight": {
                    "handoff_work_path_absent": True,
                    "keyed_source_path_absent": True,
                    "path": "/private/paths.json",
                    "run_stage_path_absent": True,
                    "size": 1,
                    "sha256": "5" * 64,
                },
                "recovery_adb_serial_sha256": "6" * 64,
            },
            "f1_orchestrator": {
                "sha256": "7" * 64,
                "candidate_attempt_limit": 1,
                "rollback_attempt_limit": 1,
                "candidate_route_in_recovery": False,
            },
            "rootfs_staging": {"adapter": {"sha256": "8" * 64}},
            "transport": {
                "runner_sha256": "9" * 64,
                "only_partition_payload": "boot",
                "forbidden_partition_writes": True,
            },
            "debian_rootfs": {
                "keyed_source": {
                    "size": fast.EXPECTED_IMAGE_BYTES,
                    "sha256": rootfs_sha,
                    "materialization": materialization,
                }
            },
            "observation": {
                "mode": base.UNATTENDED_OBSERVATION_MODE,
                "attended_window_sec": 0,
                "pre_handoff_attempt_limit": 1,
                "handoff_attempt_limit": 1,
            },
        }
        prior_manifest = self.write_json(
            root,
            "prior/prepared-manifest.json",
            prior_manifest_value,
        )
        manifest_sha = prior_manifest["sha256"]
        approval_binding = base.staging.canonical_f1_approval_binding(
            run_id=prior_run_id,
            manifest_sha256=manifest_sha,
            orchestrator_sha256="7" * 64,
            staging_adapter_sha256="8" * 64,
            flash_runner_sha256="9" * 64,
            candidate_boot_sha256=candidate_sha,
            rollback_boot_sha256=rollback_sha,
            rootfs_sha256=rootfs_sha,
            connected_d0_sha256="4" * 64,
            connected_path_preflight_sha256="5" * 64,
            recovery_adb_serial_sha256="6" * 64,
            observation_mode=base.UNATTENDED_OBSERVATION_MODE,
            attended_window_sec=0,
            pre_handoff_attempt_limit=1,
            handoff_attempt_limit=1,
        )
        approval_binding_sha = base.json_sha256(approval_binding)
        approval_token = base.APPROVAL_PREFIX + approval_binding_sha
        approval = self.write_json(
            root,
            "prior/approval-prepared.json",
            {
                "schema": base.APPROVAL_PREPARED_SCHEMA,
                "created_utc": "2026-08-01T00:00:00Z",
                "run_id": prior_run_id,
                "manifest_sha256": manifest_sha,
                "approval_binding": approval_binding,
                "approval_binding_sha256": approval_binding_sha,
                "approval_token": approval_token,
                "device_contact": False,
                "device_write": False,
                "f1_authorized": False,
                "live_authorized": False,
            },
        )
        actions = (
            "preflight",
            "approved",
            "staging-started",
            "rootfs-staged",
            "rootfs-candidate-preflight",
            "candidate-transfer-started",
            "candidate-flashed",
            "candidate-boot-ready",
            "observation-no-proof",
            "rollback-transfer-started",
            "rollback-flashed",
            "rollback-boot-ready",
            "health-verified",
            "closed",
        )
        states = {
            "preflight": "PREFLIGHT",
            "approved": "APPROVED",
            "staging-started": "APPROVED",
            "rootfs-staged": "APPROVED",
            "rootfs-candidate-preflight": "APPROVED",
            "candidate-transfer-started": "APPROVED",
            "candidate-flashed": "CANDIDATE_FLASHED",
            "candidate-boot-ready": "CANDIDATE_FLASHED",
            "observation-no-proof": "OBSERVED",
            "rollback-transfer-started": "RECOVERY_ROLLBACK",
            "rollback-flashed": "ROLLBACK_FLASHED",
            "rollback-boot-ready": "ROLLBACK_FLASHED",
            "health-verified": "HEALTH_VERIFIED",
            "closed": "CLOSED",
        }
        result_value = {
            "schema": base.ORCHESTRATOR_SCHEMA,
            "run_id": prior_run_id,
            "status": "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK",
            "manifest_sha256": manifest_sha,
            "candidate_transfer_count": 1,
            "candidate_transfer_uncertain": False,
            "candidate_replay": False,
            "debian_pid1_proven": False,
            "display_acquisition_proven": False,
            "rollback_transfer_count": 1,
            "final_health_restored": True,
            "timeline_events": list(base.CANONICAL_EVENTS),
        }
        journal = []
        for sequence, action in enumerate(actions):
            record = {
                "schema": base.JOURNAL_SCHEMA,
                "sequence": sequence,
                "timestamp_utc": "2026-08-01T00:00:00Z",
                "run_id": prior_run_id,
                "manifest_sha256": manifest_sha,
                "state": states[action],
                "action": action,
            }
            if action == "approved":
                record.update(
                    approval_consumed=True,
                    rollback_pre_authorized=True,
                    approval_binding_sha256=approval_binding_sha,
                    approval_token_sha256=hashlib.sha256(
                        approval_token.encode("utf-8")
                    ).hexdigest(),
                )
            elif action == "candidate-transfer-started":
                record["candidate_sha256"] = candidate_sha
            elif action == "candidate-flashed":
                record.update(
                    candidate_sha256=candidate_sha,
                    candidate_transfer_count=1,
                    candidate_replay=False,
                )
            elif action == "candidate-boot-ready":
                record.update(
                    candidate_version="0.10.0",
                    candidate_build="candidate-build",
                    selftest_fail_zero=True,
                    health={
                        "exact_bridge": True,
                        "selected_realpath": "/dev/ttyACM0",
                        "version": {
                            "command": ["version"],
                            "rc": 0,
                            "status": "ok",
                            "text": (
                                "version: 0.10.0 "
                                "build=candidate-build\r\n"
                            ),
                        },
                        "selftest": {
                            "command": ["selftest"],
                            "rc": 0,
                            "status": "ok",
                            "text": (
                                "selftest: pass=12 warn=1 fail=0 "
                                "duration=47ms entries=13\r\n"
                            ),
                        },
                    },
                )
            elif action == "rollback-transfer-started":
                record["rollback_sha256"] = rollback_sha
            elif action == "rollback-flashed":
                record.update(
                    rollback_sha256=rollback_sha,
                    rollback_transfer_count=1,
                    candidate_replay=False,
                )
            elif action == "rollback-boot-ready":
                record.update(
                    rollback_version="0.9.285",
                    rollback_build="v2321",
                    selftest_fail_zero=True,
                )
            elif action == "health-verified":
                record.update(
                    version="0.9.285",
                    build="v2321",
                    selftest_fail_zero=True,
                    pstore_entries_zero=True,
                    exact_bridge=True,
                    selected_realpath="/dev/ttyACM0",
                    baseline={
                        "version": {
                            "command": ["version"],
                            "rc": 0,
                            "status": "ok",
                            "text": "version: 0.9.285 build=v2321\r\n",
                        },
                        "selftest": {
                            "command": ["selftest"],
                            "rc": 0,
                            "status": "ok",
                            "text": (
                                "selftest: pass=11 warn=1 fail=0 "
                                "duration=48ms entries=12\r\n"
                            ),
                        },
                    },
                )
            elif action == "closed":
                record.update(
                    {
                        key: value
                        for key, value in result_value.items()
                        if key
                        not in {"schema", "run_id", "manifest_sha256"}
                    }
                )
            journal.append(
                self.write_json(
                    root,
                    f"prior/journal/{sequence:04d}-{action}.json",
                    record,
                )
            )
        result = self.write_json(root, "prior/result.json", result_value)
        timeline = self.write_json(
            root,
            "prior/timeline.json",
            {
                "events": [
                    {"name": name, "timestamp_utc": "2026-08-01T00:00:00Z"}
                    for name in base.CANONICAL_EVENTS
                ]
            },
        )
        receipt = self.write_json(
            root,
            "debian-ab-receipt.json",
            {"schema": fast.AB_SCHEMA},
        )
        runner = {
            "path": str(SOURCE),
            "size": SOURCE.stat().st_size,
            "sha256": base.sha256_file(SOURCE),
        }
        qualification_helper = {
            "path": str(promotion.QUALIFICATION_HELPER_PATH),
            "size": promotion.QUALIFICATION_HELPER_PATH.stat().st_size,
            "sha256": base.sha256_file(promotion.QUALIFICATION_HELPER_PATH),
        }
        resident = {
            "mode": promotion.MODE,
            "runner": runner,
            "qualification_helper": qualification_helper,
            "rootfs_preflight_disposition": "absent",
            "resident_reboot_command": ["reboot"],
            "resident_reboot_timeout_sec": 240,
            "candidate_health_checks": 2,
            "rollback_on_post_attempt_failure": True,
            "prior_closed_run": {
                "run_id": prior_run_id,
                "manifest": prior_manifest,
                "approval_prepared": approval,
                "result": result,
                "timeline": timeline,
                "journal": journal,
            },
            "debian_ab_receipt": receipt,
        }
        spec = SimpleNamespace(
            manifest={
                "schema": promotion.staging.RESIDENT_PROMOTION_MANIFEST_SCHEMA,
                "resident_promotion": resident,
                "debian_rootfs": prior_manifest_value["debian_rootfs"],
            },
            candidate=SimpleNamespace(sha256=candidate_sha),
            rollback=SimpleNamespace(sha256=rollback_sha),
            candidate_version="0.10.0",
            candidate_build="candidate-build",
            candidate_return_timeout=240,
            observation_mode=base.UNATTENDED_OBSERVATION_MODE,
            display_required=False,
            rollback_version="0.9.285",
            rollback_build="v2321",
            recovery_serial_sha256="6" * 64,
            stage=SimpleNamespace(
                local_size=fast.EXPECTED_IMAGE_BYTES,
                local_sha256=rootfs_sha,
                bridge_device="/dev/serial/by-id/fake-a90",
                bridge_realpath="/dev/ttyACM0",
                bound_files=(
                    promotion.staging.BoundFile(
                        label="debian_rootfs.keyed_source.materialization",
                        path=Path(materialization["path"]),
                        size=materialization["size"],
                        sha256=materialization["sha256"],
                    ),
                ),
            ),
        )
        return spec

    def ab_result(self) -> dict:
        return {
            "slots": {
                slot: {
                    "image": {
                        "bytes": fast.EXPECTED_IMAGE_BYTES,
                        "sha256": fast.EXPECTED_IMAGE_SHA256,
                    }
                }
                for slot in ("A", "B")
            },
            "image_byte_identical": True,
            "presenter_byte_identical": True,
            "source_unchanged": True,
            "base_unchanged": True,
        }

    def validate(self, spec, *, recovery: bool = False):
        runtime_fast = importlib.import_module("a90_resident_fast_handoff_v1")
        with mock.patch.object(
            runtime_fast,
            "validate_ab_receipt",
            return_value=self.ab_result(),
        ) as validator:
            result = promotion.validate_promotion_manifest(
                spec,
                recovery=recovery,
            )
        if not recovery:
            validator.assert_called_once()
        return result

    def install_fixture(self, root: Path):
        spec = self.fixture(root)
        resident = spec.manifest["resident_promotion"]
        spec.manifest["schema"] = promotion.staging.RESIDENT_INSTALL_MANIFEST_SCHEMA
        resident["mode"] = promotion.INSTALL_MODE
        resident.pop("resident_reboot_command")
        resident.pop("resident_reboot_timeout_sec")
        resident["candidate_health_checks"] = 1
        resident["success_terminal"] = promotion.INSTALL_STATUS
        return spec

    def test_exact_manifest_proves_prior_run_and_debian_receipt(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "workspace/private") as tmp:
            value = self.validate(self.fixture(Path(tmp)))
        self.assertEqual(value["mode"], promotion.MODE)
        self.assertEqual(value["prior_closed_run"]["candidate_transfer_count"], 1)
        self.assertEqual(value["prior_closed_run"]["rollback_transfer_count"], 1)
        self.assertTrue(value["debian_ab_receipt"]["deterministic_ab"])
        self.assertNotEqual(
            value["debian_ab_receipt"]["rootfs_sha256"],
            value["debian_ab_receipt"]["clean_rootfs_sha256"],
        )

    def test_prior_capability_qualification_is_reused_across_candidates(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "workspace/private") as tmp:
            spec = self.fixture(Path(tmp))
            spec.candidate.sha256 = "a" * 64
            spec.candidate_version = "0.11.168"
            spec.candidate_build = "phase3-minimal-g-server-core"
            value = self.validate(spec)
        self.assertEqual(
            value["prior_closed_run"]["candidate_native_exact"]["version_line"],
            "version: 0.10.0 build=candidate-build",
        )

    def test_prior_capability_survives_current_acm_realpath_change(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "workspace/private") as tmp:
            spec = self.fixture(Path(tmp))
            spec.stage.bridge_realpath = "/dev/ttyACM1"
            value = self.validate(spec)
        self.assertTrue(
            value["prior_closed_run"]["final_v2321_health_verified"]
        )

    def test_prior_health_must_match_its_historical_acm_realpath(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "workspace/private") as tmp:
            spec = self.fixture(Path(tmp))
            bound = self.journal_bound(spec, "candidate-boot-ready")
            candidate_health = json.loads(
                Path(bound["path"]).read_text(encoding="utf-8")
            )
            candidate_health["health"]["selected_realpath"] = "/dev/ttyACM9"
            self.rewrite_bound(bound, candidate_health)
            with self.assertRaisesRegex(
                promotion.ContractError,
                "candidate native health is not exact",
            ):
                self.validate(spec)

    def test_install_manifest_selects_one_health_check_and_exact_terminal(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "workspace/private") as tmp:
            value = self.validate(self.install_fixture(Path(tmp)))
        self.assertEqual(value["mode"], promotion.INSTALL_MODE)
        self.assertEqual(value["candidate_health_checks"], 1)
        self.assertEqual(value["success_terminal"], promotion.INSTALL_STATUS)
        self.assertNotIn("resident_reboot_command", value)

    def test_install_manifest_rejects_legacy_reboot_field(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "workspace/private") as tmp:
            spec = self.install_fixture(Path(tmp))
            spec.manifest["resident_promotion"]["resident_reboot_command"] = [
                "reboot"
            ]
            with self.assertRaisesRegex(promotion.ContractError, "key set"):
                self.validate(spec)

    def test_first_boot_journal_accepts_repeated_exact_unarmed_states(self) -> None:
        candidate_build = "phase3-minimal-h4-observer-complete-auto-benchmark"
        first_boot = {
            "enable_path": "/cache/a90-auto-handoff-h4.enable",
            "latch_path": "/cache/a90-auto-handoff-h4.done",
        }
        spec = SimpleNamespace(
            candidate_build=candidate_build,
            candidate_first_boot=first_boot,
        )

        def exact_receipt(command: list[str], text: str, seq: str) -> dict:
            flags = "0x0"
            return {
                "command": command,
                "rc": 0,
                "status": "ok",
                "trust": "A90P1_V1_STRUCTURAL_ONLY",
                "begin": {
                    "argc": str(len(command)),
                    "cmd": command[0],
                    "flags": flags,
                    "seq": seq,
                },
                "end": {
                    "cmd": command[0],
                    "duration_ms": "1",
                    "errno": "0",
                    "flags": flags,
                    "rc": "0",
                    "seq": seq,
                    "status": "ok",
                },
                "text": text,
            }

        preflight_script = base.candidate_first_boot_state_absence_script(
            first_boot
        )
        preflight_record = exact_receipt(
            ["run", "/bin/busybox", "sh", "-c", preflight_script],
            "A90AUTO_F1_PRE enable_absent=1 latch_absent=1\r\n",
            "1",
        )
        status_record = exact_receipt(
            ["auto-handoff-status"],
            (
                "A90AUTO_STATUS binding=1 enable=0 latch=0 "
                f"build={candidate_build}\r\n"
            ),
            "2",
        )
        log_record = exact_receipt(
            ["logcat"],
            (
                "old: A90AUTO state=unarmed-stay-native\r\n"
                "new: A90AUTO state=unarmed-stay-native\r\n"
            ),
            "3",
        )
        by_action = {
            "rootfs-candidate-preflight": {
                "candidate_first_boot_preflight": {
                    "proof": True,
                    "enable_path": first_boot["enable_path"],
                    "latch_path": first_boot["latch_path"],
                    "record": preflight_record,
                }
            },
            "candidate-boot-ready": {
                "candidate_first_boot_health": {
                    "proof": True,
                    "status": status_record,
                    "log": log_record,
                    "enable": 0,
                    "latch": 0,
                    "unarmed_log_unique": True,
                }
            },
        }
        promotion._validate_candidate_first_boot_journal(spec, by_action)
        log_record["text"] += "A90AUTO state=dispatch-once\r\n"
        with self.assertRaisesRegex(
            promotion.ContractError,
            "first resident boot proof changed",
        ):
            promotion._validate_candidate_first_boot_journal(spec, by_action)

    def test_install_manifest_rejects_schema_mode_mismatch(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "workspace/private") as tmp:
            spec = self.install_fixture(Path(tmp))
            spec.manifest["schema"] = promotion.staging.RESIDENT_PROMOTION_MANIFEST_SCHEMA
            with self.assertRaisesRegex(promotion.ContractError, "execution contract"):
                self.validate(spec)

    def test_clean_unkeyed_image_is_rejected_as_resident_input(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "workspace/private") as tmp:
            spec = self.fixture(Path(tmp))
            spec.stage.local_sha256 = fast.EXPECTED_IMAGE_SHA256
            spec.manifest["debian_rootfs"]["keyed_source"]["sha256"] = (
                fast.EXPECTED_IMAGE_SHA256
            )
            with self.assertRaisesRegex(
                promotion.ContractError,
                "fresh keyed rootfs",
            ):
                self.validate(spec)

    def test_keyed_materialization_must_remain_in_bound_closure(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "workspace/private") as tmp:
            spec = self.fixture(Path(tmp))
            spec.stage.bound_files = ()
            with self.assertRaisesRegex(
                base.ContractError,
                "bound closure",
            ):
                self.validate(spec)

    def test_prior_candidate_evidence_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "workspace/private") as tmp:
            spec = self.fixture(Path(tmp))
            bound = self.journal_bound(spec, "candidate-boot-ready")
            value = json.loads(Path(bound["path"]).read_text(encoding="utf-8"))
            value["candidate_version"] = "0.10.1"
            self.rewrite_bound(bound, value)
            with self.assertRaisesRegex(
                promotion.ContractError,
                "artifact identity or health",
            ):
                self.validate(spec)

    def test_prior_target_identity_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "workspace/private") as tmp:
            spec = self.fixture(Path(tmp))
            spec.recovery_serial_sha256 = "f" * 64
            with self.assertRaises(promotion.ContractError):
                self.validate(spec)

    def test_duplicate_prior_candidate_transfer_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "workspace/private") as tmp:
            spec = self.fixture(Path(tmp))
            prior = spec.manifest["resident_promotion"]["prior_closed_run"]
            duplicate = dict(self.journal_bound(spec, "candidate-transfer-started"))
            path = Path(duplicate["path"])
            value = json.loads(path.read_text(encoding="utf-8"))
            value["sequence"] = len(prior["journal"])
            duplicate = self.write_json(
                Path(tmp),
                f"prior/journal/{value['sequence']:04d}-candidate-transfer-started.json",
                value,
            )
            prior["journal"].append(duplicate)
            with self.assertRaisesRegex(
                promotion.ContractError,
                "contiguous and exact|state order|one candidate",
            ):
                self.validate(spec)

    def test_forged_prior_state_result_and_final_health_are_rejected(self) -> None:
        mutations = (
            ("state", "candidate-flashed", lambda value: value.update(state="TEST")),
            (
                "result",
                None,
                lambda value: value.update(
                    status="PASS_F1_V2_DEBIAN_PID1_PROVEN_AND_ROLLED_BACK"
                ),
            ),
            (
                "final-health",
                "health-verified",
                lambda value: value.update(pstore_entries_zero=False),
            ),
        )
        for label, action, mutate in mutations:
            with self.subTest(label=label), tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "workspace/private"
            ) as tmp:
                spec = self.fixture(Path(tmp))
                prior = spec.manifest["resident_promotion"]["prior_closed_run"]
                bound = prior["result"] if action is None else self.journal_bound(spec, action)
                value = json.loads(Path(bound["path"]).read_text(encoding="utf-8"))
                mutate(value)
                self.rewrite_bound(bound, value)
                with self.assertRaises(promotion.ContractError):
                    self.validate(spec)

    def test_recovery_does_not_reopen_auxiliary_eligibility_evidence(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "workspace/private") as tmp:
            spec = self.fixture(Path(tmp))
            resident = spec.manifest["resident_promotion"]
            prior = resident["prior_closed_run"]
            for binding in (
                prior["manifest"],
                prior["approval_prepared"],
                prior["result"],
                prior["timeline"],
                *prior["journal"],
                resident["debian_ab_receipt"],
            ):
                Path(binding["path"]).unlink()
            value = self.validate(spec, recovery=True)
            self.assertFalse(value["auxiliary_evidence_reopened"])
            with self.assertRaises(promotion.ContractError):
                self.validate(spec)

    def test_base_runner_refuses_promotion_without_exact_tail(self) -> None:
        spec = SimpleNamespace(manifest={"resident_promotion": {}})
        with self.assertRaisesRegex(
            base.ContractError,
            "requires its exact promotion runner",
        ):
            base.execute_approved_f1(spec, SimpleNamespace())

    def test_base_runner_rejects_arbitrary_tail(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "workspace/private") as tmp:
            spec = self.fixture(Path(tmp))
            with self.assertRaisesRegex(base.ContractError, "callback identity"):
                base.execute_approved_f1(
                    spec,
                    SimpleNamespace(),
                    promotion_tail=lambda *args: {},
                )

    def test_exact_tail_cannot_bypass_manifest_validator(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "workspace/private") as tmp:
            spec = self.fixture(Path(tmp))
            bound = self.journal_bound(spec, "candidate-flashed")
            value = json.loads(Path(bound["path"]).read_text(encoding="utf-8"))
            value["state"] = "TEST"
            self.rewrite_bound(bound, value)
            with (
                mock.patch.object(
                    fast,
                    "validate_ab_receipt",
                    return_value=self.ab_result(),
                ),
                mock.patch.object(base, "approved_bindings") as approved,
                self.assertRaisesRegex(base.ContractError, "contiguous and exact"),
            ):
                base.execute_approved_f1(
                    spec,
                    SimpleNamespace(),
                    promotion_tail=promotion.promotion_tail,
                )
            approved.assert_not_called()

    def initial_events(self, transaction_dir: Path) -> list[dict[str, str]]:
        events: list[dict[str, str]] = []
        for name in base.PROMOTION_EVENTS[:4]:
            base.add_event(
                transaction_dir,
                events,
                name,
                allow_promotion=True,
            )
        return events

    def tail_spec(self, *, install: bool = False):
        mode = promotion.INSTALL_MODE if install else promotion.MODE
        schema = (
            promotion.staging.RESIDENT_INSTALL_MANIFEST_SCHEMA
            if install
            else promotion.staging.RESIDENT_PROMOTION_MANIFEST_SCHEMA
        )
        return SimpleNamespace(
            manifest={"schema": schema, "resident_promotion": {"mode": mode}},
            candidate=SimpleNamespace(sha256="1" * 64),
            candidate_version="0.10.0",
            candidate_build="candidate-build",
            candidate_return_timeout=240,
            observer_host_ncm_profile="a90-usb-local",
            stage=SimpleNamespace(
                run_id="a90-promotion-test",
                manifest_sha256="a" * 64,
                bridge_realpath="/dev/ttyACM0",
                remote_final="/mnt/sdext/a90/runtime/exact-keyed.img",
                remote_work="/mnt/sdext/a90/runtime/d3-handoff-work.img",
                local_size=2147483648,
                local_sha256="3" * 64,
            ),
        )

    def native_health(self, spec, *, with_epoch: bool = False) -> dict:
        result = {
            "exact_bridge": True,
            "selected_realpath": spec.stage.bridge_realpath,
            "version": {
                "command": ["version"],
                "rc": 0,
                "status": "ok",
                "text": (
                    f"version: {spec.candidate_version} "
                    f"build={spec.candidate_build}\r\n"
                ),
            },
            "selftest": {
                "command": ["selftest"],
                "rc": 0,
                "status": "ok",
                "text": (
                    "selftest: pass=12 warn=1 fail=0 duration=47ms "
                    "entries=13\r\n"
                ),
            },
        }
        if with_epoch:
            result["return_epoch"] = {"returned": {"epoch": 2}}
        return result

    def command_receipt(self, command: list[str], text: str = "") -> dict:
        return {
            "command": command,
            "rc": 0,
            "status": "ok",
            "trust": "framed",
            "begin": {},
            "end": {},
            "text": text,
        }

    def host_receipt(self, stdout: str = "") -> dict:
        return {
            "command": ["host-check"],
            "returncode": 0,
            "stdout": stdout,
            "stderr": "",
        }

    def installed_health(self, spec) -> dict:
        return {
            "native": self.native_health(spec),
            "pstore": {
                "mounted_read_only": True,
                "entries": [],
                "classification": "empty",
                "warning": False,
                "unexpected_entries": [],
                "mount": self.command_receipt(
                    ["mountfs", "pstore", base.PSTORE_MOUNT_PATH, "pstore", "ro"]
                ),
                "listing": self.command_receipt(["ls", base.PSTORE_MOUNT_PATH]),
                "summary": self.command_receipt(["pstore", "full"]),
                "unmount": self.command_receipt(["umount", base.PSTORE_MOUNT_PATH]),
            },
            "rootfs": self.command_receipt(
                [
                    "run",
                    "/bin/busybox",
                    "sh",
                    "-c",
                    base.remote_source_preflight_script(spec),
                ],
                "A90F1_SOURCE_PRECHECK exact=1 work_absent=1\r\n",
            ),
            "ncm": {
                "same_current_acm_usb_parent": True,
                "exact_interface_count": 1,
                "profile_bound": True,
                "mutated": False,
                "profile_check": self.host_receipt(
                    base.HOST_NCM_CONNECTION_TYPE + "\n"
                ),
                "active_before": self.host_receipt(
                    spec.observer_host_ncm_profile + "\n"
                ),
                "ready": {
                    "verified_a90_ncm": True,
                    "direct_route": True,
                    "host_cidr_present": True,
                    "device_ping": True,
                },
            },
        }

    def test_install_health_accepts_expected_boot_pstore_records(self) -> None:
        spec = self.tail_spec(install=True)
        health = self.installed_health(spec)
        pstore = health["pstore"]
        pstore["entries"] = ["pmsg-ramoops-0", "console-ramoops-0"]
        pstore["classification"] = "expected-boot-records"
        pstore["warning"] = True
        pstore["listing"]["text"] = (
            "- 17870 pmsg-ramoops-0\r\n"
            "- 65062 console-ramoops-0\r\n"
        )
        self.assertEqual(
            promotion._validate_installed_health(spec, health),
            health,
        )

    def test_install_health_preserves_exact_legacy_empty_pstore(self) -> None:
        spec = self.tail_spec(install=True)
        health = self.installed_health(spec)
        pstore = health["pstore"]
        for key in ("classification", "warning", "unexpected_entries"):
            pstore.pop(key)
        self.assertEqual(
            promotion._validate_installed_health(spec, health),
            health,
        )
        pstore["entries"] = ["pmsg-ramoops-0"]
        pstore["listing"]["text"] = "- 12 pmsg-ramoops-0\n"
        with self.assertRaisesRegex(
            promotion.ContractError,
            "pstore health is not exact",
        ):
            promotion._validate_installed_health(spec, health)

    def append_install_prefix(self, spec, journal_dir: Path) -> dict:
        first_health = self.installed_health(spec)
        native_exact = promotion._require_exact_native_health(
            spec,
            first_health["native"],
        )
        payloads = {
            "candidate-transfer-started": {
                "candidate_sha256": spec.candidate.sha256,
                "candidate_transfer_count_max": 1,
                "candidate_replay": False,
                "rollback_required": True,
            },
            "candidate-flashed": {
                "candidate_sha256": spec.candidate.sha256,
                "candidate_transfer_count": 1,
                "candidate_replay": False,
                "rollback_required": True,
            },
            "candidate-boot-ready": {
                "candidate_version": spec.candidate_version,
                "candidate_build": spec.candidate_build,
                "selftest_fail_zero": True,
                "health": first_health["native"],
            },
            "candidate-health-verified": {
                "candidate_health_check_count": 1,
                "native_exact": native_exact,
                "health": first_health,
            },
        }
        for action, state in zip(
            promotion.INSTALL_SUCCESS_ACTIONS[:-1],
            promotion.INSTALL_SUCCESS_STATES[:-1],
            strict=True,
        ):
            base.append_record(
                journal_dir,
                state,
                action,
                payloads.get(action, {}),
                manifest_sha256=spec.stage.manifest_sha256,
                run_id=spec.stage.run_id,
            )
        return first_health

    def test_success_tail_closes_without_rollback(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "workspace/private") as tmp:
            transaction_dir = Path(tmp)
            journal_dir = transaction_dir / "journal"
            events = self.initial_events(transaction_dir)
            guard = Guard()
            spec = self.tail_spec()
            with (
                mock.patch.object(
                    promotion,
                    "_promotion_health",
                    side_effect=({"health": 1}, {"health": 2}),
                ),
                mock.patch.object(base, "settle_observation_channel", return_value={"ok": True}),
                mock.patch.object(base, "capture_bridge_serial_epoch", return_value={"epoch": 1}),
                mock.patch.object(base, "arm_candidate_return_modemmanager_guard") as arm,
                mock.patch.object(promotion, "_dispatch_resident_reboot", return_value={"accepted": True}),
                mock.patch.object(
                    base,
                    "_verify_candidate_after_return_epoch_once",
                    return_value=self.native_health(spec, with_epoch=True),
                ),
                mock.patch.object(
                    base,
                    "require_returned_modemmanager_guard",
                    return_value={"exact": True},
                ),
                mock.patch.object(
                    base,
                    "release_candidate_return_modemmanager_guard",
                    return_value={"released": True},
                ),
            ):
                result = promotion.promotion_tail(
                    spec,
                    SimpleNamespace(),
                    transaction_dir,
                    journal_dir,
                    events,
                    self.native_health(spec),
                    guard,
                )
            arm.assert_not_called()
            records = sorted(journal_dir.glob("*.json"))
            actions = [json.loads(path.read_text())["action"] for path in records]
        self.assertEqual(result["status"], "PASS_A90_F1_RP_RESIDENT_PROMOTED")
        self.assertEqual(result["rollback_transfer_count"], 0)
        self.assertEqual(tuple(result["timeline_events"]), base.PROMOTION_EVENTS)
        self.assertEqual(actions.count("resident-reboot-intent"), 1)
        self.assertEqual(actions.count("resident-reboot-dispatched"), 1)
        self.assertEqual(actions.count("closed"), 1)

    def test_install_tail_closes_after_first_health_without_reboot(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "workspace/private") as tmp:
            transaction_dir = Path(tmp)
            journal_dir = transaction_dir / "journal"
            events = self.initial_events(transaction_dir)
            guard = Guard()
            spec = self.tail_spec(install=True)
            with (
                mock.patch.object(
                    promotion,
                    "_promotion_health",
                    return_value=self.installed_health(spec),
                ) as health,
                mock.patch.object(base, "settle_observation_channel") as settle,
                mock.patch.object(promotion, "_dispatch_resident_reboot") as reboot,
                mock.patch.object(
                    base,
                    "release_candidate_return_modemmanager_guard",
                    return_value={"released": True},
                ),
            ):
                result = promotion.promotion_tail(
                    spec,
                    SimpleNamespace(),
                    transaction_dir,
                    journal_dir,
                    events,
                    self.native_health(spec),
                    guard,
                )
            actions = [
                json.loads(path.read_text())["action"]
                for path in sorted(journal_dir.glob("*.json"))
            ]
        health.assert_called_once()
        settle.assert_not_called()
        reboot.assert_not_called()
        self.assertEqual(result["status"], promotion.INSTALL_STATUS)
        self.assertEqual(result["device_safety_state"], "RESIDENT_HEALTHY")
        self.assertEqual(result["resident_reboot_count"], 0)
        self.assertEqual(result["candidate_health_check_count"], 1)
        self.assertEqual(tuple(result["timeline_events"]), promotion.INSTALL_EVENTS)
        self.assertEqual(actions.count("resident-health-verified"), 0)
        self.assertEqual(actions.count("closed"), 1)

    def test_install_health_failure_does_not_publish_success(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "workspace/private") as tmp:
            transaction_dir = Path(tmp)
            journal_dir = transaction_dir / "journal"
            events = self.initial_events(transaction_dir)
            guard = Guard()
            spec = self.tail_spec(install=True)
            with (
                mock.patch.object(
                    promotion,
                    "_promotion_health",
                    side_effect=promotion.ContractError("health failed"),
                ),
                mock.patch.object(
                    base,
                    "release_candidate_return_modemmanager_guard",
                    side_effect=lambda selected, *_args, **_kwargs: selected.release(),
                ),
                self.assertRaisesRegex(promotion.ContractError, "health failed"),
            ):
                promotion.promotion_tail(
                    spec,
                    SimpleNamespace(),
                    transaction_dir,
                    journal_dir,
                    events,
                    self.native_health(spec),
                    guard,
                )
            self.assertTrue(guard.released)
            self.assertFalse((transaction_dir / "result.json").exists())
            self.assertFalse(list(journal_dir.glob("*.json")))

    def test_install_terminal_journal_repairs_result_publication_fault(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "workspace/private") as tmp:
            transaction_dir = Path(tmp)
            journal_dir = transaction_dir / "journal"
            events = self.initial_events(transaction_dir)
            spec = self.tail_spec(install=True)
            original = base.write_private_json_exclusive
            first_health = self.append_install_prefix(spec, journal_dir)

            def result_fault(path, value):
                if path.name == "result.json":
                    raise OSError("fault after install terminal")
                return original(path, value)

            with (
                mock.patch.object(
                    base,
                    "write_private_json_exclusive",
                    side_effect=result_fault,
                ),
                self.assertRaisesRegex(OSError, "after install terminal"),
            ):
                promotion.close_installed_transaction(
                    spec,
                    transaction_dir,
                    journal_dir,
                    events,
                    first_health=first_health,
                )
            records = base.read_journal(spec, transaction_dir)
            self.assertEqual(records[-1]["state"], promotion.INSTALL_TERMINAL_STATE)
            self.assertFalse((transaction_dir / "result.json").exists())
            repaired = promotion.repair_installed_result(
                spec,
                transaction_dir,
                records,
            )
            repeated = promotion.repair_installed_result(
                spec,
                transaction_dir,
                records,
            )
        self.assertEqual(repaired, repeated)
        self.assertEqual(repaired["status"], promotion.INSTALL_STATUS)

    def test_install_terminal_recovery_repairs_only_and_never_rolls_back(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "workspace/private") as tmp:
            transaction_dir = Path(tmp)
            journal_dir = transaction_dir / "journal"
            spec = self.tail_spec(install=True)
            first_health = self.append_install_prefix(spec, journal_dir)
            promotion.close_installed_transaction(
                spec,
                transaction_dir,
                journal_dir,
                self.initial_events(transaction_dir),
                first_health=first_health,
            )
            args = SimpleNamespace(transaction_dir=transaction_dir)
            with (
                mock.patch.object(
                    base,
                    "exact_transaction_dir",
                    return_value=transaction_dir,
                ),
                mock.patch.object(base, "approved_bindings", return_value={}),
                mock.patch.object(base, "verify_local_closure"),
                mock.patch.object(base, "require_consumed_approval"),
                mock.patch.object(base, "recover_approved_rollback") as rollback,
            ):
                result = promotion.recover_promotion_or_rollback(spec, args)
        rollback.assert_not_called()
        self.assertEqual(result["status"], promotion.INSTALL_STATUS)

    def test_install_repair_rejects_malformed_terminal_or_prior_sequence(self) -> None:
        def forge_rootfs_echo(records):
            forged = [
                "run",
                "/bin/busybox",
                "sh",
                "-c",
                "echo A90F1_SOURCE_PRECHECK exact=1 work_absent=1",
            ]
            records[-2]["health"]["rootfs"]["command"] = forged
            records[-1]["first_health"]["rootfs"]["command"] = forged

        mutations = {
            "boolean-count": lambda records: records[-1].update(
                candidate_transfer_count=True
            ),
            "empty-health": lambda records: records[-1].update(first_health={}),
            "terminal-only": lambda records: records.__setitem__(
                slice(None),
                records[-1:],
            ),
            "missing-health-record": lambda records: records.pop(-2),
            "rollback-action": lambda records: records[7].update(
                action="rollback-flashed"
            ),
            "forged-rootfs-echo": forge_rootfs_echo,
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory(
                dir=REPO_ROOT / "workspace/private"
            ) as tmp:
                transaction_dir = Path(tmp)
                journal_dir = transaction_dir / "journal"
                spec = self.tail_spec(install=True)
                first_health = self.append_install_prefix(spec, journal_dir)
                promotion.close_installed_transaction(
                    spec,
                    transaction_dir,
                    journal_dir,
                    self.initial_events(transaction_dir),
                    first_health=first_health,
                )
                records = base.read_journal(spec, transaction_dir)
                (transaction_dir / "result.json").unlink()
                mutate(records)
                with self.assertRaises(promotion.ContractError):
                    promotion.repair_installed_result(
                        spec,
                        transaction_dir,
                        records,
                    )

    def test_terminal_journal_repairs_result_publication_fault(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "workspace/private") as tmp:
            transaction_dir = Path(tmp)
            journal_dir = transaction_dir / "journal"
            events = self.initial_events(transaction_dir)
            for name in base.PROMOTION_EVENTS[4:-1]:
                base.add_event(
                    transaction_dir,
                    events,
                    name,
                    allow_promotion=True,
                )
            spec = self.tail_spec()
            original = base.write_private_json_exclusive

            def result_fault(path, value):
                if path.name == "result.json":
                    raise OSError("fault after terminal journal")
                return original(path, value)

            with (
                mock.patch.object(
                    base,
                    "write_private_json_exclusive",
                    side_effect=result_fault,
                ),
                self.assertRaisesRegex(OSError, "after terminal journal"),
            ):
                promotion.close_promoted_transaction(
                    spec,
                    transaction_dir,
                    journal_dir,
                    events,
                    first_health={"first": True},
                    second_health={"second": True},
                )
            records = base.read_journal(spec, transaction_dir)
            self.assertEqual(records[-1]["state"], "PROMOTED_CLOSED")
            self.assertFalse((transaction_dir / "result.json").exists())
            repaired = promotion.repair_promoted_result(
                spec,
                transaction_dir,
                records,
            )
            repeated = promotion.repair_promoted_result(
                spec,
                transaction_dir,
                records,
            )
        self.assertEqual(repaired, repeated)
        self.assertEqual(repaired["status"], "PASS_A90_F1_RP_RESIDENT_PROMOTED")

    def test_dispatch_failure_leaves_rollback_authority_open(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "workspace/private") as tmp:
            transaction_dir = Path(tmp)
            journal_dir = transaction_dir / "journal"
            events = self.initial_events(transaction_dir)
            guard = Guard()
            spec = self.tail_spec()
            with (
                mock.patch.object(promotion, "_promotion_health", return_value={"health": 1}),
                mock.patch.object(base, "settle_observation_channel", return_value={"ok": True}),
                mock.patch.object(base, "capture_bridge_serial_epoch", return_value={"epoch": 1}),
                mock.patch.object(base, "arm_candidate_return_modemmanager_guard") as arm,
                mock.patch.object(
                    promotion,
                    "_dispatch_resident_reboot",
                    side_effect=promotion.ContractError("no marker"),
                ),
            ):
                with self.assertRaisesRegex(promotion.ContractError, "no marker"):
                    promotion.promotion_tail(
                        spec,
                        SimpleNamespace(),
                        transaction_dir,
                        journal_dir,
                        events,
                        self.native_health(spec),
                        guard,
                    )
            arm.assert_not_called()
            actions = [
                json.loads(path.read_text())["action"]
                for path in sorted(journal_dir.glob("*.json"))
            ]
        self.assertTrue(guard.released)
        self.assertIn("resident-reboot-intent", actions)
        self.assertNotIn("closed", actions)
        self.assertNotIn("resident-health-verified", actions)

    def test_guard_loss_after_second_health_prevents_promotion(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "workspace/private") as tmp:
            transaction_dir = Path(tmp)
            journal_dir = transaction_dir / "journal"
            events = self.initial_events(transaction_dir)
            guard = Guard((True, True, False))
            spec = self.tail_spec()
            with (
                mock.patch.object(
                    promotion,
                    "_promotion_health",
                    side_effect=({"health": 1}, {"health": 2}),
                ),
                mock.patch.object(base, "settle_observation_channel", return_value={}),
                mock.patch.object(base, "capture_bridge_serial_epoch", return_value={}),
                mock.patch.object(
                    base,
                    "arm_candidate_return_modemmanager_guard",
                ) as arm,
                mock.patch.object(promotion, "_dispatch_resident_reboot", return_value={}),
                mock.patch.object(
                    base,
                    "_verify_candidate_after_return_epoch_once",
                    return_value=self.native_health(spec, with_epoch=True),
                ),
                self.assertRaisesRegex(
                    promotion.ContractError,
                    "lost after health checks",
                ),
            ):
                promotion.promotion_tail(
                    spec,
                    SimpleNamespace(),
                    transaction_dir,
                    journal_dir,
                    events,
                    self.native_health(spec),
                    guard,
                )
            arm.assert_not_called()
            actions = [
                json.loads(path.read_text())["action"]
                for path in sorted(journal_dir.glob("*.json"))
            ]
        self.assertTrue(guard.released)
        self.assertNotIn("resident-health-verified", actions)
        self.assertNotIn("closed", actions)

    def test_first_native_health_requires_exact_lines(self) -> None:
        spec = self.tail_spec()
        health = self.native_health(spec)
        health["version"]["text"] += "version: forged build=forged\n"
        with self.assertRaisesRegex(promotion.ContractError, "not exact"):
            promotion._require_exact_native_health(spec, health)

    def test_ordinary_timeline_refuses_promotion_event(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "workspace/private") as tmp:
            events: list[dict[str, str]] = []
            for name in base.PROMOTION_EVENTS[:4]:
                base.add_event(Path(tmp), events, name)
            with self.assertRaisesRegex(base.ContractError, "non-canonical"):
                base.add_event(Path(tmp), events, "resident_reboot_start")

    def test_recovery_refuses_promoted_closed_transaction(self) -> None:
        spec = self.tail_spec()
        args = SimpleNamespace(transaction_dir=Path("unused"))
        records = [
            {"action": "candidate-transfer-started"},
            {"action": "closed", "state": "PROMOTED_CLOSED"},
        ]
        with (
            mock.patch.object(base, "approved_bindings", return_value={}),
            mock.patch.object(base, "verify_local_closure"),
            mock.patch.object(base, "exact_transaction_dir", return_value=Path("unused")),
            mock.patch.object(base, "read_journal", return_value=records),
            self.assertRaisesRegex(base.ContractError, "already closed"),
        ):
            base.recover_approved_rollback(spec, args)

    def test_rollback_recovery_guard_rearm_is_bounded_and_exact(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "workspace/private") as tmp:
            transaction = Path(tmp)
            guard_spec = {
                "kind": base.cdc_guard.KIND,
                "usb_vendor_id": "04e8",
                "usb_product_id": "6861",
                "usb_serial": "a90-test-serial",
                "usb_driver": "cdc_acm",
                "usb_interface_number": "02",
                "banner_hex": "00",
            }

            def arm_value(corridor: str, instance: str) -> dict:
                return {
                    "schema": base.MODEMMANAGER_GUARD_ARM_SCHEMA,
                    "corridor": corridor,
                    "max_sec": 600,
                    "child_pid": os.getpid(),
                    "guard_spec": guard_spec,
                    "topology": "usb:1-2.3",
                    "receipt": {
                        "schema": base.cdc_guard.GUARD_SCHEMA,
                        "status": "armed",
                        "spec_sha256": base.cdc_guard.digest(guard_spec),
                        "topology_sha256": hashlib.sha256(b"1-2.3").hexdigest(),
                        "rule_sha256": "3" * 64,
                        "instance_sha256": instance,
                        "output_sha256": "5" * 64,
                        "child_alive": True,
                    },
                }

            def release_value(instance: str) -> dict:
                return {
                    "schema": base.cdc_guard.GUARD_SCHEMA,
                    "status": "released",
                    "instance_sha256": instance,
                    "returncode": 0,
                    "released": True,
                }

            self.assertEqual(
                promotion._next_rollback_guard_corridor(transaction),
                "rollback-recovery-1",
            )
            first_instance = "1" * 64
            first_arm = transaction / "rollback-recovery-1-modemmanager-guard-arm.json"
            base.write_private_json_exclusive(
                first_arm,
                arm_value("rollback-recovery-1", first_instance),
            )
            with self.assertRaisesRegex(promotion.ContractError, "still active"):
                promotion._next_rollback_guard_corridor(transaction)
            interrupted = arm_value("rollback-recovery-1", first_instance)
            interrupted["child_pid"] = 99999999
            base.write_private_json_atomic(
                first_arm,
                interrupted,
            )
            base.write_private_json_exclusive(
                transaction
                / "rollback-recovery-1-modemmanager-guard-release-failed.json",
                {
                    "schema": base.cdc_guard.GUARD_SCHEMA,
                    "status": "guard-exited-uncommanded",
                    "instance_sha256": first_instance,
                    "returncode": base.cdc_guard.GUARD_UNCOMMANDED_EXIT,
                    "released": False,
                },
            )
            runtime_rule = transaction / "runtime-guard.rules"
            runtime_rule.write_text("stale\n", encoding="utf-8")
            with (
                mock.patch.object(
                    base.cdc_guard,
                    "GUARD_RUNTIME_RULE_PATH",
                    runtime_rule,
                ),
                mock.patch.object(
                    promotion,
                    "GUARD_CRASH_CLEANUP_WAIT_SEC",
                    0.0,
                ),
                self.assertRaisesRegex(promotion.ContractError, "still present"),
            ):
                promotion._next_rollback_guard_corridor(transaction)
            runtime_rule.unlink()
            with mock.patch.object(
                base.cdc_guard,
                "GUARD_RUNTIME_RULE_PATH",
                runtime_rule,
            ):
                self.assertEqual(
                    promotion._next_rollback_guard_corridor(transaction),
                    "rollback-recovery-2",
                )
            second_instance = "2" * 64
            base.write_private_json_exclusive(
                transaction / "rollback-recovery-2-modemmanager-guard-arm.json",
                arm_value("rollback-recovery-2", second_instance),
            )
            base.write_private_json_exclusive(
                transaction
                / "rollback-recovery-2-modemmanager-guard-release.json",
                release_value(second_instance),
            )
            with mock.patch.object(
                base.cdc_guard,
                "GUARD_RUNTIME_RULE_PATH",
                runtime_rule,
            ):
                with self.assertRaisesRegex(promotion.ContractError, "exhausted"):
                    promotion._next_rollback_guard_corridor(transaction)

    def test_source_reuses_base_transfer_and_recovery(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        self.assertNotIn("import subprocess", source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("dd if=", source)
        self.assertIn("base.execute_approved_f1(", source)
        self.assertIn("base.recover_approved_rollback(", source)
        self.assertIn("return_guard=guard", source)
        self.assertIn("promotion_tail=promotion_tail", source)
        self.assertIn("RESIDENT_PROMOTION_MANIFEST_SCHEMA", source)


if __name__ == "__main__":
    unittest.main()
