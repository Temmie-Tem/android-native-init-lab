"""Focused host-only tests for the A90 attended D1 session runner."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_DIR = REPO_ROOT / "workspace/public/src/scripts/server-distro"
REVAL_DIR = REPO_ROOT / "workspace/public/src/scripts/revalidation"
for path in (SERVER_DIR, REVAL_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import a90_transition_d1_session_v1 as d1  # noqa: E402
import a90_transition_engine_v2 as engine  # noqa: E402
import a90_v3403_absent_only_staging as staging  # noqa: E402
from a90_transition_contract_v2 import SessionPreflight  # noqa: E402


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_private(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, bytes):
        path.write_bytes(value)
    else:
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)


def bound(path: Path) -> d1.BoundFile:
    return d1.BoundFile(path, path.stat().st_size, digest(path))


class A90TransitionD1SessionV1Tests(unittest.TestCase):
    def resident_fixture(self, root: Path) -> tuple[Path, Path, str]:
        run_id = "a90-v3406-debian-display-f1-20260802-01"
        resident_dir = root / "resident"
        candidate = resident_dir / "candidate.img"
        rollback = resident_dir / "rollback.img"
        rootfs = resident_dir / "rootfs.img"
        observer_key = resident_dir / "observer-key"
        for path, body in (
            (candidate, b"candidate"),
            (rollback, b"rollback"),
            (rootfs, b"rootfs"),
            (observer_key, b"private-key"),
        ):
            write_private(path, body)
        manifest = {
            "schema": staging.RESIDENT_INSTALL_MANIFEST_SCHEMA,
            "status": staging.FINAL_MANIFEST_STATUS,
            "run_id": run_id,
            "candidate_boot": {
                "path": str(candidate),
                "size": candidate.stat().st_size,
                "sha256": digest(candidate),
                "partition": "boot",
                "expected_version": "0.11.161",
                "expected_build": "phase2-display-v1-native-handoff",
            },
            "rollback_boot": {
                "path": str(rollback),
                "size": rollback.stat().st_size,
                "sha256": digest(rollback),
                "partition": "boot",
                "expected_version": "0.9.285",
                "expected_build": "v2321-usb-clean-identity-rodata",
            },
            "debian_rootfs": {
                "handoff_command": [
                    d1.base.HANDOFF_COMMAND,
                    d1.base.HANDOFF_TOKEN,
                    "/mnt/sdext/a90/runtime/rootfs.img",
                    digest(rootfs),
                ],
                "keyed_source": {
                    "local_path": str(rootfs),
                    "device_path": "/mnt/sdext/a90/runtime/rootfs.img",
                    "size": rootfs.stat().st_size,
                    "sha256": digest(rootfs),
                },
                "work_copy": {"device_path": d1.WORK_PATH},
                "observer": {
                    "private_key_path": str(observer_key),
                    "public_key_sha256": "1" * 64,
                    "device_ip": "192.0.2.2",
                    "device_port": 2222,
                    "host_ncm_profile": "a90-test-ncm",
                    "transport_scope": d1.base.OBSERVER_TRANSPORT_SCOPE,
                    "wifi_or_external_network": False,
                },
            },
            "target": {
                "profile": staging.TARGET_PROFILE,
                "bridge_selected_exact": True,
                "bridge_device": "/dev/serial/by-id/usb-A90-LNX_TEST-if00",
                "bridge_selected_realpath": "/dev/ttyACM0",
                "recovery_adb_serial_sha256": "2" * 64,
                "recovery": "attended physical recovery",
            },
            "observation": {
                "handoff_attempt_limit": 1,
                "handoff_timeout_sec": 1200,
                "ssh_marker_timeout_sec": 120,
                "candidate_return_timeout_sec": 240,
            },
        }
        manifest_path = resident_dir / "manifest.json"
        write_private(manifest_path, manifest)
        manifest_sha = digest(manifest_path)
        journal_dir = resident_dir / "f1-live" / "journal"
        health = {
            "native": {
                "exact_bridge": True,
                "version": {"text": "version: 0.11.161 build=phase2-display-v1-native-handoff\r\n"},
                "selftest": {"text": "selftest: pass=12 warn=1 fail=0 duration=1ms entries=13\r\n"},
            },
            "pstore": {"mounted_read_only": True, "entries": []},
            "rootfs": {
                "rc": 0,
                "text": "A90F1_SOURCE_PRECHECK exact=1 work_absent=1\r\n",
            },
            "ncm": {
                "same_current_acm_usb_parent": True,
                "exact_interface_count": 1,
                "profile_bound": True,
                "ready": {
                    "verified_a90_ncm": True,
                    "direct_route": True,
                    "host_cidr_present": True,
                    "device_ping": True,
                },
            },
        }
        for sequence, action in enumerate(d1.RESIDENT_ACTIONS):
            record = {
                "schema": d1.base.JOURNAL_SCHEMA,
                "sequence": sequence,
                "run_id": run_id,
                "manifest_sha256": manifest_sha,
                "action": action,
            }
            if action == "candidate-health-verified":
                record["health"] = health
            if action == "closed":
                record.update(
                    {
                        "state": "RESIDENT_INSTALLED_CLOSED",
                        "status": "PASS_A90_RESIDENT_INSTALLED",
                        "device_safety_state": "RESIDENT_HEALTHY",
                        "candidate_transfer_count": 1,
                        "candidate_replay": False,
                        "candidate_health_check_count": 1,
                        "resident_reboot_count": 0,
                        "rollback_transfer_count": 0,
                        "rollback_required": False,
                    }
                )
            write_private(journal_dir / f"{sequence:04d}-{action}.json", record)
        return manifest_path, journal_dir, manifest_sha

    def session_spec(self, root: Path) -> d1.SessionSpec:
        files: dict[str, d1.BoundFile] = {}
        for role in d1.SOURCE_PATHS:
            path = root / f"{role}.py"
            write_private(path, role.encode())
            files[role] = bound(path)
        manifest = root / "manifest.json"
        candidate = root / "candidate.img"
        rollback = root / "rollback.img"
        rootfs = root / "rootfs.img"
        resident_manifest = root / "resident.json"
        resident_journal = root / "terminal.json"
        observer = root / "observer-key"
        for path, body in (
            (manifest, b"manifest"),
            (candidate, b"candidate"),
            (rollback, b"rollback"),
            (rootfs, b"rootfs"),
            (resident_manifest, b"resident"),
            (resident_journal, b"journal"),
            (observer, b"observer"),
        ):
            write_private(path, body)
        return d1.SessionSpec(
            manifest_path=manifest,
            manifest_sha256=digest(manifest),
            run_id="a90-d1-attended-20260802-01",
            resident_run_id="a90-v3406-debian-display-f1-20260802-01",
            resident_manifest=bound(resident_manifest),
            resident_journal=(bound(resident_journal),),
            candidate=bound(candidate),
            rollback=bound(rollback),
            rootfs=bound(rootfs),
            candidate_version="0.11.161",
            candidate_build="phase2-display-v1-native-handoff",
            remote_final="/mnt/sdext/a90/runtime/rootfs.img",
            remote_work=d1.WORK_PATH,
            bridge_device="/dev/serial/by-id/usb-A90-LNX_TEST-if00",
            bridge_realpath="/dev/ttyACM0",
            recovery_serial_sha256="2" * 64,
            observer_key=observer,
            observer_public_key_sha256="3" * 64,
            observer_device="192.0.2.2",
            observer_port=2222,
            observer_host_ncm_profile="a90-test-ncm",
            handoff_command=(
                d1.base.HANDOFF_COMMAND,
                d1.base.HANDOFF_TOKEN,
                "/mnt/sdext/a90/runtime/rootfs.img",
                digest(rootfs),
            ),
            handoff_timeout=1200,
            ssh_marker_timeout=120,
            candidate_return_timeout=240,
            source_closure=files,
            transaction_dir=root / d1.SESSION_DIR_NAME,
            session_lock_path=root / d1.SESSION_LOCK_NAME,
            session_duration_sec=3_600,
            max_actions=4,
            recovery_profile="attended physical recovery",
        )

    def exact_candidate_return(self, spec: d1.SessionSpec) -> dict[str, object]:
        def epoch(devnum: int) -> dict[str, object]:
            return {
                "schema": d1.base.RETURN_EPOCH_SCHEMA,
                "selected_realpath": spec.bridge_realpath,
                "tty_st_dev": 1,
                "tty_st_ino": 2,
                "tty_st_rdev": 3,
                "usb_busnum": 4,
                "usb_devnum": devnum,
            }

        return {
            "exact_bridge": True,
            "selected_realpath": spec.bridge_realpath,
            "return_epoch": {
                "proof": True,
                "pre_handoff": epoch(5),
                "returned": epoch(6),
                "usb_serial_epoch_changed": True,
            },
            "native_epoch_version_proven": True,
            "channel": {},
            "version": {},
            "selftest": {},
            "device_command_sequences": 1,
            "candidate_return_modemmanager_guard": {
                "exact_a90_acm_identity": True,
                "exact_guard_properties": True,
                "identity_sha256": "4" * 64,
                "guard_spec_sha256": "5" * 64,
                "guard_topology_sha256": "6" * 64,
            },
        }

    def anchored_invoke(self, result: engine.SessionActionResult):
        def invoke(
            effects: d1.LiveSessionEffects,
            binding,
            ordinal: int,
            action,
            observer_sha256: str,
        ) -> engine.SessionActionResult:
            del binding, action, observer_sha256
            action_dir = effects.transaction_dir / f"action-{ordinal:03d}"
            action_dir.mkdir(parents=False, exist_ok=False, mode=0o700)
            return effects._finish_action(action_dir, ordinal, result)

        return invoke

    def live_effects(
        self,
        spec: d1.SessionSpec,
        transaction: Path,
        *,
        opened_at_epoch_sec: int = 2_000_000_000,
        visible_confirmed: str = "unavailable",
        clock=None,
    ) -> d1.LiveSessionEffects:
        return d1.LiveSessionEffects(
            spec,
            transaction,
            binding=d1._binding(spec, opened_at_epoch_sec),
            opening_preflight_evidence={
                "resident_health": {"cached": True},
                "source_preflight": {"cached": True},
                "rollback_sha256": spec.rollback.sha256,
                "recovery_profile": spec.recovery_profile,
            },
            visible_confirmed=visible_confirmed,
            clock=clock,
        )

    def session_open_record(self, spec: d1.SessionSpec) -> dict[str, object]:
        binding = d1._binding(spec, 2_000_000_000)
        return {
            "approval_binding_sha256": d1.json_sha256(
                d1.approval_binding(spec)
            ),
            "session_binding_sha256": d1.json_sha256(
                d1._binding_value(binding)
            ),
            "opened_at_epoch_sec": binding.not_before_epoch_sec,
            "expires_at_epoch_sec": binding.expires_at_epoch_sec,
            "approval_consumed": True,
            "payload_transfer": False,
            "partition_write": False,
            "flash": False,
        }

    def test_build_load_and_prepare_approval_bind_resident_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            private = root / "private"
            run_base = private / "runs/server-distro"
            manifest_path, journal_dir, resident_sha = self.resident_fixture(private)
            run_id = "a90-d1-attended-20260802-01"
            output = run_base / run_id / "manifest.json"
            with mock.patch.object(d1, "PRIVATE_ROOT", private.resolve()), mock.patch.object(
                d1, "PRIVATE_RUN_BASE", run_base.resolve()
            ):
                value = d1.build_manifest(
                    resident_manifest_path=manifest_path,
                    resident_manifest_sha256=resident_sha,
                    run_id=run_id,
                    session_duration_sec=3_600,
                    max_actions=4,
                )
                write_private(output, value)
                spec = d1.load_spec(output, digest(output))
                approval = d1.prepare_approval(spec)
                accepted = d1.require_approval(spec, approval["approval_token"])
                with self.assertRaisesRegex(d1.ContractError, "approval mismatch"):
                    d1.require_approval(spec, d1.APPROVAL_PREFIX + "0" * 64)
            self.assertEqual(accepted["approval_binding"]["max_actions"], 4)
            self.assertEqual(
                accepted["approval_binding"]["session_duration_sec"],
                3_600,
            )
            self.assertNotIn("not_before_epoch_sec", accepted["approval_binding"])
            self.assertNotIn("expires_at_epoch_sec", accepted["approval_binding"])
            self.assertFalse(accepted["approval_binding"]["flash"])
            self.assertEqual(value["resident"]["terminal_status"], "PASS_A90_RESIDENT_INSTALLED")

    def test_load_rejects_alternate_resident_journal_parent(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            private = root / "private"
            run_base = private / "runs/server-distro"
            manifest_path, _, resident_sha = self.resident_fixture(private)
            run_id = "a90-d1-attended-20260802-01"
            output = run_base / run_id / "manifest.json"
            alternate = private / "alternate-resident-journal"
            with mock.patch.object(d1, "PRIVATE_ROOT", private.resolve()), mock.patch.object(
                d1, "PRIVATE_RUN_BASE", run_base.resolve()
            ):
                value = d1.build_manifest(
                    resident_manifest_path=manifest_path,
                    resident_manifest_sha256=resident_sha,
                    run_id=run_id,
                    session_duration_sec=3_600,
                    max_actions=4,
                )
                for item in value["resident"]["journal"]:
                    source = Path(item["path"])
                    copied = alternate / source.name
                    write_private(copied, source.read_bytes())
                    item.update(
                        path=str(copied),
                        size=copied.stat().st_size,
                        sha256=digest(copied),
                    )
                write_private(output, value)
                with self.assertRaisesRegex(d1.ContractError, "path is not canonical"):
                    d1.load_spec(output, digest(output))

    def test_cleanup_is_fixed_path_exact_and_contains_no_flash(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            spec = self.session_spec(Path(raw))
            script = d1._cleanup_script(spec)
        self.assertIn(f"WORK={d1.WORK_PATH}", script)
        self.assertIn('[ "$WORK_MODE" = "600" ]', script)
        self.assertIn('/bin/busybox rm "$WORK"', script)
        self.assertIn("A90D1_WORK_CLEANUP exact=1 work_absent=1", script)
        self.assertNotIn("rm -rf", script)
        self.assertNotIn("rm *", script)
        source = Path(d1.__file__).read_text(encoding="utf-8")
        self.assertNotIn("native_init_flash", source)
        self.assertNotIn("flash_command(", source)

    def test_live_effect_retained_pmsg_warning_keeps_mechanical_proof(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            spec = self.session_spec(root)
            transaction = spec.transaction_dir
            transaction.mkdir()
            calls: list[str] = []

            def receipt(name: str) -> dict[str, object]:
                calls.append(name)
                return {"rc": 0, "text": "ok"}

            observation = {
                "candidate_return": self.exact_candidate_return(spec),
                "candidate_return_modemmanager_guard_release": {
                    "released": True,
                },
                "retained_pmsg_error": {
                    "type": "ContractError",
                    "message": "retained pmsg entry absent",
                },
                "display_mechanical_proof": True,
                "bounded_display_failure": False,
            }
            patches = (
                mock.patch.object(d1, "_f1_spec", return_value=d1._f1_spec(spec)),
                mock.patch.object(d1.base, "verify_candidate_health", side_effect=lambda *_a, **_k: receipt("health")),
                mock.patch.object(d1.base, "rebind_host_ncm_after_reenumeration", side_effect=lambda *_a, **_k: receipt("ncm")),
                mock.patch.object(d1.base, "require_clean_pstore_before_handoff", side_effect=lambda *_a, **_k: receipt("pstore")),
                mock.patch.object(d1.base, "remote_source_preflight", side_effect=lambda *_a, **_k: receipt("source")),
                mock.patch.object(d1.base, "settle_observation_channel", side_effect=lambda *_a, **_k: receipt("settle")),
                mock.patch.object(d1.base, "capture_bridge_serial_epoch", side_effect=lambda *_a, **_k: receipt("epoch")),
                mock.patch.object(d1.base, "arm_candidate_return_modemmanager_guard", side_effect=lambda *_a, **_k: calls.append("arm") or object()),
                mock.patch.object(d1.base, "observe_attended_after_handoff", side_effect=lambda *_a, **_k: calls.append("observe") or observation),
                mock.patch.object(d1.base, "run_f1_shell", side_effect=lambda *_a, **_k: calls.append("cleanup") or {"rc": 0, "text": "A90D1_WORK_CLEANUP exact=1 work_absent=1"}),
            )
            with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8], patches[9]:
                effects = self.live_effects(spec, transaction)
                result = effects.invoke_action(
                    effects.binding,
                    1,
                    d1.SessionAction.SWITCHROOT_EXPERIMENT,
                    spec.source_closure["observation_pipeline"].sha256,
                )
            detail = json.loads((transaction / "action-001/result.json").read_text())
        self.assertEqual(result.status, engine.SessionActionStatus.PROVED)
        self.assertEqual(detail["proof_terminal"], "PASS_SWITCHROOT_RETURN_NO_PROOF_DISPLAY_VISIBILITY")
        self.assertEqual(detail["postflight_errors"], {})
        self.assertEqual(
            detail["observation_warnings"],
            {
                "retained_pmsg": {
                    "type": "ContractError",
                    "message": "retained pmsg observer reported an error",
                }
            },
        )
        self.assertEqual(calls.count("observe"), 1)
        self.assertEqual(
            calls,
            [
                "ncm",
                "pstore",
                "settle",
                "epoch",
                "arm",
                "observe",
                "ncm",
                "cleanup",
                "health",
                "source",
            ],
        )

    def test_post_action_visibility_binds_exact_mechanical_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            spec = self.session_spec(root)
            transaction = spec.transaction_dir
            transaction.mkdir()
            action_dir = transaction / "action-001"
            action_dir.mkdir()
            safe = SessionPreflight(True, True, True, True, True)
            scripted = engine.ScriptedSessionEffects(
                (engine.SessionActionResult(engine.SessionActionStatus.PROVED, True, postflight=safe),)
            )
            scripted.mode = d1.LiveSessionEffects.mode
            session = engine.open_attended_session(
                engine.AttendedSessionContract(
                    binding=d1._binding(spec, 2_000_000_000),
                    successors=(d1.DISPLAY_SUCCESSOR,),
                ),
                scripted,
                now_epoch_sec=2_000_000_000,
                preflight=safe,
            )
            snapshot = session.run_action(
                d1.SessionAction.SWITCHROOT_EXPERIMENT,
                now_epoch_sec=2_000_000_001,
                preflight=safe,
            )
            observation = {
                "native_release_proven": True,
                "debian_pid1_proven": True,
                "dropbear_proven": True,
                "display_mechanical_proof": True,
                "ssh": {"proof": True},
            }
            intent = {
                "schema": d1.RESULT_SCHEMA,
                "ordinal": 1,
                "handoff_dispatch_count_max": 1,
            }
            detail = {
                "schema": d1.RESULT_SCHEMA,
                "ordinal": 1,
                "handoff_dispatch_count": 1,
                "resident_healthy": True,
                "observation": observation,
            }
            outcome_value = d1._action_outcome_value(
                1,
                engine.SessionActionResult(
                    engine.SessionActionStatus.PROVED,
                    True,
                    postflight=safe,
                ),
            )
            write_private(action_dir / "handoff-intent.json", intent)
            write_private(action_dir / "observation.json", observation)
            write_private(action_dir / "result.json", detail)
            write_private(action_dir / "engine-outcome.json", outcome_value)
            with mock.patch.object(d1, "PRIVATE_ROOT", root.resolve()):
                d1._append_record(
                    spec,
                    transaction,
                    "session-open",
                    self.session_open_record(spec),
                    expected_sequence=0,
                )
                d1._append_record(
                    spec,
                    transaction,
                    "action-001-intent",
                    {"ordinal": 1},
                    expected_sequence=1,
                )
                outcome_evidence = d1._bound_file(
                    action_dir / "engine-outcome.json",
                    private=True,
                )
                d1._append_record(
                    spec,
                    transaction,
                    "action-001-result",
                    {
                        "snapshot": snapshot,
                        "outcome": snapshot["action_results"][-1],
                        "outcome_evidence": d1._as_dict(outcome_evidence),
                        "now_epoch_sec": 2_000_000_001,
                    },
                    expected_sequence=2,
                )
                with self.assertRaisesRegex(d1.ContractError, "attended operator"):
                    d1.record_visible_confirmation(
                        spec,
                        transaction_dir=transaction,
                        ordinal=1,
                        visible_confirmed="yes",
                        operator_attended=False,
                    )
                receipt = d1.record_visible_confirmation(
                    spec,
                    transaction_dir=transaction,
                    ordinal=1,
                    visible_confirmed="yes",
                    operator_attended=True,
                )
                with self.assertRaisesRegex(d1.ContractError, "already exists"):
                    d1.record_visible_confirmation(
                        spec,
                        transaction_dir=transaction,
                        ordinal=1,
                        visible_confirmed="no",
                        operator_attended=True,
                    )
            receipt_path = action_dir / "display-visible-confirmation.json"
            self.assertTrue(receipt["display_visibility_proved"])
            self.assertFalse(receipt["display_visibility_refuted"])
            self.assertFalse(receipt["device_contact"])
            self.assertFalse(receipt["device_effect"])
            self.assertEqual(receipt_path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(receipt["evidence"]["observation"]["sha256"], digest(action_dir / "observation.json"))

    def test_session_consumes_approval_once_and_resumes_without_replay(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            spec = self.session_spec(root)
            transaction = spec.transaction_dir
            write_private(
                d1.approval_path(spec),
                {
                    "schema": d1.APPROVAL_SCHEMA,
                    "created_utc": d1.utc_now(),
                    "run_id": spec.run_id,
                    "approval_binding": d1.approval_binding(spec),
                    "approval_binding_sha256": d1.json_sha256(d1.approval_binding(spec)),
                    "approval_token": d1.APPROVAL_PREFIX + d1.json_sha256(d1.approval_binding(spec)),
                    "device_contact": False,
                    "device_write": False,
                    "live_authority": False,
                },
            )
            safe = SessionPreflight(True, True, True, True, True)
            proved = engine.SessionActionResult(engine.SessionActionStatus.PROVED, True, postflight=safe)
            with mock.patch.object(d1, "PRIVATE_ROOT", root.resolve()), mock.patch.object(
                d1,
                "_preflight",
                return_value=(safe, {"ok": True}),
            ), mock.patch.object(
                d1.LiveSessionEffects,
                "invoke_action",
                autospec=True,
                side_effect=self.anchored_invoke(proved),
            ):
                first = d1.execute_switchroot(
                    spec,
                    transaction_dir=transaction,
                    approval=d1.APPROVAL_PREFIX + d1.json_sha256(d1.approval_binding(spec)),
                    resume=False,
                    operator_attended=True,
                    visible_confirmed="unavailable",
                    now_epoch_sec=2_000_000_001,
                )
                second = d1.execute_switchroot(
                    spec,
                    transaction_dir=transaction,
                    approval=None,
                    resume=True,
                    operator_attended=True,
                    visible_confirmed="unavailable",
                    now_epoch_sec=2_000_000_002,
                )
                actions = [
                    item["action"]
                    for item in d1._session_records(spec, transaction)
                ]
            with mock.patch.object(d1, "PRIVATE_ROOT", root.resolve()), mock.patch.object(
                d1, "_preflight"
            ) as preflight, self.assertRaisesRegex(
                d1.ContractError,
                "session time is not monotonic",
            ):
                d1.execute_switchroot(
                    spec,
                    transaction_dir=transaction,
                    approval=None,
                    resume=True,
                    operator_attended=True,
                    visible_confirmed="unavailable",
                    now_epoch_sec=2_000_000_001,
                )
            preflight.assert_not_called()
        self.assertEqual(first["actions_used"], 1)
        self.assertEqual(second["actions_used"], 2)
        self.assertEqual(first["opened_at_epoch_sec"], 2_000_000_001)
        self.assertEqual(
            first["expires_at_epoch_sec"] - first["opened_at_epoch_sec"],
            spec.session_duration_sec,
        )
        self.assertEqual(
            actions,
            [
                "session-open",
                "action-001-intent",
                "action-001-result",
                "action-002-intent",
                "action-002-result",
            ],
        )

    def test_fresh_window_opens_after_preflight_and_rechecks_before_effect(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            spec = replace(self.session_spec(root), session_duration_sec=1)
            transaction = spec.transaction_dir
            approval_sha = d1.json_sha256(d1.approval_binding(spec))
            write_private(
                d1.approval_path(spec),
                {
                    "schema": d1.APPROVAL_SCHEMA,
                    "created_utc": d1.utc_now(),
                    "run_id": spec.run_id,
                    "approval_binding": d1.approval_binding(spec),
                    "approval_binding_sha256": approval_sha,
                    "approval_token": d1.APPROVAL_PREFIX + approval_sha,
                    "device_contact": False,
                    "device_write": False,
                    "live_authority": False,
                },
            )
            safe = SessionPreflight(True, True, True, True, True)
            clock_values = iter((2_000_000_010, 2_000_000_011))
            with mock.patch.object(d1, "PRIVATE_ROOT", root.resolve()), mock.patch.object(
                d1, "_preflight", return_value=(safe, {"ok": True})
            ), mock.patch.object(d1, "_f1_spec") as device_effect:
                snapshot = d1.execute_switchroot(
                    spec,
                    transaction_dir=transaction,
                    approval=d1.APPROVAL_PREFIX + approval_sha,
                    resume=False,
                    operator_attended=True,
                    visible_confirmed="unavailable",
                    now_epoch_sec=2_000_000_000,
                    clock=lambda: next(clock_values),
                )
            with mock.patch.object(d1, "PRIVATE_ROOT", root.resolve()):
                binding = d1._binding_from_session_open(
                    spec,
                    d1._session_records(spec, transaction),
                )
                restored = d1._restore_session(
                    spec,
                    binding,
                    d1._session_records(spec, transaction),
                )
            device_effect.assert_not_called()
            self.assertEqual(snapshot["opened_at_epoch_sec"], 2_000_000_010)
            self.assertEqual(snapshot["expires_at_epoch_sec"], 2_000_000_011)
            self.assertEqual(
                snapshot["terminal"],
                "SESSION_CLOSED_EXPIRED_BEFORE_DISPATCH",
            )
            self.assertEqual(
                snapshot["action_results"][-1]["status"],
                "WINDOW_EXPIRED_NO_EFFECT",
            )
            self.assertEqual(
                restored.closed_terminal,
                "SESSION_CLOSED_EXPIRED_BEFORE_DISPATCH",
            )
            self.assertFalse(
                json.loads(
                    (transaction / "action-001/engine-outcome.json").read_text(
                        encoding="utf-8"
                    )
                )["action_started"]
            )
            self.assertFalse((transaction / "action-001/handoff-intent.json").exists())

    def test_dangling_action_intent_refuses_resume(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            spec = self.session_spec(root)
            transaction = spec.transaction_dir
            transaction.mkdir()
            with mock.patch.object(d1, "PRIVATE_ROOT", root.resolve()):
                d1._append_record(
                    spec,
                    transaction,
                    "session-open",
                    self.session_open_record(spec),
                    expected_sequence=0,
                )
                d1._append_record(
                    spec,
                    transaction,
                    "action-001-intent",
                    {},
                    expected_sequence=1,
                )
                with mock.patch.object(d1, "_preflight") as preflight, self.assertRaisesRegex(
                    d1.ContractError,
                    "no durable result",
                ):
                    d1.execute_switchroot(
                        spec,
                        transaction_dir=transaction,
                        approval=None,
                        resume=True,
                        operator_attended=True,
                        visible_confirmed="unavailable",
                        now_epoch_sec=2_000_000_001,
                    )
                preflight.assert_not_called()

    def test_session_journal_rejects_cross_manifest_record(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            spec = self.session_spec(root)
            transaction = spec.transaction_dir
            transaction.mkdir()
            with mock.patch.object(d1, "PRIVATE_ROOT", root.resolve()):
                d1._append_record(
                    spec,
                    transaction,
                    "session-open",
                    self.session_open_record(spec),
                    expected_sequence=0,
                )
                path = transaction / "journal/0000-session-open.json"
                record = json.loads(path.read_text(encoding="utf-8"))
                record["manifest_sha256"] = "f" * 64
                write_private(path, record)
                with self.assertRaisesRegex(d1.ContractError, "journal sequence"):
                    d1._session_records(spec, transaction)

    def test_closed_and_tampered_session_refuse_before_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            spec = self.session_spec(root)
            transaction = spec.transaction_dir
            binding_sha = d1.json_sha256(d1.approval_binding(spec))
            write_private(
                d1.approval_path(spec),
                {
                    "schema": d1.APPROVAL_SCHEMA,
                    "created_utc": d1.utc_now(),
                    "run_id": spec.run_id,
                    "approval_binding": d1.approval_binding(spec),
                    "approval_binding_sha256": binding_sha,
                    "approval_token": d1.APPROVAL_PREFIX + binding_sha,
                    "device_contact": False,
                    "device_write": False,
                    "live_authority": False,
                },
            )
            safe = SessionPreflight(True, True, True, True, True)
            blocked = engine.SessionActionResult(
                engine.SessionActionStatus.EXPERIMENT_BLOCKED,
                True,
                failure_class="WORK_CLEANUP_BLOCKED",
                postflight=safe,
            )
            with mock.patch.object(d1, "PRIVATE_ROOT", root.resolve()), mock.patch.object(
                d1, "_preflight", return_value=(safe, {"ok": True})
            ) as preflight, mock.patch.object(
                d1.LiveSessionEffects,
                "invoke_action",
                autospec=True,
                side_effect=self.anchored_invoke(blocked),
            ), mock.patch.object(
                d1, "utc_now", return_value="2026-08-02T00:00:00Z"
            ):
                d1.execute_switchroot(
                    spec,
                    transaction_dir=transaction,
                    approval=d1.APPROVAL_PREFIX + binding_sha,
                    resume=False,
                    operator_attended=True,
                    visible_confirmed="unavailable",
                    now_epoch_sec=2_000_000_001,
                )
                preflight.reset_mock()
                with self.assertRaisesRegex(d1.ContractError, "already closed"):
                    d1.execute_switchroot(
                        spec,
                        transaction_dir=transaction,
                        approval=None,
                        resume=True,
                        operator_attended=True,
                        visible_confirmed="unavailable",
                        now_epoch_sec=2_000_000_002,
                    )
                preflight.assert_not_called()
                path = transaction / "journal/0002-action-001-result.json"
                record = json.loads(path.read_text(encoding="utf-8"))
                original = json.loads(json.dumps(record))
                snapshot = record["snapshot"]
                snapshot["actions_remaining"] = 99
                write_private(path, record)
                preflight.reset_mock()
                with self.assertRaisesRegex(d1.ContractError, "snapshot is not exact"):
                    d1.execute_switchroot(
                        spec,
                        transaction_dir=transaction,
                        approval=None,
                        resume=True,
                        operator_attended=True,
                        visible_confirmed="unavailable",
                        now_epoch_sec=2_000_000_002,
                    )
                preflight.assert_not_called()

                record = original
                snapshot = record["snapshot"]
                snapshot["terminal"] = "SESSION_ACTIVE"
                snapshot["session_open"] = True
                snapshot["session_active"] = True
                snapshot["observer_repair_required"] = False
                snapshot["history"][-2:] = [
                    "ACTION_1_PROVED",
                    "SESSION_ACTIVE",
                ]
                snapshot["action_results"][-1]["status"] = "PROVED"
                snapshot["action_results"][-1]["failure_class"] = None
                record["outcome"] = dict(snapshot["action_results"][-1])
                write_private(path, record)
                preflight.reset_mock()
                with self.assertRaisesRegex(d1.ContractError, "outcome evidence"):
                    d1.execute_switchroot(
                        spec,
                        transaction_dir=transaction,
                        approval=None,
                        resume=True,
                        operator_attended=True,
                        visible_confirmed="unavailable",
                        now_epoch_sec=2_000_000_002,
                    )
                preflight.assert_not_called()

    def test_paused_observer_session_requires_ack_then_runs_new_ordinal(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            spec = self.session_spec(root)
            transaction = spec.transaction_dir
            binding_sha = d1.json_sha256(d1.approval_binding(spec))
            write_private(
                d1.approval_path(spec),
                {
                    "schema": d1.APPROVAL_SCHEMA,
                    "created_utc": d1.utc_now(),
                    "run_id": spec.run_id,
                    "approval_binding": d1.approval_binding(spec),
                    "approval_binding_sha256": binding_sha,
                    "approval_token": d1.APPROVAL_PREFIX + binding_sha,
                    "device_contact": False,
                    "device_write": False,
                    "live_authority": False,
                },
            )
            safe = SessionPreflight(True, True, True, True, True)
            no_proof = engine.SessionActionResult(
                engine.SessionActionStatus.NO_PROOF_OBSERVER,
                True,
                failure_class="DISPLAY_EVIDENCE_OBSERVER",
                postflight=safe,
                independent_safety_check=True,
            )
            with mock.patch.object(d1, "PRIVATE_ROOT", root.resolve()), mock.patch.object(
                d1, "_preflight", return_value=(safe, {"ok": True})
            ), mock.patch.object(
                d1.LiveSessionEffects,
                "invoke_action",
                autospec=True,
                side_effect=self.anchored_invoke(no_proof),
            ):
                first = d1.execute_switchroot(
                    spec,
                    transaction_dir=transaction,
                    approval=d1.APPROVAL_PREFIX + binding_sha,
                    resume=False,
                    operator_attended=True,
                    visible_confirmed="unavailable",
                    now_epoch_sec=2_000_000_001,
                )
            self.assertEqual(
                first["terminal"],
                "SESSION_PAUSED_OBSERVER_REPAIR_REQUIRED",
            )
            with mock.patch.object(d1, "PRIVATE_ROOT", root.resolve()), mock.patch.object(
                d1, "_preflight"
            ) as preflight, self.assertRaisesRegex(
                d1.ContractError,
                "explicit observer no-proof acknowledgement",
            ):
                d1.execute_switchroot(
                    spec,
                    transaction_dir=transaction,
                    approval=None,
                    resume=True,
                    operator_attended=True,
                    visible_confirmed="unavailable",
                    now_epoch_sec=2_000_000_002,
                )
            preflight.assert_not_called()
            proved = engine.SessionActionResult(
                engine.SessionActionStatus.PROVED,
                True,
                postflight=safe,
            )
            with mock.patch.object(d1, "PRIVATE_ROOT", root.resolve()), mock.patch.object(
                d1, "_preflight", return_value=(safe, {"ok": True})
            ), mock.patch.object(
                d1.LiveSessionEffects,
                "invoke_action",
                autospec=True,
                side_effect=self.anchored_invoke(proved),
            ):
                resumed = d1.execute_switchroot(
                    spec,
                    transaction_dir=transaction,
                    approval=None,
                    resume=True,
                    operator_attended=True,
                    acknowledge_observer_no_proof=True,
                    visible_confirmed="unavailable",
                    now_epoch_sec=2_000_000_002,
                )
            self.assertEqual(resumed["terminal"], "SESSION_ACTIVE")
            self.assertEqual(resumed["actions_used"], 2)
            self.assertEqual(resumed["observer_no_proof_acknowledgements"], 1)

    def test_transaction_path_and_session_lock_stop_before_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            spec = self.session_spec(root)
            with mock.patch.object(d1, "_preflight") as preflight, self.assertRaisesRegex(
                d1.ContractError,
                "path is not manifest-bound",
            ):
                d1.execute_switchroot(
                    spec,
                    transaction_dir=root / "second-fresh-session",
                    approval="unused",
                    resume=False,
                    operator_attended=True,
                    visible_confirmed="unavailable",
                    now_epoch_sec=2_000_000_001,
                )
            preflight.assert_not_called()
            descriptor = os.open(
                spec.session_lock_path,
                os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW,
                0o600,
            )
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with mock.patch.object(d1, "_preflight") as preflight, self.assertRaisesRegex(
                    d1.ContractError,
                    "already owned",
                ):
                    d1.execute_switchroot(
                        spec,
                        transaction_dir=spec.transaction_dir,
                        approval="unused",
                        resume=False,
                        operator_attended=True,
                        visible_confirmed="unavailable",
                        now_epoch_sec=2_000_000_001,
                    )
                preflight.assert_not_called()
            finally:
                os.close(descriptor)

    def test_expected_sequence_rejects_stale_second_intent(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            spec = self.session_spec(root)
            transaction = spec.transaction_dir
            transaction.mkdir()
            with mock.patch.object(d1, "PRIVATE_ROOT", root.resolve()):
                d1._append_record(
                    spec,
                    transaction,
                    "session-open",
                    self.session_open_record(spec),
                    expected_sequence=0,
                )
                d1._append_record(
                    spec,
                    transaction,
                    "action-001-intent",
                    {},
                    expected_sequence=1,
                )
                with self.assertRaisesRegex(d1.ContractError, "expected sequence"):
                    d1._append_record(
                        spec,
                        transaction,
                        "action-001-intent",
                        {},
                        expected_sequence=1,
                    )

    def test_candidate_return_error_never_proves(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            spec = self.session_spec(Path(raw))
            returned, errors = d1._classify_return_observation(
                d1._f1_spec(spec),
                {
                    "candidate_return_error": {
                        "type": "ContractError",
                        "message": "candidate return identity failed",
                    },
                    "candidate_return_modemmanager_guard_release": {
                        "released": True,
                    },
                    "display_mechanical_proof": True,
                },
            )
        self.assertFalse(returned)
        self.assertIn("return_observation", errors)

    def test_legacy_retained_pmsg_error_preserves_exact_return(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            spec = self.session_spec(Path(raw))
            returned, errors = d1._classify_return_observation(
                d1._f1_spec(spec),
                {
                    "candidate_return": self.exact_candidate_return(spec),
                    "candidate_return_error": {
                        "type": "ContractError",
                        "message": "candidate return lacks one exact retained pmsg entry",
                    },
                    "candidate_return_modemmanager_guard_release": {
                        "released": True,
                    },
                    "display_mechanical_proof": True,
                },
            )
        self.assertTrue(returned)
        self.assertEqual(
            errors,
            {"retained_pmsg": "retained pmsg observer reported an error"},
        )

    def test_retained_pmsg_error_preserves_exact_return_as_warning(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            spec = self.session_spec(Path(raw))
            returned, errors = d1._classify_return_observation(
                d1._f1_spec(spec),
                {
                    "candidate_return": self.exact_candidate_return(spec),
                    "retained_pmsg_error": {
                        "type": "ContractError",
                        "message": "retained pmsg entry absent",
                    },
                    "candidate_return_modemmanager_guard_release": {
                        "released": True,
                    },
                    "display_mechanical_proof": True,
                },
            )
        self.assertTrue(returned)
        self.assertEqual(
            errors,
            {"retained_pmsg": "retained pmsg observer reported an error"},
        )

    def test_empty_candidate_return_never_proves(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            spec = self.session_spec(Path(raw))
            returned, errors = d1._classify_return_observation(
                d1._f1_spec(spec),
                {
                    "candidate_return": {},
                    "candidate_return_modemmanager_guard_release": {
                        "released": True,
                    },
                    "retained_pmsg": {
                        "proof": True,
                        "armed_positive_control": True,
                        "capture_fsynced_before_cleanup": True,
                        "exact_cleanup": True,
                        "pstore_empty_after": True,
                    },
                },
            )
        self.assertFalse(returned)
        self.assertIn("return_observation", errors)

    def test_boolean_device_command_count_never_proves_return(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            spec = self.session_spec(Path(raw))
            candidate_return = self.exact_candidate_return(spec)
            candidate_return["device_command_sequences"] = True
            returned, errors = d1._classify_return_observation(
                d1._f1_spec(spec),
                {
                    "candidate_return": candidate_return,
                    "candidate_return_modemmanager_guard_release": {
                        "released": True,
                    },
                    "retained_pmsg": {
                        "proof": True,
                        "armed_positive_control": True,
                        "capture_fsynced_before_cleanup": True,
                        "exact_cleanup": True,
                        "pstore_empty_after": True,
                    },
                },
            )
        self.assertFalse(returned)
        self.assertIn("return_observation", errors)

    def test_malformed_observer_still_runs_cleanup_and_final_health(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            spec = self.session_spec(root)
            transaction = spec.transaction_dir
            transaction.mkdir()
            calls: list[str] = []

            def health(*_args, **_kwargs):
                calls.append("health")
                return {"exact": True}

            with mock.patch.object(
                d1, "_f1_spec", return_value=d1._f1_spec(spec)
            ), mock.patch.object(
                d1.base, "verify_candidate_health", side_effect=health
            ), mock.patch.object(
                d1.base,
                "rebind_host_ncm_after_reenumeration",
                side_effect=lambda *_a, **_k: calls.append("ncm") or {"exact": True},
            ), mock.patch.object(
                d1.base, "require_clean_pstore_before_handoff", return_value={"exact": True}
            ), mock.patch.object(
                d1.base, "remote_source_preflight", return_value={"exact": True}
            ), mock.patch.object(
                d1.base, "settle_observation_channel", return_value={"exact": True}
            ), mock.patch.object(
                d1.base, "capture_bridge_serial_epoch", return_value={"exact": True}
            ), mock.patch.object(
                d1.base, "arm_candidate_return_modemmanager_guard", return_value=object()
            ), mock.patch.object(
                d1.base, "observe_attended_after_handoff", return_value=None
            ), mock.patch.object(
                d1.base,
                "run_f1_shell",
                side_effect=lambda *_a, **_k: calls.append("cleanup")
                or {
                    "rc": 0,
                    "text": "A90D1_WORK_CLEANUP exact=1 work_absent=1",
                },
            ), mock.patch.object(
                d1.base,
                "release_candidate_return_modemmanager_guard",
                return_value={"released": True},
            ):
                effects = self.live_effects(
                    spec,
                    transaction,
                    visible_confirmed="yes",
                )
                result = effects.invoke_action(
                    effects.binding,
                    1,
                    d1.SessionAction.SWITCHROOT_EXPERIMENT,
                    spec.source_closure["observation_pipeline"].sha256,
                )
        self.assertEqual(result.status, engine.SessionActionStatus.EXPERIMENT_BLOCKED)
        self.assertEqual(calls.count("health"), 1)
        self.assertIn("cleanup", calls)

    def test_live_transitive_source_closure_is_bound(self) -> None:
        self.assertTrue(
            {
                "workspace_bootstrap",
                "bridge_selector",
                "serial_lock",
                "serial_tcp_bridge",
            }.issubset(d1.SOURCE_PATHS)
        )

    def test_blocked_experiment_closes_session_but_keeps_resident_healthy(self) -> None:
        safe = SessionPreflight(True, True, True, True, True)
        result = engine.SessionActionResult(
            engine.SessionActionStatus.EXPERIMENT_BLOCKED,
            action_started=True,
            failure_class="WORK_CLEANUP_BLOCKED",
            postflight=safe,
        )
        binding = d1.AttendedSessionBinding(
            approval_id="test-session",
            workflow=d1.Workflow.ATTENDED_SESSION_D1,
            risk_tier=d1.RiskTier.TIER_D1_TRANSIENT_NO_PAYLOAD_CONTROL,
            target_profile=staging.TARGET_PROFILE,
            manifest_sha256="1" * 64,
            resident_boot_sha256="2" * 64,
            rollback_boot_sha256="3" * 64,
            recovery_profile="test-recovery",
            device_effect_runner_sha256="4" * 64,
            observer_sha256="5" * 64,
            return_health_profile="test-health",
            action_allowlist=(d1.SessionAction.SWITCHROOT_EXPERIMENT,),
            not_before_epoch_sec=100,
            expires_at_epoch_sec=200,
            max_actions=2,
        )
        effects = engine.ScriptedSessionEffects((result,))
        session = engine.open_attended_session(
            engine.AttendedSessionContract(binding, (d1.DISPLAY_SUCCESSOR,)),
            effects,
            now_epoch_sec=101,
            preflight=safe,
        )
        snapshot = session.run_action(
            d1.SessionAction.SWITCHROOT_EXPERIMENT,
            now_epoch_sec=102,
            preflight=safe,
        )
        self.assertEqual(snapshot["terminal"], "SESSION_CLOSED_EXPERIMENT_BLOCKED")
        self.assertEqual(snapshot["device_safety_state"], "RESIDENT_HEALTHY")
        with self.assertRaisesRegex(engine.ContractError, "exact healthy stop"):
            engine.SessionActionResult(
                engine.SessionActionStatus.EXPERIMENT_BLOCKED,
                action_started=True,
                failure_class="WRONG_SUFFIX",
                postflight=safe,
            ).validate()

    def test_pre_handoff_host_failure_stops_safe_without_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            spec = self.session_spec(root)
            transaction = spec.transaction_dir
            transaction.mkdir()
            calls: list[str] = []
            with mock.patch.object(d1, "_f1_spec", return_value=object()), mock.patch.object(
                d1.base,
                "verify_candidate_health",
                side_effect=lambda *_a, **_k: calls.append("health") or {"ok": True},
            ), mock.patch.object(
                d1.base,
                "rebind_host_ncm_after_reenumeration",
                side_effect=RuntimeError("host NCM unavailable"),
            ), mock.patch.object(
                d1.base,
                "observe_attended_after_handoff",
            ) as observe:
                effects = self.live_effects(spec, transaction)
                result = effects.invoke_action(
                    effects.binding,
                    1,
                    d1.SessionAction.SWITCHROOT_EXPERIMENT,
                    spec.source_closure["observation_pipeline"].sha256,
                )
        self.assertEqual(result.status, engine.SessionActionStatus.EXPERIMENT_BLOCKED)
        self.assertEqual(calls, [])
        observe.assert_not_called()

    def test_cleanup_failure_is_safe_block_after_final_native_health(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            spec = self.session_spec(root)
            transaction = spec.transaction_dir
            transaction.mkdir()
            observation = {
                "candidate_return": self.exact_candidate_return(spec),
                "candidate_return_modemmanager_guard_release": {
                    "released": True,
                },
                "retained_pmsg": {
                    "proof": True,
                    "armed_positive_control": True,
                    "capture_fsynced_before_cleanup": True,
                    "exact_cleanup": True,
                    "pstore_empty_after": True,
                },
                "display_mechanical_proof": True,
                "bounded_display_failure": False,
            }
            ok = {"rc": 0, "text": "ok"}
            with mock.patch.object(d1, "_f1_spec", return_value=d1._f1_spec(spec)), mock.patch.object(
                d1.base, "verify_candidate_health", return_value=ok
            ) as health, mock.patch.object(
                d1.base, "rebind_host_ncm_after_reenumeration", return_value=ok
            ), mock.patch.object(
                d1.base, "require_clean_pstore_before_handoff", return_value=ok
            ), mock.patch.object(
                d1.base, "remote_source_preflight", return_value=ok
            ), mock.patch.object(
                d1.base, "settle_observation_channel", return_value=ok
            ), mock.patch.object(
                d1.base, "capture_bridge_serial_epoch", return_value=ok
            ), mock.patch.object(
                d1.base, "arm_candidate_return_modemmanager_guard", return_value=object()
            ), mock.patch.object(
                d1.base, "observe_attended_after_handoff", return_value=observation
            ), mock.patch.object(
                d1.base, "run_f1_shell", side_effect=RuntimeError("cleanup failed")
            ):
                effects = self.live_effects(spec, transaction)
                result = effects.invoke_action(
                    effects.binding,
                    1,
                    d1.SessionAction.SWITCHROOT_EXPERIMENT,
                    spec.source_closure["observation_pipeline"].sha256,
                )
            detail = json.loads((transaction / "action-001/result.json").read_text())
        self.assertEqual(result.status, engine.SessionActionStatus.EXPERIMENT_BLOCKED)
        self.assertEqual(detail["proof_terminal"], "SESSION_BLOCKED_RESIDENT_HEALTHY")
        self.assertIn("cleanup", detail["postflight_errors"])
        self.assertEqual(health.call_count, 1)

    def test_handoff_dispatch_boundary_rechecks_expiry_after_durable_intent(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            spec = self.session_spec(root)
            transaction = spec.transaction_dir
            transaction.mkdir()
            binding = d1._binding(spec, 2_000_000_000)
            clock_values = iter(
                (
                    2_000_000_001,
                    binding.expires_at_epoch_sec,
                )
            )
            effects = self.live_effects(
                spec,
                transaction,
                clock=lambda: next(clock_values),
            )
            ok = {"exact": True}
            guard = object()
            with mock.patch.object(
                d1.base, "rebind_host_ncm_after_reenumeration", return_value=ok
            ), mock.patch.object(
                d1.base, "require_clean_pstore_before_handoff", return_value=ok
            ), mock.patch.object(
                d1.base, "settle_observation_channel", return_value=ok
            ), mock.patch.object(
                d1.base, "capture_bridge_serial_epoch", return_value=ok
            ), mock.patch.object(
                d1.base, "arm_candidate_return_modemmanager_guard", return_value=guard
            ), mock.patch.object(
                d1.base, "observe_attended_after_handoff"
            ) as handoff, mock.patch.object(
                d1.base, "release_candidate_return_modemmanager_guard"
            ) as release:
                result = effects.invoke_action(
                    binding,
                    1,
                    d1.SessionAction.SWITCHROOT_EXPERIMENT,
                    spec.source_closure["observation_pipeline"].sha256,
                )
            self.assertEqual(
                result.status,
                engine.SessionActionStatus.WINDOW_EXPIRED_NO_EFFECT,
            )
            self.assertFalse(result.action_started)
            handoff.assert_not_called()
            release.assert_called_once_with(guard, transaction / "action-001")
            self.assertTrue((transaction / "action-001/handoff-intent.json").is_file())
            self.assertTrue(
                (transaction / "action-001/expiry-before-dispatch.json").is_file()
            )

    def test_pre_dispatch_revalidation_failure_sends_no_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            spec = self.session_spec(root)
            transaction = spec.transaction_dir
            transaction.mkdir()
            binding = d1._binding(spec, 2_000_000_000)
            revalidate = mock.Mock(side_effect=d1.ContractError("source changed"))
            effects = d1.LiveSessionEffects(
                spec,
                transaction,
                binding=binding,
                opening_preflight_evidence={
                    "resident_health": {"exact": True},
                    "source_preflight": {"exact": True},
                    "rollback_sha256": spec.rollback.sha256,
                    "recovery_profile": spec.recovery_profile,
                },
                visible_confirmed="unavailable",
                clock=lambda: 2_000_000_001,
                pre_dispatch_revalidate=revalidate,
            )
            ok = {"exact": True}
            guard = object()
            with mock.patch.object(
                d1.base, "rebind_host_ncm_after_reenumeration", return_value=ok
            ), mock.patch.object(
                d1.base, "require_clean_pstore_before_handoff", return_value=ok
            ), mock.patch.object(
                d1.base, "settle_observation_channel", return_value=ok
            ), mock.patch.object(
                d1.base, "capture_bridge_serial_epoch", return_value=ok
            ), mock.patch.object(
                d1.base, "arm_candidate_return_modemmanager_guard", return_value=guard
            ), mock.patch.object(
                d1.base, "observe_attended_after_handoff"
            ) as handoff, mock.patch.object(
                d1.base, "release_candidate_return_modemmanager_guard"
            ) as release:
                result = effects.invoke_action(
                    binding,
                    1,
                    d1.SessionAction.SWITCHROOT_EXPERIMENT,
                    spec.source_closure["observation_pipeline"].sha256,
                )
            self.assertEqual(
                result.status,
                engine.SessionActionStatus.EXPERIMENT_BLOCKED,
            )
            self.assertEqual(
                result.failure_class,
                "PRE_DISPATCH_INTEGRITY_BLOCKED",
            )
            self.assertTrue(result.postflight.operator_attended)
            revalidate.assert_called_once_with()
            handoff.assert_not_called()
            release.assert_called_once_with(guard, transaction / "action-001")
            self.assertTrue((transaction / "action-001/handoff-intent.json").is_file())
            self.assertTrue(
                (
                    transaction
                    / "action-001/pre-dispatch-revalidation-error.json"
                ).is_file()
            )

    def test_expired_session_refuses_before_connected_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            spec = self.session_spec(root)
            binding_sha = d1.json_sha256(d1.approval_binding(spec))
            token = d1.APPROVAL_PREFIX + binding_sha
            write_private(
                d1.approval_path(spec),
                {
                    "schema": d1.APPROVAL_SCHEMA,
                    "created_utc": d1.utc_now(),
                    "run_id": spec.run_id,
                    "approval_binding": d1.approval_binding(spec),
                    "approval_binding_sha256": binding_sha,
                    "approval_token": token,
                    "device_contact": False,
                    "device_write": False,
                    "live_authority": False,
                },
            )
            safe = SessionPreflight(True, True, True, True, True)
            proved = engine.SessionActionResult(
                engine.SessionActionStatus.PROVED,
                True,
                postflight=safe,
            )
            with mock.patch.object(d1, "PRIVATE_ROOT", root.resolve()), mock.patch.object(
                d1, "_preflight", return_value=(safe, {"ok": True})
            ), mock.patch.object(
                d1.LiveSessionEffects,
                "invoke_action",
                autospec=True,
                side_effect=self.anchored_invoke(proved),
            ):
                d1.execute_switchroot(
                    spec,
                    transaction_dir=spec.transaction_dir,
                    approval=token,
                    resume=False,
                    operator_attended=True,
                    visible_confirmed="unavailable",
                    now_epoch_sec=2_000_000_000,
                )
            with mock.patch.object(d1, "PRIVATE_ROOT", root.resolve()):
                records_before = tuple(
                    item["action"]
                    for item in d1._session_records(spec, spec.transaction_dir)
                )
            with mock.patch.object(d1, "PRIVATE_ROOT", root.resolve()), mock.patch.object(
                d1, "_preflight", return_value=(safe, {"ok": True})
            ) as preflight, mock.patch.object(
                d1.LiveSessionEffects, "invoke_action"
            ) as device_effect, self.assertRaisesRegex(
                d1.ContractError,
                "window is not active",
            ):
                d1.execute_switchroot(
                    spec,
                    transaction_dir=spec.transaction_dir,
                    approval=None,
                    resume=True,
                    operator_attended=True,
                    visible_confirmed="unavailable",
                    now_epoch_sec=(
                        2_000_000_000 + spec.session_duration_sec - 1
                    ),
                    clock=lambda: 2_000_000_000 + spec.session_duration_sec,
                )
            preflight.assert_called_once()
            device_effect.assert_not_called()
            with mock.patch.object(d1, "PRIVATE_ROOT", root.resolve()):
                self.assertEqual(
                    tuple(
                        item["action"]
                        for item in d1._session_records(spec, spec.transaction_dir)
                    ),
                    records_before,
                )
            with mock.patch.object(d1, "PRIVATE_ROOT", root.resolve()), mock.patch.object(
                d1, "_preflight"
            ) as preflight, self.assertRaisesRegex(
                d1.ContractError,
                "window is not active",
            ):
                d1.execute_switchroot(
                    spec,
                    transaction_dir=spec.transaction_dir,
                    approval=None,
                    resume=True,
                    operator_attended=True,
                    visible_confirmed="unavailable",
                    now_epoch_sec=2_000_000_000 + spec.session_duration_sec,
                )
            preflight.assert_not_called()

    def test_manifest_rejects_unknown_top_level_key(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            private = root / "private"
            run_base = private / "runs/server-distro"
            resident_manifest, journal_dir, resident_sha = self.resident_fixture(private)
            run_id = "a90-d1-attended-20260802-01"
            output = run_base / run_id / "manifest.json"
            with mock.patch.object(d1, "PRIVATE_ROOT", private.resolve()), mock.patch.object(
                d1, "PRIVATE_RUN_BASE", run_base.resolve()
            ):
                value = d1.build_manifest(
                    resident_manifest_path=resident_manifest,
                    resident_manifest_sha256=resident_sha,
                    run_id=run_id,
                    session_duration_sec=3_600,
                    max_actions=2,
                )
                value["unexpected"] = True
                write_private(output, value)
                with self.assertRaisesRegex(d1.ContractError, "schema or status"):
                    d1.load_spec(output, digest(output))

    def test_import_and_default_cli_are_host_only(self) -> None:
        script = Path(d1.__file__)
        completed = subprocess.run(
            [sys.executable, "-I", "-c", f"import runpy; runpy.run_path({str(script)!r}, run_name='not_main')"],
            check=False,
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        help_result = subprocess.run(
            [sys.executable, str(script), "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("--session-duration-sec", help_result.stdout)
        self.assertIn("--acknowledge-observer-no-proof", help_result.stdout)
        self.assertNotIn("--resident-journal-dir", help_result.stdout)
        self.assertIn("--execute-switchroot", help_result.stdout)
        self.assertNotIn("--flash", help_result.stdout)


if __name__ == "__main__":
    unittest.main()
