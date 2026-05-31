# Native Init V1357 pcie1 RC Control Surface Verifier Live

## Summary

- Cycle: `V1357`
- Type: live read-only verifier
- Decision: `v1357-pcie1-platform-surface-only`
- Result: PASS
- Script: `scripts/revalidation/native_wifi_pcie1_rc_control_surface_verifier_live_v1357.py`
- Evidence:
  - `tmp/wifi/v1357-pcie1-rc-control-surface-verifier-live/manifest.json`
  - `tmp/wifi/v1357-pcie1-rc-control-surface-verifier-live/summary.md`
  - `tmp/wifi/v1357-pcie1-rc-control-surface-verifier-live/native/`

## Decision

pcie1 platform surface is visible, but no RC1-safe userspace enumerate surface is proven

## Key Observations

| field | value |
| --- | --- |
| debugfs_mounted | False |
| pcie_platform_seen | True |
| pcie_driver_bound | True |
| pcie_driver_readlink | ../../../../bus/platform/drivers/pci-msm |
| cnss_debugfs_seen | False |
| cnss_dev_boot_present | False |
| dev_boot_usage_enumerate | False |
| dt_wlan_rc_path_count | 1 |
| dt_pcie_parent_path_count | 1 |
| dt_dynamic_prop_read_count | 2 |
| dt_rc1_hex_seen | False |
| dt_rc0_hex_seen | True |
| pcie1_gdsc_seen | False |
| pcie1_gdsc_nonzero | False |
| pcie1_clk_seen | False |
| gpio102_perst_seen | False |
| pci_device_count | 0 |
| mhi_device_count | 0 |
| mhi_devnode_seen | False |
| post_selftest_fail0 | True |
| forbidden_runtime_clean | True |

## Focused Interrupt Lines

- `162:          0          0          0          0          0          0          0          0  msmgpio-dc   8 Edge      TE_GPIO`
- `178:          0          0          0          0          0          0          0          0  msmgpio-dc  30 Edge      pn547`
- `190:          0          0          0          0          0          0          0          0  msmgpio-dc  42 Edge      UB_CON_DET`
- `204:          0          0          0          0          0          0          0          0  msmgpio-dc  53 Edge      mdm errfatal`
- `232:          0          0          0          0          0          0          0          0  msmgpio-dc  87 Level     mms_ts`
- `240:          0          0          0          0          0          0          0          0  msmgpio-dc  93 Edge      flip_cover`
- `244:          0          0          0          0          0          0          0          0  msmgpio-dc  96 Edge      8804000.sdhci cd`
- `252:          0          0          0          0          0          0          0          0  msmgpio-dc 104 Edge      msm_pcie_wake`
- `258:          0          0          0          0          0          0          0          0  msmgpio-dc 113 Edge      pn547_clk_req`
- `268:          0          0          0          0          0          0          0          0  msmgpio-dc 120 Edge      jig-irq`
- `278:          0          0          0          0          0          0          0          0  msmgpio-dc 125 Edge      sx9360_irq`
- `286:          0          0          0          0          0          0          0          0  msmgpio-dc 134 Level     pca9468`
- `290:          0          0          0          0          0          0          0          0  msmgpio-dc 142 Edge      mdm status`
- `398:          0          0          0          0          0          0          0          0   PDC-GIC 142 Level     arm-smmu-context-fault`
- `476:          0          0          0          0          0          0          0          0   PDC-GIC 396 Edge      error_irq`
- `501:          0          0          0          0          0          0          0          0     smp2p   1 Edge      error_ready_interrupt`
- `506:          0          0          0          0          0          0          0          0     smp2p   1 Edge      error_ready_interrupt`
- `511:          0          0          0          0          0          0          0          0     smp2p   1 Edge      error_ready_interrupt`
- `515:          0          0          0          0          0          0          0          0     smp2p   1 Edge      error_ready_interrupt`
- `IPI0:      3208       9527      11917      11477        938         53       1087        346       Rescheduling interrupts`
- `IPI1:         4        129        118        112        114        114        113        114       Function call interrupts`
- `IPI2:         0          0          0          0          0          0          0          0       CPU stop interrupts`
- `IPI3:         0          0          0          0          0          0          0          0       CPU stop (for crash dump) interrupts`
- `IPI4:         0          0          0          0          0          0          0          0       Timer broadcast interrupts`
- `IPI5:     47448        995       1356       1769        586          7         68        246       IRQ work interrupts`
- `IPI6:         0          0          0          0          0          0          0          0       CPU wake-up interrupts`
- `Err:          0`

## Focused dmesg Lines

- `[32m[    0.000000] [33m[0[0m:        swapper:    0] OF: reserved mem: initialized node mhi_region, compatible id shared-dma-pool`
- `[32m[    0.440932] [33m[7[31m:      swapper/0:    1] register_client_adhoc:Client handle 12 pcie1`
- `[32m[    0.441242] [33m[7[31m:      swapper/0:    1] msm_pcie_get_resources: PCIe: RC1 can't get tcsr resource.`
- `[32m[    0.441291] [33m[7[31m:      swapper/0:    1] msm_pcie_probe: PCIe: RC1 could not get pinctrl sleep state`
- `[32m[    0.872589] [33m[0[31m:      swapper/0:    1] ext-mdm soc:qcom,mdm3: Cannot config MDM_PMIC_PWR_STATUS gpio`
- `[32m[    0.872693] [33m[0[31m:      swapper/0:    1] ext-mdm soc:qcom,mdm3: mdm_configure_ipc set AP2MDM_ERRFATAL2 as a AP2MDM_ERRFATAL`

## Captures

| name | ok | rc | status | file |
| --- | --- | --- | --- | --- |
| version | True | 0 | ok | native/version.txt |
| status | True | 0 | ok | native/status.txt |
| selftest | True | 0 | ok | native/selftest.txt |
| netservice-status | True | 0 | ok | native/netservice-status.txt |
| proc-mounts | True | 0 | ok | native/proc-mounts.txt |
| pcie1-platform-ls-soc | True | 0 | ok | native/pcie1-platform-ls-soc.txt |
| pcie1-platform-ls-bus | True | 0 | ok | native/pcie1-platform-ls-bus.txt |
| pcie1-platform-uevent | True | 0 | ok | native/pcie1-platform-uevent.txt |
| pcie1-platform-modalias | True | 0 | ok | native/pcie1-platform-modalias.txt |
| pcie1-platform-driver-readlink | True | 0 | ok | native/pcie1-platform-driver-readlink.txt |
| pcie1-platform-power-runtime | True | 0 | ok | native/pcie1-platform-power-runtime.txt |
| pcie1-platform-power-control | True | 0 | ok | native/pcie1-platform-power-control.txt |
| platform-drivers-pcie-find | True | 0 | ok | native/platform-drivers-pcie-find.txt |
| debugfs-root-ls | True | 0 | ok | native/debugfs-root-ls.txt |
| cnss-debugfs-ls | False | 1 | error | native/cnss-debugfs-ls.txt |
| cnss-dev-boot-read | False | 1 | error | native/cnss-dev-boot-read.txt |
| dt-pcie-find | True | 0 | ok | native/dt-pcie-find.txt |
| dt-icnss-find | True | 0 | ok | native/dt-icnss-find.txt |
| dt-cnss-find | True | 0 | ok | native/dt-cnss-find.txt |
| dt-mhi-find | True | 0 | ok | native/dt-mhi-find.txt |
| dt-mdm-find | True | 0 | ok | native/dt-mdm-find.txt |
| dt-wlan-rc-num-find | True | 0 | ok | native/dt-wlan-rc-num-find.txt |
| dt-pcie-parent-find | True | 0 | ok | native/dt-pcie-parent-find.txt |
| regulator-pcie-grep | False | 2 | error | native/regulator-pcie-grep.txt |
| clk-pcie-grep | False | 2 | error | native/clk-pcie-grep.txt |
| gpio-pcie-grep | False | 2 | error | native/gpio-pcie-grep.txt |
| pinctrl-pcie-find | False | 1 | error | native/pinctrl-pcie-find.txt |
| pci-devices-ls | True | 0 | ok | native/pci-devices-ls.txt |
| mhi-devices-ls | True | 0 | ok | native/mhi-devices-ls.txt |
| dev-mhi-ls | False | 1 | error | native/dev-mhi-ls.txt |
| proc-interrupts | True | 0 | ok | native/proc-interrupts.txt |
| dmesg | True | 0 | ok | native/dmesg.txt |
| dt-dynamic-prop-01 | True | 0 | ok | native/dt-dynamic-prop-01.txt |
| dt-dynamic-prop-02 | True | 0 | ok | native/dt-dynamic-prop-02.txt |
| post-selftest | True | 0 | ok | native/post-selftest.txt |
| post-status | True | 0 | ok | native/post-status.txt |

## Safety

- Read-only command set only: `cat`, `ls`, `readlink`, `find`, `grep`,
  `hexdump`, `dmesg`, plus native `version`/`status`/`selftest`.
- No sysfs/debugfs write, platform bind/unbind, PCI rescan,
  `cnss/dev_boot` write, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE`,
  Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external
  ping, flash, boot image write, or partition write.

## Next

design a narrower platform-driver/RC1 entry proof or host-only reason why no safe userspace surface exists
