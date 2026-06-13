"""Regression tests for build_native_init_boot_v2312_e1_connect_event_closure."""

import json
import tempfile
import types
import unittest
from pathlib import Path

from _loader import load_revalidation

v2312 = load_revalidation("build_native_init_boot_v2312_e1_connect_event_closure")


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


def fake_v2311_with_base(fake_base):
    helper_builder = types.SimpleNamespace()
    helper_flags = (
        "-DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1",
        "-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1",
    )
    fake_v2310 = types.SimpleNamespace(
        v2309=types.SimpleNamespace(
            v2237=types.SimpleNamespace(patch_mkbootimg_tools=lambda base: setattr(base, "mkbootimg_patched", True))
        )
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
        v2310=fake_v2310,
        base_module=lambda: fake_base,
        helper_builder_module=lambda: helper_builder,
    )
    fake.configure_base = lambda: helper_flags
    return fake, helper_builder, helper_flags


class PatchV2311:
    def __init__(self, fake):
        self.fake = fake
        self.old = None

    def __enter__(self):
        self.old = v2312.v2311
        v2312.v2311 = self.fake
        return self.fake

    def __exit__(self, exc_type, exc, tb):
        v2312.v2311 = self.old


class BuildWrapperConfiguration(unittest.TestCase):
    def test_configure_base_rewrites_axes_for_v2312(self):
        fake_base = types.SimpleNamespace(DEFAULT_ARGS=fake_base_args(), base=types.SimpleNamespace(EXTRA_INIT_FLAGS=[]))
        fake, _, expected_flags = fake_v2311_with_base(fake_base)

        with PatchV2311(fake):
            helper_flags = v2312.configure_base()

        args = dict(zip(fake_base.DEFAULT_ARGS[0::2], fake_base.DEFAULT_ARGS[1::2]))
        self.assertEqual(fake.OUT_DIR, v2312.OUT_DIR)
        self.assertEqual(fake.REPORT_PATH, v2312.REPORT_PATH)
        self.assertEqual(args["--cycle"], "V2312")
        self.assertEqual(args["--decision"], "v2312-e1-connect-event-closure-source-build-pass")
        self.assertEqual(args["--init-version"], "0.9.276")
        self.assertEqual(args["--init-build"], "v2312-e1-connect-event-closure")
        self.assertEqual(args["--wifi-test-klog-prefix"], "A90v2312")
        self.assertIn("a90_android_execns_probe_v431_e1_connect_event_closure", args["--helper-binary"])
        self.assertEqual(args["--wifi-test-property-root"], v2312.REMOTE_PROPERTY_ROOT)
        self.assertEqual(helper_flags, expected_flags)
        self.assertEqual(fake_base.base.EXTRA_INIT_FLAGS, v2312.EXTRA_INIT_FLAGS)

    def test_render_report_records_combined_capture_and_safety(self):
        manifest = {
            "decision": "v2312-e1-connect-event-closure-source-build-pass",
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v2312.img",
            "boot_sha256": "boot-sha",
            "init_version": "0.9.276",
            "init_build": "v2312-e1-connect-event-closure",
            "helper_marker": "a90_android_execns_probe v427",
            "helper_sha256": "helper-sha",
            "wifi_test": {
                "helper_runtime_mode": "wifi-companion",
                "helper_timeout_sec": 75,
            },
        }

        report = v2312.render_report(manifest, ("-DTEST=1",))

        self.assertIn("# Native Init V2312 E1 Connect-Event Closure Source Build", report)
        self.assertIn("wifi connect-event [profile] [timeout_ms]", report)
        self.assertIn("NL80211_CMD_CONNECT", report)
        self.assertIn("final carrier is up", report)
        self.assertIn("does not run DHCP", report)
        self.assertIn("workspace/private/secrets/a90-wifi-test.env", report)


class MainMetadataUpdate(unittest.TestCase):
    def test_main_rewrites_manifest_and_promotion_metadata_without_real_build(self):
        tmp_parent = v2312.REPO_ROOT / "tmp"
        tmp_parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=tmp_parent) as tmp:
            root = Path(tmp)
            out_dir = root / "out"
            out_dir.mkdir()
            boot_image = root / "boot_linux_v2312_e1_connect_event_closure.img"
            report_path = root / "report.md"
            manifest_path = out_dir / "manifest.json"
            manifest_path.write_text(json.dumps({
                "decision": "v2312-e1-connect-event-closure-source-build-pass",
                "boot_sha256": "boot-sha",
                "init_version": "0.9.276",
                "init_build": "v2312-e1-connect-event-closure",
                "helper_sha256": "helper-sha",
            }), encoding="utf-8")
            old_values = {
                "OUT_DIR": v2312.OUT_DIR,
                "BOOT_IMAGE": v2312.BOOT_IMAGE,
                "REPORT_PATH": v2312.REPORT_PATH,
            }
            old_functions = {
                "configure_base": v2312.configure_base,
                "helper_builder_module": v2312.helper_builder_module,
                "base_module": v2312.base_module,
            }
            helper_builder = types.SimpleNamespace(
                patch_helper_builder=lambda base: setattr(base, "helper_patched", True)
            )
            fake_base = types.SimpleNamespace(base=types.SimpleNamespace(), main=lambda: 0)
            fake_v2311 = types.SimpleNamespace(
                v2310=types.SimpleNamespace(
                    v2309=types.SimpleNamespace(
                        v2237=types.SimpleNamespace(
                            patch_mkbootimg_tools=lambda base: setattr(base, "mkbootimg_patched", True)
                        )
                    )
                )
            )
            v2312.OUT_DIR = out_dir
            v2312.BOOT_IMAGE = boot_image
            v2312.REPORT_PATH = report_path
            v2312.configure_base = lambda: ("-DTEST=1",)
            v2312.helper_builder_module = lambda: helper_builder
            v2312.base_module = lambda: fake_base
            try:
                with PatchV2311(fake_v2311):
                    rc = v2312.main()
            finally:
                for name, value in old_values.items():
                    setattr(v2312, name, value)
                for name, value in old_functions.items():
                    setattr(v2312, name, value)

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            promotion = json.loads((out_dir / "promotion-candidate.json").read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        self.assertTrue(fake_base.helper_patched)
        self.assertTrue(fake_base.mkbootimg_patched)
        self.assertEqual(helper_builder.EXPECTED_HELPER_MARKER, v2312.EXPECTED_HELPER_MARKER)
        self.assertEqual(helper_builder.EXPECTED_HELPER_SHA256, v2312.EXPECTED_HELPER_SHA256)
        self.assertEqual(fake_base.base.EXPECTED_HELPER_MARKER, v2312.EXPECTED_HELPER_MARKER)
        self.assertEqual(fake_base.base.EXPECTED_HELPER_SHA256, v2312.EXPECTED_HELPER_SHA256)
        self.assertEqual(manifest["candidate_tag"], "v2312-e1-connect-event-closure")
        self.assertEqual(manifest["parent_baseline"], "v2311-wifi-event-module")
        self.assertEqual(manifest["rollback_baseline"], "v2237-supplicant-terminate-poll")
        self.assertEqual(manifest["helper_flags"], ["-DTEST=1"])
        closure = manifest["wifi_connect_event_closure"]
        self.assertEqual(closure["command"], "wifi connect-event [profile] [timeout_ms]")
        self.assertTrue(closure["uses_existing_connect_path"])
        self.assertFalse(closure["dhcp_attempted"])
        self.assertFalse(closure["external_ping_attempted"])
        self.assertEqual(promotion["candidate_tag"], "v2312-e1-connect-event-closure")
        self.assertEqual(promotion["source_report"], str(report_path.relative_to(v2312.REPO_ROOT)))


if __name__ == "__main__":
    unittest.main()
