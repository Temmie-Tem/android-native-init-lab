# S22+ FYG8 native PID1 and userspace experiment evidence ledger

Date: 2026-07-22 KST
Scope: S22+ experiments that constrain kernel rebuild, PID 1, early userspace,
retention, and USB/runtime bring-up
Status: H0 history and acquisition index; no device authority

## Later functional results (index update 2026-09-06)

The dated entries below retain their original evidence scope. For later bounded
read-only shell proof, see [P347](S22PLUS_FYG8_P347_OUTPUT_TIMING_PREPARED_2026-09-06.md)
and [P348](S22PLUS_FYG8_P348_RETAINED_SHELL_PREPARED_2026-09-06.md).
P348's last later witness was 390.137 seconds after lease opening, not an hour.
[P349](S22PLUS_FYG8_P349_RAM_WORKSPACE_PREPARED_2026-09-06.md) is host-qualified
but has no candidate transfer or live RAM/hour result; both approved attempts
aborted at host authentication. Current state is in [GOAL.md](../../GOAL.md),
and actual completed transfers remain in the [campaign ledger](../operations/CAMPAIGN_LEDGER_S22PLUS.md).

## Purpose and coverage

This ledger complements
`S22PLUS_FYG8_NATIVE_USERSPACE_BRINGUP_GAP_ANALYSIS_2026-07-22.md`.
The gap analysis explains the current causal model. This document records how
the relevant evidence was obtained, what each experiment actually returned,
and where its durable evidence can be reopened.

It covers result-bearing S22+ experiments and host audits that changed the
interpretation of those results. It does not enumerate every preparatory
commit, superseded policy activation, unrelated A90 experiment, or unrelated
S22+ subsystem probe. Historical action descriptions are evidence only and do
not authorize reuse.

## Evidence-strength rules

These distinctions are load-bearing:

| Observation | What it establishes | What it does not establish |
| --- | --- | --- |
| Odin transfer completed | The AP was parsed and its boot member was transferred in that session. | That the device selected or executed the transferred kernel/initramfs. |
| Odin endpoint departed | The Download transport disappeared. | Candidate boot readiness or code execution. |
| Operator saw a stable screen/no boot loop | The device remained visibly stable during the bounded window. | Kernel identity, PID 1 identity, or any source branch. |
| Android boot milestone and `uname`/identity | A candidate capable of returning Android reached the checked stock-userspace state. | Direct native PID 1 or native USB bring-up. |
| Exact run-bound marker in a complete retained stream | The marker's guarded producer path ran, subject to the exact static contract. | Any operation after the marker unless separately encoded. |
| Marker absence | The observer did not contain the marker. | Failure to execute, unless the channel and every earlier eligibility condition are independently proven. |
| `/proc/modules` membership | Module insertion/registration. | DT match, probe success, platform bind, interface publication, or function. |
| Driver/device bind symlink | The driver bound to the expected device. | UDC/gadget publication or end-to-end USB function. |
| `/sys/class/udc/<exact>` | The expected UDC surface exists. | Gadget binding, host enumeration, or framed traffic. |
| Exact ACM framed exchange | Device and host completed the bounded protocol over the selected tty. | General shell, NCM, or unrelated hardware readiness. |
| Final Android/root/hash health | Mandatory rollback restored the known baseline. | Candidate PASS. |

## Experiment chronology

### 1. Magisk boot semantic audit

**Method:** host-only unpack and byte comparison of stock and known-booting
Magisk boot images, exact cpio inventory, kernel delta analysis, and comparison
against pinned Magisk source.

**Observed:** Magisk replaced ramdisk `/init`, preserved the original init in
`.backup`, added its owned payloads, and made only the identified DEFEX and
PROCA kernel byte changes. Its expected early path restores and eventually
execs stock Android init.

**Established:** the healthy baseline includes `magiskinit`; a custom native
`/init` bypasses Magisk and cannot rely on its root daemon, policy patching,
mounts, service scripts, or Android handoff.

**Not established:** the exact runtime branch selected on every live boot.

**Evidence:**
`docs/reports/S22PLUS_FYG8_MAGISK_BOOT_SEMANTIC_AUDIT_2026-07-11.md` and
`workspace/private/outputs/s22plus_fyg8_magisk_boot_analysis_r0/`.

### 2. M1 rooted stock boot-time capture

**Method:** temporary Magisk `post-fs-data.d` and `service.d` capture scripts,
one normal Android reboot, root-owned bounded collection, cleanup, and final
health verification.

**Observed:** at 6.67 seconds uptime, 482 modules were already registered and
major USB, configfs, DRM, GPU, and display surfaces existed. At 8.81 seconds,
ADB and the stock USB property state were active.

**Established:** stock Android reaches a broad vendor hardware environment
before a Magisk post-fs-data observer can recover exact load chronology.
`modules.load`, `modules.dep`, and `modules.softdep` must supply the static
ordering baseline.

**Not established:** true first-stage insertion timing or which exact event
made each driver bind.

**Evidence:**
`docs/reports/S22PLUS_MAGISK_BOOT_TIME_CAPTURE_M1_LIVE_2026-07-07.md` and its
private run path recorded there.

### 3. M18 broad first-stage native candidate

**Method:** a freestanding native `/init` mounted minimal filesystems, emitted
a `/dev/kmsg` marker, loaded a large first-stage-derived module list plus USB
tail, attempted configfs ACM, and parked. Host observation looked for ACM; after
attended recovery, pstore and Samsung retained logs were collected.

**Observed:** no ACM or ADB, operator-observed loop/recovery behavior, no useful
M18 marker, and successful rollback. Host postmortem found unresolved hard
dependencies in the USB tail.

**Established:** that exact M18 artifact did not provide functional USB or an
internal phase. The retained channel used by M18 could not localize its stop.

**Not established:** failure of a dependency-complete stock-equivalent module
environment, failure of `/init`, or failure of any particular USB module.

**Evidence:**
`docs/reports/S22PLUS_M18_CAPTURE_POSTMORTEM_2026-07-08.md` and
`docs/reports/S22PLUS_SEC_DEBUG_M18_LIVE_RESULT_2026-07-08.md`.

### 4. O0 stock USB functional control

**Method:** under healthy rooted Android, temporarily stop the stock ttyGS0
owner, run a static device echo daemon, perform 128 CRC-framed host round trips
including one host tty reopen, then restore the stock owner. No flash or gadget
reconfiguration was involved.

**Observed:** all 128 requests completed with payload and sequence equality;
the stock service was restored and no USB re-enumeration occurred.

**Established:** host protocol, stock CDC ACM transport, tty ownership handoff,
and bounded request/response are sound.

**Not established:** native PID1 DWC3, configfs, UDC, or gadget bring-up.

**Evidence and implementation:**

- `docs/reports/NATIVE_INIT_V3403_S22PLUS_O0_STOCK_USB_CONTROL_LIVE_2026-07-10.md`
- `workspace/public/src/android/s22plus_o0_tty_echo.c`
- `workspace/public/src/scripts/revalidation/s22plus_o0_stock_usb_control.py`

### 5. O1.1 stock-first-stage boot service

**Method:** boot-only Magisk/Android candidate preserving the kernel and Magisk
entry path, add an exact early service with the corrected SELinux label, run
the same framed tty protocol, then perform mandatory Magisk rollback.

**Observed:** the early service ran, all 128 frames passed, stock tty ownership
was restored, the marker appeared in retained logs, and rollback health passed.

**Established:** the stock first-stage/module environment and Samsung gadget
can host a reliable early boot control service.

**Not established:** direct native PID1 USB bring-up.

**Evidence:**
`docs/reports/NATIVE_INIT_V3409_S22PLUS_O11_LIVE_PASS_2026-07-10.md`.

### 6. O3/O3F direct-PID1 ACM attempts

**Method:** direct native `/init` candidates attempted a statically audited
module plan, DWC3/configfs ACM setup, exact USB identity, and host framed
exchange. O3F removed glibc and extra process ownership to test a freestanding
startup shape. Continuous host udev and kernel-journal observers covered the
candidate window.

**Observed:** no candidate tty or USB add/bind event and no retained phase;
rollback returned healthy Android.

**Established:** O3F did not produce host-visible ACM, and a transient tty was
not merely missed by periodic polling.

**Not established:** whether direct PID1 reached the module plan, driver bind,
UDC, configfs, or any earlier source branch. Removing glibc did not resolve the
observable symptom.

**Evidence:**
`docs/reports/NATIVE_INIT_V3417_S22PLUS_O3F_FREESTANDING_ACM_LIVE_MISS_2026-07-10.md`
and `docs/module-map/s22plus-fyg8/subsystem-usb.md`.

### 7. V3428R stock retention positive control

**Method:** on stock/Magisk-origin PID 1, establish a clean baseline, write an
exact PRECHECK and FINAL pair to the live Samsung ring, perform attended
RDX/Download transition plus boot-only identity rollback, and collect the
first rollback boot's complete `/proc/last_kmsg` twice.

**Observed:** the exact ordered pair appeared once in the current ring and once
in both byte-identical retained reads.

**Established:** the Samsung current-ring to next-boot `/proc/last_kmsg`
transition can preserve exact run-bound records under the tested stock-origin
flow.

**Not established:** that a direct native candidate reaches the module-backed
writer or that absence in a direct candidate means non-execution.

**Evidence:**
`docs/reports/NATIVE_INIT_V3428R_S22PLUS_STOCK_TRANSITION_POSITIVE_CONTROL_LIVE_PASS_2026-07-10.md`.

### 8. V3429/V3430 direct-PID1 phase observer

**Method:** direct native `/init` attempted minimal filesystems, exact kernel
identity checks, loading/binding `sec_log_buf`, and run-bound retained records;
after the candidate window, rollback and two complete retained reads followed.

**Observed:** no marker. Host postmortem found the generated osrelease differed
from the real kernel release, causing a deterministic stop before the observer
module loaded.

**Established:** that artifact could not reach its Stage A observer as built.

**Not established:** whether `/init` itself executed. Its failure diagnostic
was emitted before the only planned retention observer existed.

**Evidence:**
`docs/reports/NATIVE_INIT_V3430_S22PLUS_V3429_PHASE_OBSERVER_LIVE_NO_PROOF_2026-07-10.md`.

### 9. V3432/V3433 corrected PID1 keystone

**Method:** remove the known osrelease mismatch, use a fresh exact direct-PID1
candidate, observe the bounded window, recover through Download, roll back, and
classify two complete retained reads.

**Observed:** custom-image warning and attended recovery, but zero marker,
malformed family, or raw token; final health passed.

**Established:** bootloader evidence was compatible with an unlocked allowed
custom boot, but the module-backed observer still did not separate PID1 entry
from pre-marker failure.

**Not established:** candidate kernel entry, `/init` exec, userspace entry, or
retention loss. This retired another blind module-backed witness attempt.

**Evidence:**
`docs/reports/NATIVE_INIT_V3433_S22PLUS_V3432_PID1_KEYSTONE_LIVE_NO_PROOF_2026-07-11.md`.

### 10. V3439 corrected ramoops positive control

**Method:** use the patched DTBO to prove a live bound ramoops backend and
`/dev/pmsg0`, write a run marker, trigger one attended sysrq panic, collect
pstore before rollback, then restore stock DTBO and boot.

**Observed:** backend and binding were proven, the operator saw the RDX panic,
but pstore contained zero records. Samsung `/proc/last_kmsg` retained panic
text without the run marker.

**Established:** backend activation alone does not make ramoops/pmsg survive
this S22+ reset path. Mainline pstore is not a reliable current witness here.

**Not established:** behavior under a materially different reset path. That
path is retired for the current ladder.

**Evidence:**
`docs/reports/NATIVE_INIT_V3439_S22PLUS_CORRECTED_RAMOOPS_LIVE_NO_PROOF_2026-07-11.md`.

### 11. R3C1 rebuilt-kernel Android viability

**Method:** construct a boot-only candidate containing the source-matched,
unpatched Full-LTO rebuilt kernel and stock-userspace carrier, boot to exact
Android milestones with kernel identity checks, then perform exact Magisk
rollback and health verification.

**Observed:** normal Android, exact FYG8 release/banner, stable samples, and
clean rollback.

**Established:** this source-matched rebuilt kernel can boot the FYG8 Android
userspace. Kernel rebuild is a viable project lever.

**Not established:** native PID 1, Debian, complete hardware stability, or
long-duration operation.

**Evidence and builder:**

- `docs/reports/S22PLUS_FYG8_R3C1_LIVE_RESULT_2026-07-12.md`
- `workspace/public/src/scripts/revalidation/build_s22plus_fyg8_r3c1_candidate.py`

### 12. R4W1-A Android-init retained witness

**Method:** boot a reviewed Android-capable candidate, reach stable Android,
obtain one canonical `adb exec-out bugreportz -s` stream, validate every ZIP
entry, classify the embedded complete `last_kmsg`, then roll back and verify
health.

**Observed:** exactly one run-bound marker in the complete bugreport stream and
retained log; no family/partial/foreign issue.

**Established:** the rebuilt candidate reached the guarded early Android PID1
path and the bugreport-stream acquisition preserved the marker exactly.

**Not established:** direct native `/init` or userspace instruction entry.

**Evidence and builder:**

- `docs/reports/S22PLUS_FYG8_R4W1A_A12_STREAM_CANDIDATE_LIVE_PASS_2026-07-13.md`
- `workspace/public/src/scripts/revalidation/build_s22plus_fyg8_r4w1a_candidate.py`

### 13. R4W1-B ring-crossing retained record

**Method:** use a 99-byte post-exec record appended at the Samsung ring cursor,
then recover and inspect retained output. The original R4W1-B helper completed
the candidate transfer but lost its post-candidate observer to endpoint-
transition handling and required a separately approved rollback. The later
first Process v2 canary transferred the same proof shape and rollback once,
then acquired two complete retained reads. A later H0 reproduction reconstructed
the exact carrier and modeled the circular-ring geometry.

**Observed:** exact 99-byte count zero, but one family record contained the
first 73 bytes; the final 26 bytes were replaced by following boot log data.
The operator reported one incomplete physical Download entry and extra boot in
the canary transition, so the prefix remained corroborative rather than an
accepted exact proof.

**Established:** the append-at-cursor design crossed the ring boundary and was
not an integrity-safe proof shape. It motivated contiguous pre-cursor
backfilling.

**Not established:** an exact accepted direct-PID1 proof, because the contract
required all 99 bytes.

**Evidence:**

- `docs/reports/S22PLUS_FYG8_R4W1D_CONTIGUOUS_PROOF_HOST_DESIGN_2026-07-21.md`
- `docs/reports/S22PLUS_FYG8_R4W1B_M4T2_CARRIER_HOST_REPRO_2026-07-14.md`
- `docs/reports/DEVICE_ACTION_PROCESS_V2_F1_CANARY_NO_PROOF_USBFS_DEPARTURE_CLOSE_2026-07-21.md`

### 14. R4W1-D compact direct-PID1 proof

**Method:** after successful `kernel_execve("/init")` on PID 1, write one exact
45-byte token as a contiguous range immediately behind a saturated Samsung
ring cursor without advancing the index. Process v2 transferred one boot-only
candidate, held the candidate, performed mandatory rollback, read
`/proc/last_kmsg` twice to EOF, and reopened the complete result/journal.

**Observed:** both retained reads were byte-identical and contained exactly one
complete marker with no foreign, partial, delimiter, or family issue. Final
health passed.

**Established:** the rebuilt kernel accepted the intended native `/init`
through `kernel_execve()` while current was PID 1. This closes the kernel-to-
userspace exec-acceptance boundary.

**Not established:** execution of the first userspace instruction, mounts,
child execution, module load, USB, or a control loop.

**Evidence and tooling:**

- `docs/reports/S22PLUS_FYG8_R4W1D_F1_LIVE_PASS_2026-07-21.md`
- `workspace/public/src/scripts/revalidation/build_s22plus_fyg8_r4w1d_candidate.py`
- `workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1d_candidate_static_checker.py`
- private Process v2 run recorded in the live report

### 15. R4W1-E E1 full checkpoint carrier

**Method:** expand the retained shape to an immutable entry plus A/B checkpoint
slots, add runtime OF/resource target gates, then run a static PID1 ladder for
mounts, one child, and five watchdog modules. Process v2 performed one exact
candidate and rollback transfer, followed by two retained reads.

**Observed:** no entry family or slot magic; final rollback health passed.

**Established:** transaction/recovery and strict absence classification worked.

**Not established:** whether the candidate reached post-exec, which new carrier
guard refused, whether userspace ran, or whether the 173-byte region was later
lost. Source agreement with the stock DT did not prove live OF translations.

**Evidence and tooling:**

- `docs/reports/S22PLUS_FYG8_R4W1E_E1_F1_LIVE_NO_PROOF_ROLLBACK_PASS_2026-07-22.md`
- `workspace/public/src/scripts/revalidation/build_s22plus_fyg8_r4w1e_e1_candidate.py`
- `workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1e_e1_candidate_static_checker.py`

### 16. R4W1-E0 minimal ENTRY versus USERSPACE discriminator

**Method:** remove the E1 OF/resource and 173-byte A/B-slot differences, reuse
the D-sized 45-byte retained slot, write ENTRY after accepted `/init` exec, and
allow PID 1 to replace it with USERSPACE after mounting proc and writing the
exact checkpoint request. Process v2 transferred candidate and rollback once,
then captured two complete retained reads.

**Observed:** zero ENTRY, USERSPACE, family, or partial bytes; reads were
byte-identical and rollback health passed.

**Established:** the E0 result is a stable no-proof observation, not a noisy or
partial classifier result.

**Not established:** candidate selection, post-exec hook reach, retained magic,
candidate-time index eligibility, first userspace instruction, or later loss.
The silent `seed_idx >= payload_size` gate remains the strongest technical
hypothesis, not a proven root cause.

**Evidence and tooling:**

- `docs/reports/S22PLUS_FYG8_R4W1E0_F1_LIVE_NO_PROOF_ROLLBACK_PASS_2026-07-22.md`
- `workspace/public/src/scripts/revalidation/build_s22plus_fyg8_r4w1e0_candidate.py`
- `workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1e0_candidate_static_checker.py`
- private Process v2 run recorded by `GOAL.md` and the live report

## Evidence acquisition methods

### A. Host-only boot artifact reconstruction

Use the checked candidate builders and static checkers rather than manual cpio
or tar edits. The current relevant tools are:

- `build_s22plus_fyg8_r4w1d_candidate.py`
- `build_s22plus_fyg8_r4w1e_e1_candidate.py`
- `build_s22plus_fyg8_r4w1e0_candidate.py`
- the matching `*_candidate_static_checker.py` files
- R4W1-D/E/E0 build, ELF, retained-layout, and artifact-contract helpers

They recover or check:

- boot header and partition geometry;
- exact kernel/Image identity;
- generic and vendor ramdisk ownership/order;
- exact cpio mode, owner, and content for `/init` and children;
- static ELF identity and absence of `PT_INTERP` where required;
- AP membership restricted to one regular `boot.img.lz4`;
- deterministic no-change repack and independent reproduction; and
- linked kernel control flow, marker count, config, module, and retained-layout
  contracts.

Generated boot images, APs, runtimes, and receipts remain under
`workspace/private/outputs/`; they are not tracked Git artifacts or live
authority.

### B. Stock connected read-only collection

A D0 stock collection can obtain bounded facts from healthy Android through
ADB and root without changing the candidate:

- `/proc/cmdline`, `/proc/bootconfig`, `/proc/version`, and `uname`;
- `/proc/modules` read to EOF;
- exact `/sys` driver/device bind links, UDC, USB role, configfs, block, and
  module surfaces;
- Android boot properties and service state;
- boot/supporting-partition readback identities where the target profile
  permits them; and
- current `/proc/ap_klog` or previous `/proc/last_kmsg` when exposed by the
  bound Samsung driver.

These facts describe the currently running stock boot only. They do not carry
automatically into a native candidate.

### C. Android-capable candidate evidence

When a candidate still reaches Android and ADB, the R4W1-A method can acquire a
canonical complete bugreport stream:

1. establish an exact clean marker baseline;
2. collect `adb exec-out bugreportz -s` to EOF from one fd;
3. hash the exact byte stream;
4. validate every ZIP member and CRC;
5. locate and classify the complete embedded retained log; and
6. prohibit a second collection from being treated as the same proof.

This method is unavailable once custom native PID 1 replaces Android and no
ADB service exists.

### D. Direct-native retained evidence

The current direct-native acquisition path is deferred until after mandatory
rollback:

1. perform the one authorized boot-only candidate transfer;
2. hold the candidate for the manifest-bounded interval;
3. enter/recover Download as required by the approved transaction;
4. transfer the exact boot-only Magisk rollback once;
5. on the first healthy stock boot, read `/proc/last_kmsg` twice to EOF through
   root without consuming or mutating it;
6. require exact size/hash equality between both reads; and
7. classify exact, family, partial, foreign, checksum, delimiter, and ordering
   states with the candidate-bound checker.

The Samsung driver snapshots the previous retained ring before installing its
new live writer. That makes the first rollback boot the key acquisition window.
The current E0 gap is that this snapshot does not expose the candidate-time
retained header or the reason the candidate hook refused.

### E. Process v2 transaction evidence

Current F1 runs produce private artifacts such as:

- `prepared.json`: exact target, candidate, rollback, manifest, and preflight;
- `candidate-attempt-01.start/result.json` plus Odin stdout/stderr;
- `rollback-attempt-01.start/result.json` plus Odin stdout/stderr;
- `rollback-observer-1.bin` and `rollback-observer-2.bin`;
- `live-state.json`: candidate/rollback classifications and final health;
- `live-result.json`: verdict, journal, timeline, and approval binding; and
- target-private continuity data.

The strict result validator reopens these instead of trusting console output.
The eight timeline events record transaction order only. In the current runner,
the `candidate_boot_ready` name and `proof` field must not be interpreted as
execution proof when they were derived only from transfer completion and Odin
endpoint departure.

Canonical runner:
`workspace/public/src/scripts/revalidation/device_action_f1_live_v2.py`.

### F. USB evidence

Use three independent layers:

1. continuous udev/kernel/USBFS observation for add, remove, replace, bind, and
   tty events;
2. device-side exact bind bundle: module registration, platform match/probe,
   DWC3 bind, UDC identity, gadget state, and tty identity; and
3. one exact framed host/device exchange with sequence, payload, and CRC.

Host enumeration alone is insufficient. Device bind state without host bytes
is also insufficient for the final control proof.

### G. Module and hardware evidence

Static selection starts from exact vendor `modules.load`, `modules.dep`,
`modules.softdep`, aliases, options, and blocklist. Runtime promotion follows:

`artifact -> dependencies/order -> finit_module -> /proc/modules -> DT match ->
probe/bind -> surface -> bounded function`

Regulators, clocks, interconnects, IOMMUs, firmware, and deferred probes cannot
be inferred from depmod alone. Record the first failed gate and stop causal
interpretation there.

### H. Operator and bootloader observations

Panel state, warning screens, loops, RDX screens, and physical Download entry
are useful corroboration and recovery evidence. ABL/XBL text in retained logs
can show unlocked verification policy and exit from boot services. Neither
sensory observation nor ABL continuation identifies the exact candidate Image
without a candidate-bound witness.

## Durable evidence locations

- **Tracked interpretation:** `GOAL.md`, this ledger, result reports, designs,
  module maps, and operation contracts under `docs/`.
- **Tracked implementation:** builders, checkers, runtime source, adapters, and
  tests under `workspace/public/src/` and `tests/`.
- **Private build outputs:** `workspace/private/outputs/`.
- **Private live runs:** `workspace/private/runs/`, including Process v2 runs
  under `workspace/private/runs/device-action-f1-live-v2/`.
- **Private inputs:** source firmware, boot images, ramdisks, and recovered
  kernel source under `workspace/private/inputs/` and `workspace/private/work/`.

Raw device logs, images, target identifiers, and credentials stay private.
Tracked reports should contain only the minimum derived facts needed to audit
the conclusion.

## Evidence currently unavailable

The repository currently has no accepted evidence for:

- exact candidate Image identity after E0 boot selection;
- E0 candidate-time Samsung retained `magic`, `idx`, or refusal branch;
- execution of E0's first userspace instruction;
- direct-PID1 module bind or UDC publication;
- direct-PID1 host ACM bytes;
- a reliable S22+ pstore/ramoops current-run record; or
- UART/EUD trace of the kernel-to-userspace transition.

These absences define the next observation design. They are not invitations to
repeat retired candidates.

## Next acquisition contract

Before another F1 candidate, an H0 design must make the following outcomes
separable:

1. intended candidate selected versus another boot path;
2. retained header valid versus invalid;
3. index eligible versus rejected;
4. ENTRY store attempted and verified versus not attempted; and
5. userspace checkpoint accepted versus never reached.

It must also correct the runner's endpoint-departure naming. It must not add
Debian, broader module loading, USB gadget setup, storage writes, panic/RDX, or
a new general framework merely to compensate for the missing discriminator.

## Safety and reuse boundary

This document is an acquisition map, not an execution recipe or approval.
Every historical candidate and acknowledgement is consumed or retired. Any
future connected work uses the current `AGENTS.md` tiers. Any F1 run requires a
new host-qualified candidate, D0 preparation, fresh exact approval, one
boot-only candidate transfer, mandatory exact rollback, and final health under
Process v2.
