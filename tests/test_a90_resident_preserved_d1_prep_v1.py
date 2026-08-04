"""Focused host tests for preserved-work cleanup and D1 reduction."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_DIR = REPO_ROOT / "workspace/public/src/scripts/server-distro"
REVAL_DIR = REPO_ROOT / "workspace/public/src/scripts/revalidation"
for path in (SERVER_DIR, REVAL_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import a90_resident_preserved_d1_prep_v1 as prep  # noqa: E402
import a90_transition_d1_session_v1 as d1  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_file(path: Path, body: bytes = b"x") -> prep.Bound:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    path.chmod(0o600)
    return prep.Bound(path.resolve(), len(body), digest(path))


class PreservedD1PrepTests(unittest.TestCase):
    def resident(self, root: Path) -> prep.ResidentEvidence:
        manifest = write_file(root / "resident-manifest.json", b"resident")
        result = write_file(root / "resident-result.json", b"result")
        journal = (write_file(root / "resident-terminal.json", b"journal"),)
        candidate = write_file(root / "candidate.img", b"candidate")
        rollback = write_file(root / "rollback.img", b"rollback")
        source = write_file(root / "source.img", b"source")
        work = write_file(root / "work.img", b"work")
        key = write_file(root / "observer-key", b"key")
        public_key = write_file(root / "observer-key.pub", b"public-key")
        spec = SimpleNamespace(
            stage=SimpleNamespace(
                bridge_device="/dev/serial/by-id/usb-A90-LNX_TEST-if00",
                bridge_realpath="/dev/ttyACM0",
                remote_final="/mnt/sdext/a90/runtime/source.img",
                remote_stage_dir="/mnt/sdext/a90/runtime/.a90-stage-test",
            )
        )
        value = {
            "protected_rootfs": {
                "source": {
                    "device_path": spec.stage.remote_final,
                    "sha256": source.sha256,
                },
                "work": {"sha256": work.sha256},
                "stage_path": spec.stage.remote_stage_dir,
            }
        }
        return prep.ResidentEvidence(
            "a90-v3406-debian-display-f1-20260804-07",
            manifest,
            result,
            journal,
            value,
            {},
            spec,
            candidate,
            rollback,
            source,
            work,
            key,
            public_key,
        )

    def cleanup_spec(self, root: Path) -> prep.CleanupSpec:
        manifest = write_file(root / "cleanup-manifest.json", b"manifest")
        pre_d0 = write_file(root / "pre-cleanup-d0.json", b"d0")
        review = write_file(root / "review.json", b"review")
        return prep.CleanupSpec(
            manifest,
            "a90-resident-work-cleanup-20260804-01",
            self.resident(root),
            pre_d0,
            review,
            {},
        )

    def test_post_cleanup_proof_is_fixed_absent_unused_and_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            script = prep._post_source_script(self.resident(Path(raw)))
        self.assertIn(f"WORK={prep.WORK_PATH}", script)
        self.assertIn("work=absent stage=absent in_use=no", script)
        self.assertIn("/proc/[0-9]*/mountinfo", script)
        self.assertIn("/proc/[0-9]*/fd/*", script)
        self.assertIn("/proc/[0-9]*/root", script)
        self.assertNotIn(" rm ", script)
        self.assertNotIn("flash", script)

    def test_cleanup_command_can_only_unlink_fixed_work_once(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            spec = self.cleanup_spec(Path(raw))
            manifest_value = {
                "protected_rootfs": {
                    "work_sha256": spec.resident.work_host.sha256,
                    "source_path": spec.resident.spec.stage.remote_final,
                    "stage_path": spec.resident.spec.stage.remote_stage_dir,
                    "source_sha256": spec.resident.source_host.sha256,
                }
            }
            with mock.patch.object(prep, "_read", return_value=manifest_value):
                command = prep._cleanup_command(spec)
        self.assertEqual(command[6], prep.WORK_PATH)
        self.assertEqual(command[-1], prep.cleanup.SOURCE_EXACT_DISTINCT)
        self.assertEqual(command.count(prep.cleanup.cleanup_script()), 1)
        self.assertNotIn("rm -rf", command[4])

    def test_ambiguous_dispatch_is_not_replayed_and_passes_only_by_reads(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            spec = self.cleanup_spec(root)
            transaction = spec.manifest.path.parent / "cleanup-live"
            args = argparse.Namespace(
                operator_attended=True,
                bridge_device=spec.resident.spec.stage.bridge_device,
                expect_realpath=spec.resident.spec.stage.bridge_realpath,
            )
            health = {"exact": True}
            with mock.patch.object(prep, "_load_approval"), mock.patch.object(
                prep, "approval_binding", return_value={"exact": True}
            ), mock.patch.object(
                prep, "_require_live_target"
            ), mock.patch.object(
                prep, "_health", return_value=health
            ), mock.patch.object(
                prep.preserved,
                "protected_paths_preflight",
                return_value={"exact": True},
            ), mock.patch.object(
                prep, "_cleanup_command", return_value=["run", "unlink-once"]
            ), mock.patch.object(
                prep.preserved,
                "_remote",
                side_effect=TimeoutError("framing lost"),
            ) as dispatch, mock.patch.object(
                prep,
                "_presence",
                return_value={"work": "absent", "source": "exact", "stage": "absent"},
            ), mock.patch.object(
                prep, "_post_source_proof", return_value={"exact": True}
            ):
                result = prep.execute_cleanup(
                    spec,
                    args,
                    approval="test",
                    transaction_dir=transaction,
                )
                with self.assertRaisesRegex(prep.ContractError, "must be new"):
                    prep.execute_cleanup(
                        spec,
                        args,
                        approval="test",
                        transaction_dir=transaction,
                    )
        self.assertEqual(dispatch.call_count, 1)
        self.assertEqual(result["dispatch_count"], 1)
        self.assertFalse(result["cleanup_retransmitted"])
        self.assertEqual(
            result["outcome"],
            "PASS_EFFECT_PROVEN_AFTER_AMBIGUOUS_RESPONSE",
        )
        self.assertTrue(result["effect_proven"])

    def test_failed_passive_reconciliation_never_claims_success(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            spec = self.cleanup_spec(root)
            args = argparse.Namespace(
                operator_attended=True,
                bridge_device=spec.resident.spec.stage.bridge_device,
                expect_realpath=spec.resident.spec.stage.bridge_realpath,
            )
            with mock.patch.object(prep, "_load_approval"), mock.patch.object(
                prep, "approval_binding", return_value={"exact": True}
            ), mock.patch.object(
                prep, "_require_live_target"
            ), mock.patch.object(prep, "_health", return_value={"exact": True}), mock.patch.object(
                prep.preserved, "protected_paths_preflight", return_value={"exact": True}
            ), mock.patch.object(
                prep, "_cleanup_command", return_value=["run", "unlink-once"]
            ), mock.patch.object(
                prep.preserved,
                "_remote",
                return_value={"rc": 0, "status": "ok", "text": "work=unlinked source=exact\r\n"},
            ), mock.patch.object(
                prep,
                "_presence",
                return_value={"work": "present", "source": "exact", "stage": "absent"},
            ), mock.patch.object(
                prep, "_post_source_proof", side_effect=prep.ContractError("work present")
            ):
                result = prep.execute_cleanup(
                    spec,
                    args,
                    approval="test",
                    transaction_dir=spec.manifest.path.parent / "cleanup-live",
                )
        self.assertEqual(result["outcome"], "STOP_NO_RETRY_WORK_ABSENCE_UNPROVEN")
        self.assertFalse(result["effect_proven"])
        self.assertFalse(result["cleanup_retransmitted"])

    def test_review_closure_covers_both_effect_and_reducer(self) -> None:
        records = prep.review_source_records()
        self.assertEqual(set(records), set(prep.SOURCE_PATHS))
        for role in (
            "repository_contract",
            "target_contract",
            "prep_runner",
            "d1_runner",
            "preserved_install_runner",
            "retained_work_cleanup_helper",
            "f1_orchestrator",
        ):
            self.assertIn(role, records)

    def test_success_loader_rejects_forged_full_shape_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            original = self.cleanup_spec(root)
            protected = {
                "work_sha256": original.resident.work_host.sha256,
                "source_path": original.resident.spec.stage.remote_final,
                "stage_path": original.resident.spec.stage.remote_stage_dir,
                "source_sha256": original.resident.source_host.sha256,
                "work_path": prep.WORK_PATH,
            }
            manifest_path = root / "cleanup-manifest.json"
            manifest_path.write_text(
                json.dumps({"protected_rootfs": protected}),
                encoding="utf-8",
            )
            manifest_path.chmod(0o600)
            manifest = prep.Bound(
                manifest_path,
                manifest_path.stat().st_size,
                digest(manifest_path),
            )
            spec = prep.CleanupSpec(
                manifest,
                original.run_id,
                original.resident,
                original.pre_d0,
                original.review,
                original.closure,
            )
            live = root / "cleanup-live"
            live.mkdir()
            binding_sha = prep.preserved.base.json_sha256(
                prep.approval_binding(spec)
            )
            command = prep._cleanup_command(spec)
            now = prep.utc_now()
            intent = {
                "schema": "a90_resident_preserved_work_cleanup_intent_v1",
                "created_utc": now,
                "run_id": spec.run_id,
                "manifest_sha256": spec.manifest.sha256,
                "approval_binding_sha256": binding_sha,
                "before_health": {"forged": True},
                "before_paths": {"forged": True},
                "work_path": prep.WORK_PATH,
                "operator_attended": True,
                "physical_recovery_available": True,
                "dispatch_limit": 1,
                "unlink_replay_forbidden": True,
            }
            dispatch = {
                "schema": "a90_resident_preserved_work_cleanup_dispatch_v1",
                "created_utc": now,
                "run_id": spec.run_id,
                "dispatch_count": 1,
                "command_sha256": prep.preserved.base.json_sha256(command),
                "approval_consumed": True,
                "unlink_replay_forbidden": True,
            }
            result = {
                "schema": prep.RESULT_SCHEMA,
                "created_utc": now,
                "run_id": spec.run_id,
                "manifest_sha256": spec.manifest.sha256,
                "outcome": "PASS_EXACT_FIXED_WORK_UNLINKED",
                "dispatch_count": 1,
                "cleanup_retransmitted": False,
                "response_proven": True,
                "dispatch_receipt": {"forged": True},
                "post_presence": {
                    "work": "absent",
                    "source": "exact",
                    "stage": "absent",
                    "receipt": {"forged": True},
                },
                "post_source": {"forged": True},
                "post_health": {"forged": True},
                "post_errors": {},
                "effect_proven": True,
                "post_health_proven": True,
                "operator_attended": True,
                "physical_recovery_available": True,
                "device_write": True,
                "deleted_path": prep.WORK_PATH,
                "flash": False,
                "payload_sent": False,
                "other_device_commands": 0,
            }
            for name, value in (
                ("intent.json", intent),
                ("dispatch.json", dispatch),
                ("result.json", result),
            ):
                path = live / name
                path.write_text(json.dumps(value), encoding="utf-8")
                path.chmod(0o600)
            with mock.patch.object(prep, "PRIVATE_ROOT", root), mock.patch.object(
                prep, "_load_approval"
            ), mock.patch.object(
                prep, "_validate_health_value", return_value={"exact": True}
            ), mock.patch.object(
                prep.preserved, "_validate_protected_proof", return_value={"exact": True}
            ), self.assertRaisesRegex(
                prep.ContractError,
                "readback receipt",
            ):
                prep._load_success_result(spec)

    def test_original_preserved_terminal_is_not_a_d1_schema(self) -> None:
        self.assertNotEqual(prep.preserved.MANIFEST_SCHEMA, prep.BASELINE_SCHEMA)
        source = Path(d1.__file__).read_text(encoding="utf-8")
        self.assertIn('value.get("schema") == preserved_prep.BASELINE_SCHEMA', source)
        self.assertNotIn(
            'value.get("schema") == preserved_prep.preserved.MANIFEST_SCHEMA',
            source,
        )

    def test_preserved_identity_requires_reduced_evidence_kind(self) -> None:
        spec = SimpleNamespace(
            candidate_version=prep.EXPECTED_VERSION,
            candidate_build=prep.EXPECTED_BUILD,
            resident_evidence_kind="ordinary-resident-install-v2",
        )
        with self.assertRaisesRegex(d1.ContractError, "exact V3406 baseline"):
            d1.verify_resident_health_exact(spec, object(), object())
        spec.resident_evidence_kind = "preserved-install-cleanup-reduced-v1"
        receipts = {
            "version": {},
            "status": {},
            "selftest": {},
        }
        with mock.patch.object(
            d1.staging,
            "require_exact_bridge",
            return_value={"selected_realpath": "/dev/ttyACM0"},
        ), mock.patch.object(
            d1.base,
            "run_f1_cmd",
            side_effect=lambda _args, command: receipts[command[0]],
        ), mock.patch.object(
            d1.staging,
            "validate_native_health_receipts",
            return_value={"exact": True},
        ):
            spec.bridge_realpath = "/dev/ttyACM0"
            health = d1.verify_resident_health_exact(
                spec,
                SimpleNamespace(stage=object()),
                object(),
            )
        self.assertEqual(health["facts"], {"exact": True})


if __name__ == "__main__":
    unittest.main()
