# Native Init v409 Wi-Fi HAL Registration Query Prep

## Summary

V409 preparation is implemented and fail-closed.

No live helper deploy, daemon start, HAL start, `lshal` execution, or Wi-Fi
bring-up was executed in this prep step.

Prepared artifacts:

- helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- helper artifact: `tmp/wifi/v409-a90_android_execns_probe-v25/a90_android_execns_probe`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v25_deploy_preflight.py`
- query runner: `scripts/revalidation/wifi_hal_registration_query_v409_runner.py`
- plan: `docs/plans/NATIVE_INIT_V409_HAL_REGISTRATION_QUERY_PLAN_2026-05-20.md`

## Helper Build

Helper v25 was built as a static ARM64 binary:

```text
artifact: tmp/wifi/v409-a90_android_execns_probe-v25/a90_android_execns_probe
sha256: e90639d55dacc5486c998c4d1470235a6c72e4759cc63ebd1f07cf90c5852b37
file: ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped
dynamic section: none
```

Required strings were present:

```text
a90_android_execns_probe v25
wifi-hal-composite-lshal-list
--allow-hal-service-query
wifi_hal_service_query.result=service-query-pass
```

## New Helper Mode

V25 adds a single bounded query mode:

```text
--mode wifi-hal-composite-lshal-list
--allow-service-manager-start-only
--allow-wifi-hal-start-only
--allow-hal-service-query
```

The query child is fixed to:

```text
/system/bin/lshal
```

It records:

```text
wifi_hal_service_query.exists
wifi_hal_service_query.executable
wifi_hal_service_query.exec_attempted
wifi_hal_service_query.exit_code
wifi_hal_service_query.signal
wifi_hal_service_query.timed_out
wifi_hal_service_query.result
wifi_hal_service_query.reason
```

## Safety Boundary

The helper and runner keep these exclusions:

```text
scan_connect_linkup=0
credentials=0
dhcp_routing=0
no wificond
no supplicant
no hostapd
no cnss_diag
no persistence/autostart
no Wi-Fi bring-up
```

The new `--allow-hal-service-query` flag is required in addition to the service
manager and HAL start-only flags.  Without the exact live approval phrase, the
runner writes an approval-required manifest and executes no device command.

## Fail-Closed Evidence

V409 registration query plan:

```text
evidence: tmp/wifi/v409-registration-query-plan-20260520-103706/
decision: v409-hal-registration-query-plan-ready
pass: True
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
```

V409 registration query no-approval run:

```text
evidence: tmp/wifi/v409-registration-query-noapproval-20260520-103706/
decision: v409-hal-registration-query-approval-required
pass: True
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
```

V409 helper v25 deploy plan:

```text
evidence: tmp/wifi/v409-helper-v25-deploy-plan-20260520-103706/
decision: execns-helper-v25-deploy-plan-ready
pass: True
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

V409 helper v25 deploy no-approval run:

```text
evidence: tmp/wifi/v409-helper-v25-deploy-noapproval-20260520-103706/
decision: execns-helper-v25-deploy-approval-required
pass: True
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

Manifest assertion check:

```text
v409 fail-closed assertions: PASS
```

## Interpretation

V409 is ready for the next operator-approved live step, but it has not been
executed live.

The direct query path depends on `/mnt/system/system/bin/lshal`.  If preflight
finds it missing, the correct next step is not Wi-Fi bring-up.  Route to V410
for either Android-side `lshal` extraction or a minimal private-namespace HIDL
service-list client.

## Next Target

First live gate:

```text
approve v409 deploy execns helper v25 only; no daemon start and no Wi-Fi bring-up
```

Second live gate, only after deploy and preflight:

```text
approve v409 bounded lshal registration query only; no scan/connect/link-up and no Wi-Fi bring-up
```
