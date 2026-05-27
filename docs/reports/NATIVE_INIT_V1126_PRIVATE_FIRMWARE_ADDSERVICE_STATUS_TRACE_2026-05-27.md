# V1126 Private Firmware addService Status Trace Report

Date: `2026-05-27`

## Result

- Decision: `v1126-private-firmware-addservice-status-permission-denied--1`
- Pass: `true`
- Evidence: `tmp/wifi/v1126-private-firmware-addservice-status-trace/manifest.json`
- Summary: `tmp/wifi/v1126-private-firmware-addservice-status-trace/summary.md`
- Runner: `scripts/revalidation/native_wifi_private_firmware_addservice_status_trace_v1126.py`
- Helper: `a90_android_execns_probe v212`

## Summary

V1126 replayed the V1125 helper-private firmware PM observer path and added
tracefs fetches around `IServiceManager::addService()`.

The runtime preconditions were active:

```text
private_firmware_mounts_requested=1
private_firmware_mnt_mounted=1
private_firmware_modem_mounted=1
vndservicemanager_readiness.ready=1
```

The `addService()` return value was captured from ARM64 `x0` immediately after
the indirect call:

```json
{
  "raw": "0xffffffff",
  "signed32": -1,
  "name": "PERMISSION_DENIED"
}
```

Tracefs counts:

```json
{
  "pm_success_branch_after_get_system_info": 1,
  "pm_default_service_manager_call": 1,
  "pm_add_service_call": 1,
  "pm_add_service_status": 1,
  "pm_add_service_fail_log": 1,
  "pm_clean_return_zero": 1
}
```

## Interpretation

The private-firmware provider regression is now a service-manager permission
failure, not a missing readiness signal, missing firmware mount, QMI startup
issue, or PM-service crash.

Current branch:

```text
private firmware mounts active
  -> vndservicemanager ready
  -> pm-service reaches get_system_info success
  -> pm-service calls addService("vendor.qcom.PeripheralManager", ...)
  -> addService returns PERMISSION_DENIED (-1)
  -> pm-service logs addService failure
  -> pm-service clean returns 0
```

The next blocker is therefore the permission decision inside
`vndservicemanager` for `vendor.qcom.PeripheralManager` under the private
firmware namespace.

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

Additional process evidence:
`tmp/wifi/v1126-post-pass-reboot-ps.txt`.

## Next

V1127 should classify the `PERMISSION_DENIED` source:

1. compare `/vendor/etc/selinux/vndservice_contexts` and resolved service label
   for `vendor.qcom.PeripheralManager`;
2. capture `vndservicemanager` stderr/logcat-equivalent output around
   `addService`;
3. compare the private firmware namespace service-manager context and SELinux
   state with the provider-positive V1092/V1095 path;
4. only after the permission path is repaired, return to the CNSS PM
   register/connect branch.
