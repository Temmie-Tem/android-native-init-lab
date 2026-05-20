# Native Init v406 System_ext VNDK Linker-List Live Result

## Summary

The exact-approved V406 system_ext VNDK APEX linker-list proof completed successfully.

This run did not start `servicemanager`, `hwservicemanager`, Wi-Fi HAL, `wificond`, supplicant, hostapd, CNSS/diag, scan/connect/link-up, or Wi-Fi bring-up. It only executed the helper in `linker-list` mode for `/vendor/bin/hw/vendor.samsung.hardware.wifi@2.0-service`.

V406 closes the V405 linker dependency gap: with helper v24 and `--vndk-apex-alias-mode v30-to-system-ext-v30`, the Wi-Fi HAL target resolves through the private `system_ext` VNDK v30 APEX and exits linker-list with child exit `0`, signal `0`, and no missing libraries.

## Approval Used

```text
approve v406 system_ext VNDK APEX linker-list proof only; no daemon start and no Wi-Fi bring-up
```

## Evidence

- approved linker-list run: `tmp/wifi/v406-system-ext-vndk-linker-list-live-20260520-100627/`
- manifest: `tmp/wifi/v406-system-ext-vndk-linker-list-live-20260520-100627/manifest.json`
- summary: `tmp/wifi/v406-system-ext-vndk-linker-list-live-20260520-100627/summary.md`
- native transcript: `tmp/wifi/v406-system-ext-vndk-linker-list-live-20260520-100627/native/run-system-ext-vndk-linker-list.txt`

Result:

```text
decision: system-ext-vndk-wifi-hal-linker-list-pass
pass: True
reason: Wi-Fi HAL linker-list dependency closure passed with system_ext VNDK v30
device_commands_executed: True
device_mutations: False
daemon_start_executed: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
```

Linker result:

```text
helper_status: namespace-ready
probe_run_rc: 0
child_exit_code: 0
child_signal: 0
timed_out: False
missing_libs: []
stdout_bytes: 2424
stderr_bytes: 0
```

## Private Namespace Proof

The helper ran in the expected mode:

```text
A90_EXECNS_BEGIN version="a90_android_execns_probe v24"
mode=linker-list
vndk_apex_alias_mode=v30-to-system-ext-v30
target_profile=vendor-wifi-hal-ext
target=/vendor/bin/hw/vendor.samsung.hardware.wifi@2.0-service
linker=/apex/com.android.runtime/bin/linker64
helper_status=namespace-ready
apex_mount_source=<private-bind-farm>
```

The previously missing Wi-Fi HIDL interface library is now visible in the private `/apex` namespace:

```text
context.apex_vndk_v30_wifi_1_0.path=/apex/com.android.vndk.v30/lib64/android.hardware.wifi@1.0.so
context.apex_vndk_v30_wifi_1_0.exists=1
context.apex_vndk_v30_wifi_1_0.size=1034472
context.apex_vndk_v30_wifi_1_0.hash=0x9969c125519d75f5
```

The source system_ext APEX is also visible through the private namespace:

```text
context.system_ext_apex_vndk_v30.path=/system/system_ext/apex/com.android.vndk.v30
context.system_ext_apex_vndk_v30.exists=1
```

The proof completed cleanly:

```text
probe_run_rc=0
child_exit_code=0
child_signal=0
timed_out=0
A90_EXECNS_END rc=0
```

## Interpretation

V405's blocker was not the Wi-Fi HAL binary itself and not the service-manager process model. It was the incomplete private APEX dependency closure: `android.hardware.wifi@1.0.so` lived in `system_ext/apex/com.android.vndk.v30`, while the earlier helper exposed only the generic `/mnt/system/system/apex` farm.

V406 proves helper v24 fixes that specific blocker. The next technically justified step is a bounded composite HAL start-only retry using helper v24's `v30-to-system-ext-v30` mode.

## Not Executed

- `servicemanager`, `hwservicemanager`, or Wi-Fi HAL daemon start.
- `wificond`, supplicant, hostapd.
- `cnss-daemon` or `cnss_diag`.
- scan/connect/link-up.
- credentials, DHCP, routing.
- rfkill, ICNSS bind/unbind, module load/unload, firmware mutation.
- Android partition writes.
- persistence or boot/autostart changes.

## Next Target

Proceed to V407: bounded composite Wi-Fi HAL start-only retry with helper v24 and `v30-to-system-ext-v30`.

V407 must still exclude scan/connect/link-up and Wi-Fi bring-up. It should only start the same bounded trio as V405:

- `servicemanager`
- `hwservicemanager`
- first Wi-Fi HAL candidate `vendor.wifi_hal_ext`

HAL start-only retry requires a new exact approval phrase and should not be inferred from the V406 linker-list approval.

