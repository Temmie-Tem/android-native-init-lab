"""Regression tests for build_native_init_boot_v2252_fwclass_boundary_stack."""

import json
import tempfile
import types
import unittest
from pathlib import Path

from _loader import load_revalidation

v2252 = load_revalidation("build_native_init_boot_v2252_fwclass_boundary_stack")


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
        "--wifi-test-helper-mode", "old-mode",
        "--wifi-test-watch-sec", "1",
        "--wifi-test-supervisor-timeout-sec", "2",
    ]


def fake_v2237_with_base(fake_base):
    def set_arg(args, key, value):
        index = args.index(key)
        args[index + 1] = value

    helper_builder = types.SimpleNamespace(HELPER_FLAGS=("builder-initial",))
    prev2131 = types.SimpleNamespace(HELPER_FLAGS=("prev2131-initial",))
    prev2133 = types.SimpleNamespace(prev2131=prev2131, HELPER_FLAGS=("prev2133-initial",))
    prev2135 = types.SimpleNamespace(prev2133=prev2133, HELPER_FLAGS=("prev2135-initial",))
    prev2137 = types.SimpleNamespace(
        prev2135=prev2135,
        HELPER_FLAGS=(
            "-DOTHER=1",
            "-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1",
            v2252.BOUNDARY_STACK_FLAG,
        ),
    )
    v726 = types.SimpleNamespace(set_arg=set_arg)
    v2230 = nested_namespace("v2189", "v2188", "v2187", "v2182", "v2178", "v2176", "v2174", "v2169", "v726", leaf=v726)

    def with_bridge_flag(flags):
        bridge = "-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1"
        return (*tuple(flag for flag in flags if flag != bridge), bridge)

    fake = types.SimpleNamespace(
        OUT_DIR=None,
        REPORT_PATH=None,
        BOOT_IMAGE=None,
        INIT_BINARY=None,
        RAMDISK_CPIO=None,
        REMOTE_PROPERTY_ROOT=None,
        EXTRA_INIT_FLAGS=("-DEXTRA=1",),
        HELPER_MODE="fake-helper-mode",
        HELPER_RUNTIME_MODE="fake-runtime-mode",
        v2230=v2230,
        with_bridge_flag=with_bridge_flag,
        base_module=lambda: fake_base,
        helper_chain=lambda: prev2137,
        helper_builder_module=lambda: helper_builder,
    )
    fake.configure_base = lambda: setattr(fake, "configured", True)
    fake.patch_mkbootimg_tools = lambda base: setattr(base, "mkbootimg_patched", True)
    return fake, prev2137, helper_builder


class PatchV2237:
    def __init__(self, fake):
        self.fake = fake
        self.old = None

    def __enter__(self):
        self.old = v2252.v2237
        v2252.v2237 = self.fake
        return self.fake

    def __exit__(self, exc_type, exc, tb):
        v2252.v2237 = self.old


class BuildWrapperConfiguration(unittest.TestCase):
    def test_with_boundary_stack_flag_deduplicates_bridge_and_boundary_flag(self):
        fake_base = types.SimpleNamespace(DEFAULT_ARGS=fake_base_args(), base=types.SimpleNamespace(EXTRA_INIT_FLAGS=[]))
        fake, _, _ = fake_v2237_with_base(fake_base)

        with PatchV2237(fake):
            flags = v2252.with_boundary_stack_flag((
                "-DOTHER=1",
                v2252.BOUNDARY_STACK_FLAG,
                "-DSECOND=1",
                v2252.BOUNDARY_STACK_FLAG,
            ))

        self.assertEqual(flags[-1], v2252.BOUNDARY_STACK_FLAG)
        self.assertEqual(flags.count(v2252.BOUNDARY_STACK_FLAG), 1)
        self.assertIn("-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1", flags)

    def test_configure_base_rewrites_v2237_axes_and_propagates_boundary_flag(self):
        fake_base = types.SimpleNamespace(DEFAULT_ARGS=fake_base_args(), base=types.SimpleNamespace(EXTRA_INIT_FLAGS=[]))
        fake, prev2137, helper_builder = fake_v2237_with_base(fake_base)

        with PatchV2237(fake):
            helper_flags = v2252.configure_base()

        args = dict(zip(fake_base.DEFAULT_ARGS[0::2], fake_base.DEFAULT_ARGS[1::2]))
        self.assertTrue(fake.configured)
        self.assertEqual(fake.OUT_DIR, v2252.OUT_DIR)
        self.assertEqual(fake.REPORT_PATH, v2252.REPORT_PATH)
        self.assertEqual(args["--cycle"], "V2252")
        self.assertEqual(args["--decision"], "v2252-fwclass-boundary-stack-source-build-pass")
        self.assertEqual(args["--init-version"], "0.9.271")
        self.assertEqual(args["--init-build"], "v2252-fwclass-boundary-stack")
        self.assertEqual(args["--wifi-test-klog-prefix"], "A90v2252")
        self.assertEqual(args["--wifi-test-watch-sec"], "190")
        self.assertEqual(args["--wifi-test-supervisor-timeout-sec"], "245")
        self.assertIn("a90_android_execns_probe_v430_fwclass_boundary_stack", args["--helper-binary"])
        self.assertEqual(helper_flags[-1], v2252.BOUNDARY_STACK_FLAG)
        self.assertEqual(prev2137.HELPER_FLAGS, helper_flags)
        self.assertEqual(prev2137.prev2135.HELPER_FLAGS, helper_flags)
        self.assertEqual(prev2137.prev2135.prev2133.prev2131.HELPER_FLAGS, helper_flags)
        self.assertEqual(helper_builder.HELPER_FLAGS, helper_flags)
        self.assertEqual(fake_base.base.EXTRA_INIT_FLAGS, v2252.EXTRA_INIT_FLAGS)

    def test_render_report_includes_boundary_stack_contract_and_safety_scope(self):
        manifest = {
            "decision": "v2252-fwclass-boundary-stack-source-build-pass",
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v2252.img",
            "boot_sha256": "boot-sha",
            "init_version": "0.9.271",
            "init_build": "v2252-fwclass-boundary-stack",
            "helper_marker": "a90_android_execns_probe v430",
            "helper_sha256": "helper-sha",
            "wifi_test": {
                "helper_runtime_mode": "wifi-companion",
                "helper_timeout_sec": 245,
            },
        }

        report = v2252.render_report(manifest, ("-DOTHER=1", v2252.BOUNDARY_STACK_FLAG))

        self.assertIn("# Native Init V2252 Firmware Class Boundary Stack Source Build", report)
        self.assertIn("Decision: `v2252-fwclass-boundary-stack-source-build-pass`", report)
        self.assertIn("A90 Linux init 0.9.271 (v2252-fwclass-boundary-stack)", report)
        self.assertIn("deterministic stack snapshots at the exact QCACLD firmware_class fallback feed boundaries", report)
        self.assertIn("A90_WIFI_TEST_BOOT_QCACLD_FWCLASS_BOUNDARY_STACK_SAMPLER=1", report)
        self.assertIn("before_feed", report)
        self.assertIn("after_feed", report)
        self.assertIn("WCNSS_qcom_cfg.ini", report)
        self.assertIn("bdwlan.bin", report)
        self.assertIn("regdb.bin", report)
        self.assertIn("did not issue live device commands", report)


class MainMetadataUpdate(unittest.TestCase):
    def test_main_rewrites_manifest_and_promotion_metadata_without_running_real_build(self):
        tmp_parent = v2252.REPO_ROOT / "tmp"
        tmp_parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=tmp_parent) as tmp:
            root = Path(tmp)
            out_dir = root / "out"
            out_dir.mkdir()
            boot_image = root / "boot_linux_v2252_fwclass_boundary_stack.img"
            report_path = root / "report.md"
            manifest_path = out_dir / "manifest.json"
            manifest_path.write_text(json.dumps({
                "decision": "v2252-fwclass-boundary-stack-source-build-pass",
                "boot_sha256": "boot-sha",
                "init_version": "0.9.271",
                "init_build": "v2252-fwclass-boundary-stack",
                "helper_sha256": "helper-sha",
            }), encoding="utf-8")
            old_values = {
                "OUT_DIR": v2252.OUT_DIR,
                "BOOT_IMAGE": v2252.BOOT_IMAGE,
                "REPORT_PATH": v2252.REPORT_PATH,
            }
            old_functions = {
                "configure_base": v2252.configure_base,
                "helper_builder_module": v2252.helper_builder_module,
                "base_module": v2252.base_module,
            }
            helper_builder = types.SimpleNamespace(
                patch_helper_builder=lambda base: setattr(base, "helper_patched", True)
            )
            fake_base = types.SimpleNamespace(base=types.SimpleNamespace(), main=lambda: 0)
            fake_v2237 = types.SimpleNamespace(
                patch_mkbootimg_tools=lambda base: setattr(base, "mkbootimg_patched", True)
            )
            v2252.OUT_DIR = out_dir
            v2252.BOOT_IMAGE = boot_image
            v2252.REPORT_PATH = report_path
            v2252.configure_base = lambda: ("-DTEST=1", v2252.BOUNDARY_STACK_FLAG)
            v2252.helper_builder_module = lambda: helper_builder
            v2252.base_module = lambda: fake_base
            try:
                with PatchV2237(fake_v2237):
                    rc = v2252.main()
            finally:
                for name, value in old_values.items():
                    setattr(v2252, name, value)
                for name, value in old_functions.items():
                    setattr(v2252, name, value)

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            promotion = json.loads((out_dir / "promotion-candidate.json").read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        self.assertTrue(fake_base.helper_patched)
        self.assertTrue(fake_base.mkbootimg_patched)
        self.assertEqual(helper_builder.EXPECTED_HELPER_MARKER, v2252.EXPECTED_HELPER_MARKER)
        self.assertEqual(helper_builder.EXPECTED_HELPER_SHA256, v2252.EXPECTED_HELPER_SHA256)
        self.assertEqual(fake_base.base.EXPECTED_HELPER_MARKER, v2252.EXPECTED_HELPER_MARKER)
        self.assertEqual(fake_base.base.EXPECTED_HELPER_SHA256, v2252.EXPECTED_HELPER_SHA256)
        self.assertEqual(manifest["candidate_tag"], "v2252-fwclass-boundary-stack")
        self.assertEqual(manifest["boundary_stack_flag"], v2252.BOUNDARY_STACK_FLAG)
        self.assertEqual(manifest["helper_flags"], ["-DTEST=1", v2252.BOUNDARY_STACK_FLAG])
        self.assertEqual(manifest["boundary_stack_contract"]["points"], ["before_feed", "after_feed"])
        self.assertEqual(
            manifest["boundary_stack_contract"]["requests"],
            ["WCNSS_qcom_cfg.ini", "bdwlan.bin", "regdb.bin"],
        )
        self.assertEqual(manifest["boundary_stack_contract"]["live_validation_cycle"], "V2253")
        self.assertEqual(promotion["candidate_tag"], "v2252-fwclass-boundary-stack")
        self.assertEqual(promotion["source_report"], str(report_path.relative_to(v2252.REPO_ROOT)))


if __name__ == "__main__":
    unittest.main()
