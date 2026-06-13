"""Regression tests for build_native_init_boot_v2189_security_p0_stage_fix."""

from __future__ import annotations

import json
import tempfile
import types
import unittest
from pathlib import Path

from _loader import load_revalidation


v2189 = load_revalidation("build_native_init_boot_v2189_security_p0_stage_fix")


def namespace_chain(*names, leaf):
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


class FakeLegacyMkbootimgDir:
    def __init__(self) -> None:
        self.unlinked = False

    def is_symlink(self) -> bool:
        return False

    def unlink(self) -> None:
        self.unlinked = True


def fake_v2188_module(fake_base, helper_builder=None):
    def set_arg(args, key, value):
        index = args.index(key)
        args[index + 1] = value

    v726 = types.SimpleNamespace(set_arg=set_arg)
    if helper_builder is not None:
        helper_path = namespace_chain(
            "v2168",
            "prev2137",
            "prev2135",
            "prev2133",
            "prev2131",
            "prev2129",
            "prev2127",
            "prev2120",
            "prev2112",
            "prev2108",
            "prev2106",
            "prev2102",
            "prev2100",
            "prev2097",
            "prev2095",
            "prev2082",
            "prev2080",
            "prev2058",
            "prev2038",
            leaf=helper_builder,
        )
        v726.v2168 = helper_path.v2168

    v2169 = types.SimpleNamespace(
        v726=v726,
        ensure_legacy_mkbootimg_link=lambda: False,
        LEGACY_MKBOOTIMG_DIR=FakeLegacyMkbootimgDir(),
    )
    v2178_path = namespace_chain("v2178", "v2176", "v2174", "v2169", leaf=v2169)
    v2182 = types.SimpleNamespace(v2178=v2178_path.v2178)
    v2187 = types.SimpleNamespace(v2182=v2182)
    return types.SimpleNamespace(
        base_module=lambda: fake_base,
        configure_base=lambda: setattr(fake_base, "configured_by_v2188", True),
        EXTRA_INIT_FLAGS=("-DIGNORED-BY-WRAPPER=1",),
        REMOTE_PROPERTY_ROOT="/fake/property/root",
        EXPECTED_HELPER_MARKER="fake-marker",
        EXPECTED_HELPER_SHA256="old-helper-sha",
        v2187=v2187,
    )


class BuildWrapperConfiguration(unittest.TestCase):
    def test_configure_base_rewrites_v2188_axes_for_stage_fix_candidate(self) -> None:
        old_v2188 = v2189.v2188
        fake_base = types.SimpleNamespace(
            DEFAULT_ARGS=fake_base_args(),
            base=types.SimpleNamespace(EXTRA_INIT_FLAGS=[]),
        )
        fake_v2188 = fake_v2188_module(fake_base)
        v2189.v2188 = fake_v2188
        try:
            v2189.configure_base()
        finally:
            v2189.v2188 = old_v2188

        args = dict(zip(fake_base.DEFAULT_ARGS[0::2], fake_base.DEFAULT_ARGS[1::2]))
        self.assertTrue(fake_base.configured_by_v2188)
        self.assertEqual(fake_v2188.OUT_DIR, v2189.OUT_DIR)
        self.assertEqual(fake_v2188.REPORT_PATH, v2189.REPORT_PATH)
        self.assertEqual(fake_v2188.BOOT_IMAGE, v2189.BOOT_IMAGE)
        self.assertEqual(fake_v2188.INIT_BINARY, v2189.INIT_BINARY)
        self.assertEqual(fake_v2188.RAMDISK_CPIO, v2189.RAMDISK_CPIO)
        self.assertEqual(args["--cycle"], "V2189")
        self.assertEqual(args["--decision"], "v2189-security-p0-stage-fix-source-build-pass")
        self.assertEqual(args["--cycle-label"], "v2189")
        self.assertEqual(args["--init-version"], "0.9.261")
        self.assertEqual(args["--init-build"], "v2189-security-p0-stage-fix")
        self.assertEqual(args["--wifi-test-klog-prefix"], "A90v2189")
        self.assertEqual(args["--wifi-test-disable"], "/cache/native-init-wifi-test-boot-v2189.disable")
        self.assertEqual(args["--wifi-test-log"], "/cache/native-init-wifi-test-boot-v2189.log")
        self.assertEqual(
            args["--wifi-test-helper-result"],
            "/cache/native-init-wifi-test-boot-v2189-helper.result",
        )
        self.assertEqual(args["--wifi-test-property-root"], v2189.REMOTE_PROPERTY_ROOT)
        self.assertIn("a90_android_execns_probe_v427_security_p0_stage_fix", args["--helper-binary"])
        self.assertEqual(fake_base.base.EXTRA_INIT_FLAGS, v2189.EXTRA_INIT_FLAGS)

    def test_main_pins_expected_helper_marker_and_sha_before_patch(self) -> None:
        old_v2188 = v2189.v2188
        fake_base = types.SimpleNamespace(
            DEFAULT_ARGS=fake_base_args(),
            base=types.SimpleNamespace(EXTRA_INIT_FLAGS=[]),
            main=lambda: 1,
        )
        patched_bases = []
        helper_builder = types.SimpleNamespace(
            EXPECTED_HELPER_MARKER="old-marker",
            EXPECTED_HELPER_SHA256="old-sha",
            patch_helper_builder=lambda base: patched_bases.append(base),
        )
        v2189.v2188 = fake_v2188_module(fake_base, helper_builder=helper_builder)
        try:
            rc = v2189.main()
        finally:
            v2189.v2188 = old_v2188

        self.assertEqual(rc, 1)
        self.assertEqual(helper_builder.EXPECTED_HELPER_MARKER, v2189.EXPECTED_HELPER_MARKER)
        self.assertEqual(helper_builder.EXPECTED_HELPER_SHA256, v2189.EXPECTED_HELPER_SHA256)
        self.assertEqual(patched_bases, [fake_base])
        self.assertIs(fake_base.render_report, v2189.render_report)

    def test_render_report_records_stage_fix_hardening_without_runtime_wifi_actions(self) -> None:
        manifest = {
            "decision": "v2189-security-p0-stage-fix-source-build-pass",
            "base_boot": "workspace/private/inputs/boot_images/base.img",
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v2189.img",
            "boot_sha256": "boot-sha",
            "init_version": "0.9.261",
            "init_build": "v2189-security-p0-stage-fix",
            "helper_marker": "a90_android_execns_probe v427",
            "helper_sha256": "helper-sha",
            "wifi_test": {
                "helper_runtime_mode": "wifi-companion",
                "helper_timeout_sec": 75,
            },
        }

        report = v2189.render_report(manifest)

        self.assertIn("# Native Init V2189 Security P0 Stage Fix Source Build", report)
        self.assertIn("Decision: `v2189-security-p0-stage-fix-source-build-pass`", report)
        self.assertIn("fixes the live validation gap", report)
        self.assertIn("generated Wi-Fi runtime files are re-owned as root", report)
        self.assertIn("host Wi-Fi profile/connect staging hardens", report)
        self.assertIn("does not initiate Wi-Fi connect, DHCP, route/DNS changes, or ping", report)
        self.assertIn("No `/dev/subsys_esoc0`", report)

    def test_normalize_manifest_axes_tracks_parent_candidate_and_unpromoted_state(self) -> None:
        old_out_dir = v2189.OUT_DIR
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                out_dir = Path(temp_dir)
                manifest_path = out_dir / "manifest.json"
                manifest_path.write_text(json.dumps({"decision": "pass"}), encoding="utf-8")
                v2189.OUT_DIR = out_dir

                v2189.normalize_manifest_axes()

                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        finally:
            v2189.OUT_DIR = old_out_dir

        self.assertEqual(manifest["decision"], "pass")
        self.assertEqual(manifest["candidate_tag"], "v2189-security-p0-stage-fix")
        self.assertEqual(manifest["parent_baseline"], "v2187-screenapp-ui-validation")
        self.assertEqual(manifest["parent_candidate"], "v2188-security-p0-hardening")
        self.assertEqual(manifest["rollback_baseline"], "v2187-screenapp-ui-validation")
        self.assertFalse(manifest["promoted_baseline"])
        self.assertEqual(manifest["version_axes"]["run_id"], "V2189")
        self.assertEqual(manifest["version_axes"]["helper_version"], "helper-v427")
        self.assertIn("staged-artifact ownership gap", manifest["version_axes"]["note"])


if __name__ == "__main__":
    unittest.main()
