# S22+ readonly root-transition witness V1

Status: **REVIEW_GATED_CAPABILITY**

Only operator-owned `SM-S906N/g0q/S906NKSS7FYG8`, retained Android32 GPT entry
41 and the completed P401 native_data root are selected. This is the first
readonly transition unit in the
[handoff plan](../plans/S22PLUS_DEBIAN_HANDOFF_EXECUTION_PLAN_2026-09-30.md).
It proves replacement host PID 1/root separately from installed Debian init.
It authorizes no Debian writable lifetime, installation, repair or service.

## One finite operation

Only V3's `switch-root` operation may use this profile. One returned attended
grant binds one operation and at most 1800 original BOOTTIME seconds:

```text
exact rooted original-A health -> Android Download -> one fresh boot-only N
  -> native UFS/ACM startup -> authenticated first-boot fixed native health
  -> fixed PID1 transition -> post-exec witness -> fixed Download request
  -> one original-A boot transfer -> full rooted Android32/GPT final health
```

There is no N admission, E, prior tail, optional reentry, reconnect, HUD request,
extra EXEC or repeat. Old candidates, installation claims and P408's closed
grant remain consumed. The first native authentication must be a fresh boot
and nonce. The existing owner retains global target exclusion, exact boot-only
archive verification, no replay and original-A recovery provenance.

One durable **compound transition intent**, before request 37/sequence 5,
consumes the fixed preparation, root transition and its sole possible witness
return. It contains no program, pathname or caller argument. The existing
console must be idle after the exact health EXEC and STATUS. Its new terminal
ACK is acceptance only. Once consumed, the native process cannot return to
generic console service, detach, reauthenticate or renew a deadline.

Successful post-exec proof permits exactly request 38/sequence 6. Before its
first byte, a no-clobber continuation receipt binds the original transition
intent, same run/boot/nonce, fixed request and fresh target departure snapshot.
The witness consumes this request before its ACK, flushes that ACK completely,
then invokes the existing fixed `reboot(RESTART2,"download")` once and parks
if it returns. This is not another operation or a second transition allowance.
The host separately proves timely USB departure, exact Download arrival, the
single A transfer and final health. ACK alone proves none of those results.

## Actual PID1 and readonly preparation

The real native PID1 execs the static preparation executable. An ordinary
root-console EXEC child is never used for this terminal transition. The parent
passes only the original nonblocking ACM fd3 and a sealed state memfd4; fd0–2
refer to `/dev/null`. State binds run, authenticated nonce, current kernel boot
digest, the three owned HUD child slots and one 300-second BOOTTIME deadline
set at request acceptance. Both replacement programs verify exact state size,
schema, seals and current boot/deadline. FD remapping first duplicates sources
outside fd0–4, including when those descriptors contain holes.

The preparation process retires native workers **before** root admission.
The reused checker supervisor requires ECHILD, so retaining HUD children would
make its result invalid. Exact child waits distinguish previously reaped
workers; already reaped PIDs are never signalled. Unknown wait state, unexpected
children or unproved five-second settlement stops before root transition.
A bounded `/proc` census admits only PID1 and kernel threads. This establishes
no surviving native userspace; it does not claim that loaded kernel drivers
have been unloaded or automatically recover from a stall.

After retirement, reuse the inspector's exact UFS controller/LU0/entry-41/GPT
binding, partition-only `BLKROSET=1`, ioctl/sysfs readback and clean-superblock
admission. The flag remains set until reboot. Dirty/RECOVER/orphan state skips
mounting. The exact static `e2fsck -fn` runs with fixed environment, no ambient
configuration, zero groups/capabilities, no_new_privs and the existing bounded
resource/output checks. PID1 now owns its finite failure kill/reap; no vanished
outer ACM supervisor is assumed. No formatter, repair, external journal,
block-data write or RO-clear is reachable.

Mount only `ro,noload,nodiscard,nodev,nosuid,noexec`. Verify actual device/type/
flags, installation markers, witness, all pinned archive metadata/content and
the four declared additional entries. No installed executable runs. Recheck
partition RO, superblock bytes and full sealed GPT after worker retirement and
root reads. A storage failure is a negative result, not permission to retain
an old-root native service manager.

## Mount, executable and descriptor ownership

Select the retained static BusyBox 1.37.0 explicitly: 1,975,064 bytes, SHA-256
`7d93682be37cf6ed46699f6fff546b80bf133cf8ec342c2d04bc23387f78bc34`.
Its executable path and BusyBox `argv[0]`/`switch_root` applet are fixed. This
does not inherit qualification from the native observer's BusyBox 1.36.1.

Create only a bounded executable tmpfs for the pinned static witness. It is
nosuid/nodev and contains no caller code. Verify its bytes and destination
before the irreversible transition. Move the ext4 mount out of the separate
work tmpfs to `/newroot`; move RAM to `/newroot/run`, configfs to
`/newroot/run/config`, and `/dev`, `/sys` (including debugfs) and `/proc` to the
new root. Configfs/gadget state and the same open ACM descriptor survive; no
UDC unbind/rebind or Debian NCM setup is part of this readonly unit.

Close every non-whitelisted descriptor, including inspector-local parent,
work, node and root handles. Ordinarily unmount both old `/run` and
`/s22-root-work` tmpfs mounts.
No lazy/forced unmount substitutes for that proof. Reject unknown mountpoints,
duplicate mounts, unexpected filesystem types, bind subroots or propagation.
Seal the resulting mount IDs and normalized mount digest for comparison after
exec. BusyBox removes old-root contents, moves the new mount, chroots and execs
only `/run/s22-witness`; it does not execute `/sbin/init` in this unit.

BusyBox's switch_root is not atomic. Its late failure or a failed replacement
exec can terminate PID1 and panic the kernel. Helper parking cannot intercept
those errors after exec. There is no claim that the deleted old initramfs can
be restarted, and no automatic recovery guarantee.

## Independent evidence and stopping

Helper text is wrapped in bounded authenticated records, never written raw to
the ACM descriptor. The new wire domain binds run, original nonce, frame type,
sequence and payload. At most 256 frames and one original native deadline are
allowed. Host raw capture precedes interpretation and is retained on error.

The separate witness verifies `getpid()==1`, current boot, actual readonly ext4
root device, partition RO, executable inode/hash on the RAM mount, full moved
mount identity, ECHILD and absence of other userspace. It closes state fd4 and
checks that only fd0–3 remain before emitting its post-exec proof. The target
kernel has no PID namespaces; `/proc/1/ns/pid` is not required. The witness's
RAM executable identity and native_data root identity remain separate facts.

`PASS_SWITCH_ROOT_WITNESS / PROVED_READONLY_HOST_PID1_ROOT_TRANSITION` requires
the authenticated post-exec record, not the earlier exec marker or native ACK.
A later failed return/capture preserves an already proved witness through
bounded H0 prefix rederivation. Prefix evidence does not close the owner, prove
Download/health, authorize a reconnect or permit another request. Missing or
invalid post-exec evidence remains NO_PROOF, including an early exit zero.

Any uncertain request, exec, child, transport or mount closes research. Helper
errors park; later BusyBox/kernel failures may leave unknown device activity.
Only the existing attended physical Download/original-A recovery remains.
The A transfer never repeats after proved completion; interrupted final reads
use health-only continuation. Android health is separate from witness proof
and cannot retrospectively prove native filesystem cleanup.

## H0 qualification and preparation

Independent review covers common/target adoption, real parent terminal dispatch,
worker/checker settlement, ARM64 syscall/mount flags, sealed state/FD remapping,
actual BusyBox and witness, bounded framing/raw preservation, compound intent
and all recovery interactions. Real ARM64 system-QEMU exercises the production
parent exec and helper/witness path on writable regular-file backing. The
backing disk must remain byte-identical. Virtual UFS/tty/return substitutions
are explicit and supply no Samsung hardware result.

Focused negatives cover wrong/dirty root, unknown children/waits, low FD holes,
mount/exec errors, absent/noexec/incorrect witness, stale or damaged records,
partial capture, early exit, lost return proof and owner no-replay/final-health
continuation. Unchanged prior rootfs and kernel compatibility checks are reused.
Current source-bound independent `s22plus_switch_root_v1_review.json`, actual
A/B boot-only qualification and fresh machine binding precede any live grant.

The foreground request adopts only the existing fixed Android preparation D0:
original-A root-health brackets, shell-v2, complete existing GPT metadata and
Android32 statfs, including retained-evidence reobservation after a pure read
failure. Preparation opens no grant and changes no device mode or filesystem.
Actual experimental transfer requires the returned finite attended start.

The separate first readonly A unit addresses the unproved retirement/root/
observation boundary. Its extra separation expires once that shared mechanism
is qualified; changes to mechanism, root mode, ownership or recovery trigger
review. Writable Debian continuation requires its separately adopted scope.
It is not an automatic second effect of this witness.
