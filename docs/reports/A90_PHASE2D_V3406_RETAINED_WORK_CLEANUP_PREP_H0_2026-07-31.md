# A90 Phase 2D V3406 Retained-Work Cleanup Preparation

Date: 2026-07-31
Decision: `A90_PHASE2D_V3406_RETAINED_WORK_CLEANUP_PREP_H0_PASS`

Independent verdict: GO
Unresolved HIGH: 0
Unresolved MEDIUM: 0
Device actions by reviewer: none

## Blocker and preservation

The first V3406 connected attempt stopped before manifest preparation because
the fixed `d3-handoff-work.img` path was present. The connected D0 result
proved one exact A90, V2321 version/build, selftest `fail=0`, zero pstore
entries, and no device write, payload, flash, or reboot. The V3406 final and
stage paths were absent.

A subsequent bounded D0 read proved the retained file was one regular 2 GiB
file, mode `0600`, link count one, not mounted, and not used as loop backing.
Its SHA256 is:

```text
0beb73d3fbf5989f0dba19163d91f9dae2efeb20c103fd4ec2ed83dd6d4505e1
```

No identical host copy existed. One USB-local NCM read-only extraction then
received exactly `2147483648` bytes into a new private mode-`0600` file. The
host SHA256 equals the device SHA256. A final D0 stat proved the device file
still existed unchanged in type, size, mode, and link count.

The separately connected S22+ received no command.

## Cleanup closure

The previously reviewed one-shot retained-work helper now selects only the
exact V3406 display run profile. It binds:

- the fixed work path, exact 2 GiB size, mode `0600`, and the SHA256 above;
- the fresh connected-D0 result for the same V3406 run;
- one exact A90 target, bridge realpath digest, and USB serial digest;
- current connected-preflight helper path, size, and SHA256;
- exact V2321 health;
- the run-derived V3406 final source and stage paths; and
- the exact host preservation file with mode `0600`, link count one, size,
  and SHA256.

Immediately before dispatch it repeats target, bridge, health, work hash,
mount, loop-backing, adjacent-absence, and host-preservation checks. It writes
fsynced intent and dispatch records before one non-recursive
`/bin/busybox rm --` command. Unsafe transport retry is disabled.

After dispatch, response loss permits only presence and health reads. The
unlink is never retransmitted. Unproved absence or unproved post-cleanup
V2321 health closes as `STOP_NO_RETRY_*`, not PASS.

## Reviewed identities and validation

```text
helper  87fce4fac85dc30b05b45e7d097ed722cb7c31cc46386938148c4e49fc3638bf
tests   69e449d13f6a7b74f95679c88e4e069b06b8c997178499df8f1e18cd7bcb7d38
```

- focused cleanup tests: `17/17 PASS`
- integrated Phase 2 regression: `187/187 PASS`
- Python `py_compile`: PASS
- `git diff --check`: PASS
- independent safety review: GO, zero unresolved High or Medium findings

Historical internal journal schema names retain their V3405 provenance. They
do not select the live profile; exact V3406 run IDs, paths, hash, manifest,
and approval binding do.

## Authority

No cleanup approval receipt exists and no unlink has been dispatched. This
report permits committing the reviewed helper and preparing one host-only
exact cleanup approval receipt. The persistent unlink still requires one
fresh exact D1 approval token.
