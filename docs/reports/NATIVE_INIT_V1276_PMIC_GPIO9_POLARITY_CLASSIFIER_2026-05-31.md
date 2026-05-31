# V1276 PMIC GPIO9 Polarity Classifier

## Result

- decision: `v1276-pmic-gpio9-matches-android-tlmm-gate-selected`
- evidence: `tmp/wifi/v1276-pmic-gpio9-polarity-classifier/manifest.json`
- scope: host-only classifier; no live command, device mutation, GPIO line
  request, PMIC write, eSoC ioctl, Wi-Fi action, flash, boot image write, or
  partition write

## Purpose

V1275 showed PMIC GPIO9 as `out ... high ...` in the native PM-service
`/dev/subsys_esoc0` response window, but SDX50M still did not respond.  V1276
compares that PMIC state against Android/reference evidence before deciding
whether PMIC GPIO9 remains a blocker.

## Classification

| field | result |
|---|---|
| native PMIC GPIO9 | `out/high` |
| Android/reference PMIC GPIO9 | `out/high` |
| PMIC GPIO9 state match | `true` |
| native downstream response | absent: GPIO142 `0`, PCI `0`, MHI `0`, no MHI pipe, no `wlan0` |
| Android positive contrast | GPIO142/PCIe/sysmon positive markers exist |
| native TLMM GPIO135/GPIO142 debugfs block | absent in V1275 exact/block capture |
| Android TLMM GPIO135/GPIO142 readability | present in reference report |

PMIC GPIO9 is no longer the best active blocker.  The remaining gap is the
downstream TLMM/PCIe/SDX50M response after PM-service enters
`mdm_subsys_powerup`.

## Next Gate

V1277 should be source/build-only helper v267.  It should add read-only TLMM
GPIO range-slice capture around GPIO135/GPIO142 plus AP2MDM/MDM2AP
pinmux/pinconf and PCIe RC1/GDSC snapshots.  PMIC GPIO9 write/hold, userspace
GPIO line request, direct eSoC ioctl retry, service-manager/HAL expansion, Wi-Fi
scan/connect, DHCP/routes/external ping, flash, and boot image write remain
rejected.
