# Native Init v387 Ptrace Timeout Cleanup Readiness

## Summary

V387 adds `a90_android_execns_probe v18` and V387 fail-closed wrappers. The helper changes the service-manager `ptrace-lite` timeout cleanup path so ptrace stop events are continued with the intended termination signal and are not counted as a reap.

This is local/static verified and read-only preflight checked. It has not been deployed to the device and has not started service-manager daemons under V387.

Wi-Fi HAL, scan, connect, credentials, DHCP, routing, rfkill writes, firmware mutation, and driver bind/unbind were not executed.

## Root Cause From v386

V386 compact capture fixed the serial output blocker, but `system-hwservicemanager` still ended as `start-only-reboot-required`. The evidence showed a stopped tracee becoming a zombie after final kill while the helper had already emitted `service_manager_start.reaped=1`.

That means the timeout cleanup loop could treat `WIFSTOPPED` as cleanup completion. This is not a terminal wait status.

## Change

- Helper marker: `a90_android_execns_probe v18`.
- Added `wait_traced_child_for_cleanup()` for service-manager ptrace timeout cleanup.
- TERM cleanup now continues stopped tracees with `SIGTERM`.
- KILL cleanup now continues stopped tracees with `SIGKILL`.
- `service_manager_start.reaped=1` is set only after `WIFEXITED` or `WIFSIGNALED`.
- Added compact machine-readable cleanup fields:
  - `service_manager_start.cleanup.<phase>.stop.signal`
  - `service_manager_start.cleanup.<phase>.stop.event`
  - `service_manager_start.cleanup.<phase>.stop.deliver_signal`
  - `service_manager_start.cleanup_stop_continued`
  - `service_manager_start.cleanup_stop_last_signal`
  - `service_manager_start.cleanup_continue_errors`

## Artifacts

Local helper:

```text
tmp/wifi/v387-a90_android_execns_probe-v18/a90_android_execns_probe
```

SHA256:

```text
1131f0e3dd61bafc5023c25d7fb019303902cdf6cea76dd2e09b44b13a42378e
```

Wrappers:

- `scripts/revalidation/wifi_execns_helper_v18_deploy_preflight.py`
- `scripts/revalidation/wifi_service_manager_start_only_v387_live_runner.py`
- `scripts/revalidation/wifi_v387_deploy_live_executor.py`

Plan:

- `docs/plans/NATIVE_INIT_V387_PTRACE_TIMEOUT_CLEANUP_PLAN_2026-05-20.md`

## Validation

Static build:

```text
bash scripts/revalidation/build_android_execns_probe_helper.sh tmp/wifi/v387-a90_android_execns_probe-v18/a90_android_execns_probe
```

Result:

```text
ELF 64-bit LSB executable, ARM aarch64, statically linked
There is no dynamic section in this file.
```

Required strings:

```text
a90_android_execns_probe v18
service_manager_start.capture_detail=compact
service_manager_start.cleanup.%s.stop.deliver_signal=%d
service_manager_start.cleanup_stop_continued=%d
service_manager_start.cleanup_continue_errors=%d
```

Python compile:

```text
python3 -m py_compile scripts/revalidation/wifi_execns_helper_v18_deploy_preflight.py scripts/revalidation/wifi_service_manager_start_only_v387_live_runner.py scripts/revalidation/wifi_v387_deploy_live_executor.py
```

Result: PASS.

Plan-only/no-approval evidence:

```text
tmp/wifi/v387-static-20260520-055116/
```

Results:

- deploy plan: `execns-helper-v18-deploy-plan-ready`, device mutation `False`, daemon start `False`, Wi-Fi bring-up `False`.
- live plan: `service-manager-start-only-live-plan-ready`, daemon start `False`, Wi-Fi bring-up `False`.
- executor plan: `v387-deploy-live-executor-plan-ready`, device command `False`, device mutation `False`, daemon start `False`, Wi-Fi bring-up `False`.
- no-approval full executor: `v387-deploy-live-executor-approval-required`, device command `False`, device mutation `False`, daemon start `False`, Wi-Fi bring-up `False`.

Read-only real-device preflight evidence:

```text
tmp/wifi/v387-readonly-preflight-20260520-055124/
```

Results:

- deploy preflight: `execns-helper-v18-deploy-blocked`, blocker `remote-helper-v18`, device mutation `False`, daemon start `False`, Wi-Fi bring-up `False`.
- live preflight: `service-manager-start-only-live-blocked`, blocker `helper-v18`, daemon start `False`, Wi-Fi bring-up `False`.

This is expected because the device still has helper v17 until V387 deploy is explicitly approved.

`git diff --check`: PASS.

## Approval Required For Live

Deploy approval phrase:

```text
approve v387 deploy execns helper v18 only; no daemon start and no Wi-Fi bring-up
```

Live approval phrase:

```text
approve v387 service-manager ptrace timeout cleanup only; no Wi-Fi HAL start and no Wi-Fi bring-up
```

## Next Step

Run V387 deployment only after the exact deploy approval phrase. Then run the bounded service-manager ptrace timeout cleanup smoke only after the exact live approval phrase.

Wi-Fi HAL/start/scan/connect remains blocked until V387 proves clean service-manager lifecycle handling.
