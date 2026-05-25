# Native Init V821 QRTR Nameservice Matrix Plan

## Goal

Run an in-helper AF_QIPCRTR nameservice lookup matrix for the candidate
service-locator, service-notifier, and WLFW services inside the known V817 lower
window.

## Scope

- Helper source:
  - `stage3/linux_init/helpers/a90_android_execns_probe.c`
- Host runners:
  - `scripts/revalidation/wifi_execns_helper_v125_deploy_preflight.py`
  - `scripts/revalidation/native_wifi_qrtr_nameservice_matrix_v821.py`
- Inputs:
  - `tmp/wifi/v820-qrtr-namespace-classifier/manifest.json`
  - V817 lower-window orchestration from
    `scripts/revalidation/native_wifi_in_window_sysmon_sampler_v817.py`
- Matrix:
  - `servloc:64:1`
  - `servnotif:66:74`
  - `servnotif:66:180`
  - `wlfw:69:0`
  - `wlfw:69:1`

## Hard Gates

- No custom kernel flash, boot image write, partition write, bootloader
  handoff, or new kernel artifact flash.
- No `esoc0` open, `qcwlanstate on/off`, bind/unbind, driver override, or
  module load/unload.
- No QMI payload transmission; only QRTR nameservice lookup/readback.
- No service-manager, Wi-Fi HAL, wificond, supplicant, scan/connect/link-up, or
  credential use.
- No DHCP, route change, or external ping.
- Preserve V775 custom OSRC kernel flashing pause.

## Success Criteria

- Helper v125 builds as static aarch64 and exposes `--qrtr-readback-matrix`.
- V821 plan and helper deploy preflight pass.
- Approved live run deploys helper v125 if needed and executes the V817 lower
  window with the matrix option.
- Matrix emits exactly five cases, all with AF_QIPCRTR socket family `42`,
  lookup send rc `0`, delete lookup send rc `0`, and no timeouts.
- `qmi_attempted=0`, `qmi_payload=0`, and all Wi-Fi HAL/connect/networking
  guardrails remain false.
- Result labels whether candidate service publication is visible or clean-empty.

## Validation

```bash
python3 -m py_compile \
  scripts/revalidation/native_wifi_qrtr_nameservice_matrix_v821.py \
  scripts/revalidation/wifi_execns_helper_v125_deploy_preflight.py

scripts/revalidation/build_android_execns_probe_helper.sh \
  tmp/wifi/v821-execns-helper-v125-build/a90_android_execns_probe

python3 scripts/revalidation/native_wifi_qrtr_nameservice_matrix_v821.py \
  --out-dir tmp/wifi/v821-qrtr-nameservice-matrix-plan-check-current \
  plan

python3 scripts/revalidation/wifi_execns_helper_v125_deploy_preflight.py \
  --out-dir tmp/wifi/v821-helper-v125-deploy-plan-check-current \
  plan

python3 scripts/revalidation/native_wifi_qrtr_nameservice_matrix_v821.py \
  preflight

python3 scripts/revalidation/native_wifi_qrtr_nameservice_matrix_v821.py \
  run
```

## Next

If V821 observes any service publication, the next cycle should classify the
visible service before any QMI payload, daemon, HAL, scan/connect, credential,
DHCP, route, or external ping step.

If the matrix is clean-empty, V822 should classify why kernel dmesg shows
sysmon/service-locator progress while AF_QIPCRTR nameservice publication remains
empty below HAL/connect.
