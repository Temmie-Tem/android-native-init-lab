# A90 V3403 Minimal F1 Orchestrator H0

Date: 2026-07-30 KST

Status:
`PASS_HOST_REMEDIATED_RE_REVIEW_PENDING_NO_LIVE_AUTHORITY`

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
- Size: `68088`
- SHA256:
  `a5309337853f5d8845c45411694b44703b1044afc900e75aef6ae89642857065`
- Focused tests:
  `tests/test_server_distro_a90_v3403_f1_orchestrator.py`
- Staging adapter SHA256:
  `93a3bf1cbf7a2af0745c3296dde62e01650a6db42b3e9b32695a85f8e19f9c8f`
- Checked flash helper SHA256:
  `366dd38304625d37607916e92ea98a95271bbc4d9dfdc7eea106a5437b6dfe53`

## Transaction boundary

The live path is unavailable by default. It requires a final
`a90_native_init_f1_prepared_v2` manifest, `ready-for-f1-approval` status, the
exact manifest/orchestrator/run bindings, passed independent reviews, and an
exact private transaction directory.

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

## Validation

- Python compilation passed.
- The orchestrator suite passes `32/32`.
- The orchestrator, staging adapter, V3403 build, D3 handoff, and rootfs group
  passes `85/85`.
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
- The private draft inspection reports `device_contact=false` and
  `device_write=false`.
- A forced live invocation with the draft is rejected before creating either
  `staging-live` or `f1-live`.

## Remaining gate

The initial review is closed `NO_GO`; the remediation has not yet passed the
required independent re-review. The current private draft remains deliberately
non-approvable.

The remaining sequence is:

1. commit and independently re-review the exact changed staging/orchestrator
   closure;
2. repeat the exact connected read-only target and all-three-path preflight
   using the stable run-ID-derived stage path;
3. bind the passed review and refreshed D0 evidence into a final manifest;
4. host-inspect that exact final manifest; and
5. obtain one fresh exact F1 approval.
