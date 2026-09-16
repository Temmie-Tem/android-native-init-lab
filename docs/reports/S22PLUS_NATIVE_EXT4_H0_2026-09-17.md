# S22+ native ext4 preparation — H0 qualification

Date: 2026-09-17. Target: `SM-S906N/g0q/S906NKSS7FYG8`.
Scope: prepare the existing Android32 layout's native_data filesystem before
Debian rootfs staging. Device actions in this unit: **zero**.

## Prepared behavior

The fixed helper resolves the FYG8 UFS LU0 and exact entry 41 from current
sysfs, checks both userdata/native mappings, excludes mounted/held native
storage and compares every byte of the sealed six/nine-block GPT capture.
Only entry 41 can receive filesystem writes; the whole-LU alias is read-only.
The native extent is 205,576,470,528 bytes. Android userdata remains 32 GiB.

The initializer runs the pinned ARM64 e2fsprogs 1.47.2 formatter with explicit
features, 4096-byte blocks, 256-byte inodes, fully initialized inode tables and
journal, zero reserved blocks and no discard. It checks the complete filesystem
with `e2fsck -fn`, mounts it with the ordinary journal, exclusively creates one
fixed 4096-byte witness, verifies every byte, synchronizes and cleanly unmounts.
The separate reader image cannot select the helper's formatting mode. Its
verification requires the sealed UUID/features and clean state before fsck and
a `ro,noload` mount; it checks the existing witness and unmounts without repair.

Both roles retain the existing native health, UFS initialization, thermal
runtime, authenticated console and output-drain correction. They add four
immutable ramdisk members: the helper, formatter, checker and fixed config.
The binaries are mode 0500; config is 0400. Tools and generated private seal
are joined to their actual A/B package bytes. The generated seal contains the
private UUID and GPT; it is never tracked.

## Evidence

| Artifact | Result |
| --- | --- |
| P399 reader, `v0.3.1-rc.1` | A/B identical; actual AP/member/init/Image/helper/tool joins PASS |
| P400 initializer, `v0.3.1-rc.2` | A/B identical; actual AP/member/init/Image/helper/tool joins PASS |
| P399 AP | 33,372,201 bytes; SHA-256 `d7f1d82d12af63a45bf9e179560ae100f76316d3543f19a02a8f35acc56ec3df` |
| P400 AP | 33,372,201 bytes; SHA-256 `5e1c4debf05f982da5d4836b7f8a66005724689b5a88c6277c984bdf913b3c27` |
| Upstream e2fsprogs 1.47.2 archive | SHA-256 `08242e64ca0e8194d9c1caad49762b19209a06318199b63ce74ae4ef2d74e63c`; fixed source/toolchain/build provenance retained |
| Actual ARM64 formatter/checker | QEMU-user execution on one exclusive disposable regular file of the exact native extent; both exit 0; checker leaves superblock unchanged |
| FYG8 kernel | Embedded config has ext4/JBD2/tmpfs/namespaces; exact source supports selected incompat `0x2c2` and read-only-compatible `0x46b` masks |
| Target ABI | Exact ARM64 UAPI open/mount/ioctl values checked; real ARM64 file flags, exclusive creation, symlink rejection, high offsets and witness roundtrip exercised |
| Focused tests | 89 passed: 70 native filesystem/core/console/owner/GPT tests plus 19 task/adapter tests |

Private evidence is under
`workspace/private/outputs/s22plus-native-ext4-h0-20260917-1/`, with actual
packages under `workspace/private/outputs/s22plus-native-ext4-v1/`.
The H0 summary joins both qualification receipts, exact-size tool execution,
kernel ABI checks and the shared filesystem binding. Native build/helper
receipts bind current sources; the earlier seal's source-input list remains
historical preparation provenance. No retained preparation receipt is relabelled.

## Owner, failure and review

One attended V3 task permits optional reader bootstrap followed by the fixed
N/E/N/A transaction, at most two operations and 7200 original BOOTTIME seconds.
Bootstrap's final session inspects the actual partition before admission.
The initializer's durable intent and global target/partition claim precede
sequence-5 EXEC. A fresh UUID/image cannot renew that claim. All fixed extra
commands finish with DETACH; subsequent health/CONTROL uses a fresh session.
Restored N must prove a new kernel boot and authentication ordinal one before
the read-only witness result can establish persistence.

Timeout, interrupted output or an uncertain writer permits no further
filesystem command. Recovery requires attended bootloader Download arrival and
the original Android A at most once. The rederived closed P398 Android32 basis
and full GPT/statfs/root-health brackets apply, including reader-bootstrap
recovery. A boot-image return does not undo formatting or prove the filesystem.

Independent review found and closed three concrete implementation issues:
the block-node aliases initially targeted a nodev workspace and were moved to
the verified device-capable `/dev` tmpfs; complete negative bootstrap inspection
needed to remain eligible for A recovery while missing final proof retains its
H0 repair guard; normal N/E/N/A close repair needed to recognize its normal A
intent. Real C/PTY and owner fault tests cover these outcomes. Review also
narrowed the post-unmount claim to actual full-GPT/clean-superblock checks.

Final independent review is `PASS_GO`, recorded in the V3 review binding over
58 execution and 156 runtime sources. It qualifies this exact exception and
source closure, not a run. The concrete 7200-second/two-operation task is
prepared with SHA-256
`86ed96184ffd6f154461654f013177cd0504c92415007315e391f9ba55fb0047`.
No grant has opened and
no P399/P400 claim has been consumed. A90/S20+ were untouched.

## Limits and next criterion

H0 proves formatter behavior on a regular file, ABI values, package identity
and bounded owner/consumer behavior. It does not prove an actual FYG8 ext4
mount, media persistence, hardware stall recovery or Debian boot. The live
criterion is one initialized and cleanly unmounted filesystem, byte-identical
witness on a fresh native boot, then exact healthy Android32 return.
Debian staging, networking and host-PID1 handoff remain later separate work.
