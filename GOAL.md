# Goal: S22+ boots into Debian with full userspace ownership

Build a usable Debian arm64 system on dedicated storage, with Debian's init
as **host PID 1 in the initial PID namespace** and Debian owning the running
system's services, devices, networking, logging and shutdown. The operator
selected this full handoff on 2026-09-16: a resident native supervisor with a
Debian chroot or an isolated Debian child is not the product architecture.

The actual allocation is **32 GiB Android userdata and 191.4580078125 GiB
native storage**. Start with the FYG8 vendor kernel. Reduce native userspace to
the device-specific early boot work needed to start Debian, then replace that
bootstrap with Debian init. Do not implement a second general Linux runtime
inside native init. Existing native capabilities are implementation inputs;
they are not all prerequisites for Debian boot or permanent background owners.

First deliver an independently booted, persistent headless Debian system with
authenticated SSH and an ordinary package-managed service. Display/input and a
desktop are later capabilities. Android remains a separately booted management
and recovery environment, not a provider of the running Debian userspace.
This goal records state, never device authority. Select only the operator-owned
`SM-S906N/g0q/S906NKSS7FYG8` through `AGENTS.md` and its binding target contract.
A90 and S20+ remain isolated.

## Current synthesis and functional priority

[P453 mountkernfs analysis and reader design](docs/reports/S22PLUS_MOUNTKERNFS_P453_ANALYSIS_H0_2026-10-23.md)
is the selected H0 unit. Exact script/callee analysis and diskless ARM64 runs
separate source-time work, reused mounts and the three new model mounts.
A controlled pstore-mount failure still returns script exit 0; script status
alone is not mount/service proof. P452 does not identify the blocking call.
Prepare the existing mountless exact P452 early/runtime reader first, with
fresh A/B qualification and current source-bound review. No device effect,
new writable history or script-skipping change is selected by this H0 work.

[P452 rcS channel](docs/reports/S22PLUS_AUTOBOOT_RCS_P452_RUN_2026-10-23.md)
is consumed and `ANDROID_CLOSED_HEALTHY`. The live service/SSH outcome remains
`NO_PROOF`. Post-return evidence proves installed Debian PID1, dispatcher entry
and successful `S01hostname.sh` completion. The strict collector retains 135
transitions including three script packets. One separately authenticated frame
on a noncanonical line adds the next `S01mountkernfs.sh` BEGIN boundary; it is
not merged into the strict result and does not prove a stall or script return.
rcS completion, 120-second services, SSH and clean shutdown remain unproved.

The bounded retained range contains three authenticated candidate boots, with
the first kernel header already outside the retained fragment. The operator
reported one accidental additional boot while attempting physical Download;
its exact span assignment and the other reset causes remain unknown. One N/A
pair is proved, with original-A recovery after the research grant expired.
Closure preserves 424 raw captures and the unchanged 15-row journal, including
one post-A read failure followed by health-only continuation. The fixed
same-returned-boot D0 adds 16 successful captures. No F1 owner remains.
Current native_data consistency and P452 early/runtime files are unmeasured.

The next H0 analysis can follow the authenticated second-script boundary into
the exact retained mountkernfs script and its callees; it must not assume that
missing later packets locate the failure. Another writable candidate requires
separate current-file qualification and fresh complete protected admission;
P452 is never replayed. The [design](docs/reports/S22PLUS_AUTOBOOT_RCS_P452_DESIGN_2026-10-21.md)
and [H0 qualification](docs/reports/S22PLUS_AUTOBOOT_RCS_P452_H0_2026-10-21.md)
retain all 37 ARM64 integration cases, 13 component cases, 123 focused tests,
actual A/B packages and the source-bound independent `PASS_GO`. Their normal
VM service/SSH/shutdown success remains H0 evidence. A90 and S20+ were untouched.

[P450 fixed journal recovery](docs/reports/S22PLUS_JOURNAL_RECOVERY_P450_RUN_2026-10-21.md)
is consumed and `ANDROID_CLOSED_HEALTHY`. Strict replay completed 24 writes /
95,232 bytes, the read-only checker passed, and protected unmount/partition RO
and state 1 / RECOVER 0 / orphan 0 are proved. All 8,971 expected entries match,
but eight tree entries remain outside the selected accounting:
`RECOVERY_NOT_PROVED`. The difference does not identify paths or admit another
writable Debian boot. Closure rederived 683 raw captures and the unchanged
20-row journal, with one post-A read failure and health-only continuation.
One N/A pair is consumed; the grant is closed and no F1 owner remains.

The separate [P451 post-replay read](docs/reports/S22PLUS_AUTOBOOT_EVIDENCE_P451_RUN_2026-10-21.md)
also closed `ANDROID_CLOSED_HEALTHY`. It captured P448's complete early/runtime
pair: 10,972/1,024 bytes and 14/6 authenticated records, matching boot and nonce.
The early bytes equal P449's original capture; both files join only P448's
first retained boot. Runtime reaches installed-init/rcS entry and fork, with
one CPU0/watchdog-enabled sample. It proves no hardware renewal, continuous
CPU state, rcS completion, 120-second services, SSH or clean shutdown.
The partition-RO mountless view is state 1 / RECOVER 0 / orphan 0. Closure
rederived 616 raw captures and the unchanged 20-row journal, with one post-A
read failure and health-only continuation. One N/A pair is consumed; both
tasks are closed and no F1 owner remains. P450's complete-root rejection and
P448's second-boot/reset uncertainty remain unchanged. Current history
qualification and complete protected admission precede another writable boot.

Both approved operations ran through reviewed operator-terminal entry points
because the agent process's `NoNewPrivs=1` blocked the mandatory host census.
The original checks and approvals stayed intact; P450's initial host-only
failure remains preserved. The retained
[P450 qualification](docs/reports/S22PLUS_JOURNAL_RECOVERY_P450_H0_2026-10-21.md)
and [P451 qualification](docs/reports/S22PLUS_AUTOBOOT_EVIDENCE_P451_H0_2026-10-21.md)
include actual A/B packages, five fresh ARM64 cases,
focused tests, both independent PASS_GO reviews and 17 preparation D0 captures
per task. A90 and S20+ were untouched.

[P449's fixed read](docs/reports/S22PLUS_AUTOBOOT_EVIDENCE_P449_RUN_2026-10-21.md)
is consumed and `ANDROID_CLOSED_HEALTHY`. It recovered P448's complete
10,972-byte early file: all 14 records authenticate through `EARLY_PRE_UNMOUNT`
and join the first retained P448 boot. Runtime is `ABSENT_IN_HOME_VIEW` with
`state=1, recover=1, orphan=0`; no mount, replay or filesystem write occurred.
The missing peer does not prove non-execution or permit a paired boot/nonce
join. Closure rederived 628 captures and the unchanged 20-row journal, with
one post-A read failure and health-only continuation. One N/A pair is consumed,
the grant is closed and no F1 owner remains. Its selected journal-recovery and
post-replay read are now completed by P450/P451 above; another writable Debian
boot still awaits current storage/history admission.
The [qualification](docs/reports/S22PLUS_AUTOBOOT_EVIDENCE_P449_H0_2026-10-21.md)
retains A/B packages, two new ARM64 cases, 33 tests, independent PASS_GO and
17 fixed preparation reads. A90 and S20+ were untouched.

[P448's single-CPU physical experiment](docs/reports/S22PLUS_AUTOBOOT_SINGLECPU_P448_RUN_2026-10-21.md)
is consumed and `ANDROID_CLOSED_HEALTHY`: one N and one original A, all 704 raw
captures and 14 journal rows rederived, grant closed and no F1 owner. The live
360-second observation obtained no NCM/SSH proof. Post-closure fixed D0 adds
16 successful captures on the same returned Android boot. Its unchanged
strict collector authenticates 131 first-boot transition records; a separately
authenticated frame proves the first rcS sleep returned zero. Installed Debian
PID1 and rcS fork are proved, but rcS completion, 120-second services and SSH
are not. The kernel reports the selected maxcpus setting and one processor.
Two distinct candidate boots are authenticated in retention; reset timing,
cause and relation to physical recovery remain unknown. Current native_data
consistency and current-run files were unknown at P448 closure; P449 above
now supplies the early file and dirty home-view observation.

[P448 H0 qualification](docs/reports/S22PLUS_AUTOBOOT_SINGLECPU_P448_H0_2026-10-21.md)
retains the actual A/B archive, 27 ARM64 cases, policy adoption and independent
PASS_GO. Normal VM SSH samples span 120.690 seconds; that result is not promoted
to physical success. The selected path uses P441 proc observation and eight
exact historical rows, without P445 phase instrumentation.
[P447](docs/reports/S22PLUS_AUTOBOOT_EVIDENCE_P447_RUN_2026-10-21.md) supplied only
P445's authenticated complete early file from a clean observed home view;
its runtime absence was never treated as non-execution or a fabricated row.
P445, P447 and P448 remain consumed. A90 and S20+ were untouched.

The preceding physical phase-observer campaign is closed.
The [bounded phase-observer design](docs/reports/S22PLUS_AUTOBOOT_PHASE_OBSERVER_DESIGN_2026-10-20.md)
selected implementation of actual watchdog/rcS progress observation while
preserving the Debian service/SSH goal. [P442](docs/reports/S22PLUS_AUTOBOOT_EVIDENCE_P442_RUN_2026-10-20.md)
consumed one attended N/A pair and closed `ANDROID_CLOSED_HEALTHY`.
It captured the complete 10,972-byte early file: all 14 records authenticate
through `EARLY_PRE_UNMOUNT` and match P441's first boot. The source is dirty
(state 1/RECOVER 1/orphan 0); runtime is `ABSENT_IN_HOME_VIEW`, not non-execution.
Closure rederived 649 captures and the unchanged 20-row journal; one post-A
read failure required only health continuation. No F1 owner remains.
Any strict replay, post-replay retrieval and new writable-root admission remain
separate. The [qualification](docs/reports/S22PLUS_AUTOBOOT_EVIDENCE_P442_H0_2026-10-20.md)
retains A/B packages, ARM64 cases, 33 tests and independent PASS_GO.
The separate [P443 strict replay](docs/reports/S22PLUS_JOURNAL_RECOVERY_P443_RUN_2026-10-20.md)
consumed one N/A pair and closed `ANDROID_CLOSED_HEALTHY`. Its 24 writes /
95,232 bytes and read-only checker completed; partition RO, protected unmount
and clean superblock are proved. All 8,971 expected entries match, but five
tree entries remain outside the selected accounting: `RECOVERY_NOT_PROVED`.
Closure rederived 600 captures and the unchanged 20-row journal; one post-A
read failure required only health continuation. No F1 owner remains.
The five-entry difference does not identify paths. P443 cannot be replayed.
The [P444 read](docs/reports/S22PLUS_AUTOBOOT_EVIDENCE_P444_RUN_2026-10-20.md)
retrieved the complete P441 pair and closed `ANDROID_CLOSED_HEALTHY`.
All 14 early and six runtime records authenticate with matching boot/nonce;
the early bytes equal P442's capture. Both files belong to P441's first boot.
Runtime reaches installed-init/rcS entry and fork, not rcS completion,
services, SSH or clean shutdown. The mountless partition-RO view is state 1,
RECOVER 0, orphan 0. Closure rederived 649 captures and the unchanged 20-row
journal, with one post-A read failure and health-only continuation.
P444 is consumed; no F1 owner remains. Its
[qualification](docs/reports/S22PLUS_AUTOBOOT_EVIDENCE_P444_H0_2026-10-20.md)
retains A/B packages, two new ARM64 cases, 27 unchanged and six fresh tests,
and source-bound PASS_GO. New history qualification and complete protected
root admission remain necessary before another writable Debian lifetime.
The [P445 phase implementation](docs/reports/S22PLUS_AUTOBOOT_PHASE_P445_H0_2026-10-20.md)
now has a fixed twelve-callsite observer and RAM rcS dispatcher in the existing
parents. Generic ARM64 lifecycle, framing, loss and ownership cases pass;
76 observer tests, 31 related host/owner tests and 12 boundary tests pass.
The corrected normal VM proves all 34 dispatcher packets, rcS completion,
120-second services, pinned SSH, controlled poweroff and clean ext4. Actual
A/B AP checks, eight archive negatives and all 57 ARM64 VM cases pass.
Final package revalidation and independent **PASS_GO** bind 140 host and
150 runtime sources. Fresh fixed Android D0 health/preparation and task
reopening pass; the one-operation/3600-second attended proposal is ready.
The first full VM
correctly missed the physical startup window after slow generic root checks;
the new VM-only timing adapter preserves physical 8.5/15-second limits.
The [physical P445 run](docs/reports/S22PLUS_AUTOBOOT_PHASE_P445_RUN_2026-10-21.md)
has now consumed one attended N/A pair and closed `ANDROID_CLOSED_HEALTHY`.
Its 360-second observation has no accepted endpoint or SSH proof. All 856 raw
captures and the unchanged 14-row journal rederive; no recovery read failed.
Same-returned-boot retention authenticates 158 preparation, four diagnostic
and 48 strict transition records through successful early-file cleanup and
configfs mount. A separately authenticated intact frame in a noncanonical
line proves second-admission BEGIN at 3.468 seconds; the strict projection
remains unchanged. There is no retained completion, installed-init/rcS,
phase-observer or service proof. Later warm-reset firmware context does not
locate the failure or prove a second candidate boot. Current native_data
consistency remains unknown. P445 is consumed, its grant is closed and no
F1 owner remains. The [P441/P445 comparison and next-experiment decision](docs/reports/S22PLUS_P441_P445_COMPARISON_NEXT_EXPERIMENT_H0_2026-10-21.md)
is now complete in H0. Retained export bytes do not resolve the actual failure
frontier; the selected early code and table comparison finds no specific new
pre-PID1 control-flow defect. The selected functional variable is
`maxcpus=1` on the P441-style Debian startup/proc-observer path, with current
authenticated history and both complete root admissions; P445 phase
instrumentation is excluded. The intended outcome is sustained same-boot
services/SSH and controlled shutdown. P446 now implements that candidate in
H0, checks CPU0 and actual watchdog driver-enabled state, and observes two
same-boot SSH endpoints 120.57 seconds apart in the normal VM. The VM models
the Samsung watchdog attribute; it proves no physical pet success.
Current native_data state/history, policy adoption and the existing
qualification/review/grant requirements remain separate prerequisites for
a future physical writable candidate. No device authority was added.

The [integration synthesis](docs/reports/S22PLUS_DEBIAN_INTEGRATION_SYNTHESIS_2026-10-13.md)
retains P410/P413's installed-PID1/rcS-entry proof and the earlier logger findings.
[P425 H0](docs/reports/S22PLUS_DEBIAN_INTEGRATED_P425_H0_2026-10-13.md) retains its
reviewed VM service/SSH/shutdown evidence; its physical candidate is consumed.
P430 proves storage-first preparation; installed services, NCM and same-boot SSH remain the physical gap.

## P441 closed healthy: watchdog task samples; rcS/services still unproved

The [P441 run](docs/reports/S22PLUS_AUTOBOOT_WATCHDOG_P441_RUN_2026-10-20.md)
consumed one attended N/A pair and closed ANDROID_CLOSED_HEALTHY. The 360-second
window had no NCM/SSH proof. Closure rederived 694 captures and the unchanged
14-row journal; no F1 owner remains. Same-returned-boot D0 authenticates 141
transition records, including admitted root, installed Debian PID1 and rcS
progress, plus nine watchdog observations; one malformed frame is rejected.
Watchdog samples are S through 10.003s, then R with 80/179 ticks at 11.009/12.006s.
Actual `cpuidle.off=1` did not prevent RT throttling and a watchdog reset reason.
A distinct second boot has only preparation-prefix evidence; its writes and
current native_data consistency are unknown. rcS completion/services/SSH and
clean native shutdown remain unproved. The grant is consumed; no replay.
The [qualification](docs/reports/S22PLUS_AUTOBOOT_WATCHDOG_P441_H0_2026-10-20.md)
retains 49 VM cases, 85 tests, PASS_GO and the 11-item checklist audit.
The [H0 follow-up](docs/reports/S22PLUS_P441_WATCHDOG_FOLLOWUP_H0_2026-10-20.md)
preserves strict results and authenticates the final frame: five TASK/WCHAN pairs.
Actual Image analysis establishes USER_HZ=100; scheduler time supplies no PC.
Core ignores pet errors. Current-data analysis is complete; dynamic phase/child progress is unknown.

## P440 retrieved the P437 pair and closed healthy

The [P440 read](docs/reports/S22PLUS_AUTOBOOT_EVIDENCE_P440_RUN_2026-10-20.md)
retrieved the complete 10,972-byte early file and newly visible 1,024-byte
runtime file after replay. All 14 early and six runtime records authenticate
with matching boot/nonce; the early bytes equal P438's earlier capture.
PASS_AUTHENTICATED_LOCAL_PROGRESS reaches RCS_ENTERED and fork, not rcS
completion, services, SSH or clean shutdown. These are first-P437-boot records.
The mountless read saw state 1/recover 0/orphan 0 under partition RO and made
no filesystem writes. One N/A pair closed ANDROID_CLOSED_HEALTHY after one
post-A read failure and health-only continuation. H0 closure rederived 617
captures and the unchanged 20-row journal; no F1 owner remains. P441 qualified
this history; every new writable boot still requires complete root admission.

## P439 closed healthy; replay/checker complete, full-root comparison negative

The [P439 run](docs/reports/S22PLUS_JOURNAL_RECOVERY_P439_RUN_2026-10-20.md)
consumed one attended N/A pair and closed ANDROID_CLOSED_HEALTHY. The strict
writer completed 24 writes/95,232 bytes, followed by clean superblock,
read-only checker success, partition RO and protected unmount. All 8,971
selected entries match, but 8,979 observed versus 8,976 admitted tree entries
leave three unaccounted entries: RECOVERY_NOT_PROVED. Their paths are not
identified by this aggregate result. One post-A ADB read failure led only to
health continuation; no transfer or writer repeated. H0 closure rederived 617
captures and the unchanged 20-row journal; no F1 owner remains.

P440 subsequently retrieved the P437 pair and P441 qualified its history.
P439 alone proves neither full-root admission nor a new effect's authority.
A90 and S20+ were untouched.

## P437/P438 closed healthy; first watchdog renewal remains the runtime gap

The [P437 run](docs/reports/S22PLUS_P437_RCS_OBSERVATION_RUN_2026-10-19.md) consumed
one N/A pair and closed ANDROID_CLOSED_HEALTHY, with no F1 owner or qualified
NCM/SSH in its 360-second window. Its 132 authenticated records prove installed
Debian PID1, rcS fork, checked fork-record persistence, child fd cleanup, exec
attempt, first WNOHANG wait and first 10ms sleep return. Last stage is
RCS_SLEEP_FIRST; child exec/rcS completion, services/SSH and clean shutdown are
unproved. One post-A ADB read failure was preserved before health-only closure;
the 16-capture retained-log D0 passed both same-boot brackets. A90/S20+ were untouched.
The [pre-transfer attempt](docs/reports/S22PLUS_P437_PRETRANSFER_STOP_2026-10-19.md)
remains separately consumed/closed N=0/A=1. The
[host correction](docs/reports/S22PLUS_P437_TRANSFER_GUARD_H0_2026-10-19.md) retains
43 tests, six integration cases and PASS_GO; runtime/41 VM cases were unchanged.

The [boot audit](docs/reports/S22PLUS_P437_BOOT_REQUIREMENTS_WATCHDOG_H0_2026-10-19.md)
separates two candidate boots. The first has gh-watchdog RT throttling at
11.988s and watchdog bark/bite/reset at 12.739s; the 317s messages belong to the
second boot. First heartbeat was due only around 16.175s. Exact missed-renewal
cause and second-boot write/rejection state remain unknown. The
[observer precursor](docs/reports/S22PLUS_WATCHDOG_OBSERVER_H0_2026-10-19.md)
has host/ARM64 task-state/CPU-time/wait-symbol checks using existing parents;
P441 separately qualified its enabled physical selection.

The [P438 read](docs/reports/S22PLUS_AUTOBOOT_EVIDENCE_P438_RUN_2026-10-20.md) consumed
one N/A pair and closed ANDROID_CLOSED_HEALTHY, with no F1 owner. Its 10,972-byte
early file authenticates all 14 records of the first P437 boot; runtime file is
ABSENT_IN_HOME_VIEW with state=1/recover=1/orphan=0. No mount/replay/data write
occurred. One post-A ADB read failure preceded health-only closure. Exact root
admission remains unresolved; fixed journal-recovery/history assessment remains
separate from watchdog diagnosis. The consumed grant gives no further authority.
The [P436 read](docs/reports/S22PLUS_AUTOBOOT_EVIDENCE_P436_RUN_2026-10-18.md) retains
P432 installed PID1/rcS-fork proof. P432–P434/P436 are consumed/healthy; P434 is
RECOVERY_NOT_PROVED and P435 remains unstarted with its original prerequisite.

The [stock FYG8 comparison](docs/reports/S22PLUS_FYG8_STOCK_FIRST_WATCHDOG_H0_2026-10-20.md)
joins original firmware/source, binaries and retained boots. Stock selects qcom-cpu-lpm
with a compiled sleep_disabled default selecting state 0/WFI; P437 selects menu.
Stock's 10.24s pet precedes 16s+ post-boot scripts. P430 has the same diagnostic
kernel and 82 module rows as P437 yet survives about 369s; later userspace differs.
This is an idle-policy lead, not a proved cause. H0 resolves 349 selected instruction
differences, matches 336 alternative/66 static-key entries, and binds hyp locks,
dynamic WFI trapping, ramdisk differences, early warnings and eight retained logs.
P441 subsequently observed watchdog task wake/CPU-time growth with cpuidle off.
Exact timer/ping/SMC phase and rcS child progress remain unproved.

## P430/P431 closed: early PID1 and durable file proved; Android healthy

The [physical report](docs/reports/S22PLUS_DEBIAN_P430_P431_PERSISTED_EARLY_PID1_RUN_2026-10-16.md)
records **PASS_PERSISTED_EARLY_PID1_PRE_UNMOUNT**: measured Debian initial PID1,
76 preparation modules, six later client returns and all 14 chained records in
a 10,972-byte file retrieved after Android recovery. RAM and file join the same
writer boot. The later mountless read is clean; writer unmount return remains
unproved. Both operations are consumed and **ANDROID_CLOSED_HEALTHY**, each
with one N/A pair and no remaining F1 owner. A90 and S20+ were untouched.
The [boot-flow audit](docs/reports/S22PLUS_DEBIAN_BOOT_FLOW_CODE_AUDIT_2026-10-16.md) maps the next autonomous Debian path.
Resolve evidence-file admission and coupled host gates before qualifying installed init/services/SSH.
P428/P429 remain consumed and closed healthy; their absent evidence grants no replay.

## Earlier completed work

P409–P429 and their exact evidence, limits and closed recovery states are retained
in the [P441 follow-up snapshot](docs/archive/roadmaps/GOAL_THROUGH_P441_FOLLOWUP_2026-10-20.md).
The snapshot preserves the complete prior 800-line goal byte-for-byte. Historical
root observations and consumed capabilities remain historical; no grant is renewed.

## Selected final architecture

```text
Samsung bootloader -> FYG8 kernel -> minimal device initramfs
                  -> root transition and exec -> Debian host PID 1
```

The early bootstrap identifies the exact root partition, prepares the storage
and essential device interfaces, mounts the Debian root, and transfers the
required mounts and console/log state. It then execs Debian init in the initial
PID namespace. The bootstrap does not fork Debian beneath a surviving native
PID 1, retain an independent native control plane, or leave an old-root process
tree running beside Debian. Select the root-transition mechanism against the
actual kernel and initramfs topology; a generic `pivot_root` assumption is not
an implementation plan.

| Responsibility | Before handoff | After handoff |
| --- | --- | --- |
| Root storage and essential hardware | Minimal bootstrap loads the necessary exact modules/firmware, creates required nodes and mounts the root | Debian owns filesystem policy, device events and subsequent initialization |
| Process and service lifecycle | Bootstrap manages only its temporary preparation processes | Debian init owns host PID 1, process reaping, service start/stop/restart and shutdown |
| USB, networking and display | Prepare only what root access or required boot observation needs | Debian services own configuration and device access; no competing native manager |
| Device-specific long-lived helpers | Identify their real lifetime and dependencies before choosing the handoff | Package and start them under Debian's service manager, with Debian-visible logs and explicit start/stop behavior |
| General Linux runtime | Use standard tools where suitable; do not recreate distribution services | Debian provides libraries, accounts/authentication, DNS, time, logging and package management |

Classify each reused native component as boot-only, a Debian-managed service,
or unnecessary for this product. A helper that cannot yet operate under Debian
is an explicit compatibility gap, not justification for hiding a second
supervisor or Android runtime behind the handoff. Existing kernel modules and
firmware may remain active: root transition does not reset the kernel or
hardware, and it does not by itself prove their later compatibility.

Build the initramfs and rootfs as a matched pair with declared versions,
paths, module/firmware dependencies, writable directories, device-manager
behavior, init/service configuration and SSH access. Prefer moving reusable
boot preparation into Debian's initramfs build hooks as compatibility permits.
No requirement to eliminate initramfs or replace the FYG8 kernel is introduced.
The steady-state rootfs should support normal Debian package and configuration
management on the dedicated partition; its initial mount mode and exact
persistent-write scope remain implementation and reviewed-capability work.

## Kernel and rootfs compatibility

Recheck the selected kernel artifact and target ABI before choosing the Debian
release, init and device manager. The retained
[FYG8 capability analysis](docs/reports/S22PLUS_FYG8_NATIVE_USERSPACE_BRINGUP_GAP_ANALYSIS_2026-07-22.md)
records disabled devtmpfs, PID/user namespaces, the cgroup PID controller and
SysV IPC. These are compatibility inputs to verify against the chosen artifact,
not a claim that a new Debian build has passed. Host PID 1 does not require a
new PID namespace.

Debian ownership does not imply a preselected systemd implementation. Assess
a small Debian init such as SysVinit against the existing kernel, and assess
systemd against its exact version's kernel/device requirements. Keep missing
kernel features explicit; do not emulate a general Linux environment inside
native init to conceal them. Any kernel change is a separate qualified unit.
Use [Debian's arm64 bootstrap documentation](https://www.debian.org/releases/stable/arm64/apds03.en.html)
for rootfs construction and
[initramfs-tools](https://manpages.debian.org/trixie/initramfs-tools-core/initramfs-tools.7.en.html)
for the standard early-boot lifecycle. Their generic kernel/bootloader setup
does not replace this target's existing boot and recovery process.

The [A90 comparison](docs/plans/A90_H16_H24_ISOLATED_DEBIAN_COMPARISON_BASELINE_2026-08-14.md)
and [firstboot audit](docs/reports/A90_H14_IMMUTABLE_FIRSTBOOT_ISOLATED_DEBIAN_MISMATCH_H0_2026-08-14.md)
are lessons: align mount/device assumptions, authentication, service ownership
and return behavior before integration. Do not import A90's selected native
supervisor architecture, consumed results or device authority. HUD, display,
boot chime and legacy SD evidence dependencies do not gate the first headless
Debian boot.

## Completion criteria for the first usable Debian system

These are prospective product criteria, not newly activated device gates:

1. **Actual Debian boot:** same-boot evidence identifies Debian init as host
   PID 1, the dedicated partition as its root, and the expected rootfs build.
   A child shell, a chroot, a namespace-local PID 1, an exec-intent marker or an
   open port alone does not establish this outcome.
2. **One userspace owner:** no independent native supervisor, competing device
   manager or surviving native old-root service tree remains. Required
   target-specific helpers have a declared Debian service owner and observable
   lifecycle. Mounts and inherited descriptors match the handoff design.
3. **Useful Debian runtime:** the selected standard command workload runs,
   package installation/configuration works, and one ordinary service can be
   started, stopped and restarted through Debian's init system. Record the
   tested packages and limitations; do not claim all Linux software works.
4. **Headless access:** a declared Debian-owned IP path supports authenticated
   SSH, DNS and the selected service workload. USB networking may qualify the
   first access path; Wi-Fi is a later capability if its dependencies are not
   ready. Port visibility alone is not authentication or service proof.
5. **Persistent operation:** a clean shutdown/reboot boots Debian again and
   preserves the selected package, configuration and synchronized test data.
   A normal boot does not depend on an interactive native shell or host daemon.
6. **Diagnosable failure and recovery:** boot-stage records connect to Debian
   logs, distinguish the last completed preparation stage from actual init
   execution, and identify the service that owns a failure. Demonstrate the
   separately authorized return/recovery path and final rooted Android health;
   report Debian functionality, recovery and terminal health independently.

Demonstrate the combined PID 1, root, ownership, SSH and workload claims in one
identified integrated run, followed by its qualified persistence/return checks.
Do not assemble a full-system PASS from unrelated experiments. Before Debian
exec, a preparation failure may stop in the bootstrap under its defined
procedure. After successful exec, the replaced native PID 1 is not available
as an automatic fallback. Post-handoff recovery must have its own demonstrated
reboot/physical-return route; no reverse root switch or automatic recovery is
assumed.

## Next bounded unit and milestones

The P448 physical unit and P449 read are closed. P448's partial progress reaches installed PID1
and rcS fork/first sleep, but the usable service/SSH criterion is still open.
Keep the live NO_PROOF result, positive retained facts and healthy Android
return distinct. The selected CPU setting alone did not establish the product
capability, and no watchdog/reset cause has been proved.

Keep Debian shell as initial owner and use fixed temporary preparation helpers.
Reuse root-transition, installed-init and same-first-gadget work, with the
[P414 observer](docs/reports/S22PLUS_DEBIAN_HANDOFF_P414_OBSERVER_H0_2026-10-03.md)
and current watchdog observations where useful. The product remains services
and same-boot SSH; diagnostics do not become a second general runtime.

P449 recovered the authenticated first-boot early file but found a dirty
home-block view and no runtime file. P450 and P451 are now qualified proposals
for fixed native_data strict journal recovery and the separate post-closure
read. Each awaits its own returned attended grant; P451 follows P450's healthy
closure and fresh machine checks. The reader's three superblock fields do not prove complete
writer eligibility; its exact current checks, reviewed scope, qualification
and returned attended grant remain required. Do not fabricate unseen history,
infer clean native_data from original-A health or admit an unknown runtime
file. Replay/checker success is distinct from complete root admission.
Compare only source-bound per-boot facts when choosing a functional successor;
optional cause analysis does not replace current-root admission or reopen a
consumed action. All new work starts from the closed healthy Android state.

1. **Integrated headless access:** qualify one complete Debian-owned boot path
   through platform preparation, protected root admission, installed PID1,
   rcS/runlevel 2, 120 seconds of sampled init/cron/sshd liveness, Debian NCM
   and same-boot pinned SSH. Include useful bounded observations in that path
   without turning each record into a separate whole-device milestone. Close
   through the selected fixed shutdown and original-A return/health procedure.
2. **Persistence and ordinary service:** after healthy closure, qualify
   package-managed service behavior, retained data/configuration and ordinary
   Debian reboot under the applicable separate scope.
3. **Later hardware:** Wi-Fi, display/input, audio and desktop follow the
   usable headless Debian base.

A future physical unit still requires a freshly qualified complete artifact,
current source-bound review, exact original-A health and applicable finite
authority, with its original recovery owner. No historical grant is reused.

ARM64 VM proof does not establish Samsung electrical USB behavior or target
service liveness. Installed-init proof, runtime progress, SSH, clean ext4 and
Android closure remain separate. Forced return can leave native_data dirty
while Android remains healthy; repair requires a separately selected scope.

## Completed history

The complete 754-line goal through P410's healthy closure and exact-Image USB
diagnosis is preserved byte-for-byte in
[the P410 closed snapshot](docs/archive/roadmaps/GOAL_THROUGH_P410_CLOSED_2026-10-01.md).
It retains the P401 installation, P403 fixed userspace, P406 root inspection,
P408 protected preparation, earlier storage/cleanup results and archive links.
Consumed claims, private journals and historical source pins keep their
original meaning and cannot be replayed.

## Continuing boundaries

Future device work requires its own current scope and exact target, artifact,
health, source and recovery binding. Never place an experiment over uncertain
health or repeat an uncertain write, transfer or control. Keep raw evidence and
identifiers private. A reporting failure permits evidence reconstruction, not
another device transition. Functional proof, recovery and terminal health remain
separate. The Debian direction selects preparation work only; filesystem
formatting, rootfs staging and runtime effects require their own reviewed
scope under the binding contracts.
