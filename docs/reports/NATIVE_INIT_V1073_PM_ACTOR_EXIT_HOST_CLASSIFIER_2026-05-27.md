# Native Init V1073 PM Actor Exit Host Classifier Report

## Summary

V1073 added a host-only classifier for the `pm-service` exit-255 blocker.  The
classifier passed and closed two weak hypotheses: Android init socket creation
is not missing, and V1072 did not simply miss a short-lived persistent
`/dev/subsys_modem` or `/dev/vndbinder` fd.

The exact syscall/reason for exit `255` is still not proven by host-only data.
The next useful gate is a bounded `pm-service`-only syscall/input classifier.

## Change

- Added `scripts/revalidation/native_wifi_pm_actor_exit_host_classifier_v1073.py`.
- Parsed the V1072 ptrace exit snapshot for `per_mgr` and `per_proxy`.
- Parsed Android vendor init rc service contracts.
- Parsed host-extracted vendor binary strings and dynamic dependencies.
- Wrote private evidence to
  `tmp/wifi/v1073-pm-actor-exit-host-classifier/manifest.json`.

## Evidence

| item | path / value |
| --- | --- |
| classifier | `scripts/revalidation/native_wifi_pm_actor_exit_host_classifier_v1073.py` |
| V1072 manifest | `tmp/wifi/v1072-pm-observer-pm-actor-exit-fd-trace-v192-live/manifest.json` |
| V1072 transcript | `tmp/wifi/v1072-pm-observer-pm-actor-exit-fd-trace-v192-live/host/pm-service-trigger-observer.txt` |
| V1073 manifest | `tmp/wifi/v1073-pm-actor-exit-host-classifier/manifest.json` |
| V1073 summary | `tmp/wifi/v1073-pm-actor-exit-host-classifier/summary.md` |

## Classifier Result

```text
decision: v1073-pm-actor-exit-host-classified
pass: True
reason: host-only rc/strings/evidence eliminate init socket creation and stale fd-observation gaps; exact exit-255 syscall remains unproven because pm-service logs are not present on stderr
next: V1074 bounded pm-service-only syscall/input classifier for openat/connect/bind/ioctl/property/binder/logd failures
```

## Init RC Classification

`vendor.per_mgr` is a normal class-core service.  There is no `socket`
directive, so an Android-init-created socket missing from native init is not the
current explanation for exit `255`.

```text
service vendor.per_mgr /vendor/bin/pm-service
    class core
    user system
    group system
    ioprio rt 4

service vendor.per_proxy /vendor/bin/pm-proxy
    class core
    user system
    group system
    disabled

on property:init.svc.vendor.per_mgr=running
    start vendor.per_proxy
```

`pm_proxy_helper` is separate and is started at Android `post-fs-data`:

```text
service vendor.per_proxy_helper /vendor/bin/pm_proxy_helper
    class core
    user system
    group system
    disabled
    oneshot

on post-fs-data
    start vendor.per_proxy_helper
```

## Binary Surface

`pm-service` depends on:

```text
libcutils.so
libutils.so
liblog.so
libbinder.so
libqmi_cci.so
libqmi_common_so.so
libqmi_encdec.so
libqmi_csi.so
libmdmdetect.so
libperipheral_client.so
```

Relevant host-only string evidence:

- `pm-service` contains `/dev/vndbinder` and `vendor.qcom.PeripheralManager`.
- `pm-service` contains `Failed to get system information` and
  `Failed to init peripheral`.
- `pm-service` does not contain a direct `/dev/subsys_modem` literal.
- `pm_proxy_helper` contains `/dev/subsys_modem`.
- `libmdmdetect.so` contains `/sys/bus/msm_subsys/devices`,
  `/sys/bus/esoc/devices`, and `/dev/subsys_%s`.
- `libqmi_csi.so` contains QRTR/QMI server registration surfaces.

## Runtime Boundary

V1072 already captured the PM actors at exit:

```text
pm_service_trigger_observer.child.per_mgr.exit_code=255
pm_service_trigger_observer.child.per_mgr.capture_exit=1
pm_service_trigger_observer.child.per_mgr.trace_exit_event=0x0000ff00

pm_service_trigger_observer.child.per_proxy.exit_code=1
pm_service_trigger_observer.child.per_proxy.capture_exit=1
pm_service_trigger_observer.child.per_proxy.trace_exit_event=0x00000100
```

The `per_mgr` exit fd set had only `/dev/null`, pipes, and sockets.  It did not
include `/dev/subsys_modem` or `/dev/vndbinder`.

## Stderr Capture

The current observer captures stderr, but it did not capture diagnostic
`pm-service` output:

```text
has_per_mgr_text=False
has_pm_proxy_helper_property_context=True
diagnostic_for_pm_service_exit=False
```

This means stderr alone is not enough to determine the exit-255 syscall/reason.
`pm-service` likely logs via Android `liblog` rather than writing the decisive
failure to stderr.

## Eliminated Causes

| cause | result |
| --- | --- |
| Missing Android init `socket` directive | eliminated |
| V1072 missing a persistent PM actor fd | eliminated |
| Direct `pm-service` literal `/dev/subsys_modem` open path | unlikely; that literal is in `pm_proxy_helper` |
| Stderr as sufficient root-cause evidence | eliminated |

## Remaining Failure Classes

| class | confidence | missing proof |
| --- | --- | --- |
| `mdmdetect` system-info or peripheral init failure | medium | failed sysfs/device lookup syscall and errno |
| QMI CSI / QRTR register or control socket failure | medium | socket family, bind/connect errno, QMI register return |
| vndbinder addService failure | low-medium | binder open/addService reachability and errno |

## Next Gate

V1074 should be a bounded `pm-service`-only syscall/input classifier.  It should
trace only selected startup syscalls and inputs:

- `openat` / `stat` for `/sys/bus/msm_subsys`, `/sys/bus/esoc`,
  `/dev/subsys_*`, `/dev/vndbinder`, `/vendor/etc/qmi_fw.conf`.
- `socket`, `bind`, `connect`, and `ioctl` for QRTR/QMI/binder setup.
- property-area reads for `vendor.peripheral.*` and linker/runtime properties.
- `liblog`/logd socket interactions if visible.

The gate must keep `mdm_helper`, CNSS, Wi-Fi HAL, scan/connect, DHCP, route
changes, external ping, `/dev/esoc*`, and boot image writes forbidden.
