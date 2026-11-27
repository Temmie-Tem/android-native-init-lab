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

The operator closed the separate S22+ modem research on **2026-11-22**.
The FYG1, GYI7 and GZE4 comparisons found no verified input for transmitting
user-supplied I/Q samples. The proposed VMID 15 permission test and A/B
waveform transmissions were never run. [Modem research closure](docs/GOAL_S22PLUS_MODEM.md)

Per-run detail through ML050 is preserved byte-for-byte in
[the ML050 snapshot](docs/archive/roadmaps/GOAL_THROUGH_ML050_MAINLINE_UFS_2026-11-19.md);
each run's report remains the authoritative record. The
[2026-11-22 uniLoader LOGM control](docs/reports/S22PLUS_UNILOADER_LOGM_RUN_2026-11-22.md)
proved the loader's byte-for-byte readback and recovered one candidate frame
from the running vendor Android snapshot. Its original-A return closed healthy
after a health-only continuation. The [SCM USB run](docs/reports/S22PLUS_MAINLINE_SCM_USB_RUN_2026-11-22.md)
then observed the mainline SCM driver bound on the physical S22+. Its one
original-A transfer and subsequent health-only continuation closed healthy.
ML050 closed healthy on 2026-11-11. ML049 was prepared and reviewed but
never executed. Every consumed run, grant and candidate stays consumed.

**Proven on mainline (RAM only):** uniLoader entry, PID1 and USB/NCM;
packaged Debian SysVinit as initial PID1; a fixed unprivileged same-boot SSH
command (ML026); authenticated normal Download return (ML027); rc2 start,
nonroot SSH and rc6 stop in one boot (ML028); the 300-second same-boot
witness; the V6+ automatic result-bound Download and original-A recovery;
one completed UFS link startup with Device Present (ML054, one boot).
**Not proven:** UFS beyond link startup (power mode, UPIU/SCSI, block
devices), installed Debian, full SysV shutdown, a general shell, stall
recovery, residency or endurance.

### Selected unit: observe the first mainline USB connection (closed)

On 2026-11-25 the first attended MAX77705 observation closed
`OBSERVED_MAX77705_USB_SWITCH` / `ANDROID_CLOSED_HEALTHY` under the v59
review set adopted in `70a5449b49`. The switch initially read open
(`0x3f`). Later reads returned `0x00`, and the host enumerated the USB2
gadget and received an authenticated response. No sample returned
`COM_USB` (`0x09`). The USB routing at enumeration and the cause of the
replug dependency remain open. Candidate and original Android each
transferred once. The original owner finished with a health-only read after
an ADB interruption. The candidate and approval are consumed.
[Physical observation and recovery](docs/reports/S22PLUS_MAINLINE_MAX77705_USB_RUN_2026-11-25.md)

**Stage 2 result: one `COM_USB` write removed the replug.** On 2026-11-26
the attended one-write run closed `OBSERVED_MAX77705_USB_ROUTE` /
`ANDROID_CLOSED_HEALTHY` with `ROUTE_CONFIGURED_WITHOUT_REPLUG` and no cue.
The switch read `0x3f` and the UDC read "not attached" for 3 s. One
`CONTROL1_W(0x09)` was followed by the host's bus reset 0.6 s later and
configuration 0.8 s later. The write held (`0x09` at readback and at the
request), with no cable change. Candidate and original Android each
transferred once; the first final health passed. This is one boot; it
shows sufficiency, not the mechanism or which kernel component should own
the write.
[Run](docs/reports/S22PLUS_MAINLINE_MAX77705_ROUTE_RUN_2026-11-26.md) ·
[Design and H0](docs/reports/S22PLUS_MAINLINE_MAX77705_ROUTE_H0_2026-11-25.md) ·
[Policy](docs/operations/S22PLUS_MAINLINE_MAX77705_ROUTE_V1.md)

**No-touch cycle (route-timer): one run closed.** The first unit of the
hands-off plan composes the unchanged Stage 2 route observer with the ML050
timer child. PID1 arms one ordinary `RESTART2("download")` at guest BOOTTIME
555 s. The original owner waits for a new Download within N launch plus
660 s, then performs one original-A transfer and Android health. No attach
cue exists. The scope was adopted in `1e12f415a2` (v61 set) after Codex
returned `ROUTE_TIMER_PASS_GO` and the operator approved the narrow
common-contract delegation.

The 2026-11-26 run closed `OBSERVED_MAX77705_USB_ROUTE` /
`ANDROID_CLOSED_HEALTHY`. The switch started at `0x3f` and one write led to
configuration, giving `ROUTE_CONFIGURED_WITHOUT_REPLUG` again. A new Download
arrived 590 s after the candidate launch, and the automatic owner restored
original A, which passed health. There was no cue and no
continue/recover dispatch. The run does not prove which caller reset the
device, and it does not cover a hang before the child is armed. It is one
normal run on the plan's evidence ladder. Activating Conditional Autonomous
F1 remains the operator's decision.

Two more normal runs are being prepared. The registry admits each AP once,
so the v62 set (`1074da5b1c`) adds two repeat-build qualifications of the same
composition to the binding module. Codex returned `ROUTE_TIMER_REPEAT_PASS_GO`.
Run 2 closed `ANDROID_CLOSED_HEALTHY` with the same route, timer and
automatic return (Download 589.77 s after N). The first health attempt
stopped on a transient `adb` `error: closed` during Android boot and was
finished by one host-side `resume_approved_health`. This is the first
hands-off gap observed
([run 2](docs/reports/S22PLUS_MAINLINE_MAX77705_ROUTE_TIMER_RUN2_2026-11-26.md)).
The v63 set (`ff8a7cde8d`, Codex `READY_CLOSED_PASS_GO`) makes the mainline
original-A readiness wait treat `error: closed` like `device not found`. The
v62 run-3 task `5235aa7c…` was abandoned without a grant. Run 3 (`d466f0e4…`) closed `ANDROID_CLOSED_HEALTHY` with the same route,
timer and automatic return. Readiness passed, but the health bracket lost
ADB at 649 s. Runs 1 to 3 all show transient ADB failures about 40 s after
the A transfer, as Android reports boot complete. Runs 2 and 3 each needed
one host-side health resume
([run 3](docs/reports/S22PLUS_MAINLINE_MAX77705_ROUTE_TIMER_RUN3_2026-11-26.md)).
That makes three normal runs, none needing a physical action, but the
health start is not yet hands-off. The v64 set (`fa2acb0ee2`, Codex
`READY_SETTLE_PASS_GO` in round 3) makes readiness wait until the target's
replies hold on one ADB transport and boot ID for 10 s before health starts.
The seven-read health acceptance is unchanged. The set also adds two
repeat-build qualifications. Run 4 (`972df4f8…`) closed
`ANDROID_CLOSED_HEALTHY` with no physical action. Health passed on its first
attempt after the settle window. The automatic-recovery usbfs scan stopped
at the Download transition (`usbfs-endpoint-departed`, racing the
candidate's own disconnect), so one host-side `recover_approved_task`
transferred the original A
([run 4](docs/reports/S22PLUS_MAINLINE_MAX77705_ROUTE_TIMER_RUN4_2026-11-27.md)).
That scan race is now the remaining hands-off gap. The v65 set
(`c56dea801f`, Codex `DEPARTURE_RACE_PASS_GO` in round 2) lets only the
automatic-recovery observation take a new census after such an empty-census
departure. Every other Odin wait keeps the strict stop. Run 5
(`6f6f922c…`) closed `ANDROID_CLOSED_HEALTHY` with no physical action and no
host-side step. The race recurred and was retried, the automatic owner
transferred A, and health passed first time
([run 5](docs/reports/S22PLUS_MAINLINE_MAX77705_ROUTE_TIMER_RUN5_2026-11-27.md)).
This is the first fully hands-off cycle. Repeatability is not yet shown. The
v66 set (`0ea046353f`, Codex `REPEAT3_PASS_GO`) qualifies three more builds
(r6 to r8) for repeatability runs. Run 6 (`dbe5406b…`) closed
`ANDROID_CLOSED_HEALTHY` with no physical action. The usbfs departure race
hit the census's initial inventory read, which v65 keeps strict, so one
`recover_approved_task` was needed
([run 6](docs/reports/S22PLUS_MAINLINE_MAX77705_ROUTE_TIMER_RUN6_2026-11-27.md)).

After that: router attach epochs (re-routing after an unplug) and the
failure-class runs of the evidence ladder.
[Plan](docs/plans/S22PLUS_MAINLINE_USB_ROUTER_AND_HANDSOFF_CYCLE_2026-11-26.md) ·
[Run](docs/reports/S22PLUS_MAINLINE_MAX77705_ROUTE_TIMER_RUN_2026-11-26.md) ·
[H0](docs/reports/S22PLUS_MAINLINE_MAX77705_ROUTE_TIMER_H0_2026-11-26.md) ·
[Policy](docs/operations/S22PLUS_MAINLINE_MAX77705_ROUTE_TIMER_V1.md)

### UFS module aligned with upstream tolerance (queued)

ML036–ML047 each stopped at one module guard. Every refusal with an upstream
counterpart was a condition that upstream `ufshcd`/`ufs-qcom` accepts without
checking. ML047's UIC_ERROR during DME_LINK_STARTUP is consistent with the
LINERESET that upstream and FYG8 expect and ignore. A second open explanation
is that CFG1 QUNIPRO_SEL never latched (written after lane clocks, bit 0
still clear on readback).
[Upstream-tolerance audit](docs/reports/S22PLUS_MAINLINE_UFS_UPSTREAM_TOLERANCE_AUDIT_H0_2026-11-19.md).

The operator selected V13: keep one link attempt; tolerate UIC_ERROR in
the link poll only; record the OR of all link-poll IS samples and, after
UIC_ERROR, the UIC error-code registers once; move QUNIPRO_SEL to the
upstream position. V13 is implemented and H0-verified, together with a
version envelope that lets later module versions be adopted through the
capability's version table without amending the root, details or target
(contract revision 81). The code and contract change passed independent
review (PASS_GO after four rounds). The V13 capability (PASS_GO), the
revision-81 terminal backend re-review (v51, PASS_GO), candidate
qualification and the exact task preparation are complete (H0).

**ML051 (first V13 run) closed `NO_PROOF` / `ANDROID_CLOSED_HEALTHY` without
testing V13:** the attach cue was issued too late by the assistant's
monitoring (refused by its own 60-second guard), no USB first response
arrived, automatic Download came at N+589.5 s and original A plus a
health-only continuation closed it. The capability is reusable; the next run
needs a fresh key-only candidate, current D0 and a new approval.
[ML051 run](docs/reports/S22PLUS_MAINLINE_ML051_V13_RUN_2026-11-19.md).

**ML052 (key-only reuse) also closed `NO_PROOF` / healthy before the module:**
the cued replug produced an authenticated USB response at W+75.7 s, but the
operator's attach resolution was recorded after the 120-second window, so
the owner stopped before the witness and permit.
[ML052 run](docs/reports/S22PLUS_MAINLINE_ML052_V13_RUN_2026-11-19.md).
[V13 H0](docs/reports/S22PLUS_MAINLINE_V13_UPSTREAM_LINK_H0_2026-11-19.md).

**UFS V13 without a replug: ML054 closed `PASS_MAINLINE_UFS_LINK` /
`ANDROID_CLOSED_HEALTHY` on 2026-11-27.** USB enumerated with no cue and no
physical action. One `DME_LINK_STARTUP` completed with result 0 and HCS
`0xf` (Device Present); the only UIC error code was PA `0x80000010`
(LINERESET indication), and CFG1 bit 0 still read clear. Authenticated
Download, one original-A transfer and final health followed with no host
recovery step. This is one boot and covers link startup only.
[ML054 run](docs/reports/S22PLUS_MAINLINE_ML054_UFS_ROUTE_RUN_2026-11-27.md).

Preparation: The operator chose UFS next
and set no-replug as the baseline. The operator-approved successor scope
S22PLUS_LATE_UFS_ROUTE_V1 composes V13 with the MAX77705 route write. It
uses the ML035 Image with only I2C GENI built in, the SE5 DT, the
byte-identical V13 module, and no attach cue. Code and contract were
adopted in v67 to v69 (`c9c1b15ecb`, `dc3aea26b4`, `886c1a4d04`). The
capability record and candidate passed owner review. The ML054 task
was `2db30bfb…`
([H0](docs/reports/S22PLUS_MAINLINE_UFS_ROUTE_H0_2026-11-27.md)).

Next (operator roadmap, 2026-11-27): first a shorter wait, then UFS
read/write and persistence across a reboot, then stability, then handover to
the upstream driver. For step 1, the operator approved a
[witness-floor variant](docs/operations/S22PLUS_MAINLINE_UFS_ROUTE_V1.md#witness-floor-variant).
It replaces the 300-second dwell with a guest BOOTTIME floor of 60 seconds.
Code, tests and contract text were adopted in v70 (`003b997d56`) after
review. **ML055 closed `NO_PROOF` / `ANDROID_CLOSED_HEALTHY`.** The floor
admitted the same-boot witness at 62.8 s and sent the permit. The session
took 230 s instead of ML054's 424 s. The fixed V13 module, however, has
its own 300-second boot-time floor and refused before any effect
(`load_errno` 110).
[ML055 run](docs/reports/S22PLUS_MAINLINE_ML055_UFS_FLOOR_RUN_2026-11-27.md).
The transport kernel's RPMh authority has the same 300-second floor. The
operator approved a floor kernel and module, rebuilt from renderings whose
only changes are those two floors, set to 60 seconds. They were adopted in
v71 (`276462cd0c`). In the disassembly, each binary changes only the
immediate `300e9−1` → `60e9−1`. Capability-4 and its candidate passed owner
review. **ML056 closed `PASS_MAINLINE_UFS_LINK` /
`ANDROID_CLOSED_HEALTHY`.** The module ran at 62.4 s of guest uptime, and
the link result matched ML054's in every field (result 0, HCS `0xf`). The
session took 202 s.
[ML056 run](docs/reports/S22PLUS_MAINLINE_ML056_UFS_BOOT_FLOOR_RUN_2026-11-27.md).
Step 1 is done. For step 2, read/write and persistence, the operator
approved the [design](docs/reports/S22PLUS_MAINLINE_UFS_RW_DESIGN_H0_2026-11-27.md).
Its target is one block in LU0's unallocated tail (LBA 62,305,152), reached
in phases. Phase 2a (read-only, report V14) was adopted in v72
(`b6e0d3bc59`) after 12 rounds of Codex review. It runs a fixed polled UTP
sequence on LU 0 after the link: NOP OUT, fDeviceInit, TEST UNIT READY,
READ CAPACITY(16), and reads of the GPT (LBAs 1–3) and the test block. It
issues no write opcode. **ML057 closed `PASS_MAINLINE_UFS_LINK` /
`ANDROID_CLOSED_HEALTHY`.** The link repeated ML056's. The storage stage
stopped safely at TEST UNIT READY: the device answered CHECK CONDITION, and the
stage refused the response on its extra-header (EHS) guard before any media
read.
[ML057 run](docs/reports/S22PLUS_MAINLINE_ML057_UFS_STORAGE_READ_RUN_2026-11-28.md).

### UFS link series (shared V2 capability, one link attempt each)

| Run | Module | Furthest point / first refusal | Report |
| --- | --- | --- | --- |
| ML029 | — | H0 wiring study; no device action | [H0](docs/reports/S22PLUS_MAINLINE_ML029_UFS_H0_2026-11-05.md) |
| ML033 | V1 | stage 0 `EBUSY`, USB-coverage admission | [run](docs/reports/S22PLUS_MAINLINE_ML033_RUN_2026-11-10.md) |
| ML034 | V1 | SH1 confirmation cache 0/0/0 (`BCM_VALUES`) | [run](docs/reports/S22PLUS_MAINLINE_ML034_RUN_2026-11-10.md) |
| ML035 | BCM fix | stage 2 `EBUSY`, predicate unobserved | [run](docs/reports/S22PLUS_MAINLINE_ML035_RUN_2026-11-10.md) |
| ML036 | v4 | stage 2 HCI quiescent: HCE nonzero | [run](docs/reports/S22PLUS_MAINLINE_ML036_RUN_2026-11-10.md) |
| ML039 | v5 | snapshot HCE `0x1`, HCS `0x10f`, IS `0x400` | [run](docs/reports/S22PLUS_MAINLINE_ML039_RUN_2026-11-10.md) |
| ML040 | v6 | handoff refused: reset CTL `0xb` | [run](docs/reports/S22PLUS_MAINLINE_ML040_RUN_2026-11-10.md) |
| ML042 | v7 | HCE stopped; HCS UCRDY `0x8` refused | [run](docs/reports/S22PLUS_MAINLINE_ML042_RUN_2026-11-11.md) |
| ML043 | v8 | IS `0x400` (stale UCCS) refused | [run](docs/reports/S22PLUS_MAINLINE_ML043_RUN_2026-11-11.md) |
| ML044 | v9 | UCCS acknowledged; stage 6 EIO before local commands | [run](docs/reports/S22PLUS_MAINLINE_ML044_RUN_2026-11-11.md) |
| ML045 | v10 | CFG1 `0x1c00052c` before/after, bit 0 clear | [run](docs/reports/S22PLUS_MAINLINE_ML045_RUN_2026-11-11.md) |
| ML046 | v11 | six local UniPro commands; link issued; EIO (word unrecorded) | [run](docs/reports/S22PLUS_MAINLINE_ML046_RUN_2026-11-11.md) |
| ML047 | v12 | link poll IS `0x00000004` (UIC_ERROR) | [run](docs/reports/S22PLUS_MAINLINE_ML047_RUN_2026-11-11.md) |
| ML051, ML052 | v13 | no USB first response in the window; module not reached | [ML051](docs/reports/S22PLUS_MAINLINE_ML051_V13_RUN_2026-11-19.md), [ML052](docs/reports/S22PLUS_MAINLINE_ML052_V13_RUN_2026-11-19.md) |
| ML054 | v13 + route | **link completed**: result 0, HCS `0xf` | [run](docs/reports/S22PLUS_MAINLINE_ML054_UFS_ROUTE_RUN_2026-11-27.md) |
| ML055 | v13 + route + 60 s floor | witness at 62.8 s; module refused (own 300 s floor, `ETIMEDOUT`), pre-effect | [run](docs/reports/S22PLUS_MAINLINE_ML055_UFS_FLOOR_RUN_2026-11-27.md) |
| ML056 | floor kernel/module + route + 60 s floor | **link completed at 62.4 s**: result 0, HCS `0xf` | [run](docs/reports/S22PLUS_MAINLINE_ML056_UFS_BOOT_FLOOR_RUN_2026-11-27.md) |
| ML057 | V14 storage module + floor kernel + route + 60 s floor | link = ML056; storage stopped at TUR (CHECK CONDITION refused on EHS guard, `-EPROTO`), no media read | [run](docs/reports/S22PLUS_MAINLINE_ML057_UFS_STORAGE_READ_RUN_2026-11-28.md) |

All closed `ANDROID_CLOSED_HEALTHY`. All through ML052 closed `NO_PROOF`;
ML054, ML056 and ML057 closed `PASS_MAINLINE_UFS_LINK`; ML055 closed `NO_PROOF`. The module source,
capability record and per-version scope are in
[the V2 capability](docs/operations/S22PLUS_MAINLINE_UFS_CAPABILITY_V2.md).

### USB first response depends on a physical replug

In every mainline run since ML021 where an authenticated USB response
arrived within the window, an attach cue had been issued and the operator
reconnected the cable. With no cue or a late cue, no USB endpoint appeared:
ML030, ML031, ML032, ML037, ML038, ML041, ML048 (cable deliberately
untouched for 120 s) and ML050 and ML051. ML032's endpoint appeared only later at
N+180 s. The cause is unproved. The UDC observation work (ML049 prepared,
ML050 run, then VM checks on 2026-11-12 and 2026-11-15) targets the
pre-connect UDC state; the physical bind/attach state remains unobserved.
[ML048](docs/reports/S22PLUS_MAINLINE_ML048_NO_REPLUG_RUN_2026-11-11.md) ·
[ML050](docs/reports/S22PLUS_MAINLINE_ML050_UDC_AUTO_RETURN_RUN_2026-11-11.md) ·
[ML050 retention](docs/reports/S22PLUS_MAINLINE_ML050_RETENTION_ANALYSIS_2026-11-12.md) ·
[VM pre-connect](docs/reports/S22PLUS_UDC_PRECONNECT_LIVE_RESPONSE_VM_2026-11-12.md) ·
[PC collector](docs/reports/S22PLUS_DEBIAN_UDC_HISTORY_PC_VM_2026-11-15.md)

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

The goal through ML026 is preserved byte-for-byte in
[the mainline RAM snapshot](docs/archive/roadmaps/GOAL_THROUGH_ML026_MAINLINE_RAM_2026-11-05.md),
and the goal through ML050 in
[the ML050 snapshot](docs/archive/roadmaps/GOAL_THROUGH_ML050_MAINLINE_UFS_2026-11-19.md).
They retain ML001–ML050 research/diagnostic history, exact report links,
proof limits, completed-unit summaries and the earlier vendor-route snapshots. Archival changes
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
