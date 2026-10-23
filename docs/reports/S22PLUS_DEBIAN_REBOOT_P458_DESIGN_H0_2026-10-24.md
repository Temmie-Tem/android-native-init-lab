# P458: ordinary Debian reboot — H0 design

## Bounded task

Establish the smallest successor to P456/P457 that can request one ordinary
Debian reboot and obtain two healthy Debian boots, retaining the same root and
SSH host key. First qualify the minimal SysV shutdown/reboot dependencies and
the second boot's admission/consumption model on private ARM64 VM disks. This
design precedes implementation. It creates no physical candidate, new grant,
policy activation or device effect. A90, S20+ and server work are outside scope.

The H0 completion criterion is executable evidence for the proposed two-boot
path and relevant interruption cases, a precise statement of remaining target
assumptions, and a concrete decision about the smallest physical successor.
An unresolved consumption gap is a negative result, not a reason to relax the
current admission or label a prototype ready for a device.

## Evidence and retained architecture

[P456](S22PLUS_DEBIAN_MINIMAL_P456_RUN_2026-10-24.md) proves the selected minimal
initial/installed Debian PID1, rc2, 120-second service observations and same-boot
SSH. The operator observed automatic power-off; the narrower machine trace
does not establish every filesystem shutdown step. [P457](S22PLUS_AUTOBOOT_PERSISTENCE_P457_RUN_2026-10-24.md)
authenticates both original run files after Android return, with whole-file
byte equality and a clean home-block superblock view. Both tasks are consumed,
closed healthy and have no active F1 owner.

Retain the FYG8 kernel, Debian-owned initial shell, minimal rcS program, packaged
rc2, CPU0/idle selection, first-gadget NCM and pinned SSH. Do not add a package,
cron workload, diagnostic marker experiment, soak requirement, new manager or
server. Ordinary reboot is the new functional question. A successful generic
VM reboot is not Samsung reset, USB, storage or recovery proof.

The sealed installed archive already has `l6:6:wait:/etc/init.d/rc 6` and the
rc6 sequence ending in `umountroot` then `reboot`. The current generated RAM
qualification command explicitly removes reboot. Its archived first-install
reboot branch also depends on a different workload/count and cannot be restored
verbatim. The current V3 automatic owner has one health stage and one shutdown;
its format/lease/A-return primitives are reusable, not its entire unchanged
execution identity.

## Admission and consumption question

Use exact first/second-boot paths and authenticated records, never wildcard
history. A first-boot completion record and a durable reboot intent have
different meanings. An intent alone neither proves that shutdown accepted a
request nor identifies what caused a later reset. The host must retain its
single command intent before transmission and never resend an uncertain
reboot. A different authenticated boot identity proves another boot, not the
absence of intervening boots.

File existence alone does not bound all attempts: an interruption after RW
mount but before durable creation can leave no consumption file. The first H0
test therefore examines actual ext4 recovery state and its ordinary mount
counter at this boundary. A possible second-boot guard derives an exact
expected mount count from authenticated first-boot evidence, rejects overflow,
and checks it before any new RW mount. It adds no raw superblock writer. The
retained generic source increments the counter and synchronously commits the
superblock on RW setup; target source and actual VM behavior still need checking.
This is a hypothesis to test, not an adopted safety argument.

| State or interruption | Required interpretation |
| --- | --- |
| Before first persistent effect | No first-boot success or consumed file is inferred. Existing startup uncertainty remains explicit. |
| First boot services complete | Same-boot service/SSH proof; reboot is not yet requested. |
| Intent durable, command uncertain | Command consumed; no retransmission, no inferred reset cause. |
| Next boot before RW admission | Clean exact root, authenticated first-boot input and the declared phase must agree. |
| Second RW mount, before file creation | Test whether recovery state/counter rejects another writable admission, including a clean error-unmount. |
| Second file durable or second services complete | A later boot must reject this consumed phase before another write. |
| Dirty, partial, foreign or inconsistent state | Stop before writes; no replay, repair, reinstall or automatic state reset. |

The test does not promise a bound on physical kernel starts or quiescence after
a kernel failure. It must identify the precise bound it actually supports on
admitted persistent work. First-boot pre-consumption uncertainty cannot be
silently declared solved by a second-boot guard.

## Evidence comparison and time ownership

Prefer the simplest exact final snapshot if it avoids a new record grammar.
If an authenticated reboot tail is needed, declare its permitted records and
comparison boundary explicitly; prefix equality is not whole-file equality.
P457's existing full-byte equality keeps its original meaning. A separate
post-return reader is optional if second-boot live evidence supplies the
required first-boot comparison.

Keep the existing 120-second service proof in each proposed installed lifetime.
Separate per-boot device BOOTTIME from the original host grant clock. The
second observation window must start from a fixed durable host event, not a
post-hoc choice between response and departure. Do not infer a new duration
from the first boot's 162.853-second host measurement or combine that value
with device uptime. VM timing cannot establish Samsung bootloader delay.

## H0 implementation and validation order

1. Inspect the hash-pinned archive's rc0/rc6 links and dependencies, the actual
   generated RAM command and minimal program, and relevant ext4 mount/remount
   source. Save bounded source receipts privately.
2. Reuse the existing generic ARM64 kernel, QEMU and installed archive in fresh
   regular-file fixtures. Exercise real packaged SysVinit, minimal rcS, rc2,
   ordinary reboot and shutdown. Identify every test-only substitution.
3. Interrupt at admission-before-mount, mount-before-file, durable consumption,
   intent-before-command and rc6, plus the normal two-boot path. Inspect VM
   disk copies offline without replay and enumerate changed paths. Add a clean
   error-unmount case because a hard kill alone cannot test that gap.
4. Exercise malformed/missing/consumed phase inputs and the real consumer.
   Preserve raw results before interpretation. Compile touched Python and
   cross-compile touched C with the existing ARM64 toolchain.
5. Record independent review of the resulting design and changed machinery.
   Only then select the physical implementation scope; the present automatic
   contract does not authorize an extra reboot or installed-root lifetime.

The relevant past-failure checklist rows are ABI, SEMANTIC, WIRE, PERSIST,
ROUTE, ARTIFACT, AUDIT and RETURN. IO applies to any new bounded evidence
channel. HOST is limited here to isolated fixture ownership; DISPLAY is not
selected. Checks and unresolved assumptions belong in the resulting H0 report.
