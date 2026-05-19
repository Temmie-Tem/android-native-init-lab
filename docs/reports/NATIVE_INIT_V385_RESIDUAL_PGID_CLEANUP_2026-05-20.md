# Native Init v385 Residual PGID Cleanup Readiness Report

## Summary

v385 prepares `a90_android_execns_probe v16` to close the v384 helper-internal postflight proof gap. The change is local/tooling-only at this point: helper v16 has been built and wrappers are fail-closed, but `/cache/bin/a90_android_execns_probe` on the device is still v15 until exact v385 deploy approval is supplied.

## Implemented Changes

- `stage3/linux_init/helpers/a90_android_execns_probe.c`
  - marker bumped to `a90_android_execns_probe v16`.
  - added `/proc` process-group scan evidence helper.
  - ptrace-lite service-manager start-only path now records residual process group cleanup fields:
    - `service_manager_start.residual_kill_sent`
    - `service_manager_start.residual_cleared`
    - `service_manager_start.residual_before_count`
    - `service_manager_start.residual_after_count`
    - `service_manager_start.pgid_scan.before_final_kill.*`
    - `service_manager_start.pgid_scan.after_final_kill.*`
- Added v385 wrappers:
  - `scripts/revalidation/wifi_execns_helper_v16_deploy_preflight.py`
  - `scripts/revalidation/wifi_service_manager_start_only_v385_live_runner.py`
  - `scripts/revalidation/wifi_v385_deploy_live_executor.py`

## Local Artifact

- path: `tmp/wifi/v385-a90_android_execns_probe-v16/a90_android_execns_probe`
- file: `ELF 64-bit LSB executable, ARM aarch64, statically linked`
- sha256: `4478c73518e950b425af0cf7db28e9570c983f428fbb0d4b5d2ee45573d37cd8`
- strings markers confirmed:
  - `a90_android_execns_probe v16`
  - `service-manager-start-only`
  - `ptrace-lite`
  - `service_manager_start.residual_kill_sent`
  - `pgid_scan`

## Validation Performed

### Static

- helper build: PASS
- `python3 -m py_compile` on v385 wrappers and shared host scripts: PASS
- `git diff --check`: PASS
- ARM64 helper host execution: expected `Exec format error`; verification uses `file`, `sha256sum`, and `strings`.

### No-Approval Gates

- executor plan evidence: `tmp/wifi/v385-plan-20260520-045123/`
  - decision: `v385-deploy-live-executor-plan-ready`
  - device commands executed: `False`
  - device mutations: `False`
  - daemon start: `False`
  - Wi-Fi bring-up: `False`
- no-approval live evidence: `tmp/wifi/v385-noapproval-live-20260520-045123/`
  - decision: `v385-deploy-live-executor-approval-required`
  - device commands executed: `False`
  - device mutations: `False`
  - daemon start: `False`
  - Wi-Fi bring-up: `False`
- no-approval deploy/preflight evidence: `tmp/wifi/v385-noapproval-deploy-20260520-045123/`
  - decision: `execns-helper-v16-deploy-blocked`
  - reason: remote helper is still v15.
  - device mutations: `False`
  - daemon start: `False`
  - Wi-Fi bring-up: `False`
- live preflight evidence: `tmp/wifi/v385-live-preflight-20260520-045158/`
  - decision: `service-manager-start-only-live-blocked`
  - blocker: helper v16 not deployed.
  - daemon start: `False`
  - Wi-Fi bring-up: `False`

## Current Device State Observed During Preflight

- native version: `A90 Linux init 0.9.61 (v319)`
- selftest: `pass=11 warn=1 fail=0`
- `/cache/bin/a90_android_execns_probe`: v15 SHA `dfd543c02ccefbbbcf2fe0eb7ee168b40d40363927a63104c7aef0b9aed0bb16`
- service-manager binaries visible: `servicemanager=True`, `hwservicemanager=True`
- temporary Binder nodes clean: `binder=False`, `hwbinder=False`, `vndbinder=False`
- Wi-Fi link count: `0`

## Required Approval Phrases

Deploy:

```text
approve v385 deploy execns helper v16 only; no daemon start and no Wi-Fi bring-up
```

Live:

```text
approve v385 service-manager residual pgid cleanup only; no Wi-Fi HAL start and no Wi-Fi bring-up
```

## Next Step

If the operator accepts the scope, run v385 deploy first, then v385 residual PGID live capture. Wi-Fi HAL/start/scan/connect/link-up remains blocked until service-manager lifecycle cleanup is proven.
