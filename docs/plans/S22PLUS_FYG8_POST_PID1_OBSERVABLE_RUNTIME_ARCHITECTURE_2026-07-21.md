# S22+ FYG8 post-PID1 observable runtime architecture

Date: 2026-07-21 KST

## Verdict

R4W1-D closes only the kernel-to-userspace activation boundary: the rebuilt
kernel accepted `/init` and continued as PID 1. The next target is not Debian,
NCM, a shell, or a large service supervisor. It is the smallest runtime that
can prove, in order:

1. userspace executed and mounted its volatile runtime;
2. one exact static child executed, returned the expected token, and was
   reaped;
3. the five-module watchdog closure loaded and the candidate remained alive;
4. the S22+ USB platform stack registered, bound, and published its UDC;
5. one ACM byte stream, then one fixed request/response, crossed the host link.

Use one new target-guarded kernel evidence carrier for all of these rungs. Keep
the rungs as separate Process v2 transactions. No current device action is
authorized by this design.

## Evidence baseline

### Proven

- R3C1 proved that a source-matched, unpatched rebuilt FYG8 kernel can boot
  normal Android and roll back cleanly.
- R4W1-D proved `kernel_execve("/init") == 0` while `current` was PID 1. Two
  complete post-rollback `/proc/last_kmsg` reads retained one exact contiguous
  proof and no foreign or partial proof.
- The R4W1-C carrier remained alive long enough for attended recovery while
  containing the exact five-module watchdog closure.
- Stock FYG8 proves that `sec_log_buf`, `dwc3-msm`, the UDC, and the MAX77705
  Type-C chain can bind under Android.

### Not proven

- No R4W1-D evidence comes from userspace. It does not prove `_start`, a mount,
  `finit_module`, child execution, bind, UDC creation, USB enumeration, or a
  control loop.
- O3F and the earlier S22+ USB candidates did not retain an internal phase.
  Their no-enumeration result cannot identify which internal operation ran.
- Module registration in `/proc/modules` is not driver probe or platform bind.
- Stock Android USB success does not prove that the same vendor modules bind
  under bare PID 1.

## Retired observation paths

Do not reopen these paths for this ladder:

- mainline pstore, pmsg, or ramoops;
- DTBO-based ramoops enablement;
- panic, RDX, EUD, or UART as a normal progress channel;
- append-only kmsg markers placed at an unchecked ring cursor;
- Download enumeration as a proxy for an internal native-init phase.

V3439 is decisive: a live, correctly bound ramoops backend with `/dev/pmsg0`,
1 MiB of pmsg space, and an attended marker-plus-panic sequence retained zero
ramoops records, while Samsung `/proc/last_kmsg` retained panic text without
the run marker. This is stronger than the fact that `CONFIG_PSTORE_PMSG=y`.

## Evidence carrier R4W1-E

### Why a new carrier is required

The R4W1-D marker is candidate-bound. Reusing that Image with a changed `/init`
would preserve the old token while changing its meaning. R4W1-E therefore
needs one new clean kernel build and a new independent static audit.

The carrier is evidence plumbing only. It must not change power, clocks,
regulators, DTBO, verified-boot policy, storage, or USB behavior.

### Corrected geometry

R4W1-D did **not** reserve bytes outside the Samsung log ring. It copied one
token into a contiguous region immediately behind the current saturated-ring
cursor and did not publish a new index. Treating that location as a permanent
carve-out would be incorrect.

R4W1-E can safely reuse this geometry only under all of these invariants:

1. Before dereferencing retained RAM, the exec hook proves the exact enabled
   DT log node, address/size, strategy, partial-reserved-memory property, and
   containing direct-mapped reserved-memory node.
2. The exec hook snapshots `magic`, `idx`, `boot_cnt`, and the selected
   contiguous region.
3. The native candidate never loads `sec_log_buf.ko`. Loading it installs the
   Samsung printk writer and can advance or rewrite the same ring.
4. Every checkpoint update reopens the header and refuses unless `magic`,
   `idx`, and `boot_cnt` still equal the exec-hook snapshot.
5. The combined proof region is selected once and never recomputed from a
   later cursor.
6. The candidate becomes quiet after its terminal checkpoint and remains in a
   bounded park until attended Download and rollback.

The existing FYG8 driver supports this distinction. Its module probe maps the
reserved buffer, exposes `/proc/last_kmsg`, pulls early logs, installs the
logger, and subsequently advances `s_log_buf->idx`. The successful R4W1-D
carrier did not load this module.

### Immutable entry proof plus A/B checkpoint slots

Use one contiguous combined region:

- one immutable, exact carrier-entry marker written by the proven post-exec
  PID-1 hook;
- checkpoint slot A;
- checkpoint slot B.

Do not use one mutable slot. Writing a new body before its final commit byte
would invalidate the previous record if reset occurs mid-copy. A/B slots keep
the prior valid generation intact:

1. invalidate the inactive slot commit byte;
2. write its fixed-width body and checksum;
3. issue a write memory barrier;
4. publish the commit byte last;
5. make the newly committed slot the active generation.

The host validates each slot independently and selects the highest valid
generation. A committed slot with a bad body or checksum is invalid by itself;
it does not discard the other valid slot. A torn new slot therefore leaves the
prior phase usable. Exact sizes and offsets are an implementation result, not a
design assumption; the complete combined region must be compact, contiguous,
and accepted by the adapted static auditor.

### Write-only PID1 checkpoint API

Expose a target-specific write-only proc node only when the R4W1-E Kconfig
flag is enabled. Its handler must require:

- `task_pid_nr(current) == 1`;
- the exec hook initialized this boot's carrier;
- exact fixed request length and reserved fields equal zero;
- unchanged Samsung log `magic`, `idx`, and `boot_cnt` snapshot;
- one E1-E4 profile kind that remains constant after its first accepted write;
- one nonzero dynamic run ID that remains constant and is later matched to an
  exact host manifest;
- the exact next profile stage, profile-derived generation, and module index;
- success only at the terminal stage and nonzero detail for failure;
- no second terminal record.

Userspace does not provide the immutable entry marker or slot address. Profile
kind selects the fixed kernel state machine. The dynamic run ID is an opaque
key mapped by an exact-hash host manifest to the Image, init, child, closure,
stage schema, and static control-flow result. It is not a self-referential hash
of binaries that embed it. The kernel gate is not a cryptographic attestation
of userspace behavior; exact artifact identity, preflight family absence,
one-shot chronology, and the independent checker remain load-bearing.

Each slot needs at least `magic`, format version, carrier ID, profile kind,
run ID, generation, stage, outcome, item index, signed detail/errno, checksum,
and a commit byte. The host must reject invalid checksum, missing commit,
duplicate or impossible generation, non-successor stage, unknown profile kind,
unexpected run or boot identity, foreign carrier, and any partial family token.

## Runtime shape

Keep exactly two code layers.

### Generic runtime core

- raw PID1 entry and PID verification;
- checked mount/readback helpers;
- tmpfs `/dev` and `/run`, plus checked manual device-node creation;
- bounded fork/exec, pipe token, timeout, exact-status wait, kill, and reap;
- ongoing orphan reap once more than one child exists;
- checkpoint client with fixed stage transitions;
- bounded framed I/O for the later ACM rung.

Extract only the process-control mechanics from `a90_run.c` and
`a90_reaper.c`. Reuse the A90 selftest result shape, not its storage, display,
audio, network, or service inventory.

### S22+ FYG8 adapter

- exact watchdog and USB module tables generated from the shipped
  `modules.dep` and `modules.softdep`;
- exact stock `.ko` hashes and runtime names;
- platform bind gates and `a600000.dwc3` UDC identity;
- forced-peripheral sysfs path, if and only if the DWC3 platform already bound;
- configfs ACM descriptors and sysfs-derived `ttyGS0` major/minor;
- stage schema, dynamic run ID, and expected host evidence.

Do not add a plugin framework, service registry, arbitrary command table, NCM,
mass storage, persistent rootfs, hot reload, or `switch_root` to this unit.

## Kernel-config decisions

Keep `CONFIG_DEVTMPFS=n`. FYG8 already has built-in procfs, sysfs, tmpfs,
configfs, DWC3 core, gadget core, ACM, and NCM support. Android first-stage init
itself demonstrates the applicable pattern: mount tmpfs on `/dev`, create only
the essential nodes, then load the required modules. The current O3F carrier
also derives dynamic tty major/minor values from sysfs.

Enabling devtmpfs would create another kernel variant and Android regression
surface without removing the actual S22+ risk, which is vendor platform bind.
Revisit it only if a required node cannot be derived from sysfs.

Do not convert vendor USB or Type-C modules to built-ins. Do not change console
routing. Further kernel changes require positive evidence from a missing
config, driver, or kernel defect, not merely absent host enumeration.

## Module-loader decision

Keep the device-side loader small and deterministic:

1. a host generator parses exact FYG8 `modules.dep` and `modules.softdep`;
2. an independent audit checks dependency closure, order, hashes, duplicate
   runtime names, and bind-gate ownership;
3. the candidate contains a static ordered table;
4. each `openat`/`finit_module`/`close` result and final `/proc/modules`
   membership is checkpointed;
5. platform bind and UDC gates are separate from module registration.

AOSP `libmodprobe` is a semantics reference for the host generator, not a new
C++ runtime dependency. Do not add BusyBox, kmod, or a general module resolver
to the first candidate.

`sec_log_buf.ko` is deliberately excluded from every native candidate module
plan while the retained checkpoint carrier is active.

## Evidence ladder

Each live rung is one fresh Process v2 F1 transaction: exact boot-only AP,
connected D0 and preparation, fresh approval, one candidate transfer, bounded
observation, exact Magisk boot rollback, and final Android/root/partition
health. A failure checkpoint is diagnostic; only the rung's exact terminal
success checkpoint can create PASS.

### E1 - Local observable runtime

Sequence:

1. kernel plants immutable PID1 entry and initializes checkpoint A/B;
2. PID1 mounts and reads back procfs, sysfs, tmpfs `/dev`, and tmpfs `/run`;
3. PID1 creates and verifies only required device nodes;
4. PID1 executes one separate static no-`PT_INTERP` child;
5. parent requires exact pipe token, EOF, expected exit status, and reap;
6. PID1 loads and verifies the exact five-module watchdog closure;
7. PID1 records terminal success and enters bounded quiet park.

This proves userspace execution, volatile runtime, one exact child lifecycle,
the watchdog closure, and bounded liveness. It does not prove generic service
supervision, USB, persistent storage, or Debian readiness.

### E2 - USB registration, bind, and UDC

Repeat E1, then load the smallest generated FYG8 USB closure. Advance a
checkpoint after each module and after each distinct gate:

- module opened and inserted;
- exact runtime name present;
- platform driver/device link present;
- DWC3 child present;
- exact UDC present.

Stop at the first errno, deferred/missing bind, changed log cursor, or ambiguous
UDC. If all modules register but the platform does not bind, stop the USB path
and analyze that exact provider/probe boundary before building a protocol.

### E3 - One-way ACM

Repeat E1 and E2. Create one generic ACM function, force peripheral mode only
after the exact platform bind, bind the exact UDC, derive `ttyGS0` from sysfs,
and send one exact profile-bound banner. PASS requires the host to receive the
exact bytes from one expected ACM endpoint; enumeration alone is insufficient.

### E4 - One bounded exchange

Repeat E1 through E3. Accept one exact length-bounded request such as
`STATUS <nonce>` and return one exact nonce-bound response. Reject NULs,
overflow, trailing data, duplicate requests, and every unknown opcode. This
rung authorizes no shell, arbitrary argv, upload, path, power action, or second
request.

After E4, a separate design may generalize the control runtime. NCM and Debian
handoff remain later projects.

## Process v2 changes

Do not fork another live helper. Extend Process v2 once with typed evidence:

- retained immutable entry plus decoded checkpoint A/B;
- optional exact ACM endpoint and byte-stream observer for E3/E4;
- `all_of` success semantics with separately classified diagnostic evidence.

The runner must keep direct serial file-descriptor ownership and bounded I/O.
Manifests change data and expected evidence; the execution core does not change
for each rung.

## Host-only gates before the first build

1. Prove the exact R4W1-D log geometry and FYG8 `sec_log_buf` writer behavior.
2. Implement A/B encode, commit, decode, and highest-valid-generation logic as
   a pure host-tested unit.
3. Test torn body, committed bad checksum with prior-slot fallback, no-valid
   slot, stale/impossible generation, changed cursor, unknown profile kind,
   unexpected run/boot identity, foreign family, and terminal replay.
4. Define E1-E4 exact stage tables. Bind each future dynamic run ID to full
   artifact identities in the exact manifest/checker; P2.7 model IDs are never
   live evidence.
5. Implement the guarded kernel source and proc API, but perform no device
   action in the same unit.
6. Implement the E1 runtime source and exact child with compile/static tests.
7. Adapt the existing clean-build, symlink-restoration, FIPS, reproducibility,
   candidate-builder, and independent-checker path; do not create a second
   builder family.

Only after those gates pass should one clean R4W1-E build be scheduled. E1 is
the first live use of that Image; a separate policy-only or kernel-only live
canary is not required unless static evidence reveals broader kernel impact.

## Stop conditions

- `sec_log_buf.ko` appears in a native candidate module plan.
- The Samsung ring cursor changes after carrier initialization.
- The retained region cannot hold an independently validated A/B layout.
- Candidate source can publish a terminal checkpoint before its required
  control-flow checks.
- A module is considered bound from `finit_module` or `/proc/modules` alone.
- E2 lacks one exact first-failure checkpoint.
- A live rung would require DTBO, vendor_boot, recovery, vbmeta, BL, CP, CSC,
  userdata, EFS, RPMB, modem, power, regulator, or partition-table changes.
- The same material failure repeats twice without new evidence.
- The design begins adding shell, NCM, Debian, or a general supervisor before
  E4 closes.

## Implementation status

P2.7 completed the carrier source and host contract on 2026-07-21. Exact ABI,
patch/source hashes, profiles, and validation are recorded in
`docs/reports/S22PLUS_FYG8_R4W1E_CHECKPOINT_CARRIER_HOST_CONTRACT_PASS_2026-07-21.md`.
No kernel build, image, device contact, or live authority was produced.

P2.8 completed the exact E1 runtime, child, checkpoint client, and host contract
on 2026-07-21. The result includes exact source identity, clean staged
two-build reproduction, AArch64 syscall disassembly audit, dynamic child proof,
and byte-exact request comparison with the P2.7 carrier model. Details are in
`docs/reports/S22PLUS_FYG8_R4W1E_E1_RUNTIME_HOST_CONTRACT_PASS_2026-07-21.md`.
No kernel build, ramdisk, candidate, device contact, or live authority was
produced.

## Next bounded unit

Adapt the existing clean R4W1 Full-LTO build, source-restoration, FIPS,
reproduction, candidate-builder, and independent-checker path to the exact
R4W1-E carrier and E1 sources. Produce one clean kernel build plus an offline
E1 ramdisk/candidate contract with a fresh manifest-bound run ID. This remains
host-only and must not create live policy, contact a device, or flash.

## External references

- Linux initramfs `/init` and PID1 contract:
  <https://www.kernel.org/doc/html/latest/filesystems/ramfs-rootfs-initramfs.html>
- Linux devtmpfs Kconfig semantics:
  <https://android.googlesource.com/kernel/common/+/8966961b31c251b854169e9886394c2a20f2cea7/drivers/base/Kconfig>
- AOSP first-stage mount, node, and module-loading sequence:
  <https://android.googlesource.com/platform/system/core/+/android16-release/init/first_stage_init.cpp>
- AOSP module dependency and soft-dependency semantics:
  <https://android.googlesource.com/platform/system/core/+/android16-qpr2-release/libmodprobe/libmodprobe.cpp>
- Linux configfs gadget construction and UDC binding:
  <https://docs.kernel.org/usb/gadget_configfs.html>
- Linux gadget serial and dynamic tty device identity:
  <https://docs.kernel.org/usb/gadget_serial.html>

These references establish generic kernel/userspace contracts. They do not
replace FYG8 source, module, bind, or live evidence.

## Review reconciliation

Three independent repository reviews and one persistent Claude Opus discussion
agreed on the small-rung order, manual `/dev`, static child proof, module/bind
separation, ACM-first transport, and reuse of the Process v2 core.

Two reviewer proposals were rejected or corrected against stronger repository
evidence:

- Claude's initial pmsg-primary proposal was withdrawn after V3439 was supplied.
- A later "reserved carve-out" interpretation was corrected by reading the
  R4W1-D patch and FYG8 `sec_log_buf` writer. The proven location is inside the
  ring, so safety depends on keeping that writer unloaded and checking that its
  cursor is unchanged.

The single-slot commit-last proposal was also strengthened to A/B slots; commit
last in one slot cannot preserve the old valid body after a torn overwrite.
