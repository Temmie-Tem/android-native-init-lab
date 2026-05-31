# Native Init V1324 Provider Response Delta Classifier

## Summary

- Cycle: `V1324`
- Type: host/source-only provider response delta classifier
- Decision: `v1324-delta-is-post-ap2mdm-mdm2ap-response-gap`
- Result: PASS
- Evidence:
  - `tmp/wifi/v1324-provider-response-delta-classifier/manifest.json`
  - `tmp/wifi/v1324-provider-response-delta-classifier/summary.md`
- Script: `scripts/revalidation/native_wifi_provider_response_delta_classifier_v1324.py`

V1324 compares existing native-negative and Android-positive evidence after
V1323. Native reaches the proprietary ext-mdm provider path and AP-side
activity: PMIC soft-reset GPIO1270, GPIO135/AP2MDM high, and GPIO141
AP2MDM_ERRFATAL-side activity. The same record keeps GPIO142/MDM2AP, the
MDM errfatal IRQ, PCIe RC1, MHI/ks, WLFW/BDF, and `wlan0` absent. Android
positive-control evidence reaches GPIO142 IRQ, PCIe RC1/L0, MHI/ks, WLFW/BDF,
and `wlan0`.

## Decision

Existing evidence is sufficient to classify the current delta as a
post-AP2MDM MDM2AP/PCIe response gap. The next useful unit is not Wi-Fi HAL,
scan/connect, credentials, DHCP, or external ping. It should be a small
observer/recapture design for GPIO142, MDM errfatal, and PCIe timing, with
any native live sampler kept read-only or explicitly reboot-bounded.

## Safety

Host/source-only classifier. No device command, helper deploy, PM actor start,
`mdm_helper` start, tracefs write, live eSoC ioctl/notify, PMIC write, GPIO
line request, direct GDSC/eSoC write, Wi-Fi HAL start, scan/connect, credential
use, DHCP/routes, external ping, flash, boot image write, or partition write
occurred.
