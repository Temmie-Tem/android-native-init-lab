# Native Init V1072 PM Actor Exit Trace Plan

## Goal

Classify the `per_mgr` and `per_proxy` early-exit boundary left by V1071 without
starting any wider Wi-Fi actor.  The observer must prove whether these PM actors
open `/dev/subsys_modem` or `/dev/vndbinder` before exiting.

## Background

V1071 repaired the PM observer SELinuxfs surface and removed the V1070
`servicemanager`/`vndservicemanager` aborts.  The remaining gap moved to the PM
actors:

```text
per_mgr exit_code=255
per_proxy exit_code=1
per_mgr_subsys_modem_seen=0
pm_proxy_helper_subsys_modem_seen=0
```

V1071 only reported final exit codes.  It did not capture the PM actor process
state at the exit boundary, so a short-lived fd open could still be missed.

## Gate

- Bump `a90_android_execns_probe` to `v192`.
- Extend PM observer `ptrace-lite` to trace `per_mgr` and `per_proxy` in addition
  to the service-manager actors.
- Enable `PTRACE_O_TRACEEXIT` for traced composite children.
- Capture child-specific `per_mgr_exit` and `per_proxy_exit` snapshots with fd
  links at the trace exit stop.
- Deploy only `/cache/bin/a90_android_execns_probe` over NCM.
- Reuse the bounded PM observer live runner with `--capture-mode ptrace-lite`.

## Forbidden

- No `mdm_helper` start.
- No CNSS daemon start.
- No Wi-Fi HAL start.
- No scan/connect/DHCP/route/external ping.
- No `/dev/esoc*` or subsystem trigger.
- No boot image write.

## Success Criteria

- Final transcript reaches `A90_EXECNS_END rc=0`.
- `per_mgr` and `per_proxy` both have `capture_exit=1`.
- Exit snapshots include child-specific fd links.
- Postflight remains safe and forbidden action flags remain false.
- The evidence determines whether PM actors opened `/dev/subsys_modem` or
  `/dev/vndbinder` before exiting.
