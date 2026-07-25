# S22+ FYG8 P2.63 E3 candidate F1 approval ready

Date: 2026-07-25 KST
Tiers: H0 and connected read-only D0
Status: `PASS_P263_E3_CANDIDATE_F1_APPROVAL_READY`
F1 authority: none

## Result

One fresh P2.60 v3 intent was derived after the artifact-safety contract
correction. The exact two-link userspace and entrypoint closure passed before
kernel qualification.

Two clean Full-LTO builds completed:

| Build | Wall time | Peak RSS | Process swaps |
|---|---:|---:|---:|
| A | `38:25.60` | `24,252,940 KiB` | `0` |
| B | `39:03.99` | `24,252,792 KiB` | `0` |

`Image`, `vmlinux`, `.config`, `System.map`, `vmlinux.symvers`, and `abi.xml`
were byte-identical across A and B. The exact P2.60 linked audit passed against
the final Full-LTO output.

Two deterministic candidate builds produced byte-identical `boot.img`,
`boot.img.lz4`, boot-only Odin AP, and artifact result. Each AP contains exactly
one regular member named `boot.img.lz4`. The corrected P2.60 artifact metadata
records the bounded peripheral-role and CDC-ACM configfs authority and does not
make the historical no-sysfs/configfs-write claim.

The independent artifact closure and offline Process v2 promotion passed.
Ready-manifest validation and live-plan rendering also passed with candidate
execution disabled and exact rollback preapproved.

## Connected D0

The first connected read-only preparation stopped because `/proc/last_kmsg`
still contained a historical E2 marker family. It created no approval record,
invoked no Odin session, requested no reboot, and transferred no partition.

One previously authorized normal Android reboot rotated that retained baseline
out. A new run directory then passed D0 and bound:

- one exact healthy FYG8 Android target;
- root, boot, and supporting-partition health;
- no Download/Odin endpoint;
- a clean retained baseline;
- the exact candidate and known-good Magisk rollback APs; and
- the current reusable execution-critical source closure.

The prepared record states `device_writes=false`, `odin_invoked=false`,
`partition_transfer=false`, `f1_authorized=false`, and
`live_authorized=false`. The fresh exact approval token and private target
evidence remain only under `workspace/private/`.

## Build-Line Findings

The earlier v2 A/B pair had already completed. It was invalidated only because
the post-build package audit found a false safety claim: P2.60 performs bounded
sysfs/configfs writes, while the generated metadata still claimed no such
writes. Correcting the exact-source-contract selector changed a source receipt
and therefore the candidate identity, which forced the final v3 A/B pair. This
was a late host-contract failure, not unfinished design or implementation.

Two host-only recurrence controls were added to the qualification runbook:

1. transfer and rehash the complete immutable intent directory, including
   `materialized-sources/`, instead of copying a hand-selected subset; and
2. serialize output-producing post-build helpers with nonblocking `flock`, then
   validate an existing complete output rather than trying to overwrite it.

No source, kernel, or candidate input changed after the v3 pair. Neither
post-build issue justified or triggered another Full-LTO build.

## Next Action

The only next device action is one exact F1 approval for the prepared private
binding. After that approval, Process v2 permits one boot-only P2.60 E3
candidate attempt and its already-bound mandatory rollback. No candidate or
rollback transfer has occurred in this unit.
