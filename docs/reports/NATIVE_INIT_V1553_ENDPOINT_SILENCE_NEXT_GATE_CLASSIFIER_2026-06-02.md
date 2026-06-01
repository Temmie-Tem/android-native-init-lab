# Native Init V1553 Endpoint Silence Next Gate Classifier

## Summary

- Cycle: `V1553`
- Type: host-only endpoint-silence next-gate classifier
- Decision: `v1553-next-gate-android-good-power-trace-reference`
- Result: `PASS`
- Reason: native AP-side RC1 power/refclk/PERST is proven and endpoint IRQs stay silent; PM/eSoC and MHI leads are already classified, so the next useful gate is an Android-good regulator/clk/gpio/irq trace reference for the successful first-L0 window
- Evidence: `tmp/wifi/v1553-endpoint-silence-next-gate-classifier/manifest.json`

V1553 reconciles V1552 with the prior PM/eSoC, sysfs-enumerate, Android-good, and MHI-position classifiers. It performs no device command or live mutation.

## Checks

| check | value |
| --- | --- |
| v1552_pass | True |
| v1552_ap_side_power_refclk_perst | True |
| v1552_endpoint_irq_silent | True |
| v1552_no_l0 | True |
| v1552_no_mhi_wlfw_wlan0 | True |
| v1551_gdsc_timing_gap_closed | True |
| v1496_provider_plus_rc1_already_no_l0 | True |
| v1530_android_good_lower_reaches_wlan | True |
| v1530_rc1_text_opaque | True |
| v1530_mhi_pm_resume_downstream | True |
| v1534_current_pm_route_reaches_powerup | True |
| v1540_endpoint_readiness_gap | True |
| source_pcie_enable_order_visible | True |
| source_mhi_pm_resume_downstream_visible | True |

## Native Fixed Point

| field | value |
| --- | --- |
| V1552 decision | v1552-ap-side-power-refclk-perst-confirmed-endpoint-silent-no-l0 |
| V1552 target counts | {"any_regulator": 52, "gpio102_set0": 2, "gpio102_set1": 1, "gpio104": 0, "gpio135": 0, "gpio142": 0, "irq_any": 0, "irq_mdm_errfatal": 0, "irq_mdm_status": 0, "irq_pcie_wake": 0, "pcie1_clock": 70, "pcie1_gdsc_disable": 2, "pcie1_gdsc_enable": 2, "pipe_clk_enable": 2, "pm8150_or_vdd": 40, "refclk_enable": 6} |
| V1552 interrupt delta | {"mdm_errfatal": 0, "mdm_status": 0, "pcie_wake": 0} |
| V1552 link/L0/MHI/WLFW | True / False / False / False |
| V1496 provider/RC1/L0/linkfail | True / True / False / True |

## Source Anchors

| group | source | line |
| --- | --- | --- |
| pcie_enable | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c:84 | #define PCIE20_PARF_LTSSM              0x1B0 |
| pcie_enable | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c:1074 | static bool is_esoc0_online(struct msm_pcie_dev_t *dev) |
| pcie_enable | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c:3591 | static int msm_pcie_vreg_init(struct msm_pcie_dev_t *dev) |
| pcie_enable | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c:3707 | static int msm_pcie_clk_init(struct msm_pcie_dev_t *dev) |
| pcie_enable | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c:3887 | static int msm_pcie_pipe_clk_init(struct msm_pcie_dev_t *dev) |
| pcie_enable | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c:4606 | static int msm_pcie_enable(struct msm_pcie_dev_t *dev, u32 options) |
| pcie_enable | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c:4632 | PCIE_INFO(dev, "PCIe: Assert the reset of endpoint of RC%d.\n", |
| pcie_enable | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c:4642 | ret = msm_pcie_vreg_init(dev); |
| pcie_enable | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c:4649 | ret = msm_pcie_clk_init(dev); |
| pcie_enable | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c:4716 | ret = msm_pcie_pipe_clk_init(dev); |
| mhi_position | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/bus/mhi/controllers/mhi_arch_qcom.c:91 | struct pci_dev *pci_dev = mhi_dev->pci_dev; |
| mhi_position | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/bus/mhi/controllers/mhi_arch_qcom.c:171 | struct pci_dev *pci_dev = mhi_dev->pci_dev; |
| mhi_position | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/bus/mhi/controllers/mhi_arch_qcom.c:194 | static int mhi_arch_esoc_ops_power_on(void *priv, unsigned int flags) |
| mhi_position | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/bus/mhi/controllers/mhi_arch_qcom.c:198 | struct pci_dev *pci_dev = mhi_dev->pci_dev; |
| mhi_position | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/bus/mhi/controllers/mhi_arch_qcom.c:222 | ret = msm_pcie_pm_control(MSM_PCIE_RESUME, pci_dev->bus->number, |
| mhi_position | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/bus/mhi/controllers/mhi_arch_qcom.c:230 | ret = mhi_pci_probe(pci_dev, NULL); |
| mhi_position | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/bus/mhi/controllers/mhi_arch_qcom.c:240 | struct pci_dev *pci_dev = mhi_dev->pci_dev; |
| mhi_position | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/bus/mhi/controllers/mhi_arch_qcom.c:259 | struct pci_dev *pci_dev = mhi_dev->pci_dev; |
| mhi_position | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/bus/mhi/controllers/mhi_arch_qcom.c:399 | pm_runtime_allow(&mhi_dev->pci_dev->dev); |
| mhi_position | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/bus/mhi/controllers/mhi_arch_qcom.c:427 | struct pci_dev *pci_dev = mhi_dev->pci_dev; |
| mhi_probe | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/bus/mhi/controllers/mhi_qcom.c:473 | static int mhi_qcom_power_up(struct mhi_controller *mhi_cntrl) |
| mhi_probe | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/bus/mhi/controllers/mhi_qcom.c:534 | ret = mhi_qcom_power_up(mhi_cntrl); |
| mhi_probe | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/bus/mhi/controllers/mhi_qcom.c:637 | ret = mhi_qcom_power_up(mhi_cntrl); |
| mhi_probe | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/bus/mhi/controllers/mhi_qcom.c:837 | int mhi_pci_probe(struct pci_dev *pci_dev, |
| mhi_probe | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/bus/mhi/controllers/mhi_qcom.c:873 | ret = mhi_qcom_power_up(mhi_cntrl); |

## Not Next

- another blind sysfs/debugfs enumerate retry
- MHI PM-resume as first-L0 trigger
- firmware/WLFW/BDF/scan/connect before native L0
- PM-service dependency repair as the primary blocker unless current route regresses
- PMIC/GPIO/GDSC direct writes or global PCI rescan

## Recommended V1554 Gate

| field | value |
| --- | --- |
| kind | Android-good bounded tracefs reference |
| events | regulator.regulator_enable/disable/set_voltage<br>clk.clk_prepare/enable/disable<br>gpio.gpio_value/direction<br>irq.irq_handler_entry/exit<br>printk.console if volume is bounded |
| window | from pm-service/modem or first lower-Wi-Fi marker through WLFW/BDF/wlan0, with rollback to native |
| compare against | V1552 native pcie_1_gdsc/refclk/pipe/PERST timestamps<br>WAKE/status/errfatal IRQ deltas<br>L0/MHI/WLFW/BDF/wlan0 markers |

## Safety

| field | value |
| --- | --- |
| host_only | True |
| device_command_executed | False |
| tracefs_write_executed | False |
| sysfs_debugfs_write_executed | False |
| wifi_hal_start_executed | False |
| scan_connect_executed | False |
| credential_use_executed | False |
| dhcp_route_executed | False |
| external_ping_executed | False |
| pmic_gpio_gdsc_write_executed | False |
| flash_executed | False |
| partition_write_executed | False |

## Next

V1554 Android-good tracefs reference: capture regulator/clk/gpio/irq events around the first successful RC1 L0/WLFW window, then compare against V1552 native trace before any new native mutation
