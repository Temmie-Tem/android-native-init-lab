# Native Init V1071 PM Observer SELinuxfs Surface Plan

## Goal

Materialize the host SELinux filesystem surface inside the private Android root
used by `wifi-companion-pm-service-trigger-observer` and verify whether the
service-manager aborts from V1070 disappear.

## Background

V1070 proved that compact ptrace capture works and that the PM observer private
root has binder devices and private properties, but it still lacked the SELinux
filesystem surface:

```text
context.selinux_status.exists=0
context.selinux_enforce.exists=0
context.selinux_policy.exists=0
context.selinux_service_manager_class.exists=0
```

`servicemanager` and `vndservicemanager` both aborted with `SIGABRT` in that
state. Older service-manager start-only evidence showed that the SELinuxfs
surface is part of the minimum runtime contract for these binaries.

## Gate

- Bump `a90_android_execns_probe` to `v189`.
- Add `wifi-companion-pm-service-trigger-observer` to
  `materialize_selinuxfs_surface()` when `--allow-pm-service-trigger-observer`
  is present.
- Build a static aarch64 helper.
- Deploy only `/cache/bin/a90_android_execns_probe` over NCM.
- Reuse the compact PM observer live gate with `--capture-mode ptrace-lite`.

## Forbidden

- No `mdm_helper` start.
- No CNSS daemon start.
- No Wi-Fi HAL start.
- No scan/connect/DHCP/route/external ping.
- No `/dev/esoc*` or subsystem trigger.
- No boot image write.

## Success Criteria

- `context.selinux_status.exists=1`.
- `context.selinux_enforce.exists=1`.
- `context.selinux_policy.exists=1`.
- The live gate reaches `pm_service_trigger_observer.result` and
  `A90_EXECNS_END`.
- Postflight remains safe and forbidden action flags remain false.
- If service-manager processes still fail, the transcript must classify the next
  blocker without widening the live action scope.
