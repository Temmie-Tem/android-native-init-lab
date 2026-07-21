# S22+ FYG8 native userspace bring-up gap analysis

Date: 2026-07-22 KST
Scope: H0 host-only source, artifact, report, and public-document review
Status: investigation checkpoint; no build, device access, image generation, or
live authority

## Executive verdict

The current no-proof result is not explained by a missing Android userspace
service. R4W1-D already proved that the FYG8 rebuilt kernel accepted the custom
ramdisk `/init` through `kernel_execve()` while the current task was PID 1.
R4W1-E0 replaced that `/init` with a static AArch64 executable whose first
observable operation requires only PID 1, a procfs mount, and the already
registered kernel checkpoint node. Android property service, `ueventd`, the
dynamic linker, SELinux second stage, `/system`, Debian, USB, and networking
are downstream of that boundary.

R4W1-E0 nevertheless retained neither its kernel ENTRY record nor its
userspace record. The strongest source-backed explanation is a silent refusal
inside the retained-log ENTRY gate, especially its requirement that the
Samsung ring index already be at least one complete payload. The post-rollback
`/proc/last_kmsg` size does not reveal the candidate-time header or index, and
the gate records no refusal reason. This is a hypothesis, not a proof.

Chronology matters here. R4W1-E E1 first transferred a candidate carrying one
173-byte contiguous retained region and closed without proof. R4W1-E0 was then
built as a separate 45-byte redesign and later also completed one candidate
transfer plus rollback, again without proof. E0 was host-only only during its
earlier design/build checkpoint; that state was superseded by its live close.

Exact candidate selection and execution also remain unproven. The bootloader
trace is consistent with an unlocked boot continuing into a kernel, but it
does not bind that boot to the candidate Image hash. The current evidence
therefore cannot distinguish these cases:

1. the intended candidate did not become the executing kernel/initramfs;
2. it executed but the retained header/index gate refused ENTRY; or
3. ENTRY was written but was not exposed by the next stock retained-log
   snapshot.

The next unit should improve this discriminator. Adding more Android or Debian
userspace is not a useful response to the E0 result.

## Evidence classes

This report uses the following labels:

- `CONFIRMED`: directly established by local source, static artifact checks,
  or accepted live evidence;
- `RULED OUT`: incompatible with the currently inspected source/artifacts;
- `WEAKENED`: still possible, but contradicted by a stronger differential;
- `OPEN`: not separated by the available evidence;
- `FUTURE GAP`: required for a useful native runtime but not for the E0 entry
  proof.

## Reconstructed boot and userspace path

### 1. Boot image assembly and ramdisk precedence

The FYG8 candidate is an Android boot-header-v4 boot image. Its `boot`
partition supplies the kernel and generic ramdisk. `vendor_boot` supplies the
device-specific ramdisk fragments, DTB, fstab, and vendor modules. Android's
documented ordering loads the selected vendor ramdisks and then the generic
ramdisk, so the generic ramdisk overlays earlier content.

Local unpack checks found:

- the E0 generic ramdisk contains the exact audited static `/init` and child;
- the vendor ramdisk contains `/first_stage_ramdisk/fstab.qcom` and
  `/lib/modules`, but no competing `/init`;
- the final repacked image unpacks back to the expected kernel, `/init`, and
  child; and
- the no-change pack path was byte-identical before candidate construction.

Conclusion: vendor-ramdisk ordering overwriting the E0 `/init` is `RULED OUT`.

Primary references:

- [AOSP boot image header](https://source.android.com/docs/core/architecture/bootloader/boot-image-header)
- [AOSP generic boot partition](https://source.android.com/docs/core/architecture/partitions/generic-boot)
- [AOSP vendor boot partitions](https://source.android.com/docs/core/architecture/partitions/vendor-boot-partitions)

### 2. Kernel initialization before `/init`

The local Android common-kernel path performs built-in initcalls before trying
the ramdisk init. The E0 checkpoint proc node is registered with
`late_initcall`, so successful kernel initialization creates it before
`kernel_init()` invokes `/init`. The E0 hook records ENTRY only after
`run_init_process()` returns success for `/init` while the current task is
PID 1.

This means the E0 ENTRY boundary is:

`kernel initcalls -> proc checkpoint registration -> kernel_execve(/init)
accepted -> retained ENTRY attempt -> first userspace instruction`

R4W1-D proved the same kernel-to-userspace exec boundary with its compact
retained marker. It did not prove that a userspace instruction executed. E0
was intended to add that missing distinction.

Primary references:

- [Android common kernel init/main.c](https://android.googlesource.com/kernel/common/+/refs/heads/android-mainline/init/main.c)
- [Linux initramfs and PID 1](https://www.kernel.org/doc/html/latest/filesystems/ramfs-rootfs-initramfs.html)
- [Linux early userspace responsibilities](https://docs.kernel.org/driver-api/early-userspace/early_userspace_support.html)

### 3. E0 native `/init`

The exact E0 runtime is a static AArch64 ELF with no `PT_INTERP`. Its entry
sequence is deliberately smaller than Android first-stage init:

1. verify `getpid() == 1`;
2. initialize the fixed checkpoint request;
3. mount and verify procfs;
4. write the first checkpoint to `/proc/s22_checkpoint`;
5. only then continue with sysfs, tmpfs `/dev`, tmpfs `/run`, `/dev/null`, the
   exact static child, and the watchdog-module closure.

Therefore a missing dynamic linker, property service, `ueventd`, `/system`,
firmware, USB, or Debian rootfs cannot explain the absence of both E0 records.
Even a failure after the first checkpoint would leave the earlier ENTRY record
unless the retained carrier itself was refused, overwritten, or lost.

### 4. What stock Android normally does instead

Android's first-stage init performs substantially more work because it must
bring up Android, not merely execute one static PID-1 program. The Android 12
path mounts early filesystems and device nodes, performs first-stage mounts,
loads or coordinates required modules, and execs `/system/bin/init
selinux_setup`. SELinux policy setup then re-execs init for second stage, where
property services, rc parsing, service startup, and the broader Android
userspace continue. `ueventd` handles coldboot device events, node ownership
and permissions, symlinks, and firmware requests.

Those responsibilities are real `FUTURE GAP`s for a durable native system,
but they are not prerequisites for E0's `_start` or first proc write.

Primary references:

- [AOSP Android 15 first_stage_init.cpp](https://android.googlesource.com/platform/system/core/+/refs/heads/android15-release/init/first_stage_init.cpp)
- [AOSP Android 15 second-stage init.cpp](https://android.googlesource.com/platform/system/core/+/refs/heads/android15-release/init/init.cpp)
- [AOSP ueventd implementation](https://android.googlesource.com/platform/system/core/+/refs/heads/android12-qpr3-s2-release/init/ueventd.cpp)

### 5. Magisk is part of the healthy Android path, not the native path

The known healthy FYG8 baseline does not execute stock Android init directly.
Its ramdisk `/init` is the pinned Magisk `magiskinit`. Host analysis established
that Magisk preserves the original init under `.backup`, restores it during
early boot, prepares its overlays and SELinux changes, and then execs the
original Android init path.

The E0 ramdisk instead places the audited native binary at `/init`. Remaining
Magisk-owned ramdisk entries are inert unless that Magisk entry program runs.
Therefore native PID 1 does not receive Magisk's mounts, policy patching,
modules, root daemon, property integration, ADB setup, or handoff to stock
Android. This is intentional and confirms two interpretation rules:

- absence of Magisk/ADB under native PID 1 is expected, not evidence that the
  first native instruction failed; and
- every early service the project needs must be supplied by the native
  runtime or by a deliberate later rootfs handoff.

Local reference:
`docs/reports/S22PLUS_FYG8_MAGISK_BOOT_SEMANTIC_AUDIT_2026-07-11.md`.

## Retained carrier analysis

### Driver behavior

The source-matched Samsung `sec_log_buf` driver behaves as follows:

1. map the retained region;
2. if the magic is invalid, replace the magic and reset `idx`/`prev_idx`;
3. copy the previous retained ring into the `/proc/last_kmsg` snapshot;
4. create `/proc/last_kmsg`;
5. pull the current kernel's early log; and
6. install the live Samsung log writer.

When `idx` is larger than the payload, the snapshot rotates the full ring from
`idx % payload_size`. When `idx` is not larger than the payload, it copies only
`idx` bytes from the start.

The native candidate intentionally does not load `sec_log_buf.ko`, so the E0
kernel accesses the retained layout directly and the next stock boot exposes
the previous contents.

### E0 gate behavior

The E0 kernel hook refuses silently unless all of these are true:

- the attempted init path is exactly `/init`;
- the current task is PID 1;
- retained magic is exact; and
- `seed_idx >= payload_size`.

Only after those checks does it write the 45-byte ENTRY immediately behind the
ring cursor and remember the header values. The proc callback later requires
the same magic, index, boot count, and ENTRY bytes before replacing ENTRY with
USERSPACE.

The `seed_idx >= payload_size` rule is stronger than the Samsung snapshot code
requires for every visible backfill. In the unsaturated case, an index of at
least the proof size can still include a backfill at `idx - proof_size` in the
next snapshot. The current rule was inherited from the successful D geometry,
but E0 did not record whether it rejected a smaller candidate-time index.

This does not establish that the index was small. It establishes that the
current all-zero result cannot distinguish a gate refusal from no execution.

### D versus E0 differential

The accepted D run placed its compact marker in a bootloader-log boundary and
the next stock snapshot retained it. At the analogous boundary in the E0
snapshot, the original bootloader text remained intact. Both candidate traces
otherwise show the unlocked/allowed boot flow continuing through boot-services
exit.

This differential makes later random overwrite of exactly the E0 slot less
likely and makes an absent/refused write more likely. It does not prove the
candidate Image was selected, because the bootloader trace contains no
candidate hash or build identity.

## Hypothesis ledger

| Hypothesis | State | Reason |
| --- | --- | --- |
| Android property service or second-stage init was required before E0 `_start` | `RULED OUT` | E0 is static and enters directly as PID 1; the first proof needs only procfs and the built-in checkpoint node. |
| A dynamic linker or Android shared library was missing | `RULED OUT` | Final `/init` has no `PT_INTERP` and uses raw syscalls. |
| Vendor ramdisk content replaced the custom `/init` | `RULED OUT` | Final unpack contains the exact generic-ramdisk `/init`; vendor ramdisk has no competing `/init`, and documented ordering favors the generic ramdisk overlay. |
| The final AP lacked the expected kernel/init/child | `RULED OUT` statically | Independent unpack, identity, ELF, and archive checks passed. This does not prove the device selected it. |
| ABL categorically rejected the custom boot image | `WEAKENED` | The retained boot trace shows the unlocked allow path and exit from boot services, but does not bind execution to the candidate hash. |
| The candidate was not selected or did not reach the E0 post-exec hook | `OPEN` | No independent candidate identity witness exists. |
| Retained magic was invalid at the candidate hook | `OPEN` | The driver can reset invalid magic on stock boot; candidate-time magic was not captured. |
| Candidate-time index was below one payload and E0 silently refused | `OPEN`, strongest current technical hypothesis | E0 requires full saturation, while the driver can expose unsaturated bytes; no refusal telemetry exists. |
| E0 wrote ENTRY and it was later lost or hidden | `OPEN`, lower probability | Physically possible, but the analogous E0 bootloader text remained intact where D visibly overlaid its marker. |
| `_start` ran but procfs mount or proc write failed | `OPEN` for USERSPACE only | This could suppress USERSPACE, but cannot explain missing ENTRY if the post-exec hook stored it successfully. |
| Missing module, firmware, USB, or storage setup caused the E0 zero result | `RULED OUT` for E0; `FUTURE GAP` afterward | These operations occur after the first checkpoint or belong to later rungs. |
| The existing runtime is already sufficient for Debian/server operation | `RULED OUT` | It is an evidence runtime that parks after a bounded ladder; it has no root handoff, general device manager, service lifecycle, or persistent control plane. |

## Process and observation defect found

The reusable F1 runner's candidate observer explicitly returns
`candidate_execution_proven: false`; it only measures Odin endpoint departure
and waits for the bounded observation interval. The same path then emits a
timeline event named `candidate_boot_ready` with `proof: true` when the
candidate transfer completed and the Odin endpoint disappeared.

That flag is not an execution proof. It did not incorrectly turn E0 into PASS,
because the retained classifier remained fail-closed, but its name and payload
are semantically misleading. Future analysis must treat it only as
`candidate_transfer_completed_and_odin_departed` until an independent boot
witness exists.

## Gaps before another E0-class live run

These are immediate diagnostic gaps, ordered by value:

1. **Independent candidate identity.** Add a bounded observation that proves
   which candidate kernel/initramfs became active without relying on the same
   retained slot used for userspace progress.
2. **Retained-gate telemetry.** Distinguish bad magic, insufficient index,
   successful ENTRY store, and later visibility loss. The current silent
   returns collapse all four into zero records.
3. **Reassess saturation as a requirement.** Prove the safe visible geometry
   against both saturated and unsaturated Samsung snapshot behavior. Any code
   change remains a new kernel/checker review unit; this report does not
   authorize it.
4. **Correct runner semantics.** Endpoint departure is transport state, not
   `candidate_boot_ready` proof.
5. **Keep channels independent.** ENTRY and USERSPACE currently share one
   physical retained carrier and one eligibility gate. A single refusal makes
   both disappear and defeats the intended two-state diagnosis.

The 73-byte prefix observed in R4W1-B is not a retained-window size limit. It
was the first fragment of a 99-byte append that crossed the circular payload
boundary. R4W1-D, E, and E0 instead use checked contiguous pre-cursor placement;
E's 173-byte contract already rejects a region larger than the full payload and
rejects a truncated observer region. A generic `<=73` candidate gate would
therefore encode the wrong model and is not part of the next design.

Do not retry the byte-identical E0 candidate. Its binding is consumed and the
observation ambiguity is now known.

## Historical-document conflicts and supersession

Several older documents remain useful evidence but are not current execution
designs:

1. `NATIVE_INIT_V3434_S22PLUS_BOOT_BOUNDARY_STATIC_MAP_HOST_PASS_2026-07-11.md`
   selected stock Android init as global PID 1 because direct PID 1 lacked a
   pre-userspace witness. R4W1-D later supplied the missing exec-acceptance
   witness. Its kernel/config map remains useful; its architecture selection is
   no longer binding for the current direct-PID1 objective.
2. `NATIVE_INIT_SERVER_DISTRO_ENDGAME_DESIGN_2026-06-30.md` is primarily an
   A90 design. Its claim that Stage 0 hardware glue was already complete does
   not transfer to S22+, and its historical `userdata` reformat allowance is
   forbidden by the current `AGENTS.md`. It can inform future rootfs handoff
   mechanics but grants no current storage action.
3. `S22PLUS_NATIVE_INIT_M18_FULL_FIRSTSTAGE_SUBSTRATE_STEER_2026-07-08.md`
   described M18 as a complete first-stage substrate. The later M18 postmortem
   found unresolved hard dependencies in its USB tail. Use the postmortem, not
   the earlier steer, for causal interpretation.
4. Archived one-shot live gates, acknowledgement strings, and reports cannot
   authorize another candidate under Process v2. The E0 binding is consumed.

These conflicts do not invalidate their captured facts. They limit which
conclusions and policies can be carried forward.

## Future native-runtime responsibility map

Once candidate identity and the first userspace instruction are independently
observable, the existing E1 through E4 ladder remains directionally correct.
The following work is needed later, but should not be pulled into the next
diagnostic candidate.

### Current kernel capability snapshot

The source-matched pre-R4W1-D configuration confirms that the basic evidence
runtime is not missing its fundamental executable or virtual-filesystem
support:

| Capability | FYG8 state | Consequence |
| --- | --- | --- |
| ELF execution and initramfs | `CONFIG_BINFMT_ELF=y`, `CONFIG_BLK_DEV_INITRD=y` | Static `/init` and child execution are supported. |
| procfs, sysfs, tmpfs | enabled | The E1 mount sequence has kernel backing. |
| Loadable modules | `CONFIG_MODULES=y` | An exact in-process `finit_module` ladder is possible. |
| Firmware loader | enabled | Direct filesystem lookup is available. User-helper support is built, but forced fallback is disabled, so exact driver call paths still matter. |
| SELinux | `CONFIG_SECURITY_SELINUX=y` | Native PID 1 must eventually choose and validate a policy-loading posture. |
| devtmpfs | disabled | Device nodes must initially be created from a bounded table/sysfs-derived identities or by a userspace device manager. |
| PID/user namespaces | disabled | Not a blocker for basic PID 1 or ordinary Debian processes; a constraint for containers and some isolation designs. |
| cgroup PID controller and SysV IPC | disabled | Not an E0 blocker; relevant to later service-manager and workload compatibility decisions. |

### PID 1 and process lifecycle

- install deliberate signal handling;
- reap all children and adopted orphans continuously;
- define fatal-child, shutdown, reboot, and recovery behavior;
- never return from PID 1; and
- retain bounded progress/error reporting independent of the control channel.

### Early filesystems and device nodes

- mount and verify procfs, sysfs, tmpfs `/dev`, tmpfs `/run`, `/dev/pts`, and
  only the additional virtual filesystems actually required;
- create essential nodes manually because the current FYG8 baseline has
  `CONFIG_DEVTMPFS=n`; and
- add a narrow uevent coldboot/device-node manager or deliberately adopt a
  proven userspace implementation before broad hardware bring-up.

Modern systemd documents `CONFIG_DEVTMPFS` as a requirement. With the current
kernel, a small custom supervisor, SysV-style init, or OpenRC-like path is a
better first rootfs handoff target than making systemd the stage-0 dependency.
Enabling devtmpfs is a separate kernel decision, not an E0 fix.

Primary reference:
[systemd build and kernel requirements](https://github.com/systemd/systemd/blob/main/README).

### Modules, probe completion, and firmware

- resolve exact FYG8 dependency and soft-dependency order from shipped module
  metadata;
- distinguish module registration from platform-driver bind and deferred
  probe completion;
- mount the filesystem containing exact vendor firmware before drivers request
  it, or implement the required bounded firmware fallback handler; and
- checkpoint each subsystem at registration, bind, and published-interface
  boundaries.

The kernel firmware API can first perform direct filesystem lookup and may
fall back to a userspace-mediated sysfs request depending on config and call
type. Android `ueventd` normally participates in that workflow. A bare PID 1
must replace the needed portion explicitly.

Primary reference:
[Linux request_firmware API](https://docs.kernel.org/driver-api/firmware/request_firmware.html).

### FYG8 stock bring-up scale and historical evidence

The FYG8 vendor ramdisk supplies a first-stage `modules.load` with 140 source
entries plus `modules.dep`, `modules.softdep`, aliases, and a blocklist. A
rooted stock capture at 6.67 seconds uptime already found 482 registered
modules and working USB/configfs, DRM, GPU, and display surfaces. That capture
was too late to reconstruct exact live insertion order, but it establishes the
scale of the Android-provided environment.

Earlier native experiments also establish what not to infer:

- a historical 141-module M18 candidate neither exposed USB nor retained a
  useful internal phase;
- its postmortem found the selected USB tail still had unresolved hard
  dependency edges; and
- therefore that run did not prove that a dependency-complete stock-equivalent
  module environment fails under native PID 1.

The current E1 five-module list is intentionally only a watchdog/survival
closure. It must not be treated as a general hardware bring-up set. Later
subsystems should use the stock metadata as the static starting point, then
advance through the repository's runtime gates:

`artifact -> dependency/order -> insertion -> registration -> DT match ->
probe/bind -> surface -> bounded function`

Do not load all 482 modules blindly. The curated module map still lists
display, GPU, audio, storage, networking, and power as incomplete subsystem
maps, and depmod metadata alone cannot establish regulators, clocks,
interconnects, IOMMUs, firmware, or deferred-probe completion.

Local references:

- `docs/reports/S22PLUS_MAGISK_BOOT_TIME_CAPTURE_M1_LIVE_2026-07-07.md`
- `docs/reports/S22PLUS_M18_CAPTURE_POSTMORTEM_2026-07-08.md`
- `docs/module-map/s22plus-fyg8/runtime-gates.md`
- `docs/module-map/s22plus-fyg8/known-gaps.md`

### Security posture

The FYG8 baseline enables SELinux. Android first stage normally loads and
transitions policy before second-stage init. A native system needs an explicit,
tested decision for SELinux initialization and policy, rather than accidentally
depending on the pre-policy boot state. This is a durability and hardening
question, not an explanation for missing E0 ENTRY.

### Real root and Debian handoff

- identify and verify the intended rootfs source without broad block writes;
- load the filesystem/storage closure needed to reach it;
- define fsck and read-only failure policy;
- mount and verify the root identity;
- prepare `/dev`, `/proc`, `/sys`, `/run`, firmware, and module paths for the
  new root; and
- perform a deliberate `switch_root`/`pivot_root` or equivalent exec handoff
  while preserving PID 1 lifecycle and recovery behavior.

Only after that boundary should the project add general services, networking,
SSH, time, DNS, logging, and persistent configuration.

### Host control transport

The current small progression remains appropriate:

1. E1: static userspace, mounts, child exec/reap, watchdog closure;
2. E2: USB platform bind and UDC publication;
3. E3: one ACM byte stream;
4. E4: one bounded framed request/response;
5. rootfs handoff and service supervision only after E4.

This sequence prevents a full Debian image from becoming the debugger for an
unobserved stage-0 failure.

## Smallest next H0 design unit

Design a three-way discriminator before producing another candidate:

1. an independent candidate-selection identity;
2. a retained-header result that exposes `magic`, `idx` class, and ENTRY-store
   outcome without requiring the existing saturated-ring gate; and
3. corrected runner event semantics that never call endpoint departure proof.

The design must preserve boot-only scope, the exact rollback path, Process v2,
and fail-closed classification. It should not add USB gadget setup, Debian,
storage writes, panic/RDX, or a general init framework.

## Local evidence index

- `GOAL.md`
- `docs/reports/S22PLUS_FYG8_NATIVE_PID1_USERSPACE_EXPERIMENT_EVIDENCE_LEDGER_2026-07-22.md`
- `docs/reports/S22PLUS_FYG8_RETENTION_DISCRIMINATOR_FEEDBACK_REASSESSMENT_2026-07-22.md`
- `docs/module-map/s22plus-fyg8/subsystem-retention.md`
- `docs/reports/S22PLUS_FYG8_R4W1D_F1_LIVE_PASS_2026-07-21.md`
- `docs/reports/S22PLUS_FYG8_R4W1E0_PID1_USERSPACE_PROOF_HOST_BUILD_PASS_2026-07-22.md`
- `docs/reports/S22PLUS_FYG8_R4W1E0_F1_LIVE_NO_PROOF_ROLLBACK_PASS_2026-07-22.md`
- `docs/plans/S22PLUS_FYG8_POST_PID1_OBSERVABLE_RUNTIME_ARCHITECTURE_2026-07-21.md`
- `workspace/public/src/patches/s22plus_fyg8_r4w1d_compact_pid1_witness.patch`
- `workspace/public/src/patches/s22plus_fyg8_r4w1e0_pid1_userspace_proof.patch`
- `workspace/public/src/native-init/s22plus_r4w1e_e1_runtime.c`
- `workspace/public/src/native-init/s22plus_r4w1e_checkpoint.c`
- `workspace/public/src/scripts/revalidation/device_action_f1_live_v2.py`
- source-matched FYG8 `drivers/samsung/debug/log_buf/sec_log_buf_main.c`
- source-matched FYG8 `drivers/samsung/debug/log_buf/sec_log_buf_last_kmsg.c`

## Investigation boundary

This checkpoint is based on host-side source, artifact, report, and retained
evidence review. The later feedback reassessment changed tracked documentation
only; no build was run, no candidate was generated, and no device was
contacted. It narrows the next question but does not authorize or claim another
live run.
