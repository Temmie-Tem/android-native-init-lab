# Project History

**English** · [한국어](PROJECT_HISTORY.ko.md)

> **This document is narrative, not evidence.**
>
> Nothing here grants device authority, and nothing here is the canonical record
> of any claim. The canonical record for each item is the linked report, plan, or
> campaign ledger; current state is defined by the binding target registry in
> `AGENTS.md` and by each `GOAL*.md`. **Where this document and a canonical
> record disagree, the canonical record wins.**
>
> Evidence terms (PROVED / observed / designed / unproved) are used exactly as
> defined in [`../devices/README.md`](../devices/README.md). Do not combine
> results from different runs into a new end-to-end success.

This document traces the repository from its first commit to the present, at the
granularity of eras. Its purpose is to record what opened and closed when — and
**why direction changed.**

- Span: 2025-11-13 to 2026-09-02
- Commits: 5,754
- Active days: 125 (including one five-month dormancy)
- Targets: Galaxy A90 5G → Galaxy S22+ → Galaxy S20+ 5G

Day-level detail belongs to `git log`, not to this file. Information that can be
regenerated is not frozen into documentation here.

---

## At a glance

| # | Era | Span | Commits | What it left behind |
| --- | --- | --- | ---: | --- |
| 1 | Seed and dormancy | 2025-11-13 – 2026-04-22 | 4 | Feasibility study only; then five months of silence |
| 2 | Reaching PID 1 | 2026-04-23 – 04-30 | 72 | Native `/init` as PID 1 on the day work resumed; module boundaries fixed |
| 3 | Becoming a console | 2026-05-02 – 05-08 | 114 | `0.9.0`–`0.9.59`: remote shell, app layer, long soak, hardening |
| 4 | Splitting the axes | 2026-05-09 – 05-18 | 136 | Flash axis separated from research axis; host harness and broker |
| 5 | The Wi-Fi campaign | 2026-05-19 – 06-06 | 1,754 | Native WLAN association, DHCP, IP traffic. The hardest stretch |
| 6 | Contract-based operation | 2026-06-07 – 06-13 | 319 | `AGENTS.md`, `GOAL.md`, `tests/`. The character of the work changes |
| 7 | The hardware stack | 2026-06-14 – 06-27 | 903 | Audio → video → input → direct GPU rendering |
| 8 | Kernel REPL and Debian | 2026-06-28 – 07-05 | 608 | Runtime kernel call proofs, self-flash, Debian PID 1 / SSH |
| 9 | A second device, a formal process | 2026-07-06 – 07-31 | 914 | S22+ rebuilt kernel boots; `/init` exec accepted; risk tiers formalized |
| 10 | Three devices and going public | 2026-08-01 – 09-02 | 930 | S20+ joins; OSS surface; deep USB frontier work |

---

## Era 1 — Seed and dormancy

**2025-11-13 – 2026-04-22 · 4 commits**

The repository was named `A90_5G_rooting` and had exactly one target, the Galaxy
A90 5G. Work consisted of a feasibility study and documentation of whether a
static `/init` could run on a vendor kernel (Phase 0). Then **no commits for
roughly five months.**

The gap is not a blemish to be smoothed over in the narrative; it is part of why
the project came back with a much clearer direction.

---

## Era 2 — Reaching PID 1

**2026-04-23 – 04-30 · 72 commits**

The founding assumption closed on the day work resumed. Stage 0 baseline capture
→ Stage 1 → Stage 2 → **Stage 3, where a native Linux `/init` entered as PID 1**
on the stock Samsung Linux 4.14.190 vendor kernel.

The project's identity changed the same week. The 04-25 commit
`Reframe project around native init userspace` redefined the goal from "rooting"
to **"a self-built native userspace on a vendor kernel."** The repository was not
actually renamed for another three months, but the turn happened here.

Established in this era:

- Serial console and host bridge, sysfs and input probes, and a blind menu driven
  by physical buttons alone with no display
- The `cmdv1` / `cmdv1x` framed shell protocol — the common channel for every
  host-side tool since
- HUD, KMS/draw, display calibration
- The `v80`–`v87` module split that fixed the **module boundaries still in use
  today**: `init_main` / `util`·`log`·`timeline`·`dev`·`storage` /
  `console`·`shell`·`cmdproto`·`run` /
  `metrics`·`kms`·`draw`·`hud`·`input`·`menu`

---

## Era 3 — Becoming a console

**2026-05-02 – 05-08 · 114 commits**

From the `0.9.0` (v100) remote shell prototype through `0.9.59` (v159) — **the
only period in which research cycles and actual flashes moved one-to-one.** With
the entry point secured, the work turned to making a console that could be
operated repeatedly.

- Service manager view, diagnostics bundles, app-layer split (about /
  displaytest / inputmonitor / cpustress)
- Static BusyBox 1.36.1 with a toybox fallback — while deliberately keeping the
  native PID 1 shell independent of BusyBox
- The long-soak layer: foundation → status → correlation → supervisor → host
  disconnect classifier, plus power and thermal trends
- Hardening batches 1–6 (`0.9.24`–`0.9.26`) in response to an external security
  review
- Kernel capability inventory; pstore, watchdog, and tracefs feasibility

The rules for the two version axes (actual flashes `0.9.x` versus research cycles
`vNNN`) live in
[`../operations/VERSIONING_POLICY.md`](../operations/VERSIONING_POLICY.md) and
[`VERSIONING.md`](VERSIONING.md). Per-version history is canonically recorded in
[`../../CHANGELOG.md`](../../CHANGELOG.md).

---

## Era 4 — Splitting the axes

**2026-05-09 – 05-18 · 136 commits**

After `v159` the **numeric version and the research cycle separated.** Real
flashes became rare while research cycles advanced independently. This is the
first point where the recognition that flashing is expensive and risky is
reflected in how the work is organized.

- `v160`–`v169` stability axis: NCM TCP, storage IO, process concurrency,
  scheduler latency, USB recovery
- `v170`–`v177` host harness: observer API, module runner, evidence bundle,
  long-run supervisor, safety gate
- `v185`–`v195` communication broker: protocol, backend, audit, auth hardening
- `v232`–`v241` attempts to reproduce Android linker, property, and namespace
  behaviour, ending in a map of linker early-abort call sites

That last item is the on-ramp to the next era: bringing up Wi-Fi would require
imitating parts of the Android runtime inside a native environment.

---

## Era 5 — The Wi-Fi campaign

**2026-05-19 – 06-06 · 1,754 commits (30% of the repository)**

The hardest stretch of the project. The Qualcomm WLAN stack is not a single
kernel driver but a set of components waiting on each other — CNSS ↔ QRTR ↔ WLFW
↔ ICNSS ↔ modem/eSoC ↔ PMIC — and all of it had to be reproduced by hand without
the Android framework.

Major waypoints:

- Private property namespace proof, execns private Binder devnodes, VNDK linker
  paths, VINTF Wi-Fi declaration collection
- Native Wi-Fi SELinux handoff proof, policy load, scan-only gate
- Modem subsystem hold/offlining, QRTR registration, service-manager ordering
- SSCTL boot proofs (`0.9.65`–`0.9.67`) and the qrtr-ns boot hook (**`0.9.68` /
  v724, 2026-05-24 — still the last image flashed to the A90**)
- Peripheral manager boundary tracing, per-proxy timing reduced from 2159 ms to
  800 ms, mdm_helper SELinux context repair, eSoC trigger routes
- PMIC pinctrl and GPIO reproduction, WLAN-PD DIAG sessions, the macloader gate

**Result (PROVED, run-scoped):** in separately journaled bounded experiments the
internal ICNSS/qcacld WLAN path reached association, DHCP, and IP traffic. Native
`wlan0` link-up and a minimal scan gate closed on 2026-06-05; connect and ping
validation were enabled on 06-06.

- Host analysis: [`../reports/WLAN0_ASSOCIATION_REGULATORY_HOST_ANALYSIS_2026-06-05.md`](../reports/WLAN0_ASSOCIATION_REGULATORY_HOST_ANALYSIS_2026-06-05.md)
- Baseline QA hold: [`../reports/NATIVE_INIT_WIFI_BASELINE_QA_HOLD_2026-06-06.md`](../reports/NATIVE_INIT_WIFI_BASELINE_QA_HOLD_2026-06-06.md)
- Later ownership evidence: [`../reports/A90_NATIVE_WIFI_OWNERSHIP_PERMANENCE_EVIDENCE_H0_2026-08-15.md`](../reports/A90_NATIVE_WIFI_OWNERSHIP_PERMANENCE_EVIDENCE_H0_2026-08-15.md)

The methodological lesson survives on the A90 device page: after a long detour
chasing the external SDX50M/eSoC/PCIe path, the real gate turned out to be the
**internal modem path**. That pattern — chase the wrong layer for a long time,
find the real gate, close it behind a safety checkpoint — repeats in every epic
that follows.

---

## Era 6 — Contract-based operation

**2026-06-07 – 06-13 · 319 commits**

Immediately after Wi-Fi closed, the workspace was reorganized, the transport
layer was made common, and Wi-Fi autoconnect and HUD surfaces were productized.
Then, **on 2026-06-12, the character of the project changed.**

`AGENTS.md`, `GOAL.md`, and `tests/` were all created that day. From this point:

- Work follows the cycle `STATE → SELECT → DESIGN → IMPLEMENT → STATIC VALIDATE
  → DEVICE → REPORT → COMMIT`
- Every claim carries an evidence grade (PROVED / observed / designed / unproved)
- Device work does not open without a binding target contract
- A large regression suite lands on 06-13, creating a host-only validation layer

The immediately preceding thread — classifying the limits of kernel observation
(V2191, BPF, JOPP/ROPP slide, kallsyms symbolization) — carries forward into
kernel-internals research.

**Every result after this point was produced under an evidence contract.** Read
earlier results with that difference in mind.

---

## Era 7 — The hardware stack

**2026-06-14 – 06-27 · 903 commits**

The era of waking dormant vendor hardware one subsystem at a time.

**USB gadget runtime control** — `usb status`, mass-storage expose/remove,
identity rodata patching, multi-LUN. v2321 was promoted as a rollback
checkpoint.
[`../reports/NATIVE_INIT_V2321_USB_CLEAN_IDENTITY_RODATA_LIVE_2026-06-14.md`](../reports/NATIVE_INIT_V2321_USB_CLEAN_IDENTITY_RODATA_LIVE_2026-06-14.md)

**Audio / ADSP** — the hardest problem of this era. It began with a tinyalsa
inventory and moved into reproducing ACDB (the audio calibration database).
Through the cal12 mem-handle blocker, reverse engineering a send-v5 deadlock, and
the AFE topology gate, a SET-cal capture and replay path was completed.

> **PROVED (run-scoped):** in a bounded live run the SM8150 audio card was
> materialized, the required calibration and routes were replayed, PCM
> write/drain was performed to the internal speaker, routes were cleaned up, and
> the device returned via the exact rollback path.
> [`../reports/NATIVE_INIT_V2814_AUDIO_CORE_PROMOTION_CANDIDATE_MARKER_LOSS_TOLERANT_LIVE_2026-06-19.md`](../reports/NATIVE_INIT_V2814_AUDIO_CORE_PROMOTION_CANDIDATE_MARKER_LOSS_TOLERANT_LIVE_2026-06-19.md)

**Video and input** — frame streaming, A/V sync, a compact stream format,
followed by a doomgeneric port, a serial-based input bridge, and DRM plane and
pageflip cadence tuning. This is the first point at which display, input, and
audio all run at once.

**GPU** — direct Adreno control. Through shader output, cache invalidation, and
clip guardband work, reaching triangle rendering on KMS, compute shaders, and 2D
textures.

**Kernel security track opens** — a PROCA/FIVE UAF candidate was recorded on
06-27 and empirically triggered at Tier-0 (non-fatal; the device survived).
Controllability of passive UAF reclaim closed as **NEGATIVE**.
[`../reports/KERNEL_SECURITY_TIER2_KASAN_LITE_RECLAIM_DUMP_2026-06-28.md`](../reports/KERNEL_SECURITY_TIER2_KASAN_LITE_RECLAIM_DUMP_2026-06-28.md)

---

## Era 8 — Kernel REPL and Debian

**2026-06-28 – 07-05 · 608 commits**

On 06-28 it was recorded that **a static kernel `.text` patch boots under RKP
(VIABLE)**, and the goal was re-chartered to a Tier-2 runtime kernel REPL. After
fixing ULEB128 root decoding in the kallsyms extractor, a system emerged for
calling kernel functions at runtime and proving their contracts (`filp_open`,
`kernel_read`, `memchr`, `kmemdup`, and many more).

This era records several operator corrections — "the blocker is a MAP mislabel,
not allocator ABI"; "the map audit is UNSOUND, do not rewrite the decoder off
it"; "a resident session must PACK the session, not target one symbol." The
practice of **leaving wrong directions in the record and reversing them** dates
from here.

In parallel, self-dd self-flashing acquired fail-closed guards and fault
injection tests and reached a live host self-flash pass.

The server-distro epic then opened:

- D0 Debian rootfs builder and host staging → **D1 chroot MVP** → **D2 SSH inside
  the chroot** → D4C userdata format and populate
- The WSTA series: Debian STA Wi-Fi, a packet filter control plane, an outbound
  tunnel, a seccomp loader, a durable HUD presenter, cold-boot persistence
- [`../reports/A90_PHASE3_DEBIAN_NETWORK_SSH_OWNERSHIP_H0_2026-08-03.md`](../reports/A90_PHASE3_DEBIAN_NETWORK_SSH_OWNERSHIP_H0_2026-08-03.md)

Debian PID 1 itself was confirmed later, at the end of July:
[`../reports/A90_V3404_D3_WORK_COPY_POSTMORTEM_DEBIAN_PID1_PROVEN_2026-07-31.md`](../reports/A90_V3404_D3_WORK_COPY_POSTMORTEM_DEBIAN_PID1_PROVEN_2026-07-31.md)

---

## Era 9 — A second device, a formal process

**2026-07-06 – 07-31 · 914 commits**

The **Galaxy S22+ (`SM-S906N`, FYG8)** joined on 07-06, to test whether the
methodology was device-independent. The start was not smooth: a recovery loop, a
disabled-vbmeta blocker, and a factory reset recovery.

**M series (securing a boot evidence channel)** — Magisk boot capture, pstore and
ramoops attempts, and then the host finding that *real persistence is Samsung
`sec_debug` (debug_level), not mainline ramoops*. EUD closed on a TZ gate
(rc:-22), and work pivoted to the DTS-exact QMP-PHY power substrate.

**O series (positive control)** — proving that stock ACM actually works first, so
that the observation apparatus itself is validated.
[`../reports/NATIVE_INIT_V3403_S22PLUS_O0_STOCK_USB_CONTROL_LIVE_2026-07-10.md`](../reports/NATIVE_INIT_V3403_S22PLUS_O0_STOCK_USB_CONTROL_LIVE_2026-07-10.md)

**R series (kernel rebuild)** — closing Full-LTO R1 and static R2, then:

> **PROVED:** a source-matched rebuilt kernel booted Android on the real device.
> [`../reports/S22PLUS_FYG8_R3C1_LIVE_RESULT_2026-07-12.md`](../reports/S22PLUS_FYG8_R3C1_LIVE_RESULT_2026-07-12.md)

> **PROVED:** a direct native candidate reached an `/init` exec that was accepted
> from the current PID 1 state.
> [`../reports/S22PLUS_FYG8_R4W1D_F1_LIVE_PASS_2026-07-21.md`](../reports/S22PLUS_FYG8_R4W1D_F1_LIVE_PASS_2026-07-21.md)

**The safety system was formalized in the same period.** On 07-21,
[`../operations/DEVICE_ACTION_RISK_TIERS.md`](../operations/DEVICE_ACTION_RISK_TIERS.md)
and
[`../operations/DEVICE_ACTION_PROCESS_V2.md`](../operations/DEVICE_ACTION_PROCESS_V2.md)
made the D0/D1/F1 risk tiers, the boot-only F1 procedure, and a reusable F1
adapter into a common layer. The resumable Odin transition core, one-shot live
policy, and the rule that a consumed candidate is permanently retired also date
from here.

On 07-19 the repository was renamed from `A90_5G_rooting` to
**`android-native-init-lab`** — the end of the single-device project.
[`../reports/REPOSITORY_RENAME_ANDROID_NATIVE_INIT_LAB_2026-07-19.md`](../reports/REPOSITORY_RENAME_ANDROID_NATIVE_INIT_LAB_2026-07-19.md)

The **P-series USB frontier** began on 07-24. An SSUSB timeout was recorded as
the frontier for the first time, and it remains the frontier today. UCSI race
analysis, the PMIC GLINK activation path, and kprobe-based electrical boundary
measurement all closed in this window.

Evidence index:
[`../reports/S22PLUS_FYG8_NATIVE_PID1_USERSPACE_EXPERIMENT_EVIDENCE_LEDGER_2026-07-22.md`](../reports/S22PLUS_FYG8_NATIVE_PID1_USERSPACE_EXPERIMENT_EVIDENCE_LEDGER_2026-07-22.md)

---

## Era 10 — Three devices and going public

**2026-08-01 – 2026-09-02 · 930 commits**

Three tracks running at once — the current structure.

### A90 — the self-built kernel track

Resident install and a reviewed D1 fast loop were activated, and switch_root was
proven repeatedly. On 08-10, **H15–H17 qualified a direct read-only UFS
handoff**, removing the previous multi-gigabyte SD work-copy dependency.

A devtmpfs exposure incident on 08-12 led to abandoning the earlier
shared-namespace design in favour of a smaller **isolated Debian** architecture:
[`../plans/A90_HEADLESS_NATIVE_WIFI_ISOLATED_DEBIAN_DESIGN_2026-08-14.md`](../plans/A90_HEADLESS_NATIVE_WIFI_ISOLATED_DEBIAN_DESIGN_2026-08-14.md)

The self-built kernel track advanced on 08-21–23: exact Snapdragon LLVM 10.0.7
was obtained, reproducing the unchanged CFP/JOPP/ROPP configuration; H34
identified an artifact inconsistency in which `rtic_mp` was missing while a stale
stock RTIC DTB was retained; and the public MPGen locator was repaired to reach a
deterministic reproduction.

- [`../reports/A90_EXACT_SNAPDRAGON_LLVM_1007_STOCK_REBUILD_H28_H0_2026-08-21.md`](../reports/A90_EXACT_SNAPDRAGON_LLVM_1007_STOCK_REBUILD_H28_H0_2026-08-21.md)
- [`../reports/A90_H34_RTIC_MP_STALE_DTB_HOST_CAUSAL_ANALYSIS_H0_2026-08-22.md`](../reports/A90_H34_RTIC_MP_STALE_DTB_HOST_CAUSAL_ANALYSIS_H0_2026-08-22.md)
- [`../reports/A90_RTIC_LOCATOR_REPAIRED_DETERMINISTIC_REBUILD_H0_2026-08-23.md`](../reports/A90_RTIC_LOCATOR_REPAIRED_DETERMINISTIC_REBUILD_H0_2026-08-23.md)

**This is PROVED host-side structural consistency, not a boot result.** The H35
package was reviewed as a bounded canary, but the live transaction failed before
the candidate write, so H35 is **unproved** and cannot be replayed:
[`../reports/A90_H35_NATIVE_RECOVERY_COMMAND_PREWRITE_FAILURE_2026-08-23.md`](../reports/A90_H35_NATIVE_RECOVERY_COMMAND_PREWRITE_FAILURE_2026-08-23.md)

### S22+ — deep work on the USB frontier

P3.xx continued. Two findings in this era moved the frontier.

**First, on 08-11 the suspicion shifted.** After the in-kernel path was refuted,
the Max77705 D+/D− mux became the candidate, and intensive work on 08-17–20
established: the mux is switched by modprobe; the bootloader writes COM_OPEN, so
the inheritance premise is refuted; the meaning of all five CONTROL1 values; RDX
bring-up is five calls and a failed MUIC probe is silent; NoAutoIBUS survives a
reboot.

**Second, on 08-21 a defect in the observation basis itself surfaced** — *the
vmlinux being audited did not belong to the Image that was actually flashed.* The
discipline that candidate runtime must be read from materialized sources comes
from here.

Current static closure and comprehensive audit:

- [`../reports/S22PLUS_FYG8_P319_SSUSB_UDC_PLAN_CLOSURE_H0_2026-08-24.md`](../reports/S22PLUS_FYG8_P319_SSUSB_UDC_PLAN_CLOSURE_H0_2026-08-24.md)
- [`../reports/S22PLUS_FYG8_USB_COMPREHENSIVE_INVESTIGATION_AUDIT_H0_2026-08-30.md`](../reports/S22PLUS_FYG8_USB_COMPREHENSIVE_INVESTIGATION_AUDIT_H0_2026-08-30.md)

On 08-29 a **proportional pre-F1 autonomy lane** was defined for the S22+ alone.
That authority does not transfer to any other target.

### S20+ — the third device

The **Galaxy S20+ 5G (`SM-G986N`)** joined on 08-12 as an isolated D0 onboarding
target. Unlike the A90 and S22+, it is the only device that started entirely
under the contract and risk-tier system.

- Exact onboarding: [`../reports/S20PLUS_G986N_ONBOARDING_D0_H0_2026-08-12.md`](../reports/S20PLUS_G986N_ONBOARDING_D0_H0_2026-08-12.md)
- Stock artifacts: [`../reports/S20PLUS_G986N_STOCK_ARTIFACT_ACQUISITION_H0_2026-08-13.md`](../reports/S20PLUS_G986N_STOCK_ARTIFACT_ACQUISITION_H0_2026-08-13.md)
- Phased design: [`../plans/S20PLUS_G986N_NATIVE_INIT_PHASED_DESIGN_2026-08-15.md`](../plans/S20PLUS_G986N_NATIVE_INIT_PHASED_DESIGN_2026-08-15.md)
- Native canary N1: [`../reports/S20PLUS_G986N_NATIVE_CANARY_N1_H0_2026-08-15.md`](../reports/S20PLUS_G986N_NATIVE_CANARY_N1_H0_2026-08-15.md)
- USB substrate: [`../reports/S20PLUS_G986N_NATIVE_USB_SUBSTRATE_H0_D0_2026-08-16.md`](../reports/S20PLUS_G986N_NATIVE_USB_SUBSTRATE_H0_D0_2026-08-16.md)
- N3-U0 (dormant): [`../reports/S20PLUS_G986N_N3U0_EVIDENCE_EXECUTION_INTEGRATION_H0_2026-08-20.md`](../reports/S20PLUS_G986N_N3U0_EVIDENCE_EXECUTION_INTEGRATION_H0_2026-08-20.md)
- Autonomous research infrastructure (inactive): [`../reports/S20PLUS_G986N_AUTONOMOUS_RESEARCH_SESSION_H0_2026-08-21.md`](../reports/S20PLUS_G986N_AUTONOMOUS_RESEARCH_SESSION_H0_2026-08-21.md)

A boot recovery canary F1 and a TWRP T2 recovery owner were activated on 08-31,
and TWRP boot identity D0 was proven on 09-01. **The N3-U0 ACM path and the
autonomous research infrastructure are host-qualified but deliberately not
activated.**

### Public surface

The OSS surface was settled on 08-07 — correcting the NOTICE third-party list and
shipping mkbootimg's license, adding `.github`, and establishing the public-tree
identifier sanitization policy. On 08-09 the host test suite baseline and its
failure taxonomy were recorded, and the Korean README was completed on 08-10.

---

## When each device joined

| Device | Joined | Repository state at the time |
| --- | --- | --- |
| Galaxy A90 5G (`SM-A908N`) | 2025-11-13 | The repository began as this device |
| Galaxy S22+ (`SM-S906N`) | 2026-07-06 | After the contract system, just before risk tiers were formalized |
| Galaxy S20+ 5G (`SM-G986N`) | 2026-08-12 | After contracts, risk tiers, and Process v2 were all in place |

The three devices do not pass authority to one another. A result on one device
never authorizes device work on another (`AGENTS.md`).

For per-device current state and frontiers, see
[`../devices/README.md`](../devices/README.md).

---

## What this document does not do

- **It does not state current status.** Current frontiers and next bounded units
  are defined by `GOAL.md` (S22+), `GOAL_A90.md`, and `GOAL_S20PLUS.md`.
- **It does not grant device authority.** No device work opens on the basis of
  this file. Only `AGENTS.md` and the selected binding target contract create
  authority.
- **It does not combine runs.** Each PROVED note above holds only within the
  scope of its own run.
- **It does not carry day-level history.** `git log` is canonical for that.

## Related documents

- [`../devices/README.md`](../devices/README.md) — per-device progress and the evidence taxonomy
- [`../../CHANGELOG.md`](../../CHANGELOG.md) — native init and boot image version history
- [`../operations/CAMPAIGN_LEDGER_A90.md`](../operations/CAMPAIGN_LEDGER_A90.md) ·
  [`../operations/CAMPAIGN_LEDGER_S22PLUS.md`](../operations/CAMPAIGN_LEDGER_S22PLUS.md) — run outcome ledgers
- [`VERSIONING.md`](VERSIONING.md) — version axis separation rules
- Superseded predecessors: [`../archive/overview/PROGRESS_LOG_2026-04-23_2026-05-02.md`](../archive/overview/PROGRESS_LOG_2026-04-23_2026-05-02.md) ·
  [`../archive/overview/PROJECT_STATUS_A90_THROUGH_2026-06-19.md`](../archive/overview/PROJECT_STATUS_A90_THROUGH_2026-06-19.md)
