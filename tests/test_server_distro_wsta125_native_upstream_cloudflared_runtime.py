from __future__ import annotations

import contextlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta125_native_upstream_cloudflared_runtime.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta125_native_upstream_cloudflared_runtime.py")


class ServerDistroWsta125NativeUpstreamCloudflaredRuntimeTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def args(self, root: Path, *extra: str):
        return runner.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "wsta125"),
            *extra,
        ])

    def live_args(self, root: Path, local_image: Path, cloudflared: Path):
        return self.args(
            root,
            "--local-image",
            str(local_image),
            "--local-image-sha256",
            runner.sha256_file(local_image),
            "--cloudflared",
            str(cloudflared),
            "--execute-native-upstream-runtime-live",
            "--allow-credentialed-wifi",
            "--allow-cloudflared-runtime-live",
            "--ack-credentialed-wifi",
            "--ack-public-exposure",
            "--ack-private-url-artifact",
            "--ack-runtime-cleanup",
            "--native-confirm-token",
            runner.wsta25.NATIVE_CONFIRM_TOKEN,
        )

    def test_default_invocation_is_inert_and_device_safe(self) -> None:
        with self.private_tmp() as tmp:
            result = runner.run(self.args(Path(tmp)))

        self.assertEqual(result["decision"], "wsta125-blocked-native-upstream-runtime-live-required")
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

    def test_explicit_live_gate_requires_native_and_runtime_acks(self) -> None:
        with self.private_tmp() as tmp:
            args = self.args(Path(tmp))
            self.assertEqual(
                runner.explicit_live_gate(args),
                (False, "wsta125-blocked-native-upstream-runtime-live-required"),
            )
            args.execute_native_upstream_runtime_live = True
            self.assertEqual(
                runner.explicit_live_gate(args),
                (False, "wsta125-blocked-credentialed-wifi-allow-required"),
            )
            args.allow_credentialed_wifi = True
            self.assertEqual(
                runner.explicit_live_gate(args),
                (False, "wsta125-blocked-cloudflared-runtime-live-allow-required"),
            )
            args.allow_cloudflared_runtime_live = True
            args.run_wsta28_precondition = True
            self.assertEqual(
                runner.explicit_live_gate(args),
                (False, "wsta125-blocked-native-reboot-allow-required"),
            )
            args.allow_native_reboot = True
            self.assertEqual(
                runner.explicit_live_gate(args),
                (False, "wsta125-blocked-credentialed-wifi-ack-required"),
            )
            args.ack_credentialed_wifi = True
            self.assertEqual(
                runner.explicit_live_gate(args),
                (False, "wsta125-blocked-public-exposure-ack-required"),
            )
            args.ack_public_exposure = True
            self.assertEqual(
                runner.explicit_live_gate(args),
                (False, "wsta125-blocked-private-url-artifact-ack-required"),
            )
            args.ack_private_url_artifact = True
            self.assertEqual(
                runner.explicit_live_gate(args),
                (False, "wsta125-blocked-runtime-cleanup-ack-required"),
            )
            args.ack_runtime_cleanup = True
            self.assertEqual(
                runner.explicit_live_gate(args),
                (False, "wsta125-blocked-native-confirm-token-required"),
            )
            args.native_confirm_token = runner.wsta25.NATIVE_CONFIRM_TOKEN
            self.assertEqual(runner.explicit_live_gate(args), (True, "ok"))

    def test_template_and_source_keep_wsta124_runtime_inside_native_upstream_session(self) -> None:
        template = runner.template()
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("--execute-native-upstream-runtime-live", template["command"])
        self.assertIn("--allow-credentialed-wifi", template["command"])
        self.assertIn("--allow-cloudflared-runtime-live", template["command"])
        self.assertIn("--ack-runtime-cleanup", template["command"])
        self.assertFalse(template["boot_flash"])
        self.assertFalse(template["public_url_value_logged"])
        self.assertIn("wsta24.stage_helper", source)
        self.assertIn('"wifi"', source)
        self.assertIn('"uplink-service"', source)
        self.assertIn('"start"', source)
        self.assertIn("wsta124.run_runtime_probe", source)
        self.assertIn("wsta124.cleanup_cloudflared_runtime", source)
        self.assertIn("wsta42.run_packet_filter", source)
        self.assertIn("wsta125-blocked-egress-route", source)
        self.assertIn("public_url_value_logged", source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())

    def test_public_summary_redacts_url_and_resolver_values(self) -> None:
        summary = runner.public_summary({
            "decision": runner.PASS_DECISION,
            "run_dir": "workspace/private/runs/x",
            "checks": {"secret_values_logged": 0},
            "resolver_sync": {
                "ready": True,
                "source": "host-resolver",
                "nameserver_count": 2,
                "host_fallback_attempted": True,
            },
            "egress_route_preflight": {
                "target_present": True,
                "route_ok": True,
                "target_redacted": True,
                "ready": True,
            },
            "cloudflared_runtime_profile": {
                "private_url_artifact": True,
                "public_url_value_logged": False,
                "secret_values_logged": 0,
            },
            "safety": {"public_url_value_logged": False},
        })
        text = json.dumps(summary, sort_keys=True)

        self.assertNotIn("https://", text)
        self.assertNotIn("trycloudflare", text)
        self.assertNotIn("nameserver ", text)
        self.assertFalse(summary["safety"]["public_url_value_logged"])

    def test_mock_live_path_holds_upstream_and_blocks_before_packet_filter_on_egress(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            local_image = root / "rootfs.img"
            local_image.write_bytes(b"rootfs")
            cloudflared = root / "cloudflared"
            cloudflared.write_bytes(b"cloudflared")
            args = self.live_args(root, local_image, cloudflared)
            cmdv1_commands: list[list[str]] = []

            def fake_cmdv1(_args, command, **_kwargs):
                cmdv1_commands.append(list(command))
                text = ""
                if command[:3] == ["wifi", "uplink-service", "start"]:
                    text = "wifi-uplink-service-start-pass"
                elif command[:3] == ["wifi", "uplink-service", "stop"]:
                    text = "wifi-uplink-service-stop-pass"
                elif command == ["selftest"]:
                    text = "selftest: pass=12 warn=1 fail=0"
                return {"text": text}

            packet_filter = mock.Mock(return_value={"parsed": {}, "returncode": 0})
            with contextlib.ExitStack() as stack:
                for patcher in (
                    mock.patch.object(runner.wsta42, "build_dpublic_helpers", return_value={"ok": True}),
                    mock.patch.object(runner.wsta42, "run_host", return_value={"returncode": 0}),
                    mock.patch.object(runner.wsta19, "try_cmdv1_retry", side_effect=fake_cmdv1),
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
                    mock.patch.object(runner.wsta24, "stage_helper", return_value={"staged": True}),
                    mock.patch.object(runner.wsta24, "run_helper", return_value={"parsed": {"ready": "1"}}),
                    mock.patch.object(runner.wsta25, "status_ready_for_confirmed_autoconnect", return_value=True),
                    mock.patch.object(runner.wsta25, "run_confirmed_helper", return_value={"parsed": {"ok": "1"}}),
                    mock.patch.object(runner.wsta42, "helper_confirmed_ok", return_value=True),
                    mock.patch.object(runner.wsta42, "native_default_route", return_value={
                        "default_route_dev": "wlan0",
                        "default_route_is_wlan0": True,
                    }),
                    mock.patch.object(runner.wsta124, "ensure_runtime_resolver", return_value={
                        "ready": True,
                        "nameserver_count": 1,
                    }),
                    mock.patch.object(runner.wsta124, "egress_route_preflight", return_value={
                        "target_present": True,
                        "route_ok": False,
                        "target_redacted": True,
                        "ready": False,
                    }),
                    mock.patch.object(runner.wsta42, "run_packet_filter", packet_filter),
                    mock.patch.object(runner.wsta24, "cleanup_helper", return_value={"cleaned": True}),
                    mock.patch.object(runner.wsta20, "cleanup_service_dir", return_value={"stdout": "cleaned"}),
                    mock.patch.object(runner.d2, "parse_cleanup", return_value={}),
                    mock.patch.object(runner.d2, "parse_postcheck", return_value={}),
                    mock.patch.object(runner.wsta94, "chroot_cleanup_ok", return_value=True),
                ):
                    stack.enter_context(patcher)
                result = runner.run(args)

        self.assertEqual(result["decision"], "wsta125-blocked-egress-route")
        self.assertTrue(result["checks"]["native_uplink_confirmed"])
        self.assertFalse(result["checks"]["egress_route_ready"])
        self.assertEqual(packet_filter.call_count, 0)
        self.assertIn(["wifi", "uplink-service", "start", result["service_dir_native"], "360000", "100"], cmdv1_commands)
        self.assertIn(["wifi", "uplink-service", "stop", result["service_dir_native"]], cmdv1_commands)

    def test_print_template_exits_without_live_work(self) -> None:
        with mock.patch.object(runner, "run", side_effect=AssertionError("unexpected run")):
            with mock.patch("builtins.print") as printed:
                rc = runner.main_with_args(["--print-template"])

        self.assertEqual(rc, 0)
        payload = printed.call_args.args[0]
        self.assertIn("WSTA125 native STA upstream", payload)
        self.assertIn("--ack-runtime-cleanup", payload)


if __name__ == "__main__":
    unittest.main()
