# Native Init V1364 pci-msm Debugfs Contract Classifier

## Summary

- Cycle: `V1364`
- Type: host-only classifier
- Decision: `v1364-pci-msm-debugfs-contract-candidate-not-approved`
- Result: PASS
- Script: `scripts/revalidation/native_wifi_pci_msm_debugfs_contract_classifier_v1364.py`
- Evidence:
  - `tmp/wifi/v1364-pci-msm-debugfs-contract-classifier/manifest.json`
  - `tmp/wifi/v1364-pci-msm-debugfs-contract-classifier/summary.md`

## Decision

V1363 exposes a pci-msm debugfs selector surface and kallsyms contains matching selector/enumerate functions. The likely contract is rc_sel=<RC> then case=<testcase>; case 11 is ENUMERATE and case 26 is status-only PERST/WAKE output. Because proprietary source/disassembly has not yet proven the exact call path, enumerate is not approved. The only defensible first write candidate is a bounded status-only case 26 probe.

## Candidate Contracts

| name | writes | expected_effect | approval_state |
| --- | --- | --- | --- |
| status-only pcie1 PERST/WAKE readout | echo 1 > /sys/kernel/debug/pci-msm/rc_sel<br>echo 26 > /sys/kernel/debug/pci-msm/case | dmesg/debug output only; no enumerate, no PERST toggle | candidate for V1365 bounded live proof |
| pcie1 enumerate | echo 1 > /sys/kernel/debug/pci-msm/rc_sel<br>echo 11 > /sys/kernel/debug/pci-msm/case | likely msm_pcie_enumerate(1), but exact call path still unproven | not approved before V1365/V1366 evidence |

## Checks

| check | pass |
| --- | --- |
| case_lists_enumerate_11 | true |
| case_lists_perst_mutations | true |
| case_lists_status_26 | true |
| kallsyms_has_debugfs_selectors | true |
| kallsyms_has_enumerate_path | true |
| pcie1_is_rc1_by_dts_order | true |
| previous_userspace_paths_closed | true |
| rc_sel_file_exists | true |
| v1363_found_debugfs_candidate | true |

## Source Facts

| fact | value |
| --- | --- |
| case_11 | 11:	 ENUMERATE |
| case_26 | 26:	 OUTPUT PERST AND WAKE GPIO STATUS |
| case_27 | 27:	 ASSERT PERST |
| kallsyms_rc_select | 0000000000000000 t msm_pcie_debugfs_rc_select |
| kallsyms_case_select | 0000000000000000 t msm_pcie_debugfs_case_select |
| kallsyms_testcase | 0000000000000000 t msm_pcie_sel_debug_testcase |
| kallsyms_enumerate | 0000000000000000 T msm_pcie_enumerate |

## Safety

- Host-only; no device command or live runtime access.
- No debugfs/sysfs write, `case=11` enumerate, platform bind/unbind, PCI rescan,
  PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE`, Wi-Fi HAL, scan/connect,
  credential handling, DHCP/routes, external ping, flash, boot image write,
  or partition write.

## Next

V1365 bounded live pci-msm debugfs status-only proof: rc_sel=1 then case=26; no enumerate
