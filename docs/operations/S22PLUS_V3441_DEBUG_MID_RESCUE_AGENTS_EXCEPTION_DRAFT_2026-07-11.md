# S22+ V3441 Debug MID Rescue Exception Draft

`DRAFT_INACTIVE` - this document is a policy proposal only. It authorizes no
device contact, reboot, flash, debug-level change, or partition write.

## Proposed AGENTS.md Clause

**Narrow operator-authorized exception (2026-07-11, S22+ V3441 debug MID
rescue boot-only live gate):** before any attempt to force Samsung sec_debug
from MID to HIGH, Codex may perform one bounded attended boot-partition-only
recovery rehearsal on the Samsung S22+ `SM-S906N`/`g0q`
`S906NKSS7FYG8` using only the checked helper
`workspace/public/src/scripts/revalidation/s22plus_v3441_debug_mid_rescue_live_gate.py`
SHA256 `7cbfa449f8ce0c1f27f97455f0b796e15b4cea28c2f8d4139c11187d2ee4d5d7`.
The active clause must contain sentinel
`S22PLUS_V3441_DEBUG_MID_RESCUE_POLICY_STATE=ACTIVE`, and the operator must
supply acknowledgement `S22PLUS-V3441-DEBUG-MID-RESCUE-LIVE`. Emergency
rollback-only use requires separate acknowledgement
`S22PLUS-V3441-DEBUG-MID-RESCUE-ROLLBACK`.

The candidate AP.tar.md5 SHA256 must be
`25a8a5b5cfdeeebd47525c236d975561da8492bb08df5716cfa9da15e00ecfd6`;
the contained padded boot image SHA256 must be
`a41fa0be63628f04b8a832ab9c54cb943ed2ab379a4a58da79ef17904dff2295`;
the AP must contain exactly one member, `boot.img.lz4`, whose SHA256 is
`c158b1c2be81c6fa5242958e541c3dca43087dc104049dd45722c890c329bd34`.
The raw replacement `/init` SHA256 must be
`ea25969efca9308a28f18d8702465651205d7ee7503413ea40ab4396f01e6dda`,
built from source SHA256
`15996f265610964c8ea9768a9af84d549819e8bde9fb371d4b438a47f6398075`.
The candidate must preserve the known Magisk boot kernel SHA256
`bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff`
and be derived in place from known-booting Magisk boot SHA256
`2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`.

Before candidate flash, the helper must verify exactly one boot-complete
Android target, Magisk `uid=0`, debug level MID decimal `18765`, the exact
known Magisk boot hash above, stock DTBO SHA256
`97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`,
stock recovery SHA256
`93fac06ca79bf4b365b25a8d49902bc41aba112ea253c30880c90e314d7895d4`,
both boot-only rollback APs, and the full FYG8 stock-firmware evidence required
by `docs/operations/S22PLUS_FYG8_STOCK_FIRMWARE_EVIDENCE_POLICY_2026-07-08.md`.

The candidate may only replace the boot ramdisk `/init`. Its first and only
intended syscall is raw AArch64
`reboot(LINUX_REBOOT_MAGIC1, LINUX_REBOOT_MAGIC2,
LINUX_REBOOT_CMD_RESTART2, "debug0x494d")`. If that syscall returns, it may
only park in a `wfe` loop. Repeated boots may repeat the idempotent MID request.
It may not emit a marker, mount a filesystem, open a device, load a module,
touch USB/configfs/watchdog, start Android, or write a block device.

After candidate transfer, the original Odin endpoint must disconnect. The
operator must then physically enter Download mode while the candidate reboot
loop is active. The helper must immediately flash the pinned Magisk boot-only
rollback AP SHA256
`d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`,
then require Android, Magisk root, MID, and the exact boot/DTBO/recovery hashes
to return. If Magisk rollback transfer fails while Download remains available,
the helper may flash only the pinned FYG8 stock boot-only fallback AP SHA256
`2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94`
whose decompressed stock boot SHA256 is
`4150b962314e6136acba61b20f471d6ee1c418b83cf8c3ee4d9cf7c91a3640ae`,
then require non-root stock Android to return and stop; that fallback is
cleanup, not PASS. The candidate plus verified
Magisk rollback is the only PASS.

If candidate transfer fails or the original Odin endpoint never disconnects,
the helper must use that still-present single endpoint for immediate boot
rollback. Such a run is `NO_PROOF` even when Magisk Android returns. Ambiguous
or absent rollback targets stop without guessing a device.

This exception does not authorize setting HIGH or LOW, `debug0x4948`, an
intentional panic, SysRq, RDX protocol commands, raw `/param` access,
`sec_param_set`, recovery/vendor_boot/DTBO/vbmeta/BL/CP/CSC/super/userdata/
persist/EFS/sec_efs/RPMB/keymaster/modem/bootloader flash, raw host `dd`,
fastboot, Magisk modules, multidisabler, format data, or any A90 action. It is
one-shot and must be retired after PASS or attempted candidate flash. A future
HIGH experiment requires a separate design, exact artifact/source pins, and a
fresh narrow exception. `S22+ V3441 debug MID rescue boot-only live gate` is
the policy marker.
