# Native Init V1287 SDX50M Power Gap Classifier

- generated: 2026-05-31
- cycle: V1287
- command: host-only classifier
- decision: `v1287-klogctl-confirms-post-esoc0-power-response-gap`
- pass: true

## Result

V1287 classified V1286 against Android-positive power evidence.

| field | value |
| --- | --- |
| V1286 klog source | `syslog-read-all` |
| V1286 filtered kmsg markers | `32` |
| native PMIC9 gpio block | matches Android `out/high` shape |
| native PMIC9 pinmux line | still reports `MUX UNCLAIMED` |
| native `pcie_1_gdsc` | `0mV` |
| native `pcie_0_gdsc` | `0mV` |
| GPIO142 IRQ | `0` |
| PCI/MHI/WLFW/SDX50M response | absent |
| Android contrast | PMIC9 `out/high`, PCIe RC1 initialized, WLFW/FW-ready/`wlan0` present |

Evidence:

- `tmp/wifi/v1287-v1286-sdx50m-power-gap-classifier/manifest.json`
- `tmp/wifi/v1287-v1286-sdx50m-power-gap-classifier/summary.md`

## Interpretation

V1286 demotes PM8150L gpio9 shape as the shortest blocker. Although the pinmux
view still reports `MUX UNCLAIMED`, the native PMIC gpio block already matches
the Android-positive `gpio9 : out ... high low` shape and the helper line-info
path saw the kernel-owned `AP2MDM_SOFT_RESET` line without requesting or holding
the line.

The active response gap is therefore after PM-service enters the eSoC path but
before any observable SDX50M response: PCIe GDSC rails stay at `0mV`, GPIO142
does not interrupt, and no PCIe/MHI/WLFW/SDX50M kmsg marker appears.

## Safety

Host-only classifier. No device command, PMIC write, GPIO line request, direct
eSoC ioctl, Wi-Fi HAL start, scan/connect, credential use, DHCP/route change,
external ping, flash, boot image write, or partition write was executed.

## Next

V1288 should build a no-write TLMM/PCIe response observer that captures
untruncated GPIO135/GPIO142, PMIC9, and PCIe GDSC state deltas before considering
any PMIC/GPIO mutation gate.
