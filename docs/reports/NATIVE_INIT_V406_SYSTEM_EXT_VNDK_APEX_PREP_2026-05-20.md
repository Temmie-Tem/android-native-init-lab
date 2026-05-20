# Native Init v406 System_ext VNDK APEX Prep Report

## Summary

V406 preparation is implemented and fail-closed.

Helper v24 adds a private `system_ext` VNDK v30 APEX materialization mode for the V405 Wi-Fi HAL linker gap. The runner is limited to a future `linker-list` proof and does not start daemons or Wi-Fi. The device still has helper v23, so the next live mutation is helper v24 deploy only and requires a separate exact approval phrase.

## Evidence

- helper artifact: `tmp/wifi/v406-a90_android_execns_probe-v24/a90_android_execns_probe`
- runner plan: `tmp/wifi/v406-system-ext-vndk-runner-plan-20260520-094844/`
- runner preflight: `tmp/wifi/v406-system-ext-vndk-runner-preflight-fixed3-20260520-095025/`
- deploy preflight: `tmp/wifi/v406-helper-v24-deploy-preflight-20260520-095042/`
- deploy no-approval: `tmp/wifi/v406-helper-v24-deploy-noapproval-20260520-095050/`
- runner no-approval: `tmp/wifi/v406-system-ext-vndk-runner-noapproval-20260520-095105/`

## Helper Build

Static ARM64 build passed:

```text
artifact: tmp/wifi/v406-a90_android_execns_probe-v24/a90_android_execns_probe
file: ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped
sha256: 7ec11d95085f1c3dc370884725b080b44150bf8b0a5f7d897df048188a815063
dynamic section: There is no dynamic section in this file.
```

Required strings are present:

```text
a90_android_execns_probe v24
v30-to-system-ext-v30
apex_vndk_v30_wifi_1_0
system_ext_apex_vndk_v30
```

## Runner Preflight

The V406 runner preflight is ready but correctly reports that helper v24 must be deployed first:

```text
decision: system-ext-vndk-linker-list-preflight-ready-needs-deploy
pass: True
reason: preflight complete; helper v24 deploy still requires exact approval
device_commands_executed: True
device_mutations: False
daemon_start_executed: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
helper-v24: needs-deploy
```

The preflight confirms:

- V405 runtime gap is the current input.
- native version and health are clean.
- real linkerconfig inputs are visible.
- `/mnt/system/system/system_ext/apex/com.android.vndk.v30` is present.
- `/mnt/system/system/system_ext/apex/com.android.vndk.v30/lib64/android.hardware.wifi@1.0.so` is present.
- process surface and Wi-Fi link surface are clean.

## Deploy Gate

Deploy preflight:

```text
decision: execns-helper-v24-deploy-preflight-ready-needs-deploy
pass: True
reason: preflight complete; helper v24 deploy still requires exact approval
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

Deploy no-approval:

```text
decision: execns-helper-v24-deploy-approval-required
pass: True
reason: exact approval phrase required; no mutation executed
device_mutations: False
daemon_start_executed: False
wifi_bringup_executed: False
```

## Linker-List Gate

Runner no-approval:

```text
decision: system-ext-vndk-linker-list-approval-required
pass: True
reason: exact approval phrase required; no device command executed
device_commands_executed: False
device_mutations: False
daemon_start_executed: False
wifi_hal_start_executed: False
wifi_bringup_executed: False
```

The planned linker-list command has 26 native shell arguments, below the current 30-argument guard.

## Safety Boundary

Not executed:

- helper v24 deploy;
- `linker-list` proof run;
- `servicemanager`, `hwservicemanager`, or Wi-Fi HAL daemon start;
- `wificond`, supplicant, hostapd, CNSS/diag;
- scan/connect/link-up;
- credentials, DHCP, routing;
- rfkill, ICNSS bind/unbind, module load/unload, firmware mutation;
- Android partition writes, persistence, or boot/autostart changes.

## Next Target

The next live step is exact-approved helper v24 deploy only:

```text
approve v406 deploy execns helper v24 only; no daemon start and no Wi-Fi bring-up
```

After deploy and postflight preflight pass, the next separate approval is linker-list proof only:

```text
approve v406 system_ext VNDK APEX linker-list proof only; no daemon start and no Wi-Fi bring-up
```

HAL start-only retry remains blocked until the linker-list proof is reviewed.

