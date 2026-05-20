# Native Init v406 System_ext VNDK APEX Plan

## Objective

Close the V405 Wi-Fi HAL linker runtime gap without widening into Wi-Fi bring-up.

V405 proved the composite process model is viable, but `/vendor/bin/hw/vendor.samsung.hardware.wifi@2.0-service` exited before the observe window because `android.hardware.wifi@1.0.so` was not visible in the helper private linker namespace. Read-only locate evidence shows the missing Wi-Fi HIDL interface libraries live under `/mnt/system/system/system_ext/apex/com.android.vndk.v30`.

## Scope

V406 is limited to private namespace materialization and linker-list proof:

- add helper v24 support for `--vndk-apex-alias-mode v30-to-system-ext-v30`;
- bind-backed private `/apex` behavior remains non-global and helper-owned;
- prove the Wi-Fi HAL dependency closure with `linker-list` before any HAL start-only retry;
- keep helper deploy and linker-list proof behind separate exact approval phrases.

## Explicit Non-Goals

- no `servicemanager`, `hwservicemanager`, or Wi-Fi HAL daemon start in V406 linker-list proof;
- no `wificond`, supplicant, hostapd, CNSS/diag lifecycle;
- no scan/connect/link-up;
- no credentials, DHCP, routing, default route, or network exposure widening;
- no rfkill write, ICNSS bind/unbind, module load/unload, firmware mutation;
- no Android partition write, persistence, or boot/autostart change.

## Design

Helper v24 extends the existing `vndk_apex_alias_mode` allowlist:

```text
none
v30-to-current
v30-to-system-ext-v30
```

The new mode keeps the existing bind-backed private APEX farm from `/mnt/system/system/apex`, then materializes:

```text
/mnt/system/system/system_ext/apex/com.android.vndk.v30
  -> private /apex/com.android.vndk.v30
```

This targets the exact V405 blocker while preserving the earlier runtime APEX behavior for `/apex/com.android.runtime` and other existing APEX entries.

## New Artifacts

- helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- helper artifact: `tmp/wifi/v406-a90_android_execns_probe-v24/a90_android_execns_probe`
- runner: `scripts/revalidation/wifi_system_ext_vndk_apex_v406_runner.py`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v24_deploy_preflight.py`

Expected helper SHA:

```text
7ec11d95085f1c3dc370884725b080b44150bf8b0a5f7d897df048188a815063
```

## Gate Sequence

1. Build helper v24 locally and verify it is static.
2. Run V406 runner `plan` and `preflight`.
3. Run V406 helper deploy wrapper `preflight`.
4. Confirm deploy `run` without approval is fail-closed.
5. Confirm linker-list runner `run` without approval is fail-closed.
6. Commit V406 preparation.
7. Only after operator approval, deploy helper v24.
8. Only after deploy postflight, run V406 linker-list proof.
9. If linker-list passes, plan a later bounded HAL start-only retry. That later retry is not V406.

## Required Future Approval Phrases

Helper deploy only:

```text
approve v406 deploy execns helper v24 only; no daemon start and no Wi-Fi bring-up
```

Linker-list proof only:

```text
approve v406 system_ext VNDK APEX linker-list proof only; no daemon start and no Wi-Fi bring-up
```

## Success Criteria

V406 preparation is ready when:

- helper v24 builds as a static ARM64 binary;
- helper strings include `a90_android_execns_probe v24`, `v30-to-system-ext-v30`, and `apex_vndk_v30_wifi_1_0`;
- runner preflight reports `system-ext-vndk-linker-list-preflight-ready-needs-deploy` while the device still has helper v23;
- deploy wrapper preflight reports `execns-helper-v24-deploy-preflight-ready-needs-deploy`;
- deploy no-approval reports `execns-helper-v24-deploy-approval-required`;
- linker-list no-approval reports `system-ext-vndk-linker-list-approval-required`;
- all no-approval paths report no daemon start, no Wi-Fi HAL start, and no Wi-Fi bring-up.

