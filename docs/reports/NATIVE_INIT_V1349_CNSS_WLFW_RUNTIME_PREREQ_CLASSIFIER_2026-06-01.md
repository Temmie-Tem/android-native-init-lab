# Native Init V1349 CNSS/WLFW Runtime Prerequisite Classifier

## Summary

- Cycle: `V1349`
- Type: host-only evidence classifier
- Decision: `v1349-cnss-pm-register-blocker-is-next-prereq`
- Result: PASS
- Evidence:
  - `tmp/wifi/v1349-cnss-wlfw-runtime-prereq-classifier/manifest.json`
  - `tmp/wifi/v1349-cnss-wlfw-runtime-prereq-classifier/summary.md`
- Script: `scripts/revalidation/native_wifi_cnss_wlfw_runtime_prereq_classifier_v1349.py`

## Key Facts

| fact | value |
| --- | --- |
| CNSS upper path | V924/V966: native reaches `cld80211` but not `wlfw_start`; Android reaches `wlfw_start`, QMI, BDF, FW-ready, and `wlan0` |
| PM register path | V1100-V1102: CNSS PM register enters `pm-service`, blocks before return/connect, and stops at the second/modem helper `0x9538` boundary |
| PM callback path | V1171-V1172: PM `state=2` callback reaches `cnss-daemon`, but the callback body only acknowledges and returns |
| Current branch | V1348 blocks lower PMIC/GPIO/GDSC/eSoC mutation and selects CNSS/WLFW runtime prerequisites |

## Decision

existing evidence converges on CNSS PM register/connect/vote as the missing prerequisite: native CNSS reaches netlink but not wlfw_start, Android wlfw_start belongs to the service window, CNSS PM register blocks in pm-service before connect, and the PM callback body is ack-only

The next unit should not chase another blind lower eSoC trigger. The highest-signal prerequisite is the CNSS PM register/connect/vote path: native `cnss-daemon` never gets past register, so it cannot issue the same PM continuation that Android's service window reaches before WLFW/QMI/BDF progress.

## Next

V1350 should define a compact PM register helper/mutex observer before any lower eSoC mutation

## Safety

Host-only classifier. No device command, helper deploy, daemon start, PM actor, tracefs/sysfs/debugfs write, eSoC ioctl/notify, PMIC/GPIO/GDSC write, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, flash, boot image write, or partition write occurred.
