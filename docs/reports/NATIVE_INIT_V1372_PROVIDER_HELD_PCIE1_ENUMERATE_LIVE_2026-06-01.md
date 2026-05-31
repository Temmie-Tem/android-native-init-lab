# Native Init V1372 Provider-held pcie1 Enumerate Live

## Summary

- Cycle: `V1372`
- Type: bounded live provider-held corrected-RC1 enumerate proof
- Decision: `v1372-provider-held-still-no-l0-clean`
- Result: PASS
- Script: `scripts/revalidation/native_wifi_provider_held_pcie1_enumerate_live_v1372.py`
- Evidence:
  - `tmp/wifi/v1372-provider-held-pcie1-enumerate-live/manifest.json`
  - `tmp/wifi/v1372-provider-held-pcie1-enumerate-live/summary.md`
  - `tmp/wifi/v1372-provider-held-pcie1-enumerate-live/native/`

## Decision

provider-held delayed corrected RC1 enumerate still stopped before L0; cleanup stayed healthy

## Interpretation

- The provider holder entered the ext-sdx50m path (`mdm_subsys_powerup`) before
  the corrected RC1 enumerate write.
- RC1 still stopped in LTSSM poll/compliance before L0; no PCI device, MHI
  node, GPIO142/MDM2AP assertion, WLFW marker, or `wlan0` appeared.
- This keeps Wi-Fi HAL, scan/connect, DHCP/routes, external ping, and upper
  eSoC notify/`BOOT_DONE`/MHI work parked. The next blocker is provider
  timing or Android-only endpoint-readiness parity, not another blind upper
  Wi-Fi retry.

## Key Observations

| field | value |
| --- | --- |
| write_ok | True |
| holder_seen | True |
| holder_block_seen | True |
| pcie_l0_seen | False |
| current_gen_seen | False |
| link_failed_seen | True |
| poll_compliance_seen | True |
| pci_device_count | 0 |
| mhi_present | False |
| gpio142_seen | False |
| wlfw_seen | False |
| wlan0_seen | False |
| cleanup_ok | True |

## Captures

| name | ok | rc | status | file |
| --- | --- | --- | --- | --- |
| version | True | 0 | ok | native/version.txt |
| selftest | True | 0 | ok | native/selftest.txt |
| status | True | 0 | ok | native/status.txt |
| mounts-before | True | 0 | ok | native/mounts-before.txt |
| debugfs-mount | True | 0 | ok | native/debugfs-mount.txt |
| mounts-during | True | 0 | ok | native/mounts-during.txt |
| before-regulator-pcie | True | 0 | ok | native/before-regulator-pcie.txt |
| before-clk-pcie | True | 0 | ok | native/before-clk-pcie.txt |
| before-gpio-pcie | True | 0 | ok | native/before-gpio-pcie.txt |
| before-pci-devices | True | 0 | ok | native/before-pci-devices.txt |
| before-mhi-devices | True | 0 | ok | native/before-mhi-devices.txt |
| before-interrupts | True | 0 | ok | native/before-interrupts.txt |
| before-dmesg-pcie-tail | True | 0 | ok | native/before-dmesg-pcie-tail.txt |
| provider-held-case11 | True | 0 | ok | native/provider-held-case11.txt |
| after-regulator-pcie | True | 0 | ok | native/after-regulator-pcie.txt |
| after-clk-pcie | True | 0 | ok | native/after-clk-pcie.txt |
| after-gpio-pcie | True | 0 | ok | native/after-gpio-pcie.txt |
| after-pci-devices | True | 0 | ok | native/after-pci-devices.txt |
| after-mhi-devices | True | 0 | ok | native/after-mhi-devices.txt |
| after-interrupts | True | 0 | ok | native/after-interrupts.txt |
| after-dmesg-pcie-tail | True | 0 | ok | native/after-dmesg-pcie-tail.txt |
| debugfs-umount | True | 0 | ok | native/debugfs-umount.txt |
| mounts-after | True | 0 | ok | native/mounts-after.txt |

## Safety

- V1372 opens only `/dev/subsys_esoc0` via a temporary char node, then writes
  corrected `rc_sel=2` and enumerate `case=11` after the Android-derived delay.
- No Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external ping,
  PERST assert/deassert debug cases, PMIC/GPIO/GDSC direct writes, eSoC
  notify/`BOOT_DONE` spoof, flash, boot image write, or partition write.

## Next

classify provider timing/MDM2AP/PON delta or Android-only endpoint readiness prerequisite
