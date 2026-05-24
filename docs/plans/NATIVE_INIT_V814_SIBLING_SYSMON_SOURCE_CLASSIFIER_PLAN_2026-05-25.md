# Native Init V814 Sibling Sysmon Source Classifier Plan

## Goal

Use V813 plus staged Samsung OSRC source to determine whether the next blocker
belongs to kernel subsystem/sysmon/service-notifier registration state rather
than userspace HAL/connect retry.

## Scope

- Target script:
  - `scripts/revalidation/native_wifi_sibling_sysmon_source_classifier_v814.py`
- Inputs:
  - V813 post-sysmon publication classifier.
  - Samsung OSRC source staged under `kernel_build/SM-A908N_KOR_12_Opensource/Kernel`.
- Source targets:
  - `drivers/soc/qcom/service-notifier.c`
  - `include/soc/qcom/service-notifier.h`
  - `drivers/soc/qcom/sysmon-qmi.c`
  - `drivers/soc/qcom/sysmon.c`
  - `drivers/soc/qcom/subsystem_restart.c`
  - `include/soc/qcom/sysmon.h`
  - `include/linux/esoc_client.h`

## Hard Gates

- Host-only: no device command.
- No custom kernel flash, boot image write, partition write, reboot, or
  bootloader handoff.
- No Wi-Fi HAL, `wificond`, supplicant, hostapd, scan/connect/link-up, or
  credential use.
- No DHCP, route change, or external ping.
- No `boot_wlan`, `qcwlanstate`, `esoc0`, bind/unbind, driver override, or
  module load/unload.

## Success Criteria

- V814 compiles and plan-only manifest passes.
- V813 manifest is present and passed.
- Required OSRC source targets are present.
- Source anchors prove service-notifier uses SERVREG QMI listener registration
  and state indications.
- Source anchors prove sysmon is registered by subsystem registration and uses
  QMI lookup/send paths.
- Classifier routes V815 to a read-only stock-v724 subsystem/sysmon/service
  registration snapshot before any new trigger.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_sibling_sysmon_source_classifier_v814.py

python3 scripts/revalidation/native_wifi_sibling_sysmon_source_classifier_v814.py \
  --out-dir tmp/wifi/v814-sibling-sysmon-source-classifier-plan-check \
  plan

python3 scripts/revalidation/native_wifi_sibling_sysmon_source_classifier_v814.py run

git diff --check
```
