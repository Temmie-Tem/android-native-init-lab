# Native Init V1063 PM Service Trigger Classifier Report

Date: `2026-05-27`

## Summary

V1063 is a host-only classifier over existing Android-positive and native PM
evidence.  No device command was executed.

Decision:

```text
v1063-pm-service-idle-input-gap-classified
```

The blocker is now narrower than firmware visibility, helper modem pre-holder,
`pm_proxy_helper`, property coverage, provider registration, or basic
`pm-service` process launch.  Native `pm-service` is alive in the expected PM
domain surface, opens `vndbinder`, then sleeps in `SyS_nanosleep` with no
`/dev/subsys_modem` fd.  Android proves the same actor should hold
`/dev/subsys_modem` before the WLFW chain completes.

## Evidence

Private evidence directory:

```text
tmp/wifi/v1063-pm-service-trigger-classifier/
```

Manifest:

```text
tmp/wifi/v1063-pm-service-trigger-classifier/manifest.json
```

Inputs:

```text
tmp/wifi/v1024-fast-fd-contract-classifier/manifest.json
tmp/wifi/v1046-android-vendor-init-rc-handoff/manifest.json
tmp/wifi/v1061-global-firmware-pm-full-contract/manifest.json
tmp/wifi/v1061-global-firmware-pm-full-contract/native/pm-full-contract-with-global-firmware.txt
tmp/wifi/v1062-pm-contract-gap-classifier/manifest.json
tmp/wifi/v860-pm-service-property-superset-replay-live/manifest.json
tmp/wifi/v861-pm-service-domain-parity-live-r2/manifest.json
docs/reports/NATIVE_INIT_V692_PERIPHERAL_REGISTRY_SNAPSHOT_LIVE_2026-05-24.md
docs/reports/NATIVE_INIT_V694_PERIPHERAL_VNDSERVICE_QUERY_LIVE_2026-05-24.md
stage3/linux_init/helpers/a90_android_execns_probe.c
```

## Classification

| Item | Value |
| --- | --- |
| Android-positive PM/eSoC fd chain | `true` |
| Native `pm-service` idle fd gap | `true` |
| Older property/provider routes closed | `true` |
| Helper direct-exec source gap | `true` |
| eSoC warning remains blocker | `true` |

## Android Positive

V1024 captured:

| Actor | Evidence |
| --- | --- |
| `pm_proxy_helper` | `/dev/subsys_modem` fd |
| `pm-service` | `/dev/subsys_modem` fd |
| `mdm_helper` | `/dev/esoc-0` fd |
| WLFW chain | `wlfw_start`, WLAN-PD, firmware-ready, `wlan0` |

The Android timing still matters because it shows the PM fd contract is not an
optional later cleanup path.  It is part of the working lower bring-up prefix.

## Native V1061

V1061 reached the relevant prefix:

```text
modem_pre_holder_confirmed=1
pm_proxy_helper_subsys_modem_fd_count=1
pm_proxy_started=1
mdm_helper_esoc0_fd_seen=1
```

The missing native edge remained stable for the full poll window:

```text
per_mgr_subsys_modem_fd_count=0
pm_full_contract_seen=0
```

The gap snapshot showed `pm-service` was not blocked in a kernel subsystem open.
It was sleeping:

```text
wchan=SyS_nanosleep
stack=SyS_nanosleep
```

The fd set included `vndbinder`, pipes, and a socket, but no
`/dev/subsys_modem`.  This makes a missing runtime request/input more likely
than a low-level device-node or SELinux open failure.

## Prior Routes Closed

- V860 removed the relevant private property denials; `pm-service` was
  observable but still had no subsystem fd.
- V694 confirmed `vendor.qcom.PeripheralManager` vndservice registration; that
  alone did not produce WLFW/BDF/`wlan0`.
- V861 showed target mapping/direct exec changes alone were insufficient.
- V1061 improved the lower prerequisite enough for `pm_proxy_helper` to hold
  `/dev/subsys_modem`, but `pm-service` still stayed idle.

## Interpretation

The next gate should not be another V1061 retry.  It should be source/build-only
support for a PM-service trigger observer that models Android init service
state and captures the exact input that makes `pm-service` leave its idle
vndbinder loop and open `/dev/subsys_modem`.

The V1061 eSoC reference-count warning also remains a hard blocker for another
live widening until the cleanup path is understood.

## Guardrails

- Host-only; no device command.
- No live retry, actor start, service-manager start, Wi-Fi HAL start,
  scan/connect, credentials, DHCP/routes, external ping, eSoC open/ioctl,
  sysfs/debugfs write, boot image write, partition write, firmware mutation, or
  Android handoff.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pm_service_trigger_classifier_v1063.py
python3 scripts/revalidation/native_wifi_pm_service_trigger_classifier_v1063.py run
```

Result:

```text
decision: v1063-pm-service-idle-input-gap-classified
pass: True
device_commands_executed: False
```

## Next

V1064 should be source/build-only first:

1. Add a PM service trigger observer mode to the helper.
2. Preserve no-subsystem-open/no-Wi-Fi guardrails.
3. Model Android init service state and PM actor lifecycle more explicitly than
   direct `execv`.
4. Capture `pm-service` vndbinder/property requests and fd transitions long
   enough to identify the missing trigger before any live PM retry.
