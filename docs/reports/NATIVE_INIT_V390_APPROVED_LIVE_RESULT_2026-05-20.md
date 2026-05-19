# Native Init v390 Approved Live Result

## Summary

V390 helper v20 deployment succeeded, and the approved service-manager crash map capture smoke produced the missing PC/LR map rows for the remaining `servicemanager` SIGABRT runtime gap.

`system-hwservicemanager` remains clean: it reaches exec, stays observable until timeout, receives ptrace cleanup, and exits as `start-only-pass`.

`system-servicemanager` still exits before the observe window with SIGABRT. V390 confirms cleanup is safe and maps both PC and LR into bionic `libc.so` with file-relative offsets. The next blocker is pulling or otherwise providing the matching Android `libc.so` ELF to symbolize those offsets.

This is not Wi-Fi bring-up. Wi-Fi HAL, scan, connect, credentials, DHCP, routing, rfkill writes, firmware mutation, and driver bind/unbind were not executed.

## Approvals Used

Deploy:

```text
approve v390 deploy execns helper v20 only; no daemon start and no Wi-Fi bring-up
```

Live:

```text
approve v390 service-manager crash map capture only; no Wi-Fi HAL start and no Wi-Fi bring-up
```

## Evidence

- Approved executor: `tmp/wifi/v390-approved-full-20260520-063910/`
  - decision: `v390-deploy-live-executor-full-service-manager-runtime-gap-servicemanager-sigabrt-captured`
  - pass: `True`
  - device commands executed: `True`
  - device mutation: helper install only
  - daemon start executed: service-manager start-only only
  - Wi-Fi bring-up: `False`
- Deploy evidence: `tmp/wifi/v390-approved-full-20260520-063910/deploy/`
  - decision: `execns-helper-v20-deploy-pass`
  - method: `serial appendfile + uudecode`
  - chunks: `783`
  - encoded bytes: `1094836`
- Live evidence: `tmp/wifi/v390-approved-full-20260520-063910/live/`
  - decision: `service-manager-start-only-live-runtime-gap`
  - pass: `True`
  - daemon start executed: `True`
  - Wi-Fi bring-up: `False`
- Runtime-gap classifier: `tmp/wifi/v390-approved-full-20260520-063910/classify/`
  - decision: `service-manager-runtime-gap-servicemanager-sigabrt-captured`
  - pass: `True`
- Symbolizer: `tmp/wifi/v390-approved-full-20260520-063910/symbolize/`
  - decision: `service-manager-crash-symbolization-maprow-ready`
  - pass: `True`
  - maprows present: `True`
  - symbols present: `False`
- SIGABRT triage: `tmp/wifi/v390-approved-full-20260520-063910/sigabrt-triage/`
  - decision: `servicemanager-sigabrt-triage-partial-evidence`
  - pass: `True`
  - remaining blocker: `abort-message`
- Postflight captures:
  - `tmp/wifi/v390-approved-full-20260520-063910/post-status.json`
  - `tmp/wifi/v390-approved-full-20260520-063910/post-ps.json`
  - `tmp/wifi/v390-approved-full-20260520-063910/post-proc-net-dev.json`

## Deploy Result

Remote helper was updated to v20:

```text
44efea328220d37f09d91e4906b7490903d789ef509f0ae2ba74a64049a47171  /cache/bin/a90_android_execns_probe
```

The deploy wrapper reports:

```text
decision: execns-helper-v20-deploy-pass
pass: True
device_mutations: True
daemon_start_executed: False
wifi_bringup_executed: False
```

NCM was not configured on the host during this run, so the deploy wrapper used the serial fallback. That is slow but within scope and did not start any daemon.

## Live Result

### `system-servicemanager`

`servicemanager` still exits before the observe window. V390 captures PC/LR map rows and proves cleanup safe.

Key service result fields:

```text
service_manager_start.capture_exec=1
service_manager_start.capture_crash=1
service_manager_start.signal=6
service_manager_start.timed_out=0
service_manager_start.observable=0
service_manager_start.term_sent=0
service_manager_start.kill_sent=0
service_manager_start.reaped=1
service_manager_start.residual_cleared=1
service_manager_start.postflight_safe=1
service_manager_start.result=start-only-runtime-gap
service_manager_start.reason=child-exited-before-observe-window
```

Captured SIGABRT:

```text
capture.crash.siginfo.signo=6
capture.crash.siginfo.code=-1
capture.crash.siginfo.addr=0x3e800000778
libc: Fatal signal 6 (SIGABRT), code -1 (SI_QUEUE) in tid 1912 (servicemanager), pid 1912 (servicemanager)
```

Selected register evidence:

```text
capture.crash.regset.nt_prstatus.x1=0x0000000000000778
capture.crash.regset.nt_prstatus.x2=0x0000000000000006
capture.crash.regset.nt_prstatus.x8=0x00000000000000f0
capture.crash.regset.nt_prstatus.lr=0x0000007fab12ee90
capture.crash.regset.nt_prstatus.sp=0x0000007fdf70c020
capture.crash.regset.nt_prstatus.pc=0x0000007fab12eebc
```

New V390 map-row evidence:

```text
capture.crash.maprow.pc.found=1
capture.crash.maprow.pc.perms=r-xp
capture.crash.maprow.pc.file_offset=0x48000
capture.crash.maprow.pc.relative_offset=0x8bebc
capture.crash.maprow.pc.path=/tmp/a90-v231-1910/root/apex/com.android.runtime/lib64/bionic/libc.so
capture.crash.maprow.lr.found=1
capture.crash.maprow.lr.perms=r-xp
capture.crash.maprow.lr.file_offset=0x48000
capture.crash.maprow.lr.relative_offset=0x8be90
capture.crash.maprow.lr.path=/tmp/a90-v231-1910/root/apex/com.android.runtime/lib64/bionic/libc.so
```

Interpretation:

- V390 resolves the v389 map-row attribution gap.
- PC and LR both map into bionic `libc.so`.
- `x8=0xf0` still indicates AArch64 `rt_tgsigqueueinfo`, so the stop point is abort delivery.
- Host symbolization did not complete because the matching Android ELF is not yet available on the host.

### `system-hwservicemanager`

`hwservicemanager` continues to pass after the v387 cleanup fix and v390 map-row changes.

Key fields:

```text
service_manager_start.capture_exec=1
service_manager_start.capture_crash=0
service_manager_start.signal=15
service_manager_start.timed_out=1
service_manager_start.observable=1
service_manager_start.term_sent=1
service_manager_start.kill_sent=0
service_manager_start.reaped=1
service_manager_start.cleanup_stop_continued=1
service_manager_start.residual_cleared=1
service_manager_start.postflight_safe=1
service_manager_start.result=start-only-pass
service_manager_start.reason=observed-until-timeout-clean-stop
```

Interpretation:

- V390 did not regress ptrace timeout cleanup.
- The remaining runtime gap remains isolated to `servicemanager` SIGABRT.

## Classifier, Symbolizer, And Triage

Runtime-gap classifier:

```text
decision: service-manager-runtime-gap-servicemanager-sigabrt-captured
pass: True
remaining_blockers: servicemanager-sigabrt-evidence
```

Symbolizer:

```text
decision: service-manager-crash-symbolization-maprow-ready
pass: True
maprows_present: True
symbols_present: False
remaining_blockers: elf-artifact
pc: /apex/com.android.runtime/lib64/bionic/libc.so + 0x8bebc
lr: /apex/com.android.runtime/lib64/bionic/libc.so + 0x8be90
```

SIGABRT triage:

```text
decision: servicemanager-sigabrt-triage-partial-evidence
pass: True
remaining_blockers: abort-message
```

Read-only device check found the matching library path on the device:

```text
/mnt/system/system/apex/com.android.runtime/lib64/bionic/libc.so
```

## Postflight Device State

Read-only checks after the run:

- `status`: PASS, `selftest: pass=11 warn=1 fail=0`.
- `ps`: no `servicemanager`, `hwservicemanager`, `vndservicemanager`, or `a90_android_execns_probe` process remains.
- `/proc/net/dev`: no Wi-Fi link.
- `netservice`: disabled, `tcpctl=stopped`, `rshell=stopped`.
- native build remains `A90 Linux init 0.9.61 (v319)`.

## Conclusion

V390 is successful as the crash map-row capture step. The service-manager runtime gap is now narrowed to bionic abort delivery offsets:

- PC: `libc.so + 0x8bebc`
- LR: `libc.so + 0x8be90`

The next blocker is host-side access to the exact Android `libc.so` ELF so those offsets can be symbolized. Wi-Fi HAL/start/scan/connect remains blocked until the `servicemanager` abort path is symbolized or otherwise mapped well enough to justify a targeted runtime repair.

## Next Step

V391 should pull or mirror the read-only Android `libc.so` from:

```text
/mnt/system/system/apex/com.android.runtime/lib64/bionic/libc.so
```

Then run `wifi_service_manager_crash_symbolize.py` with an `--elf-root` that resolves the V390 map-row path and record the symbolized PC/LR result. If the production binary is stripped too heavily for `addr2line`, V391 should at least record `readelf` metadata and disassembly around `0x8be90` / `0x8bebc`.

No Wi-Fi HAL/start/scan/connect should run in V391.
