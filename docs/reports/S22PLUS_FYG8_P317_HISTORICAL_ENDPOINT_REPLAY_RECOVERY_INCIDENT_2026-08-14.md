# S22+ FYG8 P3.17 historical-endpoint replay recovery incident

Date: 2026-08-14 KST
Target: Samsung Galaxy S22+ FYG8 only
Status: **RECOVERY-ONLY CAPABILITY INDEPENDENTLY REVIEWED; FRESH APPROVAL REQUIRED**

## Outcome boundary

The P3.17 candidate AP transferred exactly once and Odin returned success. The
operator observed a normal candidate boot without a boot loop. The bounded ACM
candidate observer returned `endpoint-timeout`, so the candidate is consumed
but not formally proved. The durable Process-v2 transaction remains
`OBSERVED`: candidate transfers are `1`, rollback transfers are `0`, and final
health is not yet verified. The exact Magisk rollback is therefore mandatory.

The first recovery inventory saw both the S22+ and S20+ in Download mode and
correctly stopped before rollback. That snapshot is sealed as sequence 17,
contains two live endpoint identities, and has SHA-256
`498a17263a3aefd9ce5f30e271df536de0a3ed65bb8656691780d71d05984da9`.
After the S20+ was physically disconnected, a second recovery invocation still
stopped before a new snapshot or rollback transfer. The current S22+ remains
parked in Download mode; the S20+ is detached. The attached A90 is outside the
Odin Download set and has received zero commands.

No candidate replay, raw `odin4`, receipt deletion, rollback transfer, or new
partition effect occurred during diagnosis and implementation.

## Root cause

`wait_for_single_live_endpoint()` resumes its endpoint-generation tracker by
calling `_resume_tracker()`. That function replays every durable snapshot and
feeds each historical `live_device_identities` vector into
`EndpointGenerationTracker.observe()`. The tracker intentionally rejects a
vector wider than one endpoint.

That rule is correct for a fresh snapshot because two current Download devices
make target selection ambiguous. It is wrong as resume semantics for this exact
history: sealed sequence 17 proves an ambiguity that already stopped a prior
invocation; it is evidence about the past, not a statement that two endpoints
are still attached. Replaying it as current state makes every later recovery
fail before fresh enumeration, even after the foreign endpoint is removed.

The defect is therefore not an Odin transfer failure and not a device-health
failure. It is a historical-receipt/current-inventory conflation in recovery
state reconstruction. The original receipt remains valid and must not be
deleted or reinterpreted as a successful target selection.

## Recovery-only repair

The incident-specific adapter is
`workspace/public/src/scripts/revalidation/s22plus_fyg8_p317_recovery_only.py`,
32,473 bytes, SHA-256
`768f393e98dd047e4b3a1b23dd1aeb1f84528e5d2f96f27428e086a4159152d1`.
Its authority document is
`workspace/public/src/device-action/recovery/s22plus_fyg8_p317_recovery_only_v1.json`,
SHA-256
`e737dd79e06929f66319caced51083e1ad4c7e66f7f8fda233b2228a028b9489`.

The adapter does not modify the common Odin-transition core or the frozen
P3.17 live adapter. That matters because those bytes are already part of the
consumed preparation binding. Instead, only inside the exact recovery process,
it replaces the two private replay seams while retaining the normal measured
enumeration, ticket revalidation, boot-only transport, journal, rollback, and
final-health paths.

The repair accepts an ambiguous historical vector only if all of these match:

- the exact P3.17 incident run directory;
- snapshot sequence 17;
- the exact sealed receipt path and SHA-256 above; and
- exactly two historical identities.

That receipt becomes an epoch barrier for generation reconstruction. It clears
only the replay tracker's previous-live set and preserves the generation count.
The next fresh single endpoint therefore receives generation 2. Any other
historical ambiguity, any second ambiguity, or any fresh multi-endpoint vector
still fails closed. The original receipt and transaction index remain intact.

## Bound inputs and transfer surface

The recovery binding is
`8ca5bd43dde4f85c466c741f8be465adee861abd472cf66247970866df007870`.
It binds:

- the exact `SM-S906N` / `g0q` / `S906NKSS7FYG8` target and `usb:2-1.3` topology;
- the consumed P3.17 approval binding `d5c2c24...` and execution closure
  `7fae669c...`;
- the manifest, prepared record, private target, candidate start/result, live
  adapter, Odin-transition core, and sequence-17 receipt;
- the exact boot-only Magisk rollback AP, 23,367,721 bytes, SHA-256
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`;
  and
- the initial `OBSERVED` live state, journal head, and endpoint index.

On first authorized entry, before fresh enumeration, the adapter publishes one
exclusive host arm receipt containing those initial mutable identities. It
writes and fsyncs a private temporary record, atomically links the complete
inode to the final no-clobber name, fsyncs the directory, and then removes the
temporary link. A crash cannot leave a partial final arm. The authority
identity in that arm is calculated from the same bytes that were parsed, and
the canonical authority is reopened before and after publication. Later
recovery of the same rollback may use that arm after the journal or endpoint
receipts legitimately advance. Without the arm, all three initial mutable
identities must remain byte-exact.

`request_download()` is prohibited because the operator already placed the
exact S22+ in Download mode. `transfer()` accepts only kind `rollback`, attempt
1, prefix `rollback-attempt-01`, and the bound AP; a candidate kind, second
attempt, changed AP, or second call is rejected before the inherited transfer
function. A recovery-only attempt-start patch also rejects candidate or second
rollback starts before the common durable writer. If attempt 1 already has a
start but lacks a durably completed result, re-entry stops without entering the
common recovery path or creating attempt 2. A closed result is accepted only
after the ordinary live-result validator reopens it against durable state.

## Host validation

The focused suite passes 17/17 and covers:

- authority and approval-token integrity;
- canonical live-authority path, same-byte authority identity, atomic
  exclusive/idempotent arm behavior, and interrupted temporary publication;
- reproduction of the original `_resume_tracker()` ambiguity failure;
- the exact barrier followed by a fresh single endpoint and ticket
  revalidation;
- altered receipt hash, a second historical ambiguity, and a fresh ambiguity;
- candidate and nonexact rollback rejection before the superclass transfer;
- the exact superclass rollback seam once followed by same-object second-call
  rejection;
- consumed attempt-1 re-entry and attempt-2 start rejection before the common
  writer; and
- validated idempotent reopening of an already closed live result; and
- prohibition on requesting another Download transition.

The real host-only `--validate` path additionally reopens the complete P3.17
bundle and prepared binding, reads the actual 18 sealed snapshots, reproduces
the old failure in memory, reconstructs generation 1 with the exact barrier,
assigns generation 2 to a synthetic fresh-single vector, and rejects a
synthetic fresh-multi vector. It performs no USB enumeration, arm write, device
command, Odin call, or partition transfer. Python compilation and scoped
`git diff --check` pass.

## Remaining authority boundary

Independent review reproduced the actual private `--validate` result and found
the initial direct-final arm write, missing successful superclass seam, parsed
authority/receipt TOCTOU, attempt-2 re-entry edge, and unvalidated closed-result
reopen. The fixes above close all five findings. This capability verdict does
not authorize live recovery. Before execution:

1. the common and focused regressions must remain green;
2. current inventory must again show exactly one Download endpoint at the
   bound S22+ topology, with the S20+ absent;
3. the exact rollback, journal, source hashes, and authority must reopen; and
4. the operator must provide the exact fresh recovery-only token emitted by
   `--validate`.

Only then may the adapter resume the original transaction. It may transfer the
exact rollback once and finish ordinary Process-v2 health closure. It may never
transfer the consumed candidate.
