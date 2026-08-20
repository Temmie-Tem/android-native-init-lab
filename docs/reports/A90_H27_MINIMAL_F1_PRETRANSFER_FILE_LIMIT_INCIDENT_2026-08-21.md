# A90 H27 minimal F1 pre-transfer file-limit incident — 2026-08-21

## Disposition

`NO_PROOF_OBSERVER / RECOVERY_REQUIRED`, with the candidate attempt consumed and
candidate replay forbidden. No candidate or rollback bytes were transferred to
the boot partition.

## What happened

The exact healthy H24 resident passed the prepared and approval gates. The
candidate helper then requested the reviewed Native-to-TWRP transition and
bound the single new A90 recovery endpoint. Before `adb push`, boot write, or
boot readback, the helper tried to create its private verified sealed copy of
the 58,368,000-byte candidate. The adapter had inherited
`RLIMIT_FSIZE=1 MiB`, intended to bound stdout/stderr, so that local sealed-copy
write failed with `EFBIG` (`File too large`).

The owner durably recorded a failed candidate result and entered its one-shot
rollback branch. That helper stopped before transfer because the ADB baseline
already contained the causally bound recovery endpoint. The run closed
`RECOVERY_REQUIRED / ROLLBACK_HEALTH_UNPROVED`; neither helper reached
`adb_push`, `boot_dd_write`, or `boot_readback_sha256`.

The operator used the physical TWRP **Reboot > System** path. Fresh sequential
read-only observation then proved the unchanged H24 resident:

- version `0.11.192` and build
  `phase3-minimal-h24-ufs-auth-native-hud-private-card-root-minimal-debian-dev`;
- self-test `pass=11 warn=1 fail=0`;
- `BOOT OK`, exact serial bridge ready, and pstore `entries=0`.

The separately connected Samsung endpoint remained outside the selected A90
transport and received no command.

## Root cause and repair boundary

One process-wide file-size limit incorrectly combined two different bounds:

1. a boot-sized local sealed scratch file required by `native_init_flash.py`;
2. bounded command stdout/stderr accepted by the adapter.

The repair gives the child a fixed 64-MiB per-file ceiling, sufficient for the
allowlisted A90 candidate and rollback sealed copies, while retaining the
existing 1-MiB post-exit acceptance limit independently for each stdout/stderr
log. Focused hostile tests require a 58,368,000-byte scratch write to succeed
and a 1-MiB-plus-one stdout file to remain rejected.

This repair is H0 only until the changed execution closure receives a fresh
independent `PASS_GO`. The consumed run and approval are never reused. Any
future device attempt requires a new run ID, fresh healthy preflight, fresh
approval, and the normal one-shot F1 sequence.
