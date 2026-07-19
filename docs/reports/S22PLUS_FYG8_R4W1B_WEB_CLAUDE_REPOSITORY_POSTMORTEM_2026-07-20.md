# S22+ FYG8 R4W1-B Web / Claude / Repository Postmortem

Date: 2026-07-20 KST

Scope: host-only, read-only investigation. No device contact, image build,
transfer, flash, or policy activation occurred in this unit.

## Verdict

R4W1-B remains `NO_PROOF`, not a candidate failure. The candidate AP transfer
completed, but the live helper lost the load-bearing observer path before
rollback. A stale Odin path was treated as fatal during disconnect observation,
and endpoint discovery plus operator confirmation shared one 120-second budget.
The normal Download endpoint appeared only when that shared budget was already
exhausted. The later recovery-only helper restored and verified Magisk, but did
not collect the first rollback boot's `/proc/last_kmsg`.

The strongest device-side explanation for a parked raw PID1 is not new. FYG8's
watchdog ownership and the required module closure were already live-proven by
M31B. The new investigation restores that evidence to the R4W1-B interpretation:

- normal FYG8 `modules.load` begins with `gh_virt_wdt.ko` and
  `qcom_wdt_core.ko`;
- the FYG8 DT binds Samsung's watchdog wrapper to
  `hypervisor:qcom,gh-watchdog`;
- M31B loaded `smem`, `minidump`, `qcom-scm`, `qcom_wdt_core`, and
  `gh_virt_wdt`, then survived the previous approximately 30-second PMIC/PON
  ceiling for the full 120-second observation window; and
- exact bootloader RE proved the UEFI watchdog is disabled at
  ExitBootServices, so later bare-PID1 timeout belongs to a post-handoff owner
  or policy.

An RDX screen is not by itself evidence that the candidate reset or that PID1
was rejected. M31B also reached an RDX `PMIC abnormal reset` screen during
manual Download recovery after its 120-second survival result was already
closed.

## Evidence Boundaries

### Proved

- Exact R4W1-B boot-only candidate transfer completed.
- Exact Magisk boot-only recovery completed and final Android health passed.
- The host helper encountered a stale `/dev/bus/usb` path after disconnect.
- Endpoint discovery consumed the confirmation budget.
- No post-candidate retained observer was captured.
- M31B established that the stock watchdog closure removes the prior park
  survival ceiling.

### Not proved

- R4W1-B `/init` execution or rejection.
- First EL0 instruction execution.
- The reset cause or exact timing during the R4W1-B candidate interval.
- Marker loss, cache visibility failure, or retained-buffer corruption.
- That RDX was entered automatically rather than as part of the operator's
  manual Download transition.

## External Reference Findings

### USB re-enumeration

Linux documents USB bus/device numbers as unstable identifiers that must not be
saved as persistent device identity. libusb also documents hotplug callback
ordering and pairing limitations. udev receives kernel add/remove/change
uevents, but those events are best used as wake-up hints rather than transfer
authority.

Application to this repository:

1. Treat each Odin appearance as a new endpoint generation.
2. Poll snapshots remain authoritative; udev/libusb may only wake the poller.
3. A path returned by `odin4 -l` but absent from the filesystem is stale
   evidence, not a live endpoint and not a fatal disconnect error.
4. Immediately before transfer, require exactly one live endpoint and
   revalidate the same generation.

References:

- https://www.kernel.org/doc/html/v4.11/driver-api/usb.html
- https://libusb.sourceforge.io/api-1.0/group__libusb__hotplug.html
- https://www.freedesktop.org/software/systemd/man/devel/udev.html

### Crash-resumable update discipline

Android A/B, Mender State Scripts, and SQLite atomic commit are not direct
implementations for this non-A/B Odin workflow, but their transaction semantics
apply:

- candidate transfer is at-most-once;
- success is not committed before post-boot evidence;
- rollback is mandatory after consumption;
- recovery resumes the same durable transaction instead of opening an
  evidence-blind second operation; and
- every externally visible phase receives an immutable, fsynced receipt before
  the next destructive transition.

SQLite itself is not adopted. Immutable JSON receipts and an append-only JSONL
index preserve the repository's transparent SHA-pinnable evidence model.

References:

- https://source.android.com/docs/core/ota/ab
- https://docs.mender.io/artifact-creation/state-scripts
- https://sqlite.org/atomiccommit.html

### First-stage module ownership and distro handoff

AOSP lists watchdog, reset, and cpufreq among essential first-stage drivers.
This independently matches FYG8 `modules.load` and M31B. Halium demonstrates the
later architectural shape: an Android-compatible boot image starts an initramfs,
mounts a Linux rootfs, performs `switch_root`, and execs systemd. Halium's
userdata rootfs and Android container are not adopted here, but the staged
handoff contract is applicable after the S22+ first-stage hardware floor and
observer are stable.

References:

- https://source.android.com/docs/core/architecture/kernel/boot-time-opt
- https://source.android.com/docs/core/architecture/partitions/generic-boot
- https://docs.halium.org/_/downloads/en/latest/pdf/

### Retained log limits

Ramoops requires a dedicated persistent RAM region and registered backend. The
current FYG8 baseline has no pstore console path, and prior ramoops attempts did
not establish a backend. It is therefore a separate future instrumentation
rung, not an R4W1-C dependency.

The current marker's `smp_wmb()` orders stores. It is not a cache-clean or reset
durability primitive. No cache-maintenance change is justified until a clean,
transaction-complete rollback observer repeatedly shows marker absence.

References:

- https://docs.kernel.org/admin-guide/ramoops.html
- https://docs.kernel.org/core-api/wrappers/memory-barriers.html

## Claude Opus Review

Claude Opus 4.8 independently recommended:

- endpoint generations with snapshot polling as authority;
- independent endpoint-wait and human-confirmation deadlines;
- immutable per-phase receipts plus append-only transaction indexing;
- an at-most-once candidate with mandatory exact rollback;
- recovery as transaction resume;
- no SQLite engine, A/B slot emulation, ramoops dependency, or watchdog disable;
  and
- preserving the existing retained witness until a complete observer result
  proves a kernel-side change is needed.

The Opus pass initially classified watchdog handoff as a new hypothesis. The
subsequent repository cross-check strengthened and corrected that statement:
M31B already made watchdog management a live-backed mechanism, not a fresh
speculation.

Usage before the Opus round was 55 percent of the five-hour session and 20
percent of the weekly allowance. Afterward it was 99 percent and 23 percent.
The existing session was above 150k context, so no second Opus round was spent
after the repository correction.

## Decision

Do not modify or reuse the retired R4W1-B helper, pins, acknowledgement, or
candidate. Preserve them as historical evidence.

Proceed host-only with a new reusable transport transaction core and tests.
The next candidate design may reuse the exact kernel-side exec-accept marker but
must use an M31B-derived watchdog-managed carrier, and its recovery path must
capture the first rollback observer before final classification. Any R4W1-C
device action still requires a separately built, reviewed, SHA-pinned,
policy-bound one-shot gate and fresh operator approval.
