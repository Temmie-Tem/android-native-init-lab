# A90 candidate-return continuation — independent-review handoff

Status: H0 handoff. No D0, D1, F1, device, USB, network, TWRP, physical, or
live authority is granted. The fixed backend is implemented and wired, but
availability is not authority: fresh independent review, qualification,
manifest, and one attended token are still required.

## Reviewed object

`workspace/public/src/scripts/server-distro/a90_f1_candidate_return_continuation_v1.py`

Capability: `A90_F1_CANDIDATE_RETURN_CONTINUATION_V1`

The runner imports the exact checked owner and adapter modules. Its execution
closure is source-only and must not contain this review JSON or any other
review/report bytes. The fixed review path expected by `prepare` is:

`docs/reports/A90_F1_CANDIDATE_RETURN_CONTINUATION_INDEPENDENT_REVIEW_2026-08-21.json`

That file is intentionally absent until an independent review produces it.
The CLI has no hardcoded live-enable flag. Its review-gate predicate reports
availability only for a direct regular canonical current `PASS_GO`; missing,
symlink, malformed, wrong, or stale-closure review rejects before backend
creation. PASS alone still does not grant token, attendance, intent, or
device authority.
The checked H0 unit contains the state machine and the exact fixed backend
`workspace/public/src/scripts/server-distro/a90_f1_candidate_return_backend_v1.py`.
The backend is selected only by the checked closure, never by a manifest or
caller, and is not live authority. Independent review must verify its fixed
USB/ADB inventory, single-Samsung operational precondition, bound A90
Native/TWRP attribution, and owner-adapter rollback delegation before any
contact is authorized.
Exactly one Samsung USB endpoint (`04e8`) must be present: non-Samsung host USB
devices may remain, but every other Samsung device must be disconnected before
the attended run. This is an intentional A90 speed/safety precondition, not a
permanent common boundary; multi-device support is out of scope and requires a
new design/review. Native is exactly one `04e8:6861` endpoint with zero ADB
rows. Recovery is exactly one `04e8:6860` endpoint and exactly one total ADB
row in `recovery` whose serial hash matches the manifest. Extra Samsung/ADB
rows, wrong product/state, or ambiguity stop before per-serial contact. Owner
mode persists only digest/status markers and redacts registered serials as
`<A90-ADB-SERIAL-SHA256:...>`; legacy mode is unchanged.
The backend cannot be constructed from a manifest or caller alone. The
continuation creates its exact activation lease only after the phase-specific
intent and both guards are durable; the lease binds review/closure, manifest,
run, pending receipt, approval, and the exact single-Samsung inventory binding. Every
runner call is bracketed by lease/intent/guard revalidation. A stale lease or
restored review swap fails before the next command; this is a workflow API
invariant, not same-UID Python isolation. Before each contact, the intent
callback rereads every strict journal envelope and requires the current 22/23
receipt join to equal the activation-bound pending receipt; cross-manifest or
receipt-substituted prefixes fail before the runner.
The backend effect surface is rollback-only. It requires exact boolean
`rollback: true`, the manifest-bound five-field rollback artifact, and direct
regular-file identity/hash checkpoints immediately before and after the owner
helper. Candidate, alternate-path, equal-SHA, extra-field, and symlink inputs
are rejected before contact.
On the Native rollback branch, the backend requires two matching strict
managed-bridge preflights (fixed ACM realpath/PID/listener inode/process
argv), with the second directly before the helper. The owner helper repeats
that fixed preflight immediately before its one Native `recovery` command;
the already-present bound recovery branch sends no Native bridge command.
Immediately before either helper invocation, the backend binds a complete raw
`/usr/bin/lsusb` byte-stream SHA-256 (not a count or Samsung-only digest) into
the owner-only argv. The owner helper repeats the fixed producer and compares
that digest before ADB binding, bridge recovery, push, or boot write. Any
producer failure, malformed/missing/surviving process, digest mismatch, or
A90-role/single-Samsung drift stops with no effect; legacy invocations omit
this mode entirely.
When the bound endpoint is still Native, the owner performs this same initial
USB/ADB raw-digest and strict Native-role check again
immediately before bridge preflight and the sole recovery frame. The owner
inventory binding is rejected unless the fixed bridge-preflight flag is also
present. The post-transition Recovery/product/serial gate is separate and follows the
legitimate Native-to-Recovery change.
The same argv carries the complete raw `/usr/bin/adb devices -l` digest and
the parsed role `NATIVE_NO_RECOVERY` or `BOUND_RECOVERY_PRESENT`. The owner
helper re-runs and strictly parses that inventory before any bridge or
per-serial ADB operation. State drift, duplicate/multiple recovery endpoints,
and extra ADB endpoint or raw inventory changes fail closed; legacy invocations
carry neither binding. After a Native-to-Recovery transition, the same
single-Samsung rule requires one `04e8:6860` endpoint and one bound recovery
ADB row; product, role, state, addition, removal, or duplicate drift is a stop.
The changed post-transition raw bytes are evidence only and are not compared to
the pre-recovery digest. An already-Recovery branch still requires the
same-epoch digest before effect. Multi-device coexistence is out of scope.

## Runner contract

| Mode | Contact | Durable effect | Required input |
|---|---:|---:|---|
| `prepare MANIFEST` | 0 | 0 | exact manifest, run, guards, `22` and valid `23` or exact missing-`23` crash prefix, current review/closure |
| `resume MANIFEST --approval TOKEN --operator-attended` | no authority until fresh review/qualification/token | continuation intent then fixed inventory/observation receipt | exact fresh token and exact pending prefix |
| `finalize MANIFEST --approval TOKEN --operator-attended` | no authority until fresh review/qualification/token | observation intent then terminal or one rollback | exact consumed return observation; physical confirmation only for TWRP branch |

The manifest can select only the candidate/rollback bytes already bound by the
owner. It cannot select a command, endpoint, serial, target, outcome, reboot,
or retry. The run namespace is derived from the manifest and the owner guards;
it is never caller-selected.

## State and no-replay rules

- An exact uncertain `22` with no `23` is reconstructed as
  `CANDIDATE_RETURN_PENDING` before contact. Its receipt digest must join
  exactly to `22.payload.receiptSha256`.
- `resume` publishes `24-candidate-return-intent.json` before inventory.
  Native candidate visibility requires `finalize`; exact TWRP identity emits
  only one operator instruction, `Reboot -> System`.
- `finalize` publishes `25-candidate-observation-intent.json` before the one
  candidate observation. An intent present after any cut blocks replay.
- Candidate PASS requires exact candidate version/build, selftest/health,
  pstore zero, fresh state, recovery, exact single-Samsung role, and
  recovery evidence equal to the manifest-bound qualification review digest.
- Rollback success has the same recovery-evidence join; a valid snapshot with
  another review digest is `RECOVERY_REQUIRED`, never rollback success.
- TWRP identity validation rejects missing/extra keys and every numeric
  bool/float/string substitution before equality; a mismatch emits no physical
  instruction.
- After durable rollback `31`, both active and candidate guards are checked
  again immediately before flash; either missing guard means no backend call
  and a `PARK_ROLLBACK_NO_REPLAY` recovery prefix.
- Owner terminal `40` is reopened and strictly read back before active-guard
  release; any durable-byte or current-review/closure mismatch retains guards
  and raises without a second publication or effect retry.
- Both continuation and manifest qualification reviews are leased by direct
  identity/SHA, with source closure bound to the continuation review;
  pre/post contact and publication checks, including the owner terminal
  callback, reject swaps even when replacement bytes are identical.
  The qualification-review SHA is explicit in approval/intent bindings, while
  its private bytes remain outside the continuation closure.
- Only explicit candidate health contradiction, wrong candidate identity, or
  exact bound TWRP return after confirmed physical action may launch the
  existing one-shot rollback. Rollback success requires its exact confirmed
  owner receipt. No observer or transport failure may launch rollback.
- PASS publication is followed by exact terminal readback and active-guard
  release only. The candidate guard is a permanent consumed no-replay marker;
  it remains present and prevents re-preparing the same candidate SHA.
- Every attributed observed record carries the exact single-Samsung USB/ADB
  inventory binding. The one-Samsung operational precondition is checked before
  and after each effect; multi-device coexistence is intentionally not modeled.

## Review questions

1. Is the fixed closure complete and free of review/report/private bytes?
2. Does every resume/finalize contact occur after its corresponding intent?
3. Are exact USB/bridge/ADB inventories and TWRP identity receipts sufficient
   to attribute the branch without accepting foreign or ambiguous endpoints?
4. Is physical confirmation required only for the TWRP branch, with no host
   reboot command or repeat instruction?
5. Are candidate PASS and rollback success gated by exact confirmed effect
   receipts and exact health snapshots?
6. Do every crash prefix, malformed receipt, guard drift, review/closure drift,
   candidate/rollback drift, observer failure, and extra endpoint park
   without candidate replay or unqualified rollback?
The first owner ADB inventory is two-pass and fail-closed: endpoint tokens are
registered before replacement across the complete stdout, while malformed,
nonzero, or timeout stdout and all nonempty stderr persist only as fixed
SHA-256/length/status markers.
