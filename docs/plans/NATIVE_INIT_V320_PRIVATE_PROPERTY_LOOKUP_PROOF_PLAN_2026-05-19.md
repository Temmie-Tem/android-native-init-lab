# v320 Plan: Private Property Lookup Proof

- date: `2026-05-19`
- scope: conditional read-only Android property lookup proof in a private namespace
- boot image change: none planned
- baseline native build: `A90 Linux init 0.9.61 (v319)`
- status: fail-closed host runner implemented / blocked until v317 live proof passes

## Summary

v319 added a bounded serial `appendfile` primitive so the v317 private property
namespace proof can copy generated property runtime files without `toybox sh`,
NCM/tcpctl, or daemon start.

v320 is the next step after v317 passes. Its goal is to prove that an
Android-linked read-only property reader can resolve selected properties from the
private `/dev/__properties__` tree created under the v317 workspace. This is
still not Wi-Fi bring-up. It must not start Android service-manager, HAL,
`wificond`, `supplicant`, CNSS, or any Wi-Fi daemon.

## Preconditions

Required before implementation or live execution:

- v317 approved live proof decision: `private-property-namespace-proof-pass`.
- v317 cleanup decision: `private-property-namespace-proof-cleaned`, or an
  explicit new run workspace with verified stale-state cleanup.
- v319 device build available on the phone: `A90 Linux init 0.9.61 (v319)`.
- v312 generated property layout manifest available:
  `tmp/wifi/v312-private-property-runtime-layout/manifest.json`.
- ACM bridge remains the control channel. NCM/tcpctl is not required for this
  proof.

If v317 is still waiting for the exact approval phrase, v320 remains a planning
artifact only.

## Technical Basis

Primary references:

- AOSP `getprop` uses `android::base::GetProperty` and the bionic system
  property APIs to print a requested property:
  <https://android.googlesource.com/platform/system/core/+/master/toolbox/getprop.cpp>
- Bionic `SystemProperties::Init()` treats a property directory as the source of
  serialized/split property contexts, and `Find()` resolves a property through
  the matching context area:
  <https://android.googlesource.com/platform/bionic/+/master/libc/system_properties/system_properties.cpp>

The preferred proof is therefore not a custom GNU static helper pretending to be
bionic. The preferred proof is to run an Android-linked reader such as
`/system/bin/getprop` inside the already-tested private Android execution
namespace, with only that child process seeing the private property tree.

## Key Changes

### Host Tool

Add `scripts/revalidation/wifi_private_property_lookup_proof.py`.

Subcommands:

- `plan`: validate prerequisite manifests and describe the exact operation.
- `run`: require v317 PASS evidence and operator approval for device mutation if
  a new private workdir is created.
- `cleanup`: remove only this proof's private temporary workspace.

The tool must use private evidence helpers and must not write host outputs
through symlinks.

### Device Helper Strategy

Preferred implementation extends `stage3/linux_init/helpers/a90_android_execns_probe.c`
with a new safe mode:

```text
--mode property-lookup
```

Allowed target profiles:

- `system-getprop`: `/system/bin/getprop`
- optional later profile: `/system/bin/toybox getprop` only if the device proves
  that command exists and uses Android property APIs.

The helper should:

1. Create a private mount namespace.
2. Build the same private Android runtime layout used by the existing linker
   probes: `/system`, `/vendor`, `/apex`, `/linkerconfig`, private `/dev/null`,
   and required `/proc` visibility.
3. Bind only the v317 private property directory into the child namespace as
   `/dev/__properties__`.
4. Execute only read-only getprop queries for allowlisted property names.
5. Capture stdout/stderr/exit status and return a structured result to the host.
6. Exit, relying on private namespace teardown for mounts; no global bind mount
   is allowed.

### Allowlisted Property Keys

Initial lookup keys should come from v312/v311 seed evidence and stay small:

- `ro.build.version.sdk`
- `ro.build.version.release`
- `ro.product.vendor.device`
- `ro.board.platform`
- selected CNSS/Wi-Fi-relevant read-only keys only if present in the v312
  manifest.

The proof must compare output with the values in the generated v312 property
layout, not with live Android global state.

## Explicitly Forbidden

- Global `/dev/__properties__` replacement.
- Bind mount over global `/dev/__properties__`.
- `/dev/socket/property_service` creation.
- Property mutation or `setprop`-like write path.
- service-manager, hwservicemanager, Wi-Fi HAL, `wificond`, `supplicant`,
  `hostapd`, CNSS, or diag daemon start.
- Wi-Fi scan/connect/link-up/credential/DHCP/routing.
- rfkill write, module load/unload, firmware mutation, or partition write.
- Public network listener creation.

## Decisions

Expected decisions:

- `private-property-lookup-blocked-v317-missing`: v317 live PASS evidence is
  absent.
- `private-property-lookup-plan-ready`: plan-only validation passed.
- `private-property-lookup-helper-blocked`: helper cannot support private
  property bind safely.
- `private-property-lookup-getprop-pass`: read-only `getprop` sees expected
  private values.
- `private-property-lookup-getprop-empty`: getprop runs but does not see the
  private property area.
- `private-property-lookup-manual-review-required`: execution completed but
  output is ambiguous.

## Validation Plan

Static:

```bash
python3 -m py_compile scripts/revalidation/wifi_private_property_lookup_proof.py
bash scripts/revalidation/build_android_execns_probe_helper.sh /tmp/a90_android_execns_probe_v320
python3 scripts/revalidation/wifi_private_property_lookup_proof.py \
  --out-dir tmp/wifi/v320-private-property-lookup-proof-plan \
  plan
git diff --check
```

Live, only after v317 PASS:

```bash
python3 scripts/revalidation/wifi_private_property_lookup_proof.py \
  --out-dir tmp/wifi/v320-private-property-lookup-proof-live \
  --approval-phrase "approve v320 private property lookup proof only; no daemon start and no Wi-Fi bring-up" \
  --allow-device-mutation \
  --assume-yes \
  run
```

Expected live result:

```text
private-property-lookup-getprop-pass
```

Post-run checks:

```bash
python3 scripts/revalidation/a90ctl.py --json version
python3 scripts/revalidation/a90ctl.py --json status
python3 scripts/revalidation/a90ctl.py --json 'netservice status'
```

Expected post-run state:

- native shell responsive;
- `netservice` unchanged;
- no Android/Wi-Fi daemon was started;
- no global property runtime path was modified.

## Acceptance

- v320 refuses live execution without v317 PASS evidence.
- v320 refuses live execution without the exact v320 approval phrase.
- The property lookup target is allowlisted and read-only.
- The private property directory is visible only inside the child/private
  namespace.
- At least one known seed property resolves to the expected v312 value.
- Cleanup removes only v320 temporary files.
- No daemon start or Wi-Fi bring-up occurs.

## Next Step

If v320 proves private read-only property lookup, the next candidate is a
bounded CNSS pre-start environment probe that reuses the private property view
but still stops before daemon execution. If v320 fails because Android `getprop`
does not consume the private tree, return to the property shim design and avoid
service start attempts.
