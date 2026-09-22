# S22+ P402: installed root matches, healthy Android return

Date: 2026-09-23 KST (2026-09-22 UTC). Target: `SM-S906N/g0q/S906NKSS7FYG8`.

The attended P402 `v0.4.0-rc.2` inspection completed on the actual Samsung
device with `PASS_INSPECTION_COMPLETED` and
`COMPLETE_RECORD_BOOT_INPUTS_MATCH`. The installation start/completion records
and original witness were present. All 8,969 expected archive entries matched,
including all 8,175 boot-input entries, with zero missing, metadata or content
mismatches. This establishes the root's observed state in P402; it does not
relabel P401's consumed NO_PROOF result or establish Debian execution.

The terminal is `ANDROID_CLOSED_HEALTHY`, `recovered=true`. One read-only
health continuation followed a failed first Android root/hash read; no boot
transfer or inspection was repeated. The final bracket proves rooted original
Android, exact boot/supporting partition hashes, unchanged complete GPT and
Android32 statfs total 34,357,624,832 bytes. The final Android boot differs from
the execution-start boot. The F1 owner is retired, the one-operation budget is
consumed, and the finite grant is closed.

## Actual inspection and proof boundary

The exact native partition was protected by its kernel RAM read-only policy
before mounting. The identified ext4 superblock was clean, with no RECOVER bit
or orphan head. The protected read-only mount, marker/witness reads, bounded
metadata/content comparisons, ordinary unmount and cleanup all completed.
The complete superblock and GPT readbacks remained identical. There was no
filesystem write, extraction, repair, chroot or execution of an installed file.

| Observation | Result |
| --- | --- |
| Expected archive closure | 8,969 matched; zero missing or mismatched |
| Boot-input subset | 8,175 entries; zero missing or mismatched |
| Known regular-file content hashed | 199,362,324 bytes |
| Bounded tree | 8,973 entries: 1,005 directories, 6,822 regular files, 1,146 links |
| Installation records and witness | Start, completion and witness all present |
| Partition protection / mount / unmount | All proved |
| Inspection output | 705 stdout bytes; empty stderr |
| Debian process / host PID 1 / SSH | Not executed or proved by this inspection |

The filesystem-wide tree observation and expected-archive comparison are
separate. The comparison checks the retained archive's defined metadata,
regular-file hashes and link targets; it is not a whole-partition image hash
or proof of all possible filesystem properties. The completed root observation
narrows the unresolved boot problem beyond missing or mismatched expected
rootfs files. It does not localize P401's missing NCM endpoint to init handoff,
userspace, USB service, or any other particular stage.

## Canonical journal-derived timeline

Times are seconds from the original 1800-second grant opening, which retained
the operator's actual returned start statement. Intent and completion remain
distinct; all device commands came from the reviewed fixed owner.

| Elapsed | Event | Evidence boundary |
| ---: | --- | --- |
| 7.267 | Fresh execution preflight complete | Exact rooted original-A health |
| 7.427–11.066 | Android Download request and departure | One control intent/result |
| 21.041–22.536 | P402 transfer | One candidate claim and completed Odin capture |
| 38.036–40.857 | Fixed protected root inspection | One pre-EXEC intent, authenticated raw result and DETACH |
| 42.272–42.866 | Same-boot native Download return | Fresh health, CONTROL and measured departure |
| 48.880–50.415 | Original-A transfer | One exact completed transfer |
| 91.693 | First final-health read stopped | Completed root/hash read returned target-not-found |
| 91.746–98.686 | Health-only continuation | Full rooted health/GPT/statfs brackets passed |
| 228.764 | Finite grant closed after H0 audit | Raw evidence rederived; owner absent, no further device action |

No physical Download intervention was needed. There were one N transfer, one
original-A transfer, one inspector execution and zero additional recovery
transfers. P402 received no reusable native admission. No A90 or S20+ target
command was issued.

## First Android read and continuation

After original A had already transferred, Android readiness was observed. The
initial inventory, devpath and property reads succeeded, but the following
root/hash read returned exit 1 with target-not-found diagnostics and empty
stdout. Its capture reports no timeout, overflow or producer error. The cause
of that brief absence is not established.

The existing attended recovery path used the original A intent/result and
performed only a new fixed read-only health observation. Both rooted health
brackets, shell-v2, complete GPT and statfs checks passed. The original failed
capture is preserved; later success does not validate the failed read. The
scientific inspection PASS remains independent of `recovered=true` and
`normal_return=false` in the unchanged terminal.

## Retained evidence and next boundary

The private run is `s22plus-debian-root-inspect-h0-20260923-1/prepared-1/task/operation-0001`.
Its task directory retains the closed grant, raw-rederived audit and an exact
214-file source snapshot joined to the independent capability review.

| Record | Bytes | SHA-256 |
| --- | ---: | --- |
| Immutable terminal | 2,432 | `995b6784fbbc193581676ff60fc9cd04efad22abc878ba027bc94a6dd1dbf9a6` |
| Raw-rederived closure audit | 1,828 | `e22382b5bda0e41ff28949e97158c599fdeb39f6cd65267fed9478fc42518cea` |
| Finite task close | 2,809 | `2e1f073c959069fe7176975feaf560d5f8780520ab91bbe6cca9f5b90a3a5b01` |
| Source snapshot manifest | 120,151 | `e077bcf04740cbfd26d62af6af02ea0ffa435593e82e0d4ad61d4c2a3cf71448` |

Source commit at execution was `c4aea92964d21693260f9e91c3e19aa0600965fa`;
the snapshot preserves the actual reviewed source bytes, including preexisting
working-tree contract bytes, rather than relying on that commit alone.
The [H0 preparation](S22PLUS_NATIVE_ROOT_INSPECTION_H0_2026-09-23.md),
[inspection policy](../operations/S22PLUS_NATIVE_ROOT_INSPECT_V1.md) and
[P401 closure](S22PLUS_DEBIAN_P401_FIRST_RUN_2026-09-23.md) retain their scopes.

Stage 2 is complete. A prospective fixed installed-userspace probe or full
Debian handoff needs its own qualified candidate and current reviewed scope.
Neither this closed grant nor the matched files authorize another flash,
chroot, installation, repair, or replay of P399/P400/P401/P402.
