# Native Init V3356 Self-dd Content-Change Design

- Cycle: `V3356`
- Decision: `design-only-content-changing-self-write-ladder`
- Scope: post-E5 design for proving a real new-image self-write without immediately adopting it as
  the default flash path.
- Device action: none.
- Flash/rollback: none.

## Context

V3355 E5 proved that normal-boot PID1 can stream-write the entire 64MiB boot partition when every
byte is written back identically. That closes the write-permission question for identity writes, but
it does not prove a content-changing fast flash. A real new-image self-write intentionally leaves
the boot partition in a different byte state and therefore needs a separate ladder.

## Design Added

The design spec now has `§12. Content-changing self-write ladder (post-E5 design)`.

The proposed rungs are:

- `F0 source-plan`: read-only staged-image validation and target SHA planning; no write.
- `F1 paired content-change roundtrip`: write a 64MiB `target.full` built by overlaying the staged
  candidate boot image on a device-captured `before.full`, verify it, then restore `before.full` in
  the same boot before any system reboot.
- `F2 boot into self-written candidate`: after F1 passes, write and verify the target image, reboot
  to system, and prove the self-written candidate boots.
- `F3 self-rollback`: from the self-written candidate, write a v2321 target image from native-init,
  verify it, reboot, and prove v2321 returns.
- `F4 opt-in host integration`: only after F0..F3 pass, add an explicit experimental host path;
  `native_init_flash.py` through TWRP remains the default and recovery-grade path.

## Key Safety Choice

The first content-changing write does not boot the changed image. F1 writes changed bytes, verifies
the full-partition target SHA, then restores the exact previous 64MiB boot snapshot and verifies the
original full SHA before any reboot. This proves byte-changing write mechanics while keeping the
first reboot after the probe pointed at the original boot bytes.

## Policy Boundary

`AGENTS.md` still names `native_init_flash.py` as the checked flash helper. The new section records a
policy gate: content-changing self-write remains design-only until the operator deliberately amends
the policy for this boot-partition-only experiment. The helper remains the fallback for recovery and
the default flash path until the full ladder passes.

## Next Bounded Unit

Implement F0 only:

- no boot-partition writes;
- no reboot into a new image;
- validate staged candidate SHA/version/header/size;
- compute `before_full_sha`, `candidate_sha`, `target_full_sha`, and a changed-chunk summary;
- report `would_write=0`.

F0 can be built and live-tested as a read-only candidate through the existing checked-helper flash
gates. F1 should remain blocked until F0 passes and the policy gate is resolved.
