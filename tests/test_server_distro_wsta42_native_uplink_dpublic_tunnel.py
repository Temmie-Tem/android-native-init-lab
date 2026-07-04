from __future__ import annotations

import socket
import tempfile
import urllib.error
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta42_native_uplink_dpublic_tunnel.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta42_native_uplink_dpublic_tunnel.py")


class ServerDistroWsta42NativeUplinkDpublicTunnelTests(unittest.TestCase):
    def test_explicit_live_gate_is_fail_closed(self) -> None:
        args = SimpleNamespace(
            allow_public_live=False,
            ack_credentialed_wifi=False,
            ack_public_exposure=False,
            native_confirm_token="",
            public_confirm_token="",
        )
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta42-blocked-explicit-public-live-allow-required"),
        )

        args.allow_public_live = True
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta42-blocked-credentialed-wifi-ack-required"),
        )

        args.ack_credentialed_wifi = True
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta42-blocked-public-exposure-ack-required"),
        )

        args.ack_public_exposure = True
        args.native_confirm_token = "wrong"
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta42-blocked-native-confirm-token-required"),
        )

        args.native_confirm_token = runner.wsta25.NATIVE_CONFIRM_TOKEN
        args.public_confirm_token = "wrong"
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta42-blocked-public-confirm-token-required"),
        )

        args.public_confirm_token = runner.PUBLIC_CONFIRM_TOKEN
        self.assertEqual(runner.explicit_live_gate(args), (True, "ok"))

    def test_classify_requires_uplink_tunnel_public_smoke_and_cleanup(self) -> None:
        checks = {
            "explicit_live_gate": True,
            "native_supported": True,
            "baseline_selftest_fail_zero": True,
            "final_selftest_fail_zero": True,
            "helpers_built": True,
            "debian_ssh_marker": True,
            "dpublic_binaries_staged": True,
            "packet_filter_preflight_ok": True,
            "use_native_uplink_profile": False,
            "native_uplink_profile_staged": True,
            "native_uplink_confirmed": True,
            "default_route_wlan0": True,
            "resolver_ready": True,
            "local_smoke_ok": True,
            "packet_filter_apply_ok": True,
            "tunnel_url_observed": True,
            "public_smoke_ok": True,
            "dpublic_cleanup_ok": True,
            "packet_filter_restore_ok": True,
            "native_uplink_profile_cleanup_ok": True,
            "chroot_cleanup_ok": True,
        }
        self.assertEqual(runner.classify({"checks": checks}), runner.PASS_DECISION)

        for key, decision in (
            ("explicit_live_gate", "wsta42-blocked-explicit-live-gate"),
            ("native_supported", "wsta42-blocked-supported-native-not-resident"),
            ("packet_filter_preflight_ok", "wsta42-blocked-packet-filter-preflight"),
            ("native_uplink_confirmed", "wsta42-blocked-native-uplink-confirmed"),
            ("default_route_wlan0", "wsta42-blocked-default-route-not-wlan0"),
            ("resolver_ready", "wsta42-blocked-resolver-sync"),
            ("local_smoke_ok", "wsta42-blocked-local-smoke"),
            ("packet_filter_apply_ok", "wsta42-blocked-packet-filter-apply"),
            ("tunnel_url_observed", "wsta42-blocked-tunnel-url"),
            ("public_smoke_ok", "wsta42-blocked-public-smoke"),
            ("dpublic_cleanup_ok", "wsta42-blocked-dpublic-cleanup"),
            ("packet_filter_restore_ok", "wsta42-blocked-packet-filter-restore"),
            ("chroot_cleanup_ok", "wsta42-blocked-chroot-cleanup"),
        ):
            variant = {"checks": {**checks, key: False}}
            self.assertEqual(runner.classify(variant), decision)

        profile_variant = {
            "checks": {
                **checks,
                "use_native_uplink_profile": True,
                "native_uplink_profile_staged": False,
            }
        }
        self.assertEqual(runner.classify(profile_variant), "wsta42-blocked-native-uplink-profile-stage")

        cleanup_variant = {
            "checks": {
                **checks,
                "use_native_uplink_profile": True,
                "native_uplink_profile_cleanup_ok": False,
            }
        }
        self.assertEqual(runner.classify(cleanup_variant), "wsta42-blocked-native-uplink-profile-cleanup")

    def test_fetch_public_url_writes_private_file_without_returning_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            args = SimpleNamespace(ssh_timeout=5.0)
            url = "https://example-test.trycloudflare.com\n"

            with mock.patch.object(runner, "ssh_exec", return_value={
                "returncode": 0,
                "stdout": url,
                "stderr": "",
            }):
                record = runner.fetch_public_url(args, run_dir)

            self.assertTrue(record["url_observed"])
            self.assertTrue(record["stdout_redacted"])
            self.assertNotIn("trycloudflare.com", repr(record))
            self.assertEqual((run_dir / "public-url.txt").read_text(encoding="utf-8"), url)

    def test_resolver_ready_requires_ready_marker_and_nameserver_count(self) -> None:
        self.assertTrue(runner.resolver_ready({"ready": True, "nameserver_count": 1}))
        self.assertFalse(runner.resolver_ready({"ready": False, "nameserver_count": 1}))
        self.assertFalse(runner.resolver_ready({"ready": True, "nameserver_count": 0}))

    def test_host_public_smoke_retries_dns_propagation_without_url_leak(self) -> None:
        class FakeResponse:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self, _limit):
                return (
                    b"A90_DPUBLIC_SMOKE_OK\n"
                    b"service=loopback-http\n"
                    b"public_exposure=outbound-tunnel-only\n"
                )

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / "public-url.txt").write_text("https://delayed.trycloudflare.com\n", encoding="utf-8")
            args = SimpleNamespace(
                public_smoke_attempts=3,
                public_curl_timeout_sec=1.0,
                public_smoke_retry_delay_sec=0.01,
            )
            with mock.patch.object(runner.urllib.request, "urlopen", side_effect=[
                urllib.error.URLError(socket.gaierror(-2, "not yet propagated")),
                urllib.error.URLError(socket.gaierror(-2, "not yet propagated")),
                FakeResponse(),
            ]), mock.patch.object(runner.time, "sleep") as sleep_mock:
                record = runner.host_public_smoke(args, run_dir)

        self.assertEqual(record["returncode"], 0)
        self.assertEqual(record["attempt"], 3)
        self.assertEqual(record["dns_error_count"], 2)
        self.assertEqual(record["last_error_reason_class"], "gaierror")
        self.assertEqual(len(record["attempts"]), 2)
        self.assertEqual(record["attempts"][0]["error_reason_class"], "gaierror")
        self.assertTrue(record["url_redacted"])
        self.assertNotIn("delayed.trycloudflare.com", repr(record))
        self.assertEqual(sleep_mock.call_count, 2)

    def test_host_public_smoke_failure_summarizes_dns_errors_without_url_leak(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / "public-url.txt").write_text("https://missing.trycloudflare.com\n", encoding="utf-8")
            args = SimpleNamespace(
                public_smoke_attempts=2,
                public_curl_timeout_sec=1.0,
                public_smoke_retry_delay_sec=0.01,
            )
            with mock.patch.object(
                runner.urllib.request,
                "urlopen",
                side_effect=urllib.error.URLError(socket.gaierror(-2, "not yet propagated")),
            ), mock.patch.object(runner.time, "sleep"):
                record = runner.host_public_smoke(args, run_dir)

        self.assertEqual(record["returncode"], 1)
        self.assertEqual(record["dns_error_count"], 2)
        self.assertEqual(record["last_error_reason_class"], "gaierror")
        self.assertTrue(record["url_redacted"])
        self.assertNotIn("missing.trycloudflare.com", repr(record))

    def test_start_smoke_parses_diagnostic_without_ssh_failure_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = SimpleNamespace(ssh_timeout=5.0)
            stdout = (
                "A90WSTA42_LOOPBACK_UP rc=0\n"
                "A90WSTA42_SMOKE_STARTED\n"
                "A90_DPUBLIC_SMOKE_OK\n"
                "A90WSTA42_SMOKE_DIAG pid_alive=1 listen=1 http_get_rc=0 log_bytes=48\n"
            )
            with mock.patch.object(runner, "ssh_exec", return_value={
                "returncode": 0,
                "stdout": stdout,
                "stderr": "",
            }):
                record = runner.start_smoke(args, Path(tmp))

            self.assertTrue(record["started"])
            self.assertTrue(record["local_smoke_ok"])
            self.assertTrue(record["pid_alive"])
            self.assertTrue(record["listen"])
            self.assertEqual(record["http_get_rc"], 0)
            self.assertEqual(record["loopback_up_rc"], 0)

    def test_packet_filter_output_parsing_and_gates(self) -> None:
        stdout = "\n".join([
            "packet_filter_helper_version=2",
            "packet_filter_backend=legacy-iptables",
            "packet_filter_apply_autostart=0",
            "packet_filter_secret_values_logged=0",
            "packet_filter_decision=packet-filter-preflight-pass",
        ])
        preflight = {"returncode": 0, "parsed": runner.parse_packet_filter_output(stdout)}
        self.assertTrue(runner.packet_filter_preflight_ok(preflight))

        apply = {"returncode": 0, "parsed": runner.parse_packet_filter_output("\n".join([
            "packet_filter_decision=packet-filter-loopback-default-drop-applied",
            "packet_filter_saved_before=1",
            "packet_filter_loopback_accept=1",
            "packet_filter_control_ssh_accept=1",
            "packet_filter_control_cidr=192.168.7.1/32",
            "packet_filter_control_ssh_port=2222",
            "packet_filter_input_default=DROP",
            "packet_filter_forward_default=DROP",
            "packet_filter_output_default=ACCEPT",
            "packet_filter_secret_values_logged=0",
        ]))}
        self.assertTrue(runner.packet_filter_apply_ok(apply))

        restore = {"returncode": 0, "parsed": runner.parse_packet_filter_output("\n".join([
            "packet_filter_decision=packet-filter-restored",
            "packet_filter_secret_values_logged=0",
        ]))}
        self.assertTrue(runner.packet_filter_restore_ok(restore))

    def test_local_image_sha_gate_uses_explicit_expected_sha(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = root / "packet-filter-ready.img"
            image.write_bytes(b"packet-filter-ready")
            expected_sha = runner.sha256_file(image)
            args = runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "run"),
                "--local-image",
                str(image),
                "--local-image-sha256",
                expected_sha,
                "--allow-public-live",
                "--ack-credentialed-wifi",
                "--ack-public-exposure",
                "--native-confirm-token",
                runner.wsta25.NATIVE_CONFIRM_TOKEN,
                "--public-confirm-token",
                runner.PUBLIC_CONFIRM_TOKEN,
            ])
            with mock.patch.object(runner, "build_dpublic_helpers", return_value={"ok": False}):
                result = runner.run(args)

        self.assertEqual(result["local_image_expected_sha256"], expected_sha)
        self.assertNotEqual(result["decision"], "wsta42-blocked-local-image-sha")
        self.assertEqual(result["decision"], "wsta42-blocked-helper-build")

    def test_profile_confirmed_requires_profile_and_native_client_success(self) -> None:
        parsed = {
            "native_wifi_uplink_client_decision": "native-wifi-uplink-client-pass",
            "native_wifi_uplink_client_requested_op": "autoconnect-confirmed",
            "native_wifi_uplink_client_secret_values_logged": "0",
            "version": runner.wsta24.UPLINK_SERVICE_VERSION,
            "op": "autoconnect",
            "owner": "native-init",
            "credentials": "private-config-gated",
            "connect": "confirm-gated",
            "dhcp_routing": "config-gated",
            "external_ping_execution": "0",
            "public_tunnel": "0",
            "secret_values_logged": "0",
            "rc": "0",
            "decision": "wifi-uplink-service-autoconnect-pass",
            "native_uplink_profile_decision": "native-uplink-profile-autoconnect-pass",
            "native_uplink_profile_public_default": "off",
            "native_uplink_profile_secret_values_logged": "0",
        }
        self.assertTrue(runner.profile_confirmed_ok({"parsed": parsed}))
        self.assertFalse(runner.profile_confirmed_ok({"parsed": {**parsed, "native_uplink_profile_public_default": "on"}}))

    def test_profile_confirmed_helper_uses_profile_not_direct_client(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = SimpleNamespace(
                native_confirm_token=runner.wsta25.NATIVE_CONFIRM_TOKEN,
                service_dir="/tmp/a90-service",
                ssh_connect_timeout=1,
            )

            with mock.patch.object(runner.wsta25, "ssh_exec_redacted_script", return_value={
                "returncode": 0,
                "stdout": (
                    "native_uplink_profile_decision=native-uplink-profile-autoconnect-pass\n"
                    "native_wifi_uplink_client_decision=native-wifi-uplink-client-pass\n"
                ),
                "stderr": "",
            }) as call:
                record = runner.run_profile_confirmed_helper(args, Path(tmp), timeout_sec=3)

            script = call.call_args.args[2]
            self.assertIn("/usr/local/bin/a90-dpublic-native-uplink-profile autoconnect-confirmed", script)
            self.assertIn("/etc/a90-dpublic/native-uplink-enable", script)
            self.assertTrue(record["profile_used"])

    def test_restore_work_image_from_clean_copies_on_device_and_verifies_sha(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            expected_sha = "a" * 64
            args = SimpleNamespace(
                remote_clean_image="/mnt/sdext/a90/runtime/debian.img.clean",
                remote_image="/mnt/sdext/a90/runtime/debian.img",
                setup_timeout=5.0,
            )
            bridge_text = (
                "A90WSTA42_IMAGE_RESTORE_BEGIN\n"
                "restore_clean_present=1\n"
                "A90WSTA42_IMAGE_RESTORE_DONE\n"
                f"{expected_sha}  /mnt/sdext/a90/runtime/debian.img\n"
            )

            with mock.patch.object(runner.wsta19, "bridge_shell", return_value={
                "rc": 0,
                "text": bridge_text,
            }) as bridge:
                record = runner.restore_work_image_from_clean(
                    args,
                    Path(tmp),
                    local_sha=expected_sha,
                )

            script = bridge.call_args.args[1]
            self.assertIn("A90WSTA42_IMAGE_RESTORE_BEGIN", script)
            self.assertIn('/bin/busybox cp "$CLEAN" "$TMP"', script)
            self.assertTrue(record["restored"])
            self.assertEqual(record["restored_sha256"], expected_sha)

    def test_prepare_remote_work_image_restores_drifted_work_from_clean_without_host_reupload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            local_sha = "b" * 64
            run_dir = Path(tmp)
            out_path = run_dir / "result.json"
            args = SimpleNamespace(
                remote_image="/mnt/sdext/a90/runtime/debian.img",
                remote_clean_image="/mnt/sdext/a90/runtime/debian.img.clean",
            )
            remote_calls: list[str] = []

            def remote_sha(_args, path):
                remote_calls.append(path)
                if path == args.remote_image and remote_calls.count(path) == 1:
                    return "drifted", {"path": path}
                return local_sha, {"path": path}

            with mock.patch.object(runner.wsta19, "remote_sha", side_effect=remote_sha), \
                 mock.patch.object(runner, "install_image_to_remote", side_effect=AssertionError("unexpected upload")), \
                 mock.patch.object(
                     runner,
                     "restore_work_image_from_clean",
                     return_value={"restored": True, "restored_sha256": local_sha},
                 ) as restore:
                result: dict = {}
                ok = runner.prepare_remote_work_image(args, result, out_path, run_dir, local_sha=local_sha)

            self.assertTrue(ok)
            self.assertEqual(remote_calls, [
                args.remote_image,
                args.remote_clean_image,
            ])
            self.assertEqual(restore.call_count, 1)
            self.assertTrue(result["remote_clean_image_enabled"])
            self.assertEqual(result["remote_sha_after_value"], local_sha)
            self.assertEqual(
                result["remote_sha_after"]["source"],
                "remote_work_restore_from_clean.restored_sha256",
            )

    def test_prepare_remote_work_image_uploads_clean_once_then_restores_work(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            local_sha = "c" * 64
            run_dir = Path(tmp)
            out_path = run_dir / "result.json"
            args = SimpleNamespace(
                remote_image="/mnt/sdext/a90/runtime/debian.img",
                remote_clean_image="/mnt/sdext/a90/runtime/debian.img.clean",
            )
            remote_values = iter([
                (None, {"path": args.remote_image}),
                (None, {"path": args.remote_clean_image}),
                (local_sha, {"path": args.remote_clean_image}),
            ])

            with mock.patch.object(runner.wsta19, "remote_sha", side_effect=lambda _args, _path: next(remote_values)), \
                 mock.patch.object(runner, "install_image_to_remote", return_value={"returncode": 0}) as install, \
                 mock.patch.object(
                     runner,
                     "restore_work_image_from_clean",
                     return_value={"restored": True, "restored_sha256": local_sha},
                 ) as restore:
                result: dict = {}
                ok = runner.prepare_remote_work_image(args, result, out_path, run_dir, local_sha=local_sha)

            self.assertTrue(ok)
            install.assert_called_once_with(args, local_sha, args.remote_clean_image)
            self.assertEqual(restore.call_count, 1)
            self.assertEqual(result["remote_clean_sha_after_value"], local_sha)
            self.assertEqual(
                result["remote_sha_after"]["source"],
                "remote_work_restore_from_clean.restored_sha256",
            )

    def test_prepare_remote_work_image_reuses_verified_clean_work_without_duplicate_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            local_sha = "e" * 64
            run_dir = Path(tmp)
            out_path = run_dir / "result.json"
            args = SimpleNamespace(
                remote_image="/mnt/sdext/a90/runtime/debian.img",
                remote_clean_image="/mnt/sdext/a90/runtime/debian.img.clean",
            )
            remote_calls: list[str] = []

            def remote_sha(_args, path):
                remote_calls.append(path)
                return local_sha, {"path": path}

            with mock.patch.object(runner.wsta19, "remote_sha", side_effect=remote_sha), \
                 mock.patch.object(runner, "install_image_to_remote", side_effect=AssertionError("unexpected upload")), \
                 mock.patch.object(runner, "restore_work_image_from_clean", side_effect=AssertionError("unexpected restore")):
                result: dict = {}
                ok = runner.prepare_remote_work_image(args, result, out_path, run_dir, local_sha=local_sha)

            self.assertTrue(ok)
            self.assertEqual(remote_calls, [args.remote_image, args.remote_clean_image])
            self.assertEqual(result["remote_clean_sha_after"]["source"], "remote_clean_sha_before")
            self.assertEqual(result["remote_clean_sha_after_value"], local_sha)
            self.assertEqual(result["remote_work_restore_from_clean"]["reason"], "work-image-already-clean")
            self.assertEqual(result["remote_sha_after"]["source"], "remote_sha_before")
            self.assertEqual(result["remote_sha_after_value"], local_sha)

    def test_prepare_remote_work_image_can_fall_back_to_legacy_direct_upload_when_clean_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            local_sha = "d" * 64
            run_dir = Path(tmp)
            out_path = run_dir / "result.json"
            args = SimpleNamespace(
                remote_image="/mnt/sdext/a90/runtime/debian.img",
                remote_clean_image="",
            )
            remote_values = iter([
                ("drifted", {"path": args.remote_image}),
                (local_sha, {"path": args.remote_image}),
            ])

            with mock.patch.object(runner.wsta19, "remote_sha", side_effect=lambda _args, _path: next(remote_values)), \
                 mock.patch.object(runner.wsta19, "install_image", return_value={"returncode": 0}) as install, \
                 mock.patch.object(runner, "restore_work_image_from_clean", side_effect=AssertionError("unexpected restore")):
                result: dict = {}
                ok = runner.prepare_remote_work_image(args, result, out_path, run_dir, local_sha=local_sha)

            self.assertTrue(ok)
            self.assertFalse(result["remote_clean_image_enabled"])
            self.assertIsNone(result["remote_clean_image"])
            self.assertEqual(install.call_count, 1)

    def test_finish_result_persists_ended_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "wsta42_result.json"
            result = {"decision": "example"}

            returned = runner.finish_result(out, result)

            self.assertIs(returned, result)
            self.assertRegex(result["ended_utc"], r"^20[0-9]{6}T[0-9]{6}Z$")
            text = out.read_text(encoding="utf-8")
            self.assertIn('"ended_utc"', text)
            self.assertIn('"decision": "example"', text)

    def test_runner_surface_is_fail_closed_and_url_redacted(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("--allow-public-live", source)
        self.assertIn("--ack-credentialed-wifi", source)
        self.assertIn("--ack-public-exposure", source)
        self.assertIn("--native-confirm-token", source)
        self.assertIn("--public-confirm-token", source)
        self.assertIn("--host-resolver-conf", source)
        self.assertIn("--use-native-uplink-profile", source)
        self.assertIn("--remote-clean-image", source)
        self.assertIn("a90_dpublic_packet_filter.sh", source)
        self.assertIn("packet_filter_restore_ok", source)
        self.assertIn("remote_work_restore_from_clean", source)
        self.assertIn("a90_dpublic_native_uplink_profile.sh", source)
        self.assertIn("wsta42-native-uplink-profile-confirmed-autoconnect", source)
        self.assertIn("content_redacted", source)
        self.assertIn("public_url_value_logged", source)
        self.assertIn("public-url.txt", source)
        self.assertIn("stdout_redacted", source)
        self.assertIn("finish_result(out_path, result)", source)
        self.assertIn('"ended_utc"', source)
        self.assertIn('"boot_flash": False', source)
        self.assertIn('"switch_root": False', source)
        self.assertIn('"userdata_touch": False', source)
        self.assertIn("explicit-public-live-gated", source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())


if __name__ == "__main__":
    unittest.main()
