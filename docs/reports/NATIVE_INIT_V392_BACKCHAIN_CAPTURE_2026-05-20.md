# Native Init v392 Backchain Capture Readiness

## Summary

V392 adds `a90_android_execns_probe v21` with bounded frame-chain capture for service-manager `ptrace-lite` crash snapshots. The helper now emits x29/frame pointer, walks up to 8 frame records from the crashing process, and records map-row evidence for each candidate return address.

This is local/static verified and read-only preflight checked. It has not been deployed to the device and has not started service-manager daemons under V392.

Wi-Fi HAL, scan, connect, credentials, DHCP, routing, rfkill writes, firmware mutation, and driver bind/unbind were not executed.

## Root Cause From v391

V391 proved the V390 PC/LR evidence points inside bionic `abort`:

```text
PC: abort@@LIBC + 168
LR: abort@@LIBC + 124
```

That is abort delivery, not the original fatal caller. V392 captures bounded caller context so the next live run can identify a return address above `abort`.

## Change

- Helper marker: `a90_android_execns_probe v21`.
- Crash snapshots preserve v20 evidence:
  - selected registers.
  - stack/register-pointer scans.
  - PC/LR map rows.
- Crash snapshots now emit:
  - `capture.crash.regset.nt_prstatus.fp`.
  - bounded `capture.crash.framechain.*`.
  - return address map rows as `capture.crash.maprow.frameN_ra.*`.
- V387 cleanup behavior and V390 map-row behavior remain unchanged.

## Artifacts

Local helper:

```text
tmp/wifi/v392-a90_android_execns_probe-v21/a90_android_execns_probe
```

SHA256:

```text
c6216cc3b579f78bfd668148a24e1948e9e08621ea7d4e21c8b280475cc09ab8
```

Wrappers:

- `scripts/revalidation/wifi_execns_helper_v21_deploy_preflight.py`
- `scripts/revalidation/wifi_service_manager_start_only_v392_live_runner.py`
- `scripts/revalidation/wifi_v392_deploy_live_executor.py`

Plan:

- `docs/plans/NATIVE_INIT_V392_BACKCHAIN_CAPTURE_PLAN_2026-05-20.md`

## Validation

Static build:

```text
bash scripts/revalidation/build_android_execns_probe_helper.sh tmp/wifi/v392-a90_android_execns_probe-v21/a90_android_execns_probe
```

Result:

```text
ELF 64-bit LSB executable, ARM aarch64, statically linked
There is no dynamic section in this file.
```

Required strings:

```text
a90_android_execns_probe v21
capture.%s.regset.nt_prstatus.fp=0x%016llx
capture.%s.framechain.fp=0x%016llx
capture.%s.framechain.%d.return_addr_raw=0x%016llx
capture.%s.framechain.%d.return_addr=0x%016llx
frame%d_ra
```

Python compile:

```text
python3 -m py_compile scripts/revalidation/wifi_execns_helper_v21_deploy_preflight.py scripts/revalidation/wifi_service_manager_start_only_v392_live_runner.py scripts/revalidation/wifi_v392_deploy_live_executor.py scripts/revalidation/wifi_service_manager_runtime_gap_classifier.py scripts/revalidation/wifi_service_manager_sigabrt_triage.py
```

Result: PASS.

Plan-only/no-approval evidence:

```text
tmp/wifi/v392-static-20260520-065750/
```

Results:

- deploy plan: `execns-helper-v21-deploy-plan-ready`, device mutation `False`, daemon start `False`, Wi-Fi bring-up `False`.
- live plan: `service-manager-start-only-live-plan-ready`, daemon start `False`, Wi-Fi bring-up `False`.
- executor plan: `v392-deploy-live-executor-plan-ready`, device command `False`, device mutation `False`, daemon start `False`, Wi-Fi bring-up `False`.
- no-approval full executor: `v392-deploy-live-executor-approval-required`, device command `False`, device mutation `False`, daemon start `False`, Wi-Fi bring-up `False`.

Read-only real-device preflight evidence:

```text
tmp/wifi/v392-readonly-preflight-20260520-065801/
```

Results:

- deploy preflight: `execns-helper-v21-deploy-blocked`, blocker `remote-helper-v21`, device mutation `False`, daemon start `False`, Wi-Fi bring-up `False`.
- live preflight: `service-manager-start-only-live-blocked`, blocker `helper-v21`, daemon start `False`, Wi-Fi bring-up `False`.
- status: PASS, `A90 Linux init 0.9.61 (v319)`, `selftest: pass=11 warn=1 fail=0`.

This is expected because the device still has helper v20 until V392 deploy is explicitly approved.

`git diff --check`: PASS.

## Approval Required For Live

Deploy approval phrase:

```text
approve v392 deploy execns helper v21 only; no daemon start and no Wi-Fi bring-up
```

Live approval phrase:

```text
approve v392 service-manager backchain capture only; no Wi-Fi HAL start and no Wi-Fi bring-up
```

## Next Step

Run V392 deployment only after the exact deploy approval phrase. Then run the bounded service-manager backchain capture smoke only after the exact live approval phrase.

Wi-Fi HAL/start/scan/connect remains blocked until the `servicemanager` abort caller is mapped well enough to justify a targeted runtime repair.
