# Native Init v409 Wi-Fi HAL Registration Query Prep

## Summary

V409 preparation is implemented and fail-closed.

No live helper deploy, daemon start, HAL start, `lshal` execution, or Wi-Fi
bring-up was executed in this prep step.

V409 is superseded by V410 before live deploy.  Do not execute the V409 deploy
approval path; use the V410 helper v26 deploy gate instead.

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

V409 is superseded by V410 and must not be used for live deploy or live query.

The direct query path proved that `/mnt/system/system/bin/lshal` is present, but
the V409 approved command stayed inside the native argument budget only by
omitting explicit `--data-wifi-mode private-empty`.  V410 fixed that by moving
the private-empty data boundary into helper v26 defaults.

## Superseded Refusal Evidence

The V409 deploy wrapper is now a superseded fail-closed gate.  Even when invoked
with the old exact approval phrase and `--apply --assume-yes`, it writes
evidence and executes no device command.

```text
evidence: tmp/wifi/v409-helper-v25-deploy-superseded-20260520-111400/
decision: v409-superseded-by-v410
pass: True
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
```

The V409 registration-query runner is also a superseded fail-closed gate.

```text
evidence: tmp/wifi/v409-registration-query-superseded-20260520-111400/
decision: v409-superseded-by-v410
pass: True
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
```

Both evidence directories are private and use no-follow exclusive evidence
writes:

```text
700 tmp/wifi/v409-helper-v25-deploy-superseded-20260520-111400
600 tmp/wifi/v409-helper-v25-deploy-superseded-20260520-111400/manifest.json
600 tmp/wifi/v409-helper-v25-deploy-superseded-20260520-111400/README.md
700 tmp/wifi/v409-registration-query-superseded-20260520-111400
600 tmp/wifi/v409-registration-query-superseded-20260520-111400/manifest.json
600 tmp/wifi/v409-registration-query-superseded-20260520-111400/README.md
```

## Replacement Target

Use the V410 runner only:

```text
scripts/revalidation/wifi_hal_registration_query_v410_runner.py
```

The next live gate is:

```text
approve v410 bounded lshal registration query only; no scan/connect/link-up and no Wi-Fi bring-up
```
