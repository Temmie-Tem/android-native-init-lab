"""Host-only contract tests for A90 V3403 absent-only rootfs staging."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
import types
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path

from _loader import load_script


stage = load_script(
    "workspace/public/src/scripts/server-distro/a90_v3403_absent_only_staging.py"
)
SOURCE = Path(
    "workspace/public/src/scripts/server-distro/a90_v3403_absent_only_staging.py"
)


def sample_spec() -> object:
    return types.SimpleNamespace(
        local_size=2147483648,
        local_sha256="a" * 64,
        remote_final=str(stage.REMOTE_FINAL),
        remote_work=str(stage.REMOTE_WORK),
        remote_stage_dir=(
            "/mnt/sdext/a90/runtime/.a90-stage-"
            "a90-v3403-debian-f1-20260730-02"
        ),
        remote_payload=(
            "/mnt/sdext/a90/runtime/.a90-stage-"
            "a90-v3403-debian-f1-20260730-02/payload.img"
        ),
        tcpctl_host=Path("workspace/public/src/scripts/revalidation/tcpctl_host.py"),
        local_image=Path("/private/keyed.img"),
    )


class A90V3403AbsentOnlyStagingTests(unittest.TestCase):
    def test_execution_support_closure_is_exact(self) -> None:
        expected = {
            "run_d1_chroot_mvp.py",
            "_workspace_bootstrap.py",
            "a90_bridge.py",
            "a90_serial_lock.py",
            "a90ctl.py",
            "serial_tcp_bridge.py",
            "evidence.py",
        }
        self.assertEqual(
            {path.name for path in stage.REQUIRED_SUPPORT_FILES},
            expected,
        )

    def test_fixed_paths_and_stage_derivation(self) -> None:
        self.assertEqual(
            str(stage.REMOTE_FINAL),
            "/mnt/sdext/a90/runtime/debian-bookworm-arm64-d3-sysvinit-v3403-keyed.img",
        )
        self.assertEqual(
            str(stage.REMOTE_WORK),
            "/mnt/sdext/a90/runtime/d3-handoff-work.img",
        )
        self.assertEqual(
            str(stage.derive_stage_dir("a90-v3403-debian-f1-20260730-02")),
            (
                "/mnt/sdext/a90/runtime/.a90-stage-"
                "a90-v3403-debian-f1-20260730-02"
            ),
        )
        with self.assertRaises(stage.ContractError):
            stage.derive_stage_dir("b" * 64)

    def test_connected_d0_semantics_bind_target_health_and_boot_artifacts(self) -> None:
        candidate = stage.BoundFile("candidate", Path("/private/candidate"), 4096, "a" * 64)
        rollback = stage.BoundFile("rollback", Path("/private/rollback"), 8192, "b" * 64)
        runner = stage.BoundFile("runner", Path("/public/runner"), 1024, "c" * 64)
        value = {
            "schema": stage.D0_RESULT_SCHEMA,
            "outcome": stage.D0_RESULT_OUTCOME,
            "target": {
                "profile": stage.TARGET_PROFILE,
                "matching_a90_usb_devices": 1,
                "bridge_selected_realpath": "/dev/exact-private-binding",
            },
            "health": {
                "bridge_exact": True,
                "bridge_running": True,
                "version": stage.EXPECTED_BASELINE_VERSION,
                "version_build": stage.EXPECTED_BASELINE_BUILD,
                "pstore_entries": 0,
                "selftest": {"fail": 0},
            },
            "safety": {
                "device_write": False,
                "flash": False,
                "payload_sent": False,
                "reboot_requested": False,
                "rootfs_staged": False,
                "userdata_touched": False,
            },
            "artifacts": {
                "candidate_boot": {"size": 4096, "sha256": "a" * 64},
                "rollback_boot": {"size": 8192, "sha256": "b" * 64},
            },
            "repository": {"runner_sha256": "c" * 64},
        }
        stage.validate_connected_d0_evidence(
            value,
            expected_realpath="/dev/exact-private-binding",
            candidate=candidate,
            rollback=rollback,
            flash_runner=runner,
        )
        value["target"]["matching_a90_usb_devices"] = 2
        with self.assertRaisesRegex(stage.ContractError, "target binding"):
            stage.validate_connected_d0_evidence(
                value,
                expected_realpath="/dev/exact-private-binding",
                candidate=candidate,
                rollback=rollback,
                flash_runner=runner,
            )

    def test_path_preflight_semantics_require_all_three_exact_paths(self) -> None:
        run_id = "a90-v3403-debian-f1-20260730-02"
        connected = stage.BoundFile(
            "connected",
            Path("/private/connected.json"),
            100,
            "d" * 64,
        )
        stage_dir = str(stage.derive_stage_dir(run_id))
        value = {
            "schema": stage.PATH_PREFLIGHT_SCHEMA,
            "run_id": run_id,
            "target_binding": {
                "connected_d0_result": str(connected.path),
                "connected_d0_result_sha256": connected.sha256,
                "target_profile": stage.TARGET_PROFILE,
                "exact_a90_bridge": True,
            },
            "read": {
                "kind": "bounded-connected-read-only",
                "framed_command": "run",
                "framed_rc": 0,
                "framed_status": "ok",
                "paths": {
                    str(stage.REMOTE_FINAL): "absent",
                    str(stage.REMOTE_WORK): "absent",
                    stage_dir: "absent",
                },
            },
            "safety": {
                "device_write": False,
                "payload_sent": False,
                "reboot_requested": False,
                "flash": False,
                "userdata_touched": False,
            },
        }
        stage.validate_path_preflight_evidence(
            value,
            run_id=run_id,
            connected_d0=connected,
            remote_final=str(stage.REMOTE_FINAL),
            remote_work=str(stage.REMOTE_WORK),
            remote_stage_dir=stage_dir,
        )
        del value["read"]["paths"][stage_dir]
        with self.assertRaisesRegex(stage.ContractError, "all exact paths"):
            stage.validate_path_preflight_evidence(
                value,
                run_id=run_id,
                connected_d0=connected,
                remote_final=str(stage.REMOTE_FINAL),
                remote_work=str(stage.REMOTE_WORK),
                remote_stage_dir=stage_dir,
            )

    def test_remote_final_rejects_every_other_path(self) -> None:
        self.assertEqual(
            stage.validate_remote_final(str(stage.REMOTE_FINAL)),
            str(stage.REMOTE_FINAL),
        )
        for value in (
            "/mnt/sdext/a90/runtime/other.img",
            "/mnt/sdext/a90/runtime/../escape.img",
            "/data/local/tmp/rootfs.img",
            str(stage.REMOTE_WORK),
        ):
            with self.subTest(value=value):
                with self.assertRaises(stage.ContractError):
                    stage.validate_remote_final(value)

    def test_manifest_must_not_be_group_or_world_writable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = Path(temp_dir) / "manifest.json"
            payload = b"{}\n"
            manifest.write_bytes(payload)
            digest = hashlib.sha256(payload).hexdigest()
            manifest.chmod(0o664)
            with self.assertRaisesRegex(stage.ContractError, "group/world-writable"):
                stage.load_manifest(manifest, digest)
            manifest.chmod(0o600)
            parsed, actual = stage.load_manifest(manifest, digest)
            self.assertEqual(parsed, {})
            self.assertEqual(actual, digest)

    def test_pstore_health_matches_only_the_exact_pstore_row(self) -> None:
        healthy = "helpers: entries=7\npstore=fs=yes mounted=no entries=0 module=yes\n"
        unhealthy = "helpers: entries=0\npstore=fs=yes mounted=no entries=2 module=yes\n"
        missing = "helpers: entries=0\n"
        self.assertIsNotNone(stage.PSTORE_ZERO_RE.search(healthy))
        self.assertIsNone(stage.PSTORE_ZERO_RE.search(unhealthy))
        self.assertIsNone(stage.PSTORE_ZERO_RE.search(missing))

    def test_preflight_is_read_only_and_requires_ext4_rw_and_absence(self) -> None:
        script = stage.remote_readonly_preflight_script(sample_spec())
        self.assertIn('[ "$FS" = "ext4" ]', script)
        self.assertIn("*,rw,*", script)
        self.assertIn("/bin/busybox --list", script)
        self.assertIn("chmod ln mkdir rm rmdir sha256sum stat sync", script)
        self.assertIn('"$FINAL" "$WORK" "$STAGE"', script)
        self.assertIn("[ -e \"$PATH_ITEM\" ] || [ -L \"$PATH_ITEM\" ]", script)
        for forbidden in (
            "\n/bin/busybox mkdir ",
            "\n/bin/busybox rm ",
            "\n/bin/busybox ln ",
            "\n/bin/busybox mv ",
            "\n/bin/busybox chmod ",
            "\n/bin/busybox dd ",
        ):
            self.assertNotIn(forbidden, script)

    def test_reserve_is_absent_only_and_nonrecursive(self) -> None:
        script = stage.remote_reserve_script(sample_spec())
        self.assertIn('/bin/busybox mkdir "$STAGE"', script)
        self.assertNotIn("mkdir -p", script)
        self.assertIn('/bin/busybox chmod 700 "$STAGE"', script)
        self.assertNotIn("rm -rf", script)
        self.assertNotIn("mv -f", script)

    def test_publish_uses_hardlink_no_clobber_and_inode_identity(self) -> None:
        script = stage.remote_publish_script(sample_spec())
        self.assertIn('[ ! -e "$FINAL" ]', script)
        self.assertIn('[ ! -L "$FINAL" ]', script)
        self.assertIn('/bin/busybox ln "$PAYLOAD" "$FINAL"', script)
        self.assertIn('PAYLOAD_ID=$(/bin/busybox stat -c %d:%i "$PAYLOAD")', script)
        self.assertIn('FINAL_ID=$(/bin/busybox stat -c %d:%i "$FINAL")', script)
        self.assertIn('[ "$PAYLOAD_ID" = "$FINAL_ID" ]', script)
        self.assertIn('FINAL_SHA=$(/bin/busybox sha256sum "$FINAL")', script)
        self.assertGreaterEqual(script.count("/bin/busybox sync"), 2)
        for forbidden in ("mv -f", 'cp "$PAYLOAD" "$FINAL"', "rm -rf", "/dev/block/", "userdata"):
            self.assertNotIn(forbidden, script)

    def test_cleanup_never_removes_a_published_final(self) -> None:
        script = stage.remote_cleanup_script(sample_spec())
        final_branch = script[
            script.index('if [ -e "$FINAL" ]'):script.index(
                'if [ -d "$STAGE" ]'
            )
        ]
        self.assertIn("final_preserved=1", final_branch)
        self.assertNotIn('rm "$FINAL"', script)
        self.assertNotIn("rm -rf", script)

    def test_transfer_targets_only_the_exclusive_stage_payload(self) -> None:
        spec = sample_spec()
        args = types.SimpleNamespace(
            bridge_host="localhost",
            bridge_port=54321,
            device_ip="usb-local-device",
            bridge_timeout=120.0,
            connect_timeout=10.0,
            tcp_timeout=60.0,
            toybox="/bin/toybox",
            transfer_timeout=1200.0,
            transfer_delay=2.0,
        )
        command = stage.transfer_command(spec, args)
        target_index = command.index("--device-binary") + 1
        self.assertEqual(command[target_index], spec.remote_payload)
        self.assertNotIn(spec.remote_final, command)
        self.assertNotIn(spec.remote_work, command)

    def test_every_prepublication_fault_leaves_final_absent(self) -> None:
        publish_index = stage.STAGE_STEPS.index("publish_link")
        for fail_step in stage.STAGE_STEPS[:publish_index]:
            with self.subTest(fail_step=fail_step):
                result = stage.simulate_stage(fail_step=fail_step)
                self.assertFalse(result.final_exists)
                self.assertFalse(result.completed)
                self.assertFalse(result.candidate_allowed)

    def test_postpublication_fault_preserves_exact_final_but_blocks_candidate(self) -> None:
        for fail_step in ("verify_link_identity", "verify_final", "remove_payload_link", "remove_stage_dir", "complete"):
            with self.subTest(fail_step=fail_step):
                result = stage.simulate_stage(fail_step=fail_step)
                self.assertTrue(result.final_exists)
                self.assertFalse(result.final_is_foreign)
                self.assertFalse(result.completed)
                self.assertFalse(result.candidate_allowed)

    def test_preexisting_paths_fail_before_reservation(self) -> None:
        for kwargs in (
            {"preexisting_final": True},
            {"preexisting_work": True},
            {"preexisting_stage": True},
        ):
            with self.subTest(kwargs=kwargs):
                result = stage.simulate_stage(**kwargs)
                self.assertEqual(result.error, "preexisting-path")
                self.assertNotIn("reserve_stage_dir", result.history)
                self.assertFalse(result.candidate_allowed)

    def test_final_race_is_not_overwritten(self) -> None:
        result = stage.simulate_stage(final_race_before_publish=True)
        self.assertEqual(result.error, "publish-no-clobber")
        self.assertTrue(result.final_exists)
        self.assertTrue(result.final_is_foreign)
        self.assertFalse(result.candidate_allowed)

    def test_success_requires_complete_cleanup_and_verified_final(self) -> None:
        result = stage.simulate_stage()
        self.assertTrue(result.completed)
        self.assertTrue(result.candidate_allowed)
        self.assertTrue(result.final_exists)
        self.assertTrue(result.final_verified)
        self.assertFalse(result.final_is_foreign)
        self.assertFalse(result.payload_exists)
        self.assertFalse(result.stage_dir_exists)

    def test_publish_step_failure_leaves_final_absent(self) -> None:
        result = stage.simulate_stage(fail_step="publish_link")
        self.assertEqual(result.error, "publish_link")
        self.assertFalse(result.final_exists)
        self.assertFalse(result.candidate_allowed)

    def test_host_link_primitive_refuses_existing_final(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            payload = root / "payload"
            final = root / "final"
            payload.write_bytes(b"payload")
            final.write_bytes(b"foreign")
            with self.assertRaises(FileExistsError):
                os.link(payload, final)
            self.assertEqual(final.read_bytes(), b"foreign")
            self.assertEqual(payload.read_bytes(), b"payload")

    def test_source_contract_is_closed(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        self.assertEqual(stage.source_contract_issues(source), ())

    def test_source_contract_rejects_overwriting_final_publication(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        mutated = source.replace(
            '/bin/busybox ln "$PAYLOAD" "$FINAL"',
            '/bin/busybox mv -f "$PAYLOAD" "$FINAL"',
            1,
        )
        issues = stage.source_contract_issues(mutated)
        self.assertTrue(any("publish contract missing" in issue for issue in issues))
        self.assertTrue(any("forbidden token" in issue for issue in issues))

    def test_source_contract_rejects_missing_inode_identity(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        mutated = source.replace(
            'FINAL_ID=$(/bin/busybox stat -c %d:%i "$FINAL")',
            "FINAL_ID=unchecked",
            1,
        )
        issues = stage.source_contract_issues(mutated)
        self.assertTrue(any("FINAL_ID=" in issue for issue in issues))

    def test_default_cli_has_no_live_mode(self) -> None:
        parser = stage.build_parser()
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
        self.assertFalse(args.execute_approved_stage)
        self.assertEqual(args.approved_manifest_sha256, "")
        self.assertEqual(args.approved_adapter_sha256, "")
        self.assertEqual(args.approved_run_id, "")
        self.assertEqual(args.bridge_host, "localhost")
        self.assertIsNone(args.device_ip)
        self.assertIsNone(args.approval)

    def test_tracked_closure_has_no_concrete_network_address(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        self.assertNotRegex(text, r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b")

    def test_live_gate_rejects_draft_before_device_calls(self) -> None:
        spec = types.SimpleNamespace(
            manifest_sha256="a" * 64,
            run_id="a90-v3403-debian-f1-20260730-02",
        )
        manifest = {
            "schema": "a90_native_init_f1_draft_v1",
            "status": "draft-host-only-not-ready-for-approval",
        }
        args = types.SimpleNamespace(
            approved_manifest_sha256="a" * 64,
            approved_adapter_sha256=stage.sha256_file(SOURCE.resolve()),
            approved_run_id=spec.run_id,
        )
        with self.assertRaisesRegex(stage.ContractError, "non-final manifest schema"):
            stage.execute_approved_stage(spec, manifest, args)

    def test_live_run_dir_is_exact_and_private(self) -> None:
        spec = types.SimpleNamespace(run_id="a90-v3403-debian-f1-20260730-02")
        expected = (
            stage.PRIVATE_RUN_BASE
            / spec.run_id
            / "staging-live"
        ).resolve()
        self.assertEqual(stage.exact_live_run_dir(spec, expected), expected)
        for path in (
            Path("/tmp/a90-stage"),
            stage.PRIVATE_RUN_BASE / spec.run_id / "other",
            stage.PRIVATE_RUN_BASE / "wrong-run" / "staging-live",
        ):
            with self.subTest(path=path):
                with self.assertRaises(stage.ContractError):
                    stage.exact_live_run_dir(spec, path)

    def test_abort_records_publish_attempt_as_ambiguous(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("publish_attempted = True", source)
        self.assertIn('"published_may_exist": publish_attempted', source)
        self.assertIn('"publish_completed": published', source)

    def test_journal_records_are_exclusive_and_ordered(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            journal = Path(temp_dir) / "journal"
            first = stage.append_record(
                journal,
                "first",
                {"value": 1},
                manifest_sha256="a" * 64,
                run_id="a90-v3403-debian-f1-20260730-02",
            )
            second = stage.append_record(
                journal,
                "second",
                {"value": 2},
                manifest_sha256="a" * 64,
                run_id="a90-v3403-debian-f1-20260730-02",
            )
            self.assertEqual(first.name, "0000-first.json")
            self.assertEqual(second.name, "0001-second.json")
            first_payload = json.loads(first.read_text())
            second_payload = json.loads(second.read_text())
            self.assertEqual(first_payload["sequence"], 0)
            self.assertEqual(second_payload["sequence"], 1)
            self.assertEqual(first_payload["manifest_sha256"], "a" * 64)
            self.assertEqual(
                first_payload["run_id"],
                "a90-v3403-debian-f1-20260730-02",
            )

    def test_private_result_writer_is_0600_under_permissive_umask(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "result.json"
            previous = os.umask(0o002)
            try:
                stage.write_private_json_exclusive(path, {"status": "PASS"})
            finally:
                os.umask(previous)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(json.loads(path.read_text())["status"], "PASS")

    def test_incomplete_journal_temp_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            journal = Path(temp_dir) / "journal"
            journal.mkdir()
            (journal / ".0000-first.json.tmp-interrupted").write_bytes(b"{")
            path = stage.append_record(
                journal,
                "first",
                {"value": 1},
                manifest_sha256="a" * 64,
                run_id="a90-v3403-debian-f1-20260730-02",
            )
            self.assertEqual(path.name, "0000-first.json")
            self.assertEqual(json.loads(path.read_text())["sequence"], 0)

    def test_live_staging_reopens_exact_parent_approval(self) -> None:
        run_id = "a90-v3403-debian-f1-20260730-02"
        spec = types.SimpleNamespace(
            run_id=run_id,
            manifest_sha256="a" * 64,
            adapter_sha256="b" * 64,
            local_sha256="c" * 64,
        )
        manifest = {
            "target": {
                "connected_d0_result": {"sha256": "1" * 64},
                "connected_path_preflight": {"sha256": "2" * 64},
                "recovery_adb_serial_sha256": "3" * 64,
            },
            "candidate_boot": {"sha256": "d" * 64},
            "rollback_boot": {"sha256": "e" * 64},
            "f1_orchestrator": {"sha256": "f" * 64},
            "transport": {"runner_sha256": "4" * 64},
        }
        binding = {
            "schema": "a90_v3403_f1_approval_binding_v1",
            "run_id": run_id,
            "manifest_sha256": "a" * 64,
            "orchestrator_sha256": "f" * 64,
            "staging_adapter_sha256": "b" * 64,
            "flash_runner_sha256": "4" * 64,
            "candidate_boot_sha256": "d" * 64,
            "rollback_boot_sha256": "e" * 64,
            "rootfs_sha256": "c" * 64,
            "connected_d0_sha256": "1" * 64,
            "connected_path_preflight_sha256": "2" * 64,
            "recovery_adb_serial_sha256": "3" * 64,
            "candidate_attempt_limit": 1,
            "mandatory_rollback_preapproved_after_candidate_start": True,
            "candidate_replay": False,
            "only_partition_payload": "boot",
        }
        binding_sha = stage.json_sha256(binding)
        prepared = {
            "schema": stage.APPROVAL_PREPARED_SCHEMA,
            "created_utc": "2026-07-30T00:00:00Z",
            "run_id": run_id,
            "manifest_sha256": "a" * 64,
            "approval_binding": binding,
            "approval_binding_sha256": binding_sha,
            "approval_token": stage.APPROVAL_PREFIX + binding_sha,
            "device_contact": False,
            "device_write": False,
            "f1_authorized": False,
            "live_authorized": False,
        }
        with tempfile.TemporaryDirectory(dir=stage.PRIVATE_ROOT) as temp_dir:
            old_base = stage.PRIVATE_RUN_BASE
            try:
                stage.PRIVATE_RUN_BASE = Path(temp_dir)
                path = Path(temp_dir) / run_id / "approval-prepared.json"
                stage.write_private_json_exclusive(path, prepared)
                accepted = stage.validate_parent_approval(
                    spec,
                    manifest,
                    prepared["approval_token"],
                )
                self.assertEqual(accepted["approval_binding_sha256"], binding_sha)
                with self.assertRaisesRegex(stage.ContractError, "does not match"):
                    stage.validate_parent_approval(spec, manifest, "wrong-token")
            finally:
                stage.PRIVATE_RUN_BASE = old_base


if __name__ == "__main__":
    unittest.main()
