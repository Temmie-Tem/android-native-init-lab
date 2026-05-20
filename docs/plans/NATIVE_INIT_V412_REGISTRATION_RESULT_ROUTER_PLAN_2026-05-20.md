# Native Init v412 Registration Result Router Plan

## Scope

V412 does not replace the V411 deploy/query gate.  It prepares the branch after
V411 by reading V411 evidence and selecting the next safe Wi-Fi step.

This is host-only.  It must not deploy helpers, start service-manager,
start the Wi-Fi HAL, scan/connect/link-up, write credentials, run DHCP, mutate
firmware, or write Android partitions.

## Context

V410 proved the composite service-manager + Wi-Fi HAL namespace can be started
and cleaned, but broad `lshal` timed out.  V411 narrowed that query to:

```text
/system/bin/lshal list --types=binderized --neat
```

AOSP HAL documentation states binderized HALs run as separate processes and are
registered with a service manager.  AOSP `lshal` source shows `--types` accepts
`binderized` and `--neat` is the machine-parsable output mode.  That makes V411
the correct narrow registration query before any wider Wi-Fi daemon work.

References:

- <https://source.android.com/docs/core/architecture/hal>
- <https://android.googlesource.com/platform/frameworks/native/+/013be5f/cmds/lshal/ListCommand.cpp>

## Implementation

Add a host-only router:

```text
scripts/revalidation/wifi_v412_registration_result_router.py
```

Inputs:

- V411 manifest path.
- Optional V411 live output referenced by `live_result.file`.

Outputs:

- private `manifest.json`
- private `summary.md`
- decision label describing the next branch

## Branches

```text
v412-registration-router-waiting-for-v411-deploy
```

V411 is still blocked by remote helper v27.  Next action remains exact-approved
V411 helper deploy only.

```text
v412-registration-router-waiting-for-v411-live-query
```

V411 post-deploy preflight is ready, but the bounded live query has not run.
Next action is exact-approved V411 binderized query.

```text
v412-registration-router-wifi-service-candidates-ready
```

V411 query passed and Wi-Fi-looking binderized service names were parsed.  Next
action is a targeted no-scan/no-link Wi-Fi HAL client proof using the captured
service name.

```text
v412-registration-router-no-wifi-service
```

V411 query passed but no Wi-Fi service was parsed.  Next action is manifest and
Android-side cross-check before attempting daemon bring-up.

```text
v412-registration-router-micro-query-needed
```

V411 runtime still failed or timed out.  Next action is a smaller targeted
hwservicemanager/HIDL query instead of broadening `lshal`.

```text
v412-registration-router-tool-missing
```

`/system/bin/lshal` is unavailable.  Next action is Android-side extraction or a
small native registration client.

## Success Criteria

- The router executes no device command.
- Evidence output remains private.
- The current V411 blocked preflight routes to `waiting-for-v411-deploy`.
- Decision labels preserve the no-Wi-Fi-bring-up boundary.
- The task queue records that V412 is prepared but does not supersede the V411
  deploy gate.
