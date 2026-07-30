"""Host-only tests for the minimal A90 V3403 F1 orchestrator."""

from __future__ import annotations

import hashlib
import json
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
        candidate_boot_timeout=300,
        rollback_boot_timeout=300,
    )


def sample_args() -> object:
    return types.SimpleNamespace(
        approved_manifest_sha256="a" * 64,
        approved_orchestrator_sha256=f1.sha256_file(SOURCE.resolve()),
        approved_run_id="a90-v3403-debian-f1-20260730-02",
        bridge_host="localhost",
        bridge_port=54321,
        bridge_timeout=180.0,
        remote_timeout=180.0,
        transfer_timeout=1200.0,
        ssh_connect_timeout=8.0,
    )


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
            "    flash_command(spec, args, rollback=False)\n\n" + marker,
            1,
        )
        issues = f1.source_contract_issues(mutated)
        self.assertIn("recovery contains a candidate execution route", issues)

    def test_candidate_flash_command_is_exact_and_boot_only(self) -> None:
        command = f1.flash_command(sample_spec(), sample_args(), rollback=False)
        self.assertEqual(command[1], str(f1.NATIVE_FLASH_PATH))
        self.assertIn("/private/candidate.img", command)
        self.assertIn("d" * 64, command)
        self.assertIn("candidate-version build=candidate-build", command)
        self.assertIn("--from-native", command)
        self.assertNotIn("--allow-unpinned-image", command)
        self.assertNotIn("--boot-block", command)
        self.assertNotIn("userdata", " ".join(command))

    def test_rollback_from_recovery_is_exact_and_not_from_native(self) -> None:
        command = f1.flash_command(
            sample_spec(),
            sample_args(),
            rollback=True,
            recovery_serial="recovery-target",
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
            f1.approved_bindings(spec, sample_args())

    def test_approved_binding_rejects_wrong_exact_hash(self) -> None:
        args = sample_args()
        args.approved_orchestrator_sha256 = "0" * 64
        with self.assertRaisesRegex(f1.ContractError, "orchestrator"):
            f1.approved_bindings(sample_spec(), args)

    def test_recovery_serial_is_digest_bound(self) -> None:
        spec = sample_spec()
        self.assertEqual(
            f1.validate_recovery_serial(spec, "recovery-target"),
            "recovery-target",
        )
        with self.assertRaisesRegex(f1.ContractError, "does not match"):
            f1.validate_recovery_serial(spec, "other-target")

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
        with tempfile.TemporaryDirectory() as temp_dir:
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
        with tempfile.TemporaryDirectory() as temp_dir:
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
        with tempfile.TemporaryDirectory() as temp_dir:
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

    def test_stage_result_must_allow_the_exact_candidate(self) -> None:
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
                journal = result_dir / "journal"
                journal.mkdir()
                journal_record = journal / "0000-closed.json"
                journal_record.write_text(
                    json.dumps(
                        {
                            "schema": "a90_v3403_absent_only_stage_journal_v1",
                            "state": "closed",
                            "result": result,
                        }
                    ),
                    encoding="utf-8",
                )
                journal_record.chmod(0o600)
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
                with self.assertRaisesRegex(f1.ContractError, "journal is absent"):
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
        self.assertEqual(args.approved_manifest_sha256, "")

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
