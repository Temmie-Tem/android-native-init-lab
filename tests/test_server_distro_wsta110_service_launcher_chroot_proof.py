from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta110_service_launcher_chroot_proof.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta110_service_launcher_chroot_proof.py")


class ServerDistroWsta110ServiceLauncherChrootProofTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def test_explicit_live_gate_is_fail_closed(self) -> None:
        args = SimpleNamespace(
            execute_service_launcher_chroot_live=False,
            allow_service_launcher_live=False,
        )
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta110-blocked-service-launcher-chroot-live-required"),
        )

        args.execute_service_launcher_chroot_live = True
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta110-blocked-service-launcher-live-allow-required"),
        )

        args.allow_service_launcher_live = True
        self.assertEqual(runner.explicit_live_gate(args), (True, "ok"))

    def test_default_run_is_device_inert(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta110"),
            ]))
            saved = json.loads((root / "wsta110" / runner.RESULT_NAME).read_text(encoding="utf-8"))

        self.assertEqual(result["decision"], "wsta110-blocked-service-launcher-chroot-live-required")
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
        ):
            self.assertFalse(result["safety"][key])

    def test_service_policy_payload_matches_wsta109_identities(self) -> None:
        payload = runner.service_policy_payload()

        self.assertTrue(payload["default_public_off"])
        self.assertEqual(payload["services"]["dpublic-smoke-httpd"]["user"], "a90www")
        self.assertEqual(payload["services"]["dpublic-smoke-httpd"]["uid"], 3901)
        self.assertEqual(payload["services"]["cloudflared-quick-tunnel"]["user"], "a90tunnel")
        self.assertEqual(payload["services"]["dpublic-hud"]["network_intent"], "no-network-intent-producer-only")
        self.assertEqual(payload["services"]["dpublic-smoke-httpd"]["ambient_capabilities"], [])
        self.assertEqual(payload["services"]["dpublic-smoke-httpd"]["bounding_capabilities"], [])
        self.assertIn("wsta-native-uplink-helper", payload["root_boundary_services"])
        self.assertFalse(payload["public_url_value_logged"])
        self.assertEqual(payload["secret_values_logged"], 0)

    def test_service_identity_stage_script_is_exact_and_conflict_checked(self) -> None:
        script = runner.service_identity_stage_script()

        self.assertIn("A90WSTA110_IDENTITY_STAGE_BEGIN", script)
        self.assertIn("A90WSTA110_ACCOUNT_CONFLICT", script)
        self.assertIn("a90www:x:3901:3901:A90 service a90www:/nonexistent:/usr/sbin/nologin", script)
        self.assertIn("a90tunnel:x:3902:3902:A90 service a90tunnel:/nonexistent:/usr/sbin/nologin", script)
        self.assertIn("a90admin:x:3903:3903:A90 service a90admin:/nonexistent:/usr/sbin/nologin", script)
        self.assertIn("a90hud:x:3904:3904:A90 service a90hud:/nonexistent:/usr/sbin/nologin", script)
        self.assertIn("service-hardening-launcher=/usr/local/bin/a90-service-launch", script)
        self.assertIn("service-hardening-public-default=off", script)
        self.assertIn("A90WSTA110_IDENTITY_STAGE_DONE", script)
        self.assertNotIn("ssid=", script.lower())
        self.assertNotIn("psk=", script.lower())

    def test_launcher_probe_script_checks_public_off_fail_closed_and_no_new_privs(self) -> None:
        script = runner.launcher_probe_script()

        self.assertIn("A90WSTA110_PROOF_BEGIN", script)
        self.assertIn("cloudflared-quick-enable", script)
        self.assertIn("A90WSTA110_PUBLIC_ENABLE_ABSENT=1", script)
        self.assertIn("mount -t proc proc /proc", script)
        self.assertIn("A90WSTA110_PROC_MOUNTED=1", script)
        self.assertIn("A90WSTA110_PROC_UNMOUNTED=1", script)
        self.assertIn("blocked-unknown-service", script)
        self.assertIn("blocked-command-required", script)
        self.assertIn("dpublic-smoke-httpd /bin/sh -c", script)
        self.assertIn("child_uid=$(id -u)", script)
        self.assertIn("child_group=$(id -gn)", script)
        self.assertIn("NoNewPrivs", script)
        self.assertIn("A90WSTA110_PROOF_DONE", script)
        self.assertNotIn("cloudflared tunnel", script)
        self.assertNotIn("ssid=", script.lower())
        self.assertNotIn("psk=", script.lower())

    def test_parse_launcher_probe_requires_runtime_identity_and_no_new_privs(self) -> None:
        stdout = "\n".join([
            "A90WSTA110_PROOF_BEGIN",
            "A90WSTA110_PROC_MOUNTED=1",
            "A90WSTA110_PUBLIC_ENABLE_ABSENT=1",
            "A90WSTA110_LAUNCHER_PRESENT=1",
            "A90WSTA110_POLICY_PRESENT=1",
            "A90WSTA110_SETPRIV_PRESENT=1",
            "a90_service_launcher_decision=blocked-unknown-service",
            "a90_service_launcher_decision=blocked-command-required",
            "A90WSTA110_UNKNOWN_BLOCKED=1",
            "A90WSTA110_COMMAND_REQUIRED_BLOCKED=1",
            "a90_service_launcher_decision=exec",
            "a90_service_launcher_service=dpublic-smoke-httpd",
            "a90_service_launcher_user=a90www",
            "a90_service_launcher_network_intent=bind-loopback-127.0.0.1:8080-only",
            "a90_service_launcher_no_new_privs=1",
            "A90WSTA110_CHILD_BEGIN",
            "child_uid=3901",
            "child_gid=3901",
            "child_user=a90www",
            "child_group=a90www",
            "child_no_new_privs=1",
            "A90WSTA110_CHILD_DONE",
            "A90WSTA110_PROC_UNMOUNTED=1",
            "A90WSTA110_PROOF_DONE",
        ])

        parsed = runner.parse_launcher_probe({"stdout": stdout})

        self.assertTrue(parsed["proc_mounted"])
        self.assertTrue(parsed["proc_unmounted"])
        self.assertTrue(parsed["public_enable_absent"])
        self.assertTrue(parsed["unknown_service_blocks"])
        self.assertTrue(parsed["command_required_blocks"])
        self.assertTrue(parsed["launcher_exec"])
        self.assertTrue(parsed["launcher_service"])
        self.assertTrue(parsed["launcher_user"])
        self.assertTrue(parsed["child_uid"])
        self.assertTrue(parsed["child_gid"])
        self.assertTrue(parsed["child_user"])
        self.assertTrue(parsed["child_group"])
        self.assertTrue(parsed["child_no_new_privs"])
        self.assertEqual(parsed["secret_values_logged"], 0)

        missing_privs = runner.parse_launcher_probe({"stdout": stdout.replace("child_no_new_privs=1", "")})
        self.assertFalse(missing_privs["child_no_new_privs"])

    def test_classify_requires_launcher_runtime_proofs(self) -> None:
        checks = {
            "explicit_live_gate": True,
            "local_image_present": True,
            "baseline_selftest_fail_zero": True,
            "native_stale_cleanup_ok": True,
            "remote_image_ready": True,
            "chroot_mount_ready": True,
            "dropbear_started": True,
            "debian_ssh_marker": True,
            "service_hardening_assets_staged": True,
            "public_default_off": True,
            "launcher_fail_closed_blocks": True,
            "launcher_exec_pass": True,
            "launcher_uid_gid_pass": True,
            "launcher_no_new_privs_pass": True,
            "chroot_cleanup_ok": True,
            "final_selftest_fail_zero": True,
        }
        self.assertEqual(runner.classify({"checks": checks}), runner.PASS_DECISION)

        for key, decision in (
            ("explicit_live_gate", "wsta110-blocked-explicit-live-gate"),
            ("service_hardening_assets_staged", "wsta110-blocked-service-hardening-stage"),
            ("public_default_off", "wsta110-blocked-public-default-off"),
            ("launcher_fail_closed_blocks", "wsta110-blocked-launcher-fail-closed"),
            ("launcher_exec_pass", "wsta110-blocked-launcher-exec"),
            ("launcher_uid_gid_pass", "wsta110-blocked-launcher-uid-gid"),
            ("launcher_no_new_privs_pass", "wsta110-blocked-launcher-no-new-privs"),
            ("chroot_cleanup_ok", "wsta110-blocked-chroot-cleanup"),
            ("final_selftest_fail_zero", "wsta110-blocked-final-selftest"),
        ):
            self.assertEqual(runner.classify({"checks": {**checks, key: False}}), decision)

    def test_service_probe_cleanup_unmounts_nested_proc_before_chroot_cleanup(self) -> None:
        script = runner.service_probe_cleanup_script("/remote/mnt")

        self.assertIn("A90WSTA110_SERVICE_PROBE_CLEANUP_BEGIN", script)
        self.assertIn("P=/remote/mnt/proc", script)
        self.assertIn('grep -q " $P " /proc/mounts', script)
        self.assertIn('umount "$P"', script)
        self.assertIn("A90WSTA110 proc_mount_absent=1", script)

    def test_write_remote_bytes_stages_with_requested_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            args = SimpleNamespace(ssh_port=2222, ssh_connect_timeout=1, device_ip="192.0.2.2")
            completed = SimpleNamespace(
                returncode=0,
                stdout=b"A90WSTA110_FILE_STAGED\n",
                stderr=b"",
            )
            with mock.patch.object(runner.subprocess, "run", return_value=completed) as run_call:
                record = runner.write_remote_bytes(
                    args,
                    run_dir,
                    "/usr/local/bin/a90-service-launch",
                    b"payload",
                    mode="0755",
                    timeout=5.0,
                )

        remote_script = run_call.call_args.args[0][-1]
        self.assertTrue(record["staged"])
        self.assertEqual(record["mode"], "0755")
        self.assertIn('TMP="${TARGET}.wsta110-tmp.$$"', remote_script)
        self.assertIn('/bin/cat > "$TMP"', remote_script)
        self.assertIn("/bin/chmod 0755", remote_script)
        self.assertIn('/bin/mv -f "$TMP" "$TARGET"', remote_script)

    def test_source_preserves_wsta_live_safety_boundaries(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn('"boot_flash": False', source)
        self.assertIn('"wifi_connect": False', source)
        self.assertIn('"public_tunnel": False', source)
        self.assertIn('"packet_filter_mutation": False', source)
        self.assertIn("prepare_remote_work_image", source)
        self.assertIn("wsta94_mount_script", source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("cloudflared tunnel", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())


if __name__ == "__main__":
    unittest.main()
