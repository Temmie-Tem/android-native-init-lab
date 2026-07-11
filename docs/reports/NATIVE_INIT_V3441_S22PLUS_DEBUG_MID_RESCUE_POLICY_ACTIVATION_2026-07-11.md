# V3441 S22+ Debug MID Rescue Policy Activation

## Verdict

`ACTIVE_ONE_SHOT_NO_DEVICE_ACTION_YET`.

The operator gave fresh live approval on 2026-07-11 after commit `bae7f262`.
`AGENTS.md` now activates exactly one attended V3441 boot-only rescue
rehearsal. The exact helper SHA256 is
`7cbfa449f8ce0c1f27f97455f0b796e15b4cea28c2f8d4139c11187d2ee4d5d7`
and the exact candidate AP.tar.md5 SHA256 is
`25a8a5b5cfdeeebd47525c236d975561da8492bb08df5716cfa9da15e00ecfd6`.

Activation itself performed no ADB command, reboot, Odin command, flash,
debug-level change, or partition write. Candidate flash start consumes the
exception regardless of result. HIGH, panic, RDX protocol, raw parameter
writes, and every non-boot flash remain unauthorized.

## Required Live Outcome

The candidate must leave the original Odin endpoint, the operator must
physically re-enter Download mode during the expected MID reboot loop, and the
helper must restore the exact Magisk boot AP. PASS requires Android, Magisk
root, MID, known boot, stock DTBO, and stock recovery to return. A stock boot
fallback is cleanup only and cannot produce PASS.
