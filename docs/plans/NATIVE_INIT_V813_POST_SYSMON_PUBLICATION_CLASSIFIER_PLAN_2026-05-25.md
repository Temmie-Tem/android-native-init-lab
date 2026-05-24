# Native Init V813 Post-Sysmon Publication Classifier Plan

## Goal

Use existing V812/V811/V785/V783/V626/V739 evidence to classify the next
post-sysmon mdm3/WLAN-PD service-publication blocker without any new device
command.

## Scope

- Target script:
  - `scripts/revalidation/native_wifi_post_sysmon_publication_classifier_v813.py`
- Inputs:
  - V812 current-stock live observer result.
  - V811 WLFW publication precondition classifier.
  - V785 Android/native memshare delta classifier.
  - V783 Android/native post-sysmon gap classifier.
  - V626 Android/native post-service180 publication classifier.
  - V739 Android/native mdm3/WLAN-PD delta classifier.

## Hard Gates

- Host-only: no device command.
- No custom kernel flash, boot image write, partition write, reboot, or
  bootloader handoff.
- No Wi-Fi HAL, `wificond`, supplicant, hostapd, scan/connect/link-up, or
  credential use.
- No DHCP, route change, or external ping.
- No `boot_wlan`, `qcwlanstate`, `esoc0`, bind/unbind, driver override, or
  module load/unload.
- No Wi-Fi secret material in tracked output.

## Success Criteria

- V813 compiles and plan-only manifest passes.
- All required prior manifests are present and passed.
- V812 proves current sysmon-without-service69 under the lower observer.
- V785 demotes memshare/CMA failure as the sole blocker.
- V783/V626 prove the Android/native post-sysmon divergence: Android has
  sibling sysmon plus service74/WLAN-PD/WLFW, while native lacks sibling sysmon,
  service74, WLAN-PD, WLFW, BDF, and `wlan0`.
- Classifier selects V814 as a below-HAL sibling sysmon/service-publication
  precondition isolation step.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_post_sysmon_publication_classifier_v813.py

python3 scripts/revalidation/native_wifi_post_sysmon_publication_classifier_v813.py \
  --out-dir tmp/wifi/v813-post-sysmon-publication-classifier-plan-check \
  plan

python3 scripts/revalidation/native_wifi_post_sysmon_publication_classifier_v813.py run

git diff --check
```
