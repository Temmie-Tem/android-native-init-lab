# S22+ fixed installed-Debian userspace probe V1

Status: **REVIEW_GATED_CAPABILITY**

This stage-3 capability applies only to operator-owned
`SM-S906N/g0q/S906NKSS7FYG8`, the retained Android32 layout and the root archive
observed by the closed P402 inspection. It is a bounded diagnostic chroot,
separate from the product goal of Debian owning initial host PID 1.
Common/target adoption, current independent source review, qualified actual
artifacts, exact healthy Android entry, physical Download recovery and one
returned finite attended grant are all required. Preparation is H0/readiness,
not authority to transfer a new boot image.

## One operation and unchanged recovery

The existing V3 owner permits only `userspace-probe`, one operation and at most
1800 original BOOTTIME seconds:

1. Fresh exact rooted original-A health, one Download request and departure.
2. One globally unconsumed probe-N boot-only transfer.
3. First-boot authenticated native health, one fixed EXEC, DETACH and actual close.
4. Fresh same-boot native health/CONTROL and measured Download departure.
5. One original-A transfer and full rooted health/GPT/Android32 statfs brackets.

There is no E, native admission, bootstrap, prior tail, reconnect, HUD, second
probe or extra operation. The kernel RO control and possible installed-code
execution share one exclusive durable pre-EXEC intent binding the command,
run, nonce, boot identity and sequence. Once intended, the command never
replays. All earlier filesystem, installation, image and inspection claims
remain consumed.

Any uncertain command, cleanup, required health or protocol stops research.
Only the existing original-A recovery continues from durable state, with actual
physical Download if native CONTROL is unavailable. Timely endpoint binding,
same-host-boot recovery and global F1 exclusion retain their V3 meanings.
After proved A transfer, only health/report continuation is allowed; A is never
resent. A healthy Android return does not prove a Debian workload succeeded.

## Protected root and fixed child

The [root inspector](S22PLUS_NATIVE_ROOT_INSPECT_V1.md) supplies exact entry-41,
UFS/LU0, full GPT, filesystem identity, partition-only `BLKROSET=1` and RO
readback, clean-superblock admission, private `ro,noload,nodiscard,nodev,noexec,nosuid`
mount, bounded comparisons, ordinary unmount and final superblock/GPT checks.
Its permanent block-RO invariant also applies here; neither helper clears the
flag. Dirty/recovery/orphan state skips mounting. Wrong identity rejects.

Execution additionally requires all expected archive entries to match, exact
start/completion records and witness, and only those three records plus the
empty, root-owned mode-0700 `lost+found` directory beyond the expected archive.
This complete root closure excludes unselected loader inputs such as an added
`/etc/ld.so.preload`. Any mismatch skips execution without installation or repair.
The probe image contains the helper and comparison table, not an archive,
formatter, checker or replacement Debian binary.

One forked child retains the helper's existing ACM command process group. It
creates a private mount namespace and uses **`MS_REMOUNT|MS_BIND`** to enable
execution only on its inherited native-root mount, preserving readonly,
nodev and nosuid. This changes per-mount flags without reconfiguring the
shared ext4 superblock; noload/nodiscard and partition block RO remain.
The child reopens that namespace's mount before chroot and verifies its actual
device/type/flags. The parent keeps and later rechecks its original noexec mount.

The child chroots, sets cwd `/`, supplies an empty pipe as stdin and bounded
stdout/stderr pipes, and closes all descriptors above 2 except a close-on-exec
setup/error pipe. It drops supplementary groups and all real/effective/saved
UIDs/GIDs to 65534, clears keepcaps, verifies zero capabilities, and enables
`no_new_privs`. Fixed limits are 8 CPU seconds, 128 MiB address space, 64 file
descriptors, 16 processes for that UID, and zero core/file-output size.
No procfs, sysfs, device, writable tmpfs or network namespace is mounted.

Only the fixed `/bin/sh -c` workload in the profile is reachable. It uses the
verified installed shell, numeric `id`, external `printf`, a synchronous
nested shell/child wait and a nested shell expected to exit 23. Environment and command
bytes are fixed; no host/user-supplied script or path is accepted. No service,
package manager, network operation, reboot, installed init or PID 1 handoff is
part of the workload. This is a reviewed fixed program, not a general sandbox
claim that unprivileged socket creation is impossible.

The helper is a subreaper. Normal completion requires the direct child's
actual wait status, complete setup/exec-error pipe framing, bounded output,
pipe EOF and `ECHILD`. Each stdout/stderr stream is capped at 4096 bytes and
retained as hex in the private outer raw output; setup evidence is capped at
16 bytes. The exact expected stdout and empty stderr, successful setup and
exec, zero child status and no unexpectedly adopted descendants are all needed
for `PROVED_FIXED_DEBIAN_USERSPACE`. Exit zero alone never proves the workload.

The child has a 30-second inner observation bound within the unchanged
240-second command/300-second native observation and original grant deadline.
It never creates another process group/session. On timeout, overflow or
unsettled execution the helper returns failure; the unchanged outer ACM
supervisor cancels and settles the entire original command group. Missing
settlement/cleanup cannot be reported as a completed probe and requires the
existing original-A recovery. There is no child restart or cleanup command.

## Proof, qualification and preparation

A fully observed synchronous setup failure, nonzero/signal exit or wrong
workload output may be a completed negative finding when process settlement,
mount cleanup, final storage guards and outer protocol are complete. It permits
normal native return but never a userspace PASS. Incomplete accounting, output,
exec state, timeout or cleanup is NO_PROOF and stops research. Even a successful
diagnostic chroot proves neither Debian host PID 1 nor USB networking/SSH.

Qualification joins actual A/B boot packages, helper/table/workload bytes,
the closed P402 root/Android evidence and current independent review. Real
ARM64 Linux VM tests exercise actual dynamic linking, privilege drop, child
execution, wait/exit semantics and unchanged writable backing disks, plus
wrong/early output, timeout, overflow, descendant and root-admission negatives.
Virtual block discovery is explicit and is not Samsung execution proof.

The named foreground preparation D0 reuses the existing fixed original-A
root-health brackets, shell-v2, complete GPT metadata and Android32 statfs.
It may reobserve a pure read failure with all original raw evidence retained.
It cannot mount native_data, execute Debian, change mode, transfer an image or
open/renew a grant. The actual live execution repeats fresh machine checks.
The separate `s22plus_native_userspace_probe_v1_review.json` binds this capability;
old review receipts and consumed source/artifact identities are not repinned.
