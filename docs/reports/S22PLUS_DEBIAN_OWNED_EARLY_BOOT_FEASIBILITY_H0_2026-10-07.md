# S22+ Debian-owned early boot: structural change feasibility

Date: 2026-10-07 KST. Target: only `SM-S906N/g0q/S906NKSS7FYG8`.
Status: **H0 architecture proposal; target implementation and boot unproved**.
Scope: record the proposed direction, reusable evidence, unresolved dependencies
and the smallest useful next investigation. This unit changes documentation
only; it performs no build, connected read, device effect or activation.

## Recommendation

Prioritize a bounded prototype in which Debian's early userspace owns boot
from the first `/init`, replacing the existing general native runtime in the
normal boot path. Reuse the hardware preparation and validation knowledge
already obtained. Further expansion of native-first handoff orchestration need
not be completed before investigating this alternative.

The intended ownership is:

```text
Samsung boot chain -> retained FYG8 kernel
  -> Debian-configured initramfs /init (initial PID namespace, PID 1)
     -> required platform/UFS preparation and protected root admission
     -> root transition and exec
  -> installed Debian init (same PID 1 and kernel boot)
     -> devices, services, networking, logging and shutdown
```

Here, "remove native" means remove the existing custom native runtime as a
required boot environment. Small S22+ hardware helpers may remain. Merely
moving the entire runtime into a Debian package would not achieve the proposed
reduction. Debian-packaged tools and boot scripts should take over the work
they can perform; target-specific code should have a defined, limited role.

This refines the [existing product goal](../../GOAL.md): Debian owns the system,
with Android separately available for management and recovery. It does not
select a replacement kernel, systemd, kexec, a new installation or a new
partition layout. Existing implementation, consumed evidence and recovery
artifacts remain available; this report neither deletes them nor interrupts
another task.

## Why this is technically plausible

The current [UFS loader](../../workspace/public/src/native-init/s22plus_native_ufs_load_v1.inc.c)
opens and checks fixed module files, then calls `finit_module`. These are Linux
userspace operations, not privileges exclusive to the native runtime. A
Debian early-boot environment with the required credentials, exact module
bytes, ordering and dependencies can in principle perform equivalent work.
Equivalent safety checks and actual driver readiness still need validation.

Debian's [initramfs-tools documentation](https://manpages.debian.org/trixie/initramfs-tools-core/initramfs-tools.7.en.html)
provides build hooks for including modules/programs and early boot scripts
before the real root is mounted. It distinguishes image construction from
runtime scripts and provides module-loading and root-mount phases. This
supports the proposed integration point, not compatibility with FYG8's
hardware or its missing kernel facilities.

The first environment must be available in RAM because the installed Debian
root cannot supply its own storage driver before that storage is accessible.
That environment can be Debian-configured from the start. Keeping a root
transition inside this boot sequence does not require the old native runtime.
The [Linux 5.10 initramfs model](https://www.kernel.org/doc/html/v5.10/filesystems/ramfs-rootfs-initramfs.html)
supports early `/init` followed by preparation and execution of the real init.

Booting with no early userspace at all is a separate, optional research topic.
It would require the kernel to reach and mount the root without a userspace
module loader. It is not a prerequisite or success criterion for this proposal.

## Existing work and evidence limits

This is not the first standalone Debian-bootstrap investigation in the repo.
The distinction is to make Debian's early-boot tooling the primary owner,
instead of extending another custom PID1 implementation or requiring the
resident native command environment before starting Debian.

| Existing evidence | Reuse and limit |
| --- | --- |
| [September bootstrap research](S22PLUS_DEBIAN_BOOTSTRAP_RESEARCH_2026-09-19.md) | Already identifies native responsibilities, storage/display coupling, Debian service ownership and FYG8 kernel gaps. Reuse this decomposition. |
| [Debian construction and ARM64 VM qualification](S22PLUS_DEBIAN_BOOTSTRAP_H0_2026-09-21.md) | Supplies package provenance, SysVinit/mdev, actual PID1/root transition, SSH/service/persistence/shutdown and negative-path evidence in a virtual machine. Hardware drivers are substituted; it is not a Samsung boot proof. |
| [P401 device construction](S22PLUS_DEBIAN_FIRST_BOOT_H0_2026-09-21.md) | Already built a standalone custom C bootstrap without the DRM userspace. Packaging and preparation are inputs, not a fresh usable candidate or installation authority. |
| [P405 physical result](S22PLUS_DEBIAN_INSTALLED_BOOT_P405_FIRST_RUN_2026-09-26.md) and [bootstrap forensics](S22PLUS_BOOTSTRAP_FORENSICS_H0_2026-09-26.md) | No Debian endpoint was proved; the stop location was unresolved. A standalone bootstrap alone did not establish a working system. Preserve early-stage observability in the replacement. |
| [P413 physical result](S22PLUS_DEBIAN_HANDOFF_P413_FIRST_RUN_2026-10-03.md) | Proves installed Debian as host PID1 and rcS entry in the same kernel boot. Service completion, NCM/SSH and Debian shutdown remain unproved. |
| [P415 physical result](S22PLUS_NATIVE_ROOT_EVIDENCE_P415_FIRST_RUN_2026-10-07.md) | Proves protected historical-file acquisition and healthy Android return. It observed native_data RECOVER set, not a clean root ready for writable boot. Missing checkpointed files do not disprove P413 execution. |

The [existing source directory](../../workspace/public/src/debian/s22plus_v1/README.md)
contains a custom [handoff implementation](../../workspace/public/src/debian/s22plus_v1/handoff.c)
and a separate [storage preparation function](../../workspace/public/src/debian/s22plus_v1/storage.c).
They are concrete reference implementations. Neither establishes that a
Debian-generated `/init` already performs the complete target sequence.

## Responsibility migration and remaining questions

| Responsibility | Proposed owner | Work that remains |
| --- | --- | --- |
| Platform providers, UFS modules and early firmware | Debian initramfs scripts and narrowly scoped helpers | Derive the complete provider/order/parameter/firmware closure; confirm probe readiness, not just successful insertion. |
| `/proc`, `/sys`, `/run`, initial `/dev` and essential nodes | Debian early userspace | Adapt the earliest device setup to the retained kernel; qualify tmpfs/mdev and required node permissions. |
| Exact target, partition and root admission | Reused checked helpers invoked by early userspace | Preserve exact binding, partition protection, clean-root and content checks before the relevant access/transition. |
| Children, file descriptors and root transition | Early boot scripts plus standard root-transition tools | Settle helpers, move the required mounts and preserve PID1 by exec; leave no old-root runtime behind. |
| Gadget, networking, SSH, logs and shutdown | Debian services | Establish one owner and qualify the target lifecycle, including the retained kernel's gadget behavior. |
| Necessary power/thermal support | Early setup or Debian service according to actual lifetime | Determine what is required for safe operation; a HUD or telemetry output is not proof of protection. |
| Native shell protocol, resident command runtime and display HUD | Outside the proposed normal boot path | Keep only a separately justified diagnostic function; do not port every experimental feature as a boot prerequisite. |

Three constraints prevent calling this a ready-made replacement:

1. **Eight UFS modules are not the complete platform.** The earlier headless
   storage hypothesis contained 42 modules. The P401 actual-artifact consumer
   binds a different, broader 73-module platform sequence plus eight UFS modules in
   [its validator](../../workspace/public/src/scripts/revalidation/s22plus_debian_artifact_v1.py).
   These are different constructions, not interchangeable minimal sets. First
   separate preparation from runtime ownership; reduce dependencies only from
   evidence, rather than assuming that a new `/init` needs just eight loads.
2. **Default Debian device management is not directly compatible.** The retained
   FYG8 analysis found DEVTMPFS and FHANDLE absent and selected SysVinit/mdev.
   Inspect the generated initramfs's actual `/init` and earliest device setup;
   a later hook cannot repair a mandatory earlier failure. Retain the working
   kernel/userspace assumptions initially instead of coupling this feasibility
   test to a systemd or custom-kernel migration.
3. **Ownership changes do not fix an unidentified kernel/USB failure.** The
   [P413 causal analysis](S22PLUS_P413_CAUSAL_RESEARCH_H0_2026-10-03.md) establishes
   a USB disconnect episode but not its trigger. The same hardware path may
   fail under Debian early userspace. The proposed reduction is an architecture
   hypothesis, not an asserted repair for P413.

## Proposed next unit and decision criteria

Start with H0 construction and inspection using the retained FYG8 kernel and
existing root identity. Produce a small Debian-configured initramfs with an
explicit inventory of packaged tools, scripts and any remaining target helper.
Compare its reached boot path with the current preparation code, including
failure behavior. Reuse existing fixtures and qualification outputs where
inputs actually match; do not rebuild or reinstall the root simply to rename
the boot owner.

The first useful target milestone, after its own applicable review and live
scope, is: the new `/init` executes as actual PID1, performs the required cold
hardware preparation, discovers the exact storage and reports protected root
admission or its precise rejection. For the dirty native_data observed by P415, a
correct rejection is diagnostic progress, not successful clean-root admission.
P415's observed state still requires the separately scoped recovery route
before a later clean-root or writable Debian test.

Subsequent milestones are installed Debian PID1 in the same boot, authenticated
SSH, an ordinary package-managed service, controlled shutdown and a fresh boot
with persistent state and re-established access. Report these separately from
original-A recovery health. VM results validate userspace paths; they cannot
substitute for the Samsung module, storage, USB or recovery observations.

Prefer the new path when the actual boot artifact no longer starts the old
native runtime, required behavior is preserved, and less custom orchestration
must be maintained. If equivalent runtime machinery merely moves into scripts,
or a concrete dependency still needs the old owner, record that result and
reassess the smallest remaining adapter. Do not finish every historical
diagnostic as a prerequisite unless it is necessary for this path's safety or
stated functional proof.

## Observation, recovery and scope

Design evidence before repeating an opaque standalone boot. Consider bounded
per-run/per-boot device-local records alongside USB, with checked writes,
integrity/boot association and later retrieval. Storage is unavailable during
the earliest steps; RAM evidence may be lost on reset. Missing records cannot
establish non-execution. Any persistent recorder needs its own allowed write
scope and must be distinguished from read-only root-admission evidence.

Once an operation is properly admitted, the desired product should not require
an interactive native host command to progress through normal Debian startup.
Moving observations off that path does not make all failures ignorable: target,
root, storage, child and required health failures still need explicit handling.
Any change to an existing observer's continuation rules belongs to the changed
execution review, not to this report.

Removing the native runtime can also remove its CONTROL and reporting paths.
Physical original-A recovery remains a separate design obligation; neither
VM reboot nor healthy normal return proves automatic recovery from a stalled
kernel or failed PID1. Reuse qualified transport/recovery machinery only within
its actual reviewed scope, and review the changed first-userspace execution
and authority interactions before target use. Current contracts, grants,
consumed claims and no-replay rules are not changed here.

This report and its goal pointer are the complete documentation unit. Existing
concurrent code/policy work and historical pins remain untouched. No candidate
ordinal or activation is assigned. A90 and S20+ are outside this proposal and
received no device action.
