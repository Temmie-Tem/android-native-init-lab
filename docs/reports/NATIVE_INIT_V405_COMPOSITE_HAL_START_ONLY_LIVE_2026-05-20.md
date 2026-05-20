# Native Init v405 Composite Wi-Fi HAL Start-Only Live Result

## Summary

The exact-approved V405 composite Wi-Fi HAL start-only smoke executed and stayed within the approved boundary.

The helper started `servicemanager`, `hwservicemanager`, and the first Wi-Fi HAL candidate in one helper-owned private namespace. It did not execute scan, connect, link-up, credentials, DHCP, routing, `wificond`, supplicant, hostapd, CNSS/diag lifecycle, firmware mutation, persistence, or Wi-Fi bring-up.

The run is a safety PASS but a runtime-gap classification: the Wi-Fi HAL process exited before the observe window because the linker could not find `android.hardware.wifi@1.0.so`. Cleanup was safe and no residual manager/HAL process or Wi-Fi link was observed.

## Approval Used

```text
approve v405 composite Wi-Fi HAL start-only smoke only; no scan/connect/link-up and no Wi-Fi bring-up
```

## Evidence

- pre-live read-only preflight: `tmp/wifi/v405-composite-hal-preflight-before-live-20260520-093943/`
- approved live smoke: `tmp/wifi/v405-composite-hal-start-only-live-20260520-094000/`
- live manifest: `tmp/wifi/v405-composite-hal-start-only-live-20260520-094000/manifest.json`
- native transcript: `tmp/wifi/v405-composite-hal-start-only-live-20260520-094000/native/run-composite-hal.txt`
- postflight process snapshot: `tmp/wifi/v405-composite-hal-start-only-live-20260520-094000/native/post-ps.txt`
- postflight network snapshot: `tmp/wifi/v405-composite-hal-start-only-live-20260520-094000/native/post-proc-net-dev.txt`
- read-only library locate evidence: `tmp/wifi/v405-wifi-hal-lib-locate-20260520-094105/`

Pre-live preflight:

```text
decision: composite-hal-start-only-preflight-ready
pass: True
reason: read-only preflight is ready; live run still needs approval
device_mutations: False
daemon_start_executed: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
```

Approved live result:

```text
decision: composite-hal-start-only-runtime-gap
pass: True
reason: composite HAL exited before observe window but cleanup is safe
device_mutations: True
daemon_start_executed: True
wifi_hal_start_executed: True
wifi_bringup_executed: False
```

## Start-Only Boundary

The helper printed the expected start-only guard:

```text
wifi_hal_composite_start.mode=guarded
wifi_hal_composite_start.target=/vendor/bin/hw/vendor.samsung.hardware.wifi@2.0-service
wifi_hal_composite_start.wifi_hal=1
wifi_hal_composite_start.scan_connect_linkup=0
wifi_hal_composite_start.wificond=0
wifi_hal_composite_start.supplicant=0
wifi_hal_composite_start.hostapd=0
wifi_hal_composite_start.cnss_diag=0
wifi_hal_composite_start.allowed=1
```

All three approved children were started:

```text
wifi_hal_composite_start.child.servicemanager.child_started=1
wifi_hal_composite_start.child.hwservicemanager.child_started=1
wifi_hal_composite_start.child.wifi_hal.child_started=1
wifi_hal_composite_start.child_started=3
```

The service-manager identities were dropped to `uid=1000 gid=1000 groups=1000,3009` with no remaining `CAP_NET_ADMIN`. The Wi-Fi HAL identity was dropped to `uid=1010 gid=1010 groups=1010,1021,3004,3005` with the requested start-only capabilities raised before exec.

## Runtime Gap

The runtime gap is a linker dependency gap, not a scan/connect failure:

```text
CANNOT LINK EXECUTABLE "/vendor/bin/hw/vendor.samsung.hardware.wifi@2.0-service": library "android.hardware.wifi@1.0.so" not found: needed by main executable
linker: CANNOT LINK EXECUTABLE "/vendor/bin/hw/vendor.samsung.hardware.wifi@2.0-service": library "android.hardware.wifi@1.0.so" not found: needed by main executable
```

Child outcome:

```text
wifi_hal_composite_start.child.servicemanager.observable=1
wifi_hal_composite_start.child.servicemanager.signal=15
wifi_hal_composite_start.child.servicemanager.reaped=1
wifi_hal_composite_start.child.hwservicemanager.observable=1
wifi_hal_composite_start.child.hwservicemanager.signal=15
wifi_hal_composite_start.child.hwservicemanager.reaped=1
wifi_hal_composite_start.child.wifi_hal.observable=0
wifi_hal_composite_start.child.wifi_hal.exit_code=1
wifi_hal_composite_start.child.wifi_hal.reaped=1
wifi_hal_composite_start.result=start-only-runtime-gap
wifi_hal_composite_start.reason=child-exited-before-observe-window
```

Read-only library locate shows the missing interface libraries exist under the `system_ext` VNDK v30 APEX:

```text
/mnt/system/system/system_ext/apex/com.android.vndk.v30/lib64/android.hardware.wifi@1.0.so
/mnt/system/system/system_ext/apex/com.android.vndk.v30/lib64/android.hardware.wifi@1.1.so
/mnt/system/system/system_ext/apex/com.android.vndk.v30/lib64/android.hardware.wifi@1.2.so
/mnt/system/system/system_ext/apex/com.android.vndk.v30/lib64/android.hardware.wifi@1.3.so
/mnt/system/system/system_ext/apex/com.android.vndk.v30/lib64/android.hardware.wifi@1.4.so
```

The current helper's private APEX bind farm is based on `/mnt/system/system/apex`. That tree has `com.android.vndk.current` but does not contain the Wi-Fi HIDL interface libraries. The Wi-Fi-specific VNDK v30 payload is under `/mnt/system/system/system_ext/apex/com.android.vndk.v30`, so the next helper needs a controlled way to materialize that APEX into the private namespace.

## Postflight Safety

The postflight `ps` snapshot contains no `servicemanager`, `hwservicemanager`, or Wi-Fi HAL process. The network snapshot stayed unchanged and no WLAN interface appeared.

Observed interface set before and after the smoke:

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

`ncm0` counters also stayed unchanged during the short start-only smoke:

```text
before ncm0: rx_bytes=725350 rx_packets=4938 tx_bytes=2896 tx_packets=28
after  ncm0: rx_bytes=725350 rx_packets=4938 tx_bytes=2896 tx_packets=28
```

## Interpretation

V405 proves the composite process model is no longer blocked at `servicemanager` or `hwservicemanager`: both managers are observable and cleanly reaped in the same helper-owned namespace as the Wi-Fi HAL child.

The remaining blocker is narrower: the helper's private APEX materialization is incomplete for Samsung's Wi-Fi HAL dependency closure. The generic VNDK alias used for earlier CNSS/linker work is not enough because the required Wi-Fi HIDL interface libraries live in `system_ext/apex/com.android.vndk.v30`.

## Next Target

Proceed to V406: system_ext VNDK APEX materialization for Wi-Fi HAL.

V406 should:

- add a non-global helper mode or option that can bind `/mnt/system/system/system_ext/apex/com.android.vndk.v30` as private `/apex/com.android.vndk.v30`;
- keep `/apex/com.android.runtime` and the rest of the existing bind-backed APEX farm behavior unchanged;
- prove linker dependency closure before any live HAL start-only retry;
- preserve the same approval boundary: no scan/connect/link-up and no Wi-Fi bring-up.

