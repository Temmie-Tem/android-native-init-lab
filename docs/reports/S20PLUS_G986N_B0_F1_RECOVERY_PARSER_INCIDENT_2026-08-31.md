# S20+ G986N B0 F1 recovery-parser incident

Date: 2026-08-31

Status: **PASS_GO - EFFECTIVE ONLY AFTER SCOPED COMMIT; CANDIDATE REPLAY FORBIDDEN**

## Runtime state

The first multi-ADB v2 run selected only the exact S20+, bound rooted resident
health and the Download endpoint, received the exact emitted approval, and
completed one attributed candidate boot transfer. The candidate cgroup is
durably quiescent. Observation produced no ADB or Download arrival, so the B0
runtime claim remains `NO_PROOF` and mandatory resident rollback is pending.

The operator subsequently reported a normal boot with no bootloop. This is a
supportive attended observation only: it does not identify the running boot
artifact, bind the current boot ID, prove root health, upgrade the B0 claim, or
replace the mandatory resident rollback.

The candidate intent and global candidate claim are consumed. Candidate replay
is forbidden. No rollback intent or rollback transfer exists. The shared guard
remains present for the exact run.

## Incident

The first `--arm-physical-rollback` invocation stopped during host journal
validation with `AttributeError: 'RawCaptureHandle' object has no attribute
'argv0_name'`. It issued no device, ADB, Odin, USB, physical-arm, or rollback
effect. The physical-arm journal remains absent.

The pinned raw-capture module durably records and strictly validates
`argv0_name` in `candidate-transfer.capture.json`, but its frozen
`RawCaptureHandle` projection omits that field. The B0 validator incorrectly
dereferenced the omitted projection attribute instead of re-deriving the field
from the validated receipt. The same latent reference existed in the
pre-candidate payload-free return result validator.

## Recovery repair

The proposed owner keeps the journal `VERSION` at v2. A new fixed helper opens
the direct canonical receipt with the B0 no-follow bounded reader, binds schema,
name, return code, timeout/output flags, producer error, and both stream
receipts back to the already validated handle, then returns the receipt value.
Transfer validation derives `argv0_name`, receipt size, and receipt SHA-256
from those exact canonical bytes. Abort-return validation uses the same helper.
No caller path, command, value, or alternate receipt is accepted.

Because the prepared binding contains the immediately preceding owner identity,
the replacement pins a one-element recovery predecessor set containing only
normalized SHA-256
`e2d612fc14549d0b0838ba66473b203126342362480636f3599fd9ea1548ed40`.
That predecessor is accepted only for `rollback` or `health` when a durable
candidate intent already exists. Candidate phase and pre-candidate use reject
it, and the existing exact global candidate claim must still validate for the
same run. The compatibility path therefore cannot replay the candidate or
authorize another run.

Host-only parsing of the exact current journal now returns
`PASS_CURRENT_JOURNAL_RECOVERY_PARSE`. No recovery device command was issued
during this validation.

## Exact proposed closure

- owner: `224,559` bytes, SHA-256
  `82ec4cee48c3a39aa8dc4de6136e8fda3fbefe88d4821a71bdb0df55d2a17c2a`;
- normalized SHA-256:
  `52f2df6aa1864a956cd4d0e43a3906ffbb613116577d7735788630a43323ea06`;
- test: `60,003` bytes, SHA-256
  `e7f4add57131bdfe7ba3b2285aa02283ff2110d1e1abb9d507e35acf7cceee7b`;
- validation: `py_compile`, 56/56 focused tests, current-journal recovery parse,
  and scoped diff checking pass;
- host closure SHA-256:
  `aa17bf9d145f4909158b9132a58e81680f94e6007777aa601630bc8104f0812a`;
- `--validate-host`: `PASS_B0_HOST_CLOSURE_ONLY`, `live_authority: false`.

## Final independent review

Fresh exact-byte review returned `PASS_GO` with HIGH/MEDIUM/LOW `0/0/0`. It
independently reproduced 56/56 tests, exact owner/normalized/test identities,
host closure, compilation, scoped diff checking, and current-journal rollback
and health parsing. Candidate-phase parsing rejected the predecessor identity.
It also re-derived the current attributed candidate transfer, cgroup
quiescence, `NO_PROOF` observation, exact global claim, absent rollback intent,
and present guard. The review made no arm, resume, device, ADB, Odin, or USB
call and no edit.

The complete owner, test, target-contract, goal, and this incident report become
effective only when committed together. The repair may continue only the
current journal's mandatory resident rollback and health closure; it grants no
candidate replay. The arm must still emit its exact physical confirmation,
which the attended operator must return before a fresh physical observation or
rollback transfer. S22+, A90, and the other attached ADB device receive zero
commands and no modification.
