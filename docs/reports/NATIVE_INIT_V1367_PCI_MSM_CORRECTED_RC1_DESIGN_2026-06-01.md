# Native Init V1367 Corrected-RC1 pci-msm Design

## Summary

- Cycle: `V1367`
- Type: host-only design
- Decision: `v1367-corrected-rc1-status-read-design-ready`
- Result: PASS
- Selected Path: `corrected-rc1-status-read`
- Script: `scripts/revalidation/native_wifi_pci_msm_corrected_rc1_design_v1367.py`
- Evidence:
  - `tmp/wifi/v1367-pci-msm-corrected-rc1-design/manifest.json`
  - `tmp/wifi/v1367-pci-msm-corrected-rc1-design/summary.md`

## Decision

V1366 proves the previous live write targeted RC0 and that pcie1 requires rc_sel=2; it also proves case=26 is source-intended as a PERST/WAKE GPIO readout while case=11 is enumerate. The next live action can be a single corrected RC1 status-read proof only if it is treated as reboot-risky and bounded; enumerate, PERST toggle, PCI rescan, and Wi-Fi bring-up remain excluded.

## Checks

| check | pass |
| --- | --- |
| case11_source_enumerates | true |
| case26_source_read_only | true |
| pcie1_current_route_stayed_off | true |
| pon_parity_closed | true |
| v1365_transport_loss_known | true |
| v1366_corrected_rc_selector | true |

## V1368 Design

| field | value |
| --- | --- |
| intent | read pcie1/RC1 PERST and WAKE status through pci-msm debugfs only |
| candidate_commands | mount debugfs only if not already mounted<br>printf '2\n' > /sys/kernel/debug/pci-msm/rc_sel<br>printf '26\n' > /sys/kernel/debug/pci-msm/case |
| preflight | native version/status/selftest fail=0<br>debugfs mount state captured<br>/sys/kernel/debug/pci-msm/case lists 26 and 11<br>pcie1 PCI/MHI devices absent before proof<br>focused dmesg and gpio/regulator/clock snapshots captured before proof |
| success_criteria | write returns without transport loss<br>after-captures complete<br>no PCI/MHI/link-up transition<br>debugfs mount state restored<br>post selftest fail=0 |
| failure_criteria | cmdv1 transport loss or reboot<br>PCI/MHI/link state transition<br>debugfs cleanup failure<br>post selftest fail>0 |
| transport_loss_handling | classify as reboot-risk failure, not pass<br>wait for bridge/device recovery before any further action<br>run status/selftest after recovery and record as out-of-window recovery evidence |

## Rejected Paths

| path | reason |
| --- | --- |
| case=11 enumerate | source calls msm_pcie_enumerate(dev->rc_idx); not a status proof |
| PERST assert/deassert debug cases | source performs gpio_set_value; direct reset mutation |
| platform bind/unbind or PCI rescan | broader than pcie1 and previously rejected by V1362 |
| kernel-side shim now | more invasive than one corrected source-read status proof; keep as fallback if V1368 fails |

## Safety

- V1367 is host-only and executes no device command.
- The selected next proof remains status-read only and keeps `case=11`
  enumerate, PERST assert/deassert, MMIO write, boot option write,
  platform bind/unbind, PCI rescan, PMIC/GPIO/GDSC direct write, eSoC
  notify/`BOOT_DONE`, Wi-Fi HAL, scan/connect, credential handling,
  DHCP/routes, external ping, flash, boot image write, and partition
  write excluded.

## Next

V1368 bounded live corrected-RC1 status-read proof: rc_sel=2 then case=26, with reboot-risk handling and no enumerate
