from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta149_dpublic_hud_intent_syscall_trace.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta149_dpublic_hud_intent_syscall_trace.py")


class ServerDistroWsta149DpublicHudIntentSyscallTraceTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def test_explicit_live_gate_requires_all_acks(self) -> None:
        args = SimpleNamespace(
            execute_hud_intent_syscall_trace_live=False,
            allow_hud_intent_trace_live=False,
            ack_private_trace_artifact=False,
            ack_runtime_cleanup=False,
        )
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta149-blocked-hud-intent-syscall-trace-live-required"),
        )

        args.execute_hud_intent_syscall_trace_live = True
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta149-blocked-hud-intent-trace-live-allow-required"),
        )

        args.allow_hud_intent_trace_live = True
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta149-blocked-private-trace-artifact-ack-required"),
        )

        args.ack_private_trace_artifact = True
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta149-blocked-runtime-cleanup-ack-required"),
        )

        args.ack_runtime_cleanup = True
        self.assertEqual(runner.explicit_live_gate(args), (True, "ok"))

    def test_default_run_is_device_inert(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta149"),
            ]))
            saved = json.loads((root / "wsta149" / runner.RESULT_NAME).read_text(encoding="utf-8"))

        self.assertEqual(result["decision"], "wsta149-blocked-hud-intent-syscall-trace-live-required")
        self.assertEqual(saved["decision"], result["decision"])
        for key in (
            "device_action",
            "boot_flash",
            "native_reboot",
            "wifi_connect",
            "dhcp",
            "public_tunnel",
            "public_smoke",
            "external_ping",
            "packet_filter_mutation",
            "userdata_touch",
            "switch_root",
            "drm_open",
            "kms_setcrtc",
        ):
            self.assertFalse(result["safety"][key])

    def test_trace_probe_script_targets_intent_producer_only(self) -> None:
        script = runner.trace_probe_script()

        self.assertIn("A90WSTA149_TRACE_BEGIN", script)
        self.assertIn("cloudflared-quick-enable", script)
        self.assertIn("A90WSTA149_PUBLIC_ENABLE_ABSENT=1", script)
        self.assertIn("command -v strace", script)
        self.assertIn("dpublic-hud", script)
        self.assertIn("a90-dpublic-hud-intent", script)
        self.assertIn("--output \"$INTENT\"", script)
        self.assertIn("/run/a90-dpublic/hud-intent.json", script)
        self.assertIn("A90WSTA149_IDENTITY_UID=", script)
        self.assertIn("A90WSTA149_IDENTITY_NO_NEW_PRIVS=", script)
        self.assertIn("A90WSTA149_INTENT_WRITTEN=1", script)
        self.assertIn("A90WSTA149_SYSCALL_HAS_ATOMIC_RENAME=1", script)
        self.assertIn("A90WSTA149_SYSCALL_NETWORK_ABSENT=1", script)
        self.assertIn("A90WSTA149_SYSCALL_IOCTL_ABSENT=1", script)
        self.assertIn("A90WSTA149_DRM_TRACE_ABSENT=1", script)
        self.assertIn("A90WSTA149_SYSCALL_LIST_BEGIN", script)
        self.assertIn("A90WSTA149_TRACE_DONE", script)
        self.assertNotIn("dpublic-hud-presenter present", script)
        self.assertNotIn("/dev/dri/card0", script)
        self.assertNotIn("SETCRTC", script)
        self.assertNotIn("iptables -A", script)
        self.assertNotIn("ssid=", script.lower())
        self.assertNotIn("psk=", script.lower())

    def test_parse_trace_probe_requires_intent_atomic_write_and_no_network_or_drm(self) -> None:
        stdout = "\n".join([
            "A90WSTA149_TRACE_BEGIN",
            "A90WSTA149_PROC_MOUNTED=1",
            "A90WSTA149_PUBLIC_ENABLE_ABSENT=1",
            "A90WSTA149_LAUNCHER_PRESENT=1",
            "A90WSTA149_POLICY_PRESENT=1",
            "A90WSTA149_HUD_INTENT_PRESENT=1",
            "A90WSTA149_SETPRIV_PRESENT=1",
            "A90WSTA149_STRACE_PRESENT=1",
            "A90WSTA149_RUN_DIR_READY=1",
            "A90WSTA149_IDENTITY_UID=3904",
            "A90WSTA149_IDENTITY_GID=3904",
            "A90WSTA149_IDENTITY_NO_NEW_PRIVS=1",
            "A90WSTA149_IDENTITY_CAP_EFF=0000000000000000",
            "A90WSTA149_TRACE_PROCESS_RC=0",
            "A90WSTA149_LAUNCHER_EXEC_LOGGED=1",
            "A90WSTA149_LAUNCHER_SERVICE_LOGGED=1",
            "A90WSTA149_INTENT_WRITTEN=1",
            "A90WSTA149_INTENT_FILE_NONEMPTY=1",
            "A90WSTA149_INTENT_SCHEMA_OK=1",
            "A90WSTA149_INTENT_SEQUENCE_OK=1",
            "A90WSTA149_INTENT_PUBLIC_OFF=1",
            "A90WSTA149_INTENT_FORBIDDEN_FIELDS_ABSENT=1",
            "A90WSTA149_TRACE_FILE_NONEMPTY=1",
            "A90WSTA149_SYSCALL_PROFILE_NONEMPTY=1",
            "A90WSTA149_SYSCALL_HAS_EXECVE=1",
            "A90WSTA149_SYSCALL_HAS_OPENAT=1",
            "A90WSTA149_SYSCALL_HAS_WRITE=1",
            "A90WSTA149_SYSCALL_HAS_FSYNC=1",
            "A90WSTA149_SYSCALL_HAS_CLOSE=1",
            "A90WSTA149_SYSCALL_HAS_ATOMIC_RENAME=1",
            "A90WSTA149_SYSCALL_NETWORK_ABSENT=1",
            "A90WSTA149_SYSCALL_IOCTL_ABSENT=1",
            "A90WSTA149_DRM_TRACE_ABSENT=1",
            "A90WSTA149_SYSCALL_LIST_BEGIN",
            "close",
            "execve",
            "fsync",
            "openat",
            "rename",
            "write",
            "A90WSTA149_SYSCALL_LIST_END",
            "A90WSTA149_PROC_UNMOUNTED=1",
            "A90WSTA149_TRACE_DONE",
        ])

        parsed = runner.parse_trace_probe({"stdout": stdout})

        self.assertTrue(parsed["proof_done"])
        self.assertTrue(parsed["public_enable_absent"])
        self.assertTrue(parsed["strace_present"])
        self.assertTrue(parsed["hud_intent_present"])
        self.assertTrue(parsed["identity_uid"])
        self.assertTrue(parsed["identity_gid"])
        self.assertTrue(parsed["identity_no_new_privs"])
        self.assertTrue(parsed["identity_cap_eff_zero"])
        self.assertTrue(parsed["intent_written"])
        self.assertTrue(parsed["intent_schema_ok"])
        self.assertTrue(parsed["intent_sequence_ok"])
        self.assertTrue(parsed["intent_forbidden_fields_absent"])
        self.assertTrue(parsed["core_syscalls_observed"])
        self.assertTrue(parsed["atomic_rename_observed"])
        self.assertTrue(parsed["network_syscalls_absent"])
        self.assertTrue(parsed["ioctl_syscall_absent"])
        self.assertTrue(parsed["drm_trace_absent"])
        self.assertEqual(parsed["syscall_names"], ["close", "execve", "fsync", "openat", "rename", "write"])

        with_socket = runner.parse_trace_probe({"stdout": stdout.replace("write\n", "write\nsocket\n")})
        self.assertFalse(with_socket["network_syscalls_absent"])

        with_ioctl = runner.parse_trace_probe({"stdout": stdout.replace("write\n", "write\nioctl\n")})
        self.assertFalse(with_ioctl["ioctl_syscall_absent"])

        missing_rename = runner.parse_trace_probe({"stdout": stdout.replace("rename\n", "")})
        self.assertFalse(missing_rename["atomic_rename_observed"])

    def test_syscall_profile_is_intent_only_and_default_off(self) -> None:
        parsed = {
            "public_enable_absent": True,
            "intent_public_off": True,
            "identity_no_new_privs": True,
            "identity_cap_eff_zero": True,
            "core_syscalls_observed": True,
            "atomic_rename_observed": True,
            "network_syscalls_absent": True,
            "ioctl_syscall_absent": True,
            "drm_trace_absent": True,
            "syscall_count": 6,
            "syscall_names": ["close", "execve", "fsync", "openat", "rename", "write"],
        }

        profile = runner.syscall_profile(parsed, {"all_saved": True})

        self.assertEqual(profile["schema"], "a90-wsta149-dpublic-hud-intent-syscall-profile-v1")
        self.assertEqual(profile["service"], "dpublic-hud")
        self.assertEqual(profile["scope"], "hud-intent-producer-only")
        self.assertTrue(profile["native_presenter_owner"])
        self.assertTrue(profile["public_default_off"])
        self.assertTrue(profile["no_new_privs"])
        self.assertTrue(profile["cap_eff_zero"])
        self.assertTrue(profile["atomic_rename_observed"])
        self.assertTrue(profile["network_syscalls_absent"])
        self.assertTrue(profile["ioctl_syscall_absent"])
        self.assertTrue(profile["drm_trace_absent"])
        self.assertEqual(profile["trace_artifacts"], {"all_saved": True})
        self.assertFalse(profile["public_url_value_logged"])
        self.assertEqual(profile["secret_values_logged"], 0)

    def test_build_and_stage_hud_intent_binary_are_scoped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary = root / "a90-dpublic-hud-intent"
            binary.write_bytes(b"arm64-intent")
            args = SimpleNamespace(ssh_timeout=3.0)
            with mock.patch.object(
                runner.wsta42,
                "ssh_write_file",
                return_value={"staged": True, "returncode": 0},
            ) as write_file:
                record = runner.stage_hud_intent_binary(args, root, binary)

        write_file.assert_called_once()
        self.assertEqual(write_file.call_args.args[2], binary)
        self.assertEqual(write_file.call_args.args[3], runner.REMOTE_HUD_INTENT)
        self.assertTrue(record["staged"])
        self.assertEqual(record["service"], "dpublic-hud")
        self.assertEqual(record["secret_values_logged"], 0)

    def test_classify_requires_trace_artifacts_and_final_health(self) -> None:
        checks = {
            "explicit_live_gate": True,
            "local_image_present": True,
            "local_image_sha_ok": True,
            "hud_intent_build_ok": True,
            "baseline_selftest_fail_zero": True,
            "native_stale_cleanup_ok": True,
            "remote_image_ready": True,
            "chroot_mount_ready": True,
            "dropbear_started": True,
            "debian_ssh_marker": True,
            "service_hardening_assets_staged": True,
            "hud_intent_staged": True,
            "hud_split_marker_staged": True,
            "trace_probe_completed": True,
            "public_default_off": True,
            "strace_present": True,
            "hud_intent_present": True,
            "service_identity_ok": True,
            "launcher_exec_logged": True,
            "intent_written": True,
            "intent_schema_ok": True,
            "trace_file_nonempty": True,
            "syscall_profile_nonempty": True,
            "syscall_core_observed": True,
            "atomic_rename_observed": True,
            "network_syscalls_absent": True,
            "drm_syscalls_absent": True,
            "trace_artifact_saved": True,
            "chroot_cleanup_ok": True,
            "final_selftest_fail_zero": True,
        }
        self.assertEqual(runner.classify({"checks": checks}), runner.PASS_DECISION)

        for key, decision in (
            ("explicit_live_gate", "wsta149-blocked-explicit-live-gate"),
            ("hud_intent_build_ok", "wsta149-blocked-hud-intent-build"),
            ("trace_probe_completed", "wsta149-blocked-trace-timeout"),
            ("service_identity_ok", "wsta149-blocked-service-identity"),
            ("atomic_rename_observed", "wsta149-blocked-atomic-rename-missing"),
            ("network_syscalls_absent", "wsta149-blocked-network-syscall-present"),
            ("drm_syscalls_absent", "wsta149-blocked-drm-syscall-present"),
            ("trace_artifact_saved", "wsta149-blocked-trace-artifact-save"),
            ("final_selftest_fail_zero", "wsta149-blocked-final-selftest"),
        ):
            self.assertEqual(runner.classify({"checks": {**checks, key: False}}), decision)

    def test_source_preserves_no_flash_no_drm_boundaries(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("--execute-hud-intent-syscall-trace-live", source)
        self.assertIn("--allow-hud-intent-trace-live", source)
        self.assertIn("--ack-private-trace-artifact", source)
        self.assertIn("--ack-runtime-cleanup", source)
        self.assertIn('"boot_flash": False', source)
        self.assertIn('"native_reboot": False', source)
        self.assertIn('"public_tunnel": False', source)
        self.assertIn('"packet_filter_mutation": False', source)
        self.assertIn('"drm_open": False', source)
        self.assertIn('"kms_setcrtc": False', source)
        self.assertIn("stage_service_hardening_assets", source)
        self.assertIn("stage_hud_intent_binary", source)
        self.assertIn("a90-dpublic-hud-intent", source)
        self.assertIn("wsta94_mount_script", source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("iptables -A", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())


if __name__ == "__main__":
    unittest.main()
