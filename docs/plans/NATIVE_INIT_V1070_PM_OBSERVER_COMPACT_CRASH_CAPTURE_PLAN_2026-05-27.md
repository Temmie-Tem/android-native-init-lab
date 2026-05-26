# Native Init V1070 PM Observer Compact Crash Capture Plan

## Goal

Capture the `servicemanager` and `vndservicemanager` `SIGABRT` boundary inside
`wifi-companion-pm-service-trigger-observer` without overflowing the NCM/tcpctl
transcript.

## Background

V1068 fixed private property materialization for PM observer, but the PM stack
still exited before the observation window:

- `servicemanager` signal `6`
- `vndservicemanager` signal `6`
- `hwservicemanager` stayed observable until cleanup
- `pm_proxy_helper` stayed observable but never opened `/dev/subsys_modem`

A first ptrace attempt produced useful crash lines but truncated before the
final helper summary. V1070 keeps the trace scope narrow and compacts observable
child output.

## Gate

- Build static `a90_android_execns_probe v188`.
- Deploy only `/cache/bin/a90_android_execns_probe` over NCM.
- Run PM observer with `--capture-mode ptrace-lite`.
- Trace only `servicemanager`, `hwservicemanager`, and `vndservicemanager`.

## Forbidden

- No `mdm_helper` start.
- No CNSS daemon start.
- No Wi-Fi HAL start.
- No scan/connect/DHCP/route/external ping.
- No `/dev/esoc*` or subsystem trigger.
- No boot image write.

## Success Criteria

- Transcript reaches `pm_service_trigger_observer.result` and `A90_EXECNS_END`.
- `servicemanager` and `vndservicemanager` have `capture_crash=1` if they abort.
- `hwservicemanager` remains cleanly observable or exits with a captured reason.
- Postflight remains safe and forbidden action flags remain false.
