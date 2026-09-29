# S22+ Debian handoff: evidence and experiment plan

Date: 2026-09-30 KST. Target: `SM-S906N/g0q/S906NKSS7FYG8` only.
Status: **PROPOSED H0 DESIGN — not an implementation, capability activation,
candidate qualification or device grant.** No device commands were performed
for this review. P401–P408 consumed artifacts and journals remain unchanged.

## Decision

Keep the product goal: the initial PID namespace's PID 1 becomes Debian init,
Debian owns the root and ordinary services, and no independent native manager
survives alongside it. Reuse the proved kernel, installed root and preparation
components. Do not rebuild a distribution or retry the blind cold-bootstrap
path merely to obtain another missing-SSH result.

Use **one shared transition implementation, many internal checkpoints, and
three default functional experiment bundles**. First prove a readonly root
transition to a small static PID-1 witness from the working native startup.
Then prove actual Debian init and basic access. Then qualify persistence and
ordinary package/service lifecycle. These are proposed work units, not three
preauthorized runs or a claim that success is guaranteed in three attempts.

The first usable-system finish line remains the goal's full set: actual Debian
host PID 1/root, one service/device owner, authenticated Debian-owned access,
working DNS and a declared package/service workload, a changed-boot persistence
check, clean shutdown and independently proved return. A witness banner or
SSH login alone does not finish the product. Display, audio and Wi-Fi are later
features if USB provides the first qualified headless path.

The witness proof must be separate from the Debian-init proof. It does not
inherently require a separate flash in every future design. For the first
physical transition, a separate readonly witness run is preferable because it
avoids mixing an irreversible root transition with the first Debian writable
lifetime, service startup and USB ownership change. Conditional consolidation
criteria are below; there is no experiment for every individual syscall.

## Reuse the evidence at its actual scope

| Existing evidence | Established result | What it does not establish / next use |
| --- | --- | --- |
| [Rootfs/virt construction](../reports/S22PLUS_DEBIAN_BOOTSTRAP_H0_2026-09-21.md) | Locked Debian 13 arm64/SysVinit root; real ARM64 Linux 5.10 virt PID-1/root transition, SSH, selected packages/services, reboot and persistence | Samsung hardware, exact FYG8 kernel execution and target gadget/service ownership. Reuse the fixtures and successful unchanged checks. |
| P401 completion marker; [P402](../reports/S22PLUS_NATIVE_ROOT_INSPECTION_P402_FIRST_RUN_2026-09-23.md) and [P406](../reports/S22PLUS_NATIVE_ROOT_STATE_P406_FIRST_RUN_2026-09-26.md) | Retained installation, protected comparison, witness, clean-root observations and Android return | Historical markers do not identify a later stop or prove every following installer cleanup instruction. Preserve the existing root. |
| [P403](../reports/S22PLUS_NATIVE_USERSPACE_PROBE_P403_FIRST_RUN_2026-09-23.md) | Installed shell/libc/child execution on Samsung under the native owner | Host PID 1 replacement, complete init startup or hardware ownership after native retirement. Reuse its real exec/error/settlement accounting. |
| [P408](../reports/S22PLUS_NATIVE_STAGED_PREFLIGHT_P408_FIRST_RUN_2026-09-27.md) | All 17 protected stages, checker, 8,969-entry comparison, loader verify/list, cleanup, authenticated console and one original-A return | Its command is a child; parent native userspace remains during the probe. It does not mount writable root or perform switch_root. Reuse checks and parser concepts, not its consumed image/grant. |
| [P404/P405/P407 forensic audit](../reports/S22PLUS_BOOTSTRAP_FORENSICS_H0_2026-09-26.md) | No expected gadget registration in retained failed-boot host records; packaging, narrow ABI/DEFEX/module/parser hypotheses checked against actual artifacts | No exact historical fault instruction. Missing NCM is not proof of switch_root failure; P407 never calls switch_root. Do not reopen these hypotheses without changed inputs/new evidence. |
| P408's final-health interruption | Original A transferred once; failed ADB read was followed by successful health-only continuation | A second transfer was unnecessary. Reuse durable transfer proof, not a blanket restart of the experiment. |

Treat PROVED target behavior, PROVED virt behavior, static/source compatibility,
ranked inference and unknown history as different evidence classes. Record a
successful earlier stage even when the later boot or final observer fails.
Android health does not retrospectively prove native filesystem cleanup.

## Concrete constraints found in this review

1. **The current EXEC route cannot implement host-PID-1 replacement.**
   `rc1_spawn()` clones a child, makes a session and execs a BusyBox shell.
   This was checked in the actual retained P408 ELF, not only its template.
   Sending `exec switch_root ...` through that route still operates in the
   child. Add a narrowly fixed terminal transition owned by the real PID 1;
   do not disguise it as another ordinary probe command.
2. **Reboot cleanup is not complete handoff cleanup.** The actual P408
   `local_close()` calls `hud1_stop()`. Its compiled loop checks each worker
   once and may send SIGKILL, then returns without a final all-children-reaped
   proof. This is not a newly diagnosed defect in its existing reboot role.
   Handoff needs finite settlement, descriptor/mount ownership and a last
   storage-availability check after retiring native workers. Do not promote
   a signal request or the old CONTROL ACK into that proof.
3. **There are two different BusyBox inputs.** The retained native observer
   uses v1.36.1; the Debian construction input is v1.37.0. The latter's actual
   static binary is 1,975,064 bytes, SHA-256
   `7d93682be37cf6ed46699f6fff546b80bf133cf8ec342c2d04bc23387f78bc34`.
   Select and pin the intended implementation explicitly. Existing evidence
   about one `/bin/busybox` must not silently qualify the other binary.
4. **The old handoff message precedes exec.** In
   [handoff.c](../../workspace/public/src/debian/s22plus_v1/handoff.c),
   writable mounting, mount moves and the message precede BusyBox exec.
   Capture evidence emitted by the new program after exec as a separate fact.
   Ordinary EXEC completion/DETACH semantics cannot be demanded from a PID 1
   that has intentionally replaced itself; define a transition-specific result.
5. **Native ACM and Debian NCM need one ownership transition.** The current
   [lab-usb](../../workspace/public/src/debian/s22plus_v1/device/lab-usb)
   assumes Debian owns gadget setup. A native-first predecessor may leave its
   ACM gadget bound. Define when its process/fd owner ends, when the gadget is
   unbound and when Debian creates NCM. A root transition alone does not perform
   that work. Preserve the witness before deliberately losing the old link.
6. **Use the actual kernel's facilities.** Re-extraction of the consumed P408
   Image verified its declared hash and obtained config SHA-256
   `8a37e3ccbe2c36623e2c57f54feb2104a3159f7963345405380805394c277c76`.
   PID/user namespaces, devtmpfs and FHANDLE remain disabled. Do not design a
   target witness that requires `/proc/1/ns/pid` to exist or a target container.
   Establish PID 1 on this bound kernel, root device/type and process ownership.

The [BusyBox 1.37 source](https://sources.debian.org/src/busybox/1%3A1.37.0-6/util-linux/switch_root.c/)
shows an ordered userspace operation: validate PID/rootfs, remove old-root
contents, move the new mount, chroot and exec the selected program. It is not
one atomic switch_root syscall. The
[Linux 5.10 initramfs documentation](https://docs.kernel.org/5.10/filesystems/ramfs-rootfs-initramfs.html)
explains why rootfs needs this treatment. A failed late exec cannot be assumed
to leave the original runtime usable; Linux also has an exec point of no return
([upstream 5.10 exec source](https://github.com/torvalds/linux/blob/v5.10/fs/exec.c),
corresponding condition checked in the retained FYG8 source tree).
Use physical original-A recovery as the existing external fallback; do not
promise a return by execing a deleted old initramfs.

## Choose the transition origin

| Route | Benefit | Additional uncertainty | Decision |
| --- | --- | --- | --- |
| Repeat the standalone P405-style cold bootstrap with more RAM logs | Small delta to that bootstrap | Its logs remain unavailable if modules/cleanup/USB startup fail before retrieval | Preserve for causal comparison; not the next default physical experiment. |
| Existing native EXEC child runs a transition program | Easy reuse of command transport | Wrong PID, child mount namespace, privilege/context differences | Reject as host-PID-1 proof. Useful only for bounded preparation tests. |
| Working native startup, then a fixed parent-PID-1 terminal transition | Observation is established before retiring the native runtime; reuses proved storage/transport setup | Requires complete native retirement and explicit descriptor/gadget succession | Preferred next H0 implementation and first physical witness route. |

This is a development route to full Debian ownership, not a product with two
supervisors. The native component ends at handoff. Keep the necessary loaded
kernel drivers; do not unload/reinsert them merely because userspace changed.
Do not strip proven bring-up dependencies at the same time as introducing
handoff. Once the full path works, reduce the temporary bootstrap separately.

## Shared proof sequence and three experiment bundles

The shared implementation records these boundaries in one boot:

```text
authenticated native health and fixed transition intent
  -> exact protected root/checker/content admission
  -> retire native workers; reap; close unrelated descriptors
  -> prove root/storage still accessible and mount ownership settled
  -> prepare fixed next-root mounts and RAM witness
  -> move /dev, /proc, /sys, /run with declared nested mounts
  -> PID 1 execs the selected BusyBox switch_root
  -> static witness executes as PID 1 under the new root
  -> [A: bounded witness result and return]
     [B/C: exec the original installed Debian init]
  -> independent Debian PID-1/root and service evidence
```

**A — readonly root-transition witness.** One fresh candidate retains partition
RO and a readonly native_data root. It combines protected admission, native
retirement, mount moves, switch_root, post-exec witness and original-A closure.
Do not split those into separate flashes: their same-boot ordering and resource
ownership are the question. The static witness may be carried on a fixed RAM
mount moved under the new root; it need not be installed into native_data.
Its location must actually permit exec. Existing noexec `/s22-root-work`, and
Debian's eventual noexec `/run`, cannot be ignored. It proves its own RAM
executable identity and the native_data root separately.

Required witness facts: the bound run/current boot, `getpid()==1`, the exact
new-root device and ext4 identity, readonly state for A, declared mount moves,
no surviving old-root userspace, and the descriptor whitelist. Transported
proof must be framed, bounded and bound to the original authenticated run;
no mutable RAM file or arbitrary success banner is sufficient. Holding an
old-root descriptor to inspect it would itself retain that root: avoid such
references in the claimed final state. Report only the cleanup actually proved.

The new terminal request must not accept a caller program/path or inherit the
generic command's shell semantics. The parent must retain the privileges needed
for handoff; P403's unprivileged child settings are not the PID-1 contract.
Likewise, reuse pure root-validation/checker components without assuming that
P408's private child mount becomes the parent's new root. Preserve the existing
native command/reboot paths; qualify the new transition path independently.

**B — actual Debian PID 1 and basic headless access.** Use the same transition
and witness with a separately selected writable-root lifetime and fixed final
exec of `/sbin/init`. A's partition-RO state persists until reboot; B uses a
fresh boot and its own admitted writable lifetime, not an unapproved RO-clear
inside A. Capture the post-switch witness, then Debian's actual PID-1 executable,
root and boot identity. Early init/rcS milestones must be observable before
lab-usb/SSH so that missing networking cannot hide an already completed handoff.
Combine boot, basic Debian-owned USB/NCM/SSH, essential service ownership and
orderly shutdown/return in this bounded unit. Keep their verdicts separate.

Transfer the temporary diagnostic endpoint to a short-lived Debian-owned
observer if required to see early services, then retire it at the declared
point. It must not become a hidden native control plane. The old native UDC
binding and descriptors must not compete with `lab-usb`. Failure after a proved
witness or Debian PID 1 preserves that proof; it does not restart the boot.

**C — useful runtime and persistence.** Once B has independently proved boot,
access and shutdown, combine one declared package/service workload, persistence
markers, one ordinary reboot with changed boot ID, reobservation, clean shutdown
and final return. Reuse the existing virt-tested `hello`/cron/logging checks and
one-use command receipts. An extra candidate boot for each package command
would add little evidence. General upgrades of bound core files are a later
identity/update design, not implied by one successful additional package.

Separate offline package execution from DNS/repository reachability in the
results. Include the declared real network/DNS and authenticated apt path before
claiming the useful-runtime goal complete; offline `hello` alone cannot supply
that evidence. Host peer/routing setup is an explicit prepared input, not a
hidden firewall or network change during the device deadline. Under the same
bounded ordinary workload, observe liveness and the declared power/thermal
health needed for that session. Loaded drivers alone do not qualify a stable
long-running or unattended system.

P408's exact archive-plus-four inventory is an initial diagnostic criterion.
After authorized Debian operation creates logs, counters and package state,
use the declared mutable-root rules of the installed system. Do not weaken the
consumed P408 validator or falsely call legitimate declared changes corruption.
Preserve the original root evidence and record the new writable lifetime.

### When to merge or split

- Merge work that shares one boot/owner and produces independently classifiable
  checkpoints: root checks with retirement/transition; Debian boot with basic
  service/access tests; package work with its persistence reboot.
- Split at a change in recovery or persistent-write semantics, an unobserved
  irreversible boundary, or a newly demonstrated hazard. The first A/B split
  is justified by readonly transition versus Debian writable/service lifetime.
- A and B may share one future physical run only if the shared witness is
  independently validated in H0, its result is collected before continuation,
  observation survives the relevant transition, and the reviewed grant already
  includes the writable continuation and recovery. A readonly success still
  does not prove the writable continuation. Do not add an unreviewed BLKRO clear.
- Do not require fresh independent review solely for a namespace/hash change.
  Review the shared transition/authority/recovery machinery once, then requalify
  permitted candidate data within that exact scope. Current P405- and
  P408-specific lanes do not already provide that new reusable scope.
- Stop at the stated unit's success and relevant checks. A negative result
  triggers its evidence-selected next branch, not a larger list of probes.

The separate first-A run addresses the currently unproved transition and
retirement boundary. Its need expires after that shared path and observable
post-switch state are qualified; revisit it when those mechanisms, root mode
or target assumptions change. It is not a permanent extra run for every image.

## Methods selected by the question they can answer

| Method / cost | Use now or on this trigger | Observable result and limit |
| --- | --- | --- |
| Retained raw replay, timeline and archive joins / low | First, before every new hypothesis | Determines what was actually sent/received and which artifacts ran; cannot recover unrecorded events. P408 need not be replayed. |
| `readelf`, `nm`, focused ARM64 objdump / low | Actual helper, switch utility, syscall/flag or generated-code mismatch | Matches ELF/ABI/call order to source; not proof the device executed the branch. Current P408 clone/retirement disassembly was checked here. |
| Exact function-byte/kernel-source comparison / moderate | A named kernel/LSM failure becomes plausible | Distinguishes build/source mismatch or a specific guard; no assumed symbols from a merely similar vmlinux. Keep raw addresses private. |
| Real ARM64 system QEMU, shared C paths, disposable writable disk / moderate | New PID-1 transition, worker settlement, mounts/fds and evidence protocol | Positive and negative semantics with disk-before/after checks; virt hardware substitutions remain explicit. Reuse the retained 5.10 fixtures. |
| qemu-user/syscall tracing / low | Static loader/libc/syscall ABI question | Useful for executable entry/errors; cannot prove PID 1, root mount transition, Samsung drivers or hardware timing. |
| C/PTY stream and retained-prefix faults / low | Protocol fragmentation, interrupted capture, bad framing/HMAC or stale boot | Tests producer/consumer evidence integrity. It is not a physical USB-disconnect experiment. |
| Same-boot target stage records and post-exec witness / physical | Only after the new capability/artifact is qualified | Direct progress and state proof; a missing end narrows an interval, not necessarily one faulting instruction. |
| Targeted tracepoints/kprobe/uprobe / conditional | An authenticated stage identifies a kernel/driver/exec interval still unresolved | P408 config enables probe events and BOOT_CONFIG, but actual availability, exact sites, finite buffers and retrieval need qualification. Not automatically a D0 action. |
| Function graph/syscall ftrace / unavailable as proposed | Only with a separately justified kernel change | Actual P408 has FTRACE but lacks FUNCTION_TRACER and FTRACE_SYSCALLS; generic ftrace recipes do not apply unchanged. |
| Dynamic debug / conditional | Relevant compiled callsites exist in the selected component | DYNAMIC_DEBUG is off, CORE is on. Per-module support must be established; arbitrary kernel-wide pr_debug activation is not assumed. |
| pstore/ramoops / optional fallback | Exact reserved backend and retrieval survival are demonstrated | Configuration enables support, not successful capture. Do not make this the primary witness or import S20+ evidence/addresses. |
| strace/ptrace or GDB / mostly H0 first | A narrowed userspace failure needs syscall/instruction detail | Changes timing and sometimes privilege/exec behavior. Check target support and the threat model before a device plan. |
| UART/EUD, raw dumps, panic injection or broad instrumentation | Not selected | Existing boundaries do not authorize them. A menu of techniques is not authority or a reason to delay the minimal working path. |

The tracing constraints were checked against the actual P408 Image, then
compared with official [ftrace](https://docs.kernel.org/5.10/trace/ftrace.html),
[boot-time tracing](https://docs.kernel.org/5.10/trace/boottime-trace.html),
[dynamic debug](https://docs.kernel.org/5.10/admin-guide/dynamic-debug-howto.html)
and [ramoops](https://docs.kernel.org/5.10/admin-guide/ramoops.html) documentation.
No tracing, pstore or firmware change was made on a device in this review.

## Result-driven branches

| Last proved boundary / failure | Next bounded investigation |
| --- | --- |
| No initial native authentication | Native startup/endpoint path. Preserve bounded host enumeration; do not infer a switch_root failure. |
| Root admission passes, worker retirement/storage recheck fails | Exact worker, wait status, retained fd or DRM/provider lifetime. Use focused source/disassembly and a corresponding VM fault. Do not leave an old native process alive to call ownership complete. |
| Pre-switch record captured, witness absent | Compare actual BusyBox, rootfs/newroot topology, mount flags, inherited descriptor disposition and exec failure path; then use a scoped kernel trace only if this cannot distinguish the remaining interval. |
| Witness valid, Debian PID 1 absent | Original init ELF/loader entry and SysVinit early path; use already proved switch mechanism unchanged. |
| Debian PID 1 valid, NCM/SSH absent | Debian rc ordering, gadget ownership, network and SSH separately. Preserve the PID-1 result rather than restarting handoff research. |
| Runtime works, next boot or persistence fails | Writable-root lifecycle, declared mutable state, shutdown sync/unmount and new-boot identity. Preserve filesystem evidence; no automatic repair/reinstall. |
| A transfer proved, final ADB health interrupted | Existing health-only continuation from the journal; no second transfer. |

## Next implementable H0 unit and completion criteria

The next work unit is **the shared PID-1 transition plus readonly witness**, not
another broad rootfs rebuild or an immediate phone boot. Its outputs are:

1. A small fixed parent transition and static witness, explicit worker/mount/fd/
   gadget ownership, exact selected BusyBox and an authenticated bounded record.
   Preserve the existing ordinary EXEC and Download meanings.
2. A real ARM64 virt rehearsal of that shared transition. Positive proof must
   include actual PID/root/executable/mount state and complete worker settlement.
   A's writable backing remains unchanged. Compare physical/virt builds and
   enumerate only the hardware-discovery substitutions.
3. Focused failures: wrong/same root, non-PID-1 invocation, busy/unknown child,
   mount move failure, noexec or missing witness, early zero/incorrect witness,
   dropped/partial/stale authenticated records, failed init exec and loss of
   post-transition transport. Missing evidence never becomes success or replay.
   Avoid tests that merely restate a growing catalog or manufacture a PASS flag.
4. Actual boot-only A/B artifact joins, finite host owner/no-replay/final-health
   tests, and the required independent review of the changed contract, terminal
   command, PID-1 privilege, writable/readonly distinction and recovery.

Only then prepare a concrete fresh physical A task. There is no reason to ask
for a speculative execution approval now. The current P408 grant is closed;
the new capability needs its own adopted scope and returned finite attended
grant. A90/S20+ sources, artifacts and authority are not part of the work unit.

## Review evidence retained

Private base:
`workspace/private/outputs/s22plus-handoff-plan-review-h0-20260930-1/`.
This review saved the 15 search results across three search angles and four
official-page fetches, the exact P408 config extraction, retained BusyBox
identity and four focused disassemblies of the actual P408 init. Historical
forensics and successful unchanged VM results were reused, not rerun.
No new payload was built and no new live capability is claimed by this plan.
The retained AP, Image and disassembled init were joined back to the qualified
build's identities. `evidence-index-final.json` has SHA-256
`1a3e1e2b076fde6e24107d0f697d68b0d1831bbaf5e4867bc472c9f74b50d9c4`.
