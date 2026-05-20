# Native Init v411 Binderized lshal Query Plan

## Scope

V411 narrows the V410 registration query timeout.  V410 proved the composite
service-manager + Wi-Fi HAL namespace is stable, but default `/system/bin/lshal`
timed out.  V411 changes only the query child to ask for binderized services:

```text
/system/bin/lshal list --types=binderized --neat
```

This is still not Wi-Fi bring-up.  It does not approve scan/connect/link-up,
credentials, DHCP, routing, rfkill writes, firmware mutation, persistent Wi-Fi
state, or Android partition writes.

## Rationale

AOSP documents `lshal` as the device-side HAL listing tool.  The AOSP source also
shows default list types include binderized services, passthrough clients, and
passthrough libraries (`bcl`).  V411 avoids that broader default path and limits
the question to `hwservicemanager` binderized registrations.

References:

- <https://source.android.com/docs/core/architecture/vintf/resources>
- <https://android.googlesource.com/platform/frameworks/native/+/013be5f/cmds/lshal/ListCommand.cpp>

## Implementation

V411 adds helper v27:

```text
version: a90_android_execns_probe v27
mode: wifi-hal-composite-lshal-binderized-list
query child: /system/bin/lshal list --types=binderized --neat
default data_wifi_mode: private-empty
```

Host gates:

```text
scripts/revalidation/wifi_execns_helper_v27_deploy_preflight.py
scripts/revalidation/wifi_hal_binderized_registration_query_v411_runner.py
```

## Approval Gates

Deploy gate:

```text
approve v411 deploy execns helper v27 only; no daemon start and no Wi-Fi bring-up
```

Live query gate, only after deploy and post-deploy preflight:

```text
approve v411 bounded binderized lshal registration query only; no scan/connect/link-up and no Wi-Fi bring-up
```

## Success Criteria

V411 prep is ready when:

- helper v27 builds as a static ARM64 binary;
- helper strings include `wifi-hal-composite-lshal-binderized-list`, `--types=binderized`, `--neat`, and `--allow-hal-service-query`;
- approved query plan remains within the native 30-argument limit;
- query run without exact approval executes no device command;
- deploy run without exact approval executes no mutation;
- read-only preflight blocks only on remote helper v27 before deploy;
- all evidence confirms no Wi-Fi bring-up boundary is crossed.
