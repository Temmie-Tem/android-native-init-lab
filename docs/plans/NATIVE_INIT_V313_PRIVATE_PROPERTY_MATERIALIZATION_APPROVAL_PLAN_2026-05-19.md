# v313 Plan: Private Property Materialization Approval Packet

- date: `2026-05-19`
- scope: host-only approval packet for future private property materialization
- boot image change: none
- restored device build: `A90 Linux init 0.9.60 (v261)`
- status: planned

## Summary

v312 produced a valid host-only private property runtime layout. Any next step
that copies or exposes those files on the device is a live mutation boundary.

v313 therefore creates an approval packet instead of implementing live
materialization.

## Key Changes

- Add `scripts/revalidation/wifi_private_property_materialization_approval.py`.
- Consume v312 layout manifest.
- Record the exact allowed future scope.
- Record actions explicitly not approved.
- Emit the required operator approval phrase for v314.

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_private_property_materialization_approval.py
python3 scripts/revalidation/wifi_private_property_materialization_approval.py \
  --out-dir tmp/wifi/v313-private-property-materialization-approval \
  run
git diff --check
```

Expected result:

```text
private-property-materialization-approval-ready
```

## Required Approval Phrase

```text
approve v314 private property namespace materialization only; no daemon start and no Wi-Fi bring-up
```

## Acceptance

- No device command and no ADB command.
- No generated file installation.
- No bind mount or namespace manipulation.
- v314 cannot proceed without explicit operator approval.

