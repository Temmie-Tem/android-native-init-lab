# Native Init V1070 PM Observer Compact Crash Capture Report

## Summary

V1070 captured compact ptrace evidence for the PM observer service-manager
abort path. The live gate reached the final helper summary and stayed postflight
safe. `servicemanager` and `vndservicemanager` both reached exec and then hit
`SIGABRT`; `hwservicemanager` reached exec and stayed observable until cleanup.

## Change

- Bumped `a90_android_execns_probe` to `v188`.
- Allowed `--capture-mode ptrace-lite` for
  `wifi-companion-pm-service-trigger-observer`.
- Traced only service-manager identities in PM observer mode.
- Added compact observable capture that omits large `maps` dumps for this trace
  gate.
- Added V1070 runner wrapper that removes the outer toybox timeout wrapper to
  stay inside the argument budget and relies on helper `--timeout-sec`.

## Evidence

| item | path / value |
| --- | --- |
| build log | `tmp/wifi/v1070-execns-helper-v188-build/build.log` |
| helper sha256 | `52c65e7a020cfe82d632bdc88379abce78451b3e38dbc91f47a2c2792723cfa3` |
| deploy log | `tmp/wifi/v1070-execns-helper-v188-build/deploy.log` |
| live manifest | `tmp/wifi/v1070-pm-observer-compact-crash-capture-live/manifest.json` |
| live transcript | `tmp/wifi/v1070-pm-observer-compact-crash-capture-live/host/pm-service-trigger-observer.txt` |

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

## Crash Capture

```text
servicemanager: traced=1 capture_exec=1 capture_crash=1 signal=6
hwservicemanager: traced=1 capture_exec=1 capture_crash=0 signal=15 cleanup
vndservicemanager: traced=1 capture_exec=1 capture_crash=1 signal=6
```

Key captured fields:

```text
capture.crash.exe=/tmp/a90-v231-1070/root/system/bin/servicemanager
capture.crash.attr/current.value=kernel\x00
capture.crash.exe=/tmp/a90-v231-1070/root/vendor/bin/vndservicemanager
capture.crash.attr/current.value=kernel\x00
```

Stderr still reports the two aborts and the hwservice duplicate warnings:

```text
libc: Fatal signal 6 (SIGABRT) ... servicemanager
Multiple same specifications for vendor.qti.hardware.data.iwlan::IIWlan.
Multiple same specifications for com.qualcomm.qti.imscmservice::IImsCmService.
libc: Fatal signal 6 (SIGABRT) ... vndservicemanag
```

## Remaining Blocker

The PM observer private root still lacks a SELinux filesystem surface:

```text
context.selinux_status.exists=0
context.selinux_enforce.exists=0
context.selinux_policy.exists=0
context.selinux_service_manager_class.exists=0
```

Older service-manager start-only evidence had those nodes materialized. The next
minimal gate should add PM observer to `materialize_selinuxfs_surface()` and
rerun the same bounded observer before changing PM ordering or starting wider
Wi-Fi actors.
