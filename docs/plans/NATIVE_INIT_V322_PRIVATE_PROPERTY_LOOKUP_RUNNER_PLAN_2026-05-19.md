# v322 Plan: Private Property Lookup Runner Integration

- date: `2026-05-19`
- scope: fail-closed host runner integration for v321 helper mode
- boot image change: none planned
- baseline native build: `A90 Linux init 0.9.61 (v319)`
- status: implementation planned / live execution blocked until v317 PASS

## Summary

v321 added static support to `a90_android_execns_probe v11` for the safe
`property-lookup` mode. v322 wires that helper mode into
`scripts/revalidation/wifi_private_property_lookup_proof.py` while preserving the
existing fail-closed gates.

This is still not Wi-Fi bring-up. If v317 PASS evidence is absent, the runner
must return `private-property-lookup-blocked-v317-missing` and execute no device
commands.

## Key Changes

- Add bridge/helper arguments to `wifi_private_property_lookup_proof.py`:
  - `--bridge-host`, `--bridge-port`, `--bridge-timeout`;
  - `--helper-path`, default `/cache/bin/a90_android_execns_probe`;
  - `--helper-timeout-sec`, default `10`.
- Restrict selected lookup keys to the same v321 helper allowlist.
- Implement the future live path only after all existing gates pass:
  - v312 generated property layout PASS;
  - v317 live namespace proof PASS;
  - exact v320 approval phrase;
  - `--allow-device-mutation` and `--assume-yes`.
- Future live command shape:

```text
run /cache/bin/a90_android_execns_probe \
  --system-root /mnt/system/system \
  --vendor-block /dev/block/sda29 \
  --vendor-fstype ext4 \
  --target-profile system-getprop \
  --mode property-lookup \
  --null-device-mode dev-null \
  --property-root /mnt/sdext/a90/private-property-v317/dev/__properties__ \
  --property-key <allowlisted-key> \
  --timeout-sec 10
```

## Validation

Static and fail-closed validation:

```bash
python3 -m py_compile scripts/revalidation/wifi_private_property_lookup_proof.py
python3 scripts/revalidation/wifi_private_property_lookup_proof.py \
  --out-dir tmp/wifi/v322-private-property-lookup-runner-plan \
  plan
python3 scripts/revalidation/wifi_private_property_lookup_proof.py \
  --out-dir tmp/wifi/v322-private-property-lookup-runner-run-blocked \
  --approval-phrase "approve v320 private property lookup proof only; no daemon start and no Wi-Fi bring-up" \
  --allow-device-mutation \
  --assume-yes \
  run
git diff --check
```

Expected current result:

- `plan`: blocked if v317 PASS evidence is missing;
- `run`: `private-property-lookup-blocked-v317-missing`;
- `device_commands_executed=false`;
- `device_mutations=false`.

## Live Boundary

Live helper execution is out of scope until v317 PASS evidence exists. Even when
unblocked, live execution remains read-only property lookup only and still must
not start Android daemons or Wi-Fi.

## Acceptance

- Runner has the complete helper command path implemented.
- Current state remains fail-closed because v317 PASS is absent.
- No device command is executed during current validation.
- Evidence manifests make the future command list auditable.
