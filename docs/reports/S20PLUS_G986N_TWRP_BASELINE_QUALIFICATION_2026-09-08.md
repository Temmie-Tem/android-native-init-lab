# S20+ retained-T2 TWRP baseline qualification

Result: **PROVED_S20PLUS_G986N_TWRP_BASELINE_HEALTHY**

Retained T2 TWRP is now the default preparation/terminal recovery environment
for prospective S20+ native-init owners adopting the reviewed
[baseline profile](../operations/S20PLUS_TWRP_BASELINE_V1.md).
At the September 8 qualification, the device was left in qualified TWRP and
the shared action guard was absent. Later H0 checks do not refresh device health.
Existing consumed P0/P1 criteria and no-replay records remain unchanged.

## Live qualification

One exact healthy-Android preflight bound the retained S20+ serial and topology.
One `adb reboot recovery` was dispatched. The checker waited for the expected
recovery ADB state and then used the existing seven-command T2 identity and
boot-metadata collector. No second reboot, partition transfer, block-content
read, mount, staging, `su`, or command to S22+/A90/another target occurred.

The live collector proved root UID 0, TWRP `3.7.1_12-AstroForge_v2`, the pinned
T2 incremental/marker, `ro.secure=0`, `ro.debuggable=1`, `mtp,adb`, running adbd,
stable exact serial/topology and a fresh recovery boot distinct from source
Android. The fixed boot link resolved to `sda23`, partition 23, 131,072 sectors
and 67,108,864 bytes. The observed rdev was `259:29`; the collector derives and
cross-checks it rather than pinning a previous boot's minor number.

There were 32 host commands: 24 inventories and 8 selected-target commands,
including the sole reboot. The final seven-command collector consisted of two
inventories and five exact-target reads. Total entry/qualification took about
48 seconds, ending at 2026-09-07 22:10:21 UTC (2026-09-08 KST). This is one
measurement, not evidence that every TWRP roundtrip is faster than Android.

Private result:
`workspace/private/runs/s20plus-g986n-routine-actions/twrp-baseline-1788818973951327366/baseline.json`

Result SHA-256:
`5649cb91010875487cb0d88a7519201b70b87a2890061da19fc81177cde45760`

## What changed

- New native-init owners should start and finish in qualified retained T2,
  rather than require full Android/Magisk boot after every run.
- Boot restoration is still separate: an F1 terminal needs its fixed first
  boot rollback transfer and existing outcome validation. TWRP metadata alone
  proves no boot bytes, Android compatibility, or successful candidate execution.
- The new checker has only entry, read-only observation/resume and H0 validation
  modes. It has no Odin, partition writer, caller command or candidate surface.
- Expected disappearance/offline/old-Android states are bounded readiness waits.
  Reboot errors and exact-identity failures preserve a cause-specific stop;
  subsequent resume cannot silently retry them. Mode-transition replay is absent.
- The owner binds the unguarded retained-T2 closure before acquiring its own guard,
  then reuses the fixed collector within that owner. A validated machine result
  closes the guard without requiring an additional screen-confirmation message.

## Scope of the change

The new default is prospective. An existing owner with an explicit Android
terminal requirement is not silently rewritten, and no consumed P1 run is
reopened. A future F1 owner must bind its actual TWRP-to-Download preparation and
post-rollback return route to this predicate. The current checker does not grant
F1 authority or prove that Odin directly returns to TWRP.

This qualification proves ordinary controlled TWRP entry and recovery health.
It does not prove automatic recovery from a hung native candidate, kmsg/pstore
retention across reboot, a new TWRP image, or partition-content integrity.
Physical fallback and exact rollback artifacts remain necessary.

## Validation and source lifecycle

Independent capability/policy review returned PASS_GO with zero findings.
Thirteen focused tests covered the real fixed collector and temporary journals/
guards with synthetic transport, including interrupted entry, no reboot during
resume, foreign guards, wrong target/identity, failed reboot, durable resume
failure, boot freshness, terminal corruption and qualification drift.
Python compilation, real retained-T2 H0 closure validation and scoped whitespace
checks passed. No firmware build or repeated 211-test suite was required.

The capability fingerprint recorded for that qualification was
`67a9f0593ff4fe0b3113ab6f108cf566727c57d00f61029617457ba08efe6ddb`.
Its immutable qualification and focused log are under
`workspace/private/outputs/s20plus_g986n/twrp_baseline_v1/`.

Before qualification, the completed P1 one-run exception's temporary B0/P0/P1
runtime hooks were retired by restoring their verified pre-exception bytes,
with P1 remaining dormant. This repaired the retained T2 source pin without
changing the consumed T2 manifest, its terminal, or its proof. Both historical
and exception-executed source snapshots remain preserved under the earlier
private recovery-exception output. No device action was used for that cleanup.

## Prospective F1 integration follow-up

H0 work added `s20plus_g986n_twrp_f1_health.py`, a recovery-health receipt
codec for a future owner. It uses the existing fixed seven-command collector
through an explicitly supplied owner capability, then replays those exchanges
offline to validate the stored receipt. It records recovery health explicitly,
retains false Android-health/boot-content claims, and rejects a terminal boot
matching a supplied prior boot. Its transcript contains private identifiers and
must be stored privately. The owner remains responsible for source/run binding,
its guard/lease, and durable bounded failure capture before parsing.

Four focused tests passed against the real collector/parser with synthetic
transport: fixed producer/replay, transcript and claim tampering, stale terminal
boot, and negative command results. Independent review returned PASS_GO for
this codec only, with no findings. This is not an integrated or activated F1
owner, and no device command occurred during this follow-up.

The installed Odin help (`odin4 -h`, version `1.2.1-dc05e3ea`) describes
`--reboot` as normal-mode reboot and offers no direct recovery reboot option.
The historical retained-T2 owner omits that flag and uses attended physical
recovery entry. This supports a prospective route consisting of exact TWRP
preflight, causal Download entry, the separately bound candidate transfer,
one fixed boot rollback without automatic reboot, attended recovery entry,
and fresh T2 terminal health. Pre-candidate abort must also return to TWRP.
An alternative normal boot followed by ADB recovery entry needs its own bounded
readiness/identity transition; it is not already qualified by baseline entry.

Current P0/B0 command dispatch and receipt validators hardcode `--reboot`,
including a private P0 capability closure. The only pre-install profile hook
is bound specifically to P1. A prospective reusable runtime seam is therefore
needed before either return route can be integrated. The selected physical
return route is implemented in the shared successor described below. The
standalone baseline qualification remains intact.

## Shared F1 runtime integration — H0 complete

Result: **PASS_GO_H0**, with the shared runtime **unconfigured and inactive**.

The new [engine](../../workspace/public/src/scripts/revalidation/s20plus_g986n_twrp_f1_engine_v2.py)
and [runtime](../../workspace/public/src/scripts/revalidation/s20plus_g986n_twrp_f1_runtime_v2.py)
are reusable successors of the B0 engine and P0 runtime. A separate shared
version is necessary because retained T2 binds the original sources and the
old P0 command validator captures its reboot rule inside a private capability
closure. The originals remain byte-for-byte unchanged: B0
`82ec4cee48c3a39aa8dc4de6136e8fda3fbefe88d4821a71bdb0df55d2a17c2a`,
P0 `c9486ec43ad5f0ed6acc2b34436a9d1be7007e9be9d81bbdcd17c2e0d423d6ef`.
No consumed journal, manifest or T2 source pin was changed.

The implemented path is:

1. Validate retained T2 before acquiring the owner's guard; bind the validated
   predecessor and current recovery health to the new run.
2. Record the empty Download baseline and one Download-entry intent before the
   fixed ADB request; retain the existing causal arrival and preparation checks.
3. Keep candidate transfer and proof separate. The fixed candidate command
   uses normal reboot; the fixed rollback command omits `--reboot`. Actual
   dispatch, the private command validator and saved receipt validation use the
   same role-bound command constructor.
4. After rollback and process quiescence, publish one physical TWRP-entry intent.
   Return a pending instruction for the operator's key sequence. Subsequent
   finalization observes exact fresh TWRP and records its arrival.
5. Close only after proved boot rollback and qualified TWRP health. Unknown
   rollback outcome retains the guard even if TWRP is healthy. Candidate proof
   remains independent. A pre-candidate abort similarly returns to TWRP using
   the physical route, with no Odin or partition operation.

The full lease, consumed-candidate registry and process-cage machinery are
retained. Inventory and selected recovery reads share the fixed ADB environment.
Every fixed recovery exchange is captured privately before parsing. Timeout,
output overflow and producer errors are rejected even with return code zero and
valid-looking output; the failure evidence is retained. Saved health is derived
again from its raw captures. A reporting cut after TWRP arrival reuses that
arrival, without another transition or observation.

Twenty-six focused tests passed: 22 runtime tests and four codec tests. They
exercise the real collector/parser, raw capture files, prepared-history and
namespace validation, actual command/receipt producers and the real private
session lease, using synthetic transport and host Python fixture processes.
No ADB or Odin process contacted a device. Independent review found and then
verified the raw-failure rejection repair, and returned PASS_GO_H0 with no
remaining findings. Python compilation and repository boundary checks passed.

Final review and test evidence are under
`workspace/private/outputs/s20plus_g986n/twrp_f1_runtime_v2/`.
The final log SHA-256 is
`91442963901b4151b564e90a38412a69a14730085e50d2ac2bf74aeac20667df`.
The baseline fingerprint remains
`67a9f0593ff4fe0b3113ab6f108cf566727c57d00f61029617457ba08efe6ddb`.

This completes the shared H0 endpoint integration. A future candidate still
needs its own artifact/proof binding and activation in this runtime; inherited
placeholder fields confer no candidate qualification. No new candidate was
built, prepared or flashed, and no connected return qualification was attempted
in this follow-up. The last live observation remains the qualified TWRP baseline
recorded above. Automatic recovery from a hung candidate is not claimed.

## September 23 binding maintenance under Revision 27

Result: **PASS_GO_H0** for the dormant runtime migration and **PASS_GO** for
the prospective baseline capability. No device command was issued.

The shared S22+ transport gained an optional `before_launch` callback after
the original S20+ qualification. The dormant TWRP runtime rejected the changed
file before loading. Its execution path does not use that helper. The exact
previously reviewed 10,937-byte transport, SHA-256
`f18e2e453e33078a184653722d4579a184c59b1c3ac10f9eb54d4a4ba437ffea`,
is now preserved as
[`s20plus_g986n_boot_only_f1_transport_v1.py`](../../workspace/public/src/scripts/revalidation/s20plus_g986n_boot_only_f1_transport_v1.py).
It is byte-identical to the file before commit `d6525774c9`; the engine import,
source closure and isolated runtime binding all select this S20+ copy. The
current S22+ transport and consumed B0/P0/T2 sources remain unchanged.

The next loader check exposed a stale registry source pin. The runtime now
binds the current shared registry, including its exact reviewed host-relocation
receipt and preserved consumed-record prefix. Freezing the old inode validator
would retain an obsolete host-layout assumption. The existing claim/release
guards remain; the added S22+ owner-creation and owner-retirement helpers are
explicitly denied in the isolated S20+ instance and included in its dependency
integrity checks. Actual relocated-registry validation passed read-only.

The old baseline review differed only in the common-contract identity and
incorporated details. Current common and selected-target authority checks were
retained. The new prospective qualification is separate from the September 8
qualification and consumed baseline. Original review records and pre-change
source bytes are preserved under the private maintenance evidence directory.

Forty-nine focused tests passed: 25 runtime, four codec, 13 baseline and seven
registry relocation/claim/lock tests. They include isolated transport-instance
identity, exact historical bytes, denial of S22+ mutators inside the S20+ lease,
and detection of rebound denial functions. Python compilation, repository
boundary and scoped whitespace checks passed. Independent review returned
zero remaining findings in the two scopes above.

The new baseline fingerprint is
`4390bc79c9735764e3fb0793f89034bc4c0aecf89549851f6502a99df6e2051b`.
`require_review()`, baseline `--validate-host` and runtime `--validate-runtime`
pass against current files. Evidence is under
`workspace/private/outputs/s20plus_g986n/twrp_binding_refresh_rev27/`:
`baseline-qualification.json`, `h0-review.json`, the two test logs and preserved
predecessor receipts/sources. The baseline qualification SHA-256 is
`d4797898b385fe9f77374704a483f30146a471d1ca43d59f358677f75b74f1fc`.

The S20+ shared guard was absent during the H0 check. The runtime is still
unconfigured/inactive; a new candidate, observation profile and F1 activation
are not supplied by this maintenance. No consumed approval or effect was
reopened, and no fresh device-health or automatic-recovery proof is claimed.
