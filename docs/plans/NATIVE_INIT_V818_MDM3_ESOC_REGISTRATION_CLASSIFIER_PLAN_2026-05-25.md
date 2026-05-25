# Native Init V818 mdm3/esoc0 Registration Classifier Plan

## Goal

Reconcile V817 in-window evidence with prior PIL/source evidence to classify
whether the next blocker is still mdm3/esoc0 service-locator/sysmon
registration, without contacting the device.

## Scope

- Target script:
  - `scripts/revalidation/native_wifi_mdm3_esoc_registration_classifier_v818.py`
- Inputs:
  - V817 in-window sysmon sampler manifest and after-companion evidence.
  - V798 PIL code gap classifier and source snippets.
  - V795 lower-window mdm3/esoc observer.

## Hard Gates

- Host-only: no device command.
- No custom kernel flash, boot image write, partition write, reboot, or
  bootloader handoff.
- No `esoc0` open, `qcwlanstate on/off`, bind/unbind, driver override, or
  module load/unload.
- No service-manager start, Wi-Fi HAL start, scan/connect/link-up, credential
  use, DHCP, route change, or external ping.

## Success Criteria

- V818 compiles and plan-only manifest passes.
- V817, V798, and V795 manifests are present and passed.
- V817 confirms mss/sysmon advance with mdm3/service publication absent.
- V798 confirms modem PIL absence is not the current blocker.
- V795 confirms holder-only retry is not enough.
- V817 after-companion evidence shows esoc sysfs/class surfaces but no
  `/dev/esoc*` or `/dev/subsys*` node.
- Classifier selects a bounded read-only V819 registration catalogue, not HAL,
  credentials, DHCP, external ping, or custom-kernel flash.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_mdm3_esoc_registration_classifier_v818.py

python3 scripts/revalidation/native_wifi_mdm3_esoc_registration_classifier_v818.py \
  --out-dir tmp/wifi/v818-mdm3-esoc-registration-classifier-plan-check \
  plan

python3 scripts/revalidation/native_wifi_mdm3_esoc_registration_classifier_v818.py run

git diff --check
```
