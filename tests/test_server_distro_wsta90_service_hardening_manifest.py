from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta90_service_hardening_manifest.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta90_service_hardening_manifest.py")


class ServerDistroWsta90ServiceHardeningManifestTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def readiness(self, *, seccomp_status: str = "ready-for-profile-source") -> dict:
        return {
            "decision": runner.wsta89.PASS_DECISION,
            "audit": {
                "controls": [
                    {"name": "seccomp-bpf-per-service", "status": seccomp_status},
                    {"name": "capability-drop-nonroot-services", "status": "needs-service-manifest"},
                    {"name": "packet-filter-default-drop", "status": "needs-netfilter-inventory"},
                ],
                "blocking_before_persistent_always_on": [
                    "capability-drop-nonroot-services",
                    "packet-filter-default-drop",
                ],
            },
        }

    def valid_args(self, root: Path, readiness: Path, *extra: str):
        return runner.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "wsta90"),
            "--emit-service-hardening-manifest",
            "--wsta89-hardening-readiness-json",
            str(readiness),
            *extra,
        ])

    def test_default_run_is_fail_closed_and_device_inert(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta90"),
            ]))

        self.assertEqual(result["decision"], "wsta90-blocked-emit-service-hardening-manifest-required")
        for key in (
            "device_action",
            "boot_flash",
            "native_reboot",
            "wifi_connect",
            "dhcp",
            "public_tunnel",
            "public_smoke",
            "userdata_touch",
            "switch_root",
        ):
            self.assertFalse(result["safety"][key])

    def test_valid_readiness_emits_service_manifest(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            readiness = root / "inputs" / "wsta89.json"
            self.write_json(readiness, self.readiness())
            result = runner.run(self.valid_args(root, readiness))
            saved = json.loads((root / "wsta90" / "wsta90_service_hardening_manifest.json").read_text(encoding="utf-8"))
            markdown = (root / "wsta90" / "wsta90_service_hardening_manifest.md").read_text(encoding="utf-8")

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(saved["decision"], runner.PASS_DECISION)
        manifest = result["manifest"]
        services = {item["name"]: item for item in manifest["services"]}
        self.assertEqual(len(services), 5)
        self.assertEqual(services["dpublic-smoke-httpd"]["target_user"], "a90www")
        self.assertEqual(services["dpublic-smoke-httpd"]["network_intent"], "bind-loopback-127.0.0.1:8080-only")
        self.assertEqual(services["cloudflared-quick-tunnel"]["target_user"], "a90tunnel")
        self.assertEqual(services["dropbear-admin-usb"]["status"], "needs-user-model")
        self.assertEqual(services["dpublic-hud"]["status"], "needs-device-node-policy")
        self.assertTrue(result["checks"]["all_services_no_new_privs"])
        self.assertTrue(result["checks"]["all_services_drop_ambient_caps"])
        self.assertTrue(manifest["global_policy"]["capability_drop_required"])
        self.assertTrue(manifest["global_policy"]["packet_filter_backend_required"])
        self.assertIn("WSTA Service Hardening Manifest", markdown)

    def test_nonpass_wsta89_readiness_blocks(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            readiness = root / "inputs" / "wsta89.json"
            bad = self.readiness()
            bad["decision"] = "blocked"
            self.write_json(readiness, bad)
            result = runner.run(self.valid_args(root, readiness))

        self.assertEqual(result["decision"], "wsta90-blocked-wsta89-readiness-not-pass")

    def test_seccomp_not_ready_blocks(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            readiness = root / "inputs" / "wsta89.json"
            self.write_json(readiness, self.readiness(seccomp_status="blocked-kernel-config"))
            result = runner.run(self.valid_args(root, readiness))

        self.assertEqual(result["decision"], "wsta90-blocked-seccomp-not-ready")

    def test_public_summary_markdown_and_template_are_redacted(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            readiness = root / "inputs" / "wsta89.json"
            self.write_json(readiness, self.readiness())
            result = runner.run(self.valid_args(root, readiness))
            summary_text = json.dumps(runner.public_summary(result), sort_keys=True)
            template_text = json.dumps(runner.template(), sort_keys=True)
            markdown = (root / "wsta90" / "wsta90_service_hardening_manifest.md").read_text(encoding="utf-8")
        tunnel_domain = "try" + "cloudflare.com"
        http_scheme = "http" + "://"
        https_scheme = "https" + "://"

        for text in (summary_text, template_text, markdown):
            self.assertNotIn(tunnel_domain, text.lower())
            self.assertNotIn("ssid=", text.lower())
            self.assertNotIn("psk=", text.lower())
            self.assertNotIn(http_scheme, text.lower())
            self.assertNotIn(https_scheme, text.lower())

    def test_print_template_exits_without_manifest(self) -> None:
        with mock.patch.object(runner, "run", side_effect=AssertionError("unexpected run")):
            with mock.patch("builtins.print") as printed:
                rc = runner.main_with_args(["--print-template"])

        self.assertEqual(rc, 0)
        payload = printed.call_args.args[0]
        self.assertIn("WSTA90 host-only", payload)
        self.assertIn("--emit-service-hardening-manifest", payload)

    def test_source_is_host_only_and_names_target_services(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("dpublic-smoke-httpd", source)
        self.assertIn("cloudflared-quick-tunnel", source)
        self.assertIn("dropbear-admin-usb", source)
        self.assertIn("dpublic-hud", source)
        self.assertIn("wsta-native-uplink-helper", source)
        self.assertIn('"boot_flash": False', source)
        self.assertIn('"public_url_value_logged": False', source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("a90ctl.py", source)
        self.assertNotIn("cloudflared tunnel", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())


if __name__ == "__main__":
    unittest.main()
