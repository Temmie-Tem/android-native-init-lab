# A90 V3403 Absent-Only Staging Adapter H0

Date: 2026-07-30 KST

Status:
`PASS_HOST_FIFTH_REMEDIATION_RE_REVIEW_PENDING_NO_LIVE_AUTHORITY`

## Scope

This unit implements and host-validates the SD rootfs staging boundary selected
after the V3403 immutable-source closure. It does not stage a device file,
flash, reboot, mount the Debian image, invoke `switch_root`, touch userdata, or
grant live authority.

The write-capable mode refuses the current private draft. It requires a final
`a90_native_init_f1_prepared_v2` manifest, status
`ready-for-f1-approval`, exact manifest and adapter hashes, the exact run ID,
an exact private parent-approval receipt and token, an exact private journal
path, and a fresh connected preflight before its first device write.

## Selected publication contract

The connected A90 reports `/mnt/sdext` as read-write ext4. The adapter therefore
uses one stable run-ID-derived, absent-only directory below
`/mnt/sdext/a90/runtime/`. The existing TCP transfer helper may publish only
the payload inside that exclusive directory. It never receives the final
rootfs path.

After exact payload size and SHA256 verification, the adapter:

1. rechecks the final rootfs path and V3403 fixed work path as absent;
2. requires payload and runtime root to share a filesystem;
3. creates the final name with BusyBox `ln`, without a force option;
4. proves payload and final have the same device/inode identity;
5. verifies final size and SHA256;
6. syncs, removes the temporary link and staging directory, syncs again, and
   reopens the final identity.

An existing final path makes `link(2)` fail without replacement. A failure
after link publication preserves the final path and records
`published_may_exist=true`; it never authorizes the candidate. Cleanup never
removes a published final and never uses recursive deletion.

## Exact implementation

- Adapter:
  `workspace/public/src/scripts/server-distro/a90_v3403_absent_only_staging.py`
- Size: `53141`
- SHA256:
  `f09ccd62da1b741e7eda7596bf9092e405553827100015ed1c7c366b49cca7b3`
- Tests:
  `tests/test_server_distro_a90_v3403_absent_only_staging.py`
- Inner payload transport:
  `workspace/public/src/scripts/revalidation/tcpctl_host.py`
- Inner transport SHA256:
  `032f3146ddc08af82f00881ae3d825066e843a41b194ee8d4c8cf09d1f3adb78`

The manifest-bound support closure contains exactly seven files: the D1
command wrapper, workspace bootstrap, bridge wrapper, serial lock, cmdv1
client, serial bridge, and private-evidence path helper. Candidate and rollback
remain exact boot-only inputs using the separately bound
`native_init_flash.py`.

The keyed rootfs remains:

- size: `2147483648`;
- SHA256:
  `36d49b9daf29166650482810a5c228075b9704692a593a1b6250d9610604ddde`;
- ext4 label: `A90D3ROOT`;
- `/root/.ssh/authorized_keys`: root-owned mode `0600`;
- pristine source SHA256:
  `16c504a8b1860fcc56272140b48d27a015bab1748b6c6be10fdb958bcdd7d749`.

## Validation

- Python compilation passed.
- The focused suite passes `31/31`.
- The new adapter plus V3403 build, D3 handoff, and D3 rootfs focused group
  passes `56/56`.
- The complete adapter/orchestrator/V3403 focused group passes `101/101`.
- Every declared prepublication fault leaves the final path absent.
- Every modeled postpublication fault preserves the exact final identity but
  keeps `candidate_allowed=false`.
- A preexisting final, work, or staging path fails before reservation.
- A final-path race is not overwritten.
- Source mutations replacing hard-link publication with `mv -f` or removing
  inode-identity proof are rejected.
- All five generated remote shell contracts pass `/bin/sh -n`.
- The connected D0 JSON must semantically prove one exact A90, exact V2321
  health, exact candidate/rollback/runner hashes, and no-write safety.
- The path-preflight JSON must semantically prove the exact final, work, and
  stable run-ID stage paths all absent.
- Every successful staging journal record carries the exact run ID and
  manifest SHA; the orchestrator accepts only the full contiguous success
  sequence.
- The staging result and each journal record are created mode `0600` even
  under umask `0002`; a final JSON name appears only after the complete
  temporary file has been written and `fsync`ed.
- An interrupted temporary journal write is ignored by sequence recovery
  because no incomplete `*.json` final name exists.
- Live staging reopens the exact private approval receipt, recomputes its full
  manifest/runner/artifact/D0/recovery binding, and requires the same fresh
  token passed by the parent orchestrator.
- No concrete USB-local device address remains in the tracked adapter or test
  closure.
- The static execution-order gate proves local closure validation, exact
  bridge and V2321 health, read-only path preflight, durable reserve/transfer
  records, payload verification, publish intent, hard-link publication, and
  candidate eligibility occur in that order.

The earlier connected read-only check passed on the exact A90 bridge:

- V2321 version/build exact;
- `selftest pass=11 warn=1 fail=0`;
- pstore `entries=0`;
- SD filesystem ext4 and read-write;
- required BusyBox applets present;
- final rootfs and fixed V3403 work path absent.

That evidence predates the stable run-ID stage path and therefore does not
satisfy the new three-path semantic gate. A fresh D0 check remains required.
No device write occurred during the earlier check.

## Second independent review remediation

The second independent review of commit
`581e5a14d6a6380c746d76d897768906d1e12bbe` returned `NO_GO`. Two findings
directly affected this adapter:

1. the final manifest still acted as its own live authorization rather than
   requiring a fresh operator approval receipt; and
2. `result.json` inherited umask `0002` through the older JSON helper and was
   then rejected by the parent as non-private.

The changed adapter now requires the exact parent-prepared approval token,
recomputes the complete binding locally, and creates its result and journal
with an exclusive private writer. The other two review findings—durable F1
journal publication and structured subprocess failures—are closed in the
orchestrator report. No live action was used to make or test these changes.

## Remaining gates

This unit is not an execution-ready F1 closure.

1. The second-remediated combined closure must pass independent re-review.
2. The exact target and all three absent paths must be refreshed with D0
   evidence for the stable run-ID stage path.
3. Only then may a final manifest replace the private draft.
4. One fresh approval must bind that final manifest and reviewed execution
   closure.

The current private draft is deliberately not approvalable and its hash must
not be used as live authority.
