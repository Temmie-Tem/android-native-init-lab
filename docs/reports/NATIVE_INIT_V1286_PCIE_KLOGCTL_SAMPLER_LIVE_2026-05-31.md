# Native Init V1286 PCIe/GDSC/klogctl Sampler Live

- generated: 2026-05-31
- cycle: V1286
- command: bounded live observation
- decision: `v1286-pm-esoc0-trigger-sampled-mdm2ap-silent-reboot-required`
- pass: true
- helper: `a90_android_execns_probe v269`

## Result

V1286 reran the bounded PM-service `/dev/subsys_esoc0` response sampler with
helper v269. The repaired kernel-log collector used the syslog/klogctl fallback.

| field | value |
| --- | --- |
| sample count | `14` |
| PM-service `/dev/subsys_esoc0` attempt | true |
| late `per_proxy` started | `1` |
| kmsg source | `syslog-read-all` |
| max filtered kmsg markers | `32` |
| PCIe kmsg markers | `0` |
| MHI kmsg markers | `0` |
| WLFW kmsg markers | `0` |
| eSoC kmsg markers | `3` |
| MDM kmsg markers | `24` |
| subsystem kmsg markers | `22` |
| GPIO142 IRQ count | `0` |
| PCI devices | `0` |
| MHI bus devices | `0` |
| MHI pipe | absent |
| `wlan0` | absent |
| `pcie_1_gdsc` | `0mV` |
| `pcie_0_gdsc` | `0mV` |
| TLMM GPIO135/GPIO142 range | visible (`0-174`) |
| debugfs cleanup | unmounted after cycle |
| post-reboot health | v724 selftest `pass=11 warn=1 fail=0` |

Evidence:

- `tmp/wifi/v1286-pcie-klogctl-sampler-live/manifest.json`
- `tmp/wifi/v1286-pcie-klogctl-sampler-live/summary.md`
- `tmp/wifi/v1286-pcie-klogctl-sampler-live/native/global-dmesg-after-observer.txt`

## Interpretation

V1286 closes the V1283 collector gap: `/dev/kmsg` is not required for this live
sampler because the helper successfully reads kernel logs through
`syslog-read-all`.

The response gap remains below the PM-service `/dev/subsys_esoc0` entry:
PM-service reaches the eSoC trigger path, but GPIO142, PCIe RC1, GDSC voltage,
MHI, WLFW, and `wlan0` do not advance. The useful next step is no longer kmsg
plumbing; it is SDX50M power/GPIO prerequisite classification.

## Safety

No Wi-Fi HAL start, scan/connect, credential use, DHCP/route change, external
ping, flash, boot image write, partition write, PMIC write, GPIO line request,
or direct eSoC ioctl was executed. The live actor remained the existing bounded
PM-service response path.

## Next

V1287 should classify the SDX50M response prerequisites from V1286 and Android
positive evidence: `pcie_1_gdsc`/`pcie_0_gdsc` staying at `0mV`, GPIO142 IRQ
staying `0`, and no PCIe/MHI/WLFW markers after PM-service enters
`mdm_subsys_powerup`.
