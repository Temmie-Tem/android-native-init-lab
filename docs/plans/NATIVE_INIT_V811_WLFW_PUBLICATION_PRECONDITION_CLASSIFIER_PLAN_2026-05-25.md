# Native Init V811 WLFW Publication Precondition Classifier Plan

## Goal

Use V810 plus existing Android/native lower-path evidence to classify why WLFW
service69 remains unpublished in native init, before any new live trigger.

## Scope

- Target script:
  - `scripts/revalidation/native_wifi_wlfw_publication_precondition_classifier_v811.py`
- Inputs:
  - V810 register/probe WLFW/FW_READY classifier.
  - V808 true-overlap provider-first + `boot_wlan` evidence.
  - V739 Android/native mdm3/WLAN-PD delta.
  - V626 post-service180 publication classifier.
  - V731/V733/V735/V738 native lower-path observers.

## Hard Gates

- Host-only: no device command.
- No custom kernel flash, boot image write, partition write, or reboot.
- No Wi-Fi HAL, `wificond`, supplicant, hostapd, scan/connect, credentials,
  DHCP, route change, or external ping.
- No `boot_wlan`, `qcwlanstate`, `esoc0`, bind/unbind, module load/unload, or
  driver override.
- No Wi-Fi secret material in tracked output.

## Success Criteria

- V811 compiles and plan-only manifest passes.
- V810 is present, passed, and maps QCACLD probe to the WLFW/FW_READY gate.
- Android reference shows mss/mdm3 online plus WLAN-PD/WLFW/BDF/`wlan0`.
- Native references show mss/QRTR/sysmon/service-notifier progress but mdm3
  remains `OFFLINING` and WLFW/service69 remains absent.
- QRTR service69 readback is clean-empty, not a readback timeout.
- Classifier selects the next blocker as mdm3/WLAN-PD/WLFW publication
  preconditions, still below HAL/scan/connect.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_wlfw_publication_precondition_classifier_v811.py

python3 scripts/revalidation/native_wifi_wlfw_publication_precondition_classifier_v811.py \
  --out-dir tmp/wifi/v811-wlfw-publication-precondition-classifier-plan-check \
  plan

python3 scripts/revalidation/native_wifi_wlfw_publication_precondition_classifier_v811.py run

git diff --check
```
