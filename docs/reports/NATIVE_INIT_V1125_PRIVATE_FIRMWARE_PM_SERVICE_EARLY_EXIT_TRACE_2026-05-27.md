# V1125 Private Firmware PM Service Early Exit Trace Report

Date: `2026-05-27`

## Result

- Decision: `v1125-private-firmware-binder-add-service-failure`
- Pass: `true`
- Evidence: `tmp/wifi/v1125-private-firmware-pm-service-early-exit-trace/manifest.json`
- Summary: `tmp/wifi/v1125-private-firmware-pm-service-early-exit-trace/summary.md`
- Runner: `scripts/revalidation/native_wifi_private_firmware_pm_service_early_exit_trace_v1125.py`
- Helper: `a90_android_execns_probe v212`

## Summary

V1125 traced `pm-service` inside the helper-private firmware PM observer
namespace, without starting `cnss-daemon`, Wi-Fi HAL, scan/connect, DHCP, or
external ping.

The private firmware surface was active:

```text
private_firmware_mounts_requested=1
private_firmware_mnt_mounted=1
private_firmware_modem_mounted=1
```

Tracefs uprobes captured the terminal PM-service branch:

```text
pm_success_branch_after_get_system_info=1
pm_init_with_driver_call=1
pm_default_service_manager_call=1
pm_string16_ctor=1
pm_add_service_call=1
pm_add_service_fail_log=1
pm_pthread_create_call=0
pm_qmi_service_start_log=0
pm_clean_return_zero=1
```

## Interpretation

The provider loss is now classified before the QMI worker path. `pm-service`
successfully gets past the system-info branch and attempts Binder service
registration, but the `addService` failure branch fires immediately. It then
performs clean shutdown and returns zero.

This narrows the blocker from a broad PeripheralManager runtime failure to the
registration path for `vendor.qcom.PeripheralManager` under the native
`vndservicemanager`/SELinux/runtime namespace surface.

## Safety

- `tracefs_write_executed=true`
- `bpf_attach_executed=false`
- `cnss_daemon_start_executed=false`
- `wifi_hal_start_executed=false`
- `scan_connect_executed=false`
- `credential_use_executed=false`
- `dhcp_route_executed=false`
- `external_ping_executed=false`
- `wifi_bringup_executed=false`

The observer reported `observer-reboot-required` because `pm_proxy_helper`
remained in D-state after the window. A cleanup reboot was performed after
evidence capture.

Post-reboot verification:

```text
version: A90 Linux init 0.9.68 (v724)
selftest: pass=11 warn=1 fail=0
netservice: ncm0=absent tcpctl=stopped
residual PM/service-manager/CNSS actors: none matched
```

Additional post-reboot process evidence:
`tmp/wifi/v1125-post-pass-reboot-ps.txt`.

## Tooling Note

The collector runs through serial `cmdv1 run` rather than `a90_tcpctl run`.
`a90_tcpctl` has a 10 second device-side run timeout, while this observer window
needs slightly more than 10 seconds to run, collect trace counts, and clean up
tracefs events.

## Next

V1126 should classify the Binder `addService` failure itself. Useful evidence is
the exact PM-service failure log text, `vndservicemanager` state at registration
time, and whether the failure is caused by service-manager readiness, SELinux
service context/policy, Binder device namespace, or an invalid service name
contract.
