# Native Init V1320 mdm_helper/ks/MHI Contract Classifier

## Summary

- Cycle: `V1320`
- Type: host-only classifier
- Decision: `v1320-mdm-helper-ks-mhi-contract-selected`
- Result: PASS
- Evidence:
  - `tmp/wifi/v1320-mdm-helper-ks-mhi-contract-classifier/manifest.json`
  - `tmp/wifi/v1320-mdm-helper-ks-mhi-contract-classifier/summary.md`
- Script: `scripts/revalidation/native_wifi_mdm_helper_ks_mhi_contract_classifier_v1320.py`

V1320 links the V1319 post-GPIO135 response gap to the Android
`mdm_helper`/`ks`/MHI image-link contract. Native has `mdm_helper` and
PM-service eSoC trigger visibility, but no `ks`, MHI pipe, GPIO142, WLFW,
or `wlan0`. Android-positive evidence has `mdm_helper`, `ks`,
`/dev/mhi_0305_01.01.00_pipe_10`, GPIO142 IRQ, PCIe RC1, WLFW, and
`wlan0`.

## Result

| surface | native | Android / reference |
| --- | --- | --- |
| GPIO135 response | GPIO142=0, MHI=False, wlan0=False | GPIO142=1, PCIe=18, wlan0=True |
| Actor contract | mdm_helper=True, ks=0, MHI=False | mdm_helper_fd=True, ks_fd=True, ks_mhi=True |
| REQ/IMG evidence | wait_req=True, img_xfer=True | android_contract=True |
| Negative control | img_xfer_alone_no_mhi=True | v895_irq_delta=0, status=0 |

## Decision

The next unit should not mutate GPIO/PMIC/GDSC or send blind eSoC
notifications. It should first build a fail-closed V1321 gate that either
observes or reproduces the Android `mdm_helper`/`ks`/MHI image-link
contract with explicit timeout and cleanup.

## Safety

Host-only classifier. No device command, tracefs write, PM actor start,
live eSoC ioctl/notify, PMIC write, userspace GPIO line request/hold,
direct eSoC ioctl, Wi-Fi HAL start, scan/connect, credential use,
DHCP/routes, external ping, flash, boot image write, or partition write
occurred.
