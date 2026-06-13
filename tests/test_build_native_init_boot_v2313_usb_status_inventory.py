"""Regression tests for build_native_init_boot_v2313_usb_status_inventory."""

import json
import tempfile
import types
import unittest
from pathlib import Path

from _loader import load_revalidation

v2313 = load_revalidation("build_native_init_boot_v2313_usb_status_inventory")


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


def fake_v2312_with_base(fake_base):
    helper_builder = types.SimpleNamespace()
    helper_flags = ("-DHELPER_A=1", "-DHELPER_B=1")
    fake_v2237 = types.SimpleNamespace(patch_mkbootimg_tools=lambda base: setattr(base, "mkbootimg_patched", True))
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
        v2311=types.SimpleNamespace(v2310=types.SimpleNamespace(v2309=types.SimpleNamespace(v2237=fake_v2237))),
        base_module=lambda: fake_base,
        helper_builder_module=lambda: helper_builder,
    )
    fake.configure_base = lambda: helper_flags
    return fake, helper_builder, helper_flags


class PatchV2312:
    def __init__(self, fake):
        self.fake = fake
        self.old = None

    def __enter__(self):
        self.old = v2313.v2312
        v2313.v2312 = self.fake
        return self.fake

    def __exit__(self, exc_type, exc, tb):
        v2313.v2312 = self.old


class BuildWrapperConfiguration(unittest.TestCase):
    def test_configure_base_rewrites_axes_for_v2313(self):
        fake_base = types.SimpleNamespace(DEFAULT_ARGS=fake_base_args(), base=types.SimpleNamespace(EXTRA_INIT_FLAGS=[]))
        fake, _, expected_flags = fake_v2312_with_base(fake_base)

        with PatchV2312(fake):
            helper_flags = v2313.configure_base()

        args = dict(zip(fake_base.DEFAULT_ARGS[0::2], fake_base.DEFAULT_ARGS[1::2]))
        self.assertEqual(fake.OUT_DIR, v2313.OUT_DIR)
        self.assertEqual(fake.REPORT_PATH, v2313.REPORT_PATH)
        self.assertEqual(args["--cycle"], "V2313")
        self.assertEqual(args["--decision"], "v2313-usb-status-inventory-source-build-pass")
        self.assertEqual(args["--init-version"], "0.9.277")
        self.assertEqual(args["--init-build"], "v2313-usb-status-inventory")
        self.assertEqual(args["--wifi-test-klog-prefix"], "A90v2313")
        self.assertIn("a90_android_execns_probe_v432_usb_status_inventory", args["--helper-binary"])
        self.assertEqual(args["--wifi-test-property-root"], v2313.REMOTE_PROPERTY_ROOT)
        self.assertEqual(helper_flags, expected_flags)
        self.assertEqual(fake_base.base.EXTRA_INIT_FLAGS, v2313.EXTRA_INIT_FLAGS)

    def test_render_report_records_read_only_usb_status_scope(self):
        manifest = {
            "decision": "v2313-usb-status-inventory-source-build-pass",
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v2313.img",
            "boot_sha256": "boot-sha",
            "init_version": "0.9.277",
            "init_build": "v2313-usb-status-inventory",
            "helper_marker": "a90_android_execns_probe v427",
            "helper_sha256": "helper-sha",
            "wifi_test": {
                "helper_runtime_mode": "wifi-companion",
                "helper_timeout_sec": 75,
            },
        }

        report = v2313.render_report(manifest, ("-DTEST=1",))

        self.assertIn("# Native Init V2313 USB Status Inventory Source Build", report)
        self.assertIn("usb [status]", report)
        self.assertIn("control-acm", report)
        self.assertIn("control-ncm", report)
        self.assertIn("mutation_attempted=0", report)
        self.assertIn("does not unbind or rebind", report)
        self.assertIn("Host-side USB enumeration is not required for U1", report)


class MainMetadataUpdate(unittest.TestCase):
    def test_main_rewrites_manifest_and_promotion_metadata_without_real_build(self):
        tmp_parent = v2313.REPO_ROOT / "tmp"
        tmp_parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=tmp_parent) as tmp:
            root = Path(tmp)
            out_dir = root / "out"
            out_dir.mkdir()
            boot_image = root / "boot_linux_v2313_usb_status_inventory.img"
            report_path = root / "report.md"
            manifest_path = out_dir / "manifest.json"
            manifest_path.write_text(json.dumps({
                "decision": "v2313-usb-status-inventory-source-build-pass",
                "boot_sha256": "boot-sha",
                "init_version": "0.9.277",
                "init_build": "v2313-usb-status-inventory",
                "helper_sha256": "helper-sha",
            }), encoding="utf-8")
            old_values = {
                "OUT_DIR": v2313.OUT_DIR,
                "BOOT_IMAGE": v2313.BOOT_IMAGE,
                "REPORT_PATH": v2313.REPORT_PATH,
            }
            old_functions = {
                "configure_base": v2313.configure_base,
                "helper_builder_module": v2313.helper_builder_module,
                "base_module": v2313.base_module,
            }
            helper_builder = types.SimpleNamespace(
                patch_helper_builder=lambda base: setattr(base, "helper_patched", True)
            )
            fake_base = types.SimpleNamespace(base=types.SimpleNamespace(), main=lambda: 0)
            fake_v2312 = types.SimpleNamespace(
                v2311=types.SimpleNamespace(
                    v2310=types.SimpleNamespace(
                        v2309=types.SimpleNamespace(
                            v2237=types.SimpleNamespace(
                                patch_mkbootimg_tools=lambda base: setattr(base, "mkbootimg_patched", True)
                            )
                        )
                    )
                )
            )
            v2313.OUT_DIR = out_dir
            v2313.BOOT_IMAGE = boot_image
            v2313.REPORT_PATH = report_path
            v2313.configure_base = lambda: ("-DTEST=1",)
            v2313.helper_builder_module = lambda: helper_builder
            v2313.base_module = lambda: fake_base
            try:
                with PatchV2312(fake_v2312):
                    rc = v2313.main()
            finally:
                for name, value in old_values.items():
                    setattr(v2313, name, value)
                for name, value in old_functions.items():
                    setattr(v2313, name, value)

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            promotion = json.loads((out_dir / "promotion-candidate.json").read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        self.assertTrue(fake_base.helper_patched)
        self.assertTrue(fake_base.mkbootimg_patched)
        self.assertEqual(helper_builder.EXPECTED_HELPER_MARKER, v2313.EXPECTED_HELPER_MARKER)
        self.assertEqual(helper_builder.EXPECTED_HELPER_SHA256, v2313.EXPECTED_HELPER_SHA256)
        self.assertEqual(fake_base.base.EXPECTED_HELPER_MARKER, v2313.EXPECTED_HELPER_MARKER)
        self.assertEqual(fake_base.base.EXPECTED_HELPER_SHA256, v2313.EXPECTED_HELPER_SHA256)
        self.assertEqual(manifest["candidate_tag"], "v2313-usb-status-inventory")
        self.assertEqual(manifest["parent_baseline"], "v2312-e1-connect-event-closure")
        self.assertEqual(manifest["rollback_baseline"], "v2237-supplicant-terminate-poll")
        self.assertEqual(manifest["helper_flags"], ["-DTEST=1"])
        inventory = manifest["usb_status_inventory"]
        self.assertEqual(inventory["command"], "usb [status]")
        self.assertEqual(inventory["version"], "a90-native-usb-status-v1")
        self.assertEqual(inventory["control_required"], ["control-acm", "control-ncm"])
        self.assertFalse(inventory["mutation_attempted"])
        self.assertFalse(inventory["host_enumeration_required"])
        self.assertEqual(promotion["candidate_tag"], "v2313-usb-status-inventory")
        self.assertEqual(promotion["source_report"], str(report_path.relative_to(v2313.REPO_ROOT)))


if __name__ == "__main__":
    unittest.main()
