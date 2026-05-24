# Native Init V807 Pre-WLFW Overlap Classifier Plan

## Goal

Classify whether V806 failed before WLFW publication because provider-first
companion services were executed sequentially and cleaned up before the
`boot_wlan` observe window, rather than being held alive across that window.

## Scope

- Target script:
  - `scripts/revalidation/native_wifi_pre_wlfw_overlap_classifier_v807.py`
- Inputs:
  - V805 classifier manifest.
  - V806 live gate manifest.
  - V806 internal V802 direct manifest.
  - V752/V802 source order.
- Evidence output:
  - `tmp/wifi/v807-pre-wlfw-overlap-classifier/`

## Hard Gates

- Host-only: no device command.
- No custom kernel flash, boot image write, partition write, reboot, Wi-Fi HAL,
  scan/connect, credentials, DHCP, route change, external ping, `boot_wlan`,
  `qcwlanstate`, `esoc0`, bind/unbind, or module action.
- No Wi-Fi secret material in tracked output.

## Success Criteria

- V807 compiles and plan-only manifest passes.
- V805/V806 inputs are present and passed.
- Source confirms V752/V802 runs companion helper before `boot_wlan` rather than
  concurrently.
- Evidence confirms critical companion children exited/postflight-cleaned before
  the `boot_wlan` result.
- Classifier selects whether V808 should run an overlapped companion +
  `boot_wlan` live gate.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pre_wlfw_overlap_classifier_v807.py

python3 scripts/revalidation/native_wifi_pre_wlfw_overlap_classifier_v807.py \
  --out-dir tmp/wifi/v807-pre-wlfw-overlap-plan-check \
  plan

python3 scripts/revalidation/native_wifi_pre_wlfw_overlap_classifier_v807.py run

git diff --check
```
