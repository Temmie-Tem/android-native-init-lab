from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta89_hardening_readiness_audit.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta89_hardening_readiness_audit.py")


class ServerDistroWsta89HardeningReadinessAuditTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def d0_summary(self) -> dict:
        return {
            "decision": "server-distro-d0-device-live-read-only-inventory-pass",
            "read_only": True,
            "flash_performed": False,
            "filesystems": {"ext4": True, "overlay": False, "tmpfs": True},
            "host_staging": {
                "root_shadow_locked": True,
                "cloudflared_present": True,
                "image_present": True,
            },
            "kernel_config": {
                "CONFIG_SECCOMP": "y",
                "CONFIG_SECCOMP_FILTER": "y",
                "CONFIG_NET_NS": "y",
                "CONFIG_VETH": "n",
                "CONFIG_TUN": "y",
                "CONFIG_OVERLAY_FS": "n",
            },
            "tun_device_present": False,
        }

    def debian_eye_summary(self) -> dict:
        return {
            "decision": "debian-eye-hardware-inventory-live-pass",
            "read_only": True,
            "public_exposure": False,
            "network": {
                "ip_addr_values_redacted": True,
                "mac_values_redacted": True,
            },
            "vendor_userspace_absent": {
                "tinymix": True,
                "tinyplay": True,
                "wpa_supplicant": True,
            },
        }

    def valid_args(self, root: Path, d0: Path, debian: Path, *extra: str):
        return runner.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "wsta89"),
            "--audit-hardening-readiness",
            "--d0-public-summary-json",
            str(d0),
            "--debian-eye-public-summary-json",
            str(debian),
            *extra,
        ])

    def test_default_run_is_fail_closed_and_device_inert(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta89"),
            ]))

        self.assertEqual(result["decision"], "wsta89-blocked-audit-hardening-readiness-required")
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

    def test_valid_inventory_produces_readiness_audit(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            d0 = root / "inputs" / "d0.json"
            debian = root / "inputs" / "debian.json"
            self.write_json(d0, self.d0_summary())
            self.write_json(debian, self.debian_eye_summary())
            result = runner.run(self.valid_args(root, d0, debian))
            saved = json.loads((root / "wsta89" / "wsta89_hardening_readiness.json").read_text(encoding="utf-8"))
            markdown = (root / "wsta89" / "wsta89_hardening_readiness.md").read_text(encoding="utf-8")

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(saved["decision"], runner.PASS_DECISION)
        audit = result["audit"]
        controls = {item["name"]: item for item in audit["controls"]}
        self.assertEqual(controls["seccomp-bpf-per-service"]["status"], "ready-for-profile-source")
        self.assertEqual(controls["network-namespace-containment"]["status"], "partial-no-veth")
        self.assertEqual(controls["tun-node-tunnel-support"]["status"], "partial-node-missing")
        self.assertEqual(controls["apparmor-mac"]["status"], "needs-proof")
        self.assertEqual(controls["packet-filter-default-drop"]["status"], "needs-netfilter-inventory")
        self.assertIn("capability-drop-nonroot-services", audit["blocking_before_persistent_always_on"])
        self.assertIn("packet-filter-default-drop", audit["blocking_before_persistent_always_on"])
        self.assertTrue(result["checks"]["seccomp_filter_available"])
        self.assertIn("WSTA D-Harden Readiness Audit", markdown)

    def test_nonpass_d0_summary_blocks(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            d0 = root / "inputs" / "d0.json"
            debian = root / "inputs" / "debian.json"
            bad = self.d0_summary()
            bad["decision"] = "blocked"
            self.write_json(d0, bad)
            self.write_json(debian, self.debian_eye_summary())
            result = runner.run(self.valid_args(root, d0, debian))

        self.assertEqual(result["decision"], "wsta89-blocked-d0-summary-not-pass")

    def test_missing_d0_summary_blocks(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            debian = root / "inputs" / "debian.json"
            self.write_json(debian, self.debian_eye_summary())
            result = runner.run(self.valid_args(root, root / "inputs" / "missing.json", debian))

        self.assertEqual(result["decision"], "wsta89-blocked-d0-summary-missing")

    def test_public_summary_markdown_and_template_are_redacted(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            d0 = root / "inputs" / "d0.json"
            debian = root / "inputs" / "debian.json"
            self.write_json(d0, self.d0_summary())
            self.write_json(debian, self.debian_eye_summary())
            result = runner.run(self.valid_args(root, d0, debian))
            summary_text = json.dumps(runner.public_summary(result), sort_keys=True)
            template_text = json.dumps(runner.template(), sort_keys=True)
            markdown = (root / "wsta89" / "wsta89_hardening_readiness.md").read_text(encoding="utf-8")
        tunnel_domain = "try" + "cloudflare.com"
        http_scheme = "http" + "://"
        https_scheme = "https" + "://"

        for text in (summary_text, template_text, markdown):
            self.assertNotIn(tunnel_domain, text.lower())
            self.assertNotIn("ssid=", text.lower())
            self.assertNotIn("psk=", text.lower())
            self.assertNotIn(http_scheme, text.lower())
            self.assertNotIn(https_scheme, text.lower())

    def test_print_template_exits_without_audit(self) -> None:
        with mock.patch.object(runner, "run", side_effect=AssertionError("unexpected run")):
            with mock.patch("builtins.print") as printed:
                rc = runner.main_with_args(["--print-template"])

        self.assertEqual(rc, 0)
        payload = printed.call_args.args[0]
        self.assertIn("WSTA89 host-only", payload)
        self.assertIn("--audit-hardening-readiness", payload)

    def test_source_is_host_only_and_points_to_d_harden_surface(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("seccomp-bpf-per-service", source)
        self.assertIn("capability-drop-nonroot-services", source)
        self.assertIn("packet-filter-default-drop", source)
        self.assertIn("tier2-text-hard-disable", source)
        self.assertIn('"boot_flash": False', source)
        self.assertIn('"public_url_value_logged": False', source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("a90ctl.py", source)
        self.assertNotIn("cloudflared tunnel", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())


if __name__ == "__main__":
    unittest.main()
