# A90 V3403 Minimal F1 Orchestrator H0

Date: 2026-07-30 KST

Status:
`PASS_HOST_SECOND_REMEDIATION_RE_REVIEW_PENDING_NO_LIVE_AUTHORITY`

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
- Size: `77243`
- SHA256:
  `332e789945f7dc234aa988386912102dc79d6e196a1a94753f2449f15f9ba5bc`
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
rollback-intent record, recovery can invoke only the rollback. If rollback
intent already exists but completion is missing, recovery never reinvokes it;
it can close only when read-only checks prove the exact V2321 final health.

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

## Validation

- Python compilation passed.
- The orchestrator suite passes `38/38`.
- The orchestrator, staging adapter, V3403 build, D3 handoff, and rootfs group
  passes `94/94`.
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
- The private draft inspection reports `device_contact=false` and
  `device_write=false`.
- A forced live invocation with the draft is rejected before creating either
  `staging-live` or `f1-live`.

## Remaining gate

Both earlier review rounds are closed `NO_GO`; the second remediation has not
yet passed the required independent re-review. The current private draft
remains deliberately non-approvable.

The remaining sequence is:

1. commit and independently re-review the exact changed staging/orchestrator
   closure;
2. repeat the exact connected read-only target and all-three-path preflight
   using the stable run-ID-derived stage path;
3. bind the passed review and refreshed D0 evidence into a final manifest;
4. host-inspect that exact final manifest; and
5. obtain one fresh exact F1 approval.
