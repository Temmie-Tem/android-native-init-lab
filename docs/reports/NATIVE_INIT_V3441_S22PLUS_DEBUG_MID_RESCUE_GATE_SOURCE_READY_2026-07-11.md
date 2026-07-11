# V3441 S22+ Debug MID Rescue Gate Source Ready

## Verdict

`HOST_SOURCE_READY_POLICY_INACTIVE_NO_DEVICE_CONTACT`.

V3441 builds a boot-only emergency MID-restoration candidate before any future
Samsung sec_debug HIGH experiment. It does not authorize or perform HIGH. No
reboot, flash, ADB command, Odin command, debug-level change, or device write
occurred in this host unit.

## Recovery Flow

1. Start from the healthy Android/Magisk/MID baseline and verify exact boot,
   DTBO, recovery, rollback, and full FYG8 stock-firmware identities.
2. Flash one boot-only rescue AP.
3. The replacement PID1's first and only syscall requests
   `reboot(..., "debug0x494d")`; if it returns, PID1 parks.
4. The operator physically enters Download mode during the expected reboot
   loop.
5. Flash the exact Magisk boot-only rollback AP.
6. PASS only if Android, root, MID, and all baseline hashes return.

This rehearsal proves that the rescue AP is accepted and that the attended
Download-to-Magisk rollback route works. Because the rehearsal starts at MID,
it cannot by itself prove a HIGH-to-MID transition. That residual uncertainty
remains explicit and belongs to the separately authorized HIGH unit.

The reboot argument is not invented for V3441: the prior operator-set SysDump
MID run returned with `sys_boot_reason=reboot,debug0x494d` and live
`debug_level=18765`. V3441 reuses that observed canonical MID request from a
minimal PID1, while still requiring a live rescue rehearsal before relying on
it for HIGH recovery.

## Candidate Pins

```text
AP.tar.md5       25a8a5b5cfdeeebd47525c236d975561da8492bb08df5716cfa9da15e00ecfd6
boot.img         a41fa0be63628f04b8a832ab9c54cb943ed2ab379a4a58da79ef17904dff2295
boot.img.lz4     c158b1c2be81c6fa5242958e541c3dca43087dc104049dd45722c890c329bd34
raw /init        ea25969efca9308a28f18d8702465651205d7ee7503413ea40ab4396f01e6dda
assembly source  15996f265610964c8ea9768a9af84d549819e8bde9fb371d4b438a47f6398075
preserved kernel bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
Magisk base      2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
```

The AP contains exactly `boot.img.lz4`. A second independent build produced
the same AP hash. A no-change MagiskBoot unpack/repack of the base is byte
identical, and the candidate preserves the exact kernel.

## Raw PID1 Audit

The stripped static AArch64 ELF has exactly one `svc #0`. Before it, it only
loads Linux reboot magic values, `RESTART2`, the `debug0x494d` pointer, and
`__NR_reboot=142`. There is no call, stack use, or store before the syscall.
After a returned syscall it executes only `wfe` plus a backward branch. The
binary contains no `download`, `/dev/`, `/sys/`, `/proc/`, `/data/`, or dynamic
loader string.

## Live Helper

```text
path=workspace/public/src/scripts/revalidation/s22plus_v3441_debug_mid_rescue_live_gate.py
sha256=7cbfa449f8ce0c1f27f97455f0b796e15b4cea28c2f8d4139c11187d2ee4d5d7
schema=s22plus_v3441_debug_mid_rescue_live_gate_v1
```

The helper verifies the exact candidate and both boot-only rollback APs, plus
all six extracted FYG8 stock-firmware files. With the policy inactive, every
device-capable mode stops before ADB or Odin contact. Run state is durably
flushed, logs stay in the private run directory, ambiguous Odin targets fail
closed, and completed runs use only `events:[{name,timestamp_utc}]` with the
eight standard phases. Candidate transfer failure or a retained original Odin
endpoint triggers immediate rollback on that exact endpoint and remains
`NO_PROOF`; it cannot be promoted to rescue PASS.

## Policy State

The proposed one-shot clause is staged at
`docs/operations/S22PLUS_V3441_DEBUG_MID_RESCUE_AGENTS_EXCEPTION_DRAFT_2026-07-11.md`
as `DRAFT_INACTIVE`. It authorizes only the rescue rehearsal and mandatory
boot rollback. It explicitly excludes HIGH, panic, RDX, raw param writes, and
all non-boot flashes.

## Validation

```text
builder and helper py_compile          PASS
focused unittest                      12/12 PASS
candidate reproducibility             PASS
AP member gate                        PASS (boot.img.lz4 only)
kernel unchanged                      PASS
policy active                         false
device contact                        false
```

## Next Gate

Commit and independently review this exact source. Only a fresh explicit
operator approval may promote the draft clause and run the attended rescue
rehearsal. A HIGH experiment remains blocked until that live rescue rehearsal
passes and is retired.
