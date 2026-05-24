# Native Init V804 PLD/ICNSS Register/Probe Prerequisite Classifier Plan

## Goal

Use existing V802/V803 evidence, V775 custom-kernel boot-failure postmortem,
stock v724 config, and staged Samsung OSRC source to decide whether the current
blocker is still PLD/ICNSS registration itself or the downstream ICNSS
`FW_READY`/probe/WLFW gate.

## Scope

- Target script:
  - `scripts/revalidation/native_wifi_pld_icnss_register_probe_prereq_classifier_v804.py`
- Inputs:
  - V775 boot incompatibility postmortem manifest.
  - V803 HDD/PLD prerequisite classifier manifest.
  - V802 provider-first `boot_wlan` dmesg and runtime surface.
  - V772 stock v724 kernel config.
  - Staged Samsung OSRC source under
    `tmp/wifi/v766-icnss-qcacld-patch-apply-build/source`.
- Source targets:
  - `wlan_hdd_main.c`
  - `wlan_hdd_driver_ops.c`
  - `pld_common.c`
  - `pld_snoc.c`
  - `icnss.c`
  - QCACLD `Kbuild`

## Hard Gates

- Host-only: no device command.
- No custom kernel flash, boot image write, partition write, or reboot.
- No Wi-Fi HAL, `wificond`, supplicant, hostapd, scan/connect, credentials,
  DHCP, route change, or external ping.
- No `boot_wlan`, `qcwlanstate`, `esoc0`, bind/unbind, module load/unload, or
  driver override.
- No Wi-Fi secret material in tracked output.

## Success Criteria

- V804 compiles and plan-only manifest passes.
- V803 prerequisite boundary is present and passed.
- V775 evidence keeps custom-kernel flashing out of the next loop.
- Stock config confirms the ICNSS/SNOC route rather than CNSS2/PCIe.
- Source confirms PLD register prerequisites and ICNSS non-sync registration
  semantics.
- V802 evidence is reclassified without over-reading `qcwlanstate` OFF or
  `Modules not initialized` as a standalone PLD register failure.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pld_icnss_register_probe_prereq_classifier_v804.py

python3 scripts/revalidation/native_wifi_pld_icnss_register_probe_prereq_classifier_v804.py \
  --out-dir tmp/wifi/v804-pld-icnss-register-probe-prereq-plan-check \
  plan

python3 scripts/revalidation/native_wifi_pld_icnss_register_probe_prereq_classifier_v804.py run

git diff --check
```
