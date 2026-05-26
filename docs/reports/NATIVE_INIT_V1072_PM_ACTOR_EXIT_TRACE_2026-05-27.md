# Native Init V1072 PM Actor Exit Trace Report

## Summary

V1072 added child-specific ptrace exit capture for the PM observer's `per_mgr`
and `per_proxy` actors.  The final v192 live gate passed safety checks and
proved that both actors exit before opening `/dev/subsys_modem` or
`/dev/vndbinder`.

This narrows the blocker from "maybe a short-lived fd was missed" to an earlier
PM actor startup/input failure: both processes reach exec, open only basic pipes
and sockets, then exit (`pm-service` status `255`, `pm-proxy` status `1`).

## Change

- Bumped `a90_android_execns_probe` to `v192`.
- Added suffix helper `str_has_suffix()` for child-specific exit labels.
- Added `PTRACE_O_TRACEEXIT` handling to composite child tracing.
- Included `per_mgr` and `per_proxy` in PM observer `ptrace-lite` tracing.
- Added final PM observer fields:
  - `capture_exit`
  - `trace_exit_event`
- Added fd summary/link capture for `*_exit` ptrace snapshots.

## Evidence

| item | path / value |
| --- | --- |
| build log | `tmp/wifi/v1072-execns-helper-v192-build/build.log` |
| helper sha256 | `b7bd0755ffe96e30656627a928d1d1e7771848e166da4dec5b44bb288ce90925` |
| deploy log | `tmp/wifi/v1072-execns-helper-v192-build/deploy.log` |
| live manifest | `tmp/wifi/v1072-pm-observer-pm-actor-exit-fd-trace-v192-live/manifest.json` |
| live transcript | `tmp/wifi/v1072-pm-observer-pm-actor-exit-fd-trace-v192-live/host/pm-service-trigger-observer.txt` |

## Live Result

```text
decision: v1066-observer-runtime-gap-clean
pass: True
reason: all_observable=0 all_postflight_safe=1
mdm_helper_start_executed: False
cnss_daemon_start_executed: False
subsys_esoc0_open_attempted: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
external_ping_executed: False
```

## Exit Trace

```text
pm_service_trigger_observer.child.per_mgr.exit_code=255
pm_service_trigger_observer.child.per_mgr.traced=1
pm_service_trigger_observer.child.per_mgr.capture_exec=1
pm_service_trigger_observer.child.per_mgr.capture_exit=1
pm_service_trigger_observer.child.per_mgr.trace_exit_event=0x0000ff00

pm_service_trigger_observer.child.per_proxy.exit_code=1
pm_service_trigger_observer.child.per_proxy.traced=1
pm_service_trigger_observer.child.per_proxy.capture_exec=1
pm_service_trigger_observer.child.per_proxy.capture_exit=1
pm_service_trigger_observer.child.per_proxy.trace_exit_event=0x00000100
```

The raw exit status values match the final exit codes (`0xff00` for `255`,
`0x0100` for `1`).

## Exit FD Surface

`pm-service` exit-stop fd set:

```text
capture.per_mgr_exit.fd_links.count=6
capture.per_mgr_exit.fd_links.entry_00.target=/dev/null
capture.per_mgr_exit.fd_links.entry_01.target=pipe:[...]
capture.per_mgr_exit.fd_links.entry_02.target=pipe:[...]
capture.per_mgr_exit.fd_links.entry_03.target=socket:[...]
capture.per_mgr_exit.fd_links.entry_04.target=socket:[...]
capture.per_mgr_exit.fd_links.entry_05.target=socket:[...]
```

`pm-proxy` exit-stop fd set:

```text
capture.per_proxy_exit.fd_links.count=6
capture.per_proxy_exit.fd_links.entry_00.target=/dev/null
capture.per_proxy_exit.fd_links.entry_01.target=pipe:[...]
capture.per_proxy_exit.fd_links.entry_02.target=pipe:[...]
capture.per_proxy_exit.fd_links.entry_03.target=socket:[...]
capture.per_proxy_exit.fd_links.entry_04.target=socket:[...]
capture.per_proxy_exit.fd_links.entry_05.target=socket:[...]
```

Classifier checks over the final transcript:

```text
subsys_modem in PM actor exit fd: false
vndbinder in PM actor exit fd: false
```

## Remaining Blocker

The PM actors exit before opening the subsystem or vndbinder fds.  The next
useful gate is a narrower syscall/input classifier for `pm-service` and
`pm-proxy`: capture selected `openat`, `connect`, `ioctl`, property-area, and
binder-related failures up to exit.  Starting `mdm_helper`, CNSS, Wi-Fi HAL,
scan/connect, DHCP, route changes, or external ping is still premature.

## Postflight

```text
selftest: pass=11 warn=1 fail=0
a90_tcpctl v1 ready
listen: bind=192.168.7.2 port=2325 auth=required
```
