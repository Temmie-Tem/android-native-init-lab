# V3442 S22+ HIGH Set-Only Gate Source Ready

## Verdict

`HOST_SOURCE_READY_POLICY_INACTIVE_NO_DEVICE_CONTACT`.

V3442 isolates the unresolved question: does the S22+ boot chain accept
`debug0x4948` as HIGH, clamp it, or reject the reboot request? It performs no
panic and sends no RDX/EUD/debug protocol command. No device contact, temporary
device file, reboot, debug-level change, or flash occurred in this host unit.

## Checked Helper

```text
path    workspace/public/src/scripts/revalidation/s22plus_v3442_high_set_only_live_gate.py
sha256  43aee96afee7542787a0a0d97a4f919e208516da96de0be281c848d047e4e8e2
schema  s22plus_v3442_high_set_only_live_gate_v1
```

## Setter

```text
source_sha256  288cbc53851ee6a29a9b0579d6868aa1cf1fbcb1c7a62cb2b10da9255ccd6339
setter_sha256  5bc230b87d090dcb694cd5eb68eb7e24a0ba5d8d9062cfada817953e5cc6f346
```

The stripped static AArch64 setter accepts only `high` or `mid`. Valid paths
perform argument reads and branches, load Linux reboot magic values and one
exact reason, then issue `__NR_reboot=142` as the first syscall. A returned
reboot syscall exits with status 70. Invalid input exits with status 64. There
are no filesystem, block-device, panic, RDX, or flash operations.

## Decision Matrix

| Observation after HIGH reboot | Classification | Cleanup |
| --- | --- | --- |
| sysfs `18760`, boot property `0x4948` | `HIGH_ACCEPTED` | dispatch MID, verify MID |
| either source alone reports HIGH | `HIGH_PARTIAL_OR_MIXED_ACCEPTANCE` | dispatch MID, verify MID |
| sysfs MID, no HIGH boot property | `HIGH_CLAMPED_OR_REJECTED_TO_MID` | no extra reboot |
| LOW or unknown | clamp/unknown | dispatch MID, verify MID |
| ADB never disappears | syscall returned/request rejected | verify MID, stop |
| Android does not return | HIGH boot-policy side effect | physical Download, V3441 rescue, second Download, Magisk rollback |

The experiment only answers HIGH acceptance. Even exact HIGH does not prove
that LCS PROD permits authenticated secure debug or that RDX will accept a
tokenless session.

## Recovery

Normal cleanup is zero-flash `debug0x494d` followed by exact MID Android
verification. The failure path reuses the live-proven V3441 boot-only rescue
artifact and exact Magisk boot rollback. Two emergency continuation modes cover
process interruption at either Download stage. Stock boot is transfer-failure
cleanup only and cannot produce PASS.

## Validation

```text
builder/helper py_compile                  PASS
focused unittest                          8/8 PASS
setter manifest and disassembly gates     PASS
single events timeline schema             PASS
inactive policy blocks all device modes   PASS
emergency recovery timeline               PASS
panic/RDX protocol strings absent         PASS
device contact                            false
```

## Policy State

The exact one-shot proposal is staged at
`docs/operations/S22PLUS_V3442_HIGH_SET_ONLY_AGENTS_EXCEPTION_DRAFT_2026-07-11.md`
as `DRAFT_INACTIVE`. A fresh explicit live approval is required to promote it.
