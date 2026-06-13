"""Regression tests for build_native_init_wifi_test_boot_v2168."""

from __future__ import annotations

import types
import unittest
from pathlib import Path

from _loader import load_revalidation


builder = load_revalidation("build_native_init_wifi_test_boot_v2168")


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


def set_arg(args: list[str], key: str, value: str) -> None:
    index = args.index(key)
    args[index + 1] = value


def fake_prev2137_module(fake_base: object, patched_bases: list[object] | None = None) -> object:
    terminal = types.SimpleNamespace(set_arg=set_arg)
    prev2008 = types.SimpleNamespace(prev2006=terminal)

    def patch_helper_builder(base: object) -> None:
        if patched_bases is not None:
            patched_bases.append(base)

    prev2038 = types.SimpleNamespace(
        prev2008=prev2008,
        patch_helper_builder=patch_helper_builder,
        EXPECTED_HELPER_MARKER=None,
        EXPECTED_HELPER_SHA256=None,
    )
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
    prev2131 = types.SimpleNamespace(prev2129=prev2129, HELPER_FLAGS=("-DOLD_HELPER=1",))
    prev2133 = types.SimpleNamespace(prev2131=prev2131, EXTRA_INIT_FLAGS=("-DOLD_2133=1",))
    prev2135 = types.SimpleNamespace(prev2133=prev2133, EXTRA_INIT_FLAGS=("-DOLD_2135=1",))
    return types.SimpleNamespace(
        OUT_DIR=None,
        REMOTE_PROPERTY_ROOT=None,
        REPORT_PATH=None,
        EXPECTED_HELPER_MARKER=None,
        EXPECTED_HELPER_SHA256=None,
        EXTRA_INIT_FLAGS=("-DOLD_2137=1",),
        HELPER_FLAGS=("-DHELPER_FLAG=1",),
        prev2135=prev2135,
        base_module=lambda: fake_base,
        configure_base=lambda: setattr(fake_base, "configured_by_prev2137", True),
    )


class BuildNativeInitWifiTestBootV2168(unittest.TestCase):
    def test_configure_base_rewrites_v2137_axes_and_fasttransport_helpers(self) -> None:
        old_prev2137 = builder.prev2137
        original_helpers_called: list[object] = []
        fake_base = types.SimpleNamespace(
            DEFAULT_ARGS=fake_base_args(),
            base=types.SimpleNamespace(
                EXTRA_INIT_FLAGS=[],
                EXPECTED_HELPER_MARKER=None,
                EXPECTED_HELPER_SHA256=None,
                ramdisk_helpers=lambda args: original_helpers_called.append(args)
                or {"bin/a90_tcpctl": Path("/old/a90_tcpctl")},
            ),
        )
        fake_prev2137 = fake_prev2137_module(fake_base)
        builder.prev2137 = fake_prev2137
        try:
            builder.configure_base()
        finally:
            builder.prev2137 = old_prev2137

        args = dict(zip(fake_base.DEFAULT_ARGS[0::2], fake_base.DEFAULT_ARGS[1::2]))
        helper_builder = (
            fake_prev2137.prev2135.prev2133.prev2131.prev2129.prev2127.prev2120
            .prev2112.prev2108.prev2106.prev2102.prev2100.prev2097.prev2095
            .prev2082.prev2080.prev2058.prev2038
        )
        self.assertTrue(fake_base.configured_by_prev2137)
        self.assertEqual(fake_prev2137.OUT_DIR, builder.OUT_DIR)
        self.assertEqual(fake_prev2137.REMOTE_PROPERTY_ROOT, builder.REMOTE_PROPERTY_ROOT)
        self.assertEqual(fake_prev2137.REPORT_PATH, builder.REPORT_PATH)
        self.assertEqual(fake_prev2137.EXPECTED_HELPER_MARKER, builder.EXPECTED_HELPER_MARKER)
        self.assertEqual(fake_prev2137.EXPECTED_HELPER_SHA256, builder.EXPECTED_HELPER_SHA256)
        self.assertEqual(fake_prev2137.EXTRA_INIT_FLAGS, builder.EXTRA_INIT_FLAGS)
        self.assertEqual(fake_prev2137.prev2135.EXTRA_INIT_FLAGS, builder.EXTRA_INIT_FLAGS)
        self.assertEqual(fake_prev2137.prev2135.prev2133.EXTRA_INIT_FLAGS, builder.EXTRA_INIT_FLAGS)
        self.assertEqual(fake_prev2137.prev2135.prev2133.prev2131.HELPER_FLAGS, fake_prev2137.HELPER_FLAGS)
        self.assertEqual(helper_builder.EXPECTED_HELPER_MARKER, builder.EXPECTED_HELPER_MARKER)
        self.assertEqual(helper_builder.EXPECTED_HELPER_SHA256, builder.EXPECTED_HELPER_SHA256)
        self.assertEqual(fake_base.REPORT_PATH, builder.REPORT_PATH)
        self.assertEqual(args["--cycle"], "V2168")
        self.assertEqual(args["--decision"], "v2168-qcacld-fwclass-fasttransport-source-build-pass")
        self.assertEqual(args["--cycle-label"], "v2168")
        self.assertEqual(args["--init-version"], "0.9.245")
        self.assertEqual(args["--init-build"], "v2168-qcacld-fwclass-fasttransport")
        self.assertEqual(args["--wifi-test-klog-prefix"], "A90v2168")
        self.assertEqual(args["--wifi-test-disable"], "/cache/native-init-wifi-test-boot-v2168.disable")
        self.assertEqual(args["--wifi-test-log"], "/cache/native-init-wifi-test-boot-v2168.log")
        self.assertEqual(args["--wifi-test-summary"], "/cache/native-init-wifi-test-boot-v2168.summary")
        self.assertEqual(args["--wifi-test-helper-result"], "/cache/native-init-wifi-test-boot-v2168-helper.result")
        self.assertEqual(args["--wifi-test-pid"], "/cache/native-init-wifi-test-boot-v2168.pid")
        self.assertEqual(args["--wifi-test-watcher-pid"], "/cache/native-init-wifi-test-boot-v2168-supervisor.pid")
        self.assertEqual(args["--wifi-test-property-root"], builder.REMOTE_PROPERTY_ROOT)
        self.assertEqual(args["--base-boot"], str(builder.BASE_BOOT))
        self.assertIn("init_v2168_qcacld_fwclass_fasttransport", args["--init-binary"])
        self.assertIn("a90_android_execns_probe_v427_qcacld_fwclass_fasttransport", args["--helper-binary"])
        self.assertEqual(fake_base.base.EXTRA_INIT_FLAGS, builder.EXTRA_INIT_FLAGS)
        self.assertEqual(fake_base.base.EXPECTED_HELPER_MARKER, builder.EXPECTED_HELPER_MARKER)
        self.assertEqual(fake_base.base.EXPECTED_HELPER_SHA256, builder.EXPECTED_HELPER_SHA256)

        helper_args = types.SimpleNamespace()
        helpers = fake_base.base.ramdisk_helpers(helper_args)
        self.assertEqual(original_helpers_called, [helper_args])
        self.assertEqual(helpers["bin/a90_tcpctl"], Path("/old/a90_tcpctl"))
        self.assertEqual(helpers["bin/a90_usbnet"], builder.USERLAND_BIN / "a90_usbnet-aarch64-static")
        self.assertEqual(helpers["bin/busybox"], builder.USERLAND_BIN / "busybox-aarch64-static-1.36.1")
        self.assertEqual(helpers["bin/toybox"], builder.USERLAND_BIN / "toybox-aarch64-static-0.8.13")

    def test_render_report_records_fasttransport_and_qcacld_route(self) -> None:
        manifest = {
            "decision": "v2168-qcacld-fwclass-fasttransport-source-build-pass",
            "base_boot": "workspace/private/inputs/boot_images/boot_linux_v725_fasttransport.img",
            "boot_image": "workspace/private/builds/native-init/v2168/boot.img",
            "boot_sha256": "boot-sha",
            "init_version": "0.9.245",
            "init_build": "v2168-qcacld-fwclass-fasttransport",
            "helper_marker": "a90_android_execns_probe v427",
            "helper_sha256": "helper-sha",
            "wifi_test": {
                "helper_runtime_mode": "firmware-class-feeder",
                "helper_timeout_sec": 90,
            },
        }

        report = builder.render_report(manifest)

        self.assertIn("# Native Init V2168 QCACLD Firmware Class Fasttransport Source Build", report)
        self.assertIn("Decision: `v2168-qcacld-fwclass-fasttransport-source-build-pass`", report)
        self.assertIn("v725-fasttransport based QCACLD firmware_class feeder test boot", report)
        self.assertIn("above `0.9.244 (v725-fasttransport)`", report)
        self.assertIn("/bin/a90_usbnet", report)
        self.assertIn("/bin/a90_tcpctl", report)
        self.assertIn("firmware_class.path", report)
        self.assertIn("RFS bridges", report)
        self.assertIn("post-FW_READY `boot_wlan`", report)
        self.assertIn(
            "rollbackable to `workspace/private/inputs/boot_images/boot_linux_v725_fasttransport.img`",
            report,
        )

    def test_main_patches_helper_sets_report_and_returns_base_rc(self) -> None:
        old_prev2137 = builder.prev2137
        try:
            for rc in (0, 4):
                patched_bases: list[object] = []
                fake_base = types.SimpleNamespace(
                    DEFAULT_ARGS=fake_base_args(),
                    base=types.SimpleNamespace(
                        EXTRA_INIT_FLAGS=[],
                        ramdisk_helpers=lambda _args: {},
                    ),
                    main=lambda rc=rc: rc,
                )
                builder.prev2137 = fake_prev2137_module(fake_base, patched_bases)

                self.assertEqual(builder.main(), rc)
                self.assertEqual(patched_bases, [fake_base])
                self.assertIs(fake_base.render_report, builder.render_report)
        finally:
            builder.prev2137 = old_prev2137


if __name__ == "__main__":
    unittest.main()
