# S22+ FYG8 P3.17 historical-endpoint replay recovery incident

Date: 2026-08-14 KST
Target: Samsung Galaxy S22+ FYG8 only
Status: **RECOVERY CLOSED; DEVICE HEALTHY; POST-CLOSE H0 AUDIT INDEPENDENTLY REVIEWED**

## Outcome boundary

The P3.17 candidate AP transferred exactly once and Odin returned success. The
operator observed a normal candidate boot without a boot loop. The bounded ACM
candidate observer returned `endpoint-timeout`, so the candidate was consumed
but not formally proved.

The first recovery inventory saw both the S22+ and S20+ in Download mode and
correctly stopped before rollback. That snapshot is sealed as sequence 17,
contains two live endpoint identities, and has SHA-256
`498a17263a3aefd9ce5f30e271df536de0a3ed65bb8656691780d71d05984da9`.
After the S20+ was physically disconnected, a second recovery invocation still
stopped before a new snapshot or rollback transfer. The repair below was then
independently reviewed and bound to a fresh exact recovery-only approval.

The approved adapter selected the one fresh S22+ endpoint at `usb:2-1.3` and
transferred the exact boot-only Magisk rollback as attempt 1. Odin returned 0
and the durable transfer classification is `odin_transfer_completed`. The
Process-v2 journal is `CLOSED` with 19 records and transfer count `1/1`.
Android boot completion, stopped boot animation, rooted health, the exact boot
and supporting-partition identities, and Download-endpoint absence all passed;
`recovery_required=false`. No candidate replay, raw host Odin, receipt deletion,
second rollback attempt, A90 command, or S20+ command occurred.

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

The pre-recovery focused suite passed 17/17 and covered:

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

## Live result boundary

Independent review reproduced the pre-recovery private `--validate` result and found
the initial direct-final arm write, missing successful superclass seam, parsed
authority/receipt TOCTOU, attempt-2 re-entry edge, and unvalidated closed-result
reopen. The fixes above closed all five findings. Before execution, the common
and focused regressions were green, current inventory showed one S22+ Download
endpoint at the bound topology with S20+ absent, every bound input reopened,
and the operator supplied the exact recovery-only token.

The official result is `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK` with outcome
`candidate_not_proven_rollback_verified`. Two byte-identical 2,097,136-byte
final reads each contain two identical P3.17 records, so the top-level decoder
returns `MAX77705_RESULT_MULTIPLICITY`. Both decoded records report:

- executability `causal_ready=true`, all three provider masks bound before and
  after, `waiting_for_supplier=ZERO`, and gadget readiness;
- diagnostic probe entry and a bound diagnostic parent plus one exact `0x25`
  client;
- stage 10, `rc=0`, all four commands issued and all four responses observed;
- CONTROL1 pre `0x3f`, post1 `0x09`, and post2 `0x09`; and
- no post2 detection latch, with the explicit retained ceiling
  `physical_switch_movement_proven=false`.

These are duplicated retained diagnostic facts, not an accepted single-run
causal result. Multiplicity blocks the campaign-level causal claim, register
readback is not a physical-conduction witness, and host silence remains
non-refuting under the frozen matrix.

## Post-close host audit

The frozen recovery adapter's original `--validate` audit expected sealed
snapshot 17 to remain the tail. Successful recovery legitimately added three
snapshots, so that pre-recovery check now rejects the expanded history. This is
a host-only post-close validation scope defect, not a device, rollback, or
health failure. The approved adapter and authority remain byte-frozen.

`s22plus_fyg8_p317_recovery_close_audit.py` separately reopens the ordinary
live-result validator, exact arm, attempt-01 evidence, absence of attempt 2,
and sequence-17 SHA. It observes 21 snapshots total; the three post-barrier
identity counts are `[1, 1, 0]`, generation advances from historical 1 to
closed 2, and a synthetic fresh multi-endpoint vector remains fatal. The audit
returns `PASS_P317_RECOVERY_CLOSED_HEALTHY_HOST_AUDIT` with device contact and
commands both zero. Independent review returns
`PASS_GO_P317_RECOVERY_CLOSE_AUDIT_V1`; the expanded focused suite passes
18/18, the device is healthy, and no recovery authority remains.

## Post-close endpoint-observer correction

A later H0 audit of the same sealed sidecar corrects one sentence in the live
interpretation above. The host was not silent: the exact P3.17 candidate
enumerated high-speed at `3-1.3` under `0000:00:14.0`, bound `cdc_acm`, and
created `ttyACM0`. The frozen candidate observer remained pinned to Download
topology `2-1.3` under the different controller `0000:00:0d.0`; it selected no
endpoint and never opened the TTY. Its `endpoint-timeout`, null endpoint
identity, and zero-byte raw file are therefore a selector misclassification,
not proof of a zero-byte read.

This correction is confined to the P3.17 endpoint sub-result. The two retained
records, campaign-level multiplicity result, 1/1 transfer accounting, healthy
close, and physical-switch ceiling remain unchanged. The detailed correction,
negative selector fixtures, two-seam CDC-ACM positive control, and successor
banner-result design are recorded in
`S22PLUS_FYG8_P317_CDC_ACM_ENDPOINT_SELECTOR_CORRECTION_H0_2026-08-14.md`.
