# Native Init v390 Crash Map Capture Readiness

## Summary

V390 adds `a90_android_execns_probe v20` with bounded crash map-row capture for service-manager `ptrace-lite` crash snapshots. The helper now records the `/proc/<pid>/maps` row containing crash PC and LR, plus file-relative offsets for both addresses.

V390 also adds a host-only parser/symbolizer that can consume the new map-row fields after an approved live run and attempt `addr2line` when matching Android ELF files are available.

This is local/static verified and read-only preflight checked. It has not been deployed to the device and has not started service-manager daemons under V390.

Wi-Fi HAL, scan, connect, credentials, DHCP, routing, rfkill writes, firmware mutation, and driver bind/unbind were not executed.

## Root Cause From v389

V389 captured selected `servicemanager` SIGABRT registers and bounded memory scans, but the PC/LR values could not be attributed to a library or symbol because the compact crash evidence recorded only maps byte/line counts.

The important V389 clue was:

```text
capture.crash.regset.nt_prstatus.x8=0x00000000000000f0
capture.crash.regset.nt_prstatus.lr=0x0000007f914e5e90
capture.crash.regset.nt_prstatus.pc=0x0000007f914e5ebc
```

`x8=0xf0` maps to AArch64 `rt_tgsigqueueinfo`, which points at abort delivery rather than the original fatal check. V390 captures map rows and offsets so that the next cycle can symbolize the abort path or choose a narrower fatal-site capture.

## Change

- Helper marker: `a90_android_execns_probe v20`.
- Crash snapshots preserve v19 evidence:
  - x0-x8
  - lr/x30
  - sp
  - pc
  - pstate
  - bounded stack/register-pointer ASCII scans
- Crash snapshots now emit PC/LR map-row evidence:
  - `capture.crash.maprow.pc.*`
  - `capture.crash.maprow.lr.*`
  - address, found flag, start/end, permissions, file offset, relative offset, path, and escaped maps line
- Host-only symbolization tool added:
  - `scripts/revalidation/wifi_service_manager_crash_symbolize.py`
- V387 cleanup behavior and V389 bounded memory behavior remain unchanged.

## Artifacts

Local helper:

```text
tmp/wifi/v390-a90_android_execns_probe-v20/a90_android_execns_probe
```

SHA256:

```text
44efea328220d37f09d91e4906b7490903d789ef509f0ae2ba74a64049a47171
```

Wrappers:

- `scripts/revalidation/wifi_execns_helper_v20_deploy_preflight.py`
- `scripts/revalidation/wifi_service_manager_start_only_v390_live_runner.py`
- `scripts/revalidation/wifi_v390_deploy_live_executor.py`
- `scripts/revalidation/wifi_service_manager_crash_symbolize.py`

Plan:

- `docs/plans/NATIVE_INIT_V390_CRASH_MAP_CAPTURE_PLAN_2026-05-20.md`

## Validation

Static build:

```text
bash scripts/revalidation/build_android_execns_probe_helper.sh tmp/wifi/v390-a90_android_execns_probe-v20/a90_android_execns_probe
```

Result:

```text
ELF 64-bit LSB executable, ARM aarch64, statically linked
There is no dynamic section in this file.
```

Required strings:

```text
a90_android_execns_probe v20
capture.%s.maprow.%s.found=1
capture.%s.maprow.%s.relative_offset=0x%llx
capture.%s.maprow.%s.line=
capture.%s.regset.nt_prstatus.pc=0x%016llx
reg_x%zu_scan
stack
```

Python compile:

```text
python3 -m py_compile scripts/revalidation/wifi_execns_helper_v20_deploy_preflight.py scripts/revalidation/wifi_service_manager_start_only_v390_live_runner.py scripts/revalidation/wifi_v390_deploy_live_executor.py scripts/revalidation/wifi_service_manager_crash_symbolize.py scripts/revalidation/wifi_service_manager_runtime_gap_classifier.py scripts/revalidation/wifi_service_manager_sigabrt_triage.py
```

Result: PASS.

Plan-only/no-approval evidence:

```text
tmp/wifi/v390-static-20260520-063230/
```

Results:

- deploy plan: `execns-helper-v20-deploy-plan-ready`, device mutation `False`, daemon start `False`, Wi-Fi bring-up `False`.
- live plan: `service-manager-start-only-live-plan-ready`, daemon start `False`, Wi-Fi bring-up `False`.
- executor plan: `v390-deploy-live-executor-plan-ready`, device command `False`, device mutation `False`, daemon start `False`, Wi-Fi bring-up `False`.
- no-approval full executor: `v390-deploy-live-executor-approval-required`, device command `False`, device mutation `False`, daemon start `False`, Wi-Fi bring-up `False`.
- host-only symbolizer against V389 evidence: `service-manager-crash-symbolization-needs-maprow`, device command `False`, device mutation `False`, daemon start `False`, Wi-Fi bring-up `False`.

Read-only real-device preflight evidence:

```text
tmp/wifi/v390-readonly-preflight-20260520-063240/
```

Results:

- deploy preflight: `execns-helper-v20-deploy-blocked`, blocker `remote-helper-v20`, device mutation `False`, daemon start `False`, Wi-Fi bring-up `False`.
- live preflight: `service-manager-start-only-live-blocked`, blocker `helper-v20`, daemon start `False`, Wi-Fi bring-up `False`.
- status: PASS, `A90 Linux init 0.9.61 (v319)`, `selftest: pass=11 warn=1 fail=0`.

This is expected because the device still has helper v19 until V390 deploy is explicitly approved.

## Approval Required For Live

Deploy approval phrase:

```text
approve v390 deploy execns helper v20 only; no daemon start and no Wi-Fi bring-up
```

Live approval phrase:

```text
approve v390 service-manager crash map capture only; no Wi-Fi HAL start and no Wi-Fi bring-up
```

## Next Step

Run V390 deployment only after the exact deploy approval phrase. Then run the bounded service-manager crash map capture smoke only after the exact live approval phrase.

After live capture, run the host-only symbolizer against `native/run-system-servicemanager.txt`. Wi-Fi HAL/start/scan/connect remains blocked until the `servicemanager` SIGABRT fatal path is mapped well enough to justify a targeted repair.
