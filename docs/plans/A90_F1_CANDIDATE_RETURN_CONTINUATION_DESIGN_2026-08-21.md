# A90 candidate System-return continuation — H0 design

Status: H0 implementation complete; live backend disabled pending independent
review. This document grants no D0, D1, F1, device, USB, ADB, TWRP,
physical, or live authority.

## Problem

The checked F1 helper can prove that the candidate boot bytes were written and
that the exact boot-prefix readback matched, then lose the outcome of its one
TWRP `Reboot -> System` request. A generic return code or helper prose cannot
distinguish that state. The owner must not immediately rollback in that one
case, because the candidate may already be booting; it must also never replay
the candidate or resend the TWRP request.

The machine receipt and durable owner park are implemented in the checked
owner. The separate candidate-neutral continuation state machine is now also
implemented, but its production backend remains disabled until its own
independent review.

## Fixed helper receipt

`native_init_flash.py` has one owner-only mode,
`--owner-receipt-mode A90_F1_OWNER_EFFECT_RECEIPT_V1`. In that mode stdout is
reserved for one canonical JSON object with this exact shape:

```json
{"bootWrittenReadbackExact":true,"mode":"A90_F1_OWNER_EFFECT_RECEIPT_V1","outcome":"BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_UNCERTAIN","schema":"a90-f1-owner-effect-receipt-v1","systemReturnAttempted":true,"systemReturnCommandOk":true,"systemReturnConfirmed":false,"writeStarted":true}
```

The fixed helper state machine emits one of:

- `PRE_WRITE_FAILURE` — no boot write started;
- `WRITE_OR_READBACK_UNCLASSIFIED` — a write was attempted, but exact prefix
  readback was not proved;
- `BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_CONFIRMED` — write/readback and
  the sole bounded TWRP return were both confirmed; or
- `BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_UNCERTAIN` — exact write/readback
  completed, but the TWRP return outcome was not confirmed.

The adapter accepts a stage only when the complete canonical receipt is
present, duplicate-free, and its boolean fields agree with the outcome. Empty
stdout, a generic nonzero return, prose, a missing receipt, or an inconsistent
receipt becomes `UNCLASSIFIED`; none may create a pending state.

The candidate PASS terminal and a successful rollback terminal additionally
require the exact `...SYSTEM_RETURN_CONFIRMED` outcome. A healthy snapshot
alone, a legacy result, or an `UNCLASSIFIED` receipt cannot create a new
success terminal. In the explicit owner receipt mode, the TWRP shell command
must return `rc=0` before disappearance of the recovery endpoint can be
considered confirmation; disappearance after a nonzero command is not
confirmation and does not create pending. The legacy helper mode retains its
historical result-object behavior and is not interpreted as a new owner
receipt.

## Durable owner park

After `22-candidate-result.json`, the owner may publish exactly one
`23-candidate-return-pending.json` only for the exact uncertain outcome above.
Its payload contains the effect receipt digest, `candidateReplay: false`, and
`rollbackIntentPublished: false`. It is published before any rollback record.
The active and candidate guards remain present. Existing H24/H27/H28 journals
without this record remain historical and are not upgraded or reinterpreted.
The consumed H28 qualification review likewise remains pinned to its original
closure and is readable only by the fixed closed-run historical readers; the
current owner rejects it for new execution. H29 and later continuation runs
must bind a fresh qualification, review, manifest, and owner closure.

The current execution result is `RECOVERY_REQUIRED` with reason
`CANDIDATE_RETURN_PENDING`; it is a park, not a terminal installation result.
No candidate retry, TWRP retry, rollback intent, reboot command, or token is
created by this unit.

If the host crashes after the durable `22-candidate-result.json` and before
the `23` publication, recovery parsing checks the complete typed `22` payload.
Only the exact uncertain outcome (`returncode != 0`, `completed: false`, valid
receipt digest, and the exact outcome string) yields
`CANDIDATE_RETURN_PENDING_RECORD_MISSING_NO_ROLLBACK`. It must not fall back to
`CANDIDATE_CONSUMED_ROLLBACK_ONLY`, and it publishes no rollback record. A
malformed, substituted, missing-outcome, or historical result is not upgraded;
an existing malformed `23` similarly yields a named no-rollback park. A
durable `41` closure remains terminal and is checked first.

The pending record is joined to the result, not merely to the manifest:
`23.payload.effectReceiptSha256` must equal
`22.payload.receiptSha256` exactly. A mismatch caused by changing either side
is `CANDIDATE_RETURN_PENDING_RECORD_INVALID_NO_ROLLBACK` and can never become
`CANDIDATE_RETURN_PENDING` or authorize rollback.

## Continuation implementation

`workspace/public/src/scripts/server-distro/a90_f1_candidate_return_continuation_v1.py`
adds fresh, candidate-neutral namespaces and requires a new independent review.
This unit contains the journal state machine and a narrow backend protocol; it
does not contain or select a device backend. A separately reviewed adapter must
implement the fixed inventory/identity observations before live activation:
Each invocation leases both the continuation review and the manifest-bound
qualification review by direct identity, size, and SHA-256, and captures the
computed source closure. The leases are revalidated before and after each
contact and journal publication, before physical instruction or rollback, and
through the owner terminal callback before active-guard release; swaps or
closure drift park/raise without accepting a restored file.
The qualification-review SHA is carried in the approval and fresh intents as
an input binding only; its private path/bytes are not added to the continuation
execution closure, so the lease does not self-reference.

1. `prepare` performs host-only current-review/closure binding and derives a
   token from the manifest, run, candidate, pending effect receipt, and owner
   closure. It does not contact a device or write durable state.
2. One attended `resume` publishes a no-replace continuation intent before
   inventory. It may classify only exact candidate Native health, exact bound
   TWRP presence, attributable candidate failure, or unresolved/foreign
   state. Exact TWRP presence yields one operator instruction to press
   `Reboot -> System`; the host sends no reboot command.
3. After the operator confirms that physical action, one separate `finalize`
   publishes an observation intent before one read. It may produce candidate
   PASS, or the already-bound one-shot rollback on attributable failure or
   exact return to bound TWRP. Observer loss, ambiguity, foreign endpoint, or
   missing attribution parks without rollback. Candidate and rollback health
   snapshots must carry the exact current qualification-review digest as their
   recovery evidence; a valid but mismatched digest parks and cannot close.
   TWRP identity is an exact-key, exact-type object: numeric stat fields reject
   bool, float, and string substitutions before value comparison.
   Rollback revalidates the active and permanent candidate guards immediately
   after durable `31` and before the backend effect; a missing guard parks the
   consumed `31` prefix without recreating or replaying it.
4. Every continuation and observation intent is consumed on success, error,
   timeout, or host loss. A present intent blocks replay. Rollback remains one
   intent/launch/result sequence and is never used to replay the candidate.
   A candidate PASS releases only the active-run guard; the candidate-SHA
   guard remains permanently consumed and rejects reuse of that candidate.

The continuation unit must not import the retired large orchestrator, execute
ADB/TWRP/USB commands, add arbitrary command selection, or make old journals
satisfy new fields. The fixed TWRP identity command is retained only as a
review input for that future adapter.

The CLI has only `prepare`, `resume`, and `finalize`. `prepare` is host-only;
`resume` and `finalize` are fail-closed while `LIVE_EXECUTION_ENABLED` is
false. The core functions accept only the reviewed backend protocol used by
host-only tests. No backend is selected by a manifest or caller, and no
command, serial, target, outcome, or reboot string is accepted as input.
