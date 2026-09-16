# S22+ first native ext4 run — functional proof and health-only recovery

Date: 2026-09-17. Exact target: `SM-S906N/g0q/S906NKSS7FYG8`.
Source commit: `7b94243caa`. Preparation and independent capability review are
recorded in the [H0 report](S22PLUS_NATIVE_EXT4_H0_2026-09-17.md).

## Distinct outcomes

- Initialization: `PASS_INITIALIZED_WRITTEN_CLEAN_UNMOUNT`. P400 formatted the
  sealed 191.4580078125 GiB native_data partition once, ran the fixed read-only
  checker, mounted ext4, exclusively wrote and fully verified the 4096-byte
  witness, synchronized it and cleanly unmounted.
- Persistence: `PASS_READONLY_WITNESS_CLEAN_UNMOUNT` on restored P399. The
  authenticated kernel boot differed from every prior measured native boot,
  its authentication ordinal was one, and the fixed clean filesystem/witness
  passed fsck and `ro,noload` read-only verification. This is actual target
  mount and fresh-boot witness evidence, beyond the earlier QEMU qualification.
- Formal operation: `ANDROID_CLOSED_HEALTHY`, `recovered=true`, with filesystem
  aggregate `NO_PROOF_RECOVERED_ANDROID`. The runner conservatively classifies
  every recovered path this way; the original terminal is unchanged. Separate
  retained-raw assessment records `PROVED_INITIALIZATION_AND_FRESH_BOOT_WITNESS`
  and explicitly keeps `normal_operation_completed=false`.
- Final Android: the original A transferred once. A failed first health read
  was followed only by the already authorized health recovery, which proved
  numeric root, exact boot/supporting partition digests, unchanged complete
  GPT and Android32 capacity. No additional image transfer occurred.

The witness SHA-256 is
`643eb87ede9928b65fbc2d47e67ab3592d5f86c74e4b3533c4e965408269c023`.
Native storage contains that filesystem and witness. Debian has not been staged.

## Canonical timeline

Times are seconds from the original grant's BOOTTIME opening, rederived from
the append-only owner journals. The task bound 7200 seconds and two operations.

| Time | Evidence |
| --- | --- |
| 71.655 | P399 bootstrap closed healthy after two N installations, four authenticated sessions and final `PASS_PARTITION_BINDING` inspection |
| 124.429 | Durable one-shot filesystem intent before P400 initialization EXEC |
| 128.791 | Initialization, witness, synchronization and clean unmount proof complete |
| 152.998 | Fresh restored-P399 read-only witness verification and clean unmount proof complete |
| 162.751 | Original-A transfer intent |
| 164.342 | Original-A transfer completed |
| 192.585 | First Android final-health bracket stopped with `RawCaptureError` |
| 200.415 | Health-only recovery completed with full GPT/capacity/root proof |
| 377.523 | H0 rederivation, source snapshot and finite task closure recorded; no F1 owner |

Bootstrap has 19 journal rows. The filesystem operation has 28 rows and seven
durable effects in their declared order. Totals are two bootstrap N transfers,
one E transfer, one restoration of admitted N, one A transfer, one filesystem
initialization and one read-only verification. There was no format retry,
repair, GPT write/restoration, Android reset, additional reboot command or
extra recovery transfer. A90/S20+ were untouched.

## First Android read failure and recovery

The first final-health attempt passed its initial selector/lane reads. Its
property command exited zero but returned only 111 bytes and six property
names; this was incomplete and was not accepted as a healthy Android bracket.
The following root-health command exited one with empty stdout and a bounded
ADB target-not-found diagnostic. Neither capture timed out, overflowed or
reported a raw-producer fault. The cause of the interruption is unproved.

The owner recorded the stop after the completed original-A transfer. It
reconstructed that transfer from its original intent/raw evidence and performed
only `recovery-health`; A was not dispatched again. Complete rooted health
brackets around the fixed GPT/statfs reads then agreed on one Android boot and
the exact original-A/supporting partition identities.

Final `/data` statfs total is 34,357,624,832 bytes, with 31,657,787,392 available
and 31,792,005,120 free at observation. All sealed GPT bytes and the native
partition extent were preserved. These Android checks are separate from the
earlier native filesystem proof and do not convert the failed normal health
attempt into a pass.

## Retained evidence and closure

Private run:
`workspace/private/runs/s22plus-native-session-v3/p399-p400-native-ext4-20260917-1/`.
Raw launch captures are under the H0 output's `live-launch/`; both CLI processes
returned zero without outer timeout or overflow. Raw command captures and the
failed attempt remain in their original owner directories.

| Record | SHA-256 |
| --- | --- |
| Immutable filesystem-operation terminal | `1c4e1a9937cea900f30f44d740b09b468ee7298e3d3fda12ecc86aac59d47038` |
| Separate retained-evidence assessment | `f99cf4fb241185de92cae502a56f8e7e5119c30e6e35dc39ffaac148426ef2bf` |
| Finite task close | `0c2b78e9cb82dcded0b54728664794d121d6d997862ffb1f33f6e99bb80cc6b8` |
| Source-snapshot manifest | `326e63b2e2b1abd94ceb2426ab7688446d1d04201ef93a16fdd073c4b3004afb` |
| Journal-derived timeline | `5f1826dbac6d07dfad9b2f10bd9363c4d45a4afcfadadb680ca19c5e30a0d409` |

The close binds both consumed operations, their exact journal tails, the
original grant, immutable terminal and copied execution/runtime sources.
Remaining task time does not authorize another action. No consumed image,
filesystem claim, old terminal or grant is made fresh by this report.
The next useful unit is H0 preparation of a matched Debian rootfs and native
bootstrap, preserving this filesystem and defining a separate staging scope.
