# S22+ native ext4 preparation V1

Status: **REVIEW_GATED_CAPABILITY**. Target: `SM-S906N/g0q/S906NKSS7FYG8` only.

This prospective capability prepares the existing Android32 layout's
191.4580078125 GiB `native_data` partition for Debian. Common/target adoption,
independent review of this exception and its execution closure, qualified fresh
artifacts and one actual returned finite attended grant are all required.
Existing GPT/reset and boot-only permissions do not authorize its filesystem writes.

## Bounded outcome

Create one ext4 filesystem on the exact new native partition, mount it in the
native runtime, write one fixed small test file, synchronize and unmount it.
After one declared fresh native boot, mount it read-only without journal
replay and verify the same bytes. Preserve the complete GPT and Android32
userdata geometry, then execute the separately bound original-A return and
rooted Android health checks. Formatting, persistence proof and final health
are distinct outcomes. No Debian rootfs, Wi-Fi or PID 1 handoff is part of this
unit.

The filesystem is intended to become Debian's root. Its first qualification
does not leave a mount or a storage daemon running. The later Debian bootstrap
will mount that same partition and hand it to Debian init; this profile does
not implement a second userspace service manager.

## Fixed implementation

- Use the retained P398 proposed GPT as the exact layout input; decode and bind
  the full primary-six/backup-nine regions, all 41 present entries, userdata's
  32 GiB extent and the native extent. Never compile a caller-selected block
  path, offset, size or partition into a generic command.
- Resolve the fixed FYG8 UFS controller's LU0 through current sysfs, verify the
  current partition number/name/start/size and device number, and compare full
  GPT bytes before accepting the endpoint. Require the native partition to be
  unmounted, without holders, with its expected 4096-byte logical block size
  and exact capacity. Only a private node for that partition may be writable;
  the whole-LU endpoint is read-only metadata access.
- Build an exact static ARM64 e2fsprogs formatter. Pin its source, build inputs,
  executable and complete argv/configuration. Use explicit ext4 features
  supported by the selected FYG8 kernel, 4096-byte blocks, 256-byte inodes,
  initialized inode tables/journal and no discard. Host defaults, external
  journals, image population, offsets, caller options and arbitrary paths are
  excluded. A normal ext4 journal is retained for the later Debian root.
- A format attempt is one-shot under an exact owner journal and global
  target/partition claim written before dispatch. Its key contains the physical
  target, fixed extent and sealed layout; changing filesystem UUID, boot image
  or output directory cannot renew it. A timeout, partial result,
  failed producer or missing reply consumes the attempt. There is no reformat,
  retry, automatic repair or fresh claim used to erase uncertainty.
- The fixed write test uses exclusive creation, no symlinks, exact byte count,
  file and directory synchronization, complete readback and clean unmount.
  Read-only persistence verification never creates the file or repairs a dirty
  filesystem. It requires the expected filesystem identity/features and clean
  state before a `ro,noload` mount.
- Use the existing authenticated native console and V3 global owner when a
  reviewed live adapter is adopted. Record raw command output and phase results
  in the existing owner journal. No generic root shell or parallel controller
  is added.
- Format success does not prove a mount, a clean close, a changed boot or
  persistence. Each requires its own complete observation. Kernel/driver stalls
  remain outside process supervision; physical recovery must be available.

## Owner sequence and bounded reads

The only task contains optional `bootstrap` followed by `native-ext4`, at most
two operations within 7200 original BOOTTIME seconds, with attended recovery.
It binds one reader N and one initializer E with the same filesystem seal.
Candidate replacement, deferred recovery, HUD, physical reconnect trials,
native-origin bootstrap and extra operations are excluded from this profile.
The existing N admission still requires two N installations and four health
sessions. Its final DETACH session adds fixed partition inspection.

`native-ext4` reuses the existing owner and transitions: starting-N health and
CONTROL; one E installation; E health, one initialization EXEC and DETACH;
same-boot E health/CONTROL; restoration of the admitted N; fresh-boot N health,
one read-only verification EXEC and DETACH; same-boot N health/CONTROL; original
A once; rooted Android health brackets around full six/nine-block GPT and
F2FS statfs reads. The initialized Android32 return basis is the rederived
closed P398 result. Final capacity remains 34,357,624,832 statfs bytes.
No Android reset or GPT restoration is part of this operation or its recovery.

Each filesystem command uses the existing sequence-5 authenticated EXEC.
The initialization intent and partition claim precede dispatch. Initialization
and verification each have a fixed 240-second command deadline within one
300-second observation and the original task deadline. Inspection uses 15
seconds within 60 seconds. These bounds replace no other observation deadline
and never extend after a partial result. Raw stdout/stderr, exact tool exits,
reaping, ordered filesystem stages and actual descriptor close are required.
Negative or missing required filesystem evidence stops normal progression.

The fixed helper creates only its owned `/dev/.s22-ext4-v1` aliases in the
existing device-capable tmpfs. It keeps `/s22-root-work` nodev and creates its
private mountpoint there, using a private mount namespace. The LU0 node is
0400; the exact native-partition node is 0600 only for initialization, otherwise
0400. Whole-LU access is read-only. All formatted blocks, ext4 journal updates
and the one 4096-byte witness are confined to entry 41, LBAs 12,115,456 through
62,305,023 at 4096 bytes per LBA. The complete GPT and both partition mappings
are checked before access; full GPT and clean superblock are checked after
successful clean unmount.

The format tool is pinned e2fsprogs 1.47.2, statically built for ARM64 from its
upstream archive. Exact feature masks, tool/configuration bytes and generated
role seal are joined through A/B helper and boot packages. H0 qualification
executes those formatter/checker binaries against a disposable regular file
of exactly 205,576,470,528 bytes. That is not evidence of a target-kernel mount.
The fixed checker uses `-fn`; it never repairs. Initialization performs an
ordinary journaled RW mount, exclusive witness creation, full readback, fsync
and syncfs, then normal unmount and clean-superblock checks. Verification
requires clean identity/features before `ro,noload` mount and never writes.

## Failure and authority boundary

An interrupted formatter can leave only this newly reserved filesystem
incomplete; restoring a boot image does not undo its writes. No old Android
userdata or other filesystem may be used as a scratch target. A completed
synchronous failure may make one ordinary unmount call only for its known
owned mount. Failed unmount is never repeated. Unknown or potentially blocked
writers authorize no more filesystem commands. Attended physical entry to the
exact bootloader Download endpoint terminates the old native kernel before
the existing one-shot original-A transfer; firmware arrival alone does not
prove filesystem success. Android root/GPT/capacity health closes recovery,
while the filesystem result remains unproved. The prior G2 grant, Android reset
and GPT restoration cannot be used as filesystem recovery.

Before live use, complete the native implementation and target-ABI tests,
actual formatter/feature qualification, fixed consumer and no-replay tests,
boot artifact qualification, independent review, common/target adoption and
one returned finite task grant. Definition and review are not a task grant.
