# Native Init V791 Current Warning Route Classifier Plan

## Goal

Classify the current V790 warning boundary without touching the device, then
route the next live Wi-Fi gate toward the actual WLFW continuation blocker.

## Scope

- Compare V790 lower-only evidence against V788, V787, V733, and V735.
- Reconcile the current warning with older Android/post-warning continuation
  reports V649, V650, and V651.
- Extract bounded dmesg timing for service `180`, service `74`, ASoC probe,
  `pm_qos`, sound-card registration, WLFW, BDF, and `wlan0`.
- Decide whether the exact ASoC `pm_qos` warning should remain the first
  blocker or become a guarded known-warning condition for the next CNSS/WLFW
  readback.

## Hard Gates

- Host-only only.
- No device command, reboot, mount, daemon start, Wi-Fi HAL, scan/connect,
  credential use, DHCP/routes, external ping, boot image write, partition
  write, or custom kernel flash.
- No broad evidence scan: local reads are bounded.
- No Wi-Fi secret material in tracked output.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_current_warning_route_classifier_v791.py
python3 scripts/revalidation/native_wifi_current_warning_route_classifier_v791.py plan
python3 scripts/revalidation/native_wifi_current_warning_route_classifier_v791.py run
git diff --check
```

## Expected Routing

- If V790 lacks the exact ASoC `pm_qos` signature, keep warning as the first
  blocker and recapture.
- If V649/V650 Android continuation evidence is missing, keep warning as the
  first blocker.
- If V790 has the exact lower-only ASoC warning and Android evidence proves the
  same class can continue to WLFW, route V792 to a known-warning-tolerant
  CNSS/WLFW readback gate below HAL/connect.
