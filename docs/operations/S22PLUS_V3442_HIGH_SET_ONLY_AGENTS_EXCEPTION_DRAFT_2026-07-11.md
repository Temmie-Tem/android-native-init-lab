# S22+ V3442 HIGH Set-Only Exception Draft

`DRAFT_INACTIVE` - this proposal authorizes no device contact, temporary file
write, reboot, debug-level change, flash, panic, or protocol command.

## Proposed AGENTS.md Clause

**Narrow operator-authorized exception (2026-07-11, S22+ V3442 HIGH set-only
live gate):** after V3441 proved the attended MID rescue boot and Magisk
rollback route, Codex may perform one bounded attended HIGH acceptance
discriminator on Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using only
checked helper
`workspace/public/src/scripts/revalidation/s22plus_v3442_high_set_only_live_gate.py`
SHA256 `43aee96afee7542787a0a0d97a4f919e208516da96de0be281c848d047e4e8e2`.
The active clause must contain
`S22PLUS_V3442_HIGH_SET_ONLY_POLICY_STATE=ACTIVE`. Live requires acknowledgement
`S22PLUS-V3442-HIGH-SET-ONLY-LIVE`; interrupted recovery from a HIGH-state
Download endpoint requires `S22PLUS-V3442-HIGH-RECOVERY-FROM-DOWNLOAD`; direct
Magisk rollback after V3441 rescue requires
`S22PLUS-V3442-MAGISK-ROLLBACK-FROM-DOWNLOAD`.

The raw setter SHA256 must be
`5bc230b87d090dcb694cd5eb68eb7e24a0ba5d8d9062cfada817953e5cc6f346`,
built from source SHA256
`288cbc53851ee6a29a9b0579d6868aa1cf1fbcb1c7a62cb2b10da9255ccd6339`.
It accepts only `high` or `mid`; a valid path's first syscall is
`reboot(RESTART2, "debug0x4948")` or
`reboot(RESTART2, "debug0x494d")`. It contains no filesystem, block, panic,
RDX, or flash syscall. Before HIGH dispatch the helper must verify the exact
MID Android/Magisk baseline, known boot, stock DTBO/recovery, complete FYG8
stock evidence, and all V3441/Magisk/stock boot recovery pins.

The helper may remove, push, chmod, hash, execute, and finally remove only
`/data/local/tmp/s22plus_v3442_debug_level_setter`. It may dispatch HIGH exactly
once. If Android returns, it may only read model/device/bootloader, boot
completion, root identity, `/sys/module/sec_debug/parameters/debug_level`,
`ro.boot.debug_level`, `ro.boot.bootreason`, and boot/DTBO/recovery hashes. It
must classify HIGH as accepted, mixed, clamped to MID/LOW, unknown, or reboot
syscall returned. Any sysfs or boot-property HIGH evidence requires one MID
restore dispatch and exact MID Android revalidation. No second HIGH request is
allowed.

If Android does not return within the bounded HIGH observation window, the
operator may physically enter Download mode. The helper may then flash only
the exact V3441 MID rescue boot AP SHA256
`25a8a5b5cfdeeebd47525c236d975561da8492bb08df5716cfa9da15e00ecfd6`,
wait for its endpoint to disconnect, require a second physical Download entry,
then flash only exact Magisk boot AP SHA256
`d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`.
If Magisk transfer fails while one Odin endpoint remains, the existing exact
FYG8 stock boot fallback AP SHA256
`2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94`
may be used as cleanup only. Recovery PASS requires Android, Magisk root, MID,
known boot, stock DTBO, and stock recovery to return.

HIGH dispatch consumes this exception regardless of result. This exception
does not authorize panic, SysRq, RDX/S-Boot USB commands, EUD writes, LCS/fuse/
QFPROM changes, raw `/param` access, `sec_param_set`, recovery/vendor_boot/DTBO/
vbmeta/BL/CP/CSC/super/userdata/persist/EFS/sec_efs/RPMB/keymaster/modem/
bootloader flash, raw host `dd`, fastboot, Magisk modules, multidisabler,
format data, or any A90 action. `S22+ V3442 HIGH set-only live gate` is the
policy marker.
