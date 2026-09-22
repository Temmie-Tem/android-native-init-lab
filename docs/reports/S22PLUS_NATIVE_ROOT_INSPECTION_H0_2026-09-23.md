# S22+ stage 2: native root inspection preparation

Date: 2026-09-23. Exact target: `SM-S906N/g0q/S906NKSS7FYG8`.

This unit prepares a one-shot native inspection of the current `native_data`
filesystem after P401's unproved Debian attempt. It does not repeat P401 or
install another rootfs. The operator requested preparation through readiness,
with experimental-image transfer held until their start instruction. The
operator separately allowed necessary existing device control during preparation.

At preparation completion, actual A/B artifact qualification, independent
`PASS_GO` and 17 fixed connected Android reads had passed. No grant had opened
or experimental image transferred at that point. The operator subsequently
returned the start instruction and P402 completed its actual protected root
inspection and healthy Android return; see the
[separate live result](S22PLUS_NATIVE_ROOT_INSPECTION_P402_FIRST_RUN_2026-09-23.md).
The readiness state below is retained as preparation history; that task and
candidate are now consumed and the grant is closed.

## Concrete bounded experiment

P402 `v0.4.0-rc.2` retains the working native UFS/ACM runtime and adds a fixed
inspector plus a comparison table derived from the exact consumed P401 archive.
One attended 1800-second grant will contain one `root-inspect` operation:
healthy Android → one fresh P402 boot transfer → native health and inspection
with DETACH → same-boot health/CONTROL → one original-A transfer → full rooted
Android/GPT/Android32 health. It earns no reusable native admission.

The completion criterion is independently observed partition/filesystem state,
a protected read-only mount when clean, bounded marker/tree/file comparisons,
normal unmount/cleanup, and healthy original-A return. A complete negative
finding remains useful evidence. No chroot, Debian process or PID 1 handoff is
part of this stage.

| Qualified artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Boot-only AP | 32,051,241 | `c782f8b26f7bbc6d12ebb3640c07d53e4e9ac59dddf10f9af2ed856aa62502df` |
| Boot image | 100,663,296 | `72c59504da1f43fb8a6015fa3de5b208e484722d52cc9b810a2a02b6f167d1f9` |
| Static ARM64 inspector | 846,200 | `67bd0b3b5500548f40f86732ae3397d0b933679fe8de4733f5701c36a60ac8f9` |
| Root comparison table | 875,961 | `76ff68e40489d846993842490adfab40fda74200f24d879cd0bc9c2aba85eac6` |

The table covers 8,969 archive entries and an 8,175-entry boot-input subset.
Physical and VM builds have identical critical C, target seal, run identity
and comparison-table bytes; only the declared board-discovery substitution
differs. The actual live image validator accepted the qualified AP/member.

The inspector binds the existing 205,576,470,528-byte native extent and sealed
GPT/UUID/features. It compares all archive metadata/content and separately
reports the boot-input subset, preserves the existing witness and installation
records, and never extracts, repairs, writes files or remounts read/write.
Absence of markers does not establish that P401 never began installation and
does not release its consumed claim.

## Kernel-grounded read-only protection

Independent inspection of the retained FYG8 kernel found two relevant paths:
ext4 orphan cleanup can temporarily clear `SB_RDONLY`, and filesystem error
recording checks block-device read-only state rather than just mount flags.
Therefore `ro,noload,nodiscard` alone cannot establish no storage writes.

The exact partition is protected with `BLKROSET=1` before any mount, followed by
`BLKROGET` and sysfs readback. Target UAPI and UFS/block dispatch inspection
show that this changes only the native partition's in-memory policy, not the
whole LU or Android partition. There is no flag-clear operation; original-A
reboot ends that kernel lifetime. The exclusive authenticated pre-EXEC intent
records this control separately from filesystem reads.

The previous clean-superblock guard is preserved. Dirty, RECOVER or orphan
state is reported without mounting. Unknown identity, geometry, features or
checksum rejects the observation. Clean roots use a private mount namespace,
`ro,noload,nodiscard,nodev,noexec,nosuid`, descriptor-based traversal without
following symlink ancestors, and normal unmount. No installed code is executed.

The independent kernel review covers nine retained source files; its private
record is 6,078 bytes, SHA-256
`bb0d994725e5b257c2c8f16eaea1d29ebd1ffed8da3b8c8f5eaabe3e2e5bb818`.
It is source evidence, separate from the actual ARM64 tests below and future
Samsung proof.

## H0 validation

Real ARM64 Linux VM tests execute the same inspector implementation against
writable, exact-geometry private regular-file disks. Only physical-board block
discovery is substituted. Every case compares all allocated data extents,
their positions, total size and mtime before and after; this is an extent-aware
equality check, not a claimed whole-file SHA-256 over the sparse disk.

| Case | Actual result |
| --- | --- |
| Complete P401 archive and markers | Read-only mount, all expected metadata/content match, normal unmount |
| Witness-only filesystem | Mounted and observed absent installation records; no install attempt |
| Start marker without completion | Incomplete installation record reported; no retry |
| Changed rootfs identity file | Completed comparison reports changed boot input |
| RECOVER flag | Protected observation, mount skipped |
| Orphan head | Protected observation, mount skipped |
| Wrong UUID | Rejected before mount |
| Changed GPT byte | Rejected before partition control or mount |
| Directory checksum corruption | Real mounted ext4 read error; observation rejected and disk unchanged |

All nine cases left their writable backing disks unchanged. Successful binding
set native-partition RO while whole-disk and userdata RO stayed zero. The
checksum case directly exercises the error path motivating block protection.
These results do not establish physical UFS/USB initialization or Samsung mount.

The new owner/parser tests cover exact accounting, missing protection/cleanup,
partial records, scope exclusion, one N/one A, no admission, interrupted RO
control, and health-only recovery. An independent intermediate review found
that malformed inspection raw evidence could block terminal publication after
proved A recovery. The terminal now preserves that scientific NO_PROOF while
closing from independent A/health evidence; a real malformed-capture test
confirms no additional flash or inspection.

All 101 focused owner/parser, actual C/PTY, transport, task,
observation/protocol, GPT-health, ext4-session and Debian-owner checks pass.
Touched Python compiles; the inspector and complete boot packages are
byte-identical across A/B builds. Documentation links, scoped diffs and the
repository public-evidence boundary check pass.

The final independent review rederived the actual package inventory and all
nine raw VM results, including current backing-disk extent equality. It passed
the exact 68-file owner/capability and 158-file native closure with no blocking
findings. Request SHA-256 is
`b4bdbcd541b3d87a257828defe67fd1cc0e828c890e1b806baddbcfa0fa6fa0c`;
the private independent record is 3,644 bytes, SHA-256
`059eca220a9402cea627b6f18f3fe89d0f5c2d915d6fd6a53794f27cdb3bab93`.
The separate inspector capability record is active only for its defined scope;
it is not a finite task grant or Samsung execution proof.

## Preparation readiness (historical)

`prepared-1` completed all 17 fixed D0 captures: rooted original-A health
before and after shell-v2/full-GPT/statfs reads. Both brackets identify one
healthy Android boot, the exact original partition hashes, unchanged complete
GPT and Android32 statfs total 34,357,624,832 bytes. The raw projection was
independently rederived after preparation. No A90 or S20+ target-specific
command was issued. No reboot or boot-mode change was needed.

The prepared task SHA-256 is
`91fd7e92b087f4860739f7ef24236edb67104b9e2cd43e6f4585bbbe0cbc66ad`.
Its proposal bound P402, one operation, 1800 seconds, actual attendance and the
original-A return. At preparation close there was no grant, candidate claim,
block RO control, native mount, experimental transfer, F1 owner or operation.
The subsequent operator start opened that grant; execution repeated fresh
health and machine bindings. The linked live report records consumption and
closure. This prepared task can no longer be used for another operation.

The source-bound plan and all artifacts/raw evidence remain private under
`s22plus-debian-root-inspect-h0-20260923-1` and the P402 output. The existing
[P401 closure](S22PLUS_DEBIAN_P401_FIRST_RUN_2026-09-23.md) is unchanged.
The [inspection policy](../operations/S22PLUS_NATIVE_ROOT_INSPECT_V1.md) defines
the exact scope and preauthorized original-A recovery. Future installation,
filesystem repair, chroot and Debian handoff remain separate work.
