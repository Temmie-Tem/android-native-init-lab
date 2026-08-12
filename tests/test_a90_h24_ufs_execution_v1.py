from __future__ import annotations

import argparse
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _loader import load_script


def passing_h24_transcript(observer: object, **changes: str) -> str:
    facts = {
        "pid1_comm": "init",
        "pid1_exe": "/usr/sbin/init",
        "root_mount": "/dev/block/a90-userdata|ext4|ro,nosuid,nodev,norecovery",
        "debian_dev_entries_before": "console,null,ptmx,pts,random,tty,ttyGS0,urandom,zero",
        "debian_dev_entries_after": "console,null,ptmx,pts,random,tty,ttyGS0,urandom,zero",
        "debian_dev_core_meta": (
            "console=character special file|5:1|600;"
            "tty=character special file|5:0|666;"
            "ptmx=character special file|5:2|666;"
            "null=character special file|1:3|666;"
            "zero=character special file|1:5|666;"
            "random=character special file|1:8|666;"
            "urandom=character special file|1:9|666"
        ),
        "debian_dev_pts_meta": "directory|755",
        "debian_dev_ttygs0_meta": "character special file|ef:0|600",
        "debian_dev_block_count": "0",
        "debian_dev_mount": "tmpfs|tmpfs|rw,nosuid,noexec,relatime,mode=755",
        "debian_dev_pts_mount": "devpts|devpts|rw,relatime,mode=620,ptmxmode=666",
        "auth_mount": "a90-h17-observer-auth|tmpfs|rw,nosuid,nodev,noexec",
        "auth_key_meta": "regular file|600|0|0|1|81",
        "firstboot_mount_count": "0",
        "hud_run_mount": "a90-dpublic-hud|tmpfs|rw,nosuid,nodev",
        "dropbear_pid": "201",
        "dropbear_exe": "/usr/sbin/dropbear",
        "listener_count": "1",
        "listener_owner": "1",
        "hud_pid": "177",
        "hud_exe": "/init (deleted)",
        "hud_exe_after": "/init (deleted)",
        "hud_start_ticks_before": "12345",
        "hud_start_ticks_after": "12345",
        "hud_drm_fd_count": "1",
        "hud_drm_fd_target": "/dev/dri/card0",
        "hud_directory_fd_count": "0",
        "hud_stdio_targets": "/dev/null|/dev/null|/dev/null",
        "hud_mnt_ns_distinct": "1",
        "hud_root_entries": "dev,run",
        "hud_dev_entries": "dri",
        "hud_dri_entries": "card0",
        "hud_run_entries": "a90-dpublic",
        "hud_card_meta": "character special file|e2:0",
        "hud_status_state": "running",
        "hud_status_pid": "177",
        "hud_present_rc": "0",
        "hud_last_sequence": "1",
        "hud_status_intent": "/run/a90-dpublic/hud-intent.json",
        "hud_status_owner": "native-init",
        "hud_status_process_model": "forked-native-child-survives-switch-root",
        "marker_autoreboot_sec": "disabled",
        "marker_dropbear_started": "1",
        "marker_hud_intent_written": "1",
        "marker_hud_presenter_pid_valid": "0",
        "marker_hud_presenter_started": "0",
        "marker_hud_started": "0",
        "marker_wifi_sta_decision": "wifi-sta-pass",
        "wlan0_operstate": "up",
        "wlan0_carrier": "1",
    }
    facts.update(changes)
    assert set(facts) == observer.EXPECTED_KEYS
    body = "\n".join(f"{key}={facts[key]}" for key in sorted(facts))
    return f"{observer.BEGIN}\n{body}\n{observer.END}\n"


class A90H24UfsExecutionV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.f1 = load_script(
            "workspace/public/src/scripts/server-distro/a90_h24_ufs_f1_runner_v1.py"
        )
        cls.d1 = load_script(
            "workspace/public/src/scripts/server-distro/a90_h24_ufs_d1_runner_v1.py"
        )

    def _baseline(self) -> tuple[dict, dict]:
        f1 = self.f1
        native = {
            "exact_bridge": True,
            "version": {
                "command": ["version"],
                "rc": 0,
                "text": f"{f1.CURRENT_VERSION} {f1.CURRENT_BUILD}",
            },
            "selftest": {
                "command": ["selftest"],
                "rc": 0,
                "text": "pass=11 warn=1 fail=0",
            },
        }
        first_boot = {
            "proof": True,
            "enable": 0,
            "latch": 0,
            "status": {
                "command": ["auto-handoff-status"],
                "rc": 0,
                "text": "binding=1 enable=0 latch=0",
            },
        }
        manifest = {
            "schema": "a90-h18-ufs-f1-manifest-v1",
            "capability": "A90_H18_POST_ROOT_FAILURE_ATTRIBUTION_V1",
            "execution_closure": {
                "sha256": f1.CURRENT_INSTALL_EXECUTION_CLOSURE_SHA256
            },
            "candidate_boot": {
                "expected_version": f1.CURRENT_VERSION,
                "expected_build": f1.CURRENT_BUILD,
                "size": f1.CURRENT_BOOT_SIZE,
                "sha256": f1.CURRENT_BOOT_SHA256,
            },
            "rollback_boot": {
                "expected_version": f1.ROLLBACK_VERSION,
                "expected_build": f1.ROLLBACK_BUILD,
                "size": f1.ROLLBACK_SIZE,
                "sha256": f1.ROLLBACK_SHA256,
            },
        }
        result = {
            "schema": "a90-h18-ufs-f1-result-v1",
            "status": "PASS_A90_H18_UFS_RESIDENT_INSTALLED",
            "device_safety_state": "RESIDENT_HEALTHY",
            "candidate_attempt_count": 1,
            "candidate_transfer_count": 1,
            "rollback_transfer_count": 0,
            "candidate_replay": False,
            "rootfs_payload_count": 0,
            "sd_stage_count": 0,
            "userdata_write_count": 0,
            "final_health": {"native": native, "first_boot": first_boot},
        }
        return manifest, result

    def _receipt(self, candidate: Path, observer_sha: str) -> dict:
        f1 = self.f1
        resolution = f1.flat_buildlib.resolve_manifest(
            f1.REPO_ROOT / f1.VERSION_MANIFEST_REL
        )
        source_keys = {}
        for role, relative in (
            (
                "flat_builder",
                "workspace/public/src/scripts/revalidation/a90_flat_builder/build.py",
            ),
            (
                "flat_builder_library",
                "workspace/public/src/scripts/revalidation/a90_flat_builder/buildlib.py",
            ),
        ):
            bound = f1.bound_file(f1.REPO_ROOT / relative)
            source_keys[role] = {
                "path": relative,
                "size": bound["size"],
                "sha256": bound["sha256"],
            }
        return {
            "schema": "a90-flat-builder-v1-ab-receipt",
            "profile": f1.CANDIDATE_BUILD,
            "byte_identical": True,
            "candidate_authority": False,
            "accepted_boot_unchanged": True,
            "manifest_sha256": f1.sha256_file(
                f1.REPO_ROOT / f1.VERSION_MANIFEST_REL
            ),
            "manifest_lineage": [
                {
                    "path": path.relative_to(f1.REPO_ROOT).as_posix(),
                    "sha256": f1.sha256_file(path),
                }
                for path in resolution.lineage
            ],
            "input_pins": {
                "accepted_boot_sha256": "1" * 64,
                "base_boot_sha256": "2" * 64,
                "helper_source_sha256": "3" * 64,
                "init_closure_sha256": f1.NATIVE_CLOSURE_SHA256,
                "mkbootimg_sha256": "4" * 64,
                "observer_authorized_key_sha256": observer_sha,
                "unpack_bootimg_sha256": "5" * 64,
            },
            "source_keys": source_keys,
            "artifacts": {
                "boot": {
                    "path": "boot.img",
                    "bytes": candidate.stat().st_size,
                    "sha256": f1.sha256_file(candidate),
                },
                "helper": {
                    "path": "build/helper",
                    "bytes": f1.CANDIDATE_HELPER_SIZE,
                    "sha256": f1.CANDIDATE_HELPER_SHA256,
                },
                "init": {
                    "path": "build/init",
                    "bytes": f1.CANDIDATE_INIT_SIZE,
                    "sha256": f1.CANDIDATE_INIT_SHA256,
                },
                "ramdisk": {
                    "path": "build/ramdisk.cpio",
                    "bytes": f1.CANDIDATE_RAMDISK_SIZE,
                    "sha256": f1.CANDIDATE_RAMDISK_SHA256,
                },
            },
            "auto_handoff_binding": f1.expected_compiled_binding(),
        }

    @staticmethod
    def _framed_receipt(command: str, text: str, *, sequence: str = "1") -> dict:
        return {
            "command": [command],
            "rc": 0,
            "status": "ok",
            "trust": "A90P1_V1_STRUCTURAL_ONLY",
            "begin": {
                "argc": "1",
                "cmd": command,
                "flags": "0x0",
                "seq": sequence,
            },
            "end": {
                "cmd": command,
                "duration_ms": "1",
                "errno": "0",
                "flags": "0x0",
                "rc": "0",
                "seq": sequence,
                "status": "ok",
            },
            "text": text,
        }

    @classmethod
    def _log_receipt(cls, payload: str, *, sequence: str) -> dict:
        record = cls._framed_receipt("logcat", "", sequence=sequence)
        record["text"] = (
            f"A90P1 BEGIN seq={sequence} cmd=logcat argc=1 flags=0x0\n"
            f"{payload}"
            "[done] logcat (1ms)\n"
            f"A90P1 END seq={sequence} cmd=logcat rc=0 errno=0 "
            "duration_ms=1 flags=0x0 status=ok\n"
        )
        return record

    def _candidate_native_health(self, selftest_text: str) -> tuple[dict, dict]:
        manifest = {"target": {"bridge_realpath": "/dev/ttyACM0"}}
        native = {
            "exact_bridge": True,
            "selected_realpath": "/dev/ttyACM0",
            "version": self._framed_receipt(
                "version",
                f"version: {self.f1.CANDIDATE_VERSION} "
                f"build={self.f1.CANDIDATE_BUILD}\n",
            ),
            "selftest": self._framed_receipt("selftest", selftest_text),
        }
        return manifest, native

    def _inventory(self, timestamp_utc: str) -> dict:
        f1 = self.f1
        observed_devt = "259:17"
        return {
            "schema": f1.INVENTORY_SCHEMA,
            "status": "PASS",
            "run_id": "a90-h24-ufs-f1-20260812-01",
            "timestamp_utc": timestamp_utc,
            "target": "Samsung Galaxy A90 5G",
            "identity": f1.UFS_IDENTITY,
            "observed_devt": observed_devt,
            "devt_stability": "same-session-only",
            "content_manifest_sha256": (
                "e1950058627446d6bbd487d6a17b80f5766be4956b54cb56659b541dab09f8f6"
            ),
            "content_file_count": 19,
            "secrets_hashed": False,
            "public_tunnel": "disabled",
            "mounted_read_only": True,
            "mounted_norecovery": True,
            "mounted_after": False,
            "userdata_write_count": 0,
            "format_count": 0,
            "repair_count": 0,
            "s22plus_command_count": 0,
            "s20plus_command_count": 0,
            "provenance": {
                "fresh_d0_bridge": f1.EXACT_BRIDGE_DEVICE,
                "fresh_d0_bridge_realpath": "/dev/ttyACM0",
                "fresh_d0_version": f1.CURRENT_VERSION,
                "fresh_d0_build": f1.CURRENT_BUILD,
                "fresh_d0_selftest": "pass=11 warn=1 fail=0",
                "fresh_d0_ufs_marker": (
                    "A90H24_D0 exact=1 devt=259:17 "
                    "devt_policy=same-session-only ufs_mounted=0 "
                    "enable_absent=1 latch_absent=1 userdata_write=0"
                ),
            },
        }

    def _journal_opening(self) -> list[dict]:
        binding_sha = self.f1.json_sha256({})
        return [
            {
                "action": "approval-consumed",
                "approval_consumed": True,
                "device_safety_state": "RESIDENT_HEALTHY",
                "candidate_transfer_count": 0,
                "rollback_transfer_count": 0,
                "rootfs_payload_count": 0,
                "sd_stage_count": 0,
                "userdata_write_count": 0,
                "approval_binding": {},
                "approval_binding_sha256": binding_sha,
            },
            {"action": "guard-armed", "candidate_replay": False, "guard": {}},
            {
                "action": "candidate-intent",
                "candidate_sha256": self.f1.CANDIDATE_BOOT_SHA256,
                "candidate_attempt_limit": 1,
                "partition": "boot",
                "rollback_pre_authorized": True,
                "approval_binding_sha256": binding_sha,
                "candidate_replay": False,
                "rootfs_payload_count": 0,
                "sd_stage_count": 0,
                "userdata_write_count": 0,
            },
        ]

    def test_f1_identity_is_h24_only(self) -> None:
        self.assertEqual(
            self.f1.CAPABILITY,
            "A90_H24_PRIVATE_CARD_ROOT_PERSISTENT_UFS_SERVER_V1",
        )
        self.assertEqual(self.f1.CURRENT_VERSION, "0.11.186")
        self.assertEqual(self.f1.CANDIDATE_VERSION, "0.11.192")
        self.assertEqual(
            self.f1.CANDIDATE_BUILD,
            "phase3-minimal-h24-ufs-auth-native-hud-private-card-root-minimal-debian-dev",
        )
        self.assertEqual(self.f1.CANDIDATE_BOOT_SIZE, 58372096)
        self.assertEqual(
            self.f1.CANDIDATE_BOOT_SHA256,
            "d8c280e4acee5d17d13270fdf25535b4ce05304e786bc22efa84ab16f6b82782",
        )
        self.assertEqual(
            self.f1.CANDIDATE_AB_RECEIPT_SHA256,
            "980a366754afe176062cc9712ac26cd89479da1d37b91ceed7539139cd0a90cf",
        )
        self.assertEqual(self.f1.CANDIDATE_AB_RECEIPT_SIZE, 5494)

    def test_h24_observer_requires_exact_private_card_root(self) -> None:
        observer = self.d1.persistent_observer
        result = observer.classify(
            passing_h24_transcript(observer),
            0,
            True,
        )
        self.assertTrue(result["proof"])
        self.assertTrue(result["checks"]["firstboot_overlay_disabled"])
        self.assertTrue(result["checks"]["native_hud_presenter"])

    def test_h24_observer_rejects_stale_status_pid(self) -> None:
        observer = self.d1.persistent_observer
        result = observer.classify(
            passing_h24_transcript(observer, hud_status_pid="999"),
            0,
            True,
        )
        self.assertFalse(result["proof"])
        self.assertFalse(result["checks"]["native_hud_presenter"])

    def test_h24_observer_rejects_extra_child_root_entry(self) -> None:
        observer = self.d1.persistent_observer
        result = observer.classify(
            passing_h24_transcript(observer, hud_root_entries="dev,proc,run"),
            0,
            True,
        )
        self.assertFalse(result["proof"])
        self.assertFalse(result["checks"]["native_hud_presenter"])

    def test_h24_observer_rejects_private_card_root_identity_drift(self) -> None:
        observer = self.d1.persistent_observer
        cases = (
            {"hud_drm_fd_target": "/dev/dri/card1"},
            {"hud_exe_after": "/usr/bin/other"},
            {"hud_start_ticks_after": "12346"},
            {"hud_directory_fd_count": "1"},
            {"hud_stdio_targets": "/dev/null|/dev/null|/dev/dri/card0"},
            {"hud_mnt_ns_distinct": "0"},
            {"hud_run_entries": "a90-dpublic,leaked"},
            {"hud_card_meta": "character special file|103:0"},
            {"hud_status_intent": "/run/a90-dpublic/stale.json"},
            {"hud_status_owner": "firstboot-overlay"},
        )
        for changes in cases:
            with self.subTest(changes=changes):
                result = observer.classify(
                    passing_h24_transcript(observer, **changes),
                    0,
                    True,
                )
                self.assertFalse(result["proof"])
                self.assertFalse(result["checks"]["native_hud_presenter"])

    def test_h24_observer_rejects_debian_device_exposure(self) -> None:
        observer = self.d1.persistent_observer
        bad_cases = (
            {
                "debian_dev_entries_before": (
                    "block,console,null,ptmx,pts,random,tty,ttyGS0,urandom,zero"
                ),
                "debian_dev_entries_after": (
                    "block,console,null,ptmx,pts,random,tty,ttyGS0,urandom,zero"
                ),
            },
            {"debian_dev_block_count": "1"},
            {
                "debian_dev_core_meta": (
                    "console=character special file|5:1|600;"
                    "tty=character special file|5:0|666;"
                    "ptmx=character special file|5:2|666;"
                    "null=character special file|e2:0|666;"
                    "zero=character special file|1:5|666;"
                    "random=character special file|1:8|666;"
                    "urandom=character special file|1:9|666"
                )
            },
            {"debian_dev_mount": "devtmpfs|devtmpfs|rw,nosuid,relatime"},
            {"debian_dev_pts_mount": "__invalid_count_0"},
            {
                "debian_dev_entries_after": (
                    "console,null,ptmx,pts,random,tty,urandom,zero"
                )
            },
        )
        for changes in bad_cases:
            with self.subTest(changes=changes):
                result = observer.classify(
                    passing_h24_transcript(observer, **changes), 0, True
                )
                self.assertFalse(result["proof"])
                self.assertFalse(result["checks"]["debian_minimal_dev"])

    def test_h24_observer_accepts_debian_dev_without_optional_ttygs0(self) -> None:
        observer = self.d1.persistent_observer
        entries = "console,null,ptmx,pts,random,tty,urandom,zero"
        result = observer.classify(
            passing_h24_transcript(
                observer,
                debian_dev_entries_before=entries,
                debian_dev_entries_after=entries,
                debian_dev_ttygs0_meta="absent",
            ),
            0,
            True,
        )
        self.assertTrue(result["proof"])

    def test_h24_observer_remote_script_emits_exact_private_root_facts(self) -> None:
        observer = self.d1.persistent_observer
        for key in (
            "hud_drm_fd_target",
            "hud_directory_fd_count",
            "hud_exe_after",
            "hud_start_ticks_before",
            "hud_start_ticks_after",
            "hud_stdio_targets",
            "hud_mnt_ns_distinct",
            "hud_root_entries",
            "hud_dev_entries",
            "hud_dri_entries",
            "hud_run_entries",
            "hud_card_meta",
            "hud_status_pid",
            "hud_status_intent",
            "hud_status_owner",
            "hud_status_process_model",
            "debian_dev_entries_before",
            "debian_dev_entries_after",
            "debian_dev_core_meta",
            "debian_dev_pts_meta",
            "debian_dev_ttygs0_meta",
            "debian_dev_block_count",
            "debian_dev_mount",
            "debian_dev_pts_mount",
        ):
            with self.subTest(key=key):
                self.assertIn(f"echo {key}=", observer.REMOTE_SCRIPT)
        self.assertIn("LC_ALL=C", observer.REMOTE_SCRIPT)
        self.assertNotIn("/usr/bin/paste", observer.REMOTE_SCRIPT)

    def test_h24_observer_rejects_boot_firstboot_overlay(self) -> None:
        observer = self.d1.persistent_observer
        result = observer.classify(
            passing_h24_transcript(observer, firstboot_mount_count="1"),
            0,
            True,
        )
        self.assertFalse(result["proof"])
        self.assertFalse(result["checks"]["firstboot_overlay_disabled"])

    def test_h24_observer_requires_zero_preintent_legacy_hud_markers(self) -> None:
        observer = self.d1.persistent_observer
        result = observer.classify(
            passing_h24_transcript(
                observer,
                marker_hud_presenter_pid_valid="1",
                marker_hud_presenter_started="1",
                marker_hud_started="1",
            ),
            0,
            True,
        )
        self.assertFalse(result["proof"])
        self.assertFalse(result["checks"]["native_hud_presenter"])

    def test_candidate_native_health_rejects_contradictory_selftest(self) -> None:
        manifest, native = self._candidate_native_health(
            "selftest: pass=11 warn=1 fail=0 fail=9 duration=1ms entries=12\n"
        )
        with self.assertRaisesRegex(self.f1.ContractError, "health facts"):
            self.f1.validate_candidate_native_health(native, manifest)

    def test_auto_status_rejects_contradictory_duplicate_fact(self) -> None:
        text = (
            "A90AUTO_STATUS binding=1 enable=0 latch=0 "
            f"build={self.f1.CANDIDATE_BUILD}\n"
            "A90AUTO_STATUS binding=1 enable=1 latch=1 "
            f"build={self.f1.CANDIDATE_BUILD}\n"
        )
        record = self._framed_receipt("auto-handoff-status", text)
        with self.assertRaisesRegex(self.f1.ContractError, "not unique"):
            self.f1.validate_h24_auto_status_record(record, enable=0, latch=0)

    def test_f1_preflight_rejects_malformed_semantic_duplicate(self) -> None:
        text = (
            "A90H24_F1_PRE exact=1 devt=259:17 "
            "devt_policy=same-session-only ufs_mounted=0 "
            "enable_absent=1 latch_absent=1 userdata_write=0\n"
            "A90H24_F1_PRE exact=0 devt=259:17 ufs_mounted=1\n"
        )
        with mock.patch.object(
            self.f1.staging,
            "require_exact_bridge",
            return_value={"selected_realpath": "/dev/ttyACM0"},
        ), mock.patch.object(
            self.f1,
            "require_current_native_health",
            return_value={"proof": True},
        ), mock.patch.object(
            self.f1.base,
            "run_f1_shell",
            return_value={"text": text},
        ), self.assertRaisesRegex(self.f1.ContractError, "preflight"):
            self.f1.exact_preflight({}, mock.Mock(stage=object()), mock.Mock())

    def test_post_flash_revalidation_rejects_source_drift(self) -> None:
        for changed_name, rollback_mode in (
            ("candidate_boot", False),
            ("rollback_boot", True),
            ("flash_runner", False),
        ):
            with self.subTest(changed_name=changed_name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                candidate = root / "candidate.img"
                rollback = root / "rollback.img"
                flash_runner = root / "flash.py"
                candidate.write_bytes(b"BOOT")
                rollback.write_bytes(b"BACK")
                flash_runner.write_bytes(b"RUN!")
                paths = {
                    "candidate_boot": candidate,
                    "rollback_boot": rollback,
                    "flash_runner": flash_runner,
                }
                manifest = {
                    name: self.f1.bound_file(path)
                    for name, path in paths.items()
                }
                manifest["candidate_boot"].update(
                    {
                        "partition": "boot",
                        "expected_version": self.f1.CANDIDATE_VERSION,
                        "expected_build": self.f1.CANDIDATE_BUILD,
                        "compiled_binding": {"binding_sha256": "a" * 64},
                        "ab_receipt": {"sha256": "b" * 64},
                        "enable_path": self.f1.ENABLE_PATH,
                        "latch_path": self.f1.LATCH_PATH,
                    }
                )
                manifest["rollback_boot"].update(
                    {
                        "partition": "boot",
                        "expected_version": self.f1.ROLLBACK_VERSION,
                        "expected_build": self.f1.ROLLBACK_BUILD,
                    }
                )
                self.f1.revalidate_post_flash_inputs(
                    manifest, rollback=rollback_mode
                )
                paths[changed_name].write_bytes(b"FAIL")
                with self.assertRaisesRegex(self.f1.ContractError, "changed"):
                    self.f1.revalidate_post_flash_inputs(
                        manifest, rollback=rollback_mode
                    )

    def test_compiled_binding_is_v10_private_card_root(self) -> None:
        binding = self.f1.expected_compiled_binding()
        self.assertEqual(binding["schema"], "a90-compiled-auto-handoff-binding-v11")
        self.assertEqual(binding["observer_auth"], "boot-private-tmpfs-v1")
        self.assertEqual(binding["display_owner"], "native-handoff-hud-v1")
        self.assertEqual(binding["firstboot_overlay"], "disabled")
        self.assertEqual(
            binding["hud_drm_device_access"],
            "private-pivot-root-card0-bind-v1",
        )
        self.assertEqual(
            binding["hud_device_exposure"],
            "card0-only-no-userdata-v1",
        )
        self.assertEqual(
            binding["debian_dev_tree_exposure"],
            "minimal-core-char-no-drm-no-userdata-v1",
        )
        self.assertEqual(
            binding["debian_proc_hud_root_exposure"],
            "card0-and-shared-public-run-no-block-no-userdata-v1",
        )
        content = {key: value for key, value in binding.items() if key != "binding_sha256"}
        self.assertEqual(binding["binding_sha256"], self.f1.json_sha256(content))

    def test_ab_receipt_binds_private_observer_identity_without_public_literal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            candidate = Path(temporary) / "boot.img"
            candidate.write_bytes(b"boot")
            observer_sha = "a" * 64
            value = self._receipt(candidate, observer_sha)
            with mock.patch.object(
                self.f1,
                "CANDIDATE_BOOT_SIZE",
                candidate.stat().st_size,
            ), mock.patch.object(
                self.f1,
                "CANDIDATE_BOOT_SHA256",
                self.f1.sha256_file(candidate),
            ):
                self.assertEqual(
                    self.f1.validate_ab_receipt(value, candidate, observer_sha),
                    self.f1.expected_compiled_binding(),
                )

    def test_ab_receipt_rejects_self_consistent_unreviewed_boot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            candidate = Path(temporary) / "boot.img"
            candidate.write_bytes(b"unreviewed")
            observer_sha = "a" * 64
            value = self._receipt(candidate, observer_sha)
            with self.assertRaisesRegex(self.f1.ContractError, "receipt"):
                self.f1.validate_ab_receipt(value, candidate, observer_sha)

    def test_reviewed_ab_receipt_file_hash_is_exact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            receipt = Path(temporary) / "ab-receipt.json"
            receipt.write_text("{}\n", encoding="utf-8")
            exact = self.f1.sha256_file(receipt)
            with mock.patch.object(
                self.f1,
                "CANDIDATE_AB_RECEIPT_SHA256",
                exact,
            ), mock.patch.object(
                self.f1,
                "CANDIDATE_AB_RECEIPT_SIZE",
                receipt.stat().st_size,
            ):
                _, value = self.f1.load_reviewed_ab_receipt(receipt)
                self.assertEqual(value, {})
            receipt.write_text('{"changed":true}\n', encoding="utf-8")
            with mock.patch.object(
                self.f1,
                "CANDIDATE_AB_RECEIPT_SHA256",
                exact,
            ), mock.patch.object(
                self.f1,
                "CANDIDATE_AB_RECEIPT_SIZE",
                len("{}\n".encode()),
            ), self.assertRaisesRegex(self.f1.ContractError, "receipt changed"):
                self.f1.load_reviewed_ab_receipt(receipt)

    def test_live_manifest_binding_rejects_semantic_receipt_replacement(self) -> None:
        exact = {
            "path": "/private/reviewed-ab-receipt.json",
            "size": self.f1.CANDIDATE_AB_RECEIPT_SIZE,
            "sha256": self.f1.CANDIDATE_AB_RECEIPT_SHA256,
        }
        self.f1.require_reviewed_ab_receipt_binding(exact)
        replaced = {**exact, "sha256": "0" * 64}
        with self.assertRaisesRegex(self.f1.ContractError, "reviewed artifact"):
            self.f1.require_reviewed_ab_receipt_binding(replaced)

    def test_ab_receipt_rejects_observer_key_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            candidate = Path(temporary) / "boot.img"
            candidate.write_bytes(b"boot")
            value = self._receipt(candidate, "a" * 64)
            with self.assertRaisesRegex(self.f1.ContractError, "receipt"):
                self.f1.validate_ab_receipt(value, candidate, "b" * 64)

    def test_ab_receipt_rejects_unreviewed_input_pin(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            candidate = Path(temporary) / "boot.img"
            candidate.write_bytes(b"boot")
            value = self._receipt(candidate, "a" * 64)
            value["input_pins"]["unreviewed_pin"] = "b" * 64
            with self.assertRaisesRegex(self.f1.ContractError, "receipt"):
                self.f1.validate_ab_receipt(value, candidate, "a" * 64)

    def test_h18_predecessor_requires_exact_installed_boot(self) -> None:
        manifest, result = self._baseline()
        self.f1._baseline_inputs(manifest, result)
        manifest["candidate_boot"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(self.f1.ContractError, "H18 resident"):
            self.f1._baseline_inputs(manifest, result)

    def test_h18_d1_predecessor_requires_exact_seven_record_terminal(self) -> None:
        self.assertEqual(len(self.f1.H18_D1_RECORDS), 7)
        self.assertEqual(
            self.f1.H18_D1_TERMINAL_RESULT_SHA256,
            "8b77eed3937fb975b034572b070d7f7146ea800822b0254aa28570b71a79b2c4",
        )
        value = {
            "run": "run01",
            "records": [
                {"path": f"/{name}", "size": size, "sha256": sha}
                for name, size, sha in self.f1.H18_D1_RECORDS[:5]
            ],
            "terminal_result_sha256": self.f1.H18_D1_TERMINAL_RESULT_SHA256,
        }
        with self.assertRaisesRegex(self.f1.ContractError, "terminal binding"):
            self.f1.validate_h18_d1_terminal(value, {}, {})

    def test_h18_live_health_does_not_use_stale_shared_allowlist(self) -> None:
        receipts = {
            command: {"command": [command], "receipt": command}
            for command in ("version", "status", "selftest")
        }
        with mock.patch.object(
            self.f1.base,
            "run_f1_cmd",
            side_effect=lambda _args, command: receipts[command[0]],
        ) as run_cmd, mock.patch.object(
            self.f1.staging,
            "validate_native_health_receipts",
        ) as validate, mock.patch.object(
            self.f1.staging,
            "require_native_health",
        ) as stale_allowlist:
            result = self.f1.require_current_native_health(SimpleNamespace())
        self.assertEqual(result, receipts)
        self.assertEqual(
            [call.args[1] for call in run_cmd.call_args_list],
            [["version"], ["status"], ["selftest"]],
        )
        validate.assert_called_once_with(
            receipts,
            expected_version=self.f1.CURRENT_VERSION,
            expected_build=self.f1.CURRENT_BUILD,
        )
        stale_allowlist.assert_not_called()

    def test_reconcile_h18_health_checks_bridge_before_device_reads(self) -> None:
        events: list[str] = []
        receipts = {
            command: {"command": [command]}
            for command in ("version", "status", "selftest")
        }
        spec = mock.Mock(stage=object())
        with mock.patch.object(
            self.f1.staging,
            "require_exact_bridge",
            side_effect=lambda *_a: events.append("bridge"),
        ), mock.patch.object(
            self.f1.base,
            "run_f1_cmd",
            side_effect=lambda _args, command: (
                events.append(command[0]) or receipts[command[0]]
            ),
        ), mock.patch.object(self.f1.staging, "validate_native_health_receipts"):
            self.f1.require_current_native_health_on_exact_bridge(
                spec, argparse.Namespace()
            )
        self.assertEqual(events, ["bridge", "version", "status", "selftest"])

    def test_d1_install_result_must_equal_deep_closed_f1_journal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            transaction = Path(temporary) / "h24-f1-live"
            journal = transaction / "journal"
            journal.mkdir(parents=True)
            result_path = transaction / "result.json"
            manifest = {"_manifest_sha256": "a" * 64}
            result = {
                "schema": self.d1.f1.RESULT_SCHEMA,
                "status": "PASS_A90_H24_UFS_RESIDENT_INSTALLED",
                "manifest_sha256": "a" * 64,
                "device_safety_state": "RESIDENT_HEALTHY",
                "candidate_attempt_count": 1,
                "candidate_transfer_count": 1,
                "rollback_transfer_count": 0,
                "candidate_replay": False,
                "rootfs_payload_count": 0,
                "sd_stage_count": 0,
                "userdata_write_count": 0,
                "final_health": {"proof": True},
            }
            result_path.write_text(json.dumps(result), encoding="utf-8")
            binding = self.d1.f1.bound_file(result_path)
            with mock.patch.object(
                self.d1.f1, "_journal_dir", return_value=journal
            ), mock.patch.object(
                self.d1.f1,
                "read_journal",
                return_value=[{"action": "closed", "result": result}],
            ), mock.patch.object(self.d1.f1, "validate_stored_candidate_health"):
                self.assertEqual(
                    self.d1._load_install_result(
                        binding,
                        binding["sha256"],
                        manifest,
                    ),
                    result,
                )
            forged = {**result, "final_health": {"proof": False}}
            with mock.patch.object(
                self.d1.f1, "_journal_dir", return_value=journal
            ), mock.patch.object(
                self.d1.f1,
                "read_journal",
                return_value=[{"action": "closed", "result": forged}],
            ), mock.patch.object(self.d1.f1, "validate_stored_candidate_health"):
                with self.assertRaisesRegex(self.d1.ContractError, "terminal"):
                    self.d1._load_install_result(
                        binding,
                        binding["sha256"],
                        manifest,
                    )

    def test_d0_inventory_is_run_bound_and_no_older_than_15_minutes(self) -> None:
        now = dt.datetime(2026, 8, 12, 0, 15, 0, tzinfo=dt.UTC)
        value = self._inventory("2026-08-12T00:00:00Z")
        self.f1.validate_ufs_inventory(
            value,
            expected_run_id=value["run_id"],
            expected_bridge_realpath="/dev/ttyACM0",
            enforce_fresh=True,
            now=now,
        )
        value["timestamp_utc"] = "2026-08-11T23:59:59Z"
        with self.assertRaisesRegex(self.f1.ContractError, "inventory"):
            self.f1.validate_ufs_inventory(
                value,
                expected_run_id=value["run_id"],
                expected_bridge_realpath="/dev/ttyACM0",
                enforce_fresh=True,
                now=now,
            )
        self.f1.validate_ufs_inventory(
            value,
            expected_run_id=value["run_id"],
            expected_bridge_realpath="/dev/ttyACM0",
            enforce_fresh=False,
            now=now,
        )
        value["s20plus_command_count"] = 1
        with self.assertRaisesRegex(self.f1.ContractError, "inventory"):
            self.f1.validate_ufs_inventory(
                value,
                expected_run_id=value["run_id"],
                expected_bridge_realpath="/dev/ttyACM0",
                enforce_fresh=False,
                now=now,
            )

    def test_historical_host_capability_qualification_fails_closed_after_contract_change(self) -> None:
        with self.assertRaisesRegex(
            self.f1.ContractError,
            "H24 host capability execution hash changed",
        ):
            self.f1.validate_host_capability_qualification()

    def test_execution_qualification_requires_both_runners(self) -> None:
        closure = self.f1.execution_closure()
        report = {
            "schema": self.f1.EXECUTION_REVIEW_SCHEMA,
            "capability": self.f1.CAPABILITY,
            "verdict": "PASS_GO",
            "review_date": "2026-08-12",
            "reviewer": self.f1.EXECUTION_REVIEWER,
            "execution_closure_sha256": closure["sha256"],
            "execution_file_count": len(closure["files"]),
            "review_scope": self.f1.EXECUTION_REVIEW_SCOPE,
            "incident": self.f1.EXECUTION_REVIEW_INCIDENT,
            "new_hazard_or_incident": True,
            "findings": {"high": [], "medium": [], "low": []},
            "validated_invariants": list(
                self.f1.EXECUTION_REVIEW_REQUIRED_INVARIANTS
            ),
            "review_contacts": {
                "device": 0,
                "dev": 0,
                "usb": 0,
                "network": 0,
                "workspace_private": 0,
                "s22plus_paths": 0,
                "s20plus_paths": 0,
                "file_modifications": 0,
            },
            "live_authority": False,
        }
        value = {
            "schema": self.f1.QUALIFICATION_SCHEMA,
            "capability": self.f1.CAPABILITY,
            "verdict": "PASS_GO",
            "predecessor_capability_closure_sha256": (
                self.f1.HOST_CAPABILITY_CLOSURE_SHA256
            ),
            "execution_closure_sha256": closure["sha256"],
            "execution_hashes": closure["files"],
            "review_scope": self.f1.EXECUTION_REVIEW_SCOPE,
            "incident": self.f1.EXECUTION_REVIEW_INCIDENT,
            "new_hazard_or_incident": True,
            "ordinal_requalification_required": False,
            "f1_runner_qualified": True,
            "d1_runner_qualified": True,
            "review_report": self.f1.EXECUTION_REVIEW_REPORT_REL,
            "live_authority": False,
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report_path = root / self.f1.EXECUTION_REVIEW_REPORT_REL
            report_path.parent.mkdir(parents=True)
            report_path.write_text(json.dumps(report), encoding="utf-8")
            value["review_report_sha256"] = self.f1.sha256_file(report_path)
            path = root / "qualification.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            binding = self.f1.bound_file(path)
            with mock.patch.object(self.f1, "REPO_ROOT", root):
                self.f1.validate_qualification(binding, closure)
                value["d1_runner_qualified"] = False
                path.unlink()
                path.write_text(json.dumps(value), encoding="utf-8")
                binding = self.f1.bound_file(path)
                with self.assertRaisesRegex(
                    self.f1.ContractError,
                    "qualification",
                ):
                    self.f1.validate_qualification(binding, closure)
                value["d1_runner_qualified"] = True
                report["findings"]["high"].append("unresolved")
                report_path.write_text(json.dumps(report), encoding="utf-8")
                value["review_report_sha256"] = self.f1.sha256_file(report_path)
                path.unlink()
                path.write_text(json.dumps(value), encoding="utf-8")
                binding = self.f1.bound_file(path)
                with self.assertRaisesRegex(
                    self.f1.ContractError,
                    "review",
                ):
                    self.f1.validate_qualification(binding, closure)

    def test_reconstructed_candidate_requires_write_and_readback(self) -> None:
        self.assertFalse(self.f1._reconstructed_candidate_transfer_is_proven({}))
        self.assertFalse(
            self.f1._reconstructed_candidate_transfer_is_proven(
                {"phase_classification": {"boot_write_completed": True}}
            )
        )
        self.assertFalse(
            self.f1._reconstructed_candidate_transfer_is_proven(
                {"phase_classification": {"readback_completed": True}}
            )
        )
        self.assertTrue(
            self.f1._reconstructed_candidate_transfer_is_proven(
                {
                    "phase_classification": {
                        "boot_write_completed": True,
                        "readback_completed": True,
                    }
                }
            )
        )

    def test_journal_rejects_count_one_without_candidate_launch(self) -> None:
        manifest = {
            "run_id": "run",
            "candidate_boot": {"size": 1, "sha256": "b" * 64},
            "target": {"bridge_realpath": "/dev/ttyACM0"},
        }
        records = [
            {
                "action": "approval-consumed",
                "approval_consumed": True,
                "device_safety_state": "RESIDENT_HEALTHY",
                "candidate_transfer_count": 0,
                "rollback_transfer_count": 0,
                "rootfs_payload_count": 0,
                "sd_stage_count": 0,
                "userdata_write_count": 0,
                "approval_binding": {},
                "approval_binding_sha256": self.f1.json_sha256({}),
            },
            {"action": "guard-armed", "candidate_replay": False, "guard": {}},
            {
                "action": "candidate-intent",
                "candidate_sha256": self.f1.CANDIDATE_BOOT_SHA256,
                "candidate_attempt_limit": 1,
                "partition": "boot",
                "rollback_pre_authorized": True,
                "approval_binding_sha256": self.f1.json_sha256({}),
                "candidate_replay": False,
                "rootfs_payload_count": 0,
                "sd_stage_count": 0,
                "userdata_write_count": 0,
            },
            {
                "action": "candidate-result",
                "candidate_attempt_count": 1,
                "candidate_transfer_count": 1,
                "candidate_replay": False,
                "record": {"returncode": 0},
            },
        ]
        with self.assertRaisesRegex(self.f1.ContractError, "launch/result proof"):
            self.f1._validate_f1_journal(records, manifest, "a" * 64)

    def test_journal_rejects_malformed_rollback_intent_and_launch_prefixes(self) -> None:
        manifest_sha = "a" * 64
        manifest = {
            "run_id": "run",
            "candidate_boot": {"size": 1, "sha256": "b" * 64},
            "rollback_boot": {"size": 2, "sha256": self.f1.ROLLBACK_SHA256},
            "target": {"bridge_realpath": "/dev/ttyACM0"},
        }
        candidate_launch = {
            "action": "candidate-launch",
            "candidate_replay": False,
            "rollback_replay": False,
            "launch": {
                "schema": "a90-h24-flash-process-group-v1",
                "kind": "candidate",
                "manifest_sha256": manifest_sha,
                "artifact_sha256": "b" * 64,
                "artifact_size": 1,
                "release_count_max": 1,
            },
        }
        candidate_result = {
            "action": "candidate-result",
            "candidate_attempt_count": 1,
            "candidate_transfer_count": 1,
            "candidate_replay": False,
            "record": {"returncode": 0},
        }
        prefix = self._journal_opening() + [candidate_launch, candidate_result]
        with self.assertRaisesRegex(self.f1.ContractError, "rollback intent"):
            self.f1._validate_f1_journal(
                prefix + [{"action": "rollback-intent"}],
                manifest,
                manifest_sha,
            )
        rollback_intent = {
            "action": "rollback-intent",
            "rollback_sha256": self.f1.ROLLBACK_SHA256,
            "rollback_attempt_limit": 1,
            "candidate_replay": False,
            "recovery_mode": "from-native",
        }
        with self.assertRaisesRegex(self.f1.ContractError, "rollback launch"):
            self.f1._validate_f1_journal(
                prefix
                + [
                    rollback_intent,
                    {"action": "rollback-launch", "launch": {}},
                ],
                manifest,
                manifest_sha,
            )

    def test_candidate_durable_health_reconcile_has_no_device_read(self) -> None:
        manifest = {"run_id": "run", "target": {"bridge_realpath": "/dev/ttyACM0"}}
        health = {"stored": "candidate"}
        records = [
            {"action": "approval-consumed"},
            {"action": "candidate-intent"},
            {
                "action": "candidate-result",
                "candidate_transfer_count": 1,
                "record": {"returncode": 0},
            },
            {
                "action": "candidate-health",
                "device_safety_state": "RESIDENT_HEALTHY",
                "health": health,
            },
        ]
        args = argparse.Namespace(operator_attended=True)
        with mock.patch.object(self.f1, "validate_live_args"), mock.patch.object(
            self.f1, "load_manifest", return_value=manifest
        ), mock.patch.object(self.f1, "_spec", return_value=object()), mock.patch.object(
            self.f1, "_journal_dir", return_value=Path("journal")
        ), mock.patch.object(
            self.f1, "read_journal", return_value=records
        ), mock.patch.object(self.f1, "require_consumed_approval"), mock.patch.object(
            self.f1,
            "validate_stored_candidate_health",
            return_value=health,
        ), mock.patch.object(
            self.f1, "_publish_reconciled_result", side_effect=lambda *a: a[-1]
        ), mock.patch.object(self.f1, "exact_candidate_health") as device_read:
            result = self.f1.reconcile_health(Path("manifest"), "a" * 64, args)
        device_read.assert_not_called()
        self.assertEqual(result["final_health"], health)

    def test_rollback_durable_health_reconcile_has_no_device_read(self) -> None:
        manifest = {"run_id": "run", "target": {"bridge_realpath": "/dev/ttyACM0"}}
        health = {"stored": "rollback"}
        records = [
            {"action": "approval-consumed"},
            {"action": "candidate-intent"},
            {
                "action": "candidate-result",
                "candidate_transfer_count": 1,
                "record": {"returncode": 0},
            },
            {"action": "rollback-intent"},
            {
                "action": "rollback-result",
                "rollback_transfer_count": 1,
                "record": {"returncode": 0},
            },
            {
                "action": "rollback-health",
                "device_safety_state": "BASELINE_HEALTHY",
                "health": health,
            },
        ]
        args = argparse.Namespace(operator_attended=True)
        with mock.patch.object(self.f1, "validate_live_args"), mock.patch.object(
            self.f1, "load_manifest", return_value=manifest
        ), mock.patch.object(self.f1, "_spec", return_value=object()), mock.patch.object(
            self.f1, "_journal_dir", return_value=Path("journal")
        ), mock.patch.object(
            self.f1, "read_journal", return_value=records
        ), mock.patch.object(self.f1, "require_consumed_approval"), mock.patch.object(
            self.f1,
            "validate_stored_rollback_health",
            return_value=health,
        ), mock.patch.object(
            self.f1, "_publish_reconciled_result", side_effect=lambda *a: a[-1]
        ), mock.patch.object(self.f1.base, "verify_final_health") as device_read:
            result = self.f1.reconcile_health(Path("manifest"), "a" * 64, args)
        device_read.assert_not_called()
        self.assertEqual(result["final_health"], health)

    def test_d1_journal_has_pending_then_physical_return_close(self) -> None:
        self.assertEqual(self.d1.JOURNAL_ACTIONS[4:], (
            "current-state",
            "final-health",
            "closed",
        ))
        self.assertEqual(len(self.d1.JOURNAL_NAMES), 7)

    def test_approval_binds_persistent_mode_and_observer(self) -> None:
        manifest = {
            "run_id": "a90-h24-ufs-f1-20260810-01",
            "target": {
                "profile": "galaxy-a90-5g-native-init",
                "bridge_device": "bridge",
                "bridge_realpath": "/dev/ttyACM0",
                "recovery_adb_identity_evidence": {"proof": True},
            },
            "observer": {
                "private_key": {"sha256": "a" * 64},
                "public_key_sha256": "b" * 64,
            },
        }
        args = argparse.Namespace(
            expect_manifest_sha256="c" * 64,
            expect_install_result_sha256="d" * 64,
            expect_execution_closure_sha256="e" * 64,
        )
        value = self.d1.approval_binding(
            manifest,
            args,
            Path("/private/run01"),
            created_utc="2026-08-10T00:00:00Z",
            expires_utc="2026-08-10T00:30:00Z",
        )
        self.assertTrue(value["persistent_debian_expected"])
        self.assertTrue(value["diagnostic_native_fallback_allowed"])
        self.assertTrue(value["diagnostic_record_required_for_attribution"])
        self.assertEqual(value["missing_diagnostic_record_verdict"], "NO_PROOF_NO_REPLAY")
        self.assertFalse(value["automatic_native_return_expected"])
        self.assertFalse(value["physical_return_dispatched_by_runner"])
        self.assertEqual(value["observer_public_key_sha256"], "b" * 64)

    def test_live_result_pass_stays_health_pending_and_open(self) -> None:
        result = self.d1._live_result(
            {"server": {"proof": True}, "guard_release": {"released": True}},
            "a" * 64,
            "yes",
        )
        self.assertEqual(result["status"], "PASS_A90_H24_PERSISTENT_SERVER_LIVE")
        self.assertEqual(
            result["device_safety_state"], "HEALTH_PENDING_PERSISTENT_DEBIAN"
        )
        self.assertFalse(result["resident_healthy"])
        self.assertFalse(result["ordinal_closed"])
        self.assertFalse(result["inter_effect_health_barrier_satisfied"])
        self.assertFalse(result["new_device_effect_authority"])

    def test_live_result_refuses_unconfirmed_visibility(self) -> None:
        result = self.d1._live_result(
            {"server": {"proof": True}, "guard_release": {"released": True}},
            "a" * 64,
            "unavailable",
        )
        self.assertEqual(result["status"], "NO_PROOF_A90_H24_PERSISTENT_SERVER_LIVE")

    def test_persistent_observation_recomputes_exact_transcript_on_resume(self) -> None:
        transcript = passing_h24_transcript(self.d1.persistent_observer)
        server = self.d1.persistent_observer.classify(transcript, 0, True)
        server["attempts"] = 1
        observation = {
            "proof": True,
            "server": server,
            "guard_release": {"released": True},
        }
        self.assertTrue(self.d1._valid_persistent_observation(observation, "yes"))
        server["facts"]["hud_start_ticks_after"] = "12346"
        self.assertFalse(self.d1._valid_persistent_observation(observation, "yes"))

    def test_persistent_observation_never_waits_for_native_return(self) -> None:
        guard = mock.Mock()
        with mock.patch.object(
            self.d1.legacy, "wait_for_bound_ncm_after_reboot", return_value={"ncm": True}
        ), mock.patch.object(
            self.d1.legacy, "rebind_host_ncm_for_bound_identity", return_value={"ok": True}
        ), mock.patch.object(
            self.d1.legacy, "validate_post_reboot_ncm_identity"
        ), mock.patch.object(
            self.d1.persistent_observer,
            "observe",
            return_value={"proof": True},
        ), mock.patch.object(
            self.d1.base,
            "release_candidate_return_modemmanager_guard",
            return_value={"released": True},
        ), mock.patch.object(
            self.d1.legacy,
            "wait_for_native_return_after_bound_ncm",
        ) as native_return:
            result = self.d1._observe(
                SimpleNamespace(observer_key=Path("key")),
                argparse.Namespace(visible_confirmed="yes"),
                Path("transaction"),
                guard,
                {"binding": True},
                "yes",
            )
        self.assertTrue(result["proof"])
        native_return.assert_not_called()

    def test_dispatch_writes_no_closed_record(self) -> None:
        writes: list[tuple[int, str]] = []
        with mock.patch.object(
            self.d1.legacy, "require_pre_reboot_observer_binding_current"
        ), mock.patch.object(
            self.d1, "require_status"
        ), mock.patch.object(
            self.d1, "_arm_reboot_once", return_value={"dispatch": True}
        ), mock.patch.object(
            self.d1,
            "_observe",
            return_value={
                "server": {"proof": True},
                "guard_release": {"released": True},
            },
        ), mock.patch.object(
            self.d1,
            "_write_record",
            side_effect=lambda _directory, index, action, _payload: writes.append(
                (index, action)
            ),
        ):
            guard = mock.Mock()
            guard.healthy.return_value = True
            self.d1._dispatch_and_observe(
                object(),
                argparse.Namespace(visible_confirmed="yes"),
                Path("transaction"),
                guard,
                {"binding": True},
                "a" * 64,
                "yes",
            )
        self.assertEqual(
            writes,
            [(2, "dispatch-result"), (3, "persistent-observation"), (4, "current-state")],
        )

    def test_userdata_probe_is_read_only_and_runtime_devt(self) -> None:
        script = self.d1._unmounted_script()
        self.assertIn("^PARTNAME=userdata$", script)
        self.assertIn("runtime", self.d1.f1.UFS_IDENTITY["devt_policy"])
        for forbidden in (" rm ", "reboot", "switch_root", " dd ", "mkfs", "mount -"):
            self.assertNotIn(forbidden, script)

    def test_userdata_probe_accepts_dynamic_exact_devt(self) -> None:
        record = {
            "command": ["placeholder"],
            "text": "A90H24_POST_PHYSICAL_RETURN devt=260:9 "
            "ufs_mount_count=0 userdata_write=0\n",
        }
        with mock.patch.object(self.d1.base, "run_f1_cmd", return_value=record), mock.patch.object(
            self.d1.base, "require_exact_f1_command_receipt", return_value=record
        ):
            value = self.d1._prove_userdata_unmounted(argparse.Namespace())
        self.assertEqual(value["device"], "260:9")
        self.assertEqual(value["devt_policy"], "runtime-resolved-same-session")

    def test_same_intent_probe_requires_exact_enable_latch_and_evidence_bytes(self) -> None:
        intent = "a" * 64
        enable = self.d1.hashlib.sha256(
            self.d1._expected_h24_state(intent, "armed-after-native-health")
        ).hexdigest()
        latch = self.d1.hashlib.sha256(
            self.d1._expected_h24_state(
                intent,
                "automatic-handoff-dispatched-no-replay",
            )
        ).hexdigest()
        evidence = self.d1.hashlib.sha256((intent + "\n").encode()).hexdigest()
        record = {
            "text": "A90H24_INTENT_BINDING "
            f"intent={intent} enable_sha256={enable} "
            f"latch_sha256={latch} evidence_sha256={evidence}\n"
        }
        with mock.patch.object(self.d1.base, "run_f1_cmd", return_value=record), mock.patch.object(
            self.d1.base, "require_exact_f1_command_receipt", return_value=record
        ):
            value = self.d1.require_same_intent_state(argparse.Namespace(), intent)
        self.assertTrue(value["proof"])
        self.assertEqual(value["intent_sha256"], intent)

    def test_same_intent_probe_rejects_foreign_latched_intent(self) -> None:
        current = "a" * 64
        foreign = "b" * 64
        record = {
            "text": "A90H24_INTENT_BINDING "
            f"intent={foreign} enable_sha256={'c' * 64} "
            f"latch_sha256={'d' * 64} evidence_sha256={'e' * 64}\n"
        }
        with mock.patch.object(self.d1.base, "run_f1_cmd", return_value=record), mock.patch.object(
            self.d1.base, "require_exact_f1_command_receipt", return_value=record
        ), self.assertRaisesRegex(self.d1.ContractError, "intent binding"):
            self.d1.require_same_intent_state(argparse.Namespace(), current)

    def test_native_fallback_attribution_is_exact_and_precedes_cleanup(self) -> None:
        before = "[1ms] init: old\n"
        after = before + (
            "[2ms] server-distro: D4 handoff stop stage=root-content "
            "rc=-1 errno=1 root_mounted=1 writable_mounted=0 "
            "evidence_bound=0 wifi_handoff_bound=0\n"
            "[3ms] server-distro: D4 handoff failure cleanup_clean=1 "
            "root_mounted=0 recovery_required=0 userdata_unchanged=1 "
            "userdata_write=0\n"
        )
        with mock.patch.object(
            self.d1,
            "_exact_log_text",
            side_effect=[before, after],
        ):
            value = self.d1.native_fallback_attribution({}, {})
        self.assertTrue(value["proof"])
        self.assertEqual(value["stage"], "root-content")
        self.assertEqual(value["rc"], -1)
        self.assertEqual(value["errno"], 1)
        self.assertTrue(value["incident_window_match"])
        self.assertTrue(value["cleanup_proof"])
        self.assertEqual(value["record_persistence"], "observed-a90-log-only")
        self.assertFalse(value["power_loss_durable_journal"])

    def test_native_fallback_compares_decoded_payload_not_protocol_envelope(self) -> None:
        before = "[1ms] init: old\n"
        appended = (
            "[2ms] server-distro: D4 handoff stop stage=root-content "
            "rc=-1 errno=1 root_mounted=1 writable_mounted=0 "
            "evidence_bound=0 wifi_handoff_bound=0\n"
            "[3ms] server-distro: D4 handoff failure cleanup_clean=1 "
            "root_mounted=0 recovery_required=0 userdata_unchanged=1 "
            "userdata_write=0\n"
        )
        opening = self._log_receipt(before, sequence="41")
        final = self._log_receipt(before + appended, sequence="47")
        value = self.d1.native_fallback_attribution(opening, final)
        self.assertTrue(value["proof"])
        self.assertEqual(value["stage"], "root-content")

    def test_native_fallback_rejects_malformed_semantic_duplicates(self) -> None:
        valid = (
            "[2ms] server-distro: D4 handoff stop stage=root-content "
            "rc=-1 errno=1 root_mounted=1 writable_mounted=0 "
            "evidence_bound=0 wifi_handoff_bound=0\n"
        )
        malformed = "[2ms] server-distro: D4 handoff stop rc=0 errno=0\n"
        cleanup = (
            "[3ms] server-distro: D4 handoff failure cleanup_clean=1 "
            "root_mounted=0 recovery_required=0 userdata_unchanged=1 "
            "userdata_write=0\n"
        )
        with mock.patch.object(
            self.d1,
            "_exact_log_text",
            side_effect=["", malformed + valid + cleanup],
        ), self.assertRaisesRegex(self.d1.ContractError, "not unique"):
            self.d1.native_fallback_attribution({}, {})

        malformed_cleanup = (
            "[3ms] server-distro: D4 handoff failure cleanup_clean=1\n"
        )
        with mock.patch.object(
            self.d1,
            "_exact_log_text",
            side_effect=["", valid + malformed_cleanup + cleanup],
        ), self.assertRaisesRegex(self.d1.ContractError, "not unique"):
            self.d1.native_fallback_attribution({}, {})

    def test_missing_diagnostic_is_no_proof_not_replay_authority(self) -> None:
        before = "[1ms] init: old\n"
        after = before + (
            "[3ms] server-distro: D4 handoff failure cleanup_clean=1 "
            "root_mounted=0 recovery_required=0 userdata_unchanged=1 "
            "userdata_write=0\n"
        )
        with mock.patch.object(
            self.d1,
            "_exact_log_text",
            side_effect=[before, after],
        ):
            value = self.d1.native_fallback_attribution({}, {})
        self.assertFalse(value["proof"])
        self.assertEqual(value["status"], "NO_PROOF_H24_FAILURE_ATTRIBUTION")
        self.assertTrue(value["cleanup_proof"])
        self.assertIn(
            self.d1._native_fallback_status(value, final=True),
            self.d1.NATIVE_FALLBACK_FINAL_STATUSES,
        )

    def test_duplicate_diagnostic_fails_closed(self) -> None:
        diagnostic = (
            "[2ms] server-distro: D4 handoff stop stage=root-content "
            "rc=-1 errno=1 root_mounted=1 writable_mounted=0 "
            "evidence_bound=0 wifi_handoff_bound=0\n"
        )
        cleanup = (
            "[3ms] server-distro: D4 handoff failure cleanup_clean=1 "
            "root_mounted=0 recovery_required=0 userdata_unchanged=1 "
            "userdata_write=0\n"
        )
        with mock.patch.object(
            self.d1,
            "_exact_log_text",
            side_effect=["", diagnostic + diagnostic + cleanup],
        ), self.assertRaisesRegex(self.d1.ContractError, "not unique"):
            self.d1.native_fallback_attribution({}, {})

    def test_native_fallback_rejects_replaced_log_history(self) -> None:
        before = "[10ms] init: opening-sentinel-A\n"
        after = (
            "[1ms] init: DIFFERENT-HISTORY-B\n"
            "[2ms] server-distro: D4 handoff stop stage=root-content "
            "rc=-1 errno=1 root_mounted=1 writable_mounted=0 "
            "evidence_bound=0 wifi_handoff_bound=0\n"
            "[3ms] server-distro: D4 handoff failure cleanup_clean=1 "
            "root_mounted=0 recovery_required=0 userdata_unchanged=1 "
            "userdata_write=0\n"
        )
        with mock.patch.object(
            self.d1,
            "_exact_log_text",
            side_effect=[before, after],
        ), self.assertRaisesRegex(self.d1.ContractError, "exact prefix"):
            self.d1.native_fallback_attribution({}, {})

    def test_native_fallback_rejects_cleanup_before_diagnostic(self) -> None:
        before = "[1ms] init: old\n"
        cleanup = (
            "[2ms] server-distro: D4 handoff failure cleanup_clean=1 "
            "root_mounted=0 recovery_required=0 userdata_unchanged=1 "
            "userdata_write=0\n"
        )
        diagnostic = (
            "[3ms] server-distro: D4 handoff stop stage=root-content "
            "rc=-1 errno=1 root_mounted=1 writable_mounted=0 "
            "evidence_bound=0 wifi_handoff_bound=0\n"
        )
        with mock.patch.object(
            self.d1,
            "_exact_log_text",
            side_effect=[before, before + cleanup + diagnostic],
        ), self.assertRaisesRegex(self.d1.ContractError, "facts changed"):
            self.d1.native_fallback_attribution({}, {})

    def test_recovery_pending_cleanup_fails_closed(self) -> None:
        diagnostic = (
            "[2ms] server-distro: D4 handoff stop stage=root-content "
            "rc=-1 errno=1 root_mounted=1 writable_mounted=0 "
            "evidence_bound=0 wifi_handoff_bound=0\n"
        )
        cleanup = (
            "[3ms] server-distro: D4 handoff failure cleanup_clean=0 "
            "root_mounted=1 recovery_required=1 userdata_unchanged=1 "
            "userdata_write=0\n"
        )
        with mock.patch.object(
            self.d1,
            "_exact_log_text",
            side_effect=["", diagnostic + cleanup],
        ), self.assertRaisesRegex(self.d1.ContractError, "recovery-pending"):
            self.d1.native_fallback_attribution({}, {})

    def test_native_fallback_finalizer_never_replays_arm_or_reboot(self) -> None:
        intent = "a" * 64
        records = [
            {"opening_log": {"command": ["logcat"]}},
            {},
            {},
            {},
            {
                "result_sha256": "b" * 64,
                "result": {
                    "device_safety_state": "HEALTH_PENDING_PERSISTENT_DEBIAN"
                },
            },
        ]
        writes: list[tuple[int, str]] = []
        attribution = {
            "proof": True,
            "stage": "persistent-hud",
            "incident_window_match": True,
            "cleanup_proof": True,
        }
        args = argparse.Namespace(
            operator_attended=True,
            transaction_dir=Path("transaction"),
        )
        with mock.patch.object(
            self.d1, "load_inputs", return_value=({}, mock.Mock(stage=object()), {})
        ), mock.patch.object(
            self.d1, "_require_transaction_dir", return_value=Path("transaction")
        ), mock.patch.object(
            self.d1, "_read_records", return_value=records
        ), mock.patch.object(
            self.d1, "_validate_records", return_value=intent
        ), mock.patch.object(
            self.d1.base.staging, "require_exact_bridge"
        ), mock.patch.object(
            self.d1,
            "require_status",
            return_value=({"record": True}, {"binding": 1, "enable": 1, "latch": 1}),
        ), mock.patch.object(
            self.d1,
            "require_same_intent_state",
            return_value={"proof": True, "intent_sha256": intent},
        ), mock.patch.object(
            self.d1.base, "verify_candidate_health", return_value={"healthy": True}
        ), mock.patch.object(
            self.d1.f1, "validate_candidate_native_health"
        ), mock.patch.object(
            self.d1, "_prove_userdata_unmounted", return_value={"proof": True}
        ), mock.patch.object(
            self.d1.base, "run_f1_cmd", return_value={"log": True}
        ), mock.patch.object(
            self.d1, "native_fallback_attribution", return_value=attribution
        ), mock.patch.object(
            self.d1,
            "_write_record",
            side_effect=lambda _directory, index, action, _payload: writes.append(
                (index, action)
            ),
        ), mock.patch.object(self.d1, "_arm_reboot_once") as replay:
            result = self.d1.finalize_native_fallback(args)
        replay.assert_not_called()
        self.assertEqual(writes, [(5, "final-health"), (6, "closed")])
        self.assertEqual(
            result["status"],
            "REFUTED_H24_POST_ROOT_FAILURE_ATTRIBUTED_NATIVE_FALLBACK_HEALTHY",
        )
        self.assertTrue(result["resident_healthy"])
        self.assertTrue(result["ordinal_closed"])
        self.assertFalse(result["candidate_replay"])

    def test_physical_return_confirmation_is_mandatory(self) -> None:
        for attended, confirmed in ((False, False), (True, False), (False, True)):
            args = argparse.Namespace(
                operator_attended=attended,
                physical_return_confirmed=confirmed,
            )
            with self.assertRaisesRegex(self.d1.ContractError, "attended confirmation"):
                self.d1.finalize_physical_return(args)

    def test_physical_return_from_intent_prefix_fills_evidence_without_replay(self) -> None:
        records: list[dict] = [
            {"opening": True},
            {"pre_reboot_binding": {"bound": True}},
        ]
        writes: list[tuple[int, str]] = []

        def write(_directory: Path, index: int, action: str, payload: dict) -> None:
            self.assertEqual(index, len(records))
            writes.append((index, action))
            records.append({"action": action, **payload})

        args = argparse.Namespace(
            operator_attended=True,
            physical_return_confirmed=True,
            transaction_dir=Path("transaction"),
        )
        with mock.patch.object(
            self.d1, "load_inputs", return_value=({}, mock.Mock(stage=object()), {})
        ), mock.patch.object(
            self.d1, "_require_transaction_dir", return_value=Path("transaction")
        ), mock.patch.object(
            self.d1, "_read_records", side_effect=lambda _directory: list(records)
        ), mock.patch.object(
            self.d1, "_validate_records", return_value="a" * 64
        ), mock.patch.object(
            self.d1.base.staging, "require_exact_bridge"
        ), mock.patch.object(
            self.d1,
            "require_status",
            return_value=({"record": True}, {"binding": 1, "enable": 1, "latch": 1}),
        ), mock.patch.object(
            self.d1.base, "verify_candidate_health", return_value={"healthy": True}
        ), mock.patch.object(
            self.d1.f1, "validate_candidate_native_health"
        ), mock.patch.object(
            self.d1, "_prove_userdata_unmounted", return_value={"proof": True}
        ), mock.patch.object(
            self.d1,
            "require_same_intent_state",
            return_value={"proof": True, "intent_sha256": "a" * 64},
        ), mock.patch.object(
            self.d1, "_write_record", side_effect=write
        ), mock.patch.object(
            self.d1, "_arm_reboot_once"
        ) as replay:
            result = self.d1.finalize_physical_return(args)
        replay.assert_not_called()
        self.assertEqual(
            writes,
            [
                (2, "dispatch-result"),
                (3, "persistent-observation"),
                (4, "current-state"),
                (5, "final-health"),
                (6, "closed"),
            ],
        )
        self.assertEqual(result["device_safety_state"], "RESIDENT_HEALTHY")
        self.assertFalse(result["live_server_proven"])
        self.assertEqual(result["physical_return_reboot_dispatch_count"], 0)
        self.assertTrue(result["inter_effect_health_barrier_satisfied"])
        self.assertFalse(result["new_device_effect_authority"])

    def test_six_record_physical_return_resume_only_appends_close(self) -> None:
        current = {"device_safety_state": "HEALTH_PENDING_PERSISTENT_DEBIAN"}
        final = {"status": "healthy"}
        records = [{}, {}, {}, {}, {"result": current}, {"result": final, "result_sha256": "a" * 64}]
        writes: list[tuple[int, str]] = []
        args = argparse.Namespace(
            operator_attended=True,
            physical_return_confirmed=True,
            transaction_dir=Path("transaction"),
        )
        with mock.patch.object(
            self.d1, "load_inputs", return_value=({}, object(), {})
        ), mock.patch.object(
            self.d1, "_require_transaction_dir", return_value=Path("transaction")
        ), mock.patch.object(
            self.d1, "_read_records", return_value=records
        ), mock.patch.object(
            self.d1, "_validate_records", return_value="b" * 64
        ), mock.patch.object(
            self.d1,
            "_write_record",
            side_effect=lambda _directory, index, action, _payload: writes.append(
                (index, action)
            ),
        ), mock.patch.object(
            self.d1.base, "verify_candidate_health"
        ) as device_contact:
            result = self.d1.finalize_physical_return(args)
        self.assertEqual(result, final)
        self.assertEqual(writes, [(6, "closed")])
        device_contact.assert_not_called()

    def test_reconcile_live_pending_uses_durable_state_without_native_contact(self) -> None:
        current = {
            "device_safety_state": "HEALTH_PENDING_PERSISTENT_DEBIAN",
            "ordinal_closed": False,
        }
        records = [{}, {}, {}, {}, {"result": current}]
        args = argparse.Namespace(transaction_dir=Path("transaction"))
        with mock.patch.object(
            self.d1, "load_inputs", return_value=({}, object(), {})
        ), mock.patch.object(
            self.d1, "_require_transaction_dir", return_value=Path("transaction")
        ), mock.patch.object(
            self.d1, "_read_records", return_value=records
        ), mock.patch.object(
            self.d1, "_validate_records"
        ), mock.patch.object(
            self.d1.base, "run_f1_cmd"
        ) as device_contact:
            value = self.d1.reconcile(args)
        self.assertEqual(
            value["terminal"], "PERSISTENT_DEBIAN_LIVE_HEALTH_PENDING_NO_REPLAY"
        )
        device_contact.assert_not_called()

    def test_cli_exposes_physical_return_not_automatic_return(self) -> None:
        options = self.d1.parser()._option_string_actions
        self.assertIn("--finalize-physical-return", options)
        self.assertIn("--finalize-native-fallback", options)
        self.assertIn("--physical-return-confirmed", options)
        self.assertNotIn("--finalize-return", options)


if __name__ == "__main__":
    unittest.main()
