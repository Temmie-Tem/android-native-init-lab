# Native Init v392 Backchain Capture Plan

## Purpose

V391 proved the V390 `servicemanager` crash PC/LR are inside bionic `abort`, not at the original fatal call site. V392 adds bounded caller-context capture while the process is ptrace-stopped so the next live run can identify who called `abort`.

The goal is caller attribution. It is not runtime repair and it is not Wi-Fi bring-up.

## Starting Evidence

- V390 approved live: `docs/reports/NATIVE_INIT_V390_APPROVED_LIVE_RESULT_2026-05-20.md`
- V391 libc symbolization: `docs/reports/NATIVE_INIT_V391_LIBC_SYMBOLIZATION_2026-05-20.md`
- V391 result:
  - PC: `libc.so + 0x8bebc` -> `abort@@LIBC + 168`
  - LR: `libc.so + 0x8be90` -> `abort@@LIBC + 124`
  - `x8=0xf0` and `svc #0` confirm the SIGABRT delivery path.

## Scope

Implement helper v21 and V392 wrappers:

- bump `a90_android_execns_probe` to `v21`.
- preserve V390 PC/LR map-row capture.
- preserve V389 bounded stack/register-pointer ASCII scan.
- emit `x29`/frame pointer as `capture.crash.regset.nt_prstatus.fp`.
- add bounded frame-chain capture:
  - starting FP and SP.
  - up to 8 frames.
  - each frame's FP, next FP, raw return address, canonical return address.
  - map-row evidence for each candidate return address as `frameN_ra`.
- stop safely on invalid pointer, non-increasing FP, out-of-bounds FP, or read error.
- preserve V387 cleanup behavior.

## Non-Goals

V392 must not perform:

- Wi-Fi HAL start.
- Wi-Fi scan/connect/link-up.
- `servicemanager`, `hwservicemanager`, CNSS, wificond, supplicant, or hostapd start outside the bounded service-manager start-only smoke.
- credentials, DHCP, routing, rfkill writes.
- driver bind/unbind or firmware mutation.
- Android partition writes.
- runtime repair before caller attribution.

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

## Expected New Fields

```text
capture.crash.regset.nt_prstatus.fp=...
capture.crash.framechain.fp=...
capture.crash.framechain.sp=...
capture.crash.framechain.max=8
capture.crash.framechain.0.fp=...
capture.crash.framechain.0.next_fp=...
capture.crash.framechain.0.return_addr_raw=...
capture.crash.framechain.0.return_addr=...
capture.crash.maprow.frame0_ra.found=...
capture.crash.maprow.frame0_ra.relative_offset=...
capture.crash.framechain.count=...
```

## Validation Plan

Local/static validation:

1. Build static ARM64 helper.
2. Confirm required marker and frame-chain capture strings.
3. Compile V392 wrappers and existing classifier/triage tools.
4. Run deploy/live/executor plan-only gates.
5. Run no-approval full executor and confirm no device command/mutation/daemon/Wi-Fi action.

Read-only real-device validation before approval:

1. Run deploy preflight and expect `remote-helper-v21` blocker while device still has v20.
2. Run live preflight and expect `helper-v21` blocker.
3. Confirm no daemon start and no Wi-Fi bring-up.
4. Confirm read-only `status` is healthy.

## Approval Phrases

Deploy:

```text
approve v392 deploy execns helper v21 only; no daemon start and no Wi-Fi bring-up
```

Live:

```text
approve v392 service-manager backchain capture only; no Wi-Fi HAL start and no Wi-Fi bring-up
```

## Next Step After Approval

After approved V392 deploy/live, parse `capture.crash.framechain.*` and `capture.crash.maprow.frameN_ra.*`. If a candidate return address maps outside bionic `abort`, symbolize that ELF in the next cycle and decide whether the abort cause is a missing runtime dependency, Binder/property/SELinux contract gap, or another service-manager environment issue.
