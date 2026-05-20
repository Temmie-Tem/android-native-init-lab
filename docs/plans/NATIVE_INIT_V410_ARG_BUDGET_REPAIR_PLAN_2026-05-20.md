# Native Init v410 Registration Query Arg-Budget Repair Plan

## Problem

V409 was prepared correctly at the service-boundary level, but the exact
approved V409 query command exceeded the native shell 30-argument budget when
all safety flags were present.

The V409 runner fallback kept the command below the limit by omitting:

```text
--data-wifi-mode private-empty
```

That is not acceptable for the live registration query gate because it weakens
the private `/data/vendor/wifi` boundary compared with V407.

## V410 Fix

V410 supersedes V409 before live deploy.

Helper v26 changes the default for:

```text
--mode wifi-hal-composite-lshal-list
```

When `--data-wifi-mode` is omitted, helper v26 sets:

```text
data_wifi_mode=private-empty
```

This keeps the approved live command at 29 arguments while preserving the
private Wi-Fi data boundary.

## Artifacts

- helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- helper artifact: `tmp/wifi/v410-a90_android_execns_probe-v26/a90_android_execns_probe`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v26_deploy_preflight.py`
- query runner: `scripts/revalidation/wifi_hal_registration_query_v410_runner.py`

Helper v26:

```text
version: a90_android_execns_probe v26
sha256: daf1b59e2475c0db28fb99eb83f8be02a46f695d8c4e435c47e68f45370a7caa
```

## Approval Gates

V410 replaces the V409 approval phrases.

Deploy approval:

```text
approve v410 deploy execns helper v26 only; no daemon start and no Wi-Fi bring-up
```

Registration query approval, only after deploy and post-deploy preflight:

```text
approve v410 bounded lshal registration query only; no scan/connect/link-up and no Wi-Fi bring-up
```

## Verification

V410 must prove before live deploy:

- helper v26 static ARM64 build PASS.
- helper strings include `a90_android_execns_probe v26`.
- helper strings include `wifi-hal-composite-lshal-list`.
- helper strings include `--allow-hal-service-query`.
- approved query plan command length is `<= 30`.
- approved query plan command includes `--allow-hal-service-query`.
- approved query plan records `helper_implicit_data_wifi_mode=private-empty`.
- no-approval deploy still refuses before mutation.
- read-only preflight still confirms `/mnt/system/system/bin/lshal`.

## Next Step

Run only the helper v26 deploy after the exact V410 deploy approval.  Do not run
the registration query until deploy and post-deploy preflight pass.
