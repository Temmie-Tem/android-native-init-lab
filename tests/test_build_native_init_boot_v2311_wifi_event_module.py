"""Regression tests for build_native_init_boot_v2311_wifi_event_module."""

import json
import tempfile
import types
import unittest
from pathlib import Path

from _loader import load_revalidation

v2311 = load_revalidation("build_native_init_boot_v2311_wifi_event_module")


def fake_base_args():
    return [
        "--cycle", "OLD",
        "--decision", "old-decision",
        "--cycle-label", "old-label",
        "--init-version", "0.0.0",
        "--init-build", "old-build",
        "--out-dir", "old-out",
        "--init-binary", "old-init",
        "--helper-binary", "old-helper",
        "--ramdisk-cpio", "old-ramdisk",
        "--boot-image", "old-boot",
        "--wifi-test-klog-prefix", "OLD",
        "--wifi-test-disable", "old-disable",
        "--wifi-test-log", "old-log",
        "--wifi-test-summary", "old-summary",
        "--wifi-test-helper-result", "old-helper-result",
        "--wifi-test-pid", "old-pid",
        "--wifi-test-watcher-pid", "old-watcher",
        "--wifi-test-property-root", "old-prop",
    ]


def fake_v2310_with_base(fake_base):
    helper_builder = types.SimpleNamespace()
    helper_flags = (
        "-DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1",
        "-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1",
    )
    fake_v2309 = types.SimpleNamespace(
        v2237=types.SimpleNamespace(patch_mkbootimg_tools=lambda base: setattr(base, "mkbootimg_patched", True))
    )
    fake = types.SimpleNamespace(
        OUT_DIR=None,
        REPORT_PATH=None,
        BOOT_IMAGE=None,
        INIT_BINARY=None,
        RAMDISK_CPIO=None,
        REMOTE_PROPERTY_ROOT="/fake/property/root",
        EXTRA_INIT_FLAGS=("-DEXTRA=1",),
        EXPECTED_HELPER_MARKER="helper-marker",
        EXPECTED_HELPER_SHA256="helper-sha",
        v2309=fake_v2309,
        base_module=lambda: fake_base,
        helper_builder_module=lambda: helper_builder,
    )
    fake.configure_base = lambda: helper_flags
    return fake, helper_builder, helper_flags


class PatchV2310:
    def __init__(self, fake):
        self.fake = fake
        self.old = None

    def __enter__(self):
        self.old = v2311.v2310
        v2311.v2310 = self.fake
        return self.fake

    def __exit__(self, exc_type, exc, tb):
        v2311.v2310 = self.old


class BuildWrapperConfiguration(unittest.TestCase):
    def test_configure_base_rewrites_axes_for_v2311(self):
        fake_base = types.SimpleNamespace(DEFAULT_ARGS=fake_base_args(), base=types.SimpleNamespace(EXTRA_INIT_FLAGS=[]))
        fake, _, expected_flags = fake_v2310_with_base(fake_base)

        with PatchV2310(fake):
            helper_flags = v2311.configure_base()

        args = dict(zip(fake_base.DEFAULT_ARGS[0::2], fake_base.DEFAULT_ARGS[1::2]))
        self.assertEqual(fake.OUT_DIR, v2311.OUT_DIR)
        self.assertEqual(fake.REPORT_PATH, v2311.REPORT_PATH)
        self.assertEqual(args["--cycle"], "V2311")
        self.assertEqual(args["--decision"], "v2311-wifi-event-module-source-build-pass")
        self.assertEqual(args["--init-version"], "0.9.275")
        self.assertEqual(args["--init-build"], "v2311-wifi-event-module")
        self.assertEqual(args["--wifi-test-klog-prefix"], "A90v2311")
        self.assertIn("a90_android_execns_probe_v430_wifi_event_module", args["--helper-binary"])
        self.assertEqual(args["--wifi-test-property-root"], v2311.REMOTE_PROPERTY_ROOT)
        self.assertEqual(helper_flags, expected_flags)
        self.assertEqual(fake_base.base.EXTRA_INIT_FLAGS, v2311.EXTRA_INIT_FLAGS)

    def test_render_report_records_t2_module_split_and_safety(self):
        manifest = {
            "decision": "v2311-wifi-event-module-source-build-pass",
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v2311.img",
            "boot_sha256": "boot-sha",
            "init_version": "0.9.275",
            "init_build": "v2311-wifi-event-module",
            "helper_marker": "a90_android_execns_probe v427",
            "helper_sha256": "helper-sha",
            "wifi_test": {
                "helper_runtime_mode": "wifi-companion",
                "helper_timeout_sec": 75,
            },
        }

        report = v2311.render_report(manifest, ("-DTEST=1",))

        self.assertIn("# Native Init V2311 Wi-Fi Event Module Source Build", report)
        self.assertIn("T2 native-init / WLAN baseline improvement", report)
        self.assertIn("a90_wifi_events.c", report)
        self.assertIn("wifi events [timeout_ms]", report)
        self.assertIn("wifi netevents [timeout_ms]", report)
        self.assertIn("behavior", report)
        self.assertIn("does not run Wi-Fi scan/connect", report)


class MainMetadataUpdate(unittest.TestCase):
    def test_main_rewrites_manifest_and_promotion_metadata_without_real_build(self):
        tmp_parent = v2311.REPO_ROOT / "tmp"
        tmp_parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=tmp_parent) as tmp:
            root = Path(tmp)
            out_dir = root / "out"
            out_dir.mkdir()
            boot_image = root / "boot_linux_v2311_wifi_event_module.img"
            report_path = root / "report.md"
            manifest_path = out_dir / "manifest.json"
            manifest_path.write_text(json.dumps({
                "decision": "v2311-wifi-event-module-source-build-pass",
                "boot_sha256": "boot-sha",
                "init_version": "0.9.275",
                "init_build": "v2311-wifi-event-module",
                "helper_sha256": "helper-sha",
            }), encoding="utf-8")
            old_values = {
                "OUT_DIR": v2311.OUT_DIR,
                "BOOT_IMAGE": v2311.BOOT_IMAGE,
                "REPORT_PATH": v2311.REPORT_PATH,
            }
            old_functions = {
                "configure_base": v2311.configure_base,
                "helper_builder_module": v2311.helper_builder_module,
                "base_module": v2311.base_module,
            }
            helper_builder = types.SimpleNamespace(
                patch_helper_builder=lambda base: setattr(base, "helper_patched", True)
            )
            fake_base = types.SimpleNamespace(base=types.SimpleNamespace(), main=lambda: 0)
            fake_v2310 = types.SimpleNamespace(
                v2309=types.SimpleNamespace(
                    v2237=types.SimpleNamespace(patch_mkbootimg_tools=lambda base: setattr(base, "mkbootimg_patched", True))
                )
            )
            v2311.OUT_DIR = out_dir
            v2311.BOOT_IMAGE = boot_image
            v2311.REPORT_PATH = report_path
            v2311.configure_base = lambda: ("-DTEST=1",)
            v2311.helper_builder_module = lambda: helper_builder
            v2311.base_module = lambda: fake_base
            try:
                with PatchV2310(fake_v2310):
                    rc = v2311.main()
            finally:
                for name, value in old_values.items():
                    setattr(v2311, name, value)
                for name, value in old_functions.items():
                    setattr(v2311, name, value)

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            promotion = json.loads((out_dir / "promotion-candidate.json").read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        self.assertTrue(fake_base.helper_patched)
        self.assertTrue(fake_base.mkbootimg_patched)
        self.assertEqual(helper_builder.EXPECTED_HELPER_MARKER, v2311.EXPECTED_HELPER_MARKER)
        self.assertEqual(helper_builder.EXPECTED_HELPER_SHA256, v2311.EXPECTED_HELPER_SHA256)
        self.assertEqual(fake_base.base.EXPECTED_HELPER_MARKER, v2311.EXPECTED_HELPER_MARKER)
        self.assertEqual(fake_base.base.EXPECTED_HELPER_SHA256, v2311.EXPECTED_HELPER_SHA256)
        self.assertEqual(manifest["candidate_tag"], "v2311-wifi-event-module")
        self.assertEqual(manifest["parent_baseline"], "v2310-nl80211-events")
        self.assertEqual(manifest["rollback_baseline"], "v2237-supplicant-terminate-poll")
        self.assertEqual(manifest["helper_flags"], ["-DTEST=1"])
        self.assertEqual(manifest["wifi_event_module"]["moved_to"], "workspace/public/src/native-init/a90_wifi_events.c")
        self.assertEqual(
            manifest["wifi_event_module"]["commands"],
            ["wifi events [timeout_ms]", "wifi netevents [timeout_ms]"],
        )
        self.assertFalse(manifest["wifi_event_module"]["behavior_change_intended"])
        self.assertEqual(promotion["candidate_tag"], "v2311-wifi-event-module")
        self.assertEqual(promotion["source_report"], str(report_path.relative_to(v2311.REPO_ROOT)))


if __name__ == "__main__":
    unittest.main()
