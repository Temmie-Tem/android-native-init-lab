"""Regression tests for build_native_init_boot_v2226_a90_boot_window_property_root."""

import json
import tempfile
import types
import unittest
from pathlib import Path

from _loader import load_revalidation

v2226 = load_revalidation("build_native_init_boot_v2226_a90_boot_window_property_root")


def nested_namespace(*names, leaf):
    current = leaf
    for name in reversed(names):
        current = types.SimpleNamespace(**{name: current})
    return current


class BuildWrapperConfiguration(unittest.TestCase):
    def test_configure_base_rewrites_v2189_axes_and_property_root(self):
        old_v2189 = v2226.v2189
        fake_base = types.SimpleNamespace(
            DEFAULT_ARGS=[
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
                "--wifi-test-helper-mode",
                "old-mode",
                "--wifi-test-watch-sec",
                "1",
                "--wifi-test-supervisor-timeout-sec",
                "2",
            ],
            base=types.SimpleNamespace(EXTRA_INIT_FLAGS=[]),
        )

        def set_arg(args, key, value):
            index = args.index(key)
            args[index + 1] = value

        v726 = types.SimpleNamespace(set_arg=set_arg)
        chain = nested_namespace("v2187", "v2182", "v2178", "v2176", "v2174", "v2169", "v726", leaf=v726)
        fake_v2189 = types.SimpleNamespace(
            base_module=lambda: fake_base,
            configure_base=lambda: setattr(fake_v2189, "configured", True),
            v2188=chain,
            EXTRA_INIT_FLAGS=["--flag"],
        )
        v2226.v2189 = fake_v2189
        try:
            v2226.configure_base()
        finally:
            v2226.v2189 = old_v2189

        args = dict(zip(fake_base.DEFAULT_ARGS[0::2], fake_base.DEFAULT_ARGS[1::2]))
        self.assertTrue(fake_v2189.configured)
        self.assertEqual(fake_v2189.OUT_DIR, v2226.OUT_DIR)
        self.assertEqual(fake_v2189.REPORT_PATH, v2226.REPORT_PATH)
        self.assertEqual(fake_v2189.REMOTE_PROPERTY_ROOT, v2226.REMOTE_PROPERTY_ROOT)
        self.assertEqual(args["--cycle"], "V2226")
        self.assertEqual(args["--decision"], "v2226-a90-boot-window-property-root-source-build-pass")
        self.assertEqual(args["--init-version"], "0.9.263")
        self.assertEqual(args["--init-build"], "v2226-a90-boot-window-property-root")
        self.assertEqual(args["--wifi-test-klog-prefix"], "A90v2226")
        self.assertEqual(args["--wifi-test-helper-mode"], "wlan-pd-cnss-output-visibility")
        self.assertEqual(args["--wifi-test-watch-sec"], "70")
        self.assertEqual(args["--wifi-test-supervisor-timeout-sec"], "95")
        self.assertEqual(args["--wifi-test-property-root"], v2226.REMOTE_PROPERTY_ROOT)
        self.assertIn("a90_android_execns_probe_v427_a90_boot_window_property_root", args["--helper-binary"])
        self.assertEqual(fake_base.base.EXTRA_INIT_FLAGS, v2226.EXTRA_INIT_FLAGS)

    def test_render_report_includes_v726_property_root_route_and_safety_scope(self):
        manifest = {
            "decision": "v2226-a90-boot-window-property-root-source-build-pass",
            "base_boot": "workspace/private/inputs/boot_images/base.img",
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v2226.img",
            "boot_sha256": "sha",
            "init_version": "0.9.263",
            "init_build": "v2226-a90-boot-window-property-root",
            "helper_marker": "a90_android_execns_probe v427",
            "helper_sha256": "helper-sha",
            "wifi_test": {
                "helper_mode": "wlan-pd-cnss-output-visibility",
                "helper_runtime_mode": "wifi-companion-wlan-pd-cnss-output-visibility-start-only",
                "helper_timeout_sec": 75,
                "supervisor_timeout_sec": 95,
                "watch_sec": 70,
                "helper_result": "/cache/result",
            },
        }

        report = v2226.render_report(manifest)

        self.assertIn("# Native Init V2226 A90 Boot-Window Property-Root Source Build", report)
        self.assertIn("Decision: `v2226-a90-boot-window-property-root-source-build-pass`", report)
        self.assertIn("property-root-fixed observer test boot", report)
        self.assertIn("Helper runtime mode: `wifi-companion-wlan-pd-cnss-output-visibility-start-only`", report)
        self.assertIn("Property root: `/mnt/sdext/a90/private-property-v317/v726/dev/__properties__`", report)
        self.assertIn("no dynamic `a90*` BPF attach", report)
        self.assertIn("does not flash, reboot, scan/connect Wi-Fi", report)

    def test_normalize_manifest_axes_adds_v2226_version_metadata(self):
        old_out_dir = v2226.OUT_DIR
        try:
            with tempfile.TemporaryDirectory() as tmp:
                out_dir = Path(tmp)
                manifest_path = out_dir / "manifest.json"
                manifest_path.write_text('{"decision": "pass"}', encoding="utf-8")
                v2226.OUT_DIR = out_dir

                v2226.normalize_manifest_axes()

                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        finally:
            v2226.OUT_DIR = old_out_dir

        self.assertEqual(manifest["decision"], "pass")
        self.assertEqual(manifest["candidate_tag"], "v2226-a90-boot-window-property-root")
        self.assertEqual(manifest["parent_baseline"], "v2189-security-p0-stage-fix")
        self.assertEqual(manifest["rollback_baseline"], "v2189-security-p0-stage-fix")
        self.assertFalse(manifest["promoted_baseline"])
        self.assertEqual(manifest["version_axes"]["run_id"], "V2226")
        self.assertEqual(manifest["version_axes"]["helper_version"], "helper-v427")
        self.assertIn("property-root-fixed observer test boot", manifest["version_axes"]["note"])
        self.assertIn("after V2225 proved the v2224 property root was missing", manifest["version_axes"]["note"])


if __name__ == "__main__":
    unittest.main()
