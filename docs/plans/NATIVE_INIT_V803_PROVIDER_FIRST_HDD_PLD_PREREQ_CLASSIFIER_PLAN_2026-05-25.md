# Native Init V803 Provider-first HDD/PLD Prerequisite Classifier Plan

## Goal

Use V802 live evidence and staged Samsung OSRC source to classify the exact
source-level boundary after `wlan: Loading driver` without running another
device action.

## Scope

- Target script:
  - `scripts/revalidation/native_wifi_provider_first_hdd_pld_prereq_classifier_v803.py`
- Inputs:
  - V802 orchestrated manifest and direct manifest.
  - V802 `dmesg-delta.txt` and `boot-wlan-observe-after-cnss.txt`.
  - Staged Samsung OSRC source under `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source`.
- Source targets:
  - `wlan_hdd_main.c`
  - `wlan_hdd_driver_ops.c`
  - `pld_snoc.c`
  - `icnss.c`

## Hard Gates

- Host-only: no device command.
- No Wi-Fi HAL, `wificond`, supplicant, hostapd, scan/connect, credentials,
  DHCP, route change, or external ping.
- No `boot_wlan`, `qcwlanstate`, `esoc0`, bind/unbind, module, partition, boot
  image, reboot, or custom kernel action.
- No Wi-Fi secret material in tracked output.

## Success Criteria

- V803 compiles and plan-only manifest passes.
- V802 is present, passed, and did not cross the connection boundary.
- V802 confirms provider-first context and bounded `boot_wlan` executed.
- OSRC source order confirms `driver loaded` is after PLD/register-driver.
- Classifier selects the next non-flash boundary for V804.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_provider_first_hdd_pld_prereq_classifier_v803.py

python3 scripts/revalidation/native_wifi_provider_first_hdd_pld_prereq_classifier_v803.py \
  --out-dir tmp/wifi/v803-provider-first-hdd-pld-prereq-plan-check \
  plan

python3 scripts/revalidation/native_wifi_provider_first_hdd_pld_prereq_classifier_v803.py run

git diff --check
```
