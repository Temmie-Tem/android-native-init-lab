# A90 candidate-return continuation — independent-review handoff

Status: H0 handoff. No D0, D1, F1, device, USB, network, TWRP, physical, or
live authority is granted. The production backend is intentionally disabled.

## Reviewed object

`workspace/public/src/scripts/server-distro/a90_f1_candidate_return_continuation_v1.py`

Capability: `A90_F1_CANDIDATE_RETURN_CONTINUATION_V1`

The runner imports the exact checked owner and adapter modules. Its execution
closure is source-only and must not contain this review JSON or any other
review/report bytes. The fixed review path expected by `prepare` is:

`docs/reports/A90_F1_CANDIDATE_RETURN_CONTINUATION_INDEPENDENT_REVIEW_2026-08-21.json`

That file is intentionally absent until an independent review produces it.
The checked H0 unit contains only the state machine and backend protocol; no
ADB/TWRP/device backend is selected or executed. A future backend must be
reviewed separately against the fixed inventory and TWRP identity constants.

## Runner contract

| Mode | Contact | Durable effect | Required input |
|---|---:|---:|---|
| `prepare MANIFEST` | 0 | 0 | exact manifest, run, guards, `22` and valid `23` or exact missing-`23` crash prefix, current review/closure |
| `resume MANIFEST --approval TOKEN --operator-attended` | disabled until review | continuation intent then observed receipt | exact fresh token and exact pending prefix |
| `finalize MANIFEST --approval TOKEN --operator-attended` | disabled until review | observation intent then terminal or one rollback | exact consumed return observation; physical confirmation only for TWRP branch |

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
  pstore zero, fresh state, recovery, unchanged foreign-target inventory, and
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
   candidate/rollback drift, observer failure, and foreign endpoint park
   without candidate replay or unqualified rollback?
