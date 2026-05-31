# Native Init V1310 Lower Prerequisite Classifier

## Summary

- Cycle: `V1310`
- Type: host-only classifier
- Decision: `v1310-static-surfaces-closed-dynamic-gdsc-sequence-blocker`
- Result: PASS
- Evidence:
  - `tmp/wifi/v1310-lower-prereq-classifier/manifest.json`
  - `tmp/wifi/v1310-lower-prereq-classifier/summary.md`
- Script: `scripts/revalidation/native_wifi_lower_prereq_classifier_v1310.py`

V1310 classifies the current native Wi-Fi blocker using V1244, V1276, V1291, V1306, and V1309 evidence. It does not run a device command.

## Classification

Static line shape is no longer the shortest blocker:

- PMIC GPIO9 out/high shape is closed by V1276.
- TLMM GPIO135/GPIO142 static shape is closed by V1291.
- Android-positive evidence still reaches PCIe RC1 and `wlan0`.

The active blocker is dynamic lower power sequencing after `pm-service` enters `/dev/subsys_esoc0` and blocks in `mdm_subsys_powerup`.

## Key Evidence

| field | value |
| --- | --- |
| V1309 focused samples | `76` |
| first path | `/dev/subsys_esoc0` |
| first wchan | `mdm_subsys_powerup` |
| PCIe1 GDSC | `0mV` |
| PCIe0 GDSC | `0mV` |
| PMIC soft-reset pinmux | `MUX UNCLAIMED` |
| MHI / `ks` / `wlan0` | absent |
| Android-positive contrast | PCIe RC1 + `wlan0` present |

## Rejected Next Gates

- blind PMIC GPIO9 write or hold
- userspace GPIO line request
- direct eSoC ioctl retry
- Wi-Fi HAL/scan/connect before lower response appears

## Next

V1311 should either:

1. add a stdout-reduced full-window lower-sequence summary sampler; or
2. classify the exact safe GDSC/eSoC prerequisite before any PMIC/GPIO/eSoC mutation.

The safer immediate engineering step is the stdout-reduced summary sampler, because V1309 still hit the helper `1MiB` stdout cap.

## Safety

- Host-only; no device command or mutation.
- No PMIC write, userspace GPIO line request/hold, direct eSoC ioctl, Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping, flash, boot image write, or partition write occurred.
