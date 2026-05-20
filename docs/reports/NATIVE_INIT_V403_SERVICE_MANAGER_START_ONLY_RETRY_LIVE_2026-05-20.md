# Native Init v403 Service-Manager Start-Only Retry Live Result

## Summary

V403 live execution completed successfully.

The exact-approved bounded start-only retry ran `servicemanager` and `hwservicemanager` inside the helper v22 private namespace. Both targets reached exec, stayed observable until the bounded timeout, then were terminated, reaped, and postflight-cleaned.

This was not Wi-Fi bring-up. Wi-Fi HAL, `wificond`, supplicant, hostapd, CNSS/diag, scan/connect/link-up, credentials, DHCP, routing, rfkill writes, firmware mutation, and Android partition writes were not executed.

## Approval Used

```text
approve v403 service-manager start-only retry only; no Wi-Fi HAL start and no Wi-Fi bring-up
```

## Evidence

Primary evidence:

- V403 live run: `tmp/wifi/v403-service-manager-start-only-retry-live-20260520-085702/`
- V403 live manifest: `tmp/wifi/v403-service-manager-start-only-retry-live-20260520-085702/manifest.json`
- `servicemanager` transcript: `tmp/wifi/v403-service-manager-start-only-retry-live-20260520-085702/native/run-system-servicemanager.txt`
- `hwservicemanager` transcript: `tmp/wifi/v403-service-manager-start-only-retry-live-20260520-085702/native/run-system-hwservicemanager.txt`
- postflight preflight: `tmp/wifi/v403-service-manager-start-only-postflight-20260520-085747/`
- supplemental HAL readiness refresh: `tmp/wifi/v403-post-service-manager-hal-readiness-refresh-20260520-085835/`

Live result:

```text
decision: service-manager-start-only-live-pass
pass: True
reason: service-manager targets observed until timeout and cleaned
daemon_start_executed: True
wifi_bringup_executed: False
```

Observations:

| target | result | reason | exec | postflight safe |
| --- | --- | --- | --- | --- |
| `system-servicemanager` | `start-only-pass` | `observed-until-timeout-clean-stop` | `True` | `True` |
| `system-hwservicemanager` | `start-only-pass` | `observed-until-timeout-clean-stop` | `True` | `True` |

Postflight:

```text
postflight_clean: True
manager_processes: []
wifi_links: []
```

## Key Runtime Evidence

Both start-only runs used helper v22:

```text
A90_EXECNS_BEGIN version="a90_android_execns_probe v22"
mode=service-manager-start-only
capture_mode=ptrace-lite
linkerconfig_mode=copy-real
```

The private namespace had the V402-proven runtime surface:

```text
context.dev_binder.exists=1
context.dev_hwbinder.exists=1
context.dev_vndbinder.exists=1
context.dev_properties.exists=1
context.selinux_status.exists=1
context.selinux_enforce.exists=1
context.selinux_policy.mode=444
context.plat_service_contexts.mode=644
context.vendor_service_contexts.mode=644
```

`servicemanager` result:

```text
service_manager_start.target=/system/bin/servicemanager
service_manager_start.wifi_hal=0
service_manager_start.scan_connect_linkup=0
service_manager_start.exec_attempted=1
service_manager_start.child_started=1
service_manager_start.timed_out=1
service_manager_start.reaped=1
service_manager_start.postflight_safe=1
service_manager_start.result=start-only-pass
service_manager_start.reason=observed-until-timeout-clean-stop
A90_EXECNS_END rc=0
```

`hwservicemanager` result:

```text
service_manager_start.target=/system/bin/hwservicemanager
service_manager_start.wifi_hal=0
service_manager_start.scan_connect_linkup=0
service_manager_start.exec_attempted=1
service_manager_start.child_started=1
service_manager_start.timed_out=1
service_manager_start.reaped=1
service_manager_start.postflight_safe=1
service_manager_start.result=start-only-pass
service_manager_start.reason=observed-until-timeout-clean-stop
A90_EXECNS_END rc=0
```

The live command compacted `data_wifi_mode` to `none` because the approved command also appends `--allow-service-manager-start-only` and the native shell has a 30-argument command limit. This is acceptable for V403 because this stage only tests service-manager lifecycle, not Wi-Fi data sockets.

## Supplemental HAL Gate Refresh

After V403, the older V364 read-only HAL/service gate was refreshed:

```text
decision: hal-service-readiness-blocked
pass: True
reason: blocked by current-binder-devnodes, current-service-manager-processes, current-property-runtime, linkerconfig-visibility
```

This does not contradict V403. V364 checks the old global/current runtime surface, while V403 proves a private helper-owned namespace with temporary Binder nodes, private properties, linkerconfig/APEX materialization, and bounded service-manager lifecycle.

The correct next step is therefore not direct Wi-Fi HAL start. The next step is a new V404 private-composite HAL readiness packet that uses the V403 model: service-manager/hwservicemanager must be supervised in the same bounded helper-owned runtime while Wi-Fi HAL readiness is checked.

## Interpretation

V403 removes the previous service-manager lifecycle blocker.

Confirmed now:

- helper v22 service-manager start-only path works.
- `servicemanager` can start and stay alive for the bounded observation window.
- `hwservicemanager` can start and stay alive for the bounded observation window.
- both targets can be terminated and reaped cleanly.
- postflight has no lingering manager process and no Wi-Fi link.

Still not proven:

- Wi-Fi HAL start-only.
- HAL registration through the live service-manager/hwservicemanager pair.
- `wificond`, supplicant, hostapd.
- scan/connect/link-up, credentials, DHCP, routing.

## Next Target

Proceed to V404: private-composite Wi-Fi HAL readiness packet.

V404 should be non-mutating first. It should plan how to keep the V403-proven `servicemanager` and `hwservicemanager` pair alive in a bounded helper-owned namespace while checking or later starting only the first Wi-Fi HAL candidate. Wi-Fi scan/connect/link-up and credentials must remain out of scope.
