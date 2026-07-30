# A90 V3403 Minimal F1 Orchestrator H0

Date: 2026-07-30 KST

Status:
`PASS_HOST_IMPLEMENTED_REVIEW_PENDING_NO_LIVE_AUTHORITY`

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
- Size: `54219`
- SHA256:
  `566c254c06b1b30e8ed45520216867a0bcd7dca36cf035ddf0b7f94b4036ecef`
- Focused tests:
  `tests/test_server_distro_a90_v3403_f1_orchestrator.py`
- Staging adapter SHA256:
  `9cc9bc2eb77e4c6ec7b3cbf0e8d978bc051a9a1b3410a716e75d0773c7a486b2`
- Checked flash helper SHA256:
  `366dd38304625d37607916e92ea98a95271bbc4d9dfdc7eea106a5437b6dfe53`

## Transaction boundary

The live path is unavailable by default. It requires a final
`a90_native_init_f1_prepared_v2` manifest, `ready-for-f1-approval` status, the
exact manifest/orchestrator/run bindings, passed independent reviews, and an
exact private transaction directory.

The orchestrator performs only this sequence:

1. reopen the complete local closure;
2. consume an exact, durably closed staging result;
3. recheck the exact bridge and healthy V2321 baseline;
4. record candidate intent before invoking the candidate helper once;
5. observe the V3403 source/work-copy markers and Debian PID1 over USB-local
   SSH;
6. wait for the bounded return to V3403;
7. record rollback intent before invoking the exact V2321 helper once; and
8. require exact V2321 health before closing.

Recovery contains no candidate route. If candidate intent exists without a
rollback-intent record, recovery can invoke only the rollback. If rollback
intent already exists but completion is missing, recovery never reinvokes it;
it can close only when read-only checks prove the exact V2321 final health.

An attended TWRP recovery route additionally requires a manifest-bound digest
of the recovery ADB serial. The raw value remains private and is never written
to tracked evidence.

## Validation

- Python compilation passed.
- The orchestrator suite passes `28/28`.
- The orchestrator, staging adapter, V3403 build, D3 handoff, and rootfs group
  passes `78/78`.
- Every modeled candidate-intent failure selects rollback-only recovery.
- A previously started rollback is never invoked twice.
- Ordered failure timelines remain canonical without inventing completion
  events.
- A candidate command cannot appear in the recovery source closure.
- Both transfer commands bind only the manifest candidate or rollback `boot`
  image and reject unpinned operation.
- A staging result is accepted only with its exact durably closed staging
  journal.
- The private draft inspection reports `device_contact=false` and
  `device_write=false`.
- A forced live invocation with the draft is rejected before creating either
  `staging-live` or `f1-live`.

## Remaining gate

This is implemented but not independently reviewed. The current private draft
is deliberately non-approvable.

The remaining sequence is:

1. independently review the combined staging and orchestrator execution
   closure;
2. bind the exact recovery-ADB serial digest and reviewed hashes;
3. promote a final manifest;
4. repeat the exact connected read-only target/path preflight; and
5. obtain one fresh exact F1 approval.
