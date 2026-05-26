# Native Init V1071 PM Observer SELinuxfs Surface Report

## Summary

V1071 added SELinuxfs surface materialization to the PM service trigger observer
private root. The live gate passed safety checks and removed the V1070
service-manager crash boundary: `servicemanager`, `hwservicemanager`, and
`vndservicemanager` all stayed observable until bounded cleanup.

The remaining runtime gap moved to the peripheral-manager side:
`per_mgr` exits with `255`, `per_proxy` exits with `1`, and neither
`pm_proxy_helper` nor `per_mgr` observes `/dev/subsys_modem`.

## Change

- Bumped `a90_android_execns_probe` to `v189`.
- Allowed `materialize_selinuxfs_surface()` for
  `wifi-companion-pm-service-trigger-observer` only when
  `--allow-pm-service-trigger-observer` is present.
- Reused the V1070 compact ptrace PM observer runner for bounded validation.

## Evidence

| item | path / value |
| --- | --- |
| build log | `tmp/wifi/v1071-execns-helper-v189-build/build.log` |
| helper sha256 | `66b43714f9b3116b1f76a7fc4ebe526bb04897d726ac1da1ad46fa77a98beb75` |
| deploy log | `tmp/wifi/v1071-execns-helper-v189-build/deploy.log` |
| live manifest | `tmp/wifi/v1071-pm-observer-selinuxfs-surface-live/manifest.json` |
| live transcript | `tmp/wifi/v1071-pm-observer-selinuxfs-surface-live/host/pm-service-trigger-observer.txt` |

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

## SELinuxfs Delta

The private root now sees the critical SELinuxfs nodes:

```text
context.selinux_status.exists=1
context.selinux_enforce.exists=1
context.selinux_policy.exists=1
```

The service-manager class entries remain absent on this kernel surface:

```text
context.selinux_service_manager_class.exists=0
context.selinux_service_manager_list.exists=0
context.selinux_service_manager_add.exists=0
context.selinux_service_manager_find.exists=0
```

## Service-Manager Delta

V1070:

```text
servicemanager signal=6 capture_crash=1
vndservicemanager signal=6 capture_crash=1
```

V1071:

```text
servicemanager observable=1 signal=15 capture_crash=0 postflight_safe=1
hwservicemanager observable=1 signal=15 capture_crash=0 postflight_safe=1
vndservicemanager observable=1 signal=15 capture_crash=0 postflight_safe=1
```

The `signal=15` exits are bounded cleanup, not spontaneous crashes.

## Remaining Blocker

```text
per_mgr observable=0 exit_code=255 postflight_safe=1
per_proxy observable=0 exit_code=1 postflight_safe=1
per_mgr_subsys_modem_seen=0
pm_proxy_helper_subsys_modem_seen=0
pm_service_trigger_observer.reason=child-exited-before-observe-window
```

Stderr still shows property-context warnings for `pm_proxy_helper`:

```text
libc: Could not find context for property "debug.ld.app.pm_proxy_helper"
libc: Access denied finding property "debug.ld.app.pm_proxy_helper"
libc: Could not find context for property "arm64.memtag.process.pm_proxy_helper"
libc: Access denied finding property "arm64.memtag.process.pm_proxy_helper"
```

Next work should classify why `per_mgr` and `per_proxy` exit before the observe
window. The service-manager crash path should be treated as repaired for this
PM observer gate.

## Postflight

```text
selftest: pass=11 warn=1 fail=0
a90_tcpctl v1 ready
listen: bind=192.168.7.2 port=2325 auth=required
```
