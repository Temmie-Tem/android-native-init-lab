"""Regression tests for build_native_init_boot_v2186_wifi_ui_polish."""

from __future__ import annotations

import json
import tempfile
import types
import unittest
from pathlib import Path

from _loader import load_revalidation


v2186 = load_revalidation("build_native_init_boot_v2186_wifi_ui_polish")


def nested_namespace(*names, leaf):
    current = leaf
    for name in reversed(names):
        current = types.SimpleNamespace(**{name: current})
    return current


def fake_base_args():
    return [
        "--cycle",
        "OLD",
        "--decision",
        "old-decision",
        "--cycle-label",
        "old-label",
        "--init-version",
        "0.0.0",
        "--init-build",
        "old-build",
        "--out-dir",
        "old-out",
        "--init-binary",
        "old-init",
        "--helper-binary",
        "old-helper",
        "--ramdisk-cpio",
        "old-ramdisk",
        "--boot-image",
        "old-boot",
        "--wifi-test-klog-prefix",
        "OLD",
        "--wifi-test-disable",
        "old-disable",
        "--wifi-test-log",
        "old-log",
        "--wifi-test-summary",
        "old-summary",
        "--wifi-test-helper-result",
        "old-helper-result",
        "--wifi-test-pid",
        "old-pid",
        "--wifi-test-watcher-pid",
        "old-watcher",
        "--wifi-test-property-root",
        "old-prop",
    ]


class BuildWrapperConfiguration(unittest.TestCase):
    def test_configure_base_rewrites_v2182_axes_for_wifi_ui_polish_candidate(self) -> None:
        old_v2182 = v2186.v2182
        fake_base = types.SimpleNamespace(
            DEFAULT_ARGS=fake_base_args(),
            base=types.SimpleNamespace(EXTRA_INIT_FLAGS=[]),
        )

        def set_arg(args, key, value):
            index = args.index(key)
            args[index + 1] = value

        v726 = types.SimpleNamespace(set_arg=set_arg)
        chain = nested_namespace("v2178", "v2176", "v2174", "v2169", "v726", leaf=v726)
        fake_v2182 = types.SimpleNamespace(
            base_module=lambda: fake_base,
            configure_base=lambda: setattr(fake_v2182, "configured", True),
            EXTRA_INIT_FLAGS=("-DIGNORED-BY-WRAPPER=1",),
            REMOTE_PROPERTY_ROOT="/fake/property/root",
            EXPECTED_HELPER_MARKER="fake-marker",
            EXPECTED_HELPER_SHA256="fake-sha",
            v2178=chain.v2178,
        )
        v2186.v2182 = fake_v2182
        try:
            v2186.configure_base()
        finally:
            v2186.v2182 = old_v2182

        args = dict(zip(fake_base.DEFAULT_ARGS[0::2], fake_base.DEFAULT_ARGS[1::2]))
        self.assertTrue(fake_v2182.configured)
        self.assertEqual(fake_v2182.OUT_DIR, v2186.OUT_DIR)
        self.assertEqual(fake_v2182.REPORT_PATH, v2186.REPORT_PATH)
        self.assertEqual(fake_v2182.BOOT_IMAGE, v2186.BOOT_IMAGE)
        self.assertEqual(fake_v2182.INIT_BINARY, v2186.INIT_BINARY)
        self.assertEqual(fake_v2182.RAMDISK_CPIO, v2186.RAMDISK_CPIO)
        self.assertEqual(args["--cycle"], "V2186")
        self.assertEqual(args["--decision"], "v2186-wifi-ui-polish-source-build-pass")
        self.assertEqual(args["--cycle-label"], "v2186")
        self.assertEqual(args["--init-version"], "0.9.258")
        self.assertEqual(args["--init-build"], "v2186-wifi-ui-polish")
        self.assertEqual(args["--wifi-test-klog-prefix"], "A90v2186")
        self.assertEqual(args["--wifi-test-disable"], "/cache/native-init-wifi-test-boot-v2186.disable")
        self.assertEqual(args["--wifi-test-log"], "/cache/native-init-wifi-test-boot-v2186.log")
        self.assertEqual(
            args["--wifi-test-helper-result"],
            "/cache/native-init-wifi-test-boot-v2186-helper.result",
        )
        self.assertEqual(args["--wifi-test-property-root"], v2186.REMOTE_PROPERTY_ROOT)
        self.assertIn("a90_android_execns_probe_v427_wifi_ui_polish", args["--helper-binary"])
        self.assertEqual(fake_base.base.EXTRA_INIT_FLAGS, v2186.EXTRA_INIT_FLAGS)

    def test_render_report_records_wifi_status_polish_and_safety_scope(self) -> None:
        manifest = {
            "decision": "v2186-wifi-ui-polish-source-build-pass",
            "base_boot": "workspace/private/inputs/boot_images/base.img",
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v2186.img",
            "boot_sha256": "boot-sha",
            "init_version": "0.9.258",
            "init_build": "v2186-wifi-ui-polish",
            "helper_marker": "a90_android_execns_probe v427",
            "helper_sha256": "helper-sha",
            "wifi_test": {
                "helper_runtime_mode": "wifi-companion",
                "helper_timeout_sec": 75,
            },
        }

        report = v2186.render_report(manifest)

        self.assertIn("# Native Init V2186 Wi-Fi UI Polish Source Build", report)
        self.assertIn("Decision: `v2186-wifi-ui-polish-source-build-pass`", report)
        self.assertIn("WPA state, RSSI, link speed, and frequency", report)
        self.assertIn("PASS/RUN/OFF/FAIL labels and RF line", report)
        self.assertIn("V2185 network ping menu/CLI", report)
        self.assertIn("Wi-Fi status and profile screens are read-only", report)
        self.assertIn("does not connect, run DHCP, change routes, or read credentials", report)
        self.assertIn("No `/dev/subsys_esoc0`", report)

    def test_normalize_manifest_axes_promotes_v2186_ui_polish_metadata(self) -> None:
        old_out_dir = v2186.OUT_DIR
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                out_dir = Path(temp_dir)
                manifest_path = out_dir / "manifest.json"
                manifest_path.write_text(json.dumps({"decision": "pass"}), encoding="utf-8")
                v2186.OUT_DIR = out_dir

                v2186.normalize_manifest_axes()

                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        finally:
            v2186.OUT_DIR = old_out_dir

        self.assertEqual(manifest["decision"], "pass")
        self.assertEqual(manifest["candidate_tag"], "v2186-wifi-ui-polish")
        self.assertEqual(manifest["parent_baseline"], "v2185-network-ping-test")
        self.assertEqual(manifest["rollback_baseline"], "v2186-wifi-ui-polish")
        self.assertTrue(manifest["promoted_baseline"])
        self.assertEqual(manifest["version_axes"]["run_id"], "V2186")
        self.assertEqual(manifest["version_axes"]["helper_version"], "helper-v427")
        self.assertIn("Wi-Fi UI polish baseline", manifest["version_axes"]["note"])


if __name__ == "__main__":
    unittest.main()
