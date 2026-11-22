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

Per-run detail through ML050 is preserved byte-for-byte in
[the ML050 snapshot](docs/archive/roadmaps/GOAL_THROUGH_ML050_MAINLINE_UFS_2026-11-19.md);
each run's report remains the authoritative record. The
[2026-11-22 uniLoader LOGM control](docs/reports/S22PLUS_UNILOADER_LOGM_RUN_2026-11-22.md)
proved the loader's byte-for-byte readback and recovered one candidate frame
from the running vendor Android snapshot. Its original-A return closed healthy
after a health-only continuation. The latest mainline physical closure remains
ML050 (`ANDROID_CLOSED_HEALTHY`, 2026-11-11). ML049 was prepared and reviewed
but never executed. Every consumed run, grant and candidate stays consumed.

**Proven on mainline (RAM only):** uniLoader entry, PID1 and USB/NCM;
packaged Debian SysVinit as initial PID1; a fixed unprivileged same-boot SSH
command (ML026); authenticated normal Download return (ML027); rc2 start,
nonroot SSH and rc6 stop in one boot (ML028); the 300-second same-boot
witness; the V6+ automatic result-bound Download and original-A recovery.
**Not proven:** Linux UFS link, installed Debian, full SysV shutdown, a
general shell, stall recovery, residency or endurance.

### Selected unit: UFS module aligned with upstream tolerance (H0)

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

All closed `NO_PROOF` with `ANDROID_CLOSED_HEALTHY`. The module source,
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
