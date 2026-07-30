"""Host-only tests for the minimal A90 V3403 F1 orchestrator."""

from __future__ import annotations

import copy
import hashlib
import json
import stat
import subprocess
import tempfile
import types
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest import mock

from _loader import load_script


f1 = load_script(
    "workspace/public/src/scripts/server-distro/a90_v3403_f1_orchestrator.py"
)
SOURCE = Path(
    "workspace/public/src/scripts/server-distro/a90_v3403_f1_orchestrator.py"
)


def sample_stage() -> object:
    run_id = "a90-v3403-debian-f1-20260730-02"
    return types.SimpleNamespace(
        run_id=run_id,
        manifest_path=Path("/private/manifest.json"),
        manifest_sha256="a" * 64,
        adapter_sha256="b" * 64,
        local_sha256="c" * 64,
        local_size=2147483648,
        remote_final="/mnt/sdext/a90/runtime/rootfs.img",
        remote_work="/mnt/sdext/a90/runtime/work.img",
        bound_files=(
            sample_bound(
                "target.connected_d0_result",
                "/private/connected-d0.json",
                "1" * 64,
            ),
            sample_bound(
                "target.connected_path_preflight",
                "/private/connected-paths.json",
                "2" * 64,
            ),
        ),
    )


def sample_bound(label: str, path: str, sha: str) -> object:
    return types.SimpleNamespace(
        label=label,
        path=Path(path),
        size=4096,
        sha256=sha,
    )


def sample_spec() -> object:
    stage = sample_stage()
    return types.SimpleNamespace(
        stage=stage,
        manifest={
            "schema": f1.FINAL_MANIFEST_SCHEMA,
            "status": f1.FINAL_MANIFEST_STATUS,
        },
        candidate=sample_bound("candidate_boot", "/private/candidate.img", "d" * 64),
        rollback=sample_bound("rollback_boot", "/private/rollback.img", "e" * 64),
        flash_runner=sample_bound("transport", str(f1.NATIVE_FLASH_PATH), "f" * 64),
        candidate_version="candidate-version",
        candidate_build="candidate-build",
        rollback_version=f1.staging.EXPECTED_BASELINE_VERSION,
        rollback_build=f1.staging.EXPECTED_BASELINE_BUILD,
        observer_device="usb-local-device",
        observer_port=2222,
        orchestrator_sha256=f1.sha256_file(SOURCE.resolve()),
        recovery_serial_sha256=hashlib.sha256(b"recovery-target").hexdigest(),
        recovery_serial="recovery-target",
        recovery_evidence=(),
        candidate_boot_timeout=300,
        rollback_boot_timeout=300,
    )


def sample_args() -> object:
    return types.SimpleNamespace(
        approval="test-approval-token",
        bridge_host="localhost",
        bridge_port=54321,
        bridge_timeout=180.0,
        remote_timeout=180.0,
        transfer_timeout=1200.0,
        staging_command_timeout=1800.0,
        flash_command_timeout=600.0,
        ssh_connect_timeout=8.0,
        recovery_path=None,
    )


def write_approval_prepared(base: Path, spec: object) -> dict[str, object]:
    binding = f1.approval_binding(spec)
    binding_sha256 = f1.json_sha256(binding)
    value: dict[str, object] = {
        "schema": f1.APPROVAL_PREPARED_SCHEMA,
        "created_utc": "2026-07-30T00:00:00Z",
        "run_id": spec.stage.run_id,
        "manifest_sha256": spec.stage.manifest_sha256,
        "approval_binding": binding,
        "approval_binding_sha256": binding_sha256,
        "approval_token": f1.APPROVAL_PREFIX + binding_sha256,
        "device_contact": False,
        "device_write": False,
        "f1_authorized": False,
        "live_authorized": False,
    }
    path = base / spec.stage.run_id / "approval-prepared.json"
    f1.write_private_json_exclusive(path, value)
    return value


def write_stage_success(base: Path, spec: object) -> dict[str, object]:
    result_dir = base / spec.stage.run_id / "staging-live"
    result_dir.mkdir(parents=True)
    result: dict[str, object] = {
        "schema": f1.staging.ADAPTER_SCHEMA,
        "run_id": spec.stage.run_id,
        "status": "PASS_ABSENT_ONLY_ROOTFS_STAGED",
        "manifest_sha256": spec.stage.manifest_sha256,
        "adapter_sha256": spec.stage.adapter_sha256,
        "rootfs": {
            "device_path": spec.stage.remote_final,
            "size": spec.stage.local_size,
            "sha256": spec.stage.local_sha256,
        },
        "publication": {"candidate_allowed": True},
    }
    path = result_dir / "result.json"
    path.write_text(json.dumps(result), encoding="utf-8")
    path.chmod(0o600)
    journal = result_dir / "journal"
    journal.mkdir()
    for sequence, state in enumerate(f1.SUCCESSFUL_STAGE_STATES):
        record: dict[str, object] = {
            "schema": "a90_v3403_absent_only_stage_journal_v1",
            "sequence": sequence,
            "timestamp_utc": "2026-07-30T00:00:00Z",
            "state": state,
            "run_id": spec.stage.run_id,
            "manifest_sha256": spec.stage.manifest_sha256,
        }
        if state == "closed":
            record["result"] = result
        journal_record = journal / f"{sequence:04d}-{state}.json"
        journal_record.write_text(json.dumps(record), encoding="utf-8")
        journal_record.chmod(0o600)
    return result


class A90V3403F1OrchestratorTests(unittest.TestCase):
    def test_canonical_timeline_is_exact_process_v2_order(self) -> None:
        self.assertEqual(
            f1.CANONICAL_EVENTS,
            (
                "live_session_start",
                "candidate_flash_start",
                "candidate_flash_done",
                "candidate_boot_ready",
                "rollback_flash_start",
                "rollback_flash_done",
                "rollback_boot_ready",
                "live_session_end",
            ),
        )

    def test_success_model_is_one_candidate_one_rollback(self) -> None:
        model = f1.simulate_transaction()
        self.assertEqual(model.candidate_attempts, 1)
        self.assertEqual(model.rollback_attempts, 1)
        self.assertFalse(model.rollback_required)
        self.assertTrue(model.observation_proven)
        self.assertTrue(model.final_health)
        self.assertTrue(model.closed)

    def test_pre_candidate_failure_needs_no_rollback(self) -> None:
        for step in ("validate", "approve", "stage"):
            with self.subTest(step=step):
                model = f1.simulate_transaction(fail_at=step, recover=True)
                self.assertEqual(model.candidate_attempts, 0)
                self.assertEqual(model.rollback_attempts, 0)
                self.assertFalse(model.rollback_required)
                self.assertFalse(model.closed)

    def test_candidate_intent_recovery_never_replays_candidate(self) -> None:
        model = f1.simulate_transaction(fail_at="candidate-intent", recover=True)
        self.assertEqual(model.candidate_attempts, 1)
        self.assertEqual(model.rollback_attempts, 1)
        self.assertIn("recover-rollback-only", model.history)
        self.assertTrue(model.final_health)
        self.assertTrue(model.closed)

    def test_observation_failure_still_recovers_rollback(self) -> None:
        model = f1.simulate_transaction(fail_at="observe", recover=True)
        self.assertEqual(model.candidate_attempts, 1)
        self.assertFalse(model.observation_proven)
        self.assertEqual(model.rollback_attempts, 1)
        self.assertTrue(model.closed)

    def test_started_rollback_is_never_reinvoked(self) -> None:
        model = f1.simulate_transaction(fail_at="rollback-intent", recover=True)
        self.assertEqual(model.rollback_attempts, 1)
        self.assertIn("rollback-retry-refused", model.history)
        self.assertTrue(model.rollback_required)
        self.assertFalse(model.closed)

    def test_source_contract_is_closed(self) -> None:
        self.assertEqual(
            f1.source_contract_issues(SOURCE.read_text(encoding="utf-8")),
            (),
        )

    def test_source_gate_rejects_candidate_route_in_recovery(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        marker = "def simulate_transaction("
        mutated = source.replace(
            marker,
            (
                "    flash_command(spec, args, rollback=False, from_native=True)"
                "\n\n" + marker
            ),
            1,
        )
        issues = f1.source_contract_issues(mutated)
        self.assertIn("recovery contains a candidate execution route", issues)

    def test_candidate_flash_command_is_exact_and_boot_only(self) -> None:
        command = f1.flash_command(
            sample_spec(),
            sample_args(),
            rollback=False,
            from_native=True,
        )
        self.assertEqual(command[1], str(f1.NATIVE_FLASH_PATH))
        self.assertIn("/private/candidate.img", command)
        self.assertIn("d" * 64, command)
        self.assertIn("candidate-version", command)
        self.assertNotIn("candidate-version build=candidate-build", command)
        self.assertIn("--serial", command)
        self.assertIn("recovery-target", command)
        self.assertIn("--from-native", command)
        self.assertNotIn("--allow-unpinned-image", command)
        self.assertNotIn("--boot-block", command)
        self.assertNotIn("userdata", " ".join(command))

    def test_rollback_from_recovery_is_exact_and_not_from_native(self) -> None:
        command = f1.flash_command(
            sample_spec(),
            sample_args(),
            rollback=True,
            from_native=False,
        )
        self.assertIn("/private/rollback.img", command)
        self.assertIn("e" * 64, command)
        self.assertIn("--serial", command)
        self.assertIn("recovery-target", command)
        self.assertNotIn("--from-native", command)

    def test_stage_command_delegates_to_reviewed_adapter(self) -> None:
        command = f1.stage_command(sample_spec(), sample_args())
        self.assertEqual(command[1], str(f1.STAGING_PATH))
        self.assertIn("--execute-approved-stage", command)
        self.assertIn("a" * 64, command)
        self.assertIn("b" * 64, command)
        self.assertIn("staging-live", " ".join(command))
        self.assertIn("--approval", command)
        self.assertIn("test-approval-token", command)
        self.assertNotIn("candidate.img", " ".join(command))

    def test_remote_source_preflight_has_no_write_primitive(self) -> None:
        source = f1.remote_source_preflight
        text = SOURCE.read_text(encoding="utf-8")
        body = text[text.index("def remote_source_preflight("):text.index("def run_handoff(")]
        self.assertIsNotNone(source)
        for token in (" rm ", " mv ", " cp ", " dd ", " mount ", " ln "):
            self.assertNotIn(token, body)

    def test_approved_binding_rejects_draft_before_live_work(self) -> None:
        spec = sample_spec()
        spec.manifest["schema"] = "a90_native_init_f1_draft_v1"
        with self.assertRaisesRegex(f1.ContractError, "non-final"):
            f1.approved_bindings(spec, sample_args(), recovery=False)

    def test_approved_binding_requires_fresh_exact_token(self) -> None:
        spec = sample_spec()
        with tempfile.TemporaryDirectory(dir=f1.staging.PRIVATE_ROOT) as temp_dir:
            old_base = f1.PRIVATE_RUN_BASE
            try:
                f1.PRIVATE_RUN_BASE = Path(temp_dir)
                prepared = write_approval_prepared(Path(temp_dir), spec)
                args = sample_args()
                with self.assertRaisesRegex(f1.ContractError, "token mismatch"):
                    f1.approved_bindings(spec, args, recovery=False)
                args.approval = prepared["approval_token"]
                accepted = f1.approved_bindings(spec, args, recovery=False)
                self.assertEqual(
                    accepted["approval_binding_sha256"],
                    prepared["approval_binding_sha256"],
                )
            finally:
                f1.PRIVATE_RUN_BASE = old_base

    def test_approval_preparation_keeps_authority_false(self) -> None:
        spec = sample_spec()
        with tempfile.TemporaryDirectory(dir=f1.staging.PRIVATE_ROOT) as temp_dir:
            old_base = f1.PRIVATE_RUN_BASE
            try:
                f1.PRIVATE_RUN_BASE = Path(temp_dir)
                with mock.patch.object(f1, "verify_local_closure"):
                    prepared = f1.prepare_approval(spec)
                self.assertTrue(
                    str(prepared["approval_token"]).startswith(f1.APPROVAL_PREFIX)
                )
                self.assertFalse(prepared["f1_authorized"])
                self.assertFalse(prepared["live_authorized"])
                mode = stat.S_IMODE(
                    (
                        Path(temp_dir)
                        / spec.stage.run_id
                        / "approval-prepared.json"
                    ).stat().st_mode
                )
                self.assertEqual(mode, 0o600)
            finally:
                f1.PRIVATE_RUN_BASE = old_base

    def test_rollback_recovery_reopens_binding_without_second_token(self) -> None:
        spec = sample_spec()
        with tempfile.TemporaryDirectory(dir=f1.staging.PRIVATE_ROOT) as temp_dir:
            old_base = f1.PRIVATE_RUN_BASE
            try:
                f1.PRIVATE_RUN_BASE = Path(temp_dir)
                write_approval_prepared(Path(temp_dir), spec)
                args = sample_args()
                args.approval = None
                accepted = f1.approved_bindings(spec, args, recovery=True)
                self.assertFalse(accepted["live_authorized"])
                args.approval = "second-token"
                with self.assertRaisesRegex(f1.ContractError, "second approval"):
                    f1.approved_bindings(spec, args, recovery=True)
            finally:
                f1.PRIVATE_RUN_BASE = old_base

    def test_final_manifest_authority_must_remain_false_until_token(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        authority = source[
            source.index('authority = _dict(manifest.get("authority")'):
            source.index('orchestrator = manifest.get("f1_orchestrator")')
        ]
        self.assertIn("must remain false before approval", authority)
        self.assertIn("fresh_operator_approval_required", authority)
        self.assertIn("manifest_grants_live_authority", authority)

    def test_recovery_serial_is_derived_from_two_digest_bound_logs(self) -> None:
        with tempfile.TemporaryDirectory(dir=f1.staging.PRIVATE_ROOT) as temp_dir:
            root = Path(temp_dir)
            evidence = []
            for name in ("candidate.log", "rollback.log"):
                path = root / name
                path.write_text(
                    "[native-init-flash 00:00:00] "
                    "ADB ready: recovery-target recovery\n",
                    encoding="utf-8",
                )
                path.chmod(0o600)
                evidence.append(
                    f1.staging.BoundFile(
                        label=name,
                        path=path,
                        size=path.stat().st_size,
                        sha256=f1.sha256_file(path),
                    )
                )
            self.assertEqual(
                f1.recovery_serial_from_evidence(
                    tuple(evidence),
                    hashlib.sha256(b"recovery-target").hexdigest(),
                ),
                "recovery-target",
            )
            with self.assertRaisesRegex(f1.ContractError, "manifest digest"):
                f1.recovery_serial_from_evidence(
                    tuple(evidence),
                    hashlib.sha256(b"other-target").hexdigest(),
                )

    def test_exact_transaction_dir_rejects_every_other_location(self) -> None:
        spec = sample_spec()
        expected = (
            f1.PRIVATE_RUN_BASE / spec.stage.run_id / "f1-live"
        ).resolve()
        self.assertEqual(f1.exact_transaction_dir(spec, expected), expected)
        for path in (
            Path("/tmp/f1-live"),
            f1.PRIVATE_RUN_BASE / spec.stage.run_id / "other",
            f1.PRIVATE_RUN_BASE / "wrong-run" / "f1-live",
        ):
            with self.subTest(path=path):
                with self.assertRaises(f1.ContractError):
                    f1.exact_transaction_dir(spec, path)

    def test_journal_is_exclusive_contiguous_and_manifest_bound(self) -> None:
        spec = sample_spec()
        with tempfile.TemporaryDirectory(dir=f1.staging.PRIVATE_ROOT) as temp_dir:
            transaction = Path(temp_dir)
            journal = transaction / "journal"
            first = f1.append_record(
                journal,
                "PREFLIGHT",
                "preflight",
                {"device_write": False},
                manifest_sha256=spec.stage.manifest_sha256,
                run_id=spec.stage.run_id,
            )
            second = f1.append_record(
                journal,
                "APPROVED",
                "approved",
                {"candidate_attempted": False},
                manifest_sha256=spec.stage.manifest_sha256,
                run_id=spec.stage.run_id,
            )
            self.assertEqual(first.name, "0000-preflight.json")
            self.assertEqual(second.name, "0001-approved.json")
            records = f1.read_journal(spec, transaction)
            self.assertEqual([record["sequence"] for record in records], [0, 1])
            self.assertTrue(all(record["manifest_sha256"] == "a" * 64 for record in records))

    def test_timeline_accepts_ordered_failure_subset(self) -> None:
        with tempfile.TemporaryDirectory(dir=f1.staging.PRIVATE_ROOT) as temp_dir:
            transaction = Path(temp_dir)
            events: list[dict[str, str]] = []
            for name in (
                "live_session_start",
                "candidate_flash_start",
                "rollback_flash_start",
                "rollback_flash_done",
                "rollback_boot_ready",
                "live_session_end",
            ):
                f1.add_event(transaction, events, name)
            loaded = f1.load_timeline(transaction)
            self.assertEqual(
                [event["name"] for event in loaded],
                [event["name"] for event in events],
            )

    def test_timeline_rejects_duplicate_and_reverse_order(self) -> None:
        with tempfile.TemporaryDirectory(dir=f1.staging.PRIVATE_ROOT) as temp_dir:
            transaction = Path(temp_dir)
            events: list[dict[str, str]] = []
            f1.add_event(transaction, events, "live_session_start")
            f1.add_event(transaction, events, "candidate_flash_start")
            with self.assertRaisesRegex(f1.ContractError, "duplicate"):
                f1.add_event(transaction, events, "candidate_flash_start")
        with tempfile.TemporaryDirectory() as temp_dir:
            transaction = Path(temp_dir)
            events = []
            f1.add_event(transaction, events, "live_session_start")
            f1.add_event(transaction, events, "rollback_flash_start")
            with self.assertRaisesRegex(f1.ContractError, "out of order"):
                f1.add_event(transaction, events, "candidate_flash_done")

    def test_timeline_repairs_every_durable_completion_without_replay(self) -> None:
        spec = sample_spec()
        with tempfile.TemporaryDirectory(dir=f1.staging.PRIVATE_ROOT) as temp_dir:
            transaction = Path(temp_dir)
            journal = transaction / "journal"
            actions = (
                ("PREFLIGHT", "preflight"),
                ("APPROVED", "candidate-transfer-started"),
                ("CANDIDATE_FLASHED", "candidate-flashed"),
                ("CANDIDATE_FLASHED", "candidate-boot-ready"),
                ("RECOVERY_ROLLBACK", "rollback-transfer-started"),
                ("ROLLBACK_FLASHED", "rollback-flashed"),
                ("ROLLBACK_FLASHED", "rollback-boot-ready"),
            )
            for state, action in actions:
                f1.append_record(
                    journal,
                    state,
                    action,
                    {},
                    manifest_sha256=spec.stage.manifest_sha256,
                    run_id=spec.stage.run_id,
                )
            events = f1.repair_timeline_from_journal(
                transaction,
                f1.read_journal(spec, transaction),
            )
            self.assertEqual(
                [event["name"] for event in events],
                list(f1.CANONICAL_EVENTS[:-1]),
            )

    def test_stray_rollback_start_event_does_not_block_idempotent_recovery(self) -> None:
        spec = sample_spec()
        with tempfile.TemporaryDirectory(dir=f1.staging.PRIVATE_ROOT) as temp_dir:
            transaction = Path(temp_dir)
            events: list[dict[str, str]] = []
            f1.add_event(transaction, events, "live_session_start")
            f1.add_event(transaction, events, "candidate_flash_start")
            f1.add_event(transaction, events, "rollback_flash_start")
            journal = transaction / "journal"
            for state, action in (
                ("PREFLIGHT", "preflight"),
                ("APPROVED", "candidate-transfer-started"),
            ):
                f1.append_record(
                    journal,
                    state,
                    action,
                    {},
                    manifest_sha256=spec.stage.manifest_sha256,
                    run_id=spec.stage.run_id,
                )
            repaired = f1.repair_timeline_from_journal(
                transaction,
                f1.read_journal(spec, transaction),
            )
            self.assertNotIn(
                "rollback_flash_start",
                [event["name"] for event in repaired],
            )
            f1.ensure_event(transaction, repaired, "rollback_flash_start")
            f1.ensure_event(transaction, repaired, "rollback_flash_start")
            self.assertEqual(
                [event["name"] for event in repaired].count("rollback_flash_start"),
                1,
            )

    def test_flash_log_classifies_host_rejection_separately(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "flash.log"
            path.write_text(
                "[native-init-flash 00:00:00] "
                "phase.native_init_flash.inspect_local_image.elapsed_sec=0.1 ok=0\n",
                encoding="utf-8",
            )
            classification = f1.classify_flash_log(path)
            self.assertFalse(classification["local_image_validated"])
            self.assertFalse(classification["native_recovery_requested"])
            self.assertFalse(classification["recovery_endpoint_selected"])
            self.assertFalse(classification["boot_write_started"])

    def test_stage_result_must_allow_the_exact_candidate(self) -> None:
        spec = sample_spec()
        with tempfile.TemporaryDirectory(dir=f1.staging.PRIVATE_ROOT) as temp_dir:
            old_base = f1.PRIVATE_RUN_BASE
            try:
                f1.PRIVATE_RUN_BASE = Path(temp_dir)
                result = write_stage_success(Path(temp_dir), spec)
                path = (
                    Path(temp_dir)
                    / spec.stage.run_id
                    / "staging-live"
                    / "result.json"
                )
                self.assertTrue(f1.validate_stage_result(spec)["publication"]["candidate_allowed"])
                result["publication"]["candidate_allowed"] = False
                path.write_text(json.dumps(result), encoding="utf-8")
                with self.assertRaises(f1.ContractError):
                    f1.validate_stage_result(spec)
            finally:
                f1.PRIVATE_RUN_BASE = old_base

    def test_stage_result_requires_a_durably_closed_journal(self) -> None:
        spec = sample_spec()
        with tempfile.TemporaryDirectory(dir=f1.staging.PRIVATE_ROOT) as temp_dir:
            old_base = f1.PRIVATE_RUN_BASE
            try:
                f1.PRIVATE_RUN_BASE = Path(temp_dir)
                result_dir = Path(temp_dir) / spec.stage.run_id / "staging-live"
                result_dir.mkdir(parents=True)
                result = {
                    "schema": f1.staging.ADAPTER_SCHEMA,
                    "run_id": spec.stage.run_id,
                    "status": "PASS_ABSENT_ONLY_ROOTFS_STAGED",
                    "manifest_sha256": spec.stage.manifest_sha256,
                    "adapter_sha256": spec.stage.adapter_sha256,
                    "rootfs": {
                        "device_path": spec.stage.remote_final,
                        "size": spec.stage.local_size,
                        "sha256": spec.stage.local_sha256,
                    },
                    "publication": {"candidate_allowed": True},
                }
                path = result_dir / "result.json"
                path.write_text(json.dumps(result), encoding="utf-8")
                path.chmod(0o600)
                with self.assertRaisesRegex(f1.ContractError, "success closure"):
                    f1.validate_stage_result(spec)
            finally:
                f1.PRIVATE_RUN_BASE = old_base

    def test_stage_result_rejects_unbound_or_noncontiguous_journal(self) -> None:
        spec = sample_spec()
        with tempfile.TemporaryDirectory(dir=f1.staging.PRIVATE_ROOT) as temp_dir:
            old_base = f1.PRIVATE_RUN_BASE
            try:
                base = Path(temp_dir)
                f1.PRIVATE_RUN_BASE = base
                write_stage_success(base, spec)
                first = (
                    base
                    / spec.stage.run_id
                    / "staging-live"
                    / "journal"
                    / "0000-approval-binding-reopened.json"
                )
                value = json.loads(first.read_text())
                value["manifest_sha256"] = "0" * 64
                first.write_text(json.dumps(value), encoding="utf-8")
                with self.assertRaisesRegex(f1.ContractError, "exact bound"):
                    f1.validate_stage_result(spec)
            finally:
                f1.PRIVATE_RUN_BASE = old_base

    def test_native_rollback_source_accepts_only_candidate_or_baseline(self) -> None:
        spec = sample_spec()
        args = sample_args()
        healthy = [
            {"text": "candidate-version build=candidate-build\n"},
            {"text": "selftest pass=1 warn=0 fail=0\n"},
        ]
        with (
            mock.patch.object(f1.staging, "require_exact_bridge"),
            mock.patch.object(f1.d1, "run_cmd", side_effect=healthy),
        ):
            result = f1.require_rollback_source_native(spec, args)
        self.assertIn("candidate-version", result["version"]["text"])

        unknown = [
            {"text": "unexpected-version\n"},
            {"text": "selftest pass=1 warn=0 fail=0\n"},
        ]
        with (
            mock.patch.object(f1.staging, "require_exact_bridge"),
            mock.patch.object(f1.d1, "run_cmd", side_effect=unknown),
        ):
            with self.assertRaisesRegex(f1.ContractError, "not the exact"):
                f1.require_rollback_source_native(spec, args)

    def test_pre_candidate_abort_closes_without_rollback(self) -> None:
        spec = sample_spec()
        with tempfile.TemporaryDirectory() as temp_dir:
            transaction = Path(temp_dir)
            events: list[dict[str, str]] = []
            f1.add_event(transaction, events, "live_session_start")
            f1.abort_before_candidate(
                spec,
                transaction,
                transaction / "journal",
                events,
                RuntimeError("staging-stop"),
            )
            result = json.loads((transaction / "result.json").read_text())
            self.assertEqual(result["status"], "ABORTED_F1_V2_BEFORE_CANDIDATE")
            self.assertEqual(result["candidate_transfer_count"], 0)
            self.assertEqual(result["rollback_transfer_count"], 0)
            self.assertFalse(result["rollback_required"])
            self.assertEqual(
                result["timeline_events"],
                ["live_session_start", "live_session_end"],
            )

    def test_default_cli_is_host_only(self) -> None:
        parser = f1.build_parser()
        with redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit):
                parser.parse_args([])
        args = parser.parse_args(
            [
                "--manifest",
                "/private/draft.json",
                "--expect-manifest-sha256",
                "a" * 64,
            ]
        )
        self.assertFalse(args.execute_approved_f1)
        self.assertFalse(args.recover_approved_rollback)
        self.assertFalse(args.prepare_approval)
        self.assertIsNone(args.approval)
        self.assertIsNone(args.recovery_path)

    def test_run_logged_timeout_is_private_and_structured(self) -> None:
        with tempfile.TemporaryDirectory(dir=f1.staging.PRIVATE_ROOT) as temp_dir:
            log = Path(temp_dir) / "flash.raw.log"
            with mock.patch.object(
                f1.subprocess,
                "run",
                side_effect=subprocess.TimeoutExpired(["private-command"], 3.0),
            ):
                record = f1.run_logged(
                    ["private-command"],
                    log_path=log,
                    timeout=3.0,
                )
            self.assertEqual(record["returncode"], 124)
            self.assertEqual(record["execution_error"]["type"], "TimeoutExpired")
            self.assertEqual(record["execution_error"]["stage"], "process-wait")
            self.assertTrue(record["process_started"])
            self.assertEqual(stat.S_IMODE(log.stat().st_mode), 0o600)

    def test_run_logged_exec_error_is_private_and_structured(self) -> None:
        with tempfile.TemporaryDirectory(dir=f1.staging.PRIVATE_ROOT) as temp_dir:
            log = Path(temp_dir) / "flash.raw.log"
            with mock.patch.object(
                f1.subprocess,
                "run",
                side_effect=FileNotFoundError(2, "missing executable"),
            ):
                record = f1.run_logged(
                    ["private-command"],
                    log_path=log,
                    timeout=3.0,
                )
            self.assertEqual(record["returncode"], 125)
            self.assertEqual(record["execution_error"]["type"], "OSError")
            self.assertEqual(record["execution_error"]["stage"], "process-spawn")
            self.assertEqual(record["execution_error"]["errno"], 2)
            self.assertFalse(record["process_started"])
            self.assertEqual(stat.S_IMODE(log.stat().st_mode), 0o600)

    def test_candidate_timeout_without_marker_preserves_rollback(self) -> None:
        classification = {
            name: False
            for name in (
                "local_image_validated",
                "native_recovery_requested",
                "recovery_endpoint_selected",
                "payload_transfer_started",
                "boot_write_started",
                "boot_write_completed",
                "readback_completed",
            )
        }
        timeout = {
            "returncode": 124,
            "process_started": True,
            "execution_error": {
                "type": "TimeoutExpired",
                "stage": "process-wait",
                "timeout_sec": 3.0,
            },
            "phase_classification": classification,
        }
        self.assertFalse(f1.candidate_failure_is_definite_pre_session(timeout))

        pre_spawn = {
            "returncode": 125,
            "process_started": False,
            "execution_error": {
                "type": "OSError",
                "stage": "process-spawn",
                "errno": 2,
            },
            "phase_classification": classification,
        }
        self.assertTrue(f1.candidate_failure_is_definite_pre_session(pre_spawn))

        completed_host_rejection = {
            "returncode": 2,
            "process_started": True,
            "phase_classification": classification,
        }
        self.assertTrue(
            f1.candidate_failure_is_definite_pre_session(
                completed_host_rejection
            )
        )

    def test_execute_candidate_timeout_routes_to_mandatory_rollback(self) -> None:
        spec = sample_spec()
        args = sample_args()
        with tempfile.TemporaryDirectory(dir=f1.staging.PRIVATE_ROOT) as temp_dir:
            base = Path(temp_dir)
            old_base = f1.PRIVATE_RUN_BASE
            try:
                f1.PRIVATE_RUN_BASE = base
                transaction = base / spec.stage.run_id / "f1-live"
                args.transaction_dir = transaction
                calls = 0

                def fake_run_logged(
                    command: list[str],
                    *,
                    log_path: Path,
                    timeout: float,
                ) -> dict[str, object]:
                    nonlocal calls
                    calls += 1
                    log_path.write_bytes(b"")
                    log_path.chmod(0o600)
                    record: dict[str, object] = {
                        **f1.command_record(log_path, 0 if calls == 1 else 124),
                        "process_started": True,
                    }
                    if calls == 2:
                        record["execution_error"] = {
                            "type": "TimeoutExpired",
                            "stage": "process-wait",
                            "timeout_sec": timeout,
                        }
                    return record

                with (
                    mock.patch.object(
                        f1,
                        "approved_bindings",
                        return_value={"approval_binding_sha256": "9" * 64},
                    ),
                    mock.patch.object(f1, "verify_local_closure"),
                    mock.patch.object(f1, "run_logged", side_effect=fake_run_logged),
                    mock.patch.object(f1, "validate_stage_result", return_value={}),
                    mock.patch.object(
                        f1.staging,
                        "require_exact_bridge",
                        return_value={},
                    ),
                    mock.patch.object(
                        f1.staging,
                        "require_baseline",
                        return_value={},
                    ),
                    mock.patch.object(
                        f1,
                        "remote_source_preflight",
                        return_value={},
                    ),
                    mock.patch.object(
                        f1,
                        "require_rollback_source_native",
                        return_value={},
                    ),
                    mock.patch.object(
                        f1,
                        "invoke_rollback",
                        return_value={"final_health": True},
                    ) as rollback,
                    mock.patch.object(
                        f1,
                        "close_transaction",
                        return_value={"status": "closed"},
                    ),
                ):
                    result = f1.execute_approved_f1(spec, args)
                self.assertEqual(result["status"], "closed")
                rollback.assert_called_once()
                journal = f1.read_journal(spec, transaction)
                actions = [record["action"] for record in journal]
                self.assertIn("candidate-invocation-failed", actions)
                self.assertNotIn("candidate-host-rejected", actions)
                failed = next(
                    record
                    for record in journal
                    if record["action"] == "candidate-invocation-failed"
                )
                self.assertTrue(failed["rollback_required"])
            finally:
                f1.PRIVATE_RUN_BASE = old_base

    def test_rollback_pre_spawn_error_preserves_same_approval_retry(self) -> None:
        spec = sample_spec()
        args = sample_args()
        with tempfile.TemporaryDirectory(dir=f1.staging.PRIVATE_ROOT) as temp_dir:
            transaction = Path(temp_dir)
            journal = transaction / "journal"

            def fail_before_spawn(
                command: list[str],
                *,
                log_path: Path,
                timeout: float,
            ) -> dict[str, object]:
                log_path.write_bytes(b"")
                log_path.chmod(0o600)
                return {
                    **f1.command_record(log_path, 125),
                    "process_started": False,
                    "execution_error": {
                        "type": "OSError",
                        "stage": "process-spawn",
                        "errno": 2,
                    },
                }

            with (
                mock.patch.object(
                    f1,
                    "run_logged",
                    side_effect=fail_before_spawn,
                ),
                self.assertRaisesRegex(
                    RuntimeError,
                    "helper did not start; recover rollback only",
                ),
            ):
                f1.invoke_rollback(
                    spec,
                    args,
                    transaction,
                    journal,
                    [],
                    from_native=True,
                )
            records = f1.read_journal(spec, transaction)
            self.assertEqual(
                [record["action"] for record in records],
                [
                    "rollback-transfer-started",
                    "rollback-process-not-started",
                ],
            )
            allowed, mode, rejection_count = f1.rollback_pre_spawn_retry(
                spec,
                transaction,
                records,
            )
            self.assertTrue(allowed)
            self.assertEqual(mode, "from-native")
            self.assertEqual(rejection_count, 1)
            self.assertTrue(records[-1]["rollback_retry_preserved"])
            self.assertEqual(records[-1]["rollback_transfer_count"], 0)

            mutations: list[tuple[str, object]] = []

            def mutated(
                label: str,
                record_index: int,
                key_path: tuple[str, ...],
                value: object,
            ) -> None:
                changed = copy.deepcopy(records)
                target: dict[str, object] = changed[record_index]
                for key in key_path[:-1]:
                    target = target[key]  # type: ignore[assignment]
                target[key_path[-1]] = value
                mutations.append((label, changed))

            mutated("intent timestamp", -2, ("timestamp_utc",), "not-utc")
            mutated("rejection timestamp", -1, ("timestamp_utc",), "not-utc")
            mutated("intent sequence float", -2, ("sequence",), 0.0)
            mutated("rejection sequence float", -1, ("sequence",), 1.0)
            mutated("attempt bool", -2, ("rollback_attempt_limit",), True)
            mutated("attempt float", -2, ("rollback_attempt_limit",), 1.0)
            mutated(
                "prior count bool",
                -2,
                ("prior_pre_spawn_rejections",),
                False,
            )
            mutated(
                "transfer count bool",
                -1,
                ("rollback_transfer_count",),
                False,
            )
            mutated(
                "returncode float",
                -1,
                ("record", "returncode"),
                125.0,
            )
            mutated(
                "raw size bool",
                -1,
                ("record", "raw_log_size"),
                False,
            )
            mutated(
                "bogus error type",
                -1,
                ("record", "execution_error", "type"),
                "BogusError",
            )
            mutated(
                "errno bool",
                -1,
                ("record", "execution_error", "errno"),
                True,
            )
            for label, changed in mutations:
                with self.subTest(mutation=label):
                    mutated_allowed, _, _ = f1.rollback_pre_spawn_retry(
                        spec,
                        transaction,
                        changed,  # type: ignore[arg-type]
                    )
                    self.assertFalse(mutated_allowed)

            historical_intent = copy.deepcopy(records[-2])
            historical_intent["sequence"] = 0
            historical_failure = {
                "schema": records[-1]["schema"],
                "sequence": 1,
                "timestamp_utc": records[-1]["timestamp_utc"],
                "run_id": records[-1]["run_id"],
                "manifest_sha256": records[-1]["manifest_sha256"],
                "state": "RECOVERY_ROLLBACK",
                "action": "rollback-invocation-failed",
                "candidate_replay": False,
                "rollback_retry_forbidden": True,
                "record": {
                    "returncode": 1,
                    "process_started": True,
                },
            }
            latest_intent = copy.deepcopy(records[-2])
            latest_intent["sequence"] = 2
            latest_rejection = copy.deepcopy(records[-1])
            latest_rejection["sequence"] = 3
            started_then_exact = [
                historical_intent,
                historical_failure,
                latest_intent,
                latest_rejection,
            ]
            history_allowed, _, _ = f1.rollback_pre_spawn_retry(
                spec,
                transaction,
                started_then_exact,
            )
            self.assertFalse(history_allowed)
            obscured_history = copy.deepcopy(started_then_exact)
            obscured_history[0]["action"] = "renamed-intent"
            obscured_history[0]["state"] = "APPROVED"
            obscured_history[1]["action"] = "renamed-failure"
            obscured_history[1]["state"] = "APPROVED"
            obscured_allowed, _, _ = f1.rollback_pre_spawn_retry(
                spec,
                transaction,
                obscured_history,
            )
            self.assertFalse(obscured_allowed)

            retry_log = (
                transaction
                / "rollback-flash-pre-spawn-retry-0001.raw.log"
            )
            retry_log.write_bytes(b"")
            retry_log.chmod(0o600)
            second_intent = copy.deepcopy(records[-2])
            second_intent["sequence"] = records[-2]["sequence"] + 2
            second_intent["prior_pre_spawn_rejections"] = 1
            second_rejection = copy.deepcopy(records[-1])
            second_rejection["sequence"] = records[-1]["sequence"] + 2
            second_rejection["record"].update(
                f1.command_record(retry_log, 125)
            )
            repeated_allowed, repeated_mode, repeated_count = (
                f1.rollback_pre_spawn_retry(
                    spec,
                    transaction,
                    [*records, second_intent, second_rejection],
                )
            )
            self.assertTrue(repeated_allowed)
            self.assertEqual(repeated_mode, "from-native")
            self.assertEqual(repeated_count, 2)

            raw_log = Path(str(records[-1]["record"]["raw_log"]))
            symlink_target = transaction / "other-empty-private.raw.log"
            symlink_target.write_bytes(b"")
            symlink_target.chmod(0o600)
            raw_log.unlink()
            raw_log.symlink_to(symlink_target)
            symlink_allowed, _, _ = f1.rollback_pre_spawn_retry(
                spec,
                transaction,
                records,
            )
            self.assertFalse(symlink_allowed)
            retargeted = copy.deepcopy(records)
            retargeted[-1]["record"]["raw_log"] = str(
                symlink_target.resolve()
            )
            retargeted_allowed, _, _ = f1.rollback_pre_spawn_retry(
                spec,
                transaction,
                retargeted,
            )
            self.assertFalse(retargeted_allowed)

    def test_unpaired_latest_rollback_intent_is_never_retried(self) -> None:
        spec = sample_spec()
        records = [
            {
                "action": "rollback-transfer-started",
                "recovery_mode": "adb-recovery",
            },
            {
                "action": "rollback-process-not-started",
                "rollback_process_started": False,
                "record": {
                    "process_started": False,
                    "execution_error": {
                        "type": "OSError",
                        "stage": "process-spawn",
                    },
                },
            },
            {
                "action": "rollback-transfer-started",
                "recovery_mode": "adb-recovery",
            },
        ]
        with tempfile.TemporaryDirectory(
            dir=f1.staging.PRIVATE_ROOT
        ) as temp_dir:
            allowed, mode, rejection_count = f1.rollback_pre_spawn_retry(
                spec,
                Path(temp_dir),
                records,
            )
            self.assertFalse(allowed)
            self.assertIsNone(mode)
            self.assertEqual(rejection_count, 0)

    def test_conflicting_started_failure_then_malformed_not_started_is_refused(
        self,
    ) -> None:
        spec = sample_spec()
        records = [
            {
                "action": "rollback-transfer-started",
                "recovery_mode": "adb-recovery",
            },
            {
                "action": "rollback-invocation-failed",
                "rollback_retry_forbidden": True,
                "record": {"process_started": True, "returncode": 1},
            },
            {
                "action": "rollback-process-not-started",
                "rollback_process_started": False,
                "record": {
                    "process_started": False,
                    "execution_error": {"stage": "process-spawn"},
                },
            },
        ]
        with tempfile.TemporaryDirectory(
            dir=f1.staging.PRIVATE_ROOT
        ) as temp_dir:
            allowed, _, rejection_count = f1.rollback_pre_spawn_retry(
                spec,
                Path(temp_dir),
                records,
            )
        self.assertFalse(allowed)
        self.assertEqual(rejection_count, 0)

    def test_recovery_reinvokes_only_definite_pre_spawn_rollback(self) -> None:
        spec = sample_spec()
        with tempfile.TemporaryDirectory(dir=f1.staging.PRIVATE_ROOT) as temp_dir:
            base = Path(temp_dir)
            old_base = f1.PRIVATE_RUN_BASE
            try:
                f1.PRIVATE_RUN_BASE = base
                prepared = write_approval_prepared(base, spec)
                transaction = base / spec.stage.run_id / "f1-live"
                journal = transaction / "journal"
                approved_payload = {
                    "approval_binding_sha256": prepared[
                        "approval_binding_sha256"
                    ],
                    "approval_token_sha256": hashlib.sha256(
                        str(prepared["approval_token"]).encode("utf-8")
                    ).hexdigest(),
                }
                records = (
                    ("PREFLIGHT", "preflight", {}),
                    ("APPROVED", "approved", approved_payload),
                    (
                        "APPROVED",
                        "candidate-transfer-started",
                        {"rollback_required": True},
                    ),
                )
                for state, action, payload in records:
                    f1.append_record(
                        journal,
                        state,
                        action,
                        payload,
                        manifest_sha256=spec.stage.manifest_sha256,
                        run_id=spec.stage.run_id,
                    )
                initial_args = sample_args()

                def fail_before_spawn(
                    command: list[str],
                    *,
                    log_path: Path,
                    timeout: float,
                ) -> dict[str, object]:
                    log_path.write_bytes(b"")
                    log_path.chmod(0o600)
                    return {
                        **f1.command_record(log_path, 125),
                        "process_started": False,
                        "execution_error": {
                            "type": "OSError",
                            "stage": "process-spawn",
                            "errno": 2,
                        },
                    }

                with (
                    mock.patch.object(
                        f1,
                        "run_logged",
                        side_effect=fail_before_spawn,
                    ),
                    self.assertRaisesRegex(
                        RuntimeError,
                        "helper did not start; recover rollback only",
                    ),
                ):
                    f1.invoke_rollback(
                        spec,
                        initial_args,
                        transaction,
                        journal,
                        [],
                        from_native=True,
                    )
                raw_log = transaction / "rollback-flash.raw.log"
                symlink_target = transaction / "retarget-empty-private.raw.log"
                symlink_target.write_bytes(b"")
                symlink_target.chmod(0o600)
                raw_log.unlink()
                raw_log.symlink_to(symlink_target)
                rejection_path = sorted(journal.glob("*.json"))[-1]
                rejection = json.loads(rejection_path.read_text())
                rejection["record"]["raw_log"] = str(
                    symlink_target.resolve()
                )
                f1.write_private_json_atomic(rejection_path, rejection)
                args = sample_args()
                args.approval = None
                args.transaction_dir = transaction
                with (
                    mock.patch.object(f1, "verify_local_closure"),
                    mock.patch.object(f1, "require_rollback_source_native"),
                    mock.patch.object(
                        f1,
                        "verify_final_health",
                        side_effect=f1.ContractError(
                            "retargeted evidence cannot prove rollback completion"
                        ),
                    ),
                    mock.patch.object(f1, "invoke_rollback") as refused_invoke,
                    self.assertRaisesRegex(
                        f1.ContractError,
                        "retargeted evidence",
                    ),
                ):
                    f1.recover_approved_rollback(spec, args)
                refused_invoke.assert_not_called()

                raw_log.unlink()
                raw_log.write_bytes(b"")
                raw_log.chmod(0o600)
                rejection["record"]["raw_log"] = str(raw_log)
                f1.write_private_json_atomic(rejection_path, rejection)
                with (
                    mock.patch.object(f1, "verify_local_closure"),
                    mock.patch.object(f1, "require_rollback_source_native"),
                    mock.patch.object(
                        f1,
                        "invoke_rollback",
                        return_value={"final_health": True},
                    ) as invoke,
                    mock.patch.object(
                        f1,
                        "close_transaction",
                        return_value={"status": "closed"},
                    ),
                ):
                    result = f1.recover_approved_rollback(spec, args)
                self.assertEqual(result["status"], "closed")
                invoke.assert_called_once()
                self.assertTrue(invoke.call_args.kwargs["from_native"])
                self.assertEqual(
                    invoke.call_args.kwargs["pre_spawn_retry_index"],
                    1,
                )

                f1.append_record(
                    journal,
                    "RECOVERY_ROLLBACK",
                    "rollback-transfer-started",
                    {
                        "rollback_sha256": spec.rollback.sha256,
                        "rollback_attempt_limit": 1,
                        "rollback_process_started": None,
                        "candidate_replay": False,
                        "recovery_mode": "from-native",
                        "prior_pre_spawn_rejections": 1,
                    },
                    manifest_sha256=spec.stage.manifest_sha256,
                    run_id=spec.stage.run_id,
                )
                f1.append_record(
                    journal,
                    "RECOVERY_ROLLBACK",
                    "rollback-invocation-failed",
                    {
                        "candidate_replay": False,
                        "rollback_retry_forbidden": True,
                        "record": {
                            "returncode": 1,
                            "process_started": True,
                        },
                    },
                    manifest_sha256=spec.stage.manifest_sha256,
                    run_id=spec.stage.run_id,
                )
                f1.append_record(
                    journal,
                    "RECOVERY_ROLLBACK",
                    "rollback-transfer-started",
                    {
                        "rollback_sha256": spec.rollback.sha256,
                        "rollback_attempt_limit": 1,
                        "rollback_process_started": None,
                        "candidate_replay": False,
                        "recovery_mode": "from-native",
                        "prior_pre_spawn_rejections": 1,
                    },
                    manifest_sha256=spec.stage.manifest_sha256,
                    run_id=spec.stage.run_id,
                )
                retry_log = (
                    transaction
                    / "rollback-flash-pre-spawn-retry-0001.raw.log"
                )
                retry_log.write_bytes(b"")
                retry_log.chmod(0o600)
                retry_record = {
                    **f1.command_record(retry_log, 125),
                    "process_started": False,
                    "execution_error": {
                        "type": "OSError",
                        "stage": "process-spawn",
                        "errno": 2,
                    },
                    "phase_classification": {
                        "local_image_validated": False,
                        "native_recovery_requested": False,
                        "recovery_endpoint_selected": False,
                        "payload_transfer_started": False,
                        "boot_write_started": False,
                        "boot_write_completed": False,
                        "readback_completed": False,
                    },
                }
                f1.append_record(
                    journal,
                    "RECOVERY_ROLLBACK",
                    "rollback-process-not-started",
                    {
                        "candidate_replay": False,
                        "rollback_process_started": False,
                        "rollback_transfer_count": 0,
                        "rollback_retry_preserved": True,
                        "record": retry_record,
                    },
                    manifest_sha256=spec.stage.manifest_sha256,
                    run_id=spec.stage.run_id,
                )
                with (
                    mock.patch.object(f1, "verify_local_closure"),
                    mock.patch.object(
                        f1,
                        "verify_final_health",
                        side_effect=f1.ContractError(
                            "historical started rollback cannot be retried"
                        ),
                    ),
                    mock.patch.object(f1, "invoke_rollback") as history_invoke,
                    self.assertRaisesRegex(
                        f1.ContractError,
                        "historical started rollback",
                    ),
                ):
                    f1.recover_approved_rollback(spec, args)
                history_invoke.assert_not_called()
            finally:
                f1.PRIVATE_RUN_BASE = old_base

    def test_incomplete_journal_temp_is_ignored_by_sequence(self) -> None:
        spec = sample_spec()
        with tempfile.TemporaryDirectory(dir=f1.staging.PRIVATE_ROOT) as temp_dir:
            transaction = Path(temp_dir)
            journal = transaction / "journal"
            journal.mkdir()
            (journal / ".0000-preflight.json.tmp-interrupted").write_bytes(b"{")
            path = f1.append_record(
                journal,
                "PREFLIGHT",
                "preflight",
                {},
                manifest_sha256=spec.stage.manifest_sha256,
                run_id=spec.stage.run_id,
            )
            self.assertEqual(path.name, "0000-preflight.json")
            self.assertEqual(len(f1.read_journal(spec, transaction)), 1)

    def test_journal_rejects_float_sequence_and_noncanonical_timestamp(self) -> None:
        spec = sample_spec()
        with tempfile.TemporaryDirectory(dir=f1.staging.PRIVATE_ROOT) as temp_dir:
            transaction = Path(temp_dir)
            path = f1.append_record(
                transaction / "journal",
                "PREFLIGHT",
                "preflight",
                {},
                manifest_sha256=spec.stage.manifest_sha256,
                run_id=spec.stage.run_id,
            )
            value = json.loads(path.read_text())
            value["sequence"] = 0.0
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(f1.ContractError, "invalid journal"):
                f1.read_journal(spec, transaction)
            value["sequence"] = 0
            value["timestamp_utc"] = "not-utc"
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(f1.ContractError, "invalid journal"):
                f1.read_journal(spec, transaction)

    def test_recovery_source_has_no_candidate_invocation(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        recovery = source[
            source.index("def recover_approved_rollback("):
            source.index("def simulate_transaction(")
        ]
        self.assertNotIn("rollback=False", recovery)
        self.assertNotIn("flash_command(spec, args, rollback=False)", recovery)

    def test_tracked_source_has_no_concrete_device_identity(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        self.assertNotRegex(text, r"/dev/serial/by-id/\S+")
        self.assertNotRegex(text, r"ttyACM[0-9]+")
        self.assertNotRegex(text, r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b")

    def test_rollback_ambiguity_is_an_explicit_stop(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn('"rollback_retry_forbidden": True', source)
        self.assertIn("do not repeat it automatically", source)

    def test_only_boot_images_reach_flash_command(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        function = source[
            source.index("def flash_command("):
            source.index("def validate_stage_result(")
        ]
        self.assertIn("spec.rollback if rollback else spec.candidate", function)
        for forbidden in (
            "vendor_boot",
            "vbmeta",
            "userdata",
            "recovery.img",
            "super.img",
        ):
            self.assertNotIn(forbidden, function)


if __name__ == "__main__":
    unittest.main()
