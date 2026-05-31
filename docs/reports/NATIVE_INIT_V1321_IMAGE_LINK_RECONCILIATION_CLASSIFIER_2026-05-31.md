# Native Init V1321 Image-link Reconciliation Classifier

## Summary

- Cycle: `V1321`
- Type: host-only reconciliation classifier
- Decision: `v1321-image-link-gate-covered-next-sdx50m-response-inputs`
- Result: PASS
- Evidence:
  - `tmp/wifi/v1321-image-link-reconciliation-classifier/manifest.json`
  - `tmp/wifi/v1321-image-link-reconciliation-classifier/summary.md`
- Script: `scripts/revalidation/native_wifi_image_link_reconciliation_classifier_v1321.py`

V1321 reconciles V1320 with the already-existing V1236-V1239 evidence.
V1320 correctly identified the Android `mdm_helper`/`ks`/MHI image-link
contract as relevant, but V1236-V1239 already prove the native late
`per_proxy` path reaches `pm-service` and `/dev/subsys_esoc0` /
`mdm_subsys_powerup`. The remaining blocker is therefore below the PM
userspace actor path: SDX50M does not produce GPIO142, PCIe RC1/MHI, WLFW,
BDF, or `wlan0` after native reaches GPIO135 / eSoC powerup.

## Decision

Do not repeat the image-link gate as the next primary branch. The next unit
should target SDX50M response inputs around `mdm_subsys_powerup` and GPIO135:
read-only GPIO142 IRQ/state, PCIe RC1, regulator/pinctrl/GDSC, MHI surface,
and reboot-bounded cleanup behavior. Wi-Fi HAL, scan/connect, credentials,
DHCP/routes, external ping, flash, boot image write, and partition write
remain blocked.

## Safety

Host-only classifier. No device command, PM actor start, `mdm_helper` start,
tracefs write, live eSoC ioctl/notify, PMIC write, userspace GPIO request,
Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping,
flash, boot image write, or partition write occurred.
