# v322 Report: Private Property Lookup Runner Integration

- date: `2026-05-19`
- scope: fail-closed host runner integration for v321 helper mode
- boot image change: none
- baseline native build: `A90 Linux init 0.9.61 (v319)`
- result: `private-property-lookup-runner-integrated-blocked-v317`

## Summary

v322 updates `scripts/revalidation/wifi_private_property_lookup_proof.py` so the
future live `run` path can call `a90_android_execns_probe v11` in
`property-lookup` mode. The runner still refuses current live execution because
v317 has not recorded `private-property-namespace-proof-pass`.

No device command was executed during v322 validation.

## Implementation

New runner options:

```text
--bridge-host 127.0.0.1
--bridge-port 54321
--bridge-timeout 90
--helper-path /cache/bin/a90_android_execns_probe
--helper-timeout-sec 10
```

Future helper command shape:

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

The selected lookup keys are now filtered to the same v321 helper allowlist.
The current v312 manifest selects 4 planned helper commands.

## Validation

Static:

```bash
python3 -m py_compile scripts/revalidation/wifi_private_property_lookup_proof.py
git diff --check
```

Fail-closed plan check:

```bash
python3 scripts/revalidation/wifi_private_property_lookup_proof.py \
  --out-dir tmp/wifi/v322-private-property-lookup-runner-plan \
  plan
```

Result:

```text
decision: private-property-lookup-blocked-v317-missing
pass: False
device_commands_executed: False
device_mutations: False
planned_commands: 4
helper_results: 0
```

Fail-closed run check with approval phrase and mutation flags:

```bash
python3 scripts/revalidation/wifi_private_property_lookup_proof.py \
  --out-dir tmp/wifi/v322-private-property-lookup-runner-run-blocked \
  --approval-phrase "approve v320 private property lookup proof only; no daemon start and no Wi-Fi bring-up" \
  --allow-device-mutation \
  --assume-yes \
  run
```

Result:

```text
decision: private-property-lookup-blocked-v317-missing
pass: False
device_commands_executed: False
device_mutations: False
planned_commands: 4
helper_results: 0
```

## Live Validation

Not executed. The runner correctly stopped before opening the bridge because the
v317 live proof gate is still missing.

## Safety Result

- no boot partition write;
- no device flash;
- no bridge command execution;
- no global `/dev/__properties__` bind;
- no property mutation;
- no daemon start or Wi-Fi bring-up.

## Next Step

The current technical path is ready up to the approval gate. The next Wi-Fi step
is either:

1. run v317 minimal private property namespace proof after the exact v317
   approval phrase, or
2. pause live property work and continue with another read-only Wi-Fi/kernel
   inventory task that does not require private property namespace mutation.
