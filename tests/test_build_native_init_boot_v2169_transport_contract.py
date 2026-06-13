"""Regression tests for build_native_init_boot_v2169_transport_contract."""

from __future__ import annotations

import json
import tempfile
import types
import unittest
from pathlib import Path

from _loader import load_revalidation


v2169 = load_revalidation("build_native_init_boot_v2169_transport_contract")


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
    def test_configure_base_rewrites_v726_axes_and_transport_contract_flags(self) -> None:
        old_v726 = v2169.v726
        fake_base = types.SimpleNamespace(
            DEFAULT_ARGS=fake_base_args(),
            base=types.SimpleNamespace(EXTRA_INIT_FLAGS=[]),
        )

        def set_arg(args, key, value):
            index = args.index(key)
            args[index + 1] = value

        fake_v726 = types.SimpleNamespace(
            base_module=lambda: fake_base,
            configure_base=lambda: setattr(fake_v726, "configured", True),
            EXPECTED_HELPER_MARKER="fake-marker",
            EXPECTED_HELPER_SHA256="fake-sha",
            EXTRA_INIT_FLAGS=("-DA90_WIFI_LIFECYCLE=1",),
            set_arg=set_arg,
        )
        v2169.v726 = fake_v726
        try:
            v2169.configure_base()
        finally:
            v2169.v726 = old_v726

        args = dict(zip(fake_base.DEFAULT_ARGS[0::2], fake_base.DEFAULT_ARGS[1::2]))
        self.assertTrue(fake_v726.configured)
        self.assertEqual(fake_v726.OUT_DIR, v2169.OUT_DIR)
        self.assertEqual(fake_v726.REPORT_PATH, v2169.REPORT_PATH)
        self.assertEqual(fake_v726.REMOTE_PROPERTY_ROOT, v2169.REMOTE_PROPERTY_ROOT)
        self.assertEqual(fake_v726.BOOT_IMAGE, v2169.BOOT_IMAGE)
        self.assertEqual(fake_v726.INIT_BINARY, v2169.INIT_BINARY)
        self.assertEqual(fake_v726.RAMDISK_CPIO, v2169.RAMDISK_CPIO)
        self.assertEqual(fake_v726.EXPECTED_HELPER_MARKER, v2169.EXPECTED_HELPER_MARKER)
        self.assertEqual(fake_v726.EXPECTED_HELPER_SHA256, v2169.EXPECTED_HELPER_SHA256)
        self.assertEqual(fake_v726.EXTRA_INIT_FLAGS, v2169.EXTRA_INIT_FLAGS)
        self.assertEqual(args["--cycle"], "V2169")
        self.assertEqual(args["--decision"], "v2169-transport-contract-source-build-pass")
        self.assertEqual(args["--cycle-label"], "v2169")
        self.assertEqual(args["--init-version"], "0.9.247")
        self.assertEqual(args["--init-build"], "v2169-transport-contract")
        self.assertEqual(args["--wifi-test-klog-prefix"], "A90v2169")
        self.assertEqual(args["--wifi-test-disable"], "/cache/native-init-wifi-test-boot-v2169.disable")
        self.assertEqual(args["--wifi-test-log"], "/cache/native-init-wifi-test-boot-v2169.log")
        self.assertEqual(
            args["--wifi-test-helper-result"],
            "/cache/native-init-wifi-test-boot-v2169-helper.result",
        )
        self.assertEqual(args["--wifi-test-property-root"], v2169.REMOTE_PROPERTY_ROOT)
        self.assertIn("a90_android_execns_probe_v427_transport_contract", args["--helper-binary"])
        self.assertEqual(fake_base.base.EXTRA_INIT_FLAGS, v2169.EXTRA_INIT_FLAGS)
        self.assertIn("-DA90_TRANSPORT_STATUS_CONTRACT=1", v2169.EXTRA_INIT_FLAGS)

    def test_ensure_legacy_mkbootimg_link_creates_and_skips_existing_link(self) -> None:
        old_mkbootimg_dir = v2169.MKBOOTIMG_DIR
        old_legacy_dir = v2169.LEGACY_MKBOOTIMG_DIR
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                target = root / "workspace" / "public" / "src" / "third_party" / "mkbootimg"
                target.mkdir(parents=True)
                legacy = root / "mkbootimg"
                v2169.MKBOOTIMG_DIR = target
                v2169.LEGACY_MKBOOTIMG_DIR = legacy

                self.assertTrue(v2169.ensure_legacy_mkbootimg_link())
                self.assertTrue(legacy.is_symlink())
                self.assertEqual(legacy.resolve(), target)
                self.assertFalse(v2169.ensure_legacy_mkbootimg_link())
        finally:
            v2169.MKBOOTIMG_DIR = old_mkbootimg_dir
            v2169.LEGACY_MKBOOTIMG_DIR = old_legacy_dir

    def test_render_report_records_transport_contract_and_safety_scope(self) -> None:
        manifest = {
            "decision": "v2169-transport-contract-source-build-pass",
            "base_boot": "workspace/private/inputs/boot_images/base.img",
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v2169.img",
            "boot_sha256": "boot-sha",
            "init_version": "0.9.247",
            "init_build": "v2169-transport-contract",
            "helper_marker": "a90_android_execns_probe v427",
            "helper_sha256": "helper-sha",
            "wifi_test": {
                "helper_runtime_mode": "wifi-companion",
                "helper_timeout_sec": 75,
            },
        }

        report = v2169.render_report(manifest)

        self.assertIn("# Native Init V2169 Transport Contract Source Build", report)
        self.assertIn("Decision: `v2169-transport-contract-source-build-pass`", report)
        self.assertIn("transport.contract=1", report)
        self.assertIn("serial/NCM/tcpctl/preferred/reason fields", report)
        self.assertIn("no Wi-Fi bring-up path change beyond status observability", report)
        self.assertIn("rollbackable to `workspace/private/inputs/boot_images/boot_linux_v726_wifi_lifecycle.img`", report)
        self.assertIn("No `/dev/subsys_esoc0`", report)

    def test_normalize_manifest_axes_records_promoted_transport_baseline(self) -> None:
        old_out_dir = v2169.OUT_DIR
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                out_dir = Path(temp_dir)
                manifest_path = out_dir / "manifest.json"
                manifest_path.write_text(json.dumps({"decision": "pass"}), encoding="utf-8")
                v2169.OUT_DIR = out_dir

                v2169.normalize_manifest_axes()

                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        finally:
            v2169.OUT_DIR = old_out_dir

        self.assertEqual(manifest["decision"], "pass")
        self.assertEqual(manifest["baseline_tag"], "v2169-transport-contract")
        self.assertEqual(manifest["version_axes"]["baseline_tag"], "v2169-transport-contract")
        self.assertEqual(manifest["version_axes"]["boot_init_parent"], "v726-wifi-lifecycle")
        self.assertEqual(manifest["version_axes"]["helper_version"], "helper-v427")
        self.assertEqual(manifest["version_axes"]["run_id"], "V2169")
        self.assertIn("transport status contract", manifest["version_axes"]["note"])


if __name__ == "__main__":
    unittest.main()
