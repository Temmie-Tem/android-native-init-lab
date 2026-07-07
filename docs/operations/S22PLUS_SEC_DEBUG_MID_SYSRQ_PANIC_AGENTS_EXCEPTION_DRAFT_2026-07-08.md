# S22+ Sec Debug MID Sysrq Panic AGENTS Exception Draft (2026-07-08)

This is an inert draft. It does not authorize live work while it remains in
this document. Copy it into `AGENTS.md` only after explicit operator
authorization for the zero-flash Android sec_debug/debug_level positive control,
including the intentional kernel crash via sysrq-trigger-c and manual recovery.

## Copy Block

```text
   **Narrow operator-authorized exception (2026-07-08, S22+ sec_debug debug_level MID sysrq-panic zero-flash only):**
   after the S22+ DTBO+M13 no-hit and the host finding that Samsung `sec_debug`
   gated by `debug_level` is the likely retained-console path, Codex may perform
   one bounded attended zero-flash Android sec_debug positive-control run on the
   Samsung S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_sec_debug_mid_sysrq_gate.py`
   and live ack token `S22PLUS-SECDEBUG-MID-SYSRQ-PANIC-LIVE-GATE`.
   This exception authorizes no Odin flash, no partition write, no boot image
   write, no DTBO write, no vendor_boot write, no recovery/vbmeta/BL/CP/CSC/super/
   userdata/EFS/sec_efs/RPMB/keymaster/modem/bootloader write, no raw host `dd`,
   no fastboot, and no Magisk module install. The current boot partition must
   match the known-booting Magisk boot SHA256
   `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`.
   The operator must first set Samsung SysDump DEBUG LEVEL to MID if available
   (`debug_level=MID`; operator-set SysDump DEBUG LEVEL MID), then pass
   confirmation token `DEBUG_LEVEL_MID_SET_BY_OPERATOR` to the helper. The helper
   may write marker `S22_SECDEBUG_MID_SYSRQ_PANIC_CONTROL` to `/dev/kmsg` and
   `/dev/pmsg0` if present, write `1` to `/proc/sys/kernel/sysrq`, and write `c`
   to `/proc/sysrq-trigger` (`sysrq-trigger-c`) to cause one intentional kernel
   crash. After manual recovery, Codex may collect `/sys/fs/pstore`,
   collect /proc/last_kmsg, and read reset/sec_debug state through ADB root.
   The expected evidence is retained kernel panic/sec_debug/upload/ramdump log
   material or the marker in `/proc/last_kmsg`, pstore, or pmsg-derived retained
   state. If no retained evidence appears, stop and do not keep changing DTBO
   or M22 candidates under this exception. Manual recovery may be required.
```

## Gate Marker Coverage

The draft intentionally includes every authorization marker required by
`s22plus_sec_debug_mid_sysrq_gate.py`:

```text
S22+ sec_debug debug_level MID sysrq-panic zero-flash
workspace/public/src/scripts/revalidation/s22plus_sec_debug_mid_sysrq_gate.py
SM-S906N/g0q/S906NKSS7FYG8
2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
S22_SECDEBUG_MID_SYSRQ_PANIC_CONTROL
S22PLUS-SECDEBUG-MID-SYSRQ-PANIC-LIVE-GATE
DEBUG_LEVEL_MID_SET_BY_OPERATOR
debug_level=MID
operator-set SysDump DEBUG LEVEL MID
sysrq-trigger-c
intentional kernel crash
collect /proc/last_kmsg
no Odin flash
no partition write
manual recovery
```
