# v320 Private Property Lookup Proof Report

- date: `2026-05-19`
- scope: fail-closed host runner for conditional private property lookup proof
- boot image change: none
- baseline native build: `A90 Linux init 0.9.61 (v319)`
- plan: `docs/plans/NATIVE_INIT_V320_PRIVATE_PROPERTY_LOOKUP_PROOF_PLAN_2026-05-19.md`
- tool: `scripts/revalidation/wifi_private_property_lookup_proof.py`

## Summary

Result: PASS for the bounded live proof.

v320 adds a host-side runner skeleton for the next private property lookup proof.
Before V317 live proof, the runner correctly refused `plan`/`run` as
`private-property-lookup-blocked-v317-missing`. After the approved V317 live
proof passed, the runner produced a V320 plan. After the separate V320 exact
approval phrase was provided, the live lookup ran inside the private property
namespace and all four allowlisted properties matched the v312 seed values.

Operational notes from live execution:

- first live attempt used stale device helper `a90_android_execns_probe v10` and
  failed because `--property-root`/`--property-key` were unsupported;
- v11 helper was deployed over serial `appendfile`/`uudecode`, not NCM/netcat,
  to avoid creating a transfer listener outside the V320 approval boundary;
- second live attempt with v11 failed until `/mnt/system` was mounted read-only;
- final live attempt with v11 plus `mountsystem ro` passed.

## Evidence

| item | path | result |
| --- | --- | --- |
| plan/refusal | `tmp/wifi/v320-private-property-lookup-proof-plan/` | `private-property-lookup-blocked-v317-missing` |
| run/refusal | `tmp/wifi/v320-private-property-lookup-proof-refuse/` | `private-property-lookup-blocked-v317-missing` |
| cleanup/no-op | `tmp/wifi/v320-private-property-lookup-proof-cleanup/` | `private-property-lookup-cleanup-not-needed` |
| plan after V317 | `tmp/wifi/v320-private-property-lookup-proof-plan-after-v317/` | `private-property-lookup-plan-ready` |
| v11 helper serial deploy | `tmp/wifi/v320-helper-v11-serial-deploy/` | `execns-helper-v11-serial-deploy-pass` |
| live stale helper failure | `tmp/wifi/v320-private-property-lookup-proof-live/` | `private-property-lookup-getprop-mismatch` |
| live unmounted system failure | `tmp/wifi/v320-private-property-lookup-proof-live-v11/` | `setup_error=bind system: No such file or directory` |
| live pass | `tmp/wifi/v320-private-property-lookup-proof-live-v11-mounted/` | `private-property-lookup-getprop-pass` |

## Selected Lookup Keys

The runner derives candidate lookup keys from the v312 property layout manifest:

| key | expected | context | type |
| --- | --- | --- | --- |
| `ro.build.version.sdk` | `31` | `u:object_r:build_prop:s0` | `int` |
| `ro.product.name` | `r3qks` | `u:object_r:build_prop:s0` | `string` |
| `ro.hardware` | `qcom` | `u:object_r:bootloader_prop:s0` | `string` |
| `ro.vendor.build.version.sdk` | `30` | `u:object_r:build_vendor_prop:s0` | `int` |

## Validation

```bash
python3 -m py_compile scripts/revalidation/wifi_private_property_lookup_proof.py
python3 scripts/revalidation/wifi_private_property_lookup_proof.py \
  --out-dir tmp/wifi/v320-private-property-lookup-proof-plan \
  plan || true
python3 scripts/revalidation/wifi_private_property_lookup_proof.py \
  --out-dir tmp/wifi/v320-private-property-lookup-proof-refuse \
  run || true
python3 scripts/revalidation/wifi_private_property_lookup_proof.py \
  --out-dir tmp/wifi/v320-private-property-lookup-proof-cleanup \
  cleanup
git diff --check
```

Result: PASS.

Post-V317 plan validation:

```bash
python3 scripts/revalidation/wifi_private_property_lookup_proof.py \
  --out-dir tmp/wifi/v320-private-property-lookup-proof-plan-after-v317 \
  plan
```

Observed output:

```text
decision: private-property-lookup-plan-ready
pass: True
reason: all prerequisites are present; live run still requires approval and helper implementation
device_commands_executed: false
device_mutations: false
```

Live validation after exact V320 approval:

```bash
python3 scripts/revalidation/wifi_private_property_lookup_proof.py \
  --out-dir tmp/wifi/v320-private-property-lookup-proof-live-v11-mounted \
  --approval-phrase 'approve v320 private property lookup proof only; no daemon start and no Wi-Fi bring-up' \
  --allow-device-mutation \
  --assume-yes \
  run
```

Observed output:

```text
decision: private-property-lookup-getprop-pass
pass: True
reason: 4 allowlisted properties matched expected v312 values
next: proceed to bounded CNSS pre-start environment probe planning
```

Live lookup results:

| key | observed | expected | status |
| --- | --- | --- | --- |
| `ro.build.version.sdk` | `31` | `31` | PASS |
| `ro.product.name` | `r3qks` | `r3qks` | PASS |
| `ro.hardware` | `qcom` | `qcom` | PASS |
| `ro.vendor.build.version.sdk` | `30` | `30` | PASS |

## Guardrails Verified

- Pre-live plan mode keeps `device_commands_executed=false`.
- Pre-live plan mode keeps `device_mutations=false`.
- v312 property layout is present and parsed.
- v319 report is present.
- Pre-V317 state blocked because V317 live proof evidence was missing.
- Post-V317 state detects `private-property-namespace-proof-pass`.
- V320 plan records four read-only property lookup commands.
- Required V320 approval phrase is recorded but not accepted implicitly.
- Live run used a private property namespace only.
- Live run did not start Wi-Fi daemons, scan/connect, DHCP, routing, rfkill,
  firmware mutation, or public network listeners.

## Required Future Approval Phrase

```text
approve v320 private property lookup proof only; no daemon start and no Wi-Fi bring-up
```

This phrase is now the next live blocker after V317 PASS. It is separate from
the V317 approval and still does not approve daemon start or Wi-Fi bring-up.

Status: consumed for the recorded live proof above. Future V320 reruns still
require the same explicit phrase.

## Decision

- historical decision: `private-property-lookup-blocked-v317-missing`
- post-V317 decision: `private-property-lookup-plan-ready`
- live decision: `private-property-lookup-getprop-pass`
- current status: V320 live proof passed
- next step: proceed to bounded CNSS pre-start environment probe planning; still
  no daemon start or Wi-Fi bring-up without a new explicit approval boundary.
