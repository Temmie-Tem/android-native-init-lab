# Native Init V1350 PM Register Supersession Classifier

## Summary

- Cycle: `V1350`
- Type: host-only corrective evidence classifier
- Decision: `v1350-pm-register-blocker-superseded-by-current-route`
- Result: PASS
- Evidence:
  - `tmp/wifi/v1350-pm-register-supersession-classifier/manifest.json`
  - `tmp/wifi/v1350-pm-register-supersession-classifier/summary.md`
- Script: `scripts/revalidation/native_wifi_pm_register_supersession_classifier_v1350.py`

## Key Facts

| fact | value |
| --- | --- |
| old blocker | V1103/V1107 prove the CNSS PM register mutex wait existed |
| superseded by ordering | V1108 removes the pre-CNSS `per_proxy` ordering and CNSS PM register/connect both return `0x0` |
| moved downward | V1109 moves the blocker below PM connect into `__subsystem_get` / `_request_firmware` |
| current route | V1345 reaches `mdm_subsys_powerup` but still sees no GPIO142/PCIe/MHI/WLFW/`wlan0` response |
| Android positive | V1347 reaches `wlfw_start`, ICNSS QMI, BDF, FW-ready, and `wlan0` |

## Decision

the old PM register mutex blocker is real but superseded: V1108 removes it and reaches CNSS PM connect, V1109 moves the blocker downward, and V1345's current route already reaches mdm_subsys_powerup with no lower response

V1349's PM-register conclusion is superseded as the immediate next branch. Repeating the old PM register/mutex observer would not move the current route forward, because the project already has evidence that CNSS PM connect can succeed and that the active blocker is now lower response plus Android-only WLFW request-path parity.

## Next

V1351 should define a compact current-route CNSS/WLFW precondition observer before any lower PMIC/GPIO/GDSC/eSoC mutation

## Safety

Host-only classifier. No device command, helper deploy, daemon start, PM actor, tracefs/sysfs/debugfs write, eSoC ioctl/notify, PMIC/GPIO/GDSC write, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, flash, boot image write, or partition write occurred.
