from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta94_packet_filter_live_gate.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta94_packet_filter_live_gate.py")


class ServerDistroWsta94PacketFilterLiveGateTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def test_explicit_live_gate_is_fail_closed(self) -> None:
        args = SimpleNamespace(
            execute_loopback_default_drop_live=False,
            allow_packet_filter_live=False,
            ack_packet_filter_mutation=False,
            force_restore_proof=False,
        )
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta94-blocked-loopback-default-drop-live-required"),
        )

        args.execute_loopback_default_drop_live = True
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta94-blocked-packet-filter-live-allow-required"),
        )

        args.allow_packet_filter_live = True
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta94-blocked-packet-filter-mutation-ack-required"),
        )

        args.ack_packet_filter_mutation = True
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta94-blocked-restore-proof-required"),
        )

        args.force_restore_proof = True
        self.assertEqual(runner.explicit_live_gate(args), (True, "ok"))

    def test_default_run_is_device_inert(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta94"),
            ]))
            saved = json.loads((root / "wsta94" / "wsta94_result.json").read_text(encoding="utf-8"))

        self.assertEqual(result["decision"], "wsta94-blocked-loopback-default-drop-live-required")
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
            "userdata_touch",
            "switch_root",
        ):
            self.assertFalse(result["safety"][key])
        self.assertFalse(result["safety"]["packet_filter_mutation"])

    def test_packet_filter_probe_script_saves_applies_restores_and_compares(self) -> None:
        script = runner.packet_filter_probe_script()

        self.assertIn("A90WSTA94_BEGIN", script)
        self.assertIn('"$IPT4" -S > "$RUN_DIR/before.probe.v4"', script)
        self.assertIn('rules_to_restore "$RUN_DIR/before.probe.v4" "$RUN_DIR/before.probe.restore.v4"', script)
        self.assertIn('"$PF" apply-loopback-default-drop', script)
        self.assertIn('"$RESTORE4" < "$RUN_DIR/before.probe.restore.v4"', script)
        self.assertIn("restore_probe_rules || fail restore 78", script)
        self.assertIn("cmp -s", script)
        self.assertNotIn('"$HTTP_BEFORE_RC" -eq 0 ] &&', script)
        self.assertNotIn('"$HTTP_AFTER_RC" -eq 0 ] &&', script)
        self.assertIn("A90WSTA94_RESTORE_EXACT_V4=1", script)
        self.assertIn("A90WSTA94_RESTORE_EXACT_V6=1", script)
        self.assertIn("A90WSTA94_PACKET_FILTER_PROBE_PASS", script)
        self.assertIn("trap cleanup EXIT INT TERM", script)
        self.assertNotIn("cloudflared tunnel", script)
        self.assertNotIn("ssid=", script.lower())
        self.assertNotIn("psk=", script.lower())

    def test_wsta94_mount_script_tolerates_busybox_losetup_attach_rc(self) -> None:
        script = runner.wsta94_mount_script("/remote/debian.img", "/remote/mnt", 2222)

        self.assertIn("A90D2_BEGIN", script)
        self.assertIn(f"LOOP={runner.WSTA94_LOOP}", script)
        self.assertIn(f"STATE={runner.WSTA94_LOOP_STATE}", script)
        self.assertIn(f'mknod "$LOOP" b "$LOOP_MAJOR" {runner.WSTA94_LOOP_MINOR}', script)
        self.assertIn("A90D2 stale_loop_detach_attempted=1", script)
        self.assertIn('losetup -d "$LOOP"', script)
        self.assertIn("LOSETUP_RC=0", script)
        self.assertIn('losetup "$LOOP" "$IMG" || LOSETUP_RC=$?', script)
        self.assertIn("A90D2 losetup_info_rc=$LOOP_INFO_RC", script)
        self.assertIn('if [ "$LOOP_INFO_RC" != "0" ]; then exit 32; fi', script)
        self.assertIn('/bin/busybox mount -t ext4 -o rw "$LOOP" "$MNT"', script)

    def test_wsta94_cleanup_and_postcheck_use_same_loop_as_mount(self) -> None:
        cleanup = runner.wsta94_cleanup_script("/remote/mnt")
        postcheck = runner.wsta94_postcheck_script("/remote/mnt")

        self.assertIn(f"L={runner.WSTA94_LOOP}", cleanup)
        self.assertIn(f"S={runner.WSTA94_LOOP_STATE}", cleanup)
        self.assertIn(f"LOOP={runner.WSTA94_LOOP}", postcheck)
        self.assertIn("losetup $L", cleanup)
        self.assertIn('losetup "$LOOP"', postcheck)

    def test_wsta94_start_dropbear_script_cleans_stale_files_and_logs_failure(self) -> None:
        public_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGcjjAE89XXoBkUgYnNOzgONvAOY8dQoRrr+w14MXmmI test"
        script = runner.wsta94_start_dropbear_script("/remote/mnt", public_key, "192.0.2.2", 2222)

        self.assertLess(len(script), 1900)
        self.assertIn("A90D2_START_BEGIN", script)
        self.assertIn("A90D2 authorized_keys=1", script)
        self.assertIn("A90D2 shadow_temp_key_only=1", script)
        self.assertIn('chown 0:0 "$M/root" "$M/root/.ssh" "$M/root/.ssh/authorized_keys"', script)
        self.assertIn('rm -f "$M$K" "$M$P" "$M$L"', script)
        self.assertIn('/usr/sbin/dropbear -F -E -r "$K"', script)
        self.assertIn('>"$M$L" 2>&1 &', script)
        self.assertIn("PID=$!", script)
        self.assertIn('kill -0 "$PID"', script)
        self.assertIn("A90D2 dropbear_listen=", script)
        self.assertIn("A90D2_DROPBEAR_STARTED", script)

    def test_parse_packet_filter_probe_requires_all_markers(self) -> None:
        stdout = "\n".join([
            "packet_filter_decision=packet-filter-preflight-pass",
            "A90WSTA94_SMOKE_STARTED=1",
            "A90WSTA94_LOOPBACK_BEFORE_OK=1",
            "packet_filter_decision=packet-filter-loopback-default-drop-applied",
            "A90WSTA94_POLICY_V4_INPUT_DROP=1",
            "A90WSTA94_POLICY_V4_FORWARD_DROP=1",
            "A90WSTA94_POLICY_V4_OUTPUT_ACCEPT=1",
            "A90WSTA94_RULE_V4_LOOPBACK_ACCEPT=1",
            "A90WSTA94_POLICY_V6_INPUT_DROP=1",
            "A90WSTA94_RULE_V6_LOOPBACK_ACCEPT=1",
            "A90WSTA94_LOOPBACK_AFTER_OK=1",
            "packet_filter_decision=packet-filter-restored",
            "A90WSTA94_RESTORE_EXACT_V4=1",
            "A90WSTA94_RESTORE_EXACT_V6=1",
            "A90WSTA94_PACKET_FILTER_PROBE_PASS",
        ])

        parsed = runner.parse_packet_filter_probe({"returncode": 0, "stdout": stdout})

        self.assertTrue(parsed["preflight_pass"])
        self.assertTrue(parsed["apply_pass"])
        self.assertTrue(parsed["restore_pass"])
        self.assertTrue(parsed["loopback_before_ok"])
        self.assertTrue(parsed["loopback_after_ok"])
        self.assertTrue(parsed["v4_input_drop"])
        self.assertTrue(parsed["v6_input_drop"])
        self.assertTrue(parsed["restore_exact_v4"])
        self.assertTrue(parsed["restore_exact_v6"])
        self.assertTrue(parsed["probe_pass"])
        self.assertEqual(parsed["secret_values_logged"], 0)

        missing_pass = runner.parse_packet_filter_probe({"returncode": 0, "stdout": stdout.replace("A90WSTA94_PACKET_FILTER_PROBE_PASS", "")})
        self.assertFalse(missing_pass["probe_pass"])

    def test_classify_requires_restore_cleanup_and_selftest(self) -> None:
        checks = {
            "explicit_live_gate": True,
            "local_image_present": True,
            "helpers_built": True,
            "remote_image_ready": True,
            "baseline_selftest_fail_zero": True,
            "native_stale_cleanup_ok": True,
            "chroot_mount_ready": True,
            "dropbear_started": True,
            "debian_ssh_marker": True,
            "loopback_binaries_staged": True,
            "packet_filter_helper_staged": True,
            "packet_filter_preflight_pass": True,
            "loopback_before_ok": True,
            "packet_filter_apply_pass": True,
            "packet_filter_default_drop_observed": True,
            "loopback_after_ok": True,
            "packet_filter_restore_pass": True,
            "packet_filter_restore_exact": True,
            "dpublic_cleanup_ok": True,
            "chroot_cleanup_ok": True,
            "final_selftest_fail_zero": True,
        }
        self.assertEqual(runner.classify({"checks": checks}), runner.PASS_DECISION)

        for key, decision in (
            ("explicit_live_gate", "wsta94-blocked-explicit-live-gate"),
            ("native_stale_cleanup_ok", "wsta94-blocked-native-stale-cleanup"),
            ("packet_filter_preflight_pass", "wsta94-blocked-packet-filter-preflight"),
            ("packet_filter_apply_pass", "wsta94-blocked-packet-filter-apply"),
            ("packet_filter_default_drop_observed", "wsta94-blocked-default-drop-observe"),
            ("loopback_after_ok", "wsta94-blocked-loopback-after-default-drop"),
            ("packet_filter_restore_pass", "wsta94-blocked-packet-filter-restore"),
            ("packet_filter_restore_exact", "wsta94-blocked-packet-filter-restore-mismatch"),
            ("chroot_cleanup_ok", "wsta94-blocked-chroot-cleanup"),
            ("final_selftest_fail_zero", "wsta94-blocked-final-selftest"),
        ):
            self.assertEqual(runner.classify({"checks": {**checks, key: False}}), decision)

    def test_chroot_cleanup_uses_postcheck_for_transient_loop_detach(self) -> None:
        result = {
            "cleanup_parse": {
                "done": True,
                "shadow_restored": True,
                "mount_cleanup_ok": True,
                "loop_cleanup_ok": False,
                "dropbear_cleanup_ok": False,
            },
            "postcheck_parse": {
                "mount_absent": True,
                "loop_node_absent": True,
                "dropbear_absent": True,
            },
        }

        self.assertTrue(runner.chroot_cleanup_ok(result))

    def test_stage_loopback_binaries_does_not_stage_public_tunnel_binary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / "a90-dpublic-smoke-httpd").write_text("smoke", encoding="utf-8")
            (run_dir / "a90-dpublic-http-get").write_text("get", encoding="utf-8")
            args = SimpleNamespace(ssh_timeout=5.0)

            with mock.patch.object(runner, "ssh_write_file_atomic", return_value={"staged": True}) as staged:
                record = runner.stage_loopback_binaries(args, run_dir)

        self.assertTrue(runner.stage_ok(record))
        remote_paths = [call.args[3] for call in staged.call_args_list]
        self.assertEqual(remote_paths, [runner.wsta42.REMOTE_SMOKE, runner.wsta42.REMOTE_HTTP_GET])
        self.assertNotIn(runner.REMOTE_PACKET_FILTER, remote_paths)

    def test_atomic_stage_writes_temp_then_renames_over_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            local = run_dir / "helper"
            local.write_text("payload", encoding="utf-8")
            args = SimpleNamespace(ssh_port=2222, ssh_connect_timeout=1, device_ip="192.0.2.2")

            completed = SimpleNamespace(
                returncode=0,
                stdout=b"A90WSTA94_FILE_STAGED\n",
                stderr=b"",
            )
            with mock.patch.object(runner.subprocess, "run", return_value=completed) as run_call:
                record = runner.ssh_write_file_atomic(
                    args,
                    run_dir,
                    local,
                    "/usr/local/bin/a90-test",
                    timeout=5.0,
                )

        remote_script = run_call.call_args.args[0][-1]
        self.assertTrue(record["staged"])
        self.assertTrue(record["atomic_replace"])
        self.assertIn('TMP="${TARGET}.wsta94-tmp.$$"', remote_script)
        self.assertIn('/bin/cat > "$TMP"', remote_script)
        self.assertIn('/bin/mv -f "$TMP" "$TARGET"', remote_script)
        self.assertNotIn("/bin/cat > /usr/local/bin/a90-test", remote_script)

    def test_native_stale_cleanup_kills_smoke_and_requires_unbound_loop(self) -> None:
        args = SimpleNamespace(cleanup_timeout=5.0, mountpoint="/remote/mnt")
        text = "\n".join([
            "A90WSTA94_NATIVE_STALE_CLEANUP_BEGIN",
            "A90WSTA94 stale_smoke_absent=1",
            "A90WSTA94 stale_dropbear_absent=1",
            "A90WSTA94 loop_info_rc=1",
            "A90WSTA94_NATIVE_STALE_CLEANUP_DONE",
        ])
        with mock.patch.object(runner.wsta19, "bridge_shell", return_value={"rc": 0, "text": text}) as bridge:
            record = runner.native_stale_cleanup(args)

        script = bridge.call_args.args[1]
        self.assertTrue(record["cleaned"])
        self.assertIn("pidof a90-dpublic-smoke-httpd", script)
        self.assertIn("pidof dropbear", script)
        self.assertIn("kill -9", script)
        self.assertIn("umount \"$MNT\"", script)
        self.assertIn(f"LOOP={runner.WSTA94_LOOP}", script)
        self.assertIn(f"mknod \"$LOOP\" b \"$LOOP_MAJOR\" {runner.WSTA94_LOOP_MINOR}", script)
        self.assertIn("losetup -d", script)

    def test_runner_exception_uses_run_id_directory(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            args = [
                "--run-id",
                "wsta94-explicit-run-id",
                "--execute-loopback-default-drop-live",
                "--allow-packet-filter-live",
                "--ack-packet-filter-mutation",
                "--force-restore-proof",
            ]
            with mock.patch.object(runner, "DEFAULT_RUN_BASE", root), mock.patch.object(runner, "run", side_effect=RuntimeError("boom")):
                rc = runner.main_with_args(args)

            self.assertEqual(rc, 1)
            self.assertTrue((root / "wsta94-explicit-run-id" / runner.RESULT_NAME).is_file())

    def test_source_has_no_public_or_credential_surface(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn('"public_tunnel": False', source)
        self.assertIn('"wifi_connect": False', source)
        self.assertIn('"packet_filter_restore_required": gate_ok', source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("cloudflared tunnel", source)
        self.assertNotIn("trycloudflare.com", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())


if __name__ == "__main__":
    unittest.main()
