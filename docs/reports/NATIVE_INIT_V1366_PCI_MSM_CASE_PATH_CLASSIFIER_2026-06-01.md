# Native Init V1366 pci-msm Case-path Classifier

## Summary

- Cycle: `V1366`
- Type: host-only classifier
- Decision: `v1366-pci-msm-case-path-corrected-rc-selector-no-live-write`
- Result: PASS
- Script: `scripts/revalidation/native_wifi_pci_msm_case_path_classifier_v1366.py`
- Evidence:
  - `tmp/wifi/v1366-pci-msm-case-path-classifier/manifest.json`
  - `tmp/wifi/v1366-pci-msm-case-path-classifier/summary.md`

## Decision

Reference pci-msm source proves rc_sel is a bitmask, not an ordinal RC index: V1365 used rc_sel=1 and therefore selected RC0, while pcie1/RC1 would require rc_sel=2. Source also shows case 26 is intended as PERST/WAKE gpio_get_value readout and case 11 calls msm_pcie_enumerate(dev->rc_idx). Because the live V1365 write still caused transport loss, no further pci-msm case write is approved without a new reboot-safe design and source/live parity check.

## Classification

| item | result | detail |
| --- | --- | --- |
| V1365 rc_sel target | wrong-RC for pcie1 | rc_sel=1 selects BIT(0)/RC0; pcie1 has cell-index 1 and needs rc_sel=2 |
| case 26 source behavior | intended read-only GPIO readout | branch reads PERST/WAKE with gpio_get_value and contains no direct enumerate/pm/gpio_set/MMIO write call |
| case 11 source behavior | mutation/enumerate | branch calls msm_pcie_enumerate(dev->rc_idx) |
| live approval | not approved | V1365 transport loss means the source-intended readout is not enough to justify another case write without a new design |

## Checks

| check | pass |
| --- | --- |
| case11_calls_msm_pcie_enumerate | true |
| case26_has_no_direct_mutating_call | true |
| case26_reads_perst_wake_gpio | true |
| debugfs_case_select_loops_bitmask | true |
| pcie1_cell_index_is_1 | true |
| rc_sel_default_is_bit0 | true |
| rc_sel_max_is_bitmask | true |
| source_snapshot_has_pci_msm | true |
| v1365_saw_transport_loss | true |

## Facts

| fact | value |
| --- | --- |
| rc_sel_semantics | bitmask: loop executes i when rc_sel & BIT(i) |
| v1365_rc_sel_written | 1 |
| v1365_actual_target | RC0 |
| pcie1_cell_index | 1 |
| pcie1_correct_rc_sel_bitmask | 2 |
| case_11_label | 11:	 ENUMERATE |
| case_26_label | 26:	 OUTPUT PERST AND WAKE GPIO STATUS |
| v1364_prior_decision | v1364-pci-msm-debugfs-contract-candidate-not-approved |
| v1365_decision | v1365-case26-transport-reset-reboot-risk |
| source_line_rc_sel_default | 862 |
| source_line_case_select | 2784 |
| source_line_case11 | 1846 |
| source_line_case26 | 2306 |
| source_line_enumerate | 5263 |

## Safety

- Host-only; no device command or live runtime access.
- No debugfs/sysfs write, corrected `rc_sel=2` live retry, `case=11`
  enumerate, PERST assert/deassert, PCI rescan, platform bind/unbind,
  PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE`, Wi-Fi HAL, scan/connect,
  credential handling, DHCP/routes, external ping, flash, boot image write,
  or partition write.

## Next

V1367 host-only corrected-RC1 design: decide whether rc_sel=2 case=26 can be made reboot-safe, or prefer a kernel-side msm_pcie_enumerate(1) shim path
