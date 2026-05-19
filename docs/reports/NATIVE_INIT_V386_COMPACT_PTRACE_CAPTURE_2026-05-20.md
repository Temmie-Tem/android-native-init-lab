# Native Init v386 Compact Ptrace Capture Readiness

## Summary

v386 adds `a90_android_execns_probe v17` with compact service-manager ptrace capture. The change is local/static verified and approval-gated. It has not been deployed to the device and has not started service-manager daemons.

Wi-Fi HAL, scan, connect, credentials, DHCP, routing, rfkill writes, firmware mutation, and driver bind/unbind were not executed.

## Root Cause From v385

v385 proved residual cleanup for `servicemanager`, but the `hwservicemanager` path printed large ptrace-lite exec snapshots to serial stdout. The host runner missed `A90P1 END` and did not parse the final `service_manager_start.*` fields, even though the bridge tail later showed eventual command completion.

## Change

- Helper marker: `a90_android_execns_probe v17`.
- Service-manager `ptrace-lite` now appends compact snapshot data to the helper stdout section instead of dumping raw `/proc/<pid>/maps` and `/proc/<pid>/mountinfo` directly to serial stdout.
- Added compact fields:
  - `service_manager_start.capture_detail=compact`
  - `capture.detail=compact`
  - `capture.<label>.exe`, `cwd`, `auxv.count`, `regset.nt_prstatus.bytes`
  - `capture.<label>.status/maps/mountinfo.bytes`, `lines`, `truncated`
- Preserved lifecycle and cleanup summary fields:
  - `service_manager_start.capture_exec`
  - `service_manager_start.capture_crash`
  - `service_manager_start.residual_kill_sent`
  - `service_manager_start.residual_cleared`
  - `service_manager_start.postflight_safe`
  - `service_manager_start.result`

## Artifacts

Local helper:

```text
tmp/wifi/v386-a90_android_execns_probe-v17/a90_android_execns_probe
```

SHA256:

```text
45c27e28c90a86c75a291edaf16d8233da51358647c1e6d1700f0e4f9cf437c5
```

Wrappers:

- `scripts/revalidation/wifi_execns_helper_v17_deploy_preflight.py`
- `scripts/revalidation/wifi_service_manager_start_only_v386_live_runner.py`
- `scripts/revalidation/wifi_v386_deploy_live_executor.py`

Plan:

- `docs/plans/NATIVE_INIT_V386_COMPACT_PTRACE_CAPTURE_PLAN_2026-05-20.md`

## Validation

Static build:

```text
bash scripts/revalidation/build_android_execns_probe_helper.sh tmp/wifi/v386-a90_android_execns_probe-v17/a90_android_execns_probe
```

Result:

```text
ELF 64-bit LSB executable, ARM aarch64, statically linked
There is no dynamic section in this file.
```

Required strings:

```text
a90_android_execns_probe v17
service_manager_start.capture_detail=compact
capture.detail=compact
```

Python compile:

```text
python3 -m py_compile scripts/revalidation/wifi_execns_helper_v17_deploy_preflight.py scripts/revalidation/wifi_service_manager_start_only_v386_live_runner.py scripts/revalidation/wifi_v386_deploy_live_executor.py
```

Result: PASS.

Plan-only evidence:

```text
tmp/wifi/v386-static-20260520-052719/
```

Results:

- deploy plan: `execns-helper-v17-deploy-plan-ready`, device mutation `False`, daemon start `False`, Wi-Fi bring-up `False`.
- live plan: `service-manager-start-only-live-plan-ready`, daemon start `False`, Wi-Fi bring-up `False`.
- executor plan: `v386-deploy-live-executor-plan-ready`, device command `False`, device mutation `False`, daemon start `False`, Wi-Fi bring-up `False`.

No-approval executor evidence:

```text
tmp/wifi/v386-noapproval-20260520-052729/
```

Result:

```text
decision: v386-deploy-live-executor-approval-required
pass: True
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

`git diff --check`: PASS.

## Approval Required For Live

Deploy approval phrase:

```text
approve v386 deploy execns helper v17 only; no daemon start and no Wi-Fi bring-up
```

Live approval phrase:

```text
approve v386 service-manager compact ptrace capture only; no Wi-Fi HAL start and no Wi-Fi bring-up
```

## Next Step

Run v386 deployment and live capture only after explicit approval. The expected success criterion is that `hwservicemanager` returns `A90P1 END` and contains machine-readable `service_manager_start.*` fields without manual bridge-tail recovery.
