"""Regression tests for build_native_init_boot_v726_wifi_lifecycle."""

from __future__ import annotations

import json
import tempfile
import types
import unittest
from pathlib import Path

from _loader import load_revalidation


builder = load_revalidation("build_native_init_boot_v726_wifi_lifecycle")


def fake_base_args() -> list[str]:
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


def namespace_chain(*names: str, leaf: object) -> object:
    current = leaf
    for name in reversed(names):
        current = types.SimpleNamespace(**{name: current})
    return current


def set_arg(args: list[str], key: str, value: str) -> None:
    index = args.index(key)
    args[index + 1] = value


def fake_v2168_module(fake_base, patched_bases=None):
    terminal = types.SimpleNamespace(set_arg=set_arg)
    helper_builder = types.SimpleNamespace(
        patch_helper_builder=lambda base: (patched_bases if patched_bases is not None else []).append(base)
    )
    prev2008 = types.SimpleNamespace(prev2006=terminal)
    prev2038 = types.SimpleNamespace(prev2008=prev2008, patch_helper_builder=helper_builder.patch_helper_builder)
    prev2058 = types.SimpleNamespace(prev2038=prev2038)
    prev2080 = types.SimpleNamespace(prev2058=prev2058)
    prev2082 = types.SimpleNamespace(prev2080=prev2080)
    prev2095 = types.SimpleNamespace(prev2082=prev2082)
    prev2097 = types.SimpleNamespace(prev2095=prev2095)
    prev2100 = types.SimpleNamespace(prev2097=prev2097)
    prev2102 = types.SimpleNamespace(prev2100=prev2100)
    prev2106 = types.SimpleNamespace(prev2102=prev2102)
    prev2108 = types.SimpleNamespace(prev2106=prev2106)
    prev2112 = types.SimpleNamespace(prev2108=prev2108)
    prev2120 = types.SimpleNamespace(prev2112=prev2112)
    prev2127 = types.SimpleNamespace(prev2120=prev2120)
    prev2129 = types.SimpleNamespace(prev2127=prev2127)
    prev2131 = types.SimpleNamespace(prev2129=prev2129)
    prev2133 = types.SimpleNamespace(prev2131=prev2131, EXTRA_INIT_FLAGS=())
    prev2135 = types.SimpleNamespace(prev2133=prev2133, EXTRA_INIT_FLAGS=())
    prev2137 = types.SimpleNamespace(prev2135=prev2135, EXTRA_INIT_FLAGS=())

    return types.SimpleNamespace(
        EXTRA_INIT_FLAGS=("-DA90_V2168_ROUTE=1",),
        base_module=lambda: fake_base,
        configure_base=lambda: setattr(fake_base, "configured_by_v2168", True),
        prev2137=prev2137,
        OUT_DIR=None,
        REPORT_PATH=None,
        REMOTE_PROPERTY_ROOT=None,
        EXPECTED_HELPER_MARKER=None,
        EXPECTED_HELPER_SHA256=None,
    )


class BuildNativeInitBootV726WifiLifecycle(unittest.TestCase):
    def test_configure_base_rewrites_v2168_axes_and_lifecycle_flags(self) -> None:
        old_v2168 = builder.v2168
        fake_base = types.SimpleNamespace(
            DEFAULT_ARGS=fake_base_args(),
            base=types.SimpleNamespace(EXTRA_INIT_FLAGS=[]),
        )
        fake_v2168 = fake_v2168_module(fake_base)
        builder.v2168 = fake_v2168
        try:
            builder.configure_base()
        finally:
            builder.v2168 = old_v2168

        args = dict(zip(fake_base.DEFAULT_ARGS[0::2], fake_base.DEFAULT_ARGS[1::2]))
        self.assertTrue(fake_base.configured_by_v2168)
        self.assertEqual(fake_v2168.OUT_DIR, builder.OUT_DIR)
        self.assertEqual(fake_v2168.REPORT_PATH, builder.REPORT_PATH)
        self.assertEqual(fake_v2168.REMOTE_PROPERTY_ROOT, builder.REMOTE_PROPERTY_ROOT)
        self.assertEqual(fake_v2168.EXPECTED_HELPER_MARKER, builder.EXPECTED_HELPER_MARKER)
        self.assertEqual(fake_v2168.EXPECTED_HELPER_SHA256, builder.EXPECTED_HELPER_SHA256)
        self.assertIn('-DNETSERVICE_USB_HELPER="/bin/a90_usbnet"', builder.EXTRA_INIT_FLAGS)
        self.assertIn('-DNETSERVICE_TCPCTL_HELPER="/bin/a90_tcpctl"', builder.EXTRA_INIT_FLAGS)
        self.assertIn("-DA90_WIFI_LIFECYCLE_MODEM_OWNER=1", builder.EXTRA_INIT_FLAGS)
        self.assertEqual(fake_v2168.EXTRA_INIT_FLAGS, builder.EXTRA_INIT_FLAGS)
        self.assertEqual(fake_v2168.prev2137.EXTRA_INIT_FLAGS, builder.EXTRA_INIT_FLAGS)
        self.assertEqual(fake_v2168.prev2137.prev2135.EXTRA_INIT_FLAGS, builder.EXTRA_INIT_FLAGS)
        self.assertEqual(fake_v2168.prev2137.prev2135.prev2133.EXTRA_INIT_FLAGS, builder.EXTRA_INIT_FLAGS)
        self.assertEqual(fake_base.base.EXTRA_INIT_FLAGS, builder.EXTRA_INIT_FLAGS)
        self.assertEqual(args["--cycle"], "V726")
        self.assertEqual(args["--decision"], "v726-wifi-lifecycle-source-build-pass")
        self.assertEqual(args["--cycle-label"], "v726")
        self.assertEqual(args["--init-version"], "0.9.246")
        self.assertEqual(args["--init-build"], "v726-wifi-lifecycle")
        self.assertEqual(args["--wifi-test-klog-prefix"], "A90v726")
        self.assertEqual(args["--wifi-test-disable"], "/cache/native-init-wifi-test-boot-v726.disable")
        self.assertEqual(args["--wifi-test-log"], "/cache/native-init-wifi-test-boot-v726.log")
        self.assertEqual(args["--wifi-test-summary"], "/cache/native-init-wifi-test-boot-v726.summary")
        self.assertEqual(args["--wifi-test-helper-result"], "/cache/native-init-wifi-test-boot-v726-helper.result")
        self.assertEqual(args["--wifi-test-pid"], "/cache/native-init-wifi-test-boot-v726.pid")
        self.assertEqual(args["--wifi-test-watcher-pid"], "/cache/native-init-wifi-test-boot-v726-supervisor.pid")
        self.assertEqual(args["--wifi-test-property-root"], builder.REMOTE_PROPERTY_ROOT)
        self.assertIn("a90_android_execns_probe_v427_wifi_lifecycle", args["--helper-binary"])

    def test_render_report_records_lifecycle_route_and_safety_scope(self) -> None:
        manifest = {
            "decision": "v726-wifi-lifecycle-source-build-pass",
            "base_boot": "workspace/private/inputs/boot_images/boot_linux_v725_fasttransport.img",
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v726_wifi_lifecycle.img",
            "boot_sha256": "boot-sha",
            "init_version": "0.9.246",
            "init_build": "v726-wifi-lifecycle",
            "helper_marker": "a90_android_execns_probe v427",
            "helper_sha256": "helper-sha",
            "wifi_test": {
                "helper_runtime_mode": "wifi-companion",
                "helper_timeout_sec": 75,
            },
        }

        report = builder.render_report(manifest)

        self.assertIn("# Native Init V726 Wi-Fi Lifecycle Source Build", report)
        self.assertIn("Decision: `v726-wifi-lifecycle-source-build-pass`", report)
        self.assertIn("V2168 QCACLD firmware_class feeder path", report)
        self.assertIn("PID1-owned `/dev/subsys_modem` lifecycle holder", report)
        self.assertIn("preserving the V725 fasttransport ramdisk contract", report)
        self.assertIn("firmware mounts", report)
        self.assertIn("RFS bridges", report)
        self.assertIn("post-FW_READY `boot_wlan`", report)
        self.assertIn("Wi-Fi runtime summary sampler", report)
        self.assertIn("No `/dev/subsys_esoc0`", report)
        self.assertIn("credential-redacted and rollbackable", report)

    def test_normalize_manifest_axes_records_legacy_cycle_and_supporting_run_ids(self) -> None:
        old_out_dir = builder.OUT_DIR
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                out_dir = Path(temp_dir)
                manifest_path = out_dir / "manifest.json"
                manifest_path.write_text(json.dumps({"cycle": "V726", "decision": "pass"}), encoding="utf-8")
                builder.OUT_DIR = out_dir

                builder.normalize_manifest_axes()

                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        finally:
            builder.OUT_DIR = old_out_dir

        self.assertIsNone(manifest["cycle"])
        self.assertEqual(manifest["legacy_cycle_field"], "V726")
        self.assertEqual(manifest["baseline_tag"], "v726-wifi-lifecycle")
        self.assertEqual(manifest["version_axes"]["baseline_tag"], "v726-wifi-lifecycle")
        self.assertEqual(manifest["version_axes"]["helper_version"], "helper-v427")
        self.assertEqual(manifest["version_axes"]["supporting_run_ids"], ["V2167", "V2168"])
        self.assertIn("not a global run ID", manifest["version_axes"]["note"])

    def test_normalize_manifest_axes_preserves_non_v726_cycle_without_legacy_field(self) -> None:
        old_out_dir = builder.OUT_DIR
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                out_dir = Path(temp_dir)
                manifest_path = out_dir / "manifest.json"
                manifest_path.write_text(json.dumps({"cycle": "OTHER", "decision": "pass"}), encoding="utf-8")
                builder.OUT_DIR = out_dir

                builder.normalize_manifest_axes()

                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        finally:
            builder.OUT_DIR = old_out_dir

        self.assertEqual(manifest["cycle"], "OTHER")
        self.assertNotIn("legacy_cycle_field", manifest)
        self.assertEqual(manifest["baseline_tag"], "v726-wifi-lifecycle")

    def test_main_patches_helper_sets_report_and_normalizes_only_on_success(self) -> None:
        old_v2168 = builder.v2168
        old_normalize = builder.normalize_manifest_axes
        try:
            for rc, expected_normalize_calls in ((0, 1), (3, 0)):
                fake_base = types.SimpleNamespace(
                    DEFAULT_ARGS=fake_base_args(),
                    base=types.SimpleNamespace(EXTRA_INIT_FLAGS=[]),
                    main=lambda rc=rc: rc,
                )
                patched_bases: list[object] = []
                normalized: list[bool] = []
                fake_v2168 = fake_v2168_module(fake_base, patched_bases=patched_bases)
                builder.v2168 = fake_v2168
                builder.normalize_manifest_axes = lambda: normalized.append(True)

                self.assertEqual(builder.main(), rc)
                self.assertEqual(patched_bases, [fake_base])
                self.assertIs(fake_base.render_report, builder.render_report)
                self.assertEqual(len(normalized), expected_normalize_calls)
        finally:
            builder.v2168 = old_v2168
            builder.normalize_manifest_axes = old_normalize


if __name__ == "__main__":
    unittest.main()
