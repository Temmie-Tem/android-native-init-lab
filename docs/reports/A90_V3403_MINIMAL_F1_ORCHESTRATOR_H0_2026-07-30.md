# A90 V3403 Minimal F1 Orchestrator H0

Date: 2026-07-30 KST

Status:
`PASS_HOST_SEVENTH_REMEDIATION_RE_REVIEW_PENDING_NO_LIVE_AUTHORITY`

## Scope

This unit adds the minimum manifest-driven owner for one A90 V3403 experiment.
It does not add a transfer primitive. It delegates rootfs publication to the
existing absent-only staging adapter and both boot-only transfers to the
existing checked `native_init_flash.py`.

No rootfs byte was staged. No reboot, recovery transition, candidate transfer,
rollback transfer, mount, `switch_root`, or userdata operation occurred.

## Exact implementation

- Orchestrator:
  `workspace/public/src/scripts/server-distro/a90_v3403_f1_orchestrator.py`
- Size: `90880`
- SHA256:
  `d95121073eeb05d4cfa19e2b5b233fceec367b00ab61dbbeaad6f38e89aef6fb`
- Focused tests:
  `tests/test_server_distro_a90_v3403_f1_orchestrator.py`
- Staging adapter SHA256:
  `f09ccd62da1b741e7eda7596bf9092e405553827100015ed1c7c366b49cca7b3`
- Checked flash helper SHA256:
  `366dd38304625d37607916e92ea98a95271bbc4d9dfdc7eea106a5437b6dfe53`

## Transaction boundary

The live path is unavailable by default. A final
`a90_native_init_f1_prepared_v2` manifest keeps candidate, staging, F1, and
live authority false. After passed independent review and fresh D0 evidence,
host-only `--prepare-approval` may create one exclusive mode-`0600` receipt
whose token binds the exact manifest, run, orchestrator, staging adapter, flash
runner, candidate, rollback, rootfs, D0/path evidence, and recovery target
digest. Initial execution requires the operator to return that exact token and
an empty exact private transaction directory. Rollback recovery refuses a
second token and reopens only the binding recorded when the initial token was
consumed.

The remediated orchestrator performs only this sequence:

1. reopen the complete local closure;
2. refuse any preexisting staging-live state and invoke the staging adapter
   once;
3. consume only the exact ten-record, run/manifest-bound staging success
   journal;
4. recheck the exact bridge, healthy V2321 baseline, and exact remote rootfs
   regular-file/size/SHA plus work-path absence immediately before candidate
   intent;
5. recover the one exact recovery ADB target from two hash-bound private logs
   and pass that serial to every candidate and rollback helper invocation;
6. record candidate intent before invoking the candidate helper once;
7. verify candidate version and build as separate post-boot fields;
8. observe the V3403 source/work-copy markers and Debian PID1 over USB-local
   SSH;
9. wait for the bounded return to V3403;
10. record rollback intent before invoking the exact V2321 helper once; and
11. require exact V2321 health before closing.

Recovery contains no candidate route. If candidate intent exists without a
rollback-intent record, recovery can invoke only the rollback. If a rollback
helper process may have started but completion is missing, recovery never
reinvokes it; it can close only when read-only checks prove exact V2321 final
health. The sole retryable exception is a structured `process-spawn` error
that proves the helper process never started and records rollback transfer
count zero. That rollback-only resume reuses the consumed approval and durable
recovery mode, not a second token or a new operator choice.

Both normal `--from-native` and attended TWRP recovery routes use the same
manifest-bound recovery ADB digest. The raw value is reconstructed only in
memory from the two private logs and remains absent from tracked evidence and
the orchestrator CLI.

## Independent review and remediation

The first independent review of commit
`c918c12ce5de49c92a65bcf5e8e20c7558b3738c` returned `NO_GO`. It found six
execution blockers:

1. normal candidate/rollback did not select the exact recovery ADB endpoint;
2. a nonexistent combined version/build marker caused pre-session rejection;
3. a timeline-before-rollback-intent crash window blocked rollback recovery;
4. manifest-hash stage-path derivation made approval-time D0 circular and D0
   JSON was hash-bound but not semantically checked;
5. preexisting staging output could be reused without a candidate-time remote
   hash; and
6. the tracked closure contained a concrete USB-local device address.

The changed closure now addresses all six. Flash logs carry a private
boolean-only phase classification so host rejection, recovery selection,
payload transfer, boot write, and readback are distinct. Timeline recovery is
derived idempotently from the durable journal; missing reporting events do not
repeat a device transition.

The second independent review of remediation commit
`581e5a14d6a6380c746d76d897768906d1e12bbe` also returned `NO_GO`. It found
four remaining blockers:

1. the final manifest's true authority flags and public hash arguments could
   authorize execution without a fresh approval receipt;
2. the staging result could be created mode `0664` and immediately rejected;
3. a crash during a single direct journal write could expose a zero-length or
   partial final `*.json`, preventing safe rollback recovery; and
4. subprocess timeout/exec failures escaped without a structured phase result,
   while raw-log privacy depended on a later chmod.

The second remediation keeps every manifest authority field false, separates
host-only approval preparation from exact-token execution, and records only a
hash of the consumed token in the durable journal. Exclusive result/journal
writers create a mode-`0600` temporary file, complete and `fsync` it, then
publish the absent final name with a hard link and directory `fsync`.
Replaceable timeline snapshots use the same private temporary-file discipline
with atomic replacement. Raw logs are opened mode `0600` before subprocess
launch, and timeout or `OSError` becomes a structured nonzero record that
flows through the existing phase classifier and durable failure path.

The third independent review of remediation commit
`451c3558a8f4476685039d15508a61ccffa4bd95` also returned `NO_GO`. It found
two exception-semantic blockers:

1. a candidate helper timeout with no recognized phase marker was closed as
   definite pre-session rejection, discarding mandatory rollback authority
   even though marker absence at timeout does not prove no device session; and
2. a rollback helper `OSError` before process creation was treated as a
   consumed, non-retryable rollback attempt, leaving no route to restore a
   candidate still running.

The third remediation records whether the subprocess actually started and
labels timeout as `process-wait` and `OSError` as `process-spawn`. Candidate
timeout is always state-uncertain and retains rollback authority; only a
completed marker-free host rejection or exact pre-spawn failure can close
before rollback. A rollback pre-spawn failure records transfer count zero and
`rollback_retry_preserved=true`. Recovery accepts that exception only when the
complete durable record proves `process_started=false` and
`stage=process-spawn`; it reuses the recorded recovery mode and same approval.
Any unpaired rollback intent, timeout, nonzero started process, or possible
device session remains retry-forbidden.

The fourth independent review of remediation commit
`844910005fcce00654f4dbe8bc60c1d674c57920` returned `NO_GO`. The two third
review blockers were closed, but the inverse malformed-journal probe exposed
one remaining gate: a loosely shaped `rollback-process-not-started` record
appended after a started nonzero failure could open a second rollback.

The fourth remediation accepts a retry only when the last two journal records
are the directly adjacent exact `rollback-transfer-started` and
`rollback-process-not-started` pair generated by the runner. It requires exact
outer key sets and sequence/state values, the manifest rollback SHA, attempt
limit, durable recovery mode, prior rejection count, zero transfer, and
retry-preserved flags. The nested execution record must have its exact key
set, return code `125`, `process_started=false`, a complete `process-spawn`
`OSError`, all-false phase classification, and the exact empty raw-log
size/SHA. Recovery reopens the expected mode-`0600` raw log at the unique
transaction path and recomputes its identity. Any missing, extra, nonadjacent,
conflicting, malformed, moved, non-private, nonempty, or hash-mismatched input
returns non-retryable.

The fifth independent review of remediation commit
`6bf5ced7d529c999c0b5f1e297b9da9ee679c681` confirmed that the fourth
conflicting sequence was closed and that a genuine pair still recovered
correctly, but returned `NO_GO` after a larger mutation matrix. Python numeric
equality admitted boolean and float substitutes for integer fields; an
arbitrary `BogusError` string passed the suffix check; noncanonical timestamps
were not rejected; and resolving the raw-log path before `lstat` allowed the
exact name to be a symlink to another private empty file.

The fifth remediation changes all load-bearing numeric fields to exact
`type(value) is int` checks, including generic journal sequence, attempt
limit, prior rejection count, transfer count, return code, raw-log size, and
errno. Journal timestamps must use the exact seconds-resolution UTC form.
Every caught spawn `OSError` is normalized to the fixed
`type=OSError,stage=process-spawn,errno>0` record, so arbitrary class strings
cannot enter the retry proof. The raw-log string must equal the exact expected
transaction path; that original path is checked with `lstat` as a private
non-symlink regular file before resolution and hash reopening. Boolean, float,
bogus-error, timestamp, and symlink mutations now fail closed.

The sixth independent review of remediation commit
`13928159f5a8a2d315048a5a2e4c0112c521fbee` passed the exact `101/101`
snapshot, 33 isolated mutations, 22 full-recovery mutations, genuine-pair
recovery, and the earlier timeout/started/unpaired/conflict semantics, but
returned `NO_GO` on two remaining global-history paths. Resolving the expected
raw-log name before comparison allowed both the exact leaf and recorded
`raw_log` to be retargeted to the same private empty symlink target. Separately,
an older `rollback-invocation-failed` with `process_started=true` could be
hidden behind a later otherwise exact adjacent pre-spawn pair because only the
last two records were validated. Both mutations reached `invoke_rollback` in
full recovery.

The sixth remediation preserves the exact canonical-parent/lexical-leaf raw
log pathname without resolving it before string equality and `lstat`. The
original expected leaf must be a private non-symlink regular file before its
resolved identity is reopened and checked. Retry history is no longer a
last-pair predicate: from the first rollback state, action, or retry-marker
field through the journal end, the complete suffix must be an even sequence of
exact adjacent intent/process-not-started pairs. Every pair is checked with
its ordinal prior-rejection count and unique raw-log name, all pairs must retain
one recovery mode, and any earlier possibly-started failure, completion,
health closure, malformed pair, renamed rollback marker, or unrelated suffix
record makes retry non-authoritative. Multiple genuine pre-spawn pairs remain
accepted and advance only the unique next log ordinal.

The seventh independent review of remediation commit
`d2196bff88e9718c5994965c11d5c1485802abcf` confirmed both sixth-review
attacks now return false with zero full-recovery invocations. It also passed
the exact `101/101` snapshot, every prior 33 isolated and 22 full-recovery
mutation, one through three genuine pairs, and the earlier timeout, mode,
ordinal, completion, approval, privacy, staging, and target invariants. It
returned `NO_GO` on two deeper evidence-identity paths. Distinct expected retry
log names could be hardlinks to the same empty inode, and a historical started
record whose outer action/state/markers were renamed away but whose nested
`record.process_started=true` remained could be ignored before a later exact
pair. Both reached `invoke_rollback` in full recovery.

The seventh remediation rejects any retry raw log whose `lstat` link count is
not exactly one, preventing distinct names from reusing one inode. Suffix
discovery now treats a nested `record.process_started` key as rollback-related
unless the complete outer key set, action, and state exactly match one known
non-rollback process-bearing journal shape (`staging-failed`, `rootfs-staged`,
`candidate-host-rejected`, `candidate-invocation-failed`, or
`candidate-flashed`). Thus a renamed or stripped historical started record
begins a malformed rollback suffix and closes retry, while an exact candidate
process record followed by one or more genuine pre-spawn pairs remains
accepted.

## Validation

- Python compilation passed.
- The orchestrator suite passes `45/45`.
- The orchestrator, staging adapter, V3403 build, D3 handoff, and rootfs group
  passes `101/101`.
- Every modeled candidate-intent failure selects rollback-only recovery.
- A previously started rollback is never invoked twice.
- Durable completion records repair missing ordered timeline events without
  inventing an unrecorded completion or replaying a transition.
- A candidate command cannot appear in the recovery source closure.
- Both transfer commands bind only the manifest candidate or rollback `boot`
  image, exact recovery ADB target, and image version marker; post-boot checks
  require version and build separately.
- A staging result is accepted only with its exact contiguous ten-record
  run/manifest-bound journal, and no preexisting staging result is reusable.
- The exact remote rootfs size/SHA and work-path absence are rechecked directly
  before candidate intent.
- The changed tracked closure contains no concrete network address.
- Approval preparation leaves `device_contact`, `device_write`,
  `f1_authorized`, and `live_authorized` false, writes its exact private
  receipt mode `0600`, and cannot overwrite an earlier receipt.
- Initial F1 rejects a missing or different exact token. Rollback recovery
  rejects any second token and requires the original binding/token hashes in
  the durable approval record.
- Journal/result final names are never opened for in-place writing. An
  interrupted temporary journal file cannot enter the contiguous `*.json`
  sequence, and timeline repair atomically replaces only a complete snapshot.
- Timeout and missing-executable fault tests produce private mode-`0600` raw
  logs and structured return codes without losing phase classification.
- An end-to-end candidate timeout fault with no marker records
  `candidate-invocation-failed`, keeps `rollback_required=true`, and reaches
  mandatory rollback rather than `candidate-host-rejected`.
- An actual rollback pre-spawn fault records process-start false and transfer
  count zero. Rollback-only recovery with no second token selects the same
  durable recovery mode and a distinct raw-log path; an unpaired later intent
  remains non-retryable.
- A started nonzero failure followed by the earlier malformed
  process-not-started shape is rejected. Direct pairing and the complete raw
  log/record identity are required before the same-approval retry branch can
  run.
- The independent matrix's bool/float numeric substitutions, bogus error
  type, noncanonical timestamps, and exact-name symlink are all rejected;
  generic journal reads also reject float sequence values.
- Retargeting both an exact-name symlink and the journal `raw_log` to its
  resolved target is rejected in the predicate and does not invoke rollback in
  full recovery.
- An older possibly-started rollback followed by a new exact pair is rejected
  in the predicate and full recovery, including when its action/state names are
  obscured but rollback marker fields remain. A history made only of multiple
  exact pre-spawn pairs remains retryable with the next unique ordinal.
- Distinct expected retry names hardlinked to one inode are rejected by both
  the predicate and full recovery.
- A renamed historical record retaining only nested `process_started=true` is
  rejected by both the predicate and full recovery; exact known candidate
  process-record shapes remain valid pre-rollback history.
- The private draft inspection reports `device_contact=false` and
  `device_write=false`.
- A forced live invocation with the draft is rejected before creating either
  `staging-live` or `f1-live`.

## Remaining gate

All seven earlier review rounds are closed `NO_GO`; the seventh remediation has
not yet passed the required independent re-review. The current private draft
remains deliberately non-approvable.

The remaining sequence is:

1. commit and independently re-review the exact changed staging/orchestrator
   closure;
2. repeat the exact connected read-only target and all-three-path preflight
   using the stable run-ID-derived stage path;
3. bind the passed review and refreshed D0 evidence into a final manifest;
4. host-inspect that exact final manifest; and
5. obtain one fresh exact F1 approval.
