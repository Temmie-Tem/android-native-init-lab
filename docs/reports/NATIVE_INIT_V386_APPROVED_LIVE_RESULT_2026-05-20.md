# Native Init v386 Approved Live Result

## Summary

v386 helper v17 deployment succeeded and compact ptrace output fixed the v385 host-capture problem: both `servicemanager` and `hwservicemanager` returned `A90P1 END`, and `hwservicemanager` produced machine-readable `service_manager_start.*` fields without manual bridge-tail recovery.

The approved live run is still **review-required** because `hwservicemanager` exposed the next cleanup bug: a ptrace-stopped child can be treated as reaped during timeout cleanup, leaving a temporary zombie in the helper's process group until PID1 reaps it later.

This is not Wi-Fi bring-up. Wi-Fi HAL, scan, connect, credentials, DHCP, routing, rfkill writes, firmware mutation, and driver bind/unbind were not executed.

## Approvals Used

Deploy:

```text
approve v386 deploy execns helper v17 only; no daemon start and no Wi-Fi bring-up
```

Live:

```text
approve v386 service-manager compact ptrace capture only; no Wi-Fi HAL start and no Wi-Fi bring-up
```

## Evidence

- Serial deploy: `tmp/wifi/v386-approved-deploy-serial-20260520-053704/`
  - decision: `execns-helper-v17-deploy-pass`
  - method: `serial appendfile + uudecode`
  - device mutation: helper install only
  - daemon start: `False`
  - Wi-Fi bring-up: `False`
- Approved live run: `tmp/wifi/v386-approved-live-20260520-054304/`
  - decision: `service-manager-start-only-live-review-required`
  - pass: `False`
  - daemon start executed: `True`
  - Wi-Fi bring-up: `False`
- Manual postflight ps capture: `tmp/wifi/v386-approved-live-20260520-054304/native/post-ps-manual-after-review.txt`

## Deploy Result

Remote helper was updated to v17:

```text
45c27e28c90a86c75a291edaf16d8233da51358647c1e6d1700f0e4f9cf437c5  /cache/bin/a90_android_execns_probe
```

The deploy wrapper reports:

```text
decision: execns-helper-v17-deploy-pass
pass: True
device_mutations: True
daemon_start_executed: False
wifi_bringup_executed: False
```

## Live Result

### `system-servicemanager`

`servicemanager` behavior is unchanged from v385: it reaches exec, crashes with SIGABRT, and cleanup is proven safe.

Key fields:

```text
service_manager_start.capture_detail=compact
service_manager_start.capture_exec=1
service_manager_start.capture_crash=1
service_manager_start.signal=6
service_manager_start.reaped=1
service_manager_start.residual_kill_sent=0
service_manager_start.residual_cleared=1
service_manager_start.postflight_safe=1
service_manager_start.result=start-only-runtime-gap
service_manager_start.reason=child-exited-before-observe-window
```

Interpretation:

- Runtime gap remains for `servicemanager`.
- Compact capture is machine-parseable.
- Cleanup is safe for this target.

### `system-hwservicemanager`

`hwservicemanager` now returns within host timeout and includes machine-readable summary fields. This confirms v386 fixed the serial output/capture problem.

Key compact fields:

```text
capture.exec_stop=1
service_manager_start.capture_detail=compact
capture.exec.pid=1739
capture.exec.exe=/tmp/a90-v231-1737/root/system/bin/hwservicemanager
capture.exec.auxv.count=19
capture.exec.regset.nt_prstatus.bytes=272
capture.exec.status.bytes=977
capture.exec.maps.bytes=1326
capture.exec.mountinfo.bytes=4376
probe_run_rc=0
A90_EXECNS_END rc=0
A90P1 END ... status=ok
```

Cleanup fields:

```text
service_manager_start.timed_out=1
service_manager_start.term_sent=1
service_manager_start.kill_sent=1
service_manager_start.reaped=1
service_manager_start.residual_kill_sent=1
service_manager_start.residual_cleared=0
service_manager_start.residual_before_count=1
service_manager_start.residual_after_count=1
service_manager_start.postflight_safe=0
service_manager_start.result=start-only-reboot-required
service_manager_start.reason=process-not-proven-stopped
```

PGID scan detail:

```text
service_manager_start.pgid_scan.before_final_kill.entry.0=pid:1739 state:t comm:hwservicemanage
service_manager_start.pgid_scan.after_final_kill.entry.0=pid:1739 state:Z comm:hwservicemanage
```

Interpretation:

- The previous serial timeout problem is fixed.
- The remaining blocker is cleanup semantics, not output size.
- The helper marks the process as `reaped=1` while the PGID scan still sees the same PID as a zombie. This points to the timeout cleanup loop treating a ptrace stop as a completed reap instead of resuming/delivering the termination signal and waiting for `WIFEXITED`/`WIFSIGNALED`.

## Postflight Device State

Manual read-only checks after the run:

- `status`: PASS, `selftest: pass=11 warn=1 fail=0`.
- `ps`: no `servicemanager`, `hwservicemanager`, `vndservicemanager`, or `a90_android_execns_probe` process remains after PID1 reaper runs.
- `/proc/net/dev`: no Wi-Fi link; `ncm0` remains the USB control network.

The live wrapper postflight also reports:

```text
postflight.clean=True
manager_processes=0
wifi_links=0
```

## Root Cause

v386 narrowed the failure from capture transport to ptrace cleanup. In the timeout cleanup path, `waitpid(..., WNOHANG)` can return a ptrace stop state. The current helper can set `child_done=true` and `reaped=true` for that event even when the child is not actually exited or signaled. Final PGID scan then sees the process as `t` before final kill and `Z` after final kill, so `kill(-pgid, 0)` remains true and `postflight_safe=0`.

This is a helper lifecycle bug. The device recovered without reboot because PID1 later reaped the child, but the helper cannot claim bounded service-manager cleanup until it handles ptrace-stopped children correctly.

## Next Step

v387 should fix ptrace timeout cleanup:

- only set `reaped=1` when `WIFEXITED(status)` or `WIFSIGNALED(status)` is true.
- when timeout cleanup sees `WIFSTOPPED(status)`, continue the tracee with the intended termination signal instead of treating it as done.
- after SIGTERM/SIGKILL, keep waiting until real exit/signal or a bounded hard timeout.
- preserve compact service-manager output and residual PGID scan evidence.

Wi-Fi HAL/start/scan/connect remains blocked until service-manager lifecycle proof is clean and machine-parseable.
