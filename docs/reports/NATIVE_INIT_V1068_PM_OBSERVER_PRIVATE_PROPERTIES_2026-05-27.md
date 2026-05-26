# Native Init V1068 PM Observer Private Properties Report

## Summary

V1068 repaired the PM observer private namespace so `/dev/__properties__` is
present. The live gate remained safe but still hit a service-manager runtime gap:
`servicemanager` and `vndservicemanager` abort with `SIGABRT`; `hwservicemanager`
stays observable until cleanup.

## Change

- Bumped `a90_android_execns_probe` to `v186`.
- Added `wifi-companion-pm-service-trigger-observer` to
  `materialize_private_properties()` when `--allow-pm-service-trigger-observer`
  and `--property-root` are present.

## Evidence

| item | path / value |
| --- | --- |
| build log | `tmp/wifi/v1068-execns-helper-v186-build/build.log` |
| deployed helper sha256 | `d11dd864f7a4114c9b77a0b7eaee23330e54d855be70501495a69fdd96139739` |
| deploy log | `tmp/wifi/v1068-execns-helper-v186-build/deploy.log` |
| live manifest | `tmp/wifi/v1068-pm-observer-private-properties-live/manifest.json` |
| live transcript | `tmp/wifi/v1068-pm-observer-private-properties-live/host/pm-service-trigger-observer.txt` |

## Live Result

```text
decision: v1066-observer-runtime-gap-clean
pass: True
reason: all_observable=0 all_postflight_safe=1
pm_service_subsys_modem_seen: False
pm_proxy_helper_subsys_modem_seen: False
mdm_helper_start_executed: False
cnss_daemon_start_executed: False
subsys_esoc0_open_attempted: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
external_ping_executed: False
```

## Positive Delta

```text
context.dev_properties.exists=1
context.dev_properties.type=directory
```

The previous warning is gone:

```text
libc: Using old property service protocol ("ro.property_service.version" is not set)
```

## Remaining Blocker

```text
servicemanager signal=6
vndservicemanager signal=6
hwservicemanager observable=1, cleanup signal=15
pm-service exit_code=255
pm-proxy exit_code=1
```

`pm_proxy_helper` stays observable but does not open `/dev/subsys_modem`.
The next gate should capture the `servicemanager` and `vndservicemanager`
`SIGABRT` cause with ptrace-lite or an equivalent compact crash surface before
changing PM actor ordering.
