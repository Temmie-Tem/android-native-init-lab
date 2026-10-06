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

## Current P413 installed PID1 and rcS entry; Android recovered healthy

P413 `v0.4.0-rc.13` completed one attended attempt on 2026-10-03 KST.
The [physical-run report and timeline](docs/reports/S22PLUS_DEBIAN_HANDOFF_P413_FIRST_RUN_2026-10-03.md)
prove fresh clean-root admission and all 8,969 expected entries, one normal
native_data RW activation, the actual PID1 writable-root witness and installed
Debian init as PID1 in the same kernel boot. The installed-init hook proved
zero inherited ACM/state descriptors, accepted START and recorded rcS entry.

The host observation then ended with **EOFError**, after that entry record and
before any rcS-complete/runlevel-complete or 120-second runtime proof. No
authenticated STOP errno was received. The host sent no USB release, NCM/SSH
request or Debian shutdown. Result: **PASS_INSTALLED_DEBIAN_PID1**, with Debian
service progress, NCM and SSH still **NO_PROOF**. EOF does not establish a reboot,
panic, rcS failure or its cause.

The exact Download endpoint was bound and original A transferred once. A
pre-dispatch USB endpoint read failure and a later boot-time ADB read failure
were preserved; continuation performed only the remaining authorized recovery
and health work. Terminal: **ANDROID_CLOSED_HEALTHY**, `recovered=true`.
There was one N and one A, with no repeated handoff/control/transfer. The grant
and candidate are consumed and closed; the F1 owner is absent. All 1,759 raw
captures, 264 frozen source files and the unchanged 17-row journal/terminal
were revalidated in H0. A90 and S20+ were untouched.

Native_data was clean before P413's writable lifetime; its cleanliness after
the forced original-A return is now **unproved**. Android health does not
preserve or renew P412's clean-root claim. The
[retained-evidence H0 assessment](docs/reports/S22PLUS_P413_EOF_FORENSICS_H0_2026-10-03.md)
completed without device commands or a new candidate. CLOCAL was already set;
the verified driver behavior and exact startup scripts do not establish a
simple ACM-close or direct rcS USB/reboot cause. The subsequent
[multi-angle causal analysis](docs/reports/S22PLUS_P413_CAUSAL_RESEARCH_H0_2026-10-03.md)
joined the EOF to an actual host USB-core disconnect and a spontaneous native
USB re-enumeration about 24.43 seconds later, before physical recovery was
requested. This explains the tty hangup/EOF path but does not distinguish a
same-boot USB restart from a kernel/SoC reboot. Ordinary carrier loss,
unsupported close_range, native-userspace watchdog petting and normal runtime
autosuspend do not supply a supported causal chain. The departure trigger
remains unproved. P413 grants no replay or filesystem repair.

The operator reports no physical unplug/replug during the cutoff. Intermittent
contact or electrical loss remains an unproved alternative, not an observed
fault; absence of plug manipulation does not alone establish reboot.

## Prior P413 prelive qualification

P413 `v0.4.0-rc.13` is the fresh archive-free handoff V2 candidate after
P412's clean-root proof. Its [prelive report](docs/reports/S22PLUS_DEBIAN_HANDOFF_P413_PRELIVE_2026-10-03.md)
records identical actual A/B boot packages, static ARM64 helpers, independent
**PASS_GO** over 264 frozen source files and 60 current focused tests.
Exact assembly/header/asset equivalence permits reuse of P411's 21 ARM64 VM
cases; their authenticated RX and TX records all rederive with the unchanged
strict consumer. No new VM execution or new Debian runtime feature was needed.

The corrected Android health consumer is included in a new capability record;
the consumed P411/P412 reviews, artifacts and journals remain unchanged.
Both guarded offline preparation and current connected fixed D0 preparation
passed. The latter revalidated rooted original Android, exact Android32 GPT,
capacity and the retained recovery binding in 19 private captures. The concrete
task hash is `cb86591156b7004700cafb49748cf77e10f1f743ddb3dc97f147dce0fb5d725a`.

That preparation opened no grant or operation and transferred no image. Its
later one-operation/3600-second physical attempt above is now consumed. Fresh
native-root admission remained mandatory and passed before RW. The retained
qualification is not physical service/NCM/SSH proof or authority to replay.

## Prior P412 clean-root proof and healthy Android closure

P412 `v0.4.0-rc.12` completed one attended operation on 2026-10-03 KST.
Its [physical-run report and timeline](docs/reports/S22PLUS_NATIVE_JOURNAL_RECOVERY_P412_FIRST_RUN_2026-10-03.md)
record **PASS_JOURNAL_RECOVERY_OBSERVED / PROVED_CLEAN_ROOT**. Native_data changed
from `clean=0 state=1 recover=1 orphan=0` to
`clean=1 state=1 recover=0 orphan=0`. The strict writer recorded only its two
successful finalization writes (5,120 bytes); no additional home-block replay
write was observed. After partition RO restoration, `e2fsck -fn` passed and
all 8,969 expected root entries matched within the existing mutable-data bounds.
Protected unmount and cleanup completed.

Authenticated native return and one original-A transfer completed normally.
The final health consumer initially selected the wrong historical GPT layout
because its operation list omitted `journal-recovery`. Both retained health
captures actually prove the unchanged Android32 GPT, original partition
hashes, rooted Android and expected capacity. An independently reviewed H0
routing correction rederived those bytes and appended only the missing final
health completion. No device command or transfer accompanied that correction.

Terminal: **ANDROID_CLOSED_HEALTHY**, `recovered=false`. One N and one A were
transferred; the one-operation/1800-second grant and candidate are consumed
and closed, with the F1 owner absent. The original failed parser log, 19-row
journal prefix, raw captures and consumed source/review pins are preserved.
A90 and S20+ were untouched. P412 executed no Debian init, service or SSH.

That clean protected-root result removed P411's observed dirty-root blocker;
P413 revalidated it before its later writable lifetime. It does not prove the
filesystem clean after P413's forced return. Fresh work still needs its own
current admission, source binding and grant. The old P412 activation stays tied
to its original source; its H0 closure review grants no new device action.

## Prior P412 H0 qualification

P412 `v0.4.0-rc.12` is the separately scoped archive-free native_data recovery
candidate. Its [H0 report](docs/reports/S22PLUS_NATIVE_JOURNAL_RECOVERY_P412_H0_2026-10-03.md)
records a byte-identical A/B boot-only package, 29 actual ARM64 tool tests,
six final kernel-VM paths, seven child-failure VMs and 92 focused unit/C/PTY
tests. The strict writer avoids ordinary e2fsck repair/orphan cleanup; the
parent restores partition RO before the fixed checker and full protected
root comparison. Independent review returned **PASS_GO** over the frozen
source/artifact closure. Concrete offline preparation passed with device
entrypoints disabled: **READY_H0_PRELIVE_ONLY**, candidate unclaimed and F1
owner absent. The new capability record preserves every consumed predecessor.

That H0 unit performed no device command, connected read, transfer, replay,
new boot or grant. P411's dirty native_data observation was its starting
evidence. The later physical operation above consumed this candidate under
the separate 1800-second scope; the original H0 evidence remains unchanged.

## Prior P411 dirty-root rejection and healthy Android closure

P411 `v0.4.0-rc.11` completed one attended attempt on 2026-10-01 KST. Fresh
fixed Android preparation passed before its one-operation/3600-second grant.
One N transfer and authenticated native health succeeded. Actual PID1 entry
and worker retirement were proved, then protected root admission observed
`clean=0 state=1 recover=1 orphan=0` on native_data.

The inspector kept partition RO, did not mount the filesystem and confirmed
unchanged superblock/GPT before cleanup. The handoff stopped with `EPROTO`
before writable activation or installed init. Result: **NO_PROOF Debian PID1**
with a proved dirty-root admission rejection. No START, 120-second service
observation, USB release, NCM, SSH or Debian shutdown occurred.

The exact Download endpoint was bound and original A transferred once. A
boot-time ADB read failed; health-only continuation then proved rooted original
Android, all original partition hashes, GPT and Android32 capacity. Terminal:
**ANDROID_CLOSED_HEALTHY**, `recovered=true`. There was one N and one A, with
no repeated control/transfer. The candidate and finite grant are consumed and
closed; the F1 owner is absent. A90 and S20+ were untouched.

The [physical-run report and timeline](docs/reports/S22PLUS_DEBIAN_HANDOFF_P411_FIRST_RUN_2026-10-01.md)
record the 1,436 operation captures, 261 frozen source files and unchanged
terminal/journal rederivation. Native USB presence after the stop does not
prove a new boot: ACM had not been retired, and no later authenticated boot
identity was acquired. The host sent no new native Download command.

The native filesystem required journal recovery when P411 observed it.
P411's Android health did not repair it or prove its later cleanliness, and
its grant authorized no repair, journal replay or reinstall. The separately
scoped P412 operation above later proved clean protected-root admission;
P411 itself remains consumed and cannot be replayed.

## Prior P411 H0 qualification

The [V2 policy](docs/operations/S22PLUS_DEBIAN_HANDOFF_V2.md) selects sequential
Debian-owned startup/120-second observation and retention of the first `g1`
for NCM. The [H0 report](docs/reports/S22PLUS_DEBIAN_HANDOFF_P411_H0_2026-10-01.md)
retains 21 ARM64 VM cases, 159 tests, identical actual boot/AP A/B bytes and
independent source-bound PASS_GO over 261 files. Its concrete task hash is
`4dba33825c8cea17463266ac2e1e8b3591a45641ed68a2fb1caa5dc93f696aa9`.
The later physical attempt above consumed that candidate and grant. Samsung
NCM/SSH and the 120-second service interval remain unproved because admission
stopped earlier; the H0 proof is not relabelled as a physical pass.

## Prior P410 installed PID1 reached; basic access failed and Android recovered

P410 `v0.4.0-rc.10` completed one attended operation on 2026-09-30 KST.
The physical authenticated transcript proves installed Debian init as host
PID1 under the writable native_data root: `PASS_INSTALLED_DEBIAN_PID1`.
This is the reached init boundary, not a successful Debian service boot.
No NCM endpoint appeared in the 180-second window and no SSH or shutdown
command was sent. About 51 seconds into that window the same P410 native ACM
identity reappeared. The reported advancing native screen is consistent with
later native startup; no later authenticated boot ID or reset-cause evidence
proves an actual reboot mechanism.

Research stopped. Attended physical Download and one original-A transfer
returned the device to `ANDROID_CLOSED_HEALTHY`, `recovered=true`. A USB read
failed before the A intent; later final-health ADB failure required only
health continuation. There was one N and one A transfer, with no repeated
handoff/control. Full rooted Android, original partition hashes, GPT and
Android32 capacity passed. Native_data cleanliness remains unknown after the
writable lifetime. The one-operation/3600-second grant and candidate are
consumed and closed; the F1 owner is absent. A90 and S20+ were untouched.

The [physical-run report](docs/reports/S22PLUS_DEBIAN_HANDOFF_P410_FIRST_RUN_2026-09-30.md)
records 1,779 raw captures, 257 frozen source files, unchanged terminal/journal,
the native USB reappearance and the limits of the PID1 proof.

Post-run H0 diagnosis confirmed a blocking USB ownership defect in the exact
P410 Image: Android configfs setup keeps the first gadget's global pointer.
The hook unbinds native `g1`, but Debian creates a second `s22-debian` object;
the old object's `unbind=1` blocks setup before NCM descriptor handling.
Independent exact-Image review and 16 source control-flow cases on host/ARM64
confirmed the mechanism. The physical run's post-hook reach and reset cause
remain unproved. Retiring native workers does not remove the kernel watchdog
petter, so that simple reset explanation is unsupported.

P411 implements the selected same-first-g1 correction under its own V2
scope. The P410 evidence and prior review remain unchanged; the root is not
assumed clean and no earlier consumed effect becomes replayable.

## Prior P409 proved readonly PID1 transition and healthy Android closure

P409 `v0.4.0-rc.9` completed one attended operation on 2026-09-30 KST.
The actual native PID1 replaced itself, settled its native workers, verified
the protected installed root and used the selected BusyBox to switch_root into
a distinct static RAM witness. Authenticated post-exec evidence proved PID1,
readonly ext4 root and partition RO, the witness executable, seven moved mounts,
only fd0–3, no other userspace and the same boot/ACM connection. Result:
`PASS_SWITCH_ROOT_WITNESS / PROVED_READONLY_HOST_PID1_ROOT_TRANSITION`.

The exact 8,969-entry root comparison passed. The witness's fixed Download
return and one original-A transfer completed. A final-health ADB boot read
failed; health-only continuation then proved rooted original Android, exact
partition hashes, full GPT and Android32 capacity. There was one N and one A
transfer, with no repeated effect. Terminal: `ANDROID_CLOSED_HEALTHY`,
`recovered=true`. Final health completed at 95.495 seconds and explicit grant
closure at 227.705 seconds; 553 raw captures and 247 saved source files were
verified. The candidate/grant are consumed and the F1 owner is absent.

The [first-run report and timeline](docs/reports/S22PLUS_SWITCH_ROOT_P409_FIRST_RUN_2026-09-30.md)
record Samsung proof of the shared retirement/root-transition/observation
mechanism. This run does not execute installed Debian init, start services,
establish NCM/SSH or test writable persistence. The closed P409 grant authorizes no successor effect. P410 subsequently
proved installed init, and P411 addresses its service/USB gap; A90 and S20+
remain isolated.

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

P415 `v0.4.0-rc.15` is the next bounded **read-before-write evidence census**.
The [P415 H0 report](docs/reports/S22PLUS_NATIVE_ROOT_EVIDENCE_P415_H0_2026-10-07.md)
and [separate root-evidence policy](docs/operations/S22PLUS_NATIVE_ROOT_EVIDENCE_V1.md)
define one fixed mountless capture of existing native_data records under
partition RO, followed by original-A return. Validly identified dirty home
blocks can be read without journal replay; their absence or older contents
never prove non-execution. This preserves P413 evidence before any future
writable boot can rotate it. It neither admits the installed root nor repairs
native_data. The durable receipt writer and USB-independent startup remain
later work informed by the captured state. Actual A/B AP qualification,
12 ARM64 cases, 96 host tests and independent PASS_GO are complete. The
concrete offline task binds one attended operation/1800 seconds and requires
the returned grant plus fresh runtime health; no P415 device action or grant
has occurred.


The [P414 observer H0 unit](docs/reports/S22PLUS_DEBIAN_HANDOFF_P414_OBSERVER_H0_2026-10-03.md)
implements a close-return/reopen barrier and parent-only ACM observation during
ordinary rcS/rc2. Fresh revision-3 helpers preserve child descriptor isolation,
original deadlines and one-shot execution; partial boundaries never authorize
release or reconnect. Host and ARM64 qualification are recorded in that report.
This is prospective instrumentation, not a demonstrated repair or causal proof
for P413's USB departure. Existing D0/AUTH cannot provide a preparation-free
post-loss boot-ID observation; a separate future design remains unimplemented.

At the operator's 2026-10-07 request, future experiment design should consider
**bounded device-local persistent evidence alongside live USB observation**,
including recovery of those records after transport loss or reboot. The next
S22+ H0 design should assess per-run/boot identity, verified stage records,
checked durable writes, storage bounds and later retrieval. Review the coupling
between USB reporting and startup progress. Missing records must not imply
non-execution, and local service liveness must not imply external SSH success.
This is a prospective design preference; persistent receipts are not yet
implemented or activated and P414's existing qualification remains separate.

The next device-related unit requires a **freshly qualified complete artifact,
exact original-A health and applicable finite authority**. Current native_data
admission must pass at the protected boundary before any writable handoff.
P414 H0 opens no grant and has not
built or activated a full boot image. Native_data cleanliness after P413 remains
unknown; neither replay nor repair is inferred. P410/P413 installed-init proof
and P411's same-gadget H0 qualification retain their separate limits.

1. **Headless access:** with a fresh candidate and exact health/root admission, prove rcS and
   runlevel 2, 120 seconds of sampled init/cron/sshd liveness, Debian NCM and
   same-boot pinned SSH. One fixed shutdown and physical original-A return
   close this prospective unit.
2. **Persistence and ordinary service:** after that unit closes healthy,
   qualify package-managed service behavior, retained data/configuration and
   ordinary Debian reboot under a separately selected scope.
3. **Later hardware/product features:** Wi-Fi, display/input, audio and desktop
   are Debian-managed capabilities after the headless base works.

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
