"""Regression tests for build_native_init_boot_v2309_rtnetlink_events."""

import json
import tempfile
import types
import unittest
from pathlib import Path

from _loader import load_revalidation

v2309 = load_revalidation("build_native_init_boot_v2309_rtnetlink_events")


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
        self.old = v2309.v2237
        v2309.v2237 = self.fake
        return self.fake

    def __exit__(self, exc_type, exc, tb):
        v2309.v2237 = self.old


class BuildWrapperConfiguration(unittest.TestCase):
    def test_configure_base_rewrites_axes_for_v2309(self):
        fake_base = types.SimpleNamespace(DEFAULT_ARGS=fake_base_args(), base=types.SimpleNamespace(EXTRA_INIT_FLAGS=[]))
        fake, _, expected_flags = fake_v2237_with_base(fake_base)

        with PatchV2237(fake):
            helper_flags = v2309.configure_base()

        args = dict(zip(fake_base.DEFAULT_ARGS[0::2], fake_base.DEFAULT_ARGS[1::2]))
        self.assertEqual(fake.OUT_DIR, v2309.OUT_DIR)
        self.assertEqual(fake.REPORT_PATH, v2309.REPORT_PATH)
        self.assertEqual(args["--cycle"], "V2309")
        self.assertEqual(args["--decision"], "v2309-rtnetlink-events-source-build-pass")
        self.assertEqual(args["--init-version"], "0.9.273")
        self.assertEqual(args["--init-build"], "v2309-rtnetlink-events")
        self.assertEqual(args["--wifi-test-klog-prefix"], "A90v2309")
        self.assertIn("a90_android_execns_probe_v430_rtnetlink_events", args["--helper-binary"])
        self.assertEqual(args["--wifi-test-property-root"], v2309.REMOTE_PROPERTY_ROOT)
        self.assertEqual(helper_flags, expected_flags)
        self.assertEqual(fake_base.base.EXTRA_INIT_FLAGS, v2309.EXTRA_INIT_FLAGS)

    def test_render_report_records_e2_scope_and_safety(self):
        manifest = {
            "decision": "v2309-rtnetlink-events-source-build-pass",
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v2309.img",
            "boot_sha256": "boot-sha",
            "init_version": "0.9.273",
            "init_build": "v2309-rtnetlink-events",
            "helper_marker": "a90_android_execns_probe v427",
            "helper_sha256": "helper-sha",
            "wifi_test": {
                "helper_runtime_mode": "wifi-companion",
                "helper_timeout_sec": 75,
            },
        }

        report = v2309.render_report(manifest, ("-DTEST=1",))

        self.assertIn("# Native Init V2309 RTNETLINK Events Source Build", report)
        self.assertIn("Active epic / E2 rtnetlink link-address monitor", report)
        self.assertIn("Wi-Fi credentials are absent", report)
        self.assertIn("wifi netevents [timeout_ms]", report)
        self.assertIn("RTMGRP_LINK | RTMGRP_IPV4_IFADDR", report)
        self.assertIn("wlan0` and `ncm0", report)
        self.assertIn("raw_ip_redacted", report)
        self.assertIn("does not run Wi-Fi scan/connect", report)


class MainMetadataUpdate(unittest.TestCase):
    def test_main_rewrites_manifest_and_promotion_metadata_without_real_build(self):
        tmp_parent = v2309.REPO_ROOT / "tmp"
        tmp_parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=tmp_parent) as tmp:
            root = Path(tmp)
            out_dir = root / "out"
            out_dir.mkdir()
            boot_image = root / "boot_linux_v2309_rtnetlink_events.img"
            report_path = root / "report.md"
            manifest_path = out_dir / "manifest.json"
            manifest_path.write_text(json.dumps({
                "decision": "v2309-rtnetlink-events-source-build-pass",
                "boot_sha256": "boot-sha",
                "init_version": "0.9.273",
                "init_build": "v2309-rtnetlink-events",
                "helper_sha256": "helper-sha",
            }), encoding="utf-8")
            old_values = {
                "OUT_DIR": v2309.OUT_DIR,
                "BOOT_IMAGE": v2309.BOOT_IMAGE,
                "REPORT_PATH": v2309.REPORT_PATH,
            }
            old_functions = {
                "configure_base": v2309.configure_base,
                "helper_builder_module": v2309.helper_builder_module,
                "base_module": v2309.base_module,
            }
            helper_builder = types.SimpleNamespace(
                patch_helper_builder=lambda base: setattr(base, "helper_patched", True)
            )
            fake_base = types.SimpleNamespace(base=types.SimpleNamespace(), main=lambda: 0)
            fake_v2237 = types.SimpleNamespace(
                patch_mkbootimg_tools=lambda base: setattr(base, "mkbootimg_patched", True)
            )
            v2309.OUT_DIR = out_dir
            v2309.BOOT_IMAGE = boot_image
            v2309.REPORT_PATH = report_path
            v2309.configure_base = lambda: ("-DTEST=1",)
            v2309.helper_builder_module = lambda: helper_builder
            v2309.base_module = lambda: fake_base
            try:
                with PatchV2237(fake_v2237):
                    rc = v2309.main()
            finally:
                for name, value in old_values.items():
                    setattr(v2309, name, value)
                for name, value in old_functions.items():
                    setattr(v2309, name, value)

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            promotion = json.loads((out_dir / "promotion-candidate.json").read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        self.assertTrue(fake_base.helper_patched)
        self.assertTrue(fake_base.mkbootimg_patched)
        self.assertEqual(helper_builder.EXPECTED_HELPER_MARKER, v2309.EXPECTED_HELPER_MARKER)
        self.assertEqual(helper_builder.EXPECTED_HELPER_SHA256, v2309.EXPECTED_HELPER_SHA256)
        self.assertEqual(fake_base.base.EXPECTED_HELPER_MARKER, v2309.EXPECTED_HELPER_MARKER)
        self.assertEqual(fake_base.base.EXPECTED_HELPER_SHA256, v2309.EXPECTED_HELPER_SHA256)
        self.assertEqual(manifest["candidate_tag"], "v2309-rtnetlink-events")
        self.assertEqual(manifest["parent_baseline"], "v2237-supplicant-terminate-poll")
        self.assertEqual(manifest["rollback_baseline"], "v2237-supplicant-terminate-poll")
        self.assertEqual(manifest["helper_flags"], ["-DTEST=1"])
        self.assertEqual(manifest["rtnetlink_events"]["command"], "wifi netevents [timeout_ms]")
        self.assertEqual(manifest["rtnetlink_events"]["groups"], ["RTMGRP_LINK", "RTMGRP_IPV4_IFADDR"])
        self.assertEqual(manifest["rtnetlink_events"]["ifaces"], ["wlan0", "ncm0"])
        self.assertEqual(manifest["rtnetlink_events"]["events"], ["RTM_NEWLINK", "RTM_DELLINK", "RTM_NEWADDR", "RTM_DELADDR"])
        self.assertTrue(manifest["rtnetlink_events"]["raw_ip_redacted"])
        self.assertEqual(promotion["candidate_tag"], "v2309-rtnetlink-events")
        self.assertEqual(promotion["source_report"], str(report_path.relative_to(v2309.REPO_ROOT)))


if __name__ == "__main__":
    unittest.main()
