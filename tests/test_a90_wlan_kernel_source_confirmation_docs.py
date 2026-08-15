"""Pin the A90 WLAN matching-kernel-source confirmation and its limits.

The tracked report must remain useful when the operator's private source is not
staged. When the exact package is staged on this host, the tests additionally
bind the source facts that make the report more than a narrative summary.
"""

from __future__ import annotations

from pathlib import Path
import hashlib
import re
import unittest


REPO = Path(__file__).resolve().parents[1]
REPORT = REPO / "docs/reports/A90_WLAN_KERNEL_SOURCE_CONFIRMATION_H0_2026-08-16.md"
PRIOR = REPO / "docs/reports/A90_WLAN_KERNEL_SIDE_COMPOSITION_H0_2026-08-15.md"
ISOLATED_DESIGN = REPO / (
    "docs/plans/A90_HEADLESS_NATIVE_WIFI_ISOLATED_DEBIAN_DESIGN_2026-08-14.md"
)
PACKAGE = REPO / (
    "workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource_13272"
)
KERNEL = PACKAGE / "Kernel"
DEFCONFIG = KERNEL / "arch/arm64/configs/r3q_kor_single_defconfig"
RUNTIME_CONFIG = REPO / "workspace/private/outputs/a90-phase2a-kernel.tBOMsQ/v3404.config"


def flatten(text: str) -> str:
    return " ".join(text.split())


def config_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if raw.startswith("CONFIG_") and "=" in raw:
            key, value = raw.split("=", 1)
            values[key] = value
        elif raw.startswith("# CONFIG_") and raw.endswith(" is not set"):
            values[raw[2:-11]] = "n"
    return values


class KernelSourceConfirmationDocsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = REPORT.read_text(encoding="utf-8")
        cls.report = flatten(cls.raw)
        cls.source_staged = KERNEL.is_dir()

    def require_source(self) -> None:
        if not self.source_staged:
            self.skipTest(f"operator private kernel source is not staged: {KERNEL}")

    def test_prior_is_preserved_and_points_to_the_followup(self) -> None:
        prior = PRIOR.read_text(encoding="utf-8")
        self.assertIn(REPORT.name, prior)
        self.assertIn("remains the historical prior", prior)
        self.assertIn("append-only correction layer", self.report)

    def test_report_records_the_material_corrections(self) -> None:
        for claim in (
            "PD bring-up prior partially refuted",
            "eight PLD wrappers, not the entire exported `cnss_utils` ABI",
            "The earlier two-message enumeration was therefore too narrow",
            "the compiled server families are three, not two",
            "exact runtime endpoint unproved",
        ):
            self.assertIn(claim, self.report)

    def test_report_keeps_unproved_roles_unproved(self) -> None:
        self.assertIn("RFS roles remain unproved", self.report)
        self.assertIn("`macloader` necessity remains **unproved**", self.report)
        self.assertIn("Removability remains unproved", self.report)
        self.assertIn("No component is retired", self.report)

    def test_report_names_the_structural_qrtr_function_without_one_binary_overclaim(self) -> None:
        self.assertIn("some correct QRTR userspace name-service implementation is a hard dependency", self.report)
        self.assertIn("does not prove that this exact executable is the only possible implementation", self.report)
        self.assertIn("not a proved QRTR isolation boundary", self.report)
        self.assertIn("It does not gate ephemeral client transmission", self.report)
        self.assertIn("denied the entire `AF_QIPCRTR` socket family", self.report)
        self.assertIn("the remote workload must inherit the same whole-family deny", self.report)
        self.assertIn("`A90_REMOTE_WORKLOAD_QRTR_REMOTE_PROCESSOR_REACHABILITY`", self.report)
        self.assertIn("direct non-relaxable enforcement set is one indivisible invariant", self.report)
        self.assertIn("no native or preexisting socket FD", self.report)
        self.assertIn("They do **not** make the seccomp filter survive", self.report)
        self.assertIn("this report alone does not do it", self.report)

        design = flatten(ISOLATED_DESIGN.read_text(encoding="utf-8"))
        for control in (
            "bootstrap sets `PR_SET_NO_NEW_PRIVS`",
            "filter is inherited across exec and descendants and cannot be removed",
            "Direct `socket()` is allowed only for `AF_INET`",
            "AF_QIPCRTR/QRTR",
            "AF_NETLINK (including kobject uevent)",
            "compat `socketcall` entry is denied completely",
            "no native/preexisting socket FD reaches the service identity",
            "`unshare`, `setns`, `mknod`, and `mknodat`; denies `clone3` completely",
            "no `CLONE_NEW*` bit or unknown service flag",
        ):
            self.assertIn(control, design)
        self.assertIn("AF_INET-only direct-socket allowlist", self.report)

    def test_report_keeps_h0_and_grants_no_authority(self) -> None:
        self.assertIn("This is H0 research evidence only", self.report)
        self.assertIn("grants no D0, D1, F1, candidate", self.report)
        self.assertIn("Option C remains research-only", self.report)
        self.assertIn("Device, `/dev`, USB, network, S22+, and S20+ contacts are zero", self.report)

    def test_manifest_and_config_provenance_match_when_staged(self) -> None:
        self.require_source()
        manifest = (PACKAGE / "MANIFEST.sha256").read_text(encoding="utf-8")
        expected = {
            "SM-A908N_KOR_12_Opensource.zip": "d0a6c9f29387a6ba9d5fe0ad8c1a1e79576f4d0c0bc463394f1cd70389897a3b",
            "Kernel.tar.gz": "403fdc49f086d238c01a796c390083c3c47c1754c218e228f29b55cc7c35d554",
            "Platform.tar.gz": "8bdbc5066ef95c3b823328fc6e8e30af2b0d827eeec7125c80ed8f162f475c27",
        }
        for name, digest in expected.items():
            self.assertIn(f"{digest}  {name}", manifest)
            self.assertIn(digest, self.raw)

        self.assertTrue(RUNTIME_CONFIG.is_file(), str(RUNTIME_CONFIG))
        source = config_values(DEFCONFIG)
        runtime = config_values(RUNTIME_CONFIG)
        self.assertEqual(len(source), 5704)
        self.assertEqual(len(runtime), 5724)
        self.assertEqual(set(source) - set(runtime), set())
        self.assertEqual(
            {key: (value, runtime[key]) for key, value in source.items() if runtime[key] != value},
            {},
        )
        self.assertEqual(
            hashlib.sha256(DEFCONFIG.read_bytes()).hexdigest(),
            "3d90a83d61a7a1873249642f7657c572e06f91a61bc3e5b737758f08ec765216",
        )

    def test_icnss_base_lookup_and_recovery_order_match_source(self) -> None:
        self.require_source()
        qmi = (KERNEL / "drivers/soc/qcom/icnss_qmi.c").read_text(errors="replace")
        icnss = (KERNEL / "drivers/soc/qcom/icnss.c").read_text(errors="replace")
        self.assertRegex(
            qmi,
            re.compile(
                r"qmi_add_lookup\(&priv->qmi,\s*WLFW_SERVICE_ID_V01,\s*"
                r"WLFW_SERVICE_VERS_V01,\s*0\)",
                re.MULTILINE,
            ),
        )
        register = icnss.index("ret = icnss_register_fw_service(priv);")
        fatal = icnss.index("goto out_destroy_wq;", register)
        recovery = icnss.index("icnss_enable_recovery(priv);", fatal)
        self.assertLess(register, fatal)
        self.assertLess(fatal, recovery)
        self.assertNotIn("ret = icnss_enable_recovery(priv);", icnss[register : recovery + 50])
        for token in ("RECOVERY_DISABLE", "SSR_ONLY", "PDR_ONLY"):
            self.assertIn(token, icnss)

        locator = (KERNEL / "drivers/soc/qcom/service-locator.c").read_text(
            errors="replace"
        )
        self.assertIn("static u32 locator_status = LOCATOR_NOT_PRESENT;", locator)
        self.assertIn("schedule_work(&pqw->pd_loc_work);", locator)
        self.assertIn("defaults to `LOCATOR_NOT_PRESENT`", self.report)

    def test_qrtr_userspace_name_service_requirement_matches_source(self) -> None:
        self.require_source()
        kconfig = (KERNEL / "net/qrtr/Kconfig").read_text(errors="replace")
        makefile = (KERNEL / "net/qrtr/Makefile").read_text(errors="replace")
        qmi = (KERNEL / "drivers/soc/qcom/qmi_interface.c").read_text(errors="replace")
        qrtr = (KERNEL / "net/qrtr/qrtr.c").read_text(errors="replace")
        self.assertIn("a userspace daemon is required", kconfig)
        self.assertNotRegex(makefile, re.compile(r"(^|[-_])ns\.o", re.MULTILINE))
        self.assertIn("NEW_SERVER and DEL_SERVER control messages", qmi)
        self.assertIn("qmi_send_new_lookup(qmi, svc);", qmi)
        self.assertIn("sock_create_kern(&init_net, AF_QIPCRTR", qmi)
        self.assertIn("static DEFINE_IDR(qrtr_ports);", qrtr)
        self.assertIn("static LIST_HEAD(qrtr_all_epts);", qrtr)
        self.assertIn("#define AID_VENDOR_QRTR\tKGIDT_INIT(2906)", qrtr)
        self.assertIn("in_egroup_p(AID_VENDOR_QRTR)", qrtr)

        create = qrtr[qrtr.index("static int qrtr_create") :]
        create = create[: create.index("static const struct nla_policy")]
        self.assertIn("sk_alloc(net, AF_QIPCRTR", create)
        self.assertIn("ipc->us.sq_node = qrtr_local_nid;", create)
        self.assertNotIn("capable(", create)
        self.assertNotIn("ns_capable(", create)

        send = qrtr[qrtr.index("static int qrtr_sendmsg") :]
        send = send[: send.index("static int qrtr_resume_tx")]
        self.assertIn("qrtr_autobind(sock)", send)
        self.assertIn("qrtr_node_lookup(addr->sq_node)", send)
        self.assertIn("qrtr_node_enqueue", send)
        self.assertNotIn("capable(", send)

        assign = qrtr[qrtr.index("static int qrtr_port_assign") :]
        assign = assign[: assign.index("/* Reset all non-control ports */")]
        self.assertLess(assign.index("if (!*port)"), assign.index("capable(CAP_NET_ADMIN)"))
        ephemeral = assign[assign.index("if (!*port)") : assign.index("} else if")]
        self.assertNotIn("capable(", ephemeral)
        self.assertIn("idr_alloc_cyclic", ephemeral)

    def test_qmi_server_correction_matches_selected_config(self) -> None:
        self.require_source()
        call_sites = (
            "drivers/platform/msm/ipa/ipa_v2/ipa_qmi_service.c",
            "drivers/platform/msm/ipa/ipa_v3/ipa_qmi_service.c",
            "drivers/soc/qcom/memshare/msm_memshare.c",
            "sound/usb/usb_audio_qmi_svc.c",
        )
        for rel in call_sites:
            self.assertIn("qmi_add_server(", (KERNEL / rel).read_text(errors="replace"), rel)
        self.assertNotIn(
            "qmi_add_server(",
            (KERNEL / "drivers/soc/qcom/icnss_qmi.c").read_text(errors="replace"),
        )
        values = config_values(DEFCONFIG)
        self.assertEqual(values["CONFIG_IPA3"], "y")
        self.assertEqual(values["CONFIG_IPA"], "n")
        self.assertEqual(values["CONFIG_MEM_SHARE_QMI_SERVICE"], "y")
        self.assertEqual(values["CONFIG_SND_USB_AUDIO_QMI"], "y")

    def test_mac_provisioning_and_fatal_ini_gate_match_source(self) -> None:
        self.require_source()
        icnss = (KERNEL / "drivers/soc/qcom/icnss.c").read_text(errors="replace")
        config = (
            KERNEL
            / "drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/inc/hdd_config.h"
        ).read_text(errors="replace")
        main = (
            KERNEL
            / "drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/src/wlan_hdd_main.c"
        ).read_text(errors="replace")
        misc = (
            KERNEL
            / "drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/inc/wlan_hdd_misc.h"
        ).read_text(errors="replace")
        self.assertIn("__ATTR(mac_addr, 0220, NULL, store_mac_addr)", icnss)
        self.assertRegex(
            config,
            re.compile(
                r"#define CFG_ENABLE_MAC_PROVISION CFG_INI_BOOL\(\s*\\\n"
                r"\s*\"enable_mac_provision\",\s*\\\n\s*0,",
                re.MULTILINE,
            ),
        )
        self.assertIn("hdd_initialize_mac_address", main)
        self.assertIn("status = cfg_parse(WLAN_INI_FILE);", main)
        self.assertIn("goto err_free_config;", main)
        self.assertIn("WCNSS_qcom_cfg.ini", misc)
        self.assertNotIn("WCNSS_qcom_cfg.ini", "\n".join(p.name for p in PACKAGE.rglob("*")))

    def test_genl_correction_and_mac_parser_defect_are_source_backed(self) -> None:
        self.require_source()
        wlan = KERNEL / "drivers/net/wireless/qualcomm/wcn39xx"
        files = (
            wlan / "qca-wifi-host-cmn/os_if/linux/wifi_pos/src/os_if_wifi_pos.c",
            wlan / "qca-wifi-host-cmn/utils/fwlog/dbglog_host.c",
            wlan / "qca-wifi-host-cmn/utils/ptt/src/wlan_ptt_sock_svc.c",
            wlan / "qcacld-3.0/core/hdd/src/wlan_hdd_spectralscan.c",
        )
        combined = "\n".join(path.read_text(errors="replace") for path in files)
        for message_id in (
            "WLAN_NL_MSG_OEM",
            "WLAN_NL_MSG_CNSS_DIAG",
            "ANI_NL_MSG_PUMAC",
            "ANI_NL_MSG_PTT",
            "WLAN_NL_MSG_SPECTRAL_SCAN",
        ):
            self.assertIn(message_id, combined)

        icnss = (KERNEL / "drivers/soc/qcom/icnss.c").read_text(errors="replace")
        parser = icnss[icnss.index("static ssize_t store_mac_addr") :]
        parser = parser[: parser.index("static ssize_t show_verinfo")]
        self.assertEqual(parser.count("(unsigned int*)&mac_from_macloader["), 6)
        self.assertIn("return 0;", parser)
        self.assertIn("must not copy this parser", self.report)
        self.assertIn('kobject_create_and_add("wifi", NULL)', icnss)
        self.assertIn("exact object corrupted by those three out-of-bounds bytes", self.report)
        self.assertIn("remotely reachable workload still receives no `/sys/wifi/mac_addr`", self.report)

        design = flatten(ISOLATED_DESIGN.read_text(encoding="utf-8"))
        self.assertIn("empty read-only synthetic tmpfs at `/sys`", design)
        self.assertIn("already gives the workload an empty read-only synthetic `/sys`", self.report)

        utils = (KERNEL / "drivers/net/wireless/cnss_utils/cnss_utils.c").read_text(
            errors="replace"
        )
        debugfs_parser = utils[utils.index("static ssize_t cnss_utils_mac_write") :]
        debugfs_parser = debugfs_parser[: debugfs_parser.index("static int cnss_utils_mac_show")]
        self.assertIn("#define MAX_NO_OF_MAC_ADDR 4", utils)
        self.assertIn("u8 mac_addr[MAX_NO_OF_MAC_ADDR][ETH_ALEN];", utils)
        self.assertIn('char temp[3] = "";', debugfs_parser)
        self.assertIn("len = strlen(mac_address);", debugfs_parser)
        self.assertIn("len -= MAC_PREFIX_LEN;", debugfs_parser)
        self.assertIn("while (len--)", debugfs_parser)
        self.assertIn("temp[0] = *mac_address++;", debugfs_parser)
        self.assertIn("temp[1] = *mac_address++;", debugfs_parser)
        self.assertLess(
            debugfs_parser.index("no_of_mac_addr_set = len / (ETH_ALEN * 2)"),
            debugfs_parser.index("while (len--)"),
        )
        self.assertLess(
            debugfs_parser.index("if (kstrtou8(temp, 16, &val))"),
            debugfs_parser.index("*dest_mac++ = val"),
        )
        self.assertIn("The first `6N` iterations", self.report)
        self.assertIn("`kstrtou8()` deterministically fails", self.report)
        self.assertIn("every syntactically valid provisioned or derived token mutates", self.report)
        self.assertIn("No destination overflow is claimed for this debugfs path", self.report)

    def test_mac_lookup_signature_and_nonreversion_are_source_backed(self) -> None:
        self.require_source()
        utils = (KERNEL / "drivers/net/wireless/cnss_utils/cnss_utils.c").read_text(
            errors="replace"
        )
        main = (
            KERNEL
            / "drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/src/wlan_hdd_main.c"
        ).read_text(errors="replace")

        self.assertRegex(
            utils,
            re.compile(
                r"enum mac_type\s*\{\s*CNSS_MAC_PROVISIONED,\s*CNSS_MAC_DERIVED,",
                re.MULTILINE,
            ),
        )
        getter = utils[utils.index("static u8 *get_wlan_mac_address") :]
        getter = getter[: getter.index("u8 *cnss_utils_get_wlan_mac_address")]
        self.assertIn('pr_err("WLAN MAC address is not set, type %d\\n", type);', getter)
        self.assertLess(getter.index("if (!addr->no_of_mac_addr_set)"), getter.index("*num = 0;"))

        setter = utils[utils.index("static int set_wlan_mac_address") :]
        setter = setter[: setter.index("int cnss_utils_set_wlan_mac_address")]
        self.assertLess(
            setter.index("if (addr->no_of_mac_addr_set)"),
            setter.index("addr->no_of_mac_addr_set = no_of_mac_addr;"),
        )
        guarded = setter[
            setter.index("if (addr->no_of_mac_addr_set)") :
            setter.index("addr->no_of_mac_addr_set = no_of_mac_addr;")
        ]
        self.assertIn("return 0;", guarded)
        self.assertNotIn("ether_addr_copy", guarded)

        platform = main[main.index("static int hdd_platform_wlan_mac") :]
        platform = platform[: platform.index("static int hdd_update_mac_addr_to_fw")]
        self.assertLess(
            platform.index("hdd_get_platform_wlan_mac_buff"),
            platform.index("hdd_get_platform_wlan_derived_mac_buff"),
        )
        self.assertIn("return -EINVAL;", platform)
        self.assertIn("static void __exit cnss_utils_exit", utils)
        self.assertEqual(config_values(DEFCONFIG)["CONFIG_CNSS_UTILS"], "y")

        for claim in (
            "exact type-0 absence line",
            "does **not** copy the",
            "**non-reversion**",
            "It is not **set-once**",
            "debugfs absence read remains corroboration",
        ):
            self.assertIn(claim, self.report)

    def test_cnss_daemon_named_kernel_interactions_are_not_base_lookup(self) -> None:
        self.require_source()
        wlan = KERNEL / "drivers/net/wireless/qualcomm/wcn39xx"
        sources = (
            wlan / "qca-wifi-host-cmn/utils/nlink/inc/wlan_nlink_common.h",
            wlan / "qcacld-3.0/core/hdd/src/wlan_hdd_napi.c",
            wlan / "qcacld-3.0/core/hdd/inc/hdd_dp_cfg.h",
            wlan
            / "qcacld-3.0/os_if/interop_issues_ap/src/wlan_cfg80211_interop_issues_ap.c",
        )
        combined = "\n".join(path.read_text(errors="replace") for path in sources)
        for token in ("cpu_map", "perfd", "tcp_limit_output_bytes", "interop issues ap"):
            self.assertIn(token, combined)
        self.assertIn("performance/policy and compatibility paths", self.report)
        self.assertIn("proprietary executable may perform transactions not named", self.report)


if __name__ == "__main__":
    unittest.main()
