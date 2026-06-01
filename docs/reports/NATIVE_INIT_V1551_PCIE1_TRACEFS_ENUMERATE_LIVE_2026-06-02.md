# Native Init V1551 PCIe1 Tracefs Enumerate Live

## Summary

- Cycle: `V1551`
- Type: bounded live tracefs observer around pcie1 sysfs-client enumerate
- Decision: `v1551-pcie1-gdsc-enable-captured-no-l0`
- Result: `PASS`
- Reason: tracefs captured pcie_1_gdsc enable activity while RC1 still failed before L0
- Evidence: `tmp/wifi/v1551-pcie1-tracefs-enumerate-live/manifest.json`

V1551 enables only selected tracefs static events, writes once to the already-proven pcie1 enumerate debugfs endpoint, disables the events, captures filtered trace lines plus dmesg, and verifies post selftest. It does not perform any Wi-Fi HAL, scan/connect, credential, DHCP/route, external ping, direct PMIC/GPIO/GDSC write, global PCI rescan, platform bind/unbind, flash, or partition write.

## Result

| field | value |
| --- | --- |
| trace result | tracefs-enumerate-pass |
| trace root | /sys/kernel/tracing |
| trigger rc | 0 |
| enabled events ok | 12 |
| target trace lines | 51 |
| pcie_1_gdsc lines | 4 |
| pcie_1_gdsc enable lines | 2 |
| pcie_1_gdsc disable lines | 2 |
| pcie1 clock lines | 48 |
| GPIO102 / GPIO104 / GPIO135 / GPIO142 | 3 / 0 / 0 / 0 |
| link failed | True |
| L0 seen | False |
| MHI seen | False |
| WLFW/FW-ready/wlan seen | False |
| mount cleanup | True |

## Event Counts

```json
{
  "target_line_count.clk.clk_enable": 11,
  "target_line_count.clk.clk_enable_complete": 11,
  "target_line_count.clk.clk_prepare": 11,
  "target_line_count.clk.clk_prepare_complete": 11,
  "target_line_count.gpio.gpio_direction": 0,
  "target_line_count.gpio.gpio_value": 3,
  "target_line_count.regulator.regulator_disable": 1,
  "target_line_count.regulator.regulator_disable_complete": 1,
  "target_line_count.regulator.regulator_enable": 1,
  "target_line_count.regulator.regulator_enable_complete": 1,
  "target_line_count.regulator.regulator_set_voltage": 0,
  "target_line_count.regulator.regulator_set_voltage_complete": 0
}
```

## Target Trace Lines

- `         busybox-729   [002] ....  1507.907642: gpio_value: 102 set 0`
- `         busybox-729   [002] ....  1507.908729: regulator_enable: name=pcie_1_gdsc`
- `         busybox-729   [002] ....  1507.908739: regulator_enable_complete: name=pcie_1_gdsc`
- `         busybox-729   [002] ....  1507.908880: clk_prepare: gcc_pcie_1_aux_clk_src`
- `         busybox-729   [002] ....  1507.908884: clk_prepare_complete: gcc_pcie_1_aux_clk_src`
- `         busybox-729   [002] ....  1507.908884: clk_prepare: gcc_pcie_1_aux_clk`
- `         busybox-729   [002] ....  1507.908886: clk_prepare_complete: gcc_pcie_1_aux_clk`
- `         busybox-729   [002] d..1  1507.908887: clk_enable: gcc_pcie_1_aux_clk_src`
- `         busybox-729   [002] d..1  1507.908888: clk_enable_complete: gcc_pcie_1_aux_clk_src`
- `         busybox-729   [002] d..1  1507.908889: clk_enable: gcc_pcie_1_aux_clk`
- `         busybox-729   [002] d..1  1507.908892: clk_enable_complete: gcc_pcie_1_aux_clk`
- `         busybox-729   [002] ....  1507.908895: clk_prepare: gcc_pcie_1_cfg_ahb_clk`
- `         busybox-729   [002] ....  1507.908896: clk_prepare_complete: gcc_pcie_1_cfg_ahb_clk`
- `         busybox-729   [002] d..1  1507.908897: clk_enable: gcc_pcie_1_cfg_ahb_clk`
- `         busybox-729   [002] d..1  1507.908901: clk_enable_complete: gcc_pcie_1_cfg_ahb_clk`
- `         busybox-729   [002] ....  1507.908916: clk_prepare: gcc_pcie_1_mstr_axi_clk`
- `         busybox-729   [002] ....  1507.908917: clk_prepare_complete: gcc_pcie_1_mstr_axi_clk`
- `         busybox-729   [002] d..1  1507.908917: clk_enable: gcc_pcie_1_mstr_axi_clk`
- `         busybox-729   [002] d..1  1507.908922: clk_enable_complete: gcc_pcie_1_mstr_axi_clk`
- `         busybox-729   [002] ....  1507.908934: clk_prepare: gcc_pcie_1_slv_axi_clk`
- `         busybox-729   [002] ....  1507.908935: clk_prepare_complete: gcc_pcie_1_slv_axi_clk`
- `         busybox-729   [002] d..1  1507.908936: clk_enable: gcc_pcie_1_slv_axi_clk`
- `         busybox-729   [002] d..1  1507.908944: clk_enable_complete: gcc_pcie_1_slv_axi_clk`
- `         busybox-729   [002] ....  1507.908947: clk_prepare: gcc_pcie_1_clkref_clk`
- `         busybox-729   [002] ....  1507.908948: clk_prepare_complete: gcc_pcie_1_clkref_clk`
- `         busybox-729   [002] d..1  1507.908949: clk_enable: gcc_pcie_1_clkref_clk`
- `         busybox-729   [002] d..1  1507.908951: clk_enable_complete: gcc_pcie_1_clkref_clk`
- `         busybox-729   [002] ....  1507.908955: clk_prepare: gcc_pcie_1_slv_q2a_axi_clk`
- `         busybox-729   [002] ....  1507.908957: clk_prepare_complete: gcc_pcie_1_slv_q2a_axi_clk`
- `         busybox-729   [002] d..1  1507.908958: clk_enable: gcc_pcie_1_slv_q2a_axi_clk`
- `         busybox-729   [002] d..1  1507.908961: clk_enable_complete: gcc_pcie_1_slv_q2a_axi_clk`
- `         busybox-729   [002] ....  1507.908987: clk_prepare: gcc_pcie_phy_refgen_clk_src`
- `         busybox-729   [002] ....  1507.908989: clk_prepare_complete: gcc_pcie_phy_refgen_clk_src`
- `         busybox-729   [002] ....  1507.908990: clk_prepare: gcc_pcie1_phy_refgen_clk`
- `         busybox-729   [002] ....  1507.908991: clk_prepare_complete: gcc_pcie1_phy_refgen_clk`
- `         busybox-729   [002] d..1  1507.908992: clk_enable: gcc_pcie_phy_refgen_clk_src`
- `         busybox-729   [002] d..1  1507.908993: clk_enable_complete: gcc_pcie_phy_refgen_clk_src`
- `         busybox-729   [002] d..1  1507.908993: clk_enable: gcc_pcie1_phy_refgen_clk`
- `         busybox-729   [002] d..1  1507.908997: clk_enable_complete: gcc_pcie1_phy_refgen_clk`
- `         busybox-729   [002] ....  1507.909013: clk_prepare: gcc_pcie_phy_aux_clk`
- `         busybox-729   [002] ....  1507.909015: clk_prepare_complete: gcc_pcie_phy_aux_clk`
- `         busybox-729   [002] d..1  1507.909017: clk_enable: gcc_pcie_phy_aux_clk`
- `         busybox-729   [002] d..1  1507.909021: clk_enable_complete: gcc_pcie_phy_aux_clk`
- `         busybox-729   [002] ....  1507.912289: clk_prepare: gcc_pcie_1_pipe_clk`
- `         busybox-729   [002] ....  1507.912291: clk_prepare_complete: gcc_pcie_1_pipe_clk`
- `         busybox-729   [002] d..1  1507.912293: clk_enable: gcc_pcie_1_pipe_clk`
- `         busybox-729   [002] d..1  1507.912305: clk_enable_complete: gcc_pcie_1_pipe_clk`
- `         busybox-729   [002] ....  1507.913389: gpio_value: 102 set 1`
- `         busybox-729   [002] ....  1508.022357: gpio_value: 102 set 0`
- `         busybox-729   [002] ....  1508.022610: regulator_disable: name=pcie_1_gdsc`
- `         busybox-729   [002] ....  1508.022619: regulator_disable_complete: name=pcie_1_gdsc`

## Safety

| field | value |
| --- | --- |
| tracefs_write_executed | True |
| sysfs_client_enumerate_executed | True |
| pmic_gpio_gdsc_direct_write_executed | False |
| direct_esoc_ioctl_executed | False |
| boot_done_spoof_executed | False |
| global_pci_rescan_executed | False |
| platform_bind_unbind_executed | False |
| wifi_hal_start_executed | False |
| scan_connect_executed | False |
| credential_use_executed | False |
| dhcp_route_executed | False |
| external_ping_executed | False |
| flash_executed | False |
| partition_write_executed | False |

## Next

classify PERST/refclk/endpoint response after confirmed RC1 power-domain enable
