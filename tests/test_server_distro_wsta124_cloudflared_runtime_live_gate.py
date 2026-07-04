from __future__ import annotations

import contextlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta124_cloudflared_runtime_live_gate.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta124_cloudflared_runtime_live_gate.py")


class ServerDistroWsta124CloudflaredRuntimeLiveGateTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def args(self, root: Path, *extra: str):
        return runner.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "wsta124"),
            *extra,
        ])

    def test_default_invocation_is_inert_and_device_safe(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            result = runner.run(self.args(root))

        self.assertEqual(result["decision"], "wsta124-blocked-cloudflared-runtime-live-required")
        self.assertFalse(result["safety"]["device_action"])
        self.assertFalse(result["safety"]["boot_flash"])
        self.assertFalse(result["safety"]["native_reboot"])
        self.assertFalse(result["safety"]["wifi_connect"])
        self.assertFalse(result["safety"]["dhcp"])
        self.assertFalse(result["safety"]["public_tunnel"])
        self.assertFalse(result["safety"]["packet_filter_mutation"])
        self.assertFalse(result["safety"]["switch_root"])
        self.assertFalse(result["safety"]["public_url_value_logged"])
        self.assertEqual(result["safety"]["secret_values_logged"], 0)

    def test_explicit_live_gate_requires_all_runtime_acks(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            args = self.args(root)
            self.assertEqual(
                runner.explicit_live_gate(args),
                (False, "wsta124-blocked-cloudflared-runtime-live-required"),
            )
            args.execute_cloudflared_runtime_live = True
            self.assertEqual(
                runner.explicit_live_gate(args),
                (False, "wsta124-blocked-cloudflared-runtime-live-allow-required"),
            )
            args.allow_cloudflared_runtime_live = True
            self.assertEqual(
                runner.explicit_live_gate(args),
                (False, "wsta124-blocked-public-exposure-ack-required"),
            )
            args.ack_public_exposure = True
            self.assertEqual(
                runner.explicit_live_gate(args),
                (False, "wsta124-blocked-private-url-artifact-ack-required"),
            )
            args.ack_private_url_artifact = True
            self.assertEqual(
                runner.explicit_live_gate(args),
                (False, "wsta124-blocked-runtime-cleanup-ack-required"),
            )
            args.ack_runtime_cleanup = True
            self.assertEqual(runner.explicit_live_gate(args), (True, "ok"))

    def test_runtime_probe_parser_requires_cloudflared_identity_and_syscalls(self) -> None:
        stdout = "\n".join([
            "A90WSTA124_RUNTIME_BEGIN",
            "A90WSTA124_PROC_MOUNTED=1",
            "A90WSTA124_PUBLIC_ENABLE_INITIAL_ABSENT=1",
            "A90WSTA124_PUBLIC_ENABLE_STAGED=1",
            "A90WSTA124_LAUNCHER_PRESENT=1",
            "A90WSTA124_CLOUDFLARED_PRESENT=1",
            "A90WSTA124_SMOKE_PRESENT=1",
            "A90WSTA124_HTTP_GET_PRESENT=1",
            "A90WSTA124_SETPRIV_PRESENT=1",
            "A90WSTA124_STRACE_PRESENT=1",
            "A90WSTA124_SMOKE_PID_FOUND=1",
            "A90WSTA124_LOOPBACK_GET_OK=1",
            "A90WSTA124_CLOUDFLARED_LAUNCH_STARTED=1",
            "A90WSTA124_CLOUDFLARED_PID_FOUND=1",
            "A90WSTA124_URL_ARTIFACT_PRIVATE=1",
            "A90WSTA124_CLOUDFLARED_UID=3902",
            "A90WSTA124_CLOUDFLARED_GID=3902",
            "A90WSTA124_CLOUDFLARED_NO_NEW_PRIVS=1",
            "A90WSTA124_CLOUDFLARED_CAP_EFF=0000000000000000",
            "A90WSTA124_COMMAND_HAS_TUNNEL=1",
            "A90WSTA124_COMMAND_NO_AUTOUPDATE=1",
            "A90WSTA124_COMMAND_ORIGIN=1",
            "A90WSTA124_COMMAND_METRICS=1",
            "A90WSTA124_CLOUDFLARED_ESTABLISHED_OUTBOUND=1",
            "A90WSTA124_CLOUDFLARED_OUTBOUND_ONLY=1",
            "A90WSTA124_TRACE_FILE_NONEMPTY=1",
            "A90WSTA124_SYSCALL_PROFILE_NONEMPTY=1",
            "A90WSTA124_SYSCALL_LIST_BEGIN",
            "connect",
            "execve",
            "socket",
            "A90WSTA124_SYSCALL_LIST_END",
            "A90WSTA124_PROC_UNMOUNTED=1",
            "A90WSTA124_RUNTIME_DONE",
        ])

        parsed = runner.parse_runtime_probe({"stdout": stdout})

        self.assertTrue(parsed["runtime_done"])
        self.assertTrue(parsed["uid_3902"])
        self.assertTrue(parsed["gid_3902"])
        self.assertTrue(parsed["no_new_privs"])
        self.assertTrue(parsed["cap_eff_zero"])
        self.assertTrue(parsed["outbound_only"])
        self.assertTrue(parsed["core_syscalls_observed"])
        self.assertEqual(parsed["syscall_names"], ["connect", "execve", "socket"])

    def test_runtime_profile_keeps_url_value_out_of_json(self) -> None:
        parsed = {
            "uid_3902": True,
            "gid_3902": True,
            "no_new_privs": True,
            "cap_eff_zero": True,
            "command_has_tunnel": True,
            "command_no_autoupdate": True,
            "command_origin": True,
            "command_metrics": True,
            "outbound_only": True,
            "established_outbound": True,
            "url_artifact_private": True,
            "core_syscalls_observed": True,
            "syscall_count": 3,
            "syscall_names": ["connect", "execve", "socket"],
        }
        profile = runner.runtime_profile(
            parsed,
            {"all_saved": True, "private_artifact": True},
            {"url_artifact_saved": True, "url_len": 37, "private_path": "workspace/private/x"},
        )
        text = json.dumps(profile, sort_keys=True)

        self.assertTrue(profile["uid_gid_proven"])
        self.assertTrue(profile["no_new_privs"])
        self.assertTrue(profile["cap_eff_zero"])
        self.assertTrue(profile["command_shape_proven"])
        self.assertTrue(profile["outbound_only"])
        self.assertTrue(profile["private_url_artifact"])
        self.assertFalse(profile["public_url_value_logged"])
        self.assertEqual(profile["secret_values_logged"], 0)
        self.assertNotIn("trycloudflare", text)
        self.assertNotIn("https://", text)

    def test_fetch_private_url_writes_private_file_but_redacts_record(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            args = self.args(root)
            run_dir = root / "wsta124"
            run_dir.mkdir(parents=True, exist_ok=True)
            url = "https://wsta124-proof." + runner.TRY_DOMAIN
            with mock.patch.object(runner.wsta42, "ssh_exec", return_value={
                "returncode": 0,
                "stdout": url + "\n",
                "stderr": "",
            }):
                record = runner.fetch_private_url(args, run_dir)
            private_path = Path(runner.REPO_ROOT) / record["private_path"]
            private_exists = private_path.is_file()
            private_value = private_path.read_text(encoding="utf-8").strip()

        self.assertTrue(record["url_artifact_saved"])
        self.assertTrue(record["stdout_redacted"])
        self.assertEqual(record["url_len"], len(url))
        self.assertFalse(record["public_url_value_logged"])
        self.assertEqual(record["secret_values_logged"], 0)
        self.assertTrue(private_exists)
        self.assertEqual(private_value, url)
        self.assertNotIn(url, json.dumps(record, sort_keys=True))

    def test_cleanup_record_requires_processes_and_sidecars_absent(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            args = self.args(root)
            with mock.patch.object(runner.wsta42, "ssh_exec", return_value={
                "returncode": 0,
                "stdout": "\n".join([
                    "A90WSTA124_RUNTIME_CLEANUP_BEGIN",
                    "A90WSTA124_CLOUDFLARED_ABSENT=1",
                    "A90WSTA124_SMOKE_ABSENT=1",
                    "A90WSTA124_ENABLE_ABSENT=1",
                    "A90WSTA124_URL_FILE_ABSENT=1",
                    "A90WSTA124_RUNTIME_CLEANUP_DONE",
                ]),
                "stderr": "",
            }):
                record = runner.cleanup_cloudflared_runtime(args, root / "wsta124")

        self.assertTrue(record["cleaned"])

    def test_template_and_source_are_gated_and_redacted(self) -> None:
        template = runner.template()
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("--execute-cloudflared-runtime-live", template["command"])
        self.assertIn("--ack-public-exposure", template["command"])
        self.assertEqual(template["public_tunnel"], "explicit-live-gated-short-lived")
        self.assertFalse(template["boot_flash"])
        self.assertFalse(template["public_url_value_logged"])
        self.assertIn("a90-service-launch", source)
        self.assertIn("cloudflared-quick-tunnel", source)
        self.assertIn("A90WSTA124_CLOUDFLARED_UID=3902", source)
        self.assertIn("A90WSTA124_CLOUDFLARED_CAP_EFF=0000000000000000", source)
        self.assertIn("A90WSTA124_SMOKE_PID_SOURCE=launch-pid", source)
        self.assertIn("A90WSTA124_RESOLVER_SYNC", source)
        self.assertIn("--host-resolver-conf", source)
        self.assertIn("wsta124-blocked-default-route-missing", source)
        self.assertIn("wsta124-blocked-resolver-sync", source)
        self.assertIn("wsta124-blocked-egress-route", source)
        self.assertIn("A90WSTA124_EGRESS_ROUTE", source)
        self.assertIn("target_redacted=1", source)
        self.assertIn('/bin/rm -f "$RUN_DIR/socket-posture"', source)
        self.assertIn("/bin/chmod 0666 \"$TRACE\"", source)
        self.assertIn("runtime_probe.sh", source)
        self.assertIn("write_remote_bytes", source)
        self.assertNotIn("pidof a90-dpublic-smoke-httpd", source)
        self.assertIn("public_url_value_logged", source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())

    def test_preflight_failure_skips_packet_filter_apply(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            local_image = root / "rootfs.img"
            local_image.write_bytes(b"rootfs")
            cloudflared = root / "cloudflared"
            cloudflared.write_bytes(b"cloudflared")
            args = self.args(
                root,
                "--local-image",
                str(local_image),
                "--local-image-sha256",
                runner.sha256_file(local_image),
                "--cloudflared",
                str(cloudflared),
                "--execute-cloudflared-runtime-live",
                "--allow-cloudflared-runtime-live",
                "--ack-public-exposure",
                "--ack-private-url-artifact",
                "--ack-runtime-cleanup",
            )
            packet_filter = mock.Mock(return_value={
                "parsed": {"packet_filter_decision": "packet-filter-tools-missing"},
                "returncode": 3,
            })
            with contextlib.ExitStack() as stack:
                for patcher in (
                    mock.patch.object(runner.wsta42, "build_dpublic_helpers", return_value={"ok": True}),
                    mock.patch.object(runner.wsta2, "run_host", return_value={"returncode": 0}),
                    mock.patch.object(
                        runner.wsta19,
                        "try_cmdv1_retry",
                        return_value={"text": "selftest: pass=12 warn=1 fail=0"},
                    ),
                    mock.patch.object(runner.wsta94, "native_stale_cleanup", return_value={"cleaned": True}),
                    mock.patch.object(runner.wsta42, "prepare_remote_work_image", return_value=True),
                    mock.patch.object(runner.d2, "generate_ssh_key", return_value={"ok": True}),
                    mock.patch.object(runner.d2, "read_public_key", return_value="ssh-ed25519 test"),
                    mock.patch.object(runner.wsta19, "bridge_shell", return_value={"text": ""}),
                    mock.patch.object(runner.d2, "parse_setup", side_effect=[
                        {"mount_ready": True, "mounted": True},
                        {"started": True, "authorized_keys": True, "shadow_temp_key_only": True},
                    ]),
                    mock.patch.object(runner.wsta19, "ssh_chroot_marker", return_value={"marker": {"marker": True}}),
                    mock.patch.object(runner.wsta110, "stage_service_hardening_assets", return_value={"ok": True}),
                    mock.patch.object(runner.wsta110, "stage_ok", return_value=True),
                    mock.patch.object(runner.wsta42, "stage_dpublic_binaries", return_value={"ok": True}),
                    mock.patch.object(runner.wsta42, "stage_binaries_ok", return_value=True),
                    mock.patch.object(runner.wsta42, "native_default_route", return_value={"default_route_dev": "wlan0"}),
                    mock.patch.object(
                        runner,
                        "ensure_runtime_resolver",
                        return_value={"ready": True, "nameserver_count": 1},
                    ),
                    mock.patch.object(runner, "egress_route_preflight", return_value={"ready": True}),
                    mock.patch.object(runner.wsta42, "run_packet_filter", packet_filter),
                    mock.patch.object(runner.d2, "parse_cleanup", return_value={}),
                    mock.patch.object(runner.d2, "parse_postcheck", return_value={}),
                    mock.patch.object(runner.wsta94, "chroot_cleanup_ok", return_value=True),
                ):
                    stack.enter_context(patcher)
                result = runner.run(args)

        self.assertEqual(result["decision"], "wsta124-blocked-packet-filter-preflight")
        self.assertEqual(packet_filter.call_args_list[0].args[2], "preflight")
        self.assertEqual(len(packet_filter.call_args_list), 1)
        self.assertEqual(result["packet_filter_apply"], {"skipped": True, "reason": "preflight-failed"})

    def test_print_template_exits_without_live_work(self) -> None:
        with mock.patch.object(runner, "run", side_effect=AssertionError("unexpected run")):
            with mock.patch("builtins.print") as printed:
                rc = runner.main_with_args(["--print-template"])

        self.assertEqual(rc, 0)
        payload = printed.call_args.args[0]
        self.assertIn("WSTA124 bounded", payload)
        self.assertIn("--ack-runtime-cleanup", payload)


if __name__ == "__main__":
    unittest.main()
