# S22+ P413: USB-departure causal analysis and smallest next discriminator

Date: 2026-10-03 KST. Target: `SM-S906N/g0q/S906NKSS7FYG8` only.

## Finding and purpose

**P413's EOF belongs to an actual host USB-core disconnect episode.** The
retained host journal, exact native USB identity and installed CDC ACM driver
connect that departure to the observed tty hangup, zero-byte read and later
`TIOCNXCL` EIO. This is stronger than the preceding
[TTY-only assessment](S22PLUS_P413_EOF_FORENSICS_H0_2026-10-03.md).

**The trigger of the USB departure remains unproved.** Closing the target ACM
descriptor is still a hypothesis, not an established cause or a demonstrated
fix. A spontaneous USB re-enumeration followed about 24.43 seconds later, before
the recorded physical-recovery request. The operator reports no earlier button
or cable manipulation. A new authenticated kernel boot identity was not acquired,
so same-boot UDC/PHY cycling and whole-device reboot remain distinguishable
possibilities, not interchangeable conclusions.

The operator subsequently clarified that no physical unplug/replug occurred.
An intermittent contact fault was mentioned only as a possibility, not an
observed event. This excludes deliberate plug manipulation by operator account;
it does not establish uninterrupted electrical contact or prove a reboot.
The host's disconnect message describes device removal from its USB view,
without identifying whether the trigger was reset, link loss or contact loss.

The product goal remains installed Debian as host PID1, ordinary Debian
services, NCM, authenticated same-boot SSH and controlled shutdown. P413 proved
installed PID1 and rcS entry; it proved neither subsequent service failure nor
service success. Improving observation serves that goal. It must not become a
second native service manager or an open-ended prerequisite to useful boot work.

This unit used host files, existing execution evidence, public primary sources,
binary inspection and isolated host PTYs. It performed **zero device commands,
zero grants, zero new boot candidates and zero production-code changes**.
P413's consumed journal and healthy Android closure remain unchanged.

## New evidence: historical host logs

The bounded host kernel journal covers 19:44–19:47 UTC on 2026-10-02; a separate
30-second system-journal slice covers the cutoff. The kernel slice contains
23 records. Its host boot identity hashes to the P413 grant's recorded host
epoch. The native descriptor serial matches the pinned tty acquisition before
and after the departure. Raw identifiers and logs remain private.

| Host journal reception, KST | Evidence |
| --- | --- |
| 04:45:09.434 | The exact native ACM device and tty were registered. |
| 04:45:36.716 | USB core recorded device-level disconnect in the EOF episode. |
| 04:46:01.148 | The same native descriptor identity was registered again with a new enumeration. |

The durable observer stop belongs to the same failure window. There is no
release request, NCM transition, shutdown request or new host Download command
between the proved installed-init prefix and that stop. The later physical
recovery request was recorded around 04:46:53 KST; first machine recovery
preparation followed around 04:46:54. Re-enumeration therefore preceded those
recovery actions. It does not by itself prove a new kernel boot.

No controller-death, host reset, hub-wide removal or system-suspend message was
found in the bounded relevant logs. Absence of such messages is not a guarantee
that every host, electrical or PM event would have been logged.

The timing analysis deliberately separates clock domains. Journal entry
timestamps are reception times; raw kernel source timestamps are not calibrated
against the operation's `CLOCK_BOOTTIME`. Systemd copies one raw kmsg timestamp
into two legacy/current source fields; this is not two independent measurements.
The initially computed 0.128 ms numerical difference is **not** asserted as
physical disconnect-to-close latency. The causal conclusion uses the matching
episode and driver mechanism, not that false precision.
[Journal fields](https://www.freedesktop.org/software/systemd/man/latest/systemd.journal-fields.html),
[journald kmsg handling](https://github.com/systemd/systemd/blob/v259.5/src/journal/journald-kmsg.c#L259-L267).

The retained START-intent file's mtime is about 22.47 seconds before the journal
departure receipt. It is an advisory host publication time, not an authenticated
rcS-entry timestamp. The 26.873-second capture includes earlier preparation.
Neither number establishes how long `close(3)`, rcS or any particular script ran.

## Causal chain and competing explanations

The upstream USB-core removal path emits the disconnect message and removes
interfaces. The installed host module's `acm_disconnect` then performs a
synchronous tty hangup without checking CLOCAL. The hung-up tty returns zero
from read and EIO from ordinary ioctls. This matches P413. CLOCAL suppresses
carrier-loss hangup; it cannot preserve a USB device that has been removed.
[USB core](https://github.com/torvalds/linux/blob/e5ab27ddd74e2d67a94c51c6f2ad87b1ff13912b/drivers/usb/core/hub.c#L2296-L2346),
[CDC ACM](https://github.com/torvalds/linux/blob/e5ab27ddd74e2d67a94c51c6f2ad87b1ff13912b/drivers/usb/class/cdc-acm.c#L1611-L1689),
[TTY hangup behavior](https://github.com/torvalds/linux/blob/e5ab27ddd74e2d67a94c51c6f2ad87b1ff13912b/drivers/tty/tty_io.c#L418-L438).

| Hypothesis | Evidence and counterevidence | Assessment |
| --- | --- | --- |
| Ordinary idle, VMIN, canonical EOF or parser mistake | The consumer waits for readiness and retries EAGAIN/EINTR. Five local PTY cases separate idle, VMIN0 and canonical EOF from hangup: only hangup also produced the observed ioctl EIO. None explains the device-level USB-core removal. | Insufficient explanation. |
| Missing CLOCAL or premature host FD close | CLOCAL was set/read back; the host retains one transport FD until cleanup after EOF. Evidence-file closure is not transport closure. | Not supported. |
| Target last-close only lowers carrier | Exact target callback clears DSR/DCD and notifies; it does not unbind UDC. P413 already survived an earlier close/reopen between init proof and rcS entry. | Not sufficient; a deeper close-related kernel fault remains a different, unproved hypothesis. |
| Ordinary USB runtime autosuspend | Non-hubs default to power/control=on; the installed CDC driver does not enable autosuspend. Its open-reader path requires remote wakeup, while the native gadget explicitly writes/readbacks bmAttributes=0x80, without that capability. Current static host configuration has no matching enabling override. | Strongly weakened for the normal path. Historical per-device PM state was not captured; exceptional PM failure is not universally excluded. |
| Native userspace retirement stops watchdog petting | Exact packaged Qualcomm modules start a kernel SCHED_FIFO pet thread with userspace petting disabled. The transition settles three userspace workers; it does not remove that kernel thread or module. | Direct userspace-petting explanation contradicted by the selected machinery. |
| rcS intentionally resets USB or reboots | Exact SysVinit, selected scripts and RAM overlays contain no selected direct UDC/reboot path there. Console setup precedes stage 1, and the target has no USB serial console. | No matching deliberate action found. This does not make all script/kernel interactions inert. |
| mdev coldplug/firmware interaction | mdev -df really performs an initial sysfs scan and can process firmware events. However, the selected modules' only request_firmware import is in an explicit MAX77705 update path not invoked by this startup; ordinary helper fallback is disabled. | Reachable general functionality, but no selected startup-to-USB-failure chain established. |
| Unsupported close_range | The exact Image implements it; the same flags=0 syscall already succeeded during the proved transition and before installed init. | Generic ENOSYS explanation excluded. |
| Kernel oops/stall, UDC/PHY/Type-C restart or independent link loss | Compatible with device departure and spontaneous re-enumeration. The Image's build defaults enable panic-on-oops and immediate panic reboot; live overrides were not captured. No panic trace, reset-cause record or later authenticated boot ID selects among them. | Principal unresolved layer; individual causes cannot be ranked reliably from this run. |

The USB PM interpretation uses the actual selected machinery plus
[upstream PM rules](https://docs.kernel.org/driver-api/usb/power-management.html).
An open fd does not inherently prohibit autosuspend if another policy enables
it; default policy, remote-wakeup eligibility and ordinary suspend versus
reset-resume are separate conditions. No timeout adjustment or blanket PM
change is justified from silence alone.

## Kernel and startup checks beyond the first assessment

The watchdog's compiled pet/bark/nominal-bite intervals are 9.36/11/14 seconds;
its kernel petter can still fail through a stuck synchronous CPU IPI, scheduling
or timer failure, or hypervisor-backend failure. None was observed. The Image's
RCU stall timeout is 21 seconds, and retained vendor DTBs request panic on RCU
stall, but the live merged command line and a stall record were not captured.
The approximate 22-second host interval must not be promoted into an RCU or
watchdog diagnosis merely because the numbers are near each other.

The exact Debian SysVinit and BusyBox sources establish additional rcS work:
mdev's background initial scan can overlap later scripts, and firmware handling
is compiled in. The selected rules contain no command hooks; normal mknod and
permission updates do not open ttyGS or remove a gadget. Firmware requests were
also checked against all 72 selected stock modules and the kernel fallback
rules. This distinguishes an actually reachable mechanism from an attractive
but unsupported missing-firmware explanation.
[BusyBox 1.37.0 source](https://busybox.net/downloads/busybox-1.37.0.tar.bz2),
[firmware fallback semantics](https://docs.kernel.org/driver-api/firmware/fallback-mechanisms.html).

Known upstream serial-gadget bugs were checked for applicability. The
[June 2025 wakeup race](https://lkml.iu.edu/hypermail/linux/kernel/2506.2/00763.html)
shows an unconditional NULL wakeup; the actual P413 Image already has a NULL
guard at that call site. Other concurrent-disconnect paths remain possible,
but their runtime trigger was not observed. The
[July 2026 stale-endpoint report](https://lkml.iu.edu/2607.3/04120.html)
requires disconnect, delayed completion, endpoint destruction and reconnect.
No selected pre-release P413 path frees that gadget/function. Finding similar
code or a matching bug title is not proof that those prerequisite events
occurred, and is not a reason to patch the consumed kernel.

## Smallest next bounded development unit

Use a fresh H0 design/qualification of a **close-return/reopen barrier before
rcS spawn**, followed by parent-only observer-FD retention while ordinary rcS
runs. Keep child `close_range(3..,0)` before exec, the original deadline, one
script execution, current root admission and existing recovery ownership.

The useful records are: before close, close returned, reopen verified, child
spawn/exec boundary and child completion. Pair host receive timestamps with
bounded USB lifecycle records. A transmitted post-close marker proves that
close returned and reopening was verified; it does not prove that no transient
USB event occurred in between. No host reconnect, persistent debug write or
additional native daemon is part of this recommendation.

This is a discriminator and observability change, **not an asserted P413 fix**.
It shortens the interval with no open gadget tty and changes its later lifetime.
Success would prove that prospective arrangement works, not retrospectively
identify P413's trigger. Failure before the barrier localizes the boundary;
failure after it shifts attention to subsequent execution or independent kernel
and USB behavior. Add per-script instrumentation only if evidence then makes
it necessary; do not begin with a new diagnostic framework.

The functional completion criterion remains rcS/runlevel progress, 120 seconds
of sampled init/cron/sshd liveness, same-boot NCM/SSH and the selected shutdown
and recovery closure. Kernel/reset observations should help discriminate a
failure without replacing those product proofs. Root-cause perfection is not
a new gate on independently safe and useful functional progress.

Native_data cleanliness remains unproved after P413's writable lifetime. A
future physical run still needs fresh applicable root/health admission and its
own authority; this H0 analysis opens neither recovery nor replay authority.

## Verification and retained research

Four tracks covered timeline/causal synthesis, host transport, target
kernel/reset machinery and Debian startup. Methods included bounded historical
journal correlation; frozen source and exact ARM64/x86 module disassembly;
target configuration and module-import analysis; primary-source web research;
and five actual host PTY counterexamples. PTYs do not simulate Samsung USB
hardware, and upstream code does not replace exact target-byte checks.

The private bundle is
`workspace/private/outputs/s22plus-p413-causal-research-h0-20261003-1/`.
It contains raw journal exports, input hashes, corrected clock/chronology
records, source receipts, isolated reproductions and three independent track
results. The correlation and PTY scripts passed `py_compile` and execution.
Documentation links, privacy, diff and repository-boundary checks passed.
All consumed P413 pins and unrelated dirty work were preserved; A90 and S20+
were untouched. No physical test or image build was needed for this assessment.
