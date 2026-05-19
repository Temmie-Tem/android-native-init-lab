# Native Init v389 Enhanced Crash Capture Readiness

## Summary

V389 adds `a90_android_execns_probe v19` with enhanced bounded crash capture for service-manager `ptrace-lite` crash snapshots. The helper now records selected AArch64 registers and bounded ASCII summaries from stack/register-pointer memory while the tracee is stopped.

This is local/static verified and read-only preflight checked. It has not been deployed to the device and has not started service-manager daemons under V389.

Wi-Fi HAL, scan, connect, credentials, DHCP, routing, rfkill writes, firmware mutation, and driver bind/unbind were not executed.

## Root Cause From v388

V388 proved the V387 `servicemanager` crash evidence was too compact: it had SIGABRT and a register-set byte count, but not selected PC/LR/SP/x0-x8 values, stack bytes, or abort-message memory/string scan. Without that, the exact AOSP fatal site cannot be selected.

## Change

- Helper marker: `a90_android_execns_probe v19`.
- Crash snapshots now emit selected `NT_PRSTATUS` fields:
  - x0-x8
  - lr/x30
  - sp
  - pc
  - pstate
- Crash snapshots now scan bounded memory:
  - stack at SP, up to 512 bytes.
  - plausible x0-x8 pointer targets, up to 128 bytes each.
- Memory output is compact ASCII summary only.
- V387 cleanup behavior remains unchanged.

## Artifacts

Local helper:

```text
tmp/wifi/v389-a90_android_execns_probe-v19/a90_android_execns_probe
```

SHA256:

```text
e3da79dec1c7ca58d3208fb0d9a55ce1411fff7159ab613ff9daf6d6befd3e6d
```

Wrappers:

- `scripts/revalidation/wifi_execns_helper_v19_deploy_preflight.py`
- `scripts/revalidation/wifi_service_manager_start_only_v389_live_runner.py`
- `scripts/revalidation/wifi_v389_deploy_live_executor.py`

Plan:

- `docs/plans/NATIVE_INIT_V389_ENHANCED_CRASH_CAPTURE_PLAN_2026-05-20.md`

## Validation

Static build:

```text
bash scripts/revalidation/build_android_execns_probe_helper.sh tmp/wifi/v389-a90_android_execns_probe-v19/a90_android_execns_probe
```

Result:

```text
ELF 64-bit LSB executable, ARM aarch64, statically linked
There is no dynamic section in this file.
```

Required strings:

```text
a90_android_execns_probe v19
capture.%s.regset.nt_prstatus.x%zu=0x%016llx
capture.%s.regset.nt_prstatus.pc=0x%016llx
capture.%s.%s.ascii.count=%d
reg_x%zu_scan
stack
```

Python compile:

```text
python3 -m py_compile scripts/revalidation/wifi_execns_helper_v19_deploy_preflight.py scripts/revalidation/wifi_service_manager_start_only_v389_live_runner.py scripts/revalidation/wifi_v389_deploy_live_executor.py scripts/revalidation/wifi_service_manager_sigabrt_triage.py
```

Result: PASS.

Plan-only/no-approval evidence:

```text
tmp/wifi/v389-static-20260520-061327/
```

Results:

- deploy plan: `execns-helper-v19-deploy-plan-ready`, device mutation `False`, daemon start `False`, Wi-Fi bring-up `False`.
- live plan: `service-manager-start-only-live-plan-ready`, daemon start `False`, Wi-Fi bring-up `False`.
- executor plan: `v389-deploy-live-executor-plan-ready`, device command `False`, device mutation `False`, daemon start `False`, Wi-Fi bring-up `False`.
- no-approval full executor: `v389-deploy-live-executor-approval-required`, device command `False`, device mutation `False`, daemon start `False`, Wi-Fi bring-up `False`.

Read-only real-device preflight evidence:

```text
tmp/wifi/v389-readonly-preflight-20260520-061337/
```

Results:

- deploy preflight: `execns-helper-v19-deploy-blocked`, blocker `remote-helper-v19`, device mutation `False`, daemon start `False`, Wi-Fi bring-up `False`.
- live preflight: `service-manager-start-only-live-blocked`, blocker `helper-v19`, daemon start `False`, Wi-Fi bring-up `False`.
- status: PASS.

This is expected because the device still has helper v18 until V389 deploy is explicitly approved.

`git diff --check`: PASS.

## Approval Required For Live

Deploy approval phrase:

```text
approve v389 deploy execns helper v19 only; no daemon start and no Wi-Fi bring-up
```

Live approval phrase:

```text
approve v389 service-manager enhanced crash capture only; no Wi-Fi HAL start and no Wi-Fi bring-up
```

## Next Step

Run V389 deployment only after the exact deploy approval phrase. Then run the bounded service-manager enhanced crash capture smoke only after the exact live approval phrase.

Wi-Fi HAL/start/scan/connect remains blocked until the `servicemanager` SIGABRT fatal site is mapped or proven irrelevant to the Wi-Fi path.
