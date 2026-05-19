# v332 Plan: Current Read-only Live Preflight

- date: `2026-05-19`
- scope: read-only native device preflight before V317 live proof
- boot image change: none planned
- device mutation: none planned
- status: implementation planned

## Summary

V331 prepared the approval-gated V317 live command packet. Before asking the
operator to run a mutation step, v332 refreshes the current device state with
read-only commands only.

This confirms that the current native boot is still `A90 Linux init 0.9.61
(v319)`, SD storage is mounted/writable, selftest has no failure, netservice is
disabled, and the native log path is still on SD.

## Command

```bash
python3 scripts/revalidation/wifi_private_property_live_preflight.py \
  --out-dir tmp/wifi/v332-current-readonly-live-preflight \
  --expect-version "A90 Linux init 0.9.61 (v319)" \
  run
```

## Validation

- Expected decision: `private-property-live-preflight-ready`
- Expected pass: `true`
- Expected device mutation: `false`
- Commands are limited to:
  - `version`
  - `status`
  - `selftest`
  - `storage`
  - `mountsd status`
  - `logpath`

## Acceptance

- Read-only live preflight passes on current clean git head.
- No `run`, write, mount, push, reboot, daemon start, Wi-Fi scan/connect/link-up,
  rfkill, module load/unload, firmware mutation, or partition write is executed.
- V317 exact approval phrase is still required before any mutation step.
