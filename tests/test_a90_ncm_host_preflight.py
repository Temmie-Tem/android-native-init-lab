from __future__ import annotations

import argparse
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


preflight = load_script("workspace/public/src/scripts/revalidation/a90_ncm_host_preflight.py")


class A90NcmHostPreflightTests(unittest.TestCase):
    def test_valid_ipv4_normalizes_and_rejects_bad_input(self) -> None:
        self.assertEqual(preflight.valid_ipv4("192.168.7.1"), "192.168.7.1")
        with self.assertRaises(argparse.ArgumentTypeError):
            preflight.valid_ipv4("999.1.1.1")

    def test_run_text_returns_stdout_stderr_and_exception_evidence(self) -> None:
        completed = mock.Mock(returncode=3, stdout="out", stderr="err")
        with mock.patch.object(preflight.subprocess, "run", return_value=completed) as run, \
                mock.patch.object(preflight, "repo_path", return_value=Path("/repo")):
            result = preflight.run_text(["cmd", "arg"], timeout=2.5)

        run.assert_called_once()
        self.assertEqual(result.command, "cmd arg")
        self.assertEqual(result.rc, 3)
        self.assertEqual(result.stdout, "out")
        self.assertEqual(result.stderr, "err")

        with mock.patch.object(preflight.subprocess, "run", side_effect=RuntimeError("boom")), \
                mock.patch.object(preflight, "repo_path", return_value=Path("/repo")):
            failed = preflight.run_text(["bad"])
        self.assertEqual(failed.rc, 127)
        self.assertIn("boom", failed.stderr)

    def test_read_text_and_service_state_handle_missing_and_systemctl_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "value"
            path.write_text("  hello\n", encoding="utf-8")
            self.assertEqual(preflight.read_text(path), "hello")
            self.assertEqual(preflight.read_text(Path(tmp) / "missing"), "")

        with mock.patch.object(preflight, "run_text", return_value=preflight.CommandResult("cmd", 0, "active\n", "")):
            self.assertEqual(preflight.service_state("NetworkManager"), "active")
        with mock.patch.object(preflight, "run_text", return_value=preflight.CommandResult("cmd", 3, "", "inactive\n")):
            self.assertEqual(preflight.service_state("missing"), "inactive")
        with mock.patch.object(preflight, "run_text", return_value=preflight.CommandResult("cmd", 3, "", "")):
            self.assertEqual(preflight.service_state("unknown"), "unknown")

    def test_ipv4_addrs_parses_ip_addr_output_and_ignores_bad_lines(self) -> None:
        output = (
            "2: enx0    inet 192.168.7.1/24 brd 192.168.7.255 scope global enx0\n"
            "3: wlan0    inet 10.0.0.2/24 brd 10.0.0.255 scope global wlan0\n"
            "4: bad line\n"
            "5: enx0    inet6 fe80::1/64 scope link\n"
        )
        with mock.patch.object(preflight, "run_text", return_value=preflight.CommandResult("ip", 0, output, "")):
            self.assertEqual(preflight.ipv4_addrs(), {"enx0": ["192.168.7.1/24"], "wlan0": ["10.0.0.2/24"]})
        with mock.patch.object(preflight, "run_text", return_value=preflight.CommandResult("ip", 1, "", "err")):
            self.assertEqual(preflight.ipv4_addrs(), {})

    def test_classify_interface_marks_samsung_cdc_ncm_candidate_and_cidr(self) -> None:
        attrs = {
            "idVendor": "04E8",
            "idProduct": "6861",
            "manufacturer": "Samsung",
            "product": "A90",
            "serial": "SER",
            "bInterfaceNumber": "02",
            "bInterfaceClass": "02",
            "bInterfaceSubClass": "0d",
        }

        def fake_read(path: Path) -> str:
            if path.name == "address":
                return "56:6c:b8:d2:17:e9"
            if path.name == "operstate":
                return "up"
            return ""

        with mock.patch.object(preflight, "usb_attrs", return_value=attrs), \
                mock.patch.object(preflight, "resolve_driver", return_value="cdc_ncm"), \
                mock.patch.object(preflight, "read_text", side_effect=fake_read):
            info = preflight.classify_interface("enx566c", "192.168.7.1/24", {"enx566c": ["192.168.7.1/24"]})

        self.assertTrue(info.candidate)
        self.assertTrue(info.has_expected_cidr)
        self.assertEqual(info.driver, "cdc_ncm")
        self.assertEqual(info.usb_vendor, "04E8")
        self.assertIn("driver=cdc_ncm", info.candidate_reason)
        self.assertIn("idVendor=04e8", info.candidate_reason)
        self.assertIn("ifname=enx*", info.candidate_reason)

    def test_render_templates_and_write_templates_are_bounded_to_store_path(self) -> None:
        with mock.patch.dict(os.environ, {"USER": "alice"}):
            templates = preflight.render_templates("192.168.7.1", 24)
        self.assertIn("/usr/sbin/ip addr replace 192.168.7.1/24 dev \"$IFACE\"", templates["a90-ncm-up.sh"])
        self.assertIn('ATTRS{idVendor}=="04e8"', templates["90-a90-ncm.rules"])
        self.assertIn("alice ALL=(root) NOPASSWD", templates["a90-ncm-sudoers"])

        with tempfile.TemporaryDirectory() as tmp:
            class Store:
                def __init__(self, root: Path) -> None:
                    self.root = root

                def path(self, name: str) -> Path:
                    return self.root / name

            written = preflight.write_templates(Store(Path(tmp)), "192.168.7.1", 24)
            written_paths = [Path(item) for item in written]
            self.assertEqual(len(written_paths), len(templates))
            self.assertTrue((Path(tmp) / "templates" / "a90-ncm-up.sh").exists())
            self.assertEqual(oct((Path(tmp) / "templates" / "a90-ncm-up.sh").stat().st_mode & 0o777), "0o700")

    def test_decide_covers_ready_partial_addr_only_needs_address_and_absent(self) -> None:
        candidate_ready = self._iface("enx0", candidate=True, has_expected_cidr=True)
        addr_only = self._iface("eth0", candidate=False, has_expected_cidr=True)
        candidate_no_addr = self._iface("enx1", candidate=True, has_expected_cidr=False)
        ok_ping = {"ok": True}
        bad_ping = {"ok": False}

        self.assertEqual(preflight.decide([candidate_ready], "192.168.7.1/24", ok_ping)[0], "a90-ncm-host-ready")
        self.assertEqual(preflight.decide([candidate_ready], "192.168.7.1/24", bad_ping)[0], "a90-ncm-host-address-present-ping-failed")
        self.assertEqual(preflight.decide([addr_only], "192.168.7.1/24", ok_ping)[0], "a90-ncm-host-ready-addr-only")
        self.assertEqual(preflight.decide([candidate_no_addr], "192.168.7.1/24", ok_ping)[0], "a90-ncm-host-needs-address")
        self.assertEqual(preflight.decide([], "192.168.7.1/24", ok_ping)[0], "a90-ncm-host-no-interface")

    def test_render_summary_includes_interface_services_templates_and_decision(self) -> None:
        manifest = {
            "generated_at": "2026-06-13T00:00:00+00:00",
            "decision": "a90-ncm-host-ready",
            "pass": True,
            "reason": "ready",
            "next_step": "use NCM deploy",
            "host_cidr": "192.168.7.1/24",
            "device_ip": "192.168.7.2",
            "ping": {"ok": True},
            "interfaces": [self._iface("enx0", candidate=True, has_expected_cidr=True).__dict__],
            "host_services": {"NetworkManager": "active"},
            "templates": ["/tmp/templates/a90-ncm-up.sh"],
        }
        rendered = preflight.render_summary(manifest)
        self.assertIn("# A90 NCM Host Preflight", rendered)
        self.assertIn("decision: `a90-ncm-host-ready`", rendered)
        self.assertIn("| enx0 | cdc_ncm | 04e8 |", rendered)
        self.assertIn("| NetworkManager | active |", rendered)
        self.assertIn("/tmp/templates/a90-ncm-up.sh", rendered)

    def test_build_manifest_no_ping_uses_no_mutation_contract_and_mocks_live_helpers(self) -> None:
        args = argparse.Namespace(host_ip="192.168.7.1", device_ip="192.168.7.2", prefix=24, no_ping=True)
        iface = self._iface("enx0", candidate=True, has_expected_cidr=True)
        store = mock.Mock()
        with mock.patch.object(preflight, "list_interfaces", return_value=[iface]) as list_interfaces, \
                mock.patch.object(preflight, "write_templates", return_value=["template-path"]) as write_templates, \
                mock.patch.object(preflight, "service_state", side_effect=["active", "inactive"]), \
                mock.patch.object(preflight, "collect_host_metadata", return_value={"git_head": "abc123"}), \
                mock.patch.object(preflight, "now_iso", return_value="now"):
            manifest = preflight.build_manifest(args, store)

        list_interfaces.assert_called_once_with("192.168.7.1/24")
        write_templates.assert_called_once_with(store, "192.168.7.1", 24)
        self.assertEqual(manifest["generated_at"], "now")
        self.assertEqual(manifest["decision"], "a90-ncm-host-address-present-ping-failed")
        self.assertFalse(manifest["pass"])
        self.assertEqual(manifest["ping"], {"command": "", "rc": 0, "ok": False, "stdout": "", "stderr": "skipped"})
        self.assertEqual(manifest["host_services"], {"NetworkManager": "active", "systemd-networkd": "inactive"})
        self.assertFalse(manifest["device_mutations"])
        self.assertFalse(manifest["host_mutations"])
        self.assertIn("changing NetworkManager profiles", manifest["blocked_actions"])

    @staticmethod
    def _iface(name: str, *, candidate: bool, has_expected_cidr: bool) -> preflight.InterfaceInfo:
        return preflight.InterfaceInfo(
            name=name,
            mac="56:6c:b8:d2:17:e9",
            operstate="up",
            driver="cdc_ncm",
            usb_vendor="04e8",
            usb_product="6861",
            usb_manufacturer="Samsung",
            usb_product_name="A90",
            usb_serial="SER",
            usb_interface_number="02",
            usb_interface_class="02",
            usb_interface_subclass="0d",
            ipv4=["192.168.7.1/24"] if has_expected_cidr else [],
            candidate=candidate,
            candidate_reason="driver=cdc_ncm",
            has_expected_cidr=has_expected_cidr,
        )


if __name__ == "__main__":
    unittest.main()
