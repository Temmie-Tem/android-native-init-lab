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

- **Packaged Debian SysVinit as mainline RAM PID1 is demonstrated by ML022.**
  Persistent Debian and ordinary headless services remain the product objective;
  the next bounded unit has not been selected or armed. Functional development
  takes priority over optional historical fault attribution or a new
  instrumentation ladder. Existing target, authority, recovery and no-replay
  requirements remain binding.
- **ML022 is consumed: PASS_DEBIAN_SYSVINIT_RAM_PID1 / ANDROID_CLOSED_HEALTHY.**
  After one instructed phone-end replug, one authenticated response proved the
  exact packaged SysVinit PID1, direct observer child/PPID 1, runlevel 2/N,
  expected kernel/live DT/initrd, one CPU, no block devices and a working timer.
  N and A each transferred once. A failed return properties read retained its
  raw error; one health-only continuation closed original A healthy without
  another transfer. Both returned V1 frame counts are zero despite positive
  live Debian proof. Persistence, ordinary services, SSH, automatic recovery
  and replug necessity remain unproved. No F1 owner or new grant remains.
  [Run and limits](docs/reports/S22PLUS_MAINLINE_ML022_RUN_2026-11-04.md) ·
  [H0 scope](docs/reports/S22PLUS_MAINLINE_ML022_DEBIAN_RAM_H0_2026-11-04.md).
- **ML021 is consumed: PASS_MAINLINE_RAM_USB / ANDROID_CLOSED_HEALTHY.**
  The fresh ordinary RAM candidate kept ML020's functional baseline. After one
  instructed phone-end replug, reported complete by the operator, the observer
  obtained one authenticated response proving RAM PID1, the expected kernel/init
  and live DT, one CPU, no block devices and a working timer. Replug necessity
  and historical failure causes remain unproved. N and A each transferred once;
  an ADB read closed during first return-health readiness, and one health-only
  continuation closed original A healthy without another transfer. Both retained
  V1 frame counts are zero despite the positive live proof. The grant/candidate
  are consumed, no F1 owner remains and no successor is armed.
  [Run and limits](docs/reports/S22PLUS_MAINLINE_ML021_RUN_2026-11-04.md) ·
  [H0 scope](docs/reports/S22PLUS_MAINLINE_ML021_USB_ATTACH_H0_2026-11-04.md).
- **Post-ML020 watchdog compatibility H0 is complete; that analysis selected no candidate.**
  Exact vendor/firmware instructions confirm active vendor arming, same-state
  control rejection and STATUS/PET limits. Current watchdog-core registration
  rejects the proposed ping-only shape. Mainline handoff arming and its timer
  deadline remain unknown; vendor settings do not supply them. Two discussion
  rounds corrected overclaims. A bounded USB source/DT/config follow-up found
  no missing VBUS branch or selected built-in driver setting. No device action,
  new grant or owner was created, and no watchdog cause was proved or excluded.
  [Findings and limits](docs/reports/S22PLUS_MAINLINE_POST_ML020_WATCHDOG_FIT_H0_2026-11-04.md).
- **ML020 is consumed: NO_PROOF / ANDROID_CLOSED_HEALTHY.** The candidate with
  only `cpuidle.off=1` added produced no USB evidence in 116 snapshots and no
  V1 loader/entry records in the complete returned log. Physical parameter
  parsing, idle-path reach and the setting's effect remain unproved.
  N and A each transferred once; the first recovery-health procedure closed
  original A healthy without a health-only continuation. No successor, new
  grant or F1 owner is armed. The H0 parameter/VM qualification remains separate.
  [Run and limits](docs/reports/S22PLUS_MAINLINE_ML020_RUN_2026-11-04.md) ·
  [H0 scope](docs/reports/S22PLUS_MAINLINE_ML020_CPUIDLE_EXCLUSION_H0_2026-11-04.md).
- **ML019 is consumed: NO_PROOF / ANDROID_CLOSED_HEALTHY.** The ordinary
  unparked V1 candidate with the USB2 PHY correction produced no USB evidence
  in 116 snapshots and no V1 loader/entry records in the complete returned log.
  This measures neither PHY reach/effect nor the cause or location of failure.
  N and A each transferred once. One health-only continuation after a preserved
  ADB disappearance proved final original-A health. No successor, grant or F1
  owner is armed. Unchanged capability/backend reviews were reused; H0 source,
  VM and artifact qualifications remain separate from this physical result.
  [Run and limits](docs/reports/S22PLUS_MAINLINE_ML019_RUN_2026-11-04.md) ·
  [H0 scope](docs/reports/S22PLUS_MAINLINE_ML019_USB_PHY_H0_2026-11-04.md).

- **ML018 is consumed: loader-handoff and kernel-entry observed /
  ANDROID_CLOSED_HEALTHY.** Both fresh V1 frames are present in the complete
  returned log and independently authenticated. The ordinary-route early park
  intentionally cannot reach PID1/USB, whose verdict remains NO_PROOF. N and A
  each transferred once; one health-only continuation closed A healthy.
  Static frames prove neither physical park, unique attempt, same-boot pairing
  nor a cause of earlier zeros. The one-park unit is complete, with no successor
  or new grant armed. [Run and limits](docs/reports/S22PLUS_MAINLINE_ML018_RUN_2026-11-04.md).

- **ML012 is consumed: NO_PROOF / ANDROID_CLOSED_HEALTHY.** The exact
  GPIO50/93 reservation correction retains V9 observation, but all 114 USB
  snapshots show absence and the complete returned log has zero V9 records.
  Missing markers locate no failure and do not measure the correction's effect.
  The operator reports the same boot-loop interval, without a new numeric period.
  N and A each transferred once. After a preserved ADB disappearance and
  incomplete property prefix without boot ID, one health-only continuation
  passed; no extra transfer occurred. The incomplete prefix cannot distinguish
  reconnect from an additional Android boot. No successor or grant is armed.
  Separate H0 analysis confirms hardware/firmware watchdog control paths below
  Linux; candidate arming, expiry and reset attribution remain unproved.
  [ML012 run](docs/reports/S22PLUS_MAINLINE_ML012_RUN_2026-10-31.md).
- **ML011 demonstrates execution inside `deferred_probe_initcall` and its first
  worker phase.** It records multiple OF-associated callback returns and the
  TLMM-associated pre-callback point, without a TLMM callback/bus return record.
  Its [run](docs/reports/S22PLUS_MAINLINE_ML011_RUN_2026-10-31.md) is consumed and
  closed healthy after one N and one original-A transfer. Missing records locate
  no failure or reset cause, and returned calls are not driver/probe success.
  ML010 retains its earlier full-initcall evidence. Earlier candidates retain their
  own evidence; no shared-boot or historical progress transfer is inferred.
  These earlier results did not prove a usable RAM PID1/USB boot; ML021 later
  supplied that separate live proof. The sister r0q port supplies
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
- **ML006 is consumed: both return witnesses observed / ANDROID_CLOSED_HEALTHY.**
  Six intact records at each site were recovered on the exact returned Android
  boot, with no damaged/foreign candidates. The later point proves return from
  `setup_arch`, the preceding helper call and `time_init` along this candidate's
  sequential path; the earlier helper may have skipped writing. The second
  helper's cleanup and return, ordinary IRQ enablement, timer ticks and PID1/USB remain
  unproved. N and original A were each transferred once; first final health
  passed. One expected target-not-found boot-wait read was preserved and handled
  by the existing bounded reobservation path. No health-only continuation or
  follow-on grant was needed. [ML006 run](docs/reports/S22PLUS_MAINLINE_ML006_RUN_2026-10-30.md).
- **ML007 is consumed: pre-IRQ and pre-rest-init observed / ANDROID_CLOSED_HEALTHY.**
  Five intact records at each site were recovered on the exact returned Android
  boot, with no damaged/foreign candidates. The later point follows IRQ unmask
  and the intervening core initialization; it proves return from this candidate's
  earlier helper call, which may have skipped writing. It does not prove its own
  cleanup/return, `rest_init` entry, IRQ delivery, timer ticks or PID1/USB. The
  operator reports the same boot-loop interval as earlier experience, without
  a numeric period or cause. All 116 USB snapshots showed absence. N and A each
  transferred once; first final health passed with no failed task capture or
  health-only continuation. No follow-on grant is armed.
  [ML007 run](docs/reports/S22PLUS_MAINLINE_ML007_RUN_2026-10-30.md).
- **ML008 is consumed: post-kthreadd-wait observed / ANDROID_CLOSED_HEALTHY.**
  Five intact first-site records and no post-async-sync record were recovered
  on the exact returned Android boot, with zero damaged/foreign candidates.
  Independent decoding agrees. Kernel initialization-thread progress is proved;
  the first helper's later return and the second recording point are unproved.
  Missing records do not locate a failure or establish non-execution. The
  operator reports the same boot-loop interval, without a numeric period.
  All 116 USB snapshots showed absence. N and A each transferred once and
  first final health passed, with no failed task capture or health-only
  continuation. No follow-on grant is armed.
  [ML008 run](docs/reports/S22PLUS_MAINLINE_ML008_RUN_2026-10-30.md).
- **ML009 is consumed: pre-basic-setup observed / ANDROID_CLOSED_HEALTHY.**
  Five intact first-site records and no post-basic-setup record were recovered
  on the exact returned Android boot, with zero damaged/foreign candidates.
  Independent decoding agrees. The first point follows earlier kernel-thread
  preparation and early initcalls; its helper return and basic-setup entry are
  unproved. Missing later evidence does not locate a driver/initcall failure.
  The operator reports the same boot-loop interval, without a numeric period.
  All 115 raw USB snapshots show actual endpoint absence. N and A each
  transferred once; first final health passed with no failed task capture or
  health-only continuation. No follow-on grant is armed.
  [ML009 run](docs/reports/S22PLUS_MAINLINE_ML009_RUN_2026-10-30.md).
- The [FYG8 ABL/live-FDT analysis](docs/reports/S22PLUS_FYG8_ABL_DT_HANDLING_H0_2026-10-27.md)
  establishes this target's DT handling and matching r0q RAM banks/splash.
  Static loader/kernel/DTB/initramfs placement and retained reservation checks
  are qualified above; ML021 separately proved live RAM PID1/USB. Bypassing
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

uniLoader has delivered the FYG8 Android control, ML003's early mainline entry
and ML021's authenticated RAM PID1/USB boot. Installed Debian on mainline is
still unproved. The initial carrier
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

## Next bounded unit: source-backed full-progress selection after ML018

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
The fixed writer and two-slot bound were retained, with exact late-fixmap,
no-map alias and cleanup qualification at the new points. Its
[attended run](docs/reports/S22PLUS_MAINLINE_ML006_RUN_2026-10-30.md) is now
consumed and closed healthy: both stages have six intact records and the
independent decoder agrees. USB/PID1 remains NO_PROOF; original A was restored
once and first final health passed. Missing markers remain unknown and do not
identify a failure location. No successor or follow-on grant is armed.

The next two-round Claude/Argon discussion selected
[ML007](docs/reports/S22PLUS_MAINLINE_ML007_BOOTSTRAP_MARKERS_H0_2026-10-30.md):
V5 markers immediately before ordinary IRQ enablement and immediately before
`rest_init`. The unchanged writer remains in the initial bootstrap task with
preemption disabled, before PID1/kthreadd creation and driver initcalls.
Exact linked calls, enabled interrupt-path interference, initial-task/CPU and
IRQ context, late mappings, no linear alias and cleanup are qualified.
Its independently reviewed and separately approved
[attended run](docs/reports/S22PLUS_MAINLINE_ML007_RUN_2026-10-30.md) is consumed
and closed healthy. Five intact records at each site establish at-least-once
progress to the point before `rest_init`; independent decoding agrees. USB/PID1
remains NO_PROOF, and the operator reports a boot loop at the same interval as
earlier experience. N and A each transferred once and first final health passed.
Delay calibration may use `lpj_fine`; the later positive proves neither timer
ticks nor IRQ delivery. No successor grant or device effect is armed.

The next two-round Claude/Argon discussion selected
[ML008](docs/reports/S22PLUS_MAINLINE_ML008_INIT_THREAD_MARKERS_H0_2026-10-30.md):
V6 calls in `kernel_init` after the kthreadd wait and after registered async
synchronization, before init-memory freeing. The writer and two-slot bound are
unchanged. Fresh layout derivation, actual PID1 entry/return context,
post-initcall mapper/reservation exclusions and late mappings are qualified.
The marker VM supplies the physical candidate initramfs so the later path is
reachable; the full RAM-PID1 VM retains its distinct VM initramfs. Final
independent review is PASS_GO with no findings. Its separately approved
[attended run](docs/reports/S22PLUS_MAINLINE_ML008_RUN_2026-10-30.md) is consumed
and closed healthy: five first-site records were recovered, while the second
site remains unproved. The missing later record does not establish a failure
interval. USB/userspace PID1 remains NO_PROOF. The operator reports the same
boot-loop interval. N and A each transferred once, and first final health
passed without a health-only continuation. No successor grant is armed.

Two-round Claude/Argon discussion selected ML009: two V7 calls immediately
before and after `do_basic_setup` in `kernel_init_freeable`. The writer and
two-slot bound are unchanged. This separates additional positive progress
through early kernel-thread preparation from the regular initcall traversal
and remaining initramfs/access/async tail. Missing ML008 or V7 records do not
select a failure interval or reset cause. Actual linked placement must account
for compiler-inlined basic setup and initcall loops. Fresh Image, actual
linked calls/loops, 318 C cases, 13 mapping cases, full RAM-PID1 VM and repeated
boot/AP packaging passed. Final independent review is PASS_GO with no findings.
Its separately approved [attended run](docs/reports/S22PLUS_MAINLINE_ML009_RUN_2026-10-30.md)
is consumed and closed healthy. Five pre-basic-setup records were recovered;
the post-basic recording point remains unproved. The missing frame supplies no
failure interval. USB/userspace PID1 remains NO_PROOF. The operator reports
the same boot-loop interval. N and A each transferred once and first final
health passed without a health-only continuation. No successor grant is armed.
The [preparation report](docs/reports/S22PLUS_MAINLINE_ML009_BASIC_SETUP_MARKERS_H0_2026-10-30.md)
retains the historical qualification and readiness checkpoint.

The operator requested consolidation to reduce repeated physical trials.
[ML010](docs/reports/S22PLUS_MAINLINE_ML010_CONSOLIDATED_TRACE_H0_2026-10-30.md)
now has a fresh H0-qualified full trace of all 1,825 regular initcall entry/return
points plus six milestones through the pre-free async return. Its 3,656 records
use a fixed latched window and retain available leading slots when history is
short. Actual C, full EL1/EL2 traversal, mapping/context, RAM-PID1 VM and package
checks passed, followed by independent PASS_GO and separately returned exact
attended approval. Its [physical run](docs/reports/S22PLUS_MAINLINE_ML010_RUN_2026-10-30.md)
is consumed and closed healthy: 12,208 intact records cover 3,590 distinct
events, with all entry/return pairs for ordinals 0–1,792 and the entry point
before ordinal 1,793, `deferred_probe_initcall` at level 7. Six damaged candidates
are rejected. The missing return does not identify a culprit or reset cause;
record counts are not boot counts. All 114 USB snapshots show actual absence.
N and A each transferred once and first final health passed without a health-only
continuation. USB/userspace PID1 remains NO_PROOF, and no successor is armed.

[ML011](docs/reports/S22PLUS_MAINLINE_ML011_DEFERRED_PROBE_H0_2026-10-30.md)
used 3,914 bounded events combining sparse initcall
progress, both deferred-initcall phases and worker/preparation/callback points
associated with a fixed 379-node DT catalog. Actual ARM64 writer/hook, real
EL1/EL2 PID1/worker, RAM-userspace-PID1 and boot-only package checks pass.
Its separately approved [physical run](docs/reports/S22PLUS_MAINLINE_ML011_RUN_2026-10-31.md)
is now consumed and closed healthy. The retained log has 284 intact records
across 82 events: first-trigger return and worker entry, nine named associations
with all five points, an unlisted-OF bucket with all five, and the TLMM association
with three pre-points but no callback/bus return. No first-flush return or phase-2
point was accepted. All 114 USB snapshots show actual absence. Explicit unknown
nodes, incomplete retries and no same-boot pairing remain limitations.

The subsequent exact-source comparison found GPIO50/93 reserved in the retained
FYG8 live FDT but omitted from the mainline board data. Two-round Claude/Argon
discussion selected [ML012](docs/reports/S22PLUS_MAINLINE_ML012_GPIO_RESERVATIONS_H0_2026-10-31.md)
to restore those reservations while retaining V9 observation. The correction
removes the two indices from GPIO registration-time direction reads; it is not
a blanket MMIO prohibition or a diagnosis of ML011. Independent static checks
find no active consumer of the reserved pins. Fresh actual-code, real-MMU,
RAM-PID1 and package qualification passed, followed by independent exact-artifact
PASS_GO and fixed preapproval D0. Its separately approved
[run](docs/reports/S22PLUS_MAINLINE_ML012_RUN_2026-10-31.md) is now consumed and
closed healthy: USB stayed absent and the complete returned log contains no
V9 record. N and A each transferred once; one health-only continuation completed
final health after ADB disappearance. The abandoned property prefix had no boot
ID, so an extra Android boot or its effect on retention cannot be established.
The source-supported board reservation is retained without a claimed physical
benefit. No successor or grant is armed.

The next bounded H0 question is useful positive evidence and return/retention
continuity after ML012. Its missing frames do not identify an early kernel
failure or a TLMM outcome. Hardware/firmware watchdog control paths below Linux
are confirmed in retained code, but candidate arming and expiry are unproved;
the operator's same-interval observation is not a causal measurement. Those
observations alone justify no timer intervention or device action.

[ML013](docs/reports/S22PLUS_MAINLINE_ML013_EARLY_TLMM_OBSERVATIONS_H0_2026-10-31.md)
now selects a bounded V10 observation successor after two-round external
discussion. One shared C latch places priority records at the newest end,
adds pre-FDT/post-setup/PID1-entry points and token-scoped TLMM structural and
return-class observations, while retaining the sparse initcall/node catalog.
Its 3,968 frames remain within the existing write ceiling. Fresh actual-code,
independent hook, fourteen real-MMU, RAM-PID1 and repeated packaging checks
pass, followed by independent PASS_GO and V10/V21 publication. Its separately
approved [run](docs/reports/S22PLUS_MAINLINE_ML013_RUN_2026-10-31.md) is now
consumed and closed healthy: all 114 USB snapshots show absence, and the
complete returned log contains zero V10 records. N and A each transferred
once. One health-only continuation completed final health after an ADB read
failure; the abandoned prefix contained only model/device and no boot ID.
An extra return boot and its effect on retention remain unproved. The GPIO
correction is retained without a physical benefit claim. Earlier latch drift
can suppress later records; no missing frame supplies failure localization.
The next bounded H0 question remains return/retention continuity. No successor
or grant is armed.

[ML014](docs/reports/S22PLUS_MAINLINE_ML014_RETURN_BOOT_IDENTITY_H0_2026-10-31.md)
is now prepared after two-round Claude/Argon discussion. It keeps V10
runtime observation and the source-supported GPIO reservations, with a fresh
candidate/key. Mainline original-A return reads now capture boot ID first in
the existing readiness/properties commands. The bounded wait and complete
health requirements are unchanged; a diagnostic prefix is never health.
Fresh artifact qualification, final independent review and fixed preapproval
D0 pass. The return-identity capability and backend V22 receipts are published
without changing the stable worker. Its separately approved
[2026-11-03 run](docs/reports/S22PLUS_MAINLINE_ML014_RUN_2026-11-03.md) is now
consumed and closed healthy: N and A each transferred once, all 114 USB
snapshots showed absence, and the complete returned log contained zero V10
records. One health-only continuation closed after an ADB disappearance.
Five earlier readiness IDs, continuation readiness, final health and the
post-closure read all share one observed Android boot ID. The abandoned
properties prefix was only `boot_id=` and supplied no UUID itself. These
observations identify no transport-failure cause, earlier unseen boot or
marker-loss mechanism. Marker eligibility and retention before the earliest
Android observation remain open H0 questions. No successor or new grant is
armed; ML013 retains its earlier consumed healthy closure.

[ML015](docs/reports/S22PLUS_MAINLINE_ML015_V2_CALIBRATION_H0_2026-11-03.md)
is prepared as a fresh existing-V2 calibration after two-round external
discussion. It retains the corrected GPIO DTB, configuration and ML014 return
observer, while replacing V10 instrumentation with the previously qualified
pre-MMU and early-C sites. Unchanged capability/backend reviews are reused;
fresh exact artifact qualification and independent entry review pass. Fixed
preapproval D0 also passes; the existing capability/backend and worker are
unchanged. Its separately approved
[physical run](docs/reports/S22PLUS_MAINLINE_ML015_RUN_2026-11-03.md) is now
consumed and closed healthy: N and A each transferred once, all 116 USB
snapshots showed absence, and neither V2 record was recovered from the complete
returned log. One health-only continuation closed after `wait-077-boot`
returned `error: closed` before full health started. Ten successful return
identity observations share one Android boot ID; earlier unseen boots,
header eligibility and retention loss remain unproved. This candidate lacks
V10 instrumentation, but its zero does not explain the older V10 results.
Positive records would establish occurrence only in this candidate, without
isolating past V10 causes or assigning meaning to a missing companion record.
No successor or new grant is armed.

[LA002](docs/reports/S22PLUS_LOADER_LOGM_LA002_RUN_2026-11-03.md) is consumed
and closed healthy with a positive LOGM write/read control on the previously
successful LA001 loader-to-Android path. Its current FDT reports eligible EL1
state, three equal header samples and zero readback mismatches; the candidate
Android snapshot contains one exact authenticated frame. All three complete
candidate health brackets share one observed boot before normal Download/A
return. N and A each transferred once. One health-only continuation completed
after an ADB disappearance; the initial properties capture was empty, so it
supplies no return-ID continuity. The
[qualified capability](docs/reports/S22PLUS_LOADER_LOGM_LA002_H0_2026-11-03.md),
backend and stable worker were unchanged during execution. Current-FDT writer
observations and static candidate-frame occurrence remain separate: no shared
attempt, reset retention, historical failure cause or mainline boot is proved.
LA002's operation and grant are consumed; no F1 owner or successor is armed.

[ML016](docs/reports/S22PLUS_MAINLINE_ML016_V1_CALIBRATION_H0_2026-11-03.md)
is H0-qualified after two-round Claude/Argon discussion.
It uses the existing V1 loader-handoff and kernel-entry records, with ML015's
exact corrected DTB/config and fresh candidate identity. Retained actual-code
checks pass using LA002's observed header as a fixture; this does not establish
ML016's physical state. No unsupported regulator, thermal or driver change is
selected. New mainline/backend review receipts reconcile LA002's
loader-only closure changes without altering recovery or the stable worker.
Fresh artifact qualification, final independent review and fixed preapproval
D0 pass. Static positives would prove occurrence only, with no
shared-boot, missing-frame localization or ML015 causal claim. Its separately
approved [physical run](docs/reports/S22PLUS_MAINLINE_ML016_RUN_2026-11-03.md)
is now consumed and closed healthy: N and A each transferred once, all 116 USB
snapshots showed absence, and the complete returned log contains neither V1
record under both decoders. First-attempt final health passed without a
health-only continuation. Ten accepted return/health/log-read observations
share one Android boot ID; an incomplete successful readiness prefix supplied
no identity. Loader/kernel occurrence, physical recording eligibility and
retention remain unproved. This zero supplies no causal explanation or basis
for an unchanged repeat. No successor or new grant is armed.

[LA003](docs/reports/S22PLUS_LOADER_PREFIX_LA003_RUN_2026-11-04.md) is consumed
and closed healthy with positive current-boot prefix-return proof. A fresh full mainline
Image executes only its fixed Image-header/primary-entry prefix, calls the
unchanged V1 writer and returns before MMU preparation. The resident loader
then copies and enters the exact original-A vendor Image at the same payload
destination. A fixed current-FDT report supplies prefix-return/CPU facts and
separate post-call log-byte comparisons; it does not prove current-attempt
stores, reset retention, historical failure cause or a full mainline boot.
The enlarged layout, actual instruction/EL paths, deterministic boot/AP,
raw producer/consumer, independent final review and fixed preapproval health
all pass. The loader-prefix capability and backend V25 remained unchanged
during the separately approved run. The report confirms the exact entry PC,
EL1 and unchanged CPU state; both post-call slot comparisons match, and three
complete candidate health brackets share one observed boot. N and A each
transferred once, and both normal Download controls completed. An empty
`error: closed` properties read
stopped initial final health; one health-only continuation then passed without
another transfer/control. The separate mainline capability is not renewed by
this selected loader-operation review. No successor or new grant was armed
at that closure.

[ML017](docs/reports/S22PLUS_MAINLINE_ML017_TLMM_EXCLUSION_H0_2026-11-04.md)
was selected after two-round Claude/Argon discussion. It disables only the
unused TLMM DT node, preserving the corrected
GPIO reservations and existing V1 writers/configuration. Complete active-DT
consumer checks found no TLMM dependency in this configuration; the compiled
DT differs only in that status property. The fresh kernel differs from ML016
only in its candidate frame and build ID, with unchanged symbol layout.
Actual V1/EL/loader tests, RAM PID1 VM, matching boot/AP packages and 82
host/terminal tests pass. Final independent current-source/artifact review is
`PASS_GO` with no findings; the new mainline and backend V26 receipts are
published with the stable worker unchanged. The actual production preparation
and fixed seven-read preapproval D0 pass. Its separately approved
[physical run](docs/reports/S22PLUS_MAINLINE_ML017_RUN_2026-11-04.md) is consumed
and closed original A healthy: all 116 USB snapshots show endpoint absence,
and the complete returned log contains neither V1 record. N and A transferred
once each. An ADB disappearance interrupted initial health; one health-only
continuation passed. A complete UUID in the initial partial properties and
the other accepted return/D0 observations share one observed Android boot,
without proving earlier continuity or a failure cause. TLMM exclusion supplied
no functional proof or historical diagnosis. No successor, new grant or F1
owner remains. A90 and S20+ are untouched.

[ML018](docs/reports/S22PLUS_MAINLINE_ML018_ENTRY_PARK_H0_2026-11-04.md)
was selected by two-round Claude/Argon discussion:
one ordinary-route `primary_entry` park immediately after the unchanged V1
writer, before `record_mmu_state`, with ML017 DT/config unchanged. It
intentionally cannot reach PID1/USB. Exact changed-Image/layout and real
EL1/EL2 park qualification, declaration/receipt admission, independent PASS_GO
review, production preparation and fixed seven-read preapproval D0 pass. The
new mainline capability/backend V27 retain the stable worker and original-A
recovery. Its separately approved [run](docs/reports/S22PLUS_MAINLINE_ML018_RUN_2026-11-04.md)
is now consumed and closed healthy: both fresh V1 records survived to the
returned log, with production and independent HMAC agreement. All 116 USB
snapshots show expected absence. N and A each transferred once, and one
health-only continuation completed recovery after an ADB disappearance.
Twelve accepted return/D0 identity observations agree on one observed Android
boot. The records prove only their build-specific stage occurrence and
survival, never physical park, unique attempt, same-boot pairing or past cause.
The one-park unit is complete. Further work needs a concrete source-backed
full-progress hypothesis; no new candidate or grant is armed.

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
