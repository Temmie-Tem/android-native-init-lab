# V1275 AP2MDM Debugfs Block Sampler

## Result

- decision: `v1275-pm-esoc0-trigger-sampled-mdm2ap-silent-reboot-required`
- evidence: `tmp/wifi/v1275-ap2mdm-block-sampler-live/manifest.json`
- helper: `a90_android_execns_probe v266`
- helper SHA256: `3bf4105d685f023ccdeb75ae28d7d104ca005fc9f70870dc6f402a9ea4038ed4`
- scope: bounded live observer using the existing late `per_proxy` / PM-service
  `/dev/subsys_esoc0` response window

## New Evidence

| field | result |
|---|---|
| response samples | `14` |
| PM-service `/dev/subsys_esoc0` attempt | `true` |
| late `per_proxy` started | `true` |
| PMIC GPIO9 line-info flags | `0x3` in all samples |
| PMIC GPIO9 line-info consumer | `AP2MDM_SOFT_RESET` in all samples |
| PMIC GPIO1270 debugfs block | present in all samples |
| PMIC GPIO9 debugfs block line | `gpio9 : out ... high ...` in all samples |
| TLMM GPIO135 debugfs block | not found |
| TLMM GPIO142 debugfs block | not found |
| PMIC GPIO9 pinconf block | present in all samples |
| TLMM GPIO135/GPIO142 pinconf blocks | present in all samples |
| PCIe `pcie_0_gdsc` / `pcie_1_gdsc` | present, `0mV` in all samples |
| GPIO142 IRQ count | `0` in all samples |
| `mdm3` state | `OFFLINING` in all samples |
| PCI device count | `0` in all samples |
| MHI bus count | `0` in all samples |
| MHI pipe | absent |
| `wlan0` | absent |
| forbidden line request/write/eSoC ioctl markers | all zero |

## Interpretation

V1275 closes the previous exact-value visibility gap for the PMIC side of the
AP2MDM soft-reset/status path.  During the same PM-service
`/dev/subsys_esoc0` response window, debugfs GPIO reports PMIC GPIO9 as an
output and includes a `high` value field, while the GPIO chardev line-info still
reports kernel-owned output consumer `AP2MDM_SOFT_RESET`.

That moves the blocker one step lower: the AP-side PMIC soft-reset line appears
asserted enough for the kernel/debugfs view, but SDX50M still does not respond.
There is still no GPIO142 interrupt, no PCIe RC1 enumeration, no MHI pipe, no
WLFW/BDF, and no `wlan0`.

The next useful step is a host-only classifier that compares this V1275 PMIC
GPIO9 block with Android reference behavior and DTS/pinctrl polarity.  Do not
advance to PMIC writes, userspace GPIO holds, or direct eSoC ioctl from this
evidence alone.

## Cleanup

The live manifest classified cleanup as reboot-required because postflight could
not prove all transient actors and mounts were safely stopped.  A reboot was
performed.  After reboot:

- `version` returned `A90 Linux init 0.9.68 (v724)`.
- `selftest` returned `pass=11 warn=1 fail=0`.
- `/proc/mounts` no longer showed `debugfs`, `/vendor/firmware_mnt`,
  `/vendor/firmware-modem`, or `/mnt/system`.

## Safety

V1275 remained read-only for the new surfaces.  It did not request or hold GPIO
lines beyond the existing line-info read, write PMIC/debugfs/regulator state,
issue direct eSoC ioctl, start Wi-Fi HAL, scan/connect, use credentials, run
DHCP/routes, send external ping, flash, write a boot image, or write partitions.

## Next

V1276 should be host-only: classify PMIC GPIO9 polarity/value against Android
reference evidence, DTS labels, and previous V895/V1228 GPIO142/PCI observations
before any write-side experiment.
