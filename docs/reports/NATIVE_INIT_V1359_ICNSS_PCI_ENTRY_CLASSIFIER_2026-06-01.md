# Native Init V1359 ICNSS/pci-msm Entry Classifier

## Summary

- Cycle: `V1359`
- Type: host-only classifier
- Decision: `v1359-no-safe-userspace-msm-pcie-enumerate-entry`
- Result: PASS
- Script: `scripts/revalidation/native_wifi_icnss_pci_entry_classifier_v1359.py`
- Evidence:
  - `tmp/wifi/v1359-icnss-pci-entry-classifier/manifest.json`
  - `tmp/wifi/v1359-icnss-pci-entry-classifier/summary.md`

## Decision

V1358 proves the live debugfs surface is ICNSS stats only and not CNSS2 dev_boot. The ICNSS source does not call msm_pcie_enumerate or expose a pcie-parent/rc-num driven userspace control. The only confirmed live surface is the already-bound pci-msm platform device, whose generic bind/unbind/rescan paths are too broad for the next mutation.

## Checks

| check | pass |
| --- | --- |
| cnss2_dev_boot_is_wrong_branch | true |
| hard_exclusions_preserved | true |
| icnss_debugfs_stats_only_source | true |
| icnss_has_no_pcie_enumerate_call | true |
| live_pcie1_platform_bound | true |
| mhi_hook_downstream_of_pci_device | true |
| mhi_sdx50m_still_relevant | true |
| msm_pcie_enumerate_declared_not_userland | true |
| pcie_parent_belongs_wil6210_not_icnss | true |
| v1358_closes_cnss_dev_boot | true |

## Source Facts

| fact | value |
| --- | --- |
| icnss_debugfs_create | root_dentry = debugfs_create_dir("icnss", NULL); |
| icnss_stats_file | debugfs_create_file("stats", 0600, root_dentry, priv, |
| icnss_dev_boot_mentions | 0 |
| icnss_msm_pcie_mentions | 0 |
| cnss2_dev_boot | debugfs_create_file("dev_boot", 0600, root_dentry, plat_priv, |
| cnss2_wlan_rc_num | qcom,wlan-rc-num = <0>; |
| wil6210_pcie_parent | qcom,pcie-parent = <&pcie1>; |

## Rejected Next Mutations

- cnss/dev_boot enumerate: unavailable on this live ICNSS kernel
- platform driver bind/unbind: too broad without a narrower MHI/pci-msm proof
- global PCI rescan: too broad and not RC1-specific
- direct PMIC/GPIO/GDSC/MMIO writes: outside current evidence

## Next

V1360 live read-only MHI platform surface verifier before considering any pci-msm bind/rescan mutation

## Safety

- Host-only; no device command or live runtime access.
- No platform bind/unbind, PCI rescan, PMIC/GPIO/GDSC write, eSoC
  notify/`BOOT_DONE`, Wi-Fi HAL, scan/connect, credential handling,
  DHCP/routes, external ping, flash, boot image write, or partition write.
