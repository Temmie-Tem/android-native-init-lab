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

- **ML030 has an H0 boot-only AP for a five-minute same-boot witness and one
  UFS link attempt.** The revised RPMh path addresses the reproduced late
  trigger and quarantines uncertain slots. The unmarked kernel ran the prior
  Debian SSH and normal-return VM checks. The phone's uptime, physical link,
  and return remain unmeasured for ML030. The proposed common scope and live
  owner require separate adoption and review. ML028 is the last physical
  closure. [ML030 evidence](docs/reports/S22PLUS_MAINLINE_ML030_DWELL_LINK_H0_2026-11-05.md)
  · [proposed scope](docs/plans/S22PLUS_ML030_LINK_ONLY_SCOPE_2026-11-05.md).

- **ML029 completed a host-only UFS wiring and probe study.** A private copy
  of the disabled ML028 DT gained two known g0q connections (reset GPIO 210
  and PHY analog L5) and a correction to the host reference-clock rate
  table. Reversing those three changes reproduced ML028's canonical DT.
  This study left the PM8350 L6/L9 supply and pre-scan command limits for
  ML030. The latest physical closure is ML028.
  [Study, sources and next decision](docs/reports/S22PLUS_MAINLINE_ML029_UFS_H0_2026-11-05.md).

- **ML028 is consumed with `PASS_DEBIAN_RC_SSH_CYCLE_RAM` and `ANDROID_CLOSED_HEALTHY`.**
  On the S22+, packaged rc2 started SSH, one fixed UID/GID 1000 command
  succeeded with zero effective capabilities, and rc6 stopped the same master.
  An exact normal Download ticket admitted original A. N and A each transferred
  once. After an ADB health read failed, the existing owner completed a fresh
  seven-read bracket and removed its network profile. The one-service RAM
  result is complete. [Physical run](docs/reports/S22PLUS_MAINLINE_ML028_RUN_2026-11-05.md) · [H0 qualification](docs/reports/S22PLUS_MAINLINE_ML028_RC_SSH_CYCLE_H0_2026-11-05.md).

- **ML027 is consumed: PASS_MAINLINE_DOWNLOAD_RAM / ANDROID_CLOSED_HEALTHY.**
  Authenticated packaged Debian RAM PID1/USB and one same-connection fixed
  control led to machine-proved normal Download and original-A return.
  N/A each transferred once. One failed final-health properties read was
  preserved; a health-only continuation completed all seven health reads
  without another transfer. The owned profile was removed and no owner remains.
  No physical Download was requested. Automatic failure recovery, full SysV
  shutdown and persistence remain unproved; its grant is consumed.
  [Run and limits](docs/reports/S22PLUS_MAINLINE_ML027_RUN_2026-11-05.md) · [H0 qualification](docs/reports/S22PLUS_MAINLINE_ML027_DOWNLOAD_RETURN_H0_2026-11-05.md).

- **ML026 is consumed: PASS_DEBIAN_SSH_RAM / ANDROID_CLOSED_HEALTHY.**
  Authenticated packaged Debian PID1/USB and one same-boot fixed SSH command
  proved UID/GID 1000 and zero effective capabilities. N/A each transferred
  once; normal final health passed and the owned profile was removed. A tool
  acknowledgment timed out, but the original continuation completed without
  replay. Anchor/final names matched, so correction causality is not isolated.
  Persistence/general shell/automatic recovery remain unproved; no new owner/grant.
  [Run and limits](docs/reports/S22PLUS_MAINLINE_ML026_RUN_2026-11-05.md) · [H0 correction](docs/reports/S22PLUS_MAINLINE_ML026_INTERFACE_BINDING_H0_2026-11-05.md).

- The mainline baseline has proved RAM PID1/USB, packaged Debian SysVinit as
  initial PID1, the ML026 fixed unprivileged same-boot SSH command and ML027's
  fixed normal Download return. ML028 joined packaged rc2 startup, nonroot SSH,
  rc6 stop and normal Download in one RAM boot. It
  has not proved installed Debian on mainline, Linux UFS, full SysV shutdown,
  a general shell, automatic failure recovery, residency or endurance.
- ML025 and ML024 are closed NO_PROOF with original-A/final health complete.
  ML024's late replug report remains separate from its actual unknown timing;
  ML025's interface-name stop remains separate from rename/replug causality.
  Their grants, candidate effects and raw failures remain consumed.

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

## Completed bounded unit: ML027 normal Download from RAM

The selected unit uses the same four-package Debian RAM SysVinit closure and
adds one distinct authenticated Download control, mutually exclusive with the
SSH variant. The same TCP connection first supplies full sealed base evidence;
only its validated current boot/artifact can receive one fixed control. The
existing mainline NVMEM reboot-mode driver gains only the exact DT Download
value, and the existing SCM NODUMP/PSCI normal reboot chain remains explicit.
There is no Linux storage or new vendor-module/reset framework.

H0 qualification, complete producer reproduction, independent review and exact
boot-only preparation were followed by one approved attended physical run.
The issued replug cue was resolved before normal control. The original
host/device windows, fixed intent-time return deadline, exact Download ticket,
single original-A transfer and final health all joined their retained evidence.
The first failed health bracket remains separate from the successful complete
health-only continuation; consumed controls and transfers never replayed.

The selected completion criterion, `PASS_MAINLINE_DOWNLOAD_RAM`, is achieved.
ACK/EOF alone were not accepted as Download arrival. This normal return proves
neither automatic stall recovery nor persistent/resident Debian. The broader
watchdog interface and Linux storage work remain separate possible subsequent
units. ML027's grant is consumed.

## Completed bounded unit: ML028 Debian rc-managed SSH cycle in RAM

The physical run met the selected service criterion. Packaged rc2 and rc6
ran their fixed SSH scripts under Debian PID 1. The stop receipt joined the
startup PID and start ticks to both successful exits, the disappearance of
the old master and pidfile, and a final count of zero matching packaged SSH
processes. The original owner proved normal Download and returned original A.
The ML028 grant is consumed.

## Completed bounded unit: ML029 mainline UFS host study

The FYG8 board overlay and captured FDT agree on six regulator votes.
Mainline's clock names expose an inherited 75–300 MHz range on `ref_clk`;
the study DT restores the shipped zero limits without changing USB's L5
constraints. The normal UFS probe performs reset, link startup and device
initialization before asynchronous SCSI discovery. The next design needs
g0q-specific evidence for the L6/L9 upstream supply, vendor auxiliary votes
and a defined limit on controller/device effects. ML029 used only retained
data and has no physical grant.

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

The previous 798-line goal through ML026 is preserved byte-for-byte in
[the mainline RAM snapshot](docs/archive/roadmaps/GOAL_THROUGH_ML026_MAINLINE_RAM_2026-11-05.md).
It retains the completed ML001–ML026 research/diagnostic history, exact report
links, proof limits and the earlier vendor-route snapshots. Archival changes
neither retained evidence nor current authority. Historical next-step text is
superseded by the current selected bounded unit; consumed grants remain consumed.

This product change does not relax partition/evidence boundaries, activate a
mainline lane, grant unattended operation or authorize Android deletion now.
Each future effect still needs the applicable exact target, current health,
artifact/source, scope and recovery binding. Required operational policy
changes are separately reviewed rather than inferred from this goal.
Uncertain writes, transfers and controls never replay. Preserve private raw
evidence and distinguish functionality, filesystem consistency, recovery and
terminal health in every result.
