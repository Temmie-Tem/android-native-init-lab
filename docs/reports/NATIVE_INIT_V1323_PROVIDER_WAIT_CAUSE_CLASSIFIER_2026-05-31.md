# Native Init V1323 Provider Wait-cause Classifier

## Summary

- Cycle: `V1323`
- Type: host-only provider wait-cause classifier
- Decision: `v1323-provider-wait-cause-is-proprietary-powerup-response`
- Result: PASS
- Evidence:
  - `tmp/wifi/v1323-provider-wait-cause-classifier/manifest.json`
  - `tmp/wifi/v1323-provider-wait-cause-classifier/summary.md`
- Script: `scripts/revalidation/native_wifi_provider_wait_cause_classifier_v1323.py`

V1323 reconciles the public Samsung OSRC subsystem restart code with
retained live evidence. The public SSR path calls the board provider
`powerup()` before `wait_for_err_ready()`, and the staged OSRC tree does
not contain the proprietary `mdm_subsys_powerup` implementation. V849,
V918, and V963 place the live native block inside that provider path, with
stacks including `sdx50m_toggle_soft_reset`, `mdm4x_do_first_power_on`,
`mdm_cmd_exe`, and `mdm_subsys_powerup`. V1318/V1319 show that native
reaches PMIC soft-reset/GPIO1270 and AP2MDM/GPIO135 activity, but never
gets MDM2AP/GPIO142, PCIe RC1/MHI, WLFW/BDF, or `wlan0`. Android-positive
reference evidence still has those downstream responses.

## Decision

The current blocker is not public `wait_for_err_ready()` and not the
previous image-link/PM actor delivery gate. It is the proprietary ext-mdm
provider response path after SDX50M soft-reset/AP2MDM activity and before
GPIO142/PCIe/MHI/WLFW response. V1324 should classify Android-vs-native
provider response deltas around GPIO142, errfatal, soft-reset, and PCIe
timing from host/source evidence first. Only a bounded read-only or
reboot-bounded live sampler is justified after that classification.

## Safety

Host-only classifier. No device command, PM actor start, `mdm_helper` start,
tracefs write, live eSoC ioctl/notify, PMIC write, GPIO line request, direct
GDSC/eSoC write, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes,
external ping, flash, boot image write, or partition write occurred.
