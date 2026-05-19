# v317 Plan: Minimal Private Property Namespace Proof

- date: `2026-05-19`
- scope: approved minimal private property namespace proof
- boot image change: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- status: runner ready / live execution blocked until operator approval

## Summary

v316 emitted the approval packet for the first live private-property proof. v317
is the first step that may mutate device state, so it must stay deliberately
small.

The goal is not to start Android services or Wi-Fi. The goal is only to prove
that generated property runtime files can be copied to a versioned private
workspace on SD storage, verified by SHA-256, and removed cleanly.

## Required Approval Phrase

```text
approve v317 minimal private property namespace proof only; no daemon start and no Wi-Fi bring-up
```

Without that exact phrase, the v317 runner must refuse live execution.

## Intended Tool

Add `scripts/revalidation/wifi_private_property_namespace_proof.py`.

Required subcommands:

- `plan`: inspect v312/v315/v316 manifests and write the planned operation list.
- `run`: require all approval gates; execute the bounded proof only after the
  exact approval phrase.
- `cleanup`: remove only the versioned private workdir created by v317.

## Inputs

- `tmp/wifi/v312-private-property-runtime-layout/manifest.json`
- `tmp/wifi/v315-private-property-live-preflight/manifest.json`
- `tmp/wifi/v316-private-property-live-approval/manifest.json`
- local v312 layout files under
  `tmp/wifi/v312-private-property-runtime-layout/layout/dev/__properties__/`

## Live Operation Boundary

Allowed after approval:

1. Verify native version/status/selftest/storage/mountsd/logpath again.
2. Create `/mnt/sdext/a90/private-property-v317`.
3. Create `/mnt/sdext/a90/private-property-v317/dev/__properties__`.
4. Copy only v312 generated property layout files into that private path.
5. Verify each copied file SHA-256 with device `toybox sha256sum`.
6. Write a private manifest under the v317 workdir.
7. Remove the v317 workdir during cleanup.

Explicitly forbidden:

- Global `/dev/__properties__` replacement.
- Global bind mount over `/dev/__properties__`.
- Global `/dev/socket/property_service` creation.
- Property mutation or `setprop`-like writes.
- service-manager, hwservicemanager, Wi-Fi HAL, `wificond`, `supplicant`,
  `hostapd`, CNSS, or diag daemon start.
- Wi-Fi scan/connect/link-up/credential/DHCP/routing.
- NCM/tcpctl start for transfer. v316 says no daemon start; therefore v317 must
  use the existing ACM bridge only.

## Transfer Strategy

Use the existing ACM bridge and toybox only.

Preferred implementation:

1. For each file, base64 encode locally.
2. Split base64 into bounded chunks.
3. Append chunks to a temporary `.b64` file in the v317 private workdir through
   `cmdv1x run /cache/bin/toybox sh -c 'printf ... >> file.b64'`.
4. Decode with `toybox base64 -d file.b64 > file.tmp`.
5. Verify SHA-256 of `file.tmp`.
6. Atomically move `file.tmp` to final path.
7. Remove `.b64` temporary file.

If device toybox lacks `base64 -d` or shell redirection support, v317 must stop
with a diagnostic decision instead of widening scope to NCM/tcpctl.

## Safety Details

- Workdir must be fixed to `/mnt/sdext/a90/private-property-v317`.
- Runner must reject any path containing `..`, NUL, or an absolute path outside
  the fixed workdir.
- Runner must never follow host output symlinks; use existing private evidence
  helpers.
- Runner must record every command and copied file hash.
- Runner must treat partial upload or SHA mismatch as failure and attempt
  best-effort cleanup.
- Cleanup must remove only `/mnt/sdext/a90/private-property-v317`.

## Validation

Static:

```bash
python3 -m py_compile scripts/revalidation/wifi_private_property_namespace_proof.py
git diff --check
```

Refusal:

```bash
python3 scripts/revalidation/wifi_private_property_namespace_proof.py \
  --out-dir tmp/wifi/v317-private-property-namespace-proof-refuse \
  run || true
```

Expected decision:

```text
private-property-namespace-proof-approval-required
```

Plan-only runner validation:

```bash
python3 scripts/revalidation/wifi_private_property_namespace_proof.py \
  --out-dir tmp/wifi/v317-private-property-namespace-proof-plan \
  plan
```

Expected decision:

```text
private-property-namespace-proof-plan-ready
```

Approved live proof:

```bash
python3 scripts/revalidation/wifi_private_property_namespace_proof.py \
  --out-dir tmp/wifi/v317-private-property-namespace-proof \
  --approval-phrase "approve v317 minimal private property namespace proof only; no daemon start and no Wi-Fi bring-up" \
  --allow-device-mutation \
  --assume-yes \
  run
```

Expected decision:

```text
private-property-namespace-proof-pass
```

Cleanup:

```bash
python3 scripts/revalidation/wifi_private_property_namespace_proof.py \
  --out-dir tmp/wifi/v317-private-property-namespace-proof-cleanup \
  --approval-phrase "approve v317 minimal private property namespace proof only; no daemon start and no Wi-Fi bring-up" \
  --allow-device-mutation \
  --assume-yes \
  cleanup
```

Expected decision:

```text
private-property-namespace-proof-cleaned
```

## Acceptance

- Approval refusal works.
- Approved run copies files only under `/mnt/sdext/a90/private-property-v317`.
- Device SHA-256 matches v312 manifest for every copied file.
- Cleanup removes the v317 workdir.
- Native shell remains responsive after run and cleanup.
- `status` still reports `netservice: disabled`.
- No daemon or Wi-Fi bring-up action occurs.

## Next Step

If v317 passes, v318 can decide whether to attempt a private mount namespace
lookup proof. That still must not replace global `/dev/__properties__` or start
Android/Wi-Fi daemons.
