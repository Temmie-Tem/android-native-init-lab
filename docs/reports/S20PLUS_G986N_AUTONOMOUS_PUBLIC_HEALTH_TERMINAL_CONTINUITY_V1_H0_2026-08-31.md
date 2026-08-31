# S20+ G986N autonomous public-health terminal-continuity v1 H0

Date: 2026-08-31

Target: Samsung Galaxy S20+ 5G (`SM-G986N` / `y2q` / `y2qksx` /
`G986NKSS8IYC2`)

Status: **H0 MODEL PASS_GO - NOT ACTIVE**

## Purpose

Define the retained terminal-continuity bytes needed to interpret an opening
command-6 receipt after the producing process is gone, without accepting a
caller-supplied serial, clock, USB identity, time, or path. This unit adapts
the frozen Phase-A receipt grammar for hostile H0 fixtures only. It is not an
opening result, campaign binding, recovery-loader integration, finalizer,
executor, campaign opening, or device authority.

The implementation is
`workspace/public/src/scripts/revalidation/s20plus_g986n_autonomous_public_health_terminal_continuity_v1_h0.py`.
Its final 40,593-byte source is SHA-256
`134c674d4ddfafae958436a011956e144214fc896cb67070bdc4c88e72f610ad`,
with activation-normalized SHA-256
`bba10951e24e798c57d4db103f9d591a09d495c753f106ca144b3b90d923095a`.
The final 36,623-byte focused test is SHA-256
`4d23a89a3526dd83d8af49efdc0f859328cfc1c8b351b33cc0889344a64010d2`.

## Receipt extension

Every modeled opening receipt adds exactly one top-level field named
`terminal_continuity`. Its value is exactly `null` for ordinals 1 through 5.
Ordinal 6 contains exactly:

```text
schema
clock_sample
adb_server_after
usb_generation
observed_after_return_retained
```

The schema is
`s20plus_g986n_autonomous_public_health_terminal_continuity_v1`, and
`observed_after_return_retained` must be the literal boolean `true`.
Each extended receipt remains capped at 8 KiB. The adapter strips only this
new field and requires the remaining receipt to pass the exact hash-loaded
Phase-A validator. The predecessor of every later receipt hashes the previous
complete extended raw bytes, not a stripped or semantically equivalent form.

The terminal clock sample must pass the exact Phase-A clock-binding validator,
equal the command-6 receipt publication logical second, and be no earlier than
the retained return. The server-after receipt must pass the Phase-A schema and
be byte-semantically equal to the intent's server receipt.

The USB receipt receives an additional exact-runtime mapping check. The
adapter opens and verifies the frozen runtime source, verifies its normalized
identity and `_expected_usbfs_rdev` function, restricts bus numbers to
1–999 and device numbers to 1–127, and requires all of:

```text
usbfs_rdev == os.makedev(189, (busnum - 1) * 128 + (devnum - 1))
usbfs_rdev == exact_runtime._expected_usbfs_rdev(busnum, devnum)
topology_sha256 == topology derived from retained health
```

This validates the retained candidate receipt's structure and mapping. It
does not prove that the runtime owner actually observed or held those nodes.

## Retained evidence and derived recovery input

The evidence input must be the exact 19-file Phase-A opening set. The adapter
strictly revalidates every stdout/stderr hash and size, both inventories,
`get-devpath`, both public snapshots, command receipts, command count, health,
tool identity, and complete evidence bound. It derives the raw serial only
from retained command-2 inventory bytes and exports only its SHA-256.

The deterministic recovery-input model accepts exactly two keyword-only
inputs: `(intent_raw, evidence)`. It exports the campaign/session identifiers,
intent/evidence/terminal-receipt/health hashes, a guard-less derived-health
identity, retained terminal-continuity objects and their hashes, and explicit
false integration/authority flags. It accepts no caller identity, time, or
destination.

The 19 files do not contain a shared-guard observation. Accordingly the model
does not manufacture `foreign_guard_present=false` or export a Phase-A source
identity. It instead fixes all three limits as false:

```text
foreign_guard_absence_authenticated
source_identity_usable
runtime_owner_observation_verified
```

The validator requires exact `bytes`, canonical JSON, the fixed size bound,
and exact equality with a fresh derivation from the same two inputs. A
canonical `bytearray`, bytes subclass, duplicate key, non-finite number,
reordered/prettified encoding, or changed retained byte fails closed.

## Identity boundary

The adapter opens, bounds, hashes, compiles, and normalization-checks the exact
Phase-A and runtime source bytes on every model derivation. The recovery
loader, recovery core, and derived manifest identities are declarative pins
copied from the exact Phase-A binding only. This adapter does not open them and
does not prove any installed private bundle.

The recovery scanner still rejects future opening-v1/campaign-binding nodes.
No command-6 writer, runtime receipt producer, guard receipt, opening-result
consumer, campaign binding, loader rotation, or finalizer integration exists.

## Hostile validation and review

The focused suite passes 41/41. The canonical twelve-suite autonomous
aggregate, including this source, passes 446/446. `py_compile`, render-only
execution, and `git diff --check` pass.

The hostile corpus covers exact source identities; status/self normalization;
all-false gates and the unconditional all-true unimplemented stub; exact
receipt schema/null placement; extended-raw predecessors; every nested
clock/server/USB field; server equality; clock ordering; runtime USB rdev and
bus/device bounds; 8-KiB receipt edges; every missing/extra/non-byte evidence
node; each raw stream and health mutation; command-2-only serial derivation;
deterministic two-input recovery bytes; bytearray rejection; guard-claim
absence; and absence of subprocess, socket, device, root, Odin, or partition
surfaces.

The first independent review found a stale self anchor and the missing inner
schema; both were corrected. A later independent review found that the first
candidate accepted a Phase-A-only USB receipt with the wrong runtime rdev,
invented foreign-guard absence, accepted a canonical bytearray, and blurred
actual versus declarative pins. All four findings were corrected. Two exact
post-correction reviews independently returned `PASS_GO` with
HIGH/MEDIUM/LOW `0/0/0`.

## Non-authority result

The final status is
`H0_AUTONOMOUS_PUBLIC_HEALTH_TERMINAL_CONTINUITY_V1_MODEL_PASS_GO_NOT_ACTIVE`.
All 14 operational/integration gates remain false. Even forcing them true
reaches an unconditional unimplemented stub. The CLI exposes only
`--render-plan`; its command, subprocess, socket, root, Odin, device-write,
and partition-transfer lists are empty.

The ADB no-autostart/host-kill hazard, concrete receipt writer, runtime-owner
observation, foreign-guard evidence, opening-result/campaign-binding/recovery
integration, private bundle, production cross-code interlock, combined review,
contract activation, mechanical activation, and a fresh attended opening all
remain future work. This PASS_GO qualifies only the exact inactive H0 bytes.
