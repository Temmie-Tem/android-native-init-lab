# S22+ V3443R Corrected HIGH Panic Comparison Exception Draft

`DRAFT_INACTIVE` - this proposal authorizes no device contact, debug-level
change, panic, USB command, reboot, flash, or recovery action.

## Proposed AGENTS.md Clause

**Narrow operator-authorized exception (2026-07-11, S22+ V3443R corrected
HIGH panic MID-control comparison live gate):** after V3443 failed closed
before panic because ADB split the compound root command, Codex may perform one
bounded attended zero-candidate-flash comparison on Samsung S22+
`SM-S906N`/`g0q` `S906NKSS7FYG8` using only checked helper
`workspace/public/src/scripts/revalidation/s22plus_v3443_high_panic_compare_live_gate.py`
SHA256 `8d66d9e1766eac674589ac77b0ea7c82b5243274cc502b3cbd20bcfb09e8192c`.
The active clause must contain
`S22PLUS_V3443R_HIGH_PANIC_COMPARE_POLICY_STATE=ACTIVE` and requires fresh
acknowledgements `S22PLUS-V3443R-HIGH-ONE-SYSRQ-PANIC`,
`S22PLUS-V3443R-RDX-PREAMBLE-ONLY`, and
`S22PLUS-V3443R-MID-RESTORE-RECOVERY`.

Before device contact, the helper must verify pinned V3440 MID control
`result.json` SHA256
`62a6d12adb5ab33f39d9d44078de09f6180a39980b417dadf1fe9a598acd7dbe`,
retained log SHA256
`a397d9688e740bc03bead8c4fd2fcc667910cfe98d2f92252a36b474e66a5b04`,
and preamble response SHA256
`3a4a3980e7835ebb77c927b99863e01847086171bdb81773e81e06f2192ab60c`.
It must prove the MID marker, SysRq panic, RDX lock, upload cause, exact
NegativeAck, and no probe or transfer. Live preflight must prove exact MID
Android/Magisk root, known boot, stock DTBO/recovery, PyUSB, and recovery
artifacts.

The helper may stage only exact setter SHA256
`5bc230b87d090dcb694cd5eb68eb7e24a0ba5d8d9062cfada817953e5cc6f346`,
dispatch HIGH once, and require exact `18760` / `0x4948`. Before arming panic,
it must execute harmless read-only compound command `id; id` through one remote
ADB shell argument protected with `shlex.quote`. Both lines must be
`uid=0(root)` and any `uid=2000(shell)` or nonzero return stops before marker or
SysRq.

Only after that control passes may the helper emit one marker to `/dev/kmsg`,
write `1` once to `/proc/sys/kernel/sysrq`, and write `c` once to
`/proc/sysrq-trigger`. It may observe USB for at most 120 seconds. Only for one
exact Samsung RDX `04e8:685d` endpoint may it send exactly `PrEaMbLe\0` and read
one bounded packet. `PrObE forbidden`; `DaTaXfEr forbidden`. Every response or
error stops before another command. qdl, Sahara, Firehose, memory ranges, RAM
reads, probe tables, and dump transfer are forbidden.

The operator must physically use RDX EXIT only after host observation
completion. On HIGH Android return, the helper may collect `/proc/last_kmsg`,
compare bounded metrics against the pinned MID control, then must dispatch MID
once. PASS requires final MID `18765` / `0x494d`, Android/Magisk root, and exact
boot/DTBO/recovery hashes. HIGH dispatch and panic each consume the exception
regardless of result and cannot be retried.

If HIGH Android does not return, attended recovery may flash only exact V3441
MID-rescue boot AP SHA256
`25a8a5b5cfdeeebd47525c236d975561da8492bb08df5716cfa9da15e00ecfd6`,
then after a second physical Download entry exact Magisk boot rollback AP
SHA256 `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`.
Exact stock boot fallback AP SHA256
`2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94`
is cleanup-only if Magisk transfer fails with one Odin endpoint. No emergency
path may redispatch HIGH or panic.

This exception authorizes no candidate flash, RAM dump, device-memory write,
partition-table action, recovery/vendor_boot/DTBO/vbmeta/BL/CP/CSC/super/
userdata/persist/EFS/sec_efs/RPMB/keymaster/modem/bootloader flash, raw host
`dd`, fastboot, Magisk module, EUD/UART write, LCS/fuse/QFPROM change, raw
parameter action, format data, native-init candidate, or A90 action. Timeline
must use only `events:[{name,timestamp_utc}]` with all eight phases.
`S22+ V3443R corrected HIGH panic MID-control comparison live gate` is the
policy marker.
