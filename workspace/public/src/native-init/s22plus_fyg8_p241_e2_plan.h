#ifndef S22PLUS_FYG8_P241_E2_PLAN_H
#define S22PLUS_FYG8_P241_E2_PLAN_H

#ifndef S22PLUS_O2_PLAN_TYPES_DEFINED
#define S22PLUS_O2_PLAN_TYPES_DEFINED
struct s22plus_o2_module_plan_entry {
    const char *filename;
    const char *runtime_name;
    const char *params;
};

struct s22plus_o2_bind_gate_entry {
    unsigned int order;
    const char *id;
    const char *kind;
    const char *path;
};
#endif

static const struct s22plus_o2_module_plan_entry s22plus_o2_module_plan[] = {
    {"qcom_hwspinlock.ko", "qcom_hwspinlock", ""},
    {"smem.ko", "smem", ""},
    {"minidump.ko", "minidump", ""},
    {"qcom-scm.ko", "qcom_scm", ""},
    {"qcom_wdt_core.ko", "qcom_wdt_core", ""},
    {"gh_virt_wdt.ko", "gh_virt_wdt", ""},
    {"cmd-db.ko", "cmd_db", ""},
    {"debug-regulator.ko", "debug_regulator", ""},
    {"icc-debug.ko", "icc_debug", ""},
    {"iommu-logger.ko", "iommu_logger", ""},
    {"phy-generic.ko", "phy_generic", ""},
    {"proxy-consumer.ko", "proxy_consumer", ""},
    {"gdsc-regulator.ko", "gdsc_regulator", ""},
    {"clk-qcom.ko", "clk_qcom", ""},
    {"clk-dummy.ko", "clk_dummy", ""},
    {"gcc-waipio.ko", "gcc_waipio", ""},
    {"qcom_iommu_util.ko", "qcom_iommu_util", ""},
    {"qnoc-qos.ko", "qnoc_qos", ""},
    {"sec_class.ko", "sec_class", ""},
    {"abc.ko", "abc", ""},
    {"sec_debug.ko", "sec_debug", ""},
    {"secure_buffer.ko", "secure_buffer", ""},
    {"qcom_ipc_logging.ko", "qcom_ipc_logging", ""},
    {"qcom-pdc.ko", "qcom_pdc", ""},
    {"pinctrl-msm.ko", "pinctrl_msm", ""},
    {"pinctrl-waipio.ko", "pinctrl_waipio", ""},
    {"qcom_rpmh.ko", "qcom_rpmh", ""},
    {"clk-rpmh.ko", "clk_rpmh", ""},
    {"rpmh-regulator.ko", "rpmh_regulator", ""},
    {"icc-bcm-voter.ko", "icc_bcm_voter", ""},
    {"qrtr.ko", "qrtr", ""},
    {"socinfo.ko", "socinfo", ""},
    {"icc-rpmh.ko", "icc_rpmh", ""},
    {"qnoc-waipio.ko", "qnoc_waipio", ""},
    {"arm_smmu.ko", "arm_smmu", ""},
    {"qmi_helpers.ko", "qmi_helpers", ""},
    {"eud.ko", "eud", ""},
    {"phy-msm-ssusb-qmp.ko", "phy_msm_ssusb_qmp", ""},
    {"repeater.ko", "repeater", ""},
    {"redriver.ko", "redriver", ""},
    {"usb_notify_layer.ko", "usb_notify_layer", ""},
    {"qcom_glink.ko", "qcom_glink", ""},
    {"qcom_glink_smem.ko", "qcom_glink_smem", ""},
    {"qcom_smd.ko", "qcom_smd", ""},
    {"rproc_qcom_common.ko", "rproc_qcom_common", ""},
    {"pdr_interface.ko", "pdr_interface", ""},
    {"pmic_glink.ko", "pmic_glink", ""},
    {"switch_class.ko", "switch_class", ""},
    {"common_muic.ko", "common_muic", ""},
    {"vbus_notifier.ko", "vbus_notifier", ""},
    {"if_cb_manager.ko", "if_cb_manager", ""},
    {"pdic_notifier_module.ko", "pdic_notifier_module", ""},
    {"usb_typec_manager.ko", "usb_typec_manager", ""},
    {"usb_f_ss_mon_gadget.ko", "usb_f_ss_mon_gadget", ""},
    {"phy-msm-snps-hs.ko", "phy_msm_snps_hs", ""},
    {"phy-msm-snps-eusb2.ko", "phy_msm_snps_eusb2", ""},
    {"qc_usb_audio.ko", "qc_usb_audio", ""},
    {"dwc3-msm.ko", "dwc3_msm", ""},
    {"ucsi_glink.ko", "ucsi_glink", ""},
};

#define S22PLUS_O2_MODULE_PLAN_COUNT \
    (sizeof(s22plus_o2_module_plan) / sizeof(s22plus_o2_module_plan[0]))

static const struct s22plus_o2_bind_gate_entry s22plus_o2_bind_gates[] = {
    {1U, "hwspinlock", "driver-bind-symlink", "/sys/bus/platform/drivers/qcom_hwspinlock/soc:hwlock"},
    {2U, "smem", "driver-bind-symlink", "/sys/bus/platform/drivers/qcom-smem/soc:qcom,smem"},
    {3U, "cmd-db", "driver-bind-symlink", "/sys/bus/platform/drivers/cmd-db/80860000.aop_cmd_db_region"},
    {4U, "rpmh", "driver-bind-symlink", "/sys/bus/platform/drivers/rpmh/af20000.rsc"},
    {5U, "gcc-waipio", "driver-bind-symlink", "/sys/bus/platform/drivers/gcc-waipio/100000.clock-controller"},
    {6U, "ssusb", "driver-bind-symlink", "/sys/bus/platform/drivers/msm-dwc3/a600000.ssusb"},
    {7U, "dwc3-core", "driver-bind-symlink", "/sys/bus/platform/drivers/dwc3/a600000.dwc3"},
    {8U, "udc", "class-device", "/sys/class/udc/a600000.dwc3"},
};

#define S22PLUS_O2_BIND_GATE_COUNT \
    (sizeof(s22plus_o2_bind_gates) / sizeof(s22plus_o2_bind_gates[0]))

#endif
