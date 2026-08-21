# A90 candidate System-return continuation — H0 design

Status: H0 implementation complete; the fixed backend is wired but remains
non-authoritative pending fresh independent review, qualification, and a
current attended token. This document grants no D0, D1, F1, device, USB,
ADB, TWRP, physical, or live authority.

## Problem

The checked F1 helper can prove that the candidate boot bytes were written and
that the exact boot-prefix readback matched, then lose the outcome of its one
TWRP `Reboot -> System` request. A generic return code or helper prose cannot
distinguish that state. The owner must not immediately rollback in that one
case, because the candidate may already be booting; it must also never replay
the candidate or resend the TWRP request.

The machine receipt and durable owner park are implemented in the checked
owner. The separate candidate-neutral continuation state machine and its
fixed production backend are now implemented. Backend availability is not
authority: a fresh independent review must bind the current closure, current
qualification and manifest must pass, and one attended token must be current
before any contact or physical instruction.
There is no static live-enable boolean. `review_gate_present()` is only an
availability predicate: it is true only when the direct regular review path
contains a canonical, current `PASS_GO` review with the exact schema, scope,
zero findings/contacts, and current closure. Absent, symlink, malformed,
wrong-verdict, or stale-closure review makes the CLI reject before backend
creation; a PASS review alone still cannot create a token or authorize contact.

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
This unit contains the journal state machine and selects only the exact fixed
backend module
`workspace/public/src/scripts/server-distro/a90_f1_candidate_return_backend_v1.py`.
That backend implements bounded USB/ADB inventory, fixed Native/TWRP
observations, and owner-adapter rollback delegation. It accepts no caller
command, serial, endpoint, target, outcome, or reboot string. Its availability
is still H0: independent review, fresh qualification/manifest binding, and an
attended token remain required before any live effect or observation.
The operational precondition is exactly one Samsung USB endpoint (`04e8`).
Non-Samsung host USB devices may remain, but every other Samsung device must
be disconnected before the attended run. This is intentionally an A90
speed/safety boundary, not a permanent common boundary; multi-device support
is out of scope and requires a new design/review. Native is exactly one
`04e8:6861` endpoint with zero ADB rows. Recovery is exactly one `04e8:6860`
endpoint with exactly one total ADB row in `recovery` whose serial hash equals
the manifest binding. Extra Samsung/ADB rows, wrong product/state, or
ambiguity park before per-serial contact.
The owner helper registers the qualification serial hash before its first
inventory. The owner `HostRunner` captures every ADB inventory through pipes,
registers recoverable endpoint tokens, and persists stdout and stderr only as
fixed SHA-256/length/status markers. Registered serials in later
command/exception/child output become `<A90-ADB-SERIAL-SHA256:...>`; raw bytes
exist only transiently for the in-process parser. Legacy mode keeps its
historical logging path and does not enable this owner redactor.
The backend factory requires an opaque continuation-issued activation lease
whose exact module sentinel binds the current manifest, run, pending receipt,
approval, phase, review/closure lease, and guard/intent callbacks. `prepare`
cannot create it. Every backend method and every subprocess call revalidates
that lease before and after contact; stale phase, intent, guard, manifest, or
single-Samsung inventory state fails before the next runner call. This is a fail-closed
workflow API, not a claim that same-UID Python code is an isolation boundary.
The intent callback rereads the strict current journal prefix before contact:
every envelope must bind the activation manifest, and the live 22/23 receipt
join must equal the activation's pending-receipt binding. A complete prefix for
another manifest or a substituted receipt therefore fails before the runner.
Its effect entry is rollback-only: `rollback` must be the exact boolean
`true`, and the artifact must be the strict five-field manifest rollback
binding. Candidate, alternate-path, equal-SHA, schema/type, and symlink
variants fail before contact. A direct regular-file identity/hash checkpoint
is taken immediately before and after the existing helper, with lease and
guard checks around both checkpoints.
For rollback from an exact Native endpoint, the backend performs the fixed
`a90_bridge.py preflight` twice: once to bind the managed listener generation
and again immediately before the helper. The strict receipt binds the fixed
ACM realpath, managed PID, listener inode, process argv, and selected-device
identity. A generation/realpath/PID change parks before the helper. The owner
helper repeats the same fixed preflight immediately before its sole Native
`recovery` frame; a bound recovery endpoint skips bridge recovery entirely.
Immediately before delegating either rollback branch to the owner helper, the
backend performs one final strict USB/ADB inventory and binds the SHA-256 of
the complete raw `/usr/bin/lsusb` byte stream (including non-Samsung rows and
ordering) into the fixed owner argv. In explicit owner receipt mode,
`native_init_flash.py` runs the same fixed producer itself and compares the
raw digest before any ADB inventory, Native bridge frame, push, boot write, or
other device command. A producer error, malformed or missing output, surviving
process, digest mismatch, single-Samsung/A90-role drift, or recovery ambiguity parks
with zero effect; legacy helper invocations do not receive or interpret this
owner-only binding.
For the Native branch, a separate pre-frame gate repeats the initial raw USB
and ADB digests and strict `NATIVE_NO_RECOVERY`/`04e8:6861` role immediately before the fixed bridge preflight and sole
`recovery` frame. A mutation after the earlier baseline gate therefore stops
before the bridge; an owner inventory binding is invalid unless it also carries
the fixed bridge-preflight flag. The later Recovery gate is a distinct
post-transition check.
The same owner-only join binds the complete raw `/usr/bin/adb devices -l`
byte stream and one parsed role: `NATIVE_NO_RECOVERY` or
`BOUND_RECOVERY_PRESENT`. The helper re-runs that fixed inventory and requires
both the exact raw digest and exact role before any bridge recovery, per-serial
ADB shell/push, or boot write. A recovery-to-device/offline/unauthorized
transition, duplicate or multiple recovery serial, or extra ADB endpoint
therefore stops before effect; legacy helper invocations carry no ADB binding
flags. After Native legitimately becomes Recovery, the post-transition gate
requires exactly one Samsung `04e8:6860` endpoint and one bound recovery ADB
row. Product, role, state, addition, removal, or duplicate drift stops, while
the changed post-transition raw USB/ADB bytes are evidence only and are not
compared to the pre-recovery digest. An already-Recovery branch still requires
the same-epoch raw digest before effect; multi-device coexistence is out of scope.
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
   exact return to bound TWRP. Observer loss, ambiguity, extra endpoint, or
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

The continuation unit must not import the retired large orchestrator, accept
arbitrary command selection, or make old journals satisfy new fields. The
fixed backend executes only its bounded USB/ADB inventory and fixed TWRP
identity command; it never uses ADB on Native, never contacts another Samsung
endpoint, and never sends a host reboot command. The durable observed record
carries the exact single-Samsung USB/ADB inventory binding; no multi-device
coexistence baseline is modeled by this unit.

The CLI has only `prepare`, `resume`, and `finalize`. `prepare` is host-only.
The fixed backend is selected by the checked module closure, never by a
manifest or caller; review/qualification/manifest/token/attendance gates
remain mandatory before `resume` or `finalize` can contact a device. No
command, serial, target, outcome, or reboot string is accepted as input.
For the first owner ADB inventory, the runner performs a bounded two-pass
capture: it registers every recoverable endpoint first-column token, then
persists both stdout and stderr only as fixed SHA-256/length/status markers.
Valid, malformed, nonzero, and timed-out output all use digest-only persistence;
raw streams remain transient parser input.
