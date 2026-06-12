"""Regression tests for build_native_init_boot_v2236_strict_wifi_connect."""

import types
import unittest

from _loader import load_revalidation

v2236 = load_revalidation("build_native_init_boot_v2236_strict_wifi_connect")


def nested_namespace(*names, leaf):
    current = leaf
    for name in reversed(names):
        current = types.SimpleNamespace(**{name: current})
    return current


def prev_chain(*attrs, leaf):
    current = leaf
    for attr in reversed(attrs):
        current = types.SimpleNamespace(**{attr: current}, HELPER_FLAGS=("initial",))
    return current


def fake_v2230_with_base(fake_base):
    def set_arg(args, key, value):
        index = args.index(key)
        args[index + 1] = value

    helper_builder = types.SimpleNamespace(HELPER_FLAGS=("builder-initial",))
    prev2137 = prev_chain(
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
    prev2137.HELPER_FLAGS = ("base-flag", v2236.SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG)

    v726 = types.SimpleNamespace(
        set_arg=set_arg,
        v2168=types.SimpleNamespace(prev2137=prev2137),
    )
    chain = nested_namespace("v2187", "v2182", "v2178", "v2176", "v2174", "v2169", "v726", leaf=v726)
    fake_v2189 = types.SimpleNamespace(v2188=chain)
    fake = types.SimpleNamespace(
        v2189=fake_v2189,
        base_module=lambda: fake_base,
        configure_base=lambda: setattr(fake, "configured", True),
    )
    return fake, prev2137, helper_builder


class BuildWrapperConfiguration(unittest.TestCase):
    def test_with_bridge_flag_deduplicates_and_appends_bridge_flag(self):
        flags = v2236.with_bridge_flag((
            "-DOTHER=1",
            v2236.SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG,
            "-DSECOND=1",
        ))

        self.assertEqual(flags[-1], v2236.SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG)
        self.assertEqual(flags.count(v2236.SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG), 1)
        self.assertEqual(flags[:-1], ("-DOTHER=1", "-DSECOND=1"))

    def test_configure_base_rewrites_v2230_axes_and_helper_bridge_flags(self):
        old_v2230 = v2236.v2230
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
        fake_v2230, prev2137, helper_builder = fake_v2230_with_base(fake_base)
        v2236.v2230 = fake_v2230
        try:
            helper_flags = v2236.configure_base()
        finally:
            v2236.v2230 = old_v2230

        args = dict(zip(fake_base.DEFAULT_ARGS[0::2], fake_base.DEFAULT_ARGS[1::2]))
        self.assertTrue(fake_v2230.configured)
        self.assertEqual(fake_v2230.OUT_DIR, v2236.OUT_DIR)
        self.assertEqual(fake_v2230.REPORT_PATH, v2236.REPORT_PATH)
        self.assertEqual(fake_v2230.REMOTE_PROPERTY_ROOT, v2236.REMOTE_PROPERTY_ROOT)
        self.assertEqual(args["--cycle"], "V2236")
        self.assertEqual(args["--decision"], "v2236-strict-wifi-connect-source-build-pass")
        self.assertEqual(args["--init-version"], "0.9.267")
        self.assertEqual(args["--init-build"], "v2236-strict-wifi-connect")
        self.assertEqual(args["--wifi-test-klog-prefix"], "A90v2236")
        self.assertEqual(args["--wifi-test-watch-sec"], "180")
        self.assertEqual(args["--wifi-test-supervisor-timeout-sec"], "215")
        self.assertEqual(args["--wifi-test-property-root"], v2236.REMOTE_PROPERTY_ROOT)
        self.assertIn("a90_android_execns_probe_v430_strict_wifi_connect", args["--helper-binary"])
        self.assertIn(v2236.SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG, helper_flags)
        self.assertEqual(prev2137.HELPER_FLAGS, helper_flags)
        self.assertEqual(prev2137.prev2135.HELPER_FLAGS, helper_flags)
        self.assertEqual(prev2137.prev2135.prev2133.prev2131.HELPER_FLAGS, helper_flags)
        self.assertEqual(helper_builder.HELPER_FLAGS, helper_flags)
        self.assertEqual(fake_base.base.EXTRA_INIT_FLAGS, v2236.EXTRA_INIT_FLAGS)

    def test_render_report_includes_strict_connect_route_and_safety_scope(self):
        manifest = {
            "decision": "v2236-strict-wifi-connect-source-build-pass",
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v2236.img",
            "boot_sha256": "sha",
            "init_version": "0.9.267",
            "init_build": "v2236-strict-wifi-connect",
            "helper_marker": "a90_android_execns_probe v430",
            "helper_sha256": "helper-sha",
            "wifi_test": {
                "helper_runtime_mode": "wifi-companion-wlan-pd-service-object-visible-trigger-start-only",
                "helper_timeout_sec": 215,
            },
        }

        report = v2236.render_report(manifest, ("-DOTHER=1", v2236.SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG))

        self.assertIn("# Native Init V2236 Strict Wi-Fi Connect Source Build", report)
        self.assertIn("Decision: `v2236-strict-wifi-connect-source-build-pass`", report)
        self.assertIn("strict Wi-Fi connect validation test boot", report)
        self.assertIn("require `wpa_state=COMPLETED`", report)
        self.assertIn("stale `wpa_supplicant` is not reused", report)
        self.assertIn(v2236.SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG, report)
        self.assertIn("bounded native Wi-Fi scan/connect/DHCP/ping only under stored private profiles", report)


if __name__ == "__main__":
    unittest.main()
