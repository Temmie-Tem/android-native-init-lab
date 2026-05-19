# Native Init v392 Approved Backchain Capture Result

## Summary

The approved V392 helper v21 deploy and service-manager backchain capture run completed successfully inside the approved scope.

V392 deployed `a90_android_execns_probe v21`, ran bounded service-manager start-only crash capture, classified the remaining runtime gap, parsed frame-chain evidence, and routed the result through V394.

This was not Wi-Fi bring-up. Wi-Fi HAL, scan, connect, credentials, DHCP, routing, rfkill writes, driver bind/unbind, firmware mutation, and Android partition writes were not executed.

## Approvals Used

Deploy:

```text
approve v392 deploy execns helper v21 only; no daemon start and no Wi-Fi bring-up
```

Live:

```text
approve v392 service-manager backchain capture only; no Wi-Fi HAL start and no Wi-Fi bring-up
```

## Evidence

- approved executor: `tmp/wifi/v392-approved-full-20260520-072551/`
- post-live route: `tmp/wifi/v394-route-after-v392-approved-20260520-072551/`

Top-level executor result:

```text
decision: v392-deploy-live-executor-full-service-manager-framechain-symbolization-pass
pass: True
device_commands_executed: True
device_mutations: True
daemon_start_executed: True
wifi_bringup_executed: False
```

Post-live router result:

```text
decision: v392-post-live-router-symbolized-caller-ready
pass: True
reason: framechain symbolized non-abort caller candidates: __libc_init
next: plan targeted service-manager runtime repair from symbolized caller evidence; no Wi-Fi HAL yet
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

## Deploy Result

V392 deploy installed helper v21:

```text
c6216cc3b579f78bfd668148a24e1948e9e08621ea7d4e21c8b280475cc09ab8  /cache/bin/a90_android_execns_probe
```

Deploy manifest:

```text
decision: execns-helper-v21-deploy-pass
pass: True
device_mutations: True
daemon_start_executed: False
wifi_bringup_executed: False
```

The deploy path used serial transfer. NCM host ping was not available during deploy, but serial fallback completed successfully.

## Live Result

Live manifest:

```text
decision: service-manager-start-only-live-runtime-gap
pass: True
daemon_start_executed: True
wifi_bringup_executed: False
postflight.clean: True
postflight.manager_processes: []
postflight.wifi_links: []
```

Target observations:

- `system-servicemanager`: `start-only-runtime-gap`, `child-exited-before-observe-window`, `postflight_safe=True`
- `system-hwservicemanager`: `start-only-pass`, `observed-until-timeout-clean-stop`, `postflight_safe=True`

Key service-manager crash evidence:

```text
capture.crash.siginfo.signo=6
capture.crash.siginfo.code=-1
capture.crash.regset.nt_prstatus.x8=0x00000000000000f0
capture.crash.regset.nt_prstatus.pc=0x0000007fb8f1eebc
capture.crash.regset.nt_prstatus.lr=0x0000007fb8f1ee90
capture.crash.regset.nt_prstatus.fp=0x0000007fe4fc9dd0
capture.crash.regset.nt_prstatus.sp=0x0000007fe4fc9d30
```

PC/LR still point into bionic abort delivery:

```text
pc: /tmp/a90-v231-2009/root/apex/com.android.runtime/lib64/bionic/libc.so + 0x8bebc
lr: /tmp/a90-v231-2009/root/apex/com.android.runtime/lib64/bionic/libc.so + 0x8be90
```

## Framechain Result

Framechain analyzer:

```text
decision: service-manager-framechain-symbolization-pass
pass: True
framechain_present: True
maprows_present: True
symbols_present: True
```

Captured frame-chain candidates:

| frame | mapped object | relative offset | symbolization |
| --- | --- | --- | --- |
| 0 | `/system/lib64/liblog.so` | `0x63bc` | ELF missing |
| 1 | `/system/lib64/libbase.so` | `0x16188` | ELF missing |
| 2 | `/system/bin/servicemanager` | `0x8294` | ELF missing |
| 3 | `/system/bin/servicemanager` | `0x13b14` | ELF missing |
| 4 | `bionic/libc.so` | `0x84378` | `__libc_init` |
| 5 | `/system/bin/servicemanager` | `0x8058` | ELF missing |
| 6 | none | none | stop: `next-fp-not-plausible` |

Interpretation:

- V392 proves the crash is not limited to abort PC/LR; caller frames were captured.
- Only the libc frame could be symbolized with existing V391 ELF evidence.
- The actionable frames are likely in `servicemanager`, `libbase`, and `liblog`; those matching Android system ELFs are not yet mirrored locally.
- The next safe step is read-only pull/symbolization of those mapped frame ELFs before any runtime repair or HAL start-only plan.

## Postflight State

- postflight process scan found no `servicemanager`, `hwservicemanager`, `vndservicemanager`, or `a90_android_execns_probe` process.
- postflight netdev scan found no Wi-Fi links.
- native status remains healthy:
  - `A90 Linux init 0.9.61 (v319)`
  - `selftest: pass=11 warn=1 fail=0`
  - `netservice: disabled tcpctl=stopped`
  - `rshell: stopped`

## Next Target

Proceed to V396: read-only frame ELF pull and symbolization for:

- `/mnt/system/system/bin/servicemanager`
- `/mnt/system/system/lib64/libbase.so`
- `/mnt/system/system/lib64/liblog.so`

Then rerun `wifi_service_manager_framechain_analyze.py` with the new system ELF root and decide whether the next runtime repair can target a concrete `servicemanager`/`libbase` caller.
