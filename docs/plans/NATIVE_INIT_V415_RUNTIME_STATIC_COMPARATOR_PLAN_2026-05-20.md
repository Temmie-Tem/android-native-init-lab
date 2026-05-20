# Native Init v415 Runtime Static Comparator Plan

## Scope

V415 compares V411 runtime binderized registration evidence against the V414
ranked static Wi-Fi target set.

V415 is host-only.  It reads existing evidence and must not execute bridge or
device commands, deploy helpers, start service-manager, start Wi-Fi HALs,
scan/connect/link-up, or perform Wi-Fi bring-up.

## Inputs

- V411 binderized registration query manifest.
- V414 static/runtime target classifier manifest.

Current default V411 input is the read-only preflight result, so the expected
current output is still `waiting-for-v411-deploy`.

## Implementation

Add:

```text
scripts/revalidation/wifi_v415_runtime_static_comparator.py
```

The comparator extracts HIDL fqinstances from V411 live output when available,
then compares them against V414 primary and secondary runtime match patterns.

## Decisions

```text
v415-runtime-static-comparator-waiting-for-v411-deploy
```

V411 is blocked before runtime query.  Next action remains exact-approved helper
v27 deploy.

```text
v415-runtime-static-comparator-waiting-for-v411-live-query
```

V411 post-deploy preflight is ready, but runtime query is absent.

```text
v415-runtime-static-primary-match
```

V411 runtime registrations match the V414 primary Samsung Wi-Fi target.  Next
step is a no-scan/no-link HIDL client proof plan.

```text
v415-runtime-static-secondary-match
```

V411 runtime registrations match a secondary Wi-Fi target but not the primary.

```text
v415-runtime-static-no-match
```

V411 runtime registrations do not match the ranked static target set.

```text
v415-runtime-static-comparator-micro-query-needed
```

V411 runtime query timed out, failed, or lacked the tool.  Use V414 target
patterns for a narrower micro `hwservicemanager` query.

## Success Criteria

- Executes no device command.
- Evidence output is private.
- Current blocked V411 evidence routes to waiting-for-deploy.
- Primary V414 runtime match set is preserved in output.
- Queue keeps V411 helper v27 deploy as the next live gate.
