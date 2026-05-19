# Native Init v385 Approved Live Result

## Summary

v385 helper v16 deployment succeeded, but the approved service-manager residual-PGID live run is still **review-required**. The v16 cleanup fields were proven for `servicemanager`, while `hwservicemanager` output exceeded the current host capture window because ptrace-lite prints a large exec snapshot over the slow serial channel before helper timeout cleanup can complete and be parsed by the runner.

This is not Wi-Fi bring-up. Wi-Fi HAL, scan, connect, credentials, DHCP, routing, rfkill writes, firmware mutation, and driver bind/unbind were not executed.

## Approvals Used

Deploy:

```text
approve v385 deploy execns helper v16 only; no daemon start and no Wi-Fi bring-up
```

Live:

```text
approve v385 service-manager residual pgid cleanup only; no Wi-Fi HAL start and no Wi-Fi bring-up
```

## Evidence

- Initial full executor attempt: `tmp/wifi/v385-approved-full-20260520-045531/`
  - interrupted because NCM/auto install path did not complete within the observed window.
  - device remained responsive afterward.
- Serial deploy rerun: `tmp/wifi/v385-approved-deploy-serial-20260520-050248/`
  - decision: `execns-helper-v16-deploy-pass`
  - method: `serial appendfile + uudecode`
  - chunks: `911`
  - device mutation: helper install only
  - daemon start: `False`
  - Wi-Fi bring-up: `False`
- Approved live run: `tmp/wifi/v385-approved-live-20260520-050940/`
  - decision: `service-manager-start-only-live-review-required`
  - pass: `False`
  - daemon start executed: `True`
  - Wi-Fi bring-up: `False`
- Manual postflight ps capture: `tmp/wifi/v385-approved-live-20260520-050940/native/post-ps-manual.txt`
- Bridge capture excerpt for missing hw END: `tmp/wifi/v385-approved-live-20260520-050940/native/run-system-hwservicemanager-bridge-tail.txt`

## Deploy Result

Remote helper was updated from v15 to v16:

```text
4478c73518e950b425af0cf7db28e9570c983f428fbb0d4b5d2ee45573d37cd8  /cache/bin/a90_android_execns_probe
```

The deploy wrapper reports:

```text
decision: execns-helper-v16-deploy-pass
pass: True
device_mutations: True
daemon_start_executed: False
wifi_bringup_executed: False
```

## Live Result

### `system-servicemanager`

`servicemanager` reached exec and crashed with SIGABRT as in v384, but v16 cleanup evidence completed cleanly:

```text
service_manager_start.capture_exec=1
service_manager_start.capture_crash=1
service_manager_start.signal=6
service_manager_start.reaped=1
service_manager_start.residual_kill_sent=0
service_manager_start.residual_cleared=1
service_manager_start.residual_before_count=-1
service_manager_start.residual_after_count=-1
service_manager_start.postflight_safe=1
service_manager_start.result=start-only-runtime-gap
service_manager_start.reason=child-exited-before-observe-window
```

Interpretation:

- Runtime gap is still present: `servicemanager` aborts quickly after exec.
- Cleanup is proven safe for this target.
- Residual PGID scan was not needed because the process group was already gone.

### `system-hwservicemanager`

The runner capture did not receive `A90P1 END` before host timeout:

```text
A90P1 END marker not found
```

However, the bridge capture later shows the command did eventually end:

```text
[done] run (85317ms)
A90P1 END seq=9283 cmd=run rc=0 errno=0 duration_ms=85317 flags=0x2 status=ok
```

The helper output ended with:

```text
capture.exec_stop=1
capture.exec.pid=1677
capture.exec.exe=/tmp/a90-v231-1675/root/system/bin/hwservicemanager
A90_EXECNS_CAPTURE_exec_mountinfo_END bytes=4376 truncated=0
cleanup_status=attempted
A90_EXECNS_END rc=0
```

But `probe_run_rc`, `A90_EXECNS_STDOUT_BEGIN`, and `service_manager_start.*` summary fields were not captured for this target. Native log shows the run lasted about 85 seconds and PID1 reaped the child with SIGKILL:

```text
cmd: end name=run rc=0 errno=0 duration=85317ms flags=0x2
reaper: reaped pid=1677 reason=cmd-end signal=9
```

Interpretation:

- The v16 residual cleanup fields were not proven for `hwservicemanager`.
- The failure mode is now clearer: ptrace-lite exec snapshot is too verbose for serial capture and delays helper control flow/host parsing.
- A compact capture profile is needed before retrying live proof.

## Postflight Device State

Manual read-only checks after the run:

- `version`: PASS, native remains `A90 Linux init 0.9.61 (v319)`.
- `status`: PASS, `selftest: pass=11 warn=1 fail=0`.
- `ps`: no `servicemanager`, `hwservicemanager`, `vndservicemanager`, or `a90_android_execns_probe` process remains.
- `/proc/net/dev`: no Wi-Fi link; `ncm0` is present from USB control network.

## Root Cause

`a90_android_execns_probe` currently prints detailed ptrace exec snapshots directly to stdout. On `hwservicemanager`, that output includes register, status, maps, and mountinfo sections before timeout cleanup can be summarized. Over USB ACM serial, the output path is slow enough that the host runner times out before seeing `A90P1 END`, and the helper's own timeout cleanup cannot be reliably consumed by host tooling.

This means v385 improved cleanup evidence format, but the live proof is blocked by capture transport/verbosity rather than by an observed leftover service-manager process.

## Next Step

v386 should implement a compact ptrace capture mode for service-manager start-only proof:

- keep `capture.exec_stop=1`, target path, pid/pgid, signal, result, residual cleanup fields, and final postflight summary.
- suppress or sharply cap register dumps, maps, and mountinfo by default for bounded live proof.
- optionally write verbose raw snapshots to a file on SD/cache instead of serial stdout.
- rerun service-manager start-only with the same no-Wi-Fi guardrails after compact output is available.

Wi-Fi HAL/start/scan/connect remains blocked until service-manager lifecycle proof is both complete and machine-parseable.
