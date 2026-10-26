# S20+ next PID1 witness: route selection

Date: 2026-09-23. Target: `SM-G986N / y2q / y2qksx / G986NKSS8IYC2`.
Status: **H0 RESEARCH COMPLETE; RECOMMENDATION ONLY; NO NEW CANDIDATE OR ACTIVATION**.

This status describes the route-selection phase. The subsequent [P2 H0 implementation and validation](S20PLUS_G986N_P2_RAM_SNAPSHOT_H0_2026-09-23.md) is complete; live activation remains closed.

The recommended next H0 unit is a fresh, minimal PID1 witness that saves its
early evidence in RAM before handing off to the unchanged resident Magisk init.
The host would retrieve that snapshot through the same boot's existing Android
ADB/root transport. Direct native USB remains the eventual resident transport;
it should not be the only observation channel for the next first-light attempt.

This answers the bounded question of how to establish execution of our `/init`
as initial PID1. It does not establish a standalone native environment, Debian
boot, a working new payload, or automatic recovery. No device command, build,
activation, candidate consumption, reboot or partition operation was performed.
S22+, A90 and other-target device command counts are zero.

## What the retained records actually establish

| Path | Observed result | Implication for the next candidate |
| --- | --- | --- |
| S20+ P0 first consumed candidate | Its candidate backend was not invoked; a host identity comparison stopped it. | Consumption is not execution evidence. |
| S20+ P0 V2 | Transfer outcome uncertain after a process-cage failure; ACM observation was `NO_PROOF`. | Preserve uncertainty; do not count this as a proved execution failure. |
| S20+ P0 V3 | Boot-only transfer and process quiescence proved; no exact ACM banner in 180 seconds; resident rollback and health complete. | A failure anywhere before USB output remains indistinguishable from failure to execute `/init`. |
| S20+ P1 | Candidate transfer proved; Android ADB metadata appeared; public-health rejection preceded root and kmsg acquisition. | Neither handoff failure nor witness absence was established. Fix acquisition as a separate responsibility. |
| S22+ July 7 chainload | Wrapper-to-Magisk experiment failed to establish rooted Android or its marker and was rolled back. | A relevant negative precedent, not proof that all Magisk handoffs fail. |
| A90 resident / S22+ native V3 | Native USB state/selftest or authenticated native sessions were observed on those exact targets. | Useful architecture for the eventual native resident; their working transport and recovery do not transfer to S20+. |

The P0 distinctions above were checked against the retained per-run intents,
results and terminals, not just aggregate attempt counts. In particular, the
September 6 narrative that three candidates all executed and stayed silent is
too broad. Its useful observation-channel criticism survives this correction.
No old result or journal was changed. See the [P0 execution history](S20PLUS_G986N_P0_PID1_ODIN_F1_OWNER_H0_2026-09-01.md#2026-09-02-candidate-preflight-false-positive),
[P1 run/recovery](S20PLUS_G986N_P1_RUN_RECOVERY_2026-09-08.md), and
[historical channel analysis](S20PLUS_G986N_EARLY_BOOT_OBSERVATION_CHANNELS_2026-09-06.md).

P1's source is also materially different from the early S22+ wrapper. The S20+
producer uses a freestanding AArch64 entry, checks `getpid() == 1`, records
procfs/namespace/boot values, creates no child, restores Magisk to `/init`, and
preserves the kernel's argv/envp. It tests failure paths. The S22+ experiment used
a libc wrapper, extra marker files and a fallback exec path. These differences
do not diagnose the S22+ failure or prove the S20+ handoff. They prevent treating
the two experiments as identical. Sources: [S20+ producer](../../workspace/public/src/native-init/s20plus_p1_pid1_witness_init.c),
[S22+ producer](../../workspace/public/src/native-init/s22plus_init_magisk_chainload.c),
[S22+ result](S22PLUS_NATIVE_INIT_P2_MAGISK_CHAINLOAD_LIVE_2026-07-07.md#result).

## Comparison

| Option | Advantage | Remaining dependency / cost | Selection |
| --- | --- | --- | --- |
| PID1 → direct native ACM | Independent of Android; useful foundation for a resident runtime. | S20+ early role/UDC/gadget/tty path has no positive live result. Silent failure still loses all stage evidence. | Long-term direction; defer another opaque first-light attempt. |
| P1-style handoff, then read live kmsg | Smallest observer change; reuses the candidate architecture. | Early log prefix may be overwritten before ADB/root becomes usable. | Useful diagnostic fallback, weaker than saving the prefix early. |
| PID1 snapshot in RAM → Magisk → same-boot ADB | Separates early evidence production from late transport; preserves the log prefix before Android traffic. | New bounded snapshot producer/reader and exact Magisk file-relocation validation; handoff/root still must work. | Recommended next H0 candidate design. |
| PMSG / last_kmsg after reboot into TWRP | Could observe a candidate that never exposes USB. | Exact-route retention and provenance remain unproved; another kernel boot can replace the old snapshot. | Separate fallback research, not the next candidate's sole proof. |

S20+ has built-in configfs ACM and the DWC3/Samsung notifier components in its
exact kernel. That removes S22+'s module-loading dependency but does not prove
early attachment. Linux's [configfs documentation](https://kernel.org/doc/html/latest/usb/gadget_configfs.html)
requires an actual UDC binding; [FunctionFS](https://www.kernel.org/doc/html/latest/usb/functionfs.html)
additionally requires a userspace function to supply descriptors and keep its
endpoints open. Adding adbd/FunctionFS or NCM would expand the first witness.
See the [S20+ substrate audit](S20PLUS_G986N_NATIVE_USB_SUBSTRATE_H0_D0_2026-08-16.md).

Download arrival and a fixed banner are insufficient alone. UART is also a poor
next choice under the exact retained configuration, which disables the relevant
serial console. TWRP as a terminal environment does not preserve the previous
boot's live `/dev/kmsg`; it needs a separately demonstrated retention channel.
The PMSG V1 trial wrote no marker and performed no reboot, so its `NO_PROOF`
does not disprove RAM retention. See the [early observation audit](S20PLUS_G986N_EARLY_BOOT_OBSERVATION_H0_2026-09-05.md)
and [PMSG trial](S20PLUS_G986N_PMSG_WARM_REBOOT_D1_TRIAL_FAILURE_2026-09-05.md).

## Why the RAM snapshot is plausible

The exact retained Magisk v30.7 archive reverified at SHA-256
`9a908fc13a60bbb95c848c9e8cfbb5bd4e49fda98ee6932907c4a517fbc95437`.
Its extracted `init.rs`, `mount.rs`, `mount.cpp`, `rootdir.cpp`, `twostage.rs` and
`docs/guides.md` matched the archive member bytes. The current P1 manifest has
`overlay.d/sbin` and `debug_ramdisk` already present in the resident ramdisk.

The [official overlay guide](https://topjohnwu.github.io/Magisk/guides.html#root-directory-overlay-system)
documents special treatment of `overlay.d/sbin`: its contents go to Magisk's
internal tmpfs. A new arbitrary top-level overlay filename does not have that
guarantee. The exact v30.7 implementation makes the route concrete:

- [mount.rs:77–92](https://github.com/topjohnwu/Magisk/blob/v30.7/native/src/init/mount.rs#L77): `prepare_data()` mounts temporary data storage and copies `overlay.d` into it.
- [mount.cpp:212](https://github.com/topjohnwu/Magisk/blob/v30.7/native/src/init/mount.cpp#L212): `setup_tmp()` binds the temporary tree at the selected Magisk location.
- [rootdir.cpp:262–312](https://github.com/topjohnwu/Magisk/blob/v30.7/native/src/init/rootdir.cpp#L262): the read-only-root path moves the `sbin` overlay contents into that location.

This supports an H0 design in which the witness publishes a uniquely named,
non-executable snapshot under the existing `overlay.d/sbin` directory before
exec. The added evidence storage would be RAM-only; the witness would not write
the physical `/data` partition. Runtime validation must establish the actual
mount/path and refuse a persistent-storage fallback. Ordinary resident
Android/Magisk boot behavior remains a separate existing dependency.

**This is source-backed feasibility, not a tested S20+ snapshot handoff.**
Magisk copies/moves can fail, the candidate can hang, and Android/root may never
appear. A file copied through Magisk is not tamper-proof against a hostile root.

The [kernel kmsg ABI](https://www.kernel.org/doc/Documentation/ABI/testing/dev-kmsg)
explains the other half: reads return records, nonblocking exhaustion returns
`EAGAIN`, and overrun can produce `EPIPE`. Sequence numbers reveal missing
records. Userspace cannot select kernel facility zero, but it can write
arbitrary message text; facility identifies kernel versus userspace, not a
particular PID. The target's retained `printk.c` agrees. Reading before handoff
reduces later FIFO eviction; it cannot recover records already evicted before
PID1 starts.

The exact stock config reverified at
`5e4e4a986f7aae396dc3ebb03818a4c0b9bea5f6948c5e17eb6abaf8d988f760`.
`LOG_BUF_SHIFT=17` is a base size, not proof of a 128-KiB live capacity:
`LOG_CPU_MAX_BUF_SHIFT=17`, eight configured CPUs and source CPU scaling can
increase it, and command-line/allocation behavior also matters. No live ring
size or survival duration was measured in this task.

## Recommended implementation boundary

1. Preserve the reviewed first-entry PID check and original Magisk handoff.
   A fresh candidate emits its own candidate/run binding and kernel-derived
   PID, procfs namespace and boot identity. A run value supplies freshness,
   not cryptographic origin authentication.
2. Before exec, acquire a finite nonblocking raw kmsg prefix through the
   witness record and publish it with bounded status metadata in the RAM
   location above. Use explicit byte/record/time bounds; reject loss,
   malformed records, short publication and partial files. Evidence failure
   must still reach the existing handoff when the involved syscalls return.
   This is not a guarantee against a hung syscall or a failed exec.
3. Separate host observation readiness from full Android health. Establish
   the exact prepared target, build, topology, current boot and required
   privilege before the fixed read, without requiring the UI to finish first.
   Preserve bounded raw predicate output before parsing and classify expected
   startup states separately from target conflicts or unexpected failures.
   Any bounded reobservation must belong to the newly reviewed profile.
4. Retrieve the exact RAM file and bind its bytes to before/after same-boot
   identity. Preserve raw bytes before interpretation. A live kmsg read may
   supply corroboration but is not required to retain an already saved prefix.
5. Preserve the existing evidence requirements: sequence zero and continuity,
   kernel `/init` dispatch record, first userspace witness ordering, PID and
   initial namespace checks, candidate/transfer/source binding, and the stated
   controlled-experiment assumptions. A stored prefix needs an explicit new
   acquisition type; do not relabel it as the old live-kmsg receipt or relax
   missing-prefix rejection. A matching file alone is not proof.
6. Keep candidate evidence, Android readiness, boot rollback and final TWRP
   health as separate results. Adopt the shared TWRP runtime's actual start,
   boot rollback without auto-reboot, attended physical entry and terminal
   validation. Healthy TWRP cannot close an uncertain boot rollback.

The concrete P1 defect is visible in the current consumer: `observe_candidate()`
waits for the inherited resident-health result before invoking the kmsg reader;
the public parser demands `boot_completed=1` and `bootanim=stopped`. The consumed
failure did not retain the rejected values, so a timing explanation remains a
hypothesis. [P1 owner](../../workspace/public/src/scripts/revalidation/s20plus_g986n_p1_pid1_witness_f1.py)
and [health parser](../../workspace/public/src/scripts/revalidation/s20plus_g986n_boot_recovery_canary_b0_f1.py)
provide the executable evidence. Android's [init documentation](https://android.googlesource.com/platform/system/core/+/refs/tags/android-13.0.0_r1/init/README.md)
separately describes early init and later boot stages; it does not establish
when this Samsung build's ADB/root becomes available.

The next implementation should validate the actual producer's success and
failure paths, exact ARM64 syscall ABI, partial snapshot handling, Magisk
relocation, delayed readiness, identity changes and reporting cuts. Fixtures
must not be presented as live Magisk/USB/retention proof. Reuse unchanged tests
and source qualifications. The new producer, acquisition semantics and owner
integration require the repository's independent review before activation.

If early capture already lacks sequence zero, preserve the diagnostic result
and reconsider the channel; do not weaken attribution. If the RAM handoff
cannot be established, an observer-only successor remains the smaller fallback,
with its log-retention limit stated. If Android/Magisk handoff itself is shown
to fail, move to native USB stage observation or separately qualify persistence.
Do not require a complete S22+ failure diagnosis before useful S20+ H0 work.

## Sources, validation and scope

Exa was used for five searches across native USB, Magisk handoff/overlay,
kmsg/persistence and Android init. They returned 25 results with 25 distinct
URL strings; multiple kernel-documentation URLs cover the same document and
are not independent corroboration. Only original kernel/AOSP/Magisk sources
support the public technical claims. Exact retained target files and run
records take precedence over generic documentation for device-specific facts.

Additional historical references: [A90 resident qualification](A90_RESIDENT_INSTALL_V2_F1_PASS_2026-08-02.md),
[S22+ native session V3](S22PLUS_NATIVE_SESSION_V3_LIVE_2026-09-15.md),
[ramoops documentation](https://docs.kernel.org/admin-guide/ramoops.html), and
[current TWRP runtime qualification](S20PLUS_G986N_TWRP_BASELINE_QUALIFICATION_2026-09-08.md).

This unit changes only this research report and the selected goal's next-work
pointer. No execution code, policy, activation, artifact or consumed evidence
was changed. Source/archive checks and scoped documentation checks are the
appropriate validation; no image build or device experiment is required to
complete this route-selection task.
