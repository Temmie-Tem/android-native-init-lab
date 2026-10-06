# S22+ FYG8 preparation in Debian early userspace — H0

Target: operator-owned `SM-S906N / g0q / S906NKSS7FYG8` only.
Scope: prospective initramfs construction and ARM64 VM tests. No connected
read, device effect, Samsung boot/AP package, candidate activation or grant.
A90 and S20+ were untouched. Kernel bytes were neither modified nor rebuilt.

## Bounded result

This unit moves the retained platform/UFS module sequence into a small child
of Debian initramfs-tools' shell `/init`. It ends after exact GPT and protected
native_data superblock observation. It does not mount native_data, clear its
read-only flag, repair ext4, execute installed Debian, configure a USB gadget,
or perform reboot/recovery. Debian's PID1 remains at a terminal stop.

The earlier [Debian-owned boot VM proof](S22PLUS_DEBIAN_OWNED_EARLY_BOOT_H0_2026-10-07.md)
remains separate: that virtual hardware path reached installed SysVinit and
SSH. This new FYG8 artifact does not yet combine physical preparation, full
root admission and installed-PID1 handoff into a qualified phone boot.

## Retained inputs and ownership

The fixed Image comes from the sealed P399 input. Its SHA-256 is
`d510a3f83a6d48392649df325223e9847f85e2ee35989f32db0fb6abff371a3d`.
The inventory preserves the exact 73-entry platform declaration, followed by
the existing eight UFS entries, without pruning. Module names, order,
parameters, sizes, digests and origin metadata are checked against retained
or pinned stock vendor inputs. Actual Image export CRCs and earlier module
exports satisfy all **3,926 imports**. Modinfo dependencies also occur earlier
in the sequence. This establishes static linkage closure, not successful
insertion, device binding, probe completion or firmware readiness.

The source includes kernel release and board-model checks as early rejection
conditions. They are not unique device identity or a substitute for the
future transport runner's exact-target and boot-artifact binding.

Debian `mkinitramfs` 0.148.4 builds the archive from the already authenticated
Debian package cache. The shared builder extracts packages in a mapped-root
user/mount/PID namespace; it installs nothing in the host. `/init` differs
from Debian's packaged source by one line: its devtmpfs mount sources
`/scripts/fyg8-dev`. The hook supplies tmpfs `/dev`, console-or-null standard
fds and a tmpfs evidence directory, invokes the child and stops before
Debian's generic root selection and mount stages.

There is no invoked udev/mdev daemon, cold block-device scan or custom native
PID1/console runtime. Exact temporary block aliases are created only after
sysfs geometry binding and removed on completion. Modules live in a fixed
private initramfs directory, outside the normal modules.dep search tree.
The packaged Debian utilities remain available; this is a prototype builder,
not an on-device package-upgrade mechanism or an archive-size optimization.

### Firmware boundary

`pdic_max77705.ko` imports `request_firmware`, `release_firmware` and Samsung's
firmware signature verifier. None of the 81 modules declares a
`MODULE_FIRMWARE` name, and neither retained ramdisk contains standalone files
under `lib/firmware` or `vendor/firmware`. No arbitrary firmware was added.
Those negative static observations do **not** establish that firmware is
unnecessary: conditional driver requests, built-in blobs and complete PDIC
readiness remain unresolved. UFS discovery has its own required observation;
module presence cannot satisfy it. The preserved platform plan's USB driver
binding conditions have not become a USB capability claim in this port.

## Child behavior and evidence

The C child uses target ARM64 UAPI assertions and the existing protected
storage primitives. Before insertion it validates every module file and
requires the selected runtime names to be absent. At each insertion it pins
and hashes the same fd supplied to `finit_module`, uses flags zero, records a
checked BEGIN, performs one call and verifies module presence before DONE.
Any failure, including `EEXIST`, ends the sequence; no insertion is retried.

Storage discovery requires the exact UFS controller/LU0 relationship,
native_data partition index and extent, current userdata extent, block size,
no native_data holders and no relevant mounted partition. Only absence is
reobserved for a finite number of checked sleeps. The helper compares the
sealed GPT, sets **only native_data's RAM RO flag**, verifies ioctl/sysfs RO,
reads the superblock and checks its original checksum and identity. It then
rechecks GPT, unchanged superblock bytes and RO before closing aliases.
It never clears RO and never opens a block device for writing.

`METADATA_CLEAN` means only the sealed superblock identity and clean-state
predicate matched. It is not complete ext4 integrity, immutable-root closure,
installed-root admission or execution proof. `METADATA_DIRTY` preserves the
distinction without attempting a mount or journal replay. The physical P415
record remains dirty/`recover=1`; this H0 work changes no physical state.

Records are exclusive-created under `/run/initramfs`, checked as a root-owned
0700 tmpfs directory. They carry construction identity, kernel boot ID,
sequence, module stage, storage/RO stage and terminal result. Each write and
fsync is checked before the next effect; the file is bounded to 64 KiB and
256 records. Existing evidence is not overwritten. These are local RAM
records, not authenticated USB proof or durable storage receipts.

Before storage is usable, RAM evidence can disappear on reset. A missing
record never proves non-execution. A future boot-capable design should export
these records through the reviewed observer, and after exact root admission
consider checked, bounded per-run/per-boot durable receipts and later recovery
retrieval. No persistent receipt write is implemented or authorized here.
A userspace deadline also cannot recover a blocked kernel module-insertion
call; this terminal prototype has no demonstrated physical recovery route.

## Validation

The private evidence root is
`workspace/private/outputs/s22plus-debian-fyg8-port-h0-20261007-1/`.
`inputs-2` retains the inventory and raw modinfo/import/export inspection;
`build-5` records final source snapshots and generated-header pins. The
7,105,815-byte target initramfs has SHA-256
`6a43abfc8fdd669e1d57592c19112062c78aa0811b0a96b7fff9ce72319e88d6`.
Its static AArch64 child has SHA-256
`99db65741654db5364eb8411bf553c38c267ce2a405f299b968fb1d8bec79869`.
`final-audit.json` confirms final artifact/evidence equality and source pins;
`independent-review.json` preserves the independent H0 verdict.

The target archive is reproducible across independent A/B constructions.
The shared builder regression reproduces the prior full-boot VM image exactly
at `461cc1e65918f7171b4b1364f5afbe60bf275b00cacc2b185a234c627947d6e8`;
its unchanged full-lifecycle evidence is reused rather than rerun.

The new `vm-2` suite passes ten real ARM64 system-VM cases. Its starting
archive is the validated build-3 artifact, byte-identical to the final target
artifact. Only board guard, module insertion/presence and UFS sysfs discovery
are substituted. Module file checks, normal-path block ioctls, GPT/superblock reads,
RAM evidence writes and alias cleanup execute on the real ARM64 kernel.
Negative cases deliberately change inputs or inject the named failure; the
RO-error case injects EIO immediately before BLKROSET. The VM harness alone
exports records and powers down; those actions are absent from the target
hook. Test disks remain host **regular files** and are writable to QEMU, so
unchanged-disk checks are meaningful.

| Case | Required observation |
| --- | --- |
| Clean superblock | All 81 ordered BEGIN/DONE pairs; metadata clean; exit 0. |
| RECOVER bit set | Metadata dirty; exit 2; no mount or replay. |
| Wrong UUID | Reject under native_data RO; no metadata admission. |
| Changed PMBR byte | Storage bound; exact GPT rejection before RO_BEGIN. |
| Changed module byte / symlink | Reject before the first insertion. |
| Insertion EIO / EEXIST | Exactly one BEGIN, no DONE and no retry. |
| Injected EIO before BLKROSET | Reject before superblock admission. |
| Existing record file | Exit 102; retained sentinel unchanged; no module attempt. |

Every case preserves the complete sparse disk extent fingerprint, including
size, allocated extent positions/content and modification timestamp. This is
an extent-aware equality proof, not a whole-file SHA-256. Positive and dirty
cases leave only native_data RO; disk and userdata remain RW. No case mounts
ext4, and all owned aliases are gone at the terminal boundary.

An additional `vm-console-1` case makes the initial console node unopenable.
While the child is running, the VM-only guard directly checks that PID1's
fds 0, 1 and 2 point to `/dev/null`. Preparation and RAM records then complete;
only the VM exporter opens a separate console afterward. This checks the
actual fallback path needed by FYG8's lack of an early usable console.

Three host negative checks reject an extra module file, changed load order
and changed origin digest. Python compilation, static ARM64 compilation and
ELF/symbol inspection accompany the builds. No linked helper mount, exec,
formatter or reboot entrypoint survives garbage collection. Final repository
boundary, link and diff checks passed. Independent review returned PASS_H0
with no unresolved blocking findings; it qualifies this H0 capability only.

### Preserved H0 corrections

The first inventory assumed all modules used stock 0644 metadata; the retained
custom module is pinned 0640. Validation now uses its exact retained receipt
and retains checks for root ownership, a single link and no group/world
write permission. The first archive
audit rejected GNU cpio's leading `.` root directory record; a narrow Debian
adapter validates/removes that record before invoking the unchanged strict
Samsung parser. A later in-progress build correctly rejected source drift.

The first GPT-negative VM fixture invalidated partition-table discovery, so
the helper stopped with ENODEV before its own GPT reader. Raw evidence is
retained in `vm-1`; the corrected PMBR-byte fixture tests the intended exact
metadata comparison while retaining kernel partition registration. No failed
H0 record is relabelled or deleted. Independent review also prompted complete
seal-producer/header provenance and exact payload-member-set checks.

## Remaining physical work

The next implementation step is to join early preparation to complete
protected root admission and an authenticated observation/recovery design,
then Debian's existing root transition. The actual FYG8 module initialization,
UFS discovery, conditional firmware behavior and USB lifecycle require their
own exact physical evidence. The existing dirty native_data requires its
separate reviewed recovery owner before writable Debian admission.

No kernel change is justified by the static and virtual evidence obtained
here. A later kernel patch or rebuild should answer a demonstrated target
limitation or measured optimization need. None of these H0 artifacts grants
a new effect, retires a pending physical owner or replays a consumed action.
