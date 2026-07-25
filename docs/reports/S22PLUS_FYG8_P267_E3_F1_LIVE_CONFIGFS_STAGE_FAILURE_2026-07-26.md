# S22+ FYG8 P2.67 E3 F1 live configfs-stage failure

Date: 2026-07-26 KST
Tier: F1
Status: `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`
Transaction: `CLOSED`
Recovery required: false

## Result

One exact P2.60 v3 E3 candidate and one exact Magisk rollback were transferred
under one prepared Process v2 binding. The operator observed a successful
candidate boot and no boot loop.

The typed host ACM observer reached its bounded endpoint deadline without
finding the candidate interface. Its transient host guard was released and
removed. No ACM banner was accepted.

Two post-rollback retained reads are byte-identical and contain one exact
terminal-failure record:

```text
generation 80: stage=0x87 item=11 outcome=progress detail=0
generation 81: stage=0x88 item=0  outcome=failure  detail=5
classification: E2_FAILURE_OBSERVED
```

The record has one exact family and one exact record. It has zero integrity
issues, foreign families, historical families, fallback records, UNSAT
records, delimiter mismatches, and partial-head or partial-tail records.

Stage `0x87`, item 11 again proves exact membership of:

```text
/sys/class/udc/a600000.dwc3
```

The P2.60 source contract maps stage `0x88`, item 0 to the first E3-local
operation, `p260_mount_configfs()`. E3 did not reach gadget creation, `ttyGS0`,
banner queueing, role selection, UDC binding, host enumeration, or configured
state.

## Post-Live Root Cause

The stage implementation contains a deterministic filesystem-magic defect:

```c
#define P260_CONFIGFS_MAGIC 0x62656572L
```

`0x62656572` is the Linux sysfs magic. Linux configfs defines its magic as
`0x62656570` in `fs/configfs/mount.c`:

<https://android.googlesource.com/kernel/common/+/a7cce099450f8fc597a6ac215440666610895fb7/fs/configfs/mount.c>

After mount and `statfs`, the candidate requires exact equality with the wrong
constant:

```c
return probe.f_type == P260_CONFIGFS_MAGIC ? 0 : -EIO;
```

A correctly mounted configfs therefore cannot pass this candidate's stage
`0x88` validator. This is a sufficient source-level blocker and must be fixed
before another E3 candidate.

The retained ABI carries only errno-form detail 5. `p260_mount_configfs()`
also forwards direct mount and `statfs` errors. This record therefore does not
prove that the wrong-magic comparison was the unique runtime producer of
`EIO`; it proves the configfs stage failed. The source defect independently
proves that the candidate was incapable of accepting a correct configfs
result.

The existing source contract pinned the runtime include by SHA and checked
that configfs operations existed, but it did not semantically compare the
magic against the authoritative filesystem definition. That is the narrow
static-validation gap.

## Rollback Recovery Deviation

The exact rollback transfer returned `odin_transfer_completed`, and the
durable journal reached `ROLLBACK_FLASHED`. The initial execution process then
stopped fail-closed while measuring the final USB endpoint inventory:

```text
measured USB endpoint inventory failed
```

No candidate or rollback transfer was repeated. Process v2 recovery reopened
the existing transaction at `ROLLBACK_FLASHED`, reconciled the completed
rollback, and performed only final health and retained-evidence verification.

## Final Verification

Final evidence proves:

- candidate transfer completed once;
- rollback transfer completed once;
- Android boot complete and boot animation stopped;
- expected FYG8 kernel and Magisk-root boot identity;
- root, boot, recovery, vendor-boot, and DTBO health;
- Odin endpoint absence;
- two byte-identical full retained reads;
- transaction state `CLOSED`; and
- all eight canonical timeline events in order.

```text
candidate_completed=true
rollback_completed=true
candidate_observer_accepted=false
final_verified=true
marker_accepted=false
recovery_required=false
```

The candidate did not prove E3. The previous P2.58A E2 terminal proof remains
valid and this run independently reproduced its real-UDC frontier.

## Disposition

The binding and approval are consumed. No S22+ F1 authority remains.

The next bounded unit is H0 only:

1. replace the configfs magic with `0x62656570`;
2. add a semantic source-contract regression that distinguishes configfs from
   sysfs magic and fails under mutation;
3. update the source receipt and run focused static validation; and
4. derive fresh qualified artifacts, D0 evidence, and approval before any
   later F1.

Do not widen the correction into gadget, role, PHY, or host-observer changes.
Those paths were not reached by this candidate.
