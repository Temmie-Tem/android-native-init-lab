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

## Current P412 journal-recovery H0 ready

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

No device command, connected read, transfer, replay, new boot or grant occurred.
The last physical state remains P411's healthy Android closure and dirty
native_data observation below. P412 does not prove physical filesystem repair
or Debian service/USB progress. Its proposed later attended one-operation
scope is at most 1800 seconds with one original-A return; that boot restoration
does not undo a partial native_data replay.

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

The native filesystem required journal recovery when observed. Android health
does not repair it or prove its later cleanliness. P411 grants no repair,
journal replay or reinstall. The next required work is a separately scoped
filesystem recovery proposal and renewed protected root qualification before
another fresh Debian handoff candidate; P411 cannot be replayed.

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

The immediate prerequisite is **a separately granted attended P412 native_data
recovery attempt**; its H0 qualification and concrete offline task are ready.
P411 is consumed after a protected dirty-root
rejection; its grant cannot repair the journal or authorize a successor.
P410's installed-init proof and P411's H0 same-gadget qualification remain
valid within their original limits.

1. **Root recovery:** fresh connected preparation and one attended P412 attempt
   under its reviewed write scope, then re-establish clean protected root and
   immutable-content admission. The current goal itself grants no repair.
2. **Headless access:** with a fresh candidate and exact health/root admission, prove rcS and
   runlevel 2, 120 seconds of sampled init/cron/sshd liveness, Debian NCM and
   same-boot pinned SSH. One fixed shutdown and physical original-A return
   close this prospective unit.
3. **Persistence and ordinary service:** after that unit closes healthy,
   qualify package-managed service behavior, retained data/configuration and
   ordinary Debian reboot under a separately selected scope.
4. **Later hardware/product features:** Wi-Fi, display/input, audio and desktop
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
