# Goal: S22+ mainline Linux and resident Debian home server

On **2026-10-27**, the operator selected **mainline Linux as the final kernel
direction** for the operator-owned Samsung Galaxy S22+
SM-S906N / g0q / S906NKSS7FYG8. The final product boots directly into a
persistent Debian arm64 home server, with Debian init as **host PID 1 in the
initial PID namespace**, ordinary package-managed services and authenticated
headless access. A resident native supervisor or isolated Debian child is not
the selected product architecture.

**Android is to be retired from the final operating system.** Its present role
is a verified experimental return and management environment. Keep that route
during early mainline qualification, then replace its role with an independently
usable Linux rescue path and demonstrated Download recovery. Returning to
Android after each experiment is not a requirement of final resident operation.
Android retirement does not imply removing the bootloader, hypervisor,
TrustZone, calibration, device-identity or required firmware partitions.

The FYG8 vendor-kernel route remains a retained recovery/comparison resource;
it is no longer the final kernel architecture or the primary development track.
Do not update Samsung firmware, including the proposed One UI 8 / Android 16
route. Firmware stays FYG8 while the Linux kernel and device tree are developed
separately under the applicable target contract.

This goal records product direction and state, **never device authority**.
[AGENTS.md](AGENTS.md) and the [S22+ binding target contract](docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md)
continue to govern actual effects. This selection changes no active lane,
permanent boundary, source review, grant or recovery owner. A90 and S20+
identities, goals, artifacts and authority remain separate.

## Current state and evidence

- **Mainline progress through FDT setup and paging is demonstrated by ML005.**
  Its exact post-FDT and post-`paging_init` records were recovered after healthy
  original-A return; ML003/ML004 retain their earlier entry/MMU evidence.
  A usable RAM PID1/USB boot is still unproved. The sister r0q port supplies
  a starting point, not complete g0q qualification. The current
  [mainline assessment](docs/reports/S22PLUS_MAINLINE_SERVER_ASSESSMENT_H0_2026-10-27.md)
  records source evidence, known gaps and the proposed staged qualification.
- **First mainline H0 build is available.** Linux 7.2.11, a generated g0q DTB,
  static RAM PID1/initramfs and uniLoader were built. The actual kernel/PID1
  passed authenticated VM observation, and the production NCM setup passed
  a dummy-UDC test. These are not physical g0q evidence.
  [First build](docs/reports/S22PLUS_MAINLINE_RAM_CANARY_H0_2026-10-27.md).
- **Loader entry and boot packaging are now H0-qualified.** The 2026-10-28
  successor fixes file-copy/header geometry, admits safe runtime source
  placements and rejects a live-stub collision before stores. The actual
  linked loader passed 20 instruction-level cases, 1,051 direct copy cases
  and separate actual-EL QEMU entry tests. Two boot-v4/AP packages are identical.
  That unit performed no registration, activation, grant or device action.
  [Entry and packaging report](docs/reports/S22PLUS_MAINLINE_LOADER_ENTRY_H0_2026-10-28.md).
- **Mainline execution/observation/return integration is implemented.** The
  existing V3 owner now has one RAM/USB operation with original-A return,
  raw-first single-request observation and fixed preapproval health. The
  retained runtime/package is reused; 61 host tests and actual host network
  readiness and independent source-bound review passed. The connector's
  70-test upgrade and real ordinary-terminal restart are complete; named
  preapproval D0, mainline start and original-owner recovery/health ran through
  that connector. The earlier managed-process permission stop remains preserved.
  [Integration report](docs/reports/S22PLUS_MAINLINE_LIVE_INTEGRATION_H0_2026-10-28.md).
  [Connector completion](docs/reports/S22PLUS_MAINLINE_CONNECTOR_H0_2026-10-28.md).
- **ML001 first physical attempt is consumed: NO_PROOF / ANDROID_CLOSED_HEALTHY.**
  One N transfer completed, but all 117 fixed USB2 captures showed absence
  through the original 120-second window. No socket request or PID1 proof
  occurred. One attended physical Download/original-A return completed; a
  fresh health-only continuation passed after a preserved ADB `error: closed`.
  N and A were each transferred once. Automatic recovery and the point where
  mainline boot/USB stopped remain unproved. No replay or successor is armed.
  The operator observed the Samsung logo/unofficial-software warning followed
  by an unchanged screen; this was not a multiline kernel log or PID1 proof.
  [ML001 run report](docs/reports/S22PLUS_MAINLINE_ML001_RUN_2026-10-28.md).
- **A firmware/loader placement conflict is reproduced and corrected in H0.**
  The retained normal EFI configuration and ABL path supply 64 possible source
  placements; the old loader accepts one and safely rejects 63. A staging-only
  successor accepts all 64 at its copy guard, passes representative full copies,
  the 20-case/1,051-copy corpus and actual-EL QEMU, and has a deterministic
  boot-only package. This is conditional static/emulated evidence, not ML001's
  measured failure cause. The H0 comparison retains the old canary identity;
  no new live candidate or grant is armed.
  [Placement successor](docs/reports/S22PLUS_MAINLINE_ABL_PLACEMENT_SUCCESSOR_H0_2026-10-28.md).
- **ML002 is consumed: NO_PROOF / ANDROID_CLOSED_HEALTHY.** The fresh
  staging-corrected candidate passed H0 qualification and exact admission, then
  one attended N transfer completed. All 117 fixed USB2 samples showed absence;
  no authenticated request or PID1 proof occurred. The operator reported
  repeated reboots approximately every 8–9 seconds; reset cause and execution
  stage remain unproved. One physical Download/original-A return completed,
  followed by fresh successful health-only continuation after a preserved ADB
  target-not-found failure. N and A were each transferred once; no replay or
  follow-on grant is armed.
  [ML002 run record](docs/reports/S22PLUS_MAINLINE_ML002_RUN_2026-10-29.md).
- **LA001 loader-to-FYG8 control is consumed: PASS / ANDROID_CLOSED_HEALTHY.**
  The current-boot loader marker, exact vendor kernel and complete Android
  proof passed. A fresh same-boot bracket bound normal Download return and
  original-A restoration. One health-only continuation completed final health
  after a preserved ADB disappearance; N and A were each transferred once.
  This demonstrates the selected loader/vendor-FDT path, not mainline boot,
  ML002's replaced-DTB path or its reset cause. No follow-on grant is armed.
  [LA001 run record](docs/reports/S22PLUS_LOADER_ANDROID_LA001_RUN_2026-10-29.md).
- **Samsung retained-log feasibility is complete in H0.** The existing
  header-preserving placement and actual Samsung snapshot consumer support a
  small marker without a logger port; 12 extracted-source host cases passed.
  ML002 reserves this firmware-shared slice as no-map, so the proposed sites
  are the loader handoff and checked pre-MMU kernel entry. Missing
  markers cannot establish non-execution, and a boot-loop pair cannot by itself
  establish one shared boot.
  [Feasibility report](docs/reports/S22PLUS_MAINLINE_RETAINED_LOG_FEASIBILITY_H0_2026-10-29.md).
- **ML003 is consumed: early kernel entry observed / ANDROID_CLOSED_HEALTHY.**
  All 116 USB samples showed absence and the operator again reported a boot
  loop. After one N and one physical Download/original-A transfer, health-only
  continuation completed final Android health. The fixed same-returned-boot
  log read recovered six intact loader-handoff and six `primary_entry` records,
  with no damaged/foreign candidates. This proves both early sites were reached
  at least once in ML003; it does not count boots, prove a same-boot pair,
  identify reset cause or demonstrate PID1/USB. The USB terminal remains
  NO_PROOF. No replay or follow-on grant is armed.
  [ML003 run](docs/reports/S22PLUS_MAINLINE_ML003_RUN_2026-10-30.md).
- **ML003 reset-report provenance is bounded in H0.** The exact FYG8 reporter
  maps OEM enum 6 to the retained NoC label; the general restart word and
  upload string are separate inputs. The UEFI restore label can also appear
  after a failed read, as reproduced with actual instructions. Fresh-event
  attribution and the faulting component remain unproved. The subsequent
  ML004 MMU/early-C and ML005 post-FDT/post-paging runs are closed below.
  [Provenance and next design](docs/reports/S22PLUS_MAINLINE_ML003_RESET_PROVENANCE_H0_2026-10-30.md).
- **ML005 is consumed: post-FDT and post-paging observed / ANDROID_CLOSED_HEALTHY.**
  The same-returned-boot read recovered five intact records at each site,
  with no damaged/foreign candidates. This proves at-least-once progress
  through `setup_machine_fdt` and `paging_init`, including return from this
  candidate's earlier helper call. It does not prove the second writer's later
  cleanup/return, a boot count, reset cause or PID1/USB. The USB terminal remains
  NO_PROOF. The operator reports that ML005 also continued to boot-loop;
  its reset period and cause remain unproved. One N and one original-A transfer completed; first final health
  passed, with no health-only retry. No replay or follow-on grant is armed.
  [ML005 run](docs/reports/S22PLUS_MAINLINE_ML005_RUN_2026-10-30.md).
- The [FYG8 ABL/live-FDT analysis](docs/reports/S22PLUS_FYG8_ABL_DT_HANDLING_H0_2026-10-27.md)
  establishes this target's DT handling and matching r0q RAM banks/splash.
  Static loader/kernel/DTB/initramfs placement and retained reservation checks
  are qualified above; usable mainline boot remains unproved. Bypassing
  ABL's DT pipeline does not remove Gunyah.
- **P462 vendor-kernel proof remains valid within its original scope:** two
  Debian boots, one offline hello installation, function and exact retention
  across reboot, pinned SSH and automatic Download/original-A return.
  It is consumed and closed ANDROID_CLOSED_HEALTHY.
  [Run report](docs/reports/S22PLUS_DEBIAN_PACKAGE_P462_RUN_2026-10-27.md).
- **P463 is consumed: NO_PROOF / ANDROID_CLOSED_HEALTHY.** After one N
  transfer, a host UTF-8 profile-label decoding failure stopped the operation
  before sharing intent, SSH health or clock dispatch. One attended original-A
  return completed. The prospective UTF-8 correction passed focused and
  independent H0 checks; the consumed action cannot replay.
  [Run report](docs/reports/S22PLUS_DEBIAN_APT_P463_RUN_2026-10-27.md).
- The retained post-P463 fixed D0 observation is **M=40, needs-recovery set,
  valid checksum, healthy Android**. Current native_data package/run-file
  contents remain unobserved. Android health is not native_data consistency.
  Preserve the known P462 package state and all consumed P463 evidence.
- The current allocation is **32 GiB Android userdata and 191.4580078125 GiB
  native storage**. This is the present layout, not a permanent product
  requirement. Android removal or storage reallocation is a later separately
  designed and reviewed migration; this goal authorizes neither.

The unfinished host-only boot-journal integration is **paused and unactivated**.
Do not continue it as the selected next experiment or infer qualification from
its partial codec tests. Revisit filesystem recovery before using the existing
writable root, with the selected kernel and actual current evidence. It is not
a prerequisite for the RAM-only mainline canary.

## Selected architecture and reuse

The initial preferred mainline boot route is:

    retained Samsung ABL -> reviewed uniLoader boot payload
                        -> mainline Linux + g0q DTB + minimal initramfs
                        -> admitted Debian root -> exec Debian host PID 1

uniLoader has delivered the FYG8 Android control and ML003's early mainline
entry; a complete mainline PID1/USB boot is still unproved. The initial carrier
should retain stock vendor_boot/DTBO and avoid changing the bootloader or
recovery partition. Pin the complete loader/kernel/patch/config/DTB/initramfs
set. Do not copy the sister port's Android-removal or flashing workflow.

Reuse Debian userspace, authenticated access design, package/data expectations,
host tooling and raw-first evidence/recovery practices where compatible.
Vendor modules, platform preparation, USB ownership, watchdog controls,
kernel health predicates and prior artifact reviews do not automatically
transfer to mainline. Required firmware remains privately retained and bound.

The bootstrap owns only temporary preparation and root admission. Debian owns
services, process reaping, device events, networking, logging, filesystem
policy and shutdown after exec. Target-specific long-lived helpers must be
ordinary Debian-managed services with explicit lifecycle and logs. Normal
resident boot must not require an interactive native shell or a development
host permission exchange.

Retain the current Debian init/root where compatible for initial integration.
Evaluate systemd, containers and other ordinary Linux facilities against the
new kernel's actual configuration and runtime; do not require a simultaneous
userspace migration merely to prove the new boot path. Display, desktop,
camera, telephony, sensors and system suspend are optional later work.

## Next bounded unit: ML006 setup_arch and time_init return witnesses

The [ML002 joint analysis](docs/reports/S22PLUS_MAINLINE_ML002_BOOTLOOP_ANALYSIS_H0_2026-10-29.md)
keeps the reset cause and physical boot stage unproved. It identified a
conditional static mismatch between the retained hypervisor's vendor service
UID and the actual mainline Gunyah-watchdog registration filter. Merely enabling
that driver would not resolve the analyzed discovery path; this is not proof
of ML002's cause, and no guard or runtime was changed.

The completed comparison kept the exact original-A FYG8 vendor kernel and
inherited Android initrd, passing through a qualified uniLoader with the full
current ABL FDT. It adds one candidate-bound FDT marker so a complete current
Android proof can distinguish the loader path from ordinary Android return.
The [control policy](docs/operations/S22PLUS_LOADER_ANDROID_V1.md) and
[H0 qualification](docs/reports/S22PLUS_LOADER_ANDROID_H0_2026-10-29.md) bind the
one-shot owner, fixed evidence, normal Download return and original-A recovery.
LA001 now proves this selected physical loader/vendor-Android path and its
original-A return. The one finite attended operation is closed and consumed.
There is no standing approval or consumed-run replay.

**Control completion criterion — met:** a candidate-bound marker, exact kernel and
partition identities in one current Android boot, followed by original-A
restoration and health. A failed or absent proof may close NO_PROOF only after
that return. The comparison added no native_data access or watchdog changes.
It can qualify shared loader stages; it cannot prove the replaced-DTB mainline
path or identify ML002's reset cause. The watchdog trace remains separate H0
research.

The post-LA001 comparison selected a bounded Samsung retained-log feasibility
check. That check is complete: the reader format and compression do not require
a Samsung logger port, and a small header-preserving span is source-compatible.
ML003 implements a candidate-bound loader-handoff marker and a pre-MMU
mainline-entry marker, with positive-only decoding and the existing original-A
return. Its separate fixed post-return reader joins the exact closed mainline
owner and same returned Android boot. Its 2026-10-30 attended run is complete:
both early stage markers survived the tested physical return, while full
PID1/USB proof remained absent. Original-A restoration and final health passed.
The candidate, exact approval and operation are consumed and closed.

The bounded [reset-report analysis](docs/reports/S22PLUS_MAINLINE_ML003_RESET_PROVENANCE_H0_2026-10-30.md)
joined the retained firmware's reporter, OEM-slot writer and log-restoration
path. Runtime configuration and event freshness remain unresolved; the next
progress experiment is not gated on open-ended secure-firmware analysis.
The [ML004 successor](docs/reports/S22PLUS_MAINLINE_ML004_MMU_MARKERS_H0_2026-10-30.md)
qualified the points before `__enable_mmu` and after `early_ioremap_init`,
before `setup_machine_fdt`, with bounded Normal-NC temporary mappings and the
same no-map reservation. Its [attended run](docs/reports/S22PLUS_MAINLINE_ML004_RUN_2026-10-30.md)
is now consumed and closed healthy: both stage records were recovered, proving
MMU-enabled progress through `start_kernel` into the named early-C recording
point in `setup_arch`. The recorder's later unmapping/return, FDT setup and
subsequent initialization remain unproved. The operator reported recurrent
resets during the candidate; reset cause and period are not established.
RAM PID1/USB remains NO_PROOF. Original A was restored once and its first
final-health bracket passed. There is no follow-on grant or replay authority.

Two-round Claude/Argon discussion and exact source checks selected
[ML005](docs/reports/S22PLUS_MAINLINE_ML005_ARCH_MARKERS_H0_2026-10-30.md):
two C markers after `setup_machine_fdt` and after `paging_init`, replacing both
earlier sites within the same two-slot bound. The actual new kernel passes
both linked-writer tests, real EL1/EL2 no-map/page-table checks and VM PID1
evidence. The exact loader-produced DTB also passes the bounded real-kernel
FDT path fixture. Independent final review is PASS_GO with no unresolved
findings. Its [attended run](docs/reports/S22PLUS_MAINLINE_ML005_RUN_2026-10-30.md)
is now consumed and closed healthy: both new stages have five intact records,
and the independent decoder agrees. The post-paging point proves return from
this candidate's preceding helper call along the sequential path. It does
not prove its own later cleanup/return or later initialization. USB/PID1
remains NO_PROOF; original A was restored once and first final health passed.
Missing markers remain unknown; earlier candidates keep their original
evidence and meanings. No successor or follow-on grant is armed.

Two-round Claude/Argon discussion selected
[ML006](docs/reports/S22PLUS_MAINLINE_ML006_CORE_MARKERS_H0_2026-10-30.md):
V4 calls in `start_kernel` immediately after `setup_arch` and `time_init` return.
These distinguish later architecture progress from subsequent core memory,
scheduler, IRQ and timer initialization, before ordinary IRQ enablement.
The fixed writer and two-slot bound are retained, with exact late-fixmap,
no-map alias and cleanup qualification at the new points. H0 qualification
passed and final independent review is PASS_GO with no unresolved findings.
The corrected explicit-receipt producer, production task admission and current
fixed D0/raw Android health passed. ML006 is ready for its exact returned
one-operation attended approval; no grant, control or partition transfer exists.
Missing markers remain unknown and do not identify a failure location.

The exact firmware's panel auto-refresh setting supports inherited-display
investigation, but active scanout remains unmeasured. Display and additional
host USB event diagnostics remain possible observations, not already qualified
physical channels. The retained RAM-only canary objective below is unchanged.

**Retained mainline scope:** prepare and qualify the smallest exact g0q boot-only candidate that
runs a RAM PID1 and emits authenticated evidence over fixed USB2 peripheral
networking, without Linux-side UFS access or an installed-root mount.

1. Pin and reproduce the chosen mainline base, necessary port patches,
   uniLoader revision, config, g0q DTB and initramfs. Verify load/decompression
   ranges, runtime reservations, board-specific power dependencies and relevant
   past-failure checklist rows using current source/artifact consumers.
2. Use one little CPU and the essential clock, interrupt, timer, SCM, PMIC and
   USB-PHY dependencies. Compile out UFS and disable its controller and PHY;
   retain CONFIG_BLOCK in the first build to limit unrelated Kconfig changes. Exclude Wi-Fi/BT,
   PCIe, display/GPU, audio, camera, touch and remote-processor workloads.
   Preserve reserved memory even when its associated peripheral is disabled.
3. Avoid charger programming, OTG source mode and PD voltage experiments.
   Treat inherited watchdog/charging state explicitly; omitting a driver does
   not prove the hardware is off. No automatic recovery is assumed.
4. Qualify candidate/DTB/initramfs identity, same-boot actual PID1, basic
   memory/timer behavior, authenticated USB evidence and UFS-device absence.
   VM and static checks remain distinct from physical USB and boot proof.
5. Complete the changed execution/recovery review and applicable finite
   attended entry preparation before any physical effect. Existing FYG8-only
   readiness or historical approval cannot admit this candidate unchanged.
   The first physical owner retains its exact original-A return and health
   requirements under the current binding contract.

**Completion criterion:** one identified mainline g0q boot with RAM PID1 and
authenticated USB evidence, followed by the qualified original Android return
and health. A descriptor, boot logo or exec intent alone does not satisfy it.
Early failure uses the original attended physical Download recovery.

This unit does not mount, replay, repair, format or install native_data. The
retained M=40 issue remains an explicit prerequisite for later root access,
not a reason to add storage effects to the first canary.

## Milestones toward the final server

1. **Mainline boot and access:** close the RAM-only canary with separate boot,
   USB and recovery claims.
2. **Power and recoverability:** qualify the actual Gunyah/watchdog interface,
   bounded timeout reset and defined failure coverage; conservative thermal
   and frequency control; battery/input-current/charge limits and policy-failure
   behavior. Demonstrate safe idle and sustained combined load. A normal reboot
   does not prove stall recovery, and charge-current control is not an SOC cap
   or battery bypass.
3. **Protected Debian integration:** qualify read-only UFS first, then the
   existing root's current journal and exact package/data state. Permit writes
   only under the selected native_data scope. Require full current-root
   admission before installed execution. NFS root is an optional intermediate
   way to test userspace without local filesystem writes.
4. **Useful persistent runtime:** prove host PID1, one userspace owner,
   authenticated SSH/networking, ordinary package installation/configuration,
   service lifecycle and the selected container workload. Show synchronized
   data/configuration retention across clean reboot in the same integrated
   system. Do not combine unrelated historical runs into a mainline PASS.
5. **Resident recovery and updates:** boot without the development host;
   qualify network reconnection, clean/crash shutdown behavior, startup after
   power loss/low battery, and a rescue route independent of the writable root.
   Version the kernel/DTB/initramfs/modules together and qualify failed-update
   recovery and reboot-loop containment. Preserve exact host recovery artifacts.
6. **Android retirement:** once the new recovery role is demonstrated, perform
   a separately scoped migration to Linux-only operation and any needed storage
   reallocation. Retain required firmware/identity/calibration and usable
   Download recovery. Final normal operation stays in Debian.

Maintain a supported kernel and a reviewable local patch set; a frozen port
release is not a security-maintenance plan. Firmware remaining on FYG8 retains
its own security limitations. Keep important data backed up away from the phone.

## Retained history and continuing boundaries

The previous **794-line FYG8 goal through P463** is preserved byte-for-byte in
[the vendor-route snapshot](docs/archive/roadmaps/GOAL_THROUGH_P463_VENDOR_ROUTE_2026-10-27.md).
It retains all original run descriptions, source references, proof limitations
and the earlier [P410 snapshot](docs/archive/roadmaps/GOAL_THROUGH_P410_CLOSED_2026-10-01.md).
These snapshots are historical evidence, not current product direction or
device authority. Consumed journals, artifacts and grants remain consumed.

This product change does not relax partition/evidence boundaries, activate a
mainline lane, grant unattended operation or authorize Android deletion now.
Each future effect still needs the applicable exact target, current health,
artifact/source, scope and recovery binding. Required operational policy
changes are separately reviewed rather than inferred from this goal.
Uncertain writes, transfers and controls never replay. Preserve private raw
evidence and distinguish functionality, filesystem consistency, recovery and
terminal health in every result.
