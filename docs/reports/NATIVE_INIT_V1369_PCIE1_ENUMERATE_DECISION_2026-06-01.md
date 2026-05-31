# Native Init V1369 pcie1 Enumerate Decision

## Summary

- Cycle: `V1369`
- Type: host-only decision
- Decision: `v1369-select-corrected-debugfs-rc1-enumerate-design`
- Result: PASS
- Selected Path: `corrected-debugfs-case11-enumerate`
- Script: `scripts/revalidation/native_wifi_pcie1_enumerate_decision_v1369.py`
- Evidence:
  - `tmp/wifi/v1369-pcie1-enumerate-decision/manifest.json`
  - `tmp/wifi/v1369-pcie1-enumerate-decision/summary.md`

## Decision

The corrected pci-msm debugfs path is now narrower than a new kernel shim: V1368 proved rc_sel=2 reaches RC1 safely for status, and source shows case=11 calls msm_pcie_enumerate(dev->rc_idx), which performs msm_pcie_enable(PM_ALL) then PCI root-bus scan/add. A bounded rc_sel=2 case=11 enumerate proof is the next direct blocker test; it must still exclude Wi-Fi HAL/scan/connect and treat transport loss or unexpected health/link side effects as failure.

## Checks

| check | pass |
| --- | --- |
| broad_bind_rescan_rejected | true |
| case11_calls_msm_pcie_enumerate | true |
| current_route_keeps_pcie1_off | true |
| enumerate_calls_msm_pcie_enable_pm_all | true |
| enumerate_scans_root_bus | true |
| v1366_correct_selector_bitmask | true |
| v1368_rc1_values_observed | true |
| v1368_status_path_clean | true |

## Source Lines

| symbol | line |
| --- | --- |
| debugfs_case_select | 2784 |
| case11 | 1846 |
| msm_pcie_enumerate | 5263 |
| msm_pcie_enable_pm_all | 5280 |
| pci_scan_root_bus_bridge | 5344 |
| pci_bus_add_devices | 5355 |

## V1370 Design

| field | value |
| --- | --- |
| candidate_commands | mount debugfs only if not already mounted<br>printf '2\n' > /sys/kernel/debug/pci-msm/rc_sel<br>printf '11\n' > /sys/kernel/debug/pci-msm/case |
| preflight | native version/status/selftest fail=0<br>V1368-style rc_sel=2 case=26 status path already clean<br>debugfs mount state captured<br>PCI/MHI devices absent before enumerate<br>pcie1 regulator/clock/gpio/dmesg snapshots captured before enumerate |
| success_signals | command returns without transport loss<br>dmesg includes RC1 enumerate attempt<br>pcie1 GDSC/clock/PERST/link or PCI/MHI state changes are captured<br>post selftest fail=0 |
| failure_signals | transport loss/reboot<br>post selftest fail>0<br>unexpected non-RC1 PCI changes<br>debugfs cleanup failure |
| hard_stops | do not start Wi-Fi HAL<br>do not scan/connect/use credentials<br>do not run DHCP/routes/external ping<br>do not use PERST assert/deassert debug cases<br>do not write PMIC/GPIO/GDSC directly<br>do not write boot image or partitions |

## Rejected Paths

| path | reason |
| --- | --- |
| new kernel shim before debugfs enumerate | more invasive than an existing source-proven case=11 path after V1368 selector proof |
| platform bind/unbind or PCI rescan | already rejected as broad/non-RC1-specific by V1362 |
| Wi-Fi HAL or connect now | pcie1 enumerate/WLFW/MHI prerequisite is not proven yet |

## Safety

- V1369 is host-only and executes no device command.
- The selected next proof still excludes Wi-Fi HAL, scan/connect,
  credential handling, DHCP/routes, external ping, PERST assert/deassert,
  PMIC/GPIO/GDSC direct writes, eSoC notify/`BOOT_DONE`, flash, boot image
  write, and partition write.

## Next

V1370 bounded live corrected-RC1 enumerate proof: rc_sel=2 then case=11, no Wi-Fi HAL or network bring-up
