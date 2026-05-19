# Native Init v389 Approved Live Result

## Summary

V389 helper v19 deployment succeeded, and the approved service-manager enhanced crash-capture smoke produced the first useful bounded register/stack evidence for the remaining `servicemanager` SIGABRT runtime gap.

`system-hwservicemanager` remains clean: it reaches exec, stays observable until timeout, is continued through ptrace cleanup, and exits as `start-only-pass`.

`system-servicemanager` still exits before the observe window with SIGABRT. V389 confirms cleanup is safe and captures selected AArch64 registers, stack summary, register-pointer memory scans, and compact maps metadata. The next blocker is symbolizing the abort-delivery PC/LR and capturing the map rows that contain those addresses.

This is not Wi-Fi bring-up. Wi-Fi HAL, scan, connect, credentials, DHCP, routing, rfkill writes, firmware mutation, and driver bind/unbind were not executed.

## Approvals Used

Deploy:

```text
approve v389 deploy execns helper v19 only; no daemon start and no Wi-Fi bring-up
```

Live:

```text
approve v389 service-manager enhanced crash capture only; no Wi-Fi HAL start and no Wi-Fi bring-up
```

## Evidence

- Serial deploy: `tmp/wifi/v389-approved-deploy-serial-20260520-061712/`
  - decision: `execns-helper-v19-deploy-pass`
  - method: `serial appendfile + uudecode`
  - device mutation: helper install only
  - daemon start: `False`
  - Wi-Fi bring-up: `False`
- Approved live run: `tmp/wifi/v389-approved-live-20260520-062315/`
  - decision: `service-manager-start-only-live-runtime-gap`
  - pass: `True`
  - daemon start executed: `True`
  - Wi-Fi bring-up: `False`
- Runtime-gap classifier: `tmp/wifi/v389-approved-live-20260520-062315/classify/`
  - decision: `service-manager-runtime-gap-servicemanager-sigabrt-captured`
  - pass: `True`
- SIGABRT triage: `tmp/wifi/v389-approved-live-20260520-062315/sigabrt-triage/`
  - decision: `servicemanager-sigabrt-triage-partial-evidence`
  - pass: `True`
  - remaining blocker: `abort-message`
- Postflight captures:
  - `tmp/wifi/v389-approved-live-20260520-062315/post-status.json`
  - `tmp/wifi/v389-approved-live-20260520-062315/post-ps.txt`
  - `tmp/wifi/v389-approved-live-20260520-062315/post-proc-net-dev.txt`

## Deploy Result

Remote helper was updated to v19:

```text
e3da79dec1c7ca58d3208fb0d9a55ce1411fff7159ab613ff9daf6d6befd3e6d  /cache/bin/a90_android_execns_probe
```

The deploy wrapper reports:

```text
decision: execns-helper-v19-deploy-pass
pass: True
device_mutations: True
daemon_start_executed: False
wifi_bringup_executed: False
```

## Live Result

### `system-servicemanager`

`servicemanager` still exits before the observe window. V389 captures a stronger crash snapshot and proves cleanup safe.

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
service_manager_start.cleanup_stop_continued=0
service_manager_start.residual_cleared=1
service_manager_start.postflight_safe=1
service_manager_start.result=start-only-runtime-gap
service_manager_start.reason=child-exited-before-observe-window
```

Captured SIGABRT:

```text
capture.crash.siginfo.signo=6
capture.crash.siginfo.code=-1
capture.crash.siginfo.addr=0x3e800000739
libc: Fatal signal 6 (SIGABRT), code -1 (SI_QUEUE) in tid 1849 (servicemanager), pid 1849 (servicemanager)
```

Selected register evidence:

```text
capture.crash.regset.nt_prstatus.bytes=272
capture.crash.regset.nt_prstatus.words=34
capture.crash.regset.nt_prstatus.x0=0x0000000000000000
capture.crash.regset.nt_prstatus.x1=0x0000000000000739
capture.crash.regset.nt_prstatus.x2=0x0000000000000006
capture.crash.regset.nt_prstatus.x3=0x0000007fe4553760
capture.crash.regset.nt_prstatus.x4=0x0000007f940d6000
capture.crash.regset.nt_prstatus.x5=0x0000007f940d6000
capture.crash.regset.nt_prstatus.x6=0x0000007f940d6000
capture.crash.regset.nt_prstatus.x7=0x000000000056d2be
capture.crash.regset.nt_prstatus.x8=0x00000000000000f0
capture.crash.regset.nt_prstatus.lr=0x0000007f914e5e90
capture.crash.regset.nt_prstatus.sp=0x0000007fe4553740
capture.crash.regset.nt_prstatus.pc=0x0000007f914e5ebc
capture.crash.regset.nt_prstatus.pstate=0x0000000000001000
```

Bounded memory evidence:

```text
capture.crash.reg_x3_scan.bytes=128
capture.crash.reg_x4_scan.bytes=128
capture.crash.reg_x5_scan.bytes=128
capture.crash.reg_x6_scan.bytes=128
capture.crash.stack.bytes=512
capture.crash.stack.ascii.count=0
capture.crash.maps.bytes=8192
capture.crash.maps.lines=70
capture.crash.maps.truncated=1
```

Interpretation:

- V389 resolves the v388 evidence gap for selected register values and bounded stack/register-pointer memory scanning.
- `x8=0x00000000000000f0` maps to AArch64 syscall `__NR_rt_tgsigqueueinfo` (`240`), so the stopped PC/LR are in SIGABRT delivery or abort plumbing, not yet the original fatal check.
- The helper only records compact maps metadata, not the map rows containing `pc` and `lr`. That prevents reliable library/offset attribution for `0x7f914e5ebc` and `0x7f914e5e90`.
- No abort message string was recovered from stack or register-pointer scans.

### `system-hwservicemanager`

`hwservicemanager` continues to pass after the v387 cleanup fix.

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

- V389 did not regress the ptrace timeout cleanup behavior fixed in v387.
- The remaining runtime gap is isolated to `servicemanager` SIGABRT, not general service-manager namespace execution or cleanup.

## Classifier And Triage Result

Runtime-gap classifier:

```text
decision: service-manager-runtime-gap-servicemanager-sigabrt-captured
pass: True
reason: servicemanager SIGABRT was captured by ptrace-lite crash evidence
```

SIGABRT triage:

```text
decision: servicemanager-sigabrt-triage-partial-evidence
pass: True
reason: SIGABRT triage has partial fatal-site evidence
remaining_blockers: abort-message
```

The triage now sees:

- register values: present.
- stack or abort-memory evidence: present.
- Binder device node materialization: present.
- abort message: still missing.

## Postflight Device State

Read-only checks after the run:

- `status`: PASS, `selftest: pass=11 warn=1 fail=0`.
- `ps`: no `servicemanager`, `hwservicemanager`, `vndservicemanager`, or `a90_android_execns_probe` process remains.
- `/proc/net/dev`: no Wi-Fi link.
- `netservice`: disabled, `tcpctl=stopped`, `rshell=stopped`.
- native build remains `A90 Linux init 0.9.61 (v319)`.

The live wrapper postflight reports:

```text
postflight.clean=True
manager_processes=0
wifi_links=0
```

## Conclusion

V389 is successful as an evidence-capture step. It confirms that the service-manager execution namespace is good enough for `hwservicemanager`, and that `servicemanager` reaches abort delivery with clean postflight recovery.

The remaining blocker is not process cleanup. It is the `servicemanager` fatal-site attribution. V389 can show the abort-delivery registers, but not the library map rows or symbol offsets needed to choose the next runtime repair.

## Next Step

V390 should add crash map-row and symbolization capture:

- capture the `/proc/<pid>/maps` row containing `pc`.
- capture the `/proc/<pid>/maps` row containing `lr`.
- compute library-relative offsets for `pc` and `lr`.
- preserve bounded output; do not reintroduce v385 serial-output flooding.
- optionally add host-side symbolization if the referenced Android ELF is available from the mounted vendor/system image or prior extracted artifacts.

Wi-Fi HAL/start/scan/connect remains blocked until `servicemanager` no longer exits early or the abort site is mapped well enough to justify a targeted repair.
