"""Regression tests for build_native_init_boot_v2254_wifi_detail_surface."""

import json
import tempfile
import types
import unittest
from pathlib import Path

from _loader import load_revalidation

v2254 = load_revalidation("build_native_init_boot_v2254_wifi_detail_surface")


def nested_namespace(*names, leaf):
    current = leaf
    for name in reversed(names):
        current = types.SimpleNamespace(**{name: current})
    return current


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


def fake_v2237_with_base(fake_base):
    def set_arg(args, key, value):
        index = args.index(key)
        args[index + 1] = value

    helper_builder = types.SimpleNamespace()
    v726 = types.SimpleNamespace(set_arg=set_arg)
    v2230 = nested_namespace("v2189", "v2188", "v2187", "v2182", "v2178", "v2176", "v2174", "v2169", "v726", leaf=v726)
    helper_flags = (
        "-DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1",
        "-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1",
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
        v2230=v2230,
        base_module=lambda: fake_base,
        helper_builder_module=lambda: helper_builder,
    )
    fake.configure_base = lambda: helper_flags
    fake.patch_mkbootimg_tools = lambda base: setattr(base, "mkbootimg_patched", True)
    return fake, helper_builder, helper_flags


class PatchV2237:
    def __init__(self, fake):
        self.fake = fake
        self.old = None

    def __enter__(self):
        self.old = v2254.v2237
        v2254.v2237 = self.fake
        return self.fake

    def __exit__(self, exc_type, exc, tb):
        v2254.v2237 = self.old


class BuildWrapperConfiguration(unittest.TestCase):
    def test_configure_base_rewrites_v2237_axes_and_preserves_helper_flags(self):
        fake_base = types.SimpleNamespace(DEFAULT_ARGS=fake_base_args(), base=types.SimpleNamespace(EXTRA_INIT_FLAGS=[]))
        fake, _, expected_flags = fake_v2237_with_base(fake_base)

        with PatchV2237(fake):
            helper_flags = v2254.configure_base()

        args = dict(zip(fake_base.DEFAULT_ARGS[0::2], fake_base.DEFAULT_ARGS[1::2]))
        self.assertEqual(fake.OUT_DIR, v2254.OUT_DIR)
        self.assertEqual(fake.REPORT_PATH, v2254.REPORT_PATH)
        self.assertEqual(args["--cycle"], "V2254")
        self.assertEqual(args["--decision"], "v2254-wifi-detail-surface-source-build-pass")
        self.assertEqual(args["--init-version"], "0.9.272")
        self.assertEqual(args["--init-build"], "v2254-wifi-detail-surface")
        self.assertEqual(args["--wifi-test-klog-prefix"], "A90v2254")
        self.assertIn("a90_android_execns_probe_v430_wifi_detail_surface", args["--helper-binary"])
        self.assertEqual(args["--wifi-test-property-root"], v2254.REMOTE_PROPERTY_ROOT)
        self.assertEqual(helper_flags, expected_flags)
        self.assertEqual(fake_base.base.EXTRA_INIT_FLAGS, v2254.EXTRA_INIT_FLAGS)

    def test_render_report_records_t2_transition_and_read_only_detail_fields(self):
        manifest = {
            "decision": "v2254-wifi-detail-surface-source-build-pass",
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v2254.img",
            "boot_sha256": "boot-sha",
            "init_version": "0.9.272",
            "init_build": "v2254-wifi-detail-surface",
            "helper_marker": "a90_android_execns_probe v427",
            "helper_sha256": "helper-sha",
            "wifi_test": {
                "helper_runtime_mode": "wifi-companion",
                "helper_timeout_sec": 75,
            },
        }

        report = v2254.render_report(manifest, ("-DTEST=1",))

        self.assertIn("# Native Init V2254 Wi-Fi Detail Surface Source Build", report)
        self.assertIn("Track: T2 WLAN native-init surface/cleanup", report)
        self.assertIn("Dropped from T1 to T2 for this iteration", report)
        self.assertIn("default_route_present", report)
        self.assertIn("gateway_label", report)
        self.assertIn("resolv_conf.nameserver_count", report)
        self.assertIn("NETWORK > WIFI STATUS", report)
        self.assertIn("read-only `/sys`, `/proc/net/route`, and `/cache/a90-wifi/resolv.conf`", report)
        self.assertIn("did not issue live device commands", report)


class MainMetadataUpdate(unittest.TestCase):
    def test_main_rewrites_manifest_and_promotion_metadata_without_running_real_build(self):
        tmp_parent = v2254.REPO_ROOT / "tmp"
        tmp_parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=tmp_parent) as tmp:
            root = Path(tmp)
            out_dir = root / "out"
            out_dir.mkdir()
            boot_image = root / "boot_linux_v2254_wifi_detail_surface.img"
            report_path = root / "report.md"
            manifest_path = out_dir / "manifest.json"
            manifest_path.write_text(json.dumps({
                "decision": "v2254-wifi-detail-surface-source-build-pass",
                "boot_sha256": "boot-sha",
                "init_version": "0.9.272",
                "init_build": "v2254-wifi-detail-surface",
                "helper_sha256": "helper-sha",
            }), encoding="utf-8")
            old_values = {
                "OUT_DIR": v2254.OUT_DIR,
                "BOOT_IMAGE": v2254.BOOT_IMAGE,
                "REPORT_PATH": v2254.REPORT_PATH,
            }
            old_functions = {
                "configure_base": v2254.configure_base,
                "helper_builder_module": v2254.helper_builder_module,
                "base_module": v2254.base_module,
            }
            helper_builder = types.SimpleNamespace(
                patch_helper_builder=lambda base: setattr(base, "helper_patched", True)
            )
            fake_base = types.SimpleNamespace(base=types.SimpleNamespace(), main=lambda: 0)
            fake_v2237 = types.SimpleNamespace(
                patch_mkbootimg_tools=lambda base: setattr(base, "mkbootimg_patched", True)
            )
            v2254.OUT_DIR = out_dir
            v2254.BOOT_IMAGE = boot_image
            v2254.REPORT_PATH = report_path
            v2254.configure_base = lambda: ("-DTEST=1",)
            v2254.helper_builder_module = lambda: helper_builder
            v2254.base_module = lambda: fake_base
            try:
                with PatchV2237(fake_v2237):
                    rc = v2254.main()
            finally:
                for name, value in old_values.items():
                    setattr(v2254, name, value)
                for name, value in old_functions.items():
                    setattr(v2254, name, value)

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            promotion = json.loads((out_dir / "promotion-candidate.json").read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        self.assertTrue(fake_base.helper_patched)
        self.assertTrue(fake_base.mkbootimg_patched)
        self.assertEqual(helper_builder.EXPECTED_HELPER_MARKER, v2254.EXPECTED_HELPER_MARKER)
        self.assertEqual(helper_builder.EXPECTED_HELPER_SHA256, v2254.EXPECTED_HELPER_SHA256)
        self.assertEqual(fake_base.base.EXPECTED_HELPER_MARKER, v2254.EXPECTED_HELPER_MARKER)
        self.assertEqual(fake_base.base.EXPECTED_HELPER_SHA256, v2254.EXPECTED_HELPER_SHA256)
        self.assertEqual(manifest["candidate_tag"], "v2254-wifi-detail-surface")
        self.assertEqual(manifest["parent_baseline"], "v2237-supplicant-terminate-poll")
        self.assertEqual(manifest["rollback_baseline"], "v2237-supplicant-terminate-poll")
        self.assertEqual(manifest["helper_flags"], ["-DTEST=1"])
        self.assertEqual(
            manifest["wifi_detail_surface"]["status_fields_added"],
            [
                "default_route_present",
                "gateway_label",
                "gateway_rc",
                "resolv_conf.present",
                "resolv_conf.nameserver_count",
            ],
        )
        self.assertEqual(manifest["wifi_detail_surface"]["ui_surface"], "NETWORK > WIFI STATUS")
        self.assertEqual(manifest["wifi_detail_surface"]["scope"], "read-only status/menu surface")
        self.assertEqual(promotion["candidate_tag"], "v2254-wifi-detail-surface")
        self.assertEqual(promotion["source_report"], str(report_path.relative_to(v2254.REPO_ROOT)))


if __name__ == "__main__":
    unittest.main()
