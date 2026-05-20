# Native Init v407 Composite Wi-Fi HAL Start-Only Retry Live Result

## Summary

The exact-approved V407 bounded composite Wi-Fi HAL start-only retry completed successfully.

This run started only the approved trio inside one helper-owned private namespace:

- `servicemanager`
- `hwservicemanager`
- first Wi-Fi HAL candidate `vendor.wifi_hal_ext`

The run did not execute scan/connect/link-up, credentials, DHCP, routing, `wificond`, supplicant, hostapd, CNSS/diag lifecycle, firmware mutation, persistence, or Wi-Fi bring-up.

V407 is the first composite HAL start-only PASS: all three approved child processes were observable until the timeout, then SIGTERM-cleaned and reaped with safe postflight.

## Approval Used

```text
approve v407 composite Wi-Fi HAL start-only retry only; no scan/connect/link-up and no Wi-Fi bring-up
```

## Evidence

- approved live run: `tmp/wifi/v407-composite-hal-start-only-retry-live-20260520-101410/`
- live manifest: `tmp/wifi/v407-composite-hal-start-only-retry-live-20260520-101410/manifest.json`
- native transcript: `tmp/wifi/v407-composite-hal-start-only-retry-live-20260520-101410/native/run-composite-hal.txt`
- postflight process snapshot: `tmp/wifi/v407-composite-hal-start-only-retry-live-20260520-101410/native/post-ps.txt`
- postflight network snapshot: `tmp/wifi/v407-composite-hal-start-only-retry-live-20260520-101410/native/post-proc-net-dev.txt`

Result:

```text
decision: v407-composite-hal-start-only-retry-pass
pass: True
reason: composite HAL target observed until timeout and cleaned
next_step: route next Wi-Fi HAL registration evidence
device_commands_executed: True
device_mutations: True
daemon_start_executed: True
wifi_hal_start_executed: True
wifi_bringup_executed: False
```

Helper result:

```text
helper_result: start-only-pass
helper_reason: observed-until-timeout-clean-stop
all_observable_at_timeout: True
all_postflight_safe: True
```

## Start-Only Boundary

The helper used the V406-proven private APEX mapping:

```text
A90_EXECNS_BEGIN version="a90_android_execns_probe v24"
mode=wifi-hal-composite-start-only
vndk_apex_alias_mode=v30-to-system-ext-v30
target=/vendor/bin/hw/vendor.samsung.hardware.wifi@2.0-service
allow_service_manager_start_only=1
allow_wifi_hal_start_only=1
helper_status=namespace-ready
```

The previously missing Wi-Fi interface library remained visible:

```text
context.apex_vndk_v30_wifi_1_0.path=/apex/com.android.vndk.v30/lib64/android.hardware.wifi@1.0.so
context.apex_vndk_v30_wifi_1_0.exists=1
context.apex_vndk_v30_wifi_1_0.hash=0x9969c125519d75f5
```

The explicit Wi-Fi exclusion guard stayed active:

```text
wifi_hal_composite_start.scan_connect_linkup=0
wifi_hal_composite_start.wificond=0
wifi_hal_composite_start.supplicant=0
wifi_hal_composite_start.hostapd=0
wifi_hal_composite_start.cnss_diag=0
```

## Child Process Result

All three approved children started:

```text
wifi_hal_composite_start.child.servicemanager.child_started=1
wifi_hal_composite_start.child.hwservicemanager.child_started=1
wifi_hal_composite_start.child.wifi_hal.child_started=1
wifi_hal_composite_start.child_started=3
```

All three were observable until timeout and then cleaned:

```text
wifi_hal_composite_start.child.servicemanager.observable=1
wifi_hal_composite_start.child.servicemanager.signal=15
wifi_hal_composite_start.child.servicemanager.reaped=1
wifi_hal_composite_start.child.servicemanager.postflight_safe=1

wifi_hal_composite_start.child.hwservicemanager.observable=1
wifi_hal_composite_start.child.hwservicemanager.signal=15
wifi_hal_composite_start.child.hwservicemanager.reaped=1
wifi_hal_composite_start.child.hwservicemanager.postflight_safe=1

wifi_hal_composite_start.child.wifi_hal.observable=1
wifi_hal_composite_start.child.wifi_hal.signal=15
wifi_hal_composite_start.child.wifi_hal.reaped=1
wifi_hal_composite_start.child.wifi_hal.postflight_safe=1

wifi_hal_composite_start.all_observable_at_timeout=1
wifi_hal_composite_start.all_postflight_safe=1
wifi_hal_composite_start.result=start-only-pass
wifi_hal_composite_start.reason=observed-until-timeout-clean-stop
```

Identity drops also matched the expected start-only contracts:

- service managers: `uid=1000`, `gid=1000`, groups `1000,3009`, no `CAP_NET_ADMIN`.
- Wi-Fi HAL: `uid=1010`, `gid=1010`, groups `1010,1021,3004,3005`, `CAP_NET_ADMIN` present for the HAL process.

## Stderr

No linker failure remains. The only stderr content was known non-fatal Android runtime/service-context noise:

```text
Multiple same specifications for vendor.qti.hardware.data.iwlan::IIWlan.
Multiple same specifications for com.qualcomm.qti.imscmservice::IImsCmService.
SELinux: Loaded service_contexts from:
    /system/etc/selinux/plat_hwservice_contexts
    /vendor/etc/selinux/vendor_hwservice_contexts
libc: Using old property service protocol ("ro.property_service.version" is not set)
```

## Postflight Safety

The postflight `ps` snapshot contains no `servicemanager`, `hwservicemanager`, or Wi-Fi HAL process.

The network surface still has no WLAN-like interface. The interface set before and after was:

```text
dummy0
ncm0
sit0
lo
ip6tnl0
bond0
ip_vti0
ip6_vti0
```

`ncm0` RX counters changed slightly during the run because the host control channel remained active. No `wlan*`, `swlan*`, `p2p*`, `wiphy*`, or `phy*` link appeared.

## Interpretation

V407 proves the bounded private-namespace process model can keep `servicemanager`, `hwservicemanager`, and Samsung's Wi-Fi HAL alive through the observe window after V406 fixed the `system_ext` VNDK dependency gap.

This is still not Wi-Fi bring-up. It proves only:

- private runtime namespace is sufficient for the first HAL candidate to start;
- service-manager pair and HAL can coexist in one bounded helper-owned namespace;
- cleanup is safe;
- scan/connect/link-up remains untouched.

## Next Target

Proceed to V408: Wi-Fi HAL registration and service-surface evidence.

V408 should collect evidence while the same bounded trio is alive, without scan/connect/link-up:

- `hwservicemanager`/HIDL registration surface, if query tooling is available;
- Binder/hwbinder FD and map evidence for the HAL child;
- child stderr/stdout hints around service registration;
- postflight process and Wi-Fi link cleanliness.

Wi-Fi bring-up remains blocked until HAL registration evidence is reviewed.

