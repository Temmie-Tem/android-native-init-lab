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

## Read-Only Device Preflight

After the prep commit, V409 read-only device preflight was run without deploy
approval.  It did not mutate the device, start daemons, start the Wi-Fi HAL, or
bring up Wi-Fi.

Helper v25 deploy preflight:

```text
evidence: tmp/wifi/v409-helper-v25-deploy-readonly-preflight-20260520-103906/
decision: execns-helper-v25-deploy-preflight-ready-needs-deploy
pass: True
reason: preflight complete; helper v25 deploy still requires exact approval
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

Key deploy-preflight checks:

```text
local-helper-v25: pass
local-helper-v25-query-guard: pass
native-clean: pass
service-manager-processes-clean: pass
wifi-link-surface-clean: pass
remote-helper-v25: needs-deploy
remote-helper-v25-query-guard: needs-deploy
approval-gate: needs-operator
```

NCM host ping was warning-only in auto transfer mode:

```text
ncm-host-reachable: warn
```

This does not block deploy because the deploy wrapper can use serial fallback.

V409 registration query preflight:

```text
evidence: tmp/wifi/v409-registration-query-readonly-preflight-20260520-103926/
decision: v409-hal-registration-query-blocked
pass: False
reason: blocked before live run by helper-v25
device_commands_executed: True
device_mutations: False
daemon_start_executed: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
```

Key query-preflight checks:

```text
v408-registration-surface-pass: pass
native-clean: pass
helper-v25: blocked
lshal-binary: pass
runtime-materials: pass
system-ext-vndk-v30: pass
service-manager-binaries: pass
process-surface-clean: pass
wifi-link-clean: pass
approval-gate: needs-operator
```

The important narrowing is:

```text
/mnt/system/system/bin/lshal exists and is usable for the direct V409 query path.
The remaining blocker is helper v25 deploy.
```

Additional approval-readiness guardcheck:

```text
evidence: tmp/wifi/v409-helper-v25-deploy-guardcheck-preflight-20260520-104455/
decision: execns-helper-v25-deploy-preflight-ready-needs-deploy
pass: True
local-helper-v25-query-guard: pass
remote-helper-v25-query-guard: needs-deploy
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

This confirms the local helper artifact contains both the new mode and the
explicit `--allow-hal-service-query` guard before any approved deploy.

## Interpretation

V409 is ready for the next operator-approved live step, but it has not been
executed live.

The direct query path depends on `/mnt/system/system/bin/lshal`.  Read-only
preflight now proves that it is present.  Therefore the next live step remains
helper v25 deploy only.  The actual registration query remains a separate later
approval after deploy and post-deploy preflight.

## Next Target

First live gate:

```text
approve v409 deploy execns helper v25 only; no daemon start and no Wi-Fi bring-up
```

Approved deploy command:

```bash
OUT=tmp/wifi/v409-execns-helper-v25-deploy-live-$(date +%Y%m%d-%H%M%S)
python3 scripts/revalidation/wifi_execns_helper_v25_deploy_preflight.py \
  --out-dir "$OUT" \
  --approval-phrase 'approve v409 deploy execns helper v25 only; no daemon start and no Wi-Fi bring-up' \
  --apply \
  --assume-yes \
  run
```

Post-deploy read-only preflight command:

```bash
OUT=tmp/wifi/v409-registration-query-post-deploy-preflight-$(date +%Y%m%d-%H%M%S)
python3 scripts/revalidation/wifi_hal_registration_query_v409_runner.py \
  --out-dir "$OUT" \
  preflight
```

Second live gate, only after deploy and preflight:

```text
approve v409 bounded lshal registration query only; no scan/connect/link-up and no Wi-Fi bring-up
```
