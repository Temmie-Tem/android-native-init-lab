"""Pin the calibrated A90 V3342 MAC-provisioning existing-evidence audit."""

from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys
import unittest

TESTS = Path(__file__).resolve().parent
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

from _loader import load_script


REPO = Path(__file__).resolve().parents[1]
REPORT = REPO / "docs/reports/A90_WLAN_MAC_PROVISIONING_EXISTING_EVIDENCE_H0_2026-08-16.md"
SOURCE_REPORT = REPO / "docs/reports/A90_WLAN_KERNEL_SOURCE_CONFIRMATION_H0_2026-08-16.md"
V3342_BUILD = REPO / "docs/reports/NATIVE_INIT_V3342_SOFTAP_S3_FWSOURCE_IFTYPE_PROBE_SOURCE_BUILD_2026-06-28.md"
V3342_LIVE = REPO / "docs/reports/NATIVE_INIT_V3342_SOFTAP_S3_FWSOURCE_IFTYPE_PROBE_LIVE_2026-06-28.md"
V2092 = REPO / "docs/archive/legacy/reports/NATIVE_INIT_V2092_MAC_FALSIFIER_TFTP_REDIRECT_2026-06-05.md"
CAPSULE = REPO / "docs/security/hardening/a90-wlan-vendor-property-ablation-2026-08-15/inventory/a90-h24-wlan-capsule-dependency-inventory-v1.json"
PACKAGE = REPO / "workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource_13272"
KERNEL = PACKAGE / "Kernel"
V3342_COMMIT = "3e7eed10bb23193d5cb5e84eff9e4fa4637a7fa0"
HELPER_REL = "workspace/public/src/native-init/helpers/a90_android_execns_probe.c"

V3342_RUNNER = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3342_softap_s3_fwsource_iftype_probe.py"
)


def flat(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8", errors="replace").split())


def frozen_v3342_helper() -> str:
    return subprocess.run(
        ["git", "show", f"{V3342_COMMIT}:{HELPER_REL}"],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def kernel_mac_setter_sites() -> list[str]:
    """Search every regular file without consulting ignore configuration."""
    pattern = re.compile(rb"cnss_utils_set_wlan_(?:derived_)?mac_address\s*\(")
    sites: list[str] = []
    for root in (KERNEL / "drivers", KERNEL / "include"):
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            base = Path(dirpath)
            dirnames[:] = sorted(
                name for name in dirnames if not (base / name).is_symlink()
            )
            for name in sorted(filenames):
                path = base / name
                if path.is_symlink() or not path.is_file():
                    continue
                for line_no, line in enumerate(path.read_bytes().splitlines(), 1):
                    if pattern.search(line):
                        sites.append(
                            f"{path}:{line_no}:{line.decode('utf-8', errors='replace')}"
                        )
    return sites


class A90WlanMacProvisioningExistingEvidenceDocsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = REPORT.read_text(encoding="utf-8")
        cls.report = " ".join(cls.raw.split())
        cls.source_staged = KERNEL.is_dir()

    def require_source(self) -> None:
        if not self.source_staged:
            self.skipTest(f"operator private kernel source is not staged: {KERNEL}")

    def test_source_report_points_to_the_followup_without_refreezing_goal(self) -> None:
        name = REPORT.name
        self.assertIn(name, SOURCE_REPORT.read_text(encoding="utf-8"))
        self.assertNotIn(name, (REPO / "GOAL_A90.md").read_text(encoding="utf-8"))
        self.assertIn("source-only statements below remain preserved", flat(SOURCE_REPORT))
        self.assertIn("does not retire `H0D01-H0D10`", self.report)
        self.assertIn("effective V3342 value", flat(SOURCE_REPORT))
        self.assertIn("remain unproved", flat(SOURCE_REPORT))

    def test_v3342_build_and_live_bind_the_same_candidate(self) -> None:
        build = V3342_BUILD.read_text(encoding="utf-8")
        live = V3342_LIVE.read_text(encoding="utf-8")
        for value in (
            "836f76249d578ef42e25a2d0c7b43cc3ef1d8db9efe5dabc6ee5ce13b10e5502",
            "fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef",
            "0.11.106",
            "v3342-softap-s3-fwsource-iftype-probe",
        ):
            self.assertIn(value, build)
            self.assertIn(value, live)
            self.assertIn(value, self.raw)

    def test_v3342_flag_chain_has_feeder_and_no_macloader_feature(self) -> None:
        flags = tuple(V3342_RUNNER.previous.wifi_route.configure_helper_flags())
        self.assertEqual(len(flags), 25)
        self.assertIn(
            "-DA90_WIFI_TEST_BOOT_SERVICE_OBJECT_POST_FW_READY_FWCLASS_BRIDGE=1",
            flags,
        )
        self.assertIn("-DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1", flags)
        self.assertIn(
            "-DA90_WIFI_TEST_BOOT_QCACLD_FIRMWARE_CLASS_FALLBACK_FEEDER=1",
            flags,
        )
        self.assertFalse(any("MACLOADER" in flag for flag in flags), flags)
        self.assertFalse(any("ANDROID_RMT_STORAGE_IDENTITY" in flag for flag in flags), flags)
        self.assertFalse(any("ANDROID_TFTP_SERVER_IDENTITY" in flag for flag in flags), flags)

        helper = frozen_v3342_helper()
        for macro in (
            "A90_WIFI_TEST_BOOT_MACLOADER_PRE_CNSS",
            "A90_WIFI_TEST_BOOT_MACLOADER_MAC_SOURCE_BRIDGE",
            "A90_WIFI_TEST_BOOT_MACLOADER_SYSCALL_TRACE",
            "A90_WIFI_TEST_BOOT_MACLOADER_PROPERTY_SERVICE_ACK",
        ):
            self.assertRegex(
                helper,
                re.compile(rf"#ifndef {macro}\s+#define {macro} 0", re.MULTILINE),
            )
        self.assertIn("if (macloader_pre_cnss)", helper)
        self.assertIn('"/vendor/bin/hw/macloader"', helper)

        unchanged = subprocess.run(
            [
                "git",
                "diff",
                "--quiet",
                V3342_COMMIT,
                "HEAD",
                "--",
                "workspace/public/src/scripts/revalidation/build_native_init_boot_v2237_supplicant_terminate_poll.py",
                "workspace/public/src/scripts/revalidation/build_native_init_boot_v3341_softap_s3_iftype_probe.py",
                "workspace/public/src/scripts/revalidation/build_native_init_boot_v3342_softap_s3_fwsource_iftype_probe.py",
            ],
            cwd=REPO,
            check=False,
        )
        self.assertEqual(unchanged.returncode, 0)

    def test_same_live_receipt_binds_ini_feed_and_working_wlan(self) -> None:
        live = V3342_LIVE.read_text(encoding="utf-8")
        for fact in (
            "source_policy=qcacld-fwsource-mounted-vendor-first",
            "request_0.firmware=wlan/qca_cld/WCNSS_qcom_cfg.ini",
            "request_0.source_rc=0",
            "request_0.source_bytes=13343",
            "request_0.fed=1",
            "wlan_pd_service_object_visible_trigger.wlan0_present=1",
            "ap_iftype_iface_created=1",
            "ap_iftype_cleanup_ok=1",
        ):
            self.assertIn(fact, live)
            self.assertIn(fact.replace("wlan_pd_service_object_visible_trigger.", ""), self.report)

    def test_v2092_is_kept_as_non_cooccurring_corroboration(self) -> None:
        old = V2092.read_text(encoding="utf-8")
        for fact in (
            "mac_info_read | False",
            "mac_addr_open | False",
            "mac_addr_write | False",
            "kernel_assign_line | False",
            "| V2091 | macloader-no-mac-addr-write | True | True | False | True | 1 | 1 | 0 | 6 | 0 | 0 | 0 |",
        ):
            self.assertIn(fact, old)
        self.assertIn("does not, by itself, prove the effective INI value", self.report)
        self.assertIn("unbound build-generation gap", self.report)

    def test_report_calibrates_prior_file_bytes_and_session_count(self) -> None:
        for claim in (
            "strong V3342 prior; effective and current values remain unproved",
            "does **not** prove the effective V3342 boolean false",
            "effective `mac_provision` boolean was false | **strong prior; unproved**",
            "current H24 vendor file is byte-identical to V3342 | **unproved**",
            "does not change the projected program from thirty sessions to twenty-nine",
            "prevents an additional macloader qualification/ablation unit",
            "The correct rule is **read existing bytes when exact current identity is later required; do not replace them**",
        ):
            self.assertIn(claim, self.report)
        self.assertNotIn('"role": "macloader"', CAPSULE.read_text(encoding="utf-8"))

    def test_wp2_4_effect_observation_is_same_run_and_fail_closed(self) -> None:
        for claim in (
            "`cnss_utils_mac_show()` reads the same persistent",
            "the getter does not consume or clear that state",
            "MAC_PROVISION_VALUE_UNRESOLVED",
            "MAC_PROVISION_FALSE_PROVED_EXACT_RUN",
            "MAC_PROVISION_TRUE_PROVED_EXACT_RUN",
            "an empty string caused by a read error is never “absent.”",
            "not a current D0 action and grants no D0 or live authority",
        ):
            self.assertIn(claim, self.report)

    def test_report_keeps_h0_and_grants_no_live_authority(self) -> None:
        self.assertIn("This is H0 research evidence only", self.report)
        self.assertIn("grants no D0, D1, F1, candidate", self.report)
        self.assertIn("Option C remains research-only", self.report)
        self.assertIn("Device, `/dev`, USB, network, S22+, and S20+ contacts are zero", self.report)
        self.assertIn("A stock firmware download is not a prerequisite", self.report)
        self.assertIn("`WP2-4` property observation schema", self.report)
        self.assertIn("grants no D0 authority", self.report)

    def test_matching_kernel_platform_mac_and_startup_order(self) -> None:
        self.require_source()
        defconfig = (KERNEL / "arch/arm64/configs/r3q_kor_single_defconfig").read_text(
            errors="replace"
        )
        pld = (
            KERNEL
            / "drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/pld/inc/pld_common.h"
        ).read_text(errors="replace")
        utils = (KERNEL / "drivers/net/wireless/cnss_utils/cnss_utils.c").read_text(
            errors="replace"
        )
        main = (
            KERNEL
            / "drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/src/wlan_hdd_main.c"
        ).read_text(errors="replace")
        ops = (
            KERNEL
            / "drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/src/wlan_hdd_driver_ops.c"
        ).read_text(errors="replace")

        self.assertIn("CONFIG_CNSS_UTILS=y", defconfig)
        self.assertIn("return cnss_utils_get_wlan_mac_address(dev, num);", pld)
        self.assertIn("priv = kzalloc(sizeof(*priv), GFP_KERNEL);", utils)

        init = main[main.index("static int hdd_platform_wlan_mac") :]
        init = init[: init.index("static int hdd_set_smart_chainmask_enabled")]
        self.assertIn("return -EINVAL;", init)
        self.assertIn("else if (hdd_ctx->config->mac_provision)", init)
        self.assertLess(
            init.index("ret = hdd_platform_wlan_mac(hdd_ctx);"),
            init.index("status = hdd_update_mac_config(hdd_ctx);"),
        )

        startup = main[main.index("int hdd_wlan_startup") :]
        startup = startup[: startup.index("QDF_STATUS hdd_psoc_create_vdevs")]
        self.assertIn("errno = hdd_initialize_mac_address(hdd_ctx);", startup)
        self.assertIn("goto unregister_wiphy;", startup)

        probe = ops[ops.index("static int __hdd_soc_probe") :]
        probe = probe[: probe.index("int hdd_soc_probe")]
        self.assertLess(probe.index("hdd_wlan_startup(hdd_ctx)"), probe.index("hdd_psoc_create_vdevs(hdd_ctx)"))

    def test_setter_search_does_not_hide_the_direct_debugfs_writer(self) -> None:
        self.require_source()
        lines = kernel_mac_setter_sites()
        provisioned_calls = [line for line in lines if "set_wlan_mac_address(" in line]
        derived_calls = [line for line in lines if "set_wlan_derived_mac_address(" in line]
        self.assertEqual(len(provisioned_calls), 4, provisioned_calls)
        self.assertEqual(len(derived_calls), 2, derived_calls)
        self.assertEqual(sum("drivers/soc/qcom/icnss.c" in line for line in provisioned_calls), 2)
        self.assertEqual(sum("cnss_utils.c" in line for line in derived_calls), 1)
        self.assertEqual(sum("include/net/cnss_utils.h" in line for line in derived_calls), 1)

        utils = (KERNEL / "drivers/net/wireless/cnss_utils/cnss_utils.c").read_text(
            errors="replace"
        )
        writer = utils[utils.index("static ssize_t cnss_utils_mac_write") :]
        writer = writer[: writer.index("static int cnss_utils_mac_show")]
        self.assertIn("dest_mac = &priv->wlan_mac_addr.mac_addr[0][0];", writer)
        self.assertIn("priv->wlan_mac_addr.no_of_mac_addr_set =", writer)
        self.assertLess(writer.index("no_of_mac_addr_set ="), writer.index("while (len--)"))
        self.assertIn("temp[0] = *mac_address++;", writer)
        self.assertIn("temp[1] = *mac_address++;", writer)
        self.assertIn("if (kstrtou8(temp, 16, &val))", writer)
        self.assertIn("*dest_mac++ = val;", writer)
        self.assertIn("count and valid prefix are not rolled back", self.report)

    def test_v3342_shared_pid_proc_root_leaves_opaque_writer_unproved(self) -> None:
        helper = frozen_v3342_helper()
        flags = tuple(V3342_RUNNER.previous.wifi_route.configure_helper_flags())

        self.assertIn(
            'mount("proc", paths->proc, "proc", MS_NOSUID | MS_NODEV | MS_NOEXEC, NULL)',
            helper,
        )
        self.assertIn('"/proc/1/root/mnt/vendor/firmware"', helper)
        self.assertIn('"/proc/1/root/vendor/firmware"', helper)
        self.assertIn(
            'return apply_android_init_root_identity_contract(prefix, "rmt_storage-init-root");',
            helper,
        )
        self.assertIn(
            'return apply_android_init_root_identity_contract(prefix, "tftp_server-init-root");',
            helper,
        )
        self.assertFalse(any("MACLOADER_MAC_SOURCE_BRIDGE" in flag for flag in flags), flags)
        self.assertIn("private root did not receive", self.report)
        self.assertIn("does not close `/proc/1/root`", self.report)
        self.assertIn("outer sysfs nor outer debugfs seeding is excluded", self.report)


if __name__ == "__main__":
    unittest.main()
