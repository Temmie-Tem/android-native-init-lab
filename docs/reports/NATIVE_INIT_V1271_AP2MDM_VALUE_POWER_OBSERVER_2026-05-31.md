# V1271 AP2MDM Value/Power Observer

## Result

- decision: `v1271-pm-esoc0-trigger-sampled-mdm2ap-silent-reboot-required`
- evidence: `tmp/wifi/v1271-ap2mdm-value-power-observer-live/manifest.json`
- helper: `a90_android_execns_probe v265`
- helper SHA256: `97ffa91a1aa7b8f4ab2c3a74716ae5664c703e98fe19a322351b1277fbd282b2`
- live action: bounded late `per_proxy` / PM-service response sampler
- post-run recovery: reboot cleanup completed, native version returns `A90 Linux init 0.9.68 (v724)`, selftest returns `fail=0`

## New Evidence

| field | result |
|---|---|
| response samples | `14` |
| PM-service `/dev/subsys_esoc0` attempt | `true` |
| PMIC GPIO9 line-info present | `true` |
| PMIC GPIO9 flags | `0x3` in all samples |
| PMIC GPIO9 kernel-owned | `true` in all samples |
| PMIC GPIO9 output flag | `true` in all samples |
| PMIC GPIO9 consumer | `AP2MDM_SOFT_RESET` in all samples |
| `/sys/kernel/debug/gpio` mounted/readable | `true` |
| PMIC GPIO1270 debugfs-gpio line | not found |
| TLMM GPIO135 debugfs-gpio line | not found |
| TLMM GPIO142 debugfs-gpio line | not found |
| PMIC GPIO9 pinconf header | present in all samples |
| TLMM GPIO135 pinmux/pinconf header | present in all samples |
| TLMM GPIO142 pinmux/pinconf header | present in all samples |
| PCIe `pcie_0_gdsc` / `pcie_1_gdsc` | present, `0mV` in all samples |
| GPIO142 IRQ count | `0` in all samples |
| `mdm3` state | `OFFLINING` in all samples |
| PCI device count | `0` in all samples |
| MHI bus count | `0` in all samples |
| MHI pipe | absent |
| `wlan0` | absent |
| forbidden line request/write/eSoC ioctl markers | all zero |

## Interpretation

V1271 keeps the V1267 lower-boundary result intact and adds value/power
visibility.  The PMIC GPIO9 chardev line-info still proves the kernel owns the
line as an output with consumer `AP2MDM_SOFT_RESET` during the PM-service
`/dev/subsys_esoc0` response window.  Pinctrl debugfs also sees the PMIC GPIO9
and TLMM GPIO135/GPIO142 surfaces.

The missing fact is still the actual asserted electrical value.  The debugfs
GPIO text was mounted/readable, but the exact global GPIO1270 / TLMM GPIO135 /
TLMM GPIO142 value lines were not present in the captured text.  Therefore V1271
does not justify any GPIO request/hold or PMIC write.  It instead narrows the
next observer target to a broader read-only debugfs GPIO/pinconf block capture
that can show the value/state line if the kernel exposes it under a different
format.

The downstream SDX50M response remains absent: no GPIO142 interrupt, no PCIe
RC1 enumeration, no MHI pipe, no WLFW/BDF, and no `wlan0`.

## Cleanup

The live manifest classified cleanup as reboot-required because postflight could
not prove all transient actors and mounts were safely stopped.  A reboot was
performed.  After reboot:

- `version` returned `A90 Linux init 0.9.68 (v724)`.
- `selftest` returned `pass=11 warn=1 fail=0`.
- `/proc/mounts` no longer showed `debugfs`, `/vendor/firmware_mnt`,
  `/vendor/firmware-modem`, or `/mnt/system`.

## Next

V1272 should be host-only classification for the next read-only observer shape.
The preferred next helper change is not a write or GPIO hold.  It is a compact
debugfs/pinconf block sampler that captures the relevant surrounding lines for:

- PM8150L GPIO chip/range containing global GPIO1270.
- PMIC GPIO9 pinmux and pinconf block, not only the first matching header line.
- TLMM GPIO135/GPIO142 pinmux and pinconf block.
- PCIe RC1/GDSC read-only state.

Continue to block PMIC writes, userspace GPIO line request/hold, direct eSoC
ioctl, new daemon/HAL start beyond the bounded PM-service response path, Wi-Fi
scan/connect, credentials, DHCP/routes, external ping, flash, boot image write,
and partition write.
