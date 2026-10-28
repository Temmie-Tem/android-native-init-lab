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

- **Mainline on this g0q: not yet demonstrated.** The sister r0q port supplies
  a credible starting point, not g0q qualification. The current
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
- The [FYG8 ABL/live-FDT analysis](docs/reports/S22PLUS_FYG8_ABL_DT_HANDLING_H0_2026-10-27.md)
  establishes this target's DT handling and matching r0q RAM banks/splash.
  Static loader/kernel/DTB/initramfs placement and retained reservation checks
  are qualified above; physical g0q admission remains unproved. Bypassing
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

uniLoader is a proposed carrier, not a proved g0q boot path. The initial carrier
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

## Next bounded unit: RAM-only g0q mainline USB canary

The selected next runtime change is the H0-qualified staging-only successor.
Prepare its fresh canary identity and connect the exact new artifacts and
independent review through the existing candidate admission/owner before a new
finite attended run. Reuse successful unchanged checks and preserve ML001.
The exact firmware's panel auto-refresh setting supports later inherited-display
work, but active scanout remains unmeasured. Display and additional host USB
event diagnostics are separate follow-ups, not prerequisites for correcting the
reproduced placement conflict or proof of the old run's failure stage.

**Scope:** prepare and qualify the smallest exact g0q boot-only candidate that
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
