# S22+ Debian-owned early boot: ARM64 VM result

Date: 2026-10-07 KST. Target research: `SM-S906N/g0q/S906NKSS7FYG8`.
Result: **PASS_DEBIAN_EARLY_BOOT_VIRT_H0**; Samsung execution remains unproved.
Scope: the first bounded implementation from the
[architecture proposal](S22PLUS_DEBIAN_OWNED_EARLY_BOOT_FEASIBILITY_H0_2026-10-07.md).
No device was read, booted, written or repaired. No kernel was modified/built,
and no Samsung boot/AP package or live capability was prepared.

## Result and architectural difference

Debian initramfs-tools 0.148.4 supplies the initial `/init` shell script. Its
packaged `mkinitramfs` constructs the actual archive, and its packaged
`run-init` performs the final transition to installed SysVinit. The VM starts
this path directly, without first executing the existing custom native PID1,
resident console, display runtime or native host-command sequence.

The first `/init` executes as actual PID 1 (`/proc/1/exe` is `/usr/bin/sh`).
It prepares devices, admits the protected root and records its boot identity.
After the transition, authenticated SSH checks `/proc/1/exe` as `/usr/sbin/init`,
the actual ext4 root, tmpfs `/dev`, devpts and the same kernel boot identity.
The recorded early command line is exactly `/bin/sh /init`. Ordinary SysV
shutdown reaches power-down; the final ext4 superblock is clean and
`e2fsck -fn` passes.

| Real ARM64 VM case | Outcome |
| --- | --- |
| Normal root | Debian shell PID1 -> protected root admission -> installed SysVinit in the same boot; public-key SSH; ordinary shutdown and clean ext4. |
| Wrong root UUID | Child reports `root-uuid`; PID1 parks at `root-identity`; no root-admitted or final-exec marker; entire disk unchanged. |
| Altered installed init bytes | Reused content verifier rejects the root; PID1 parks at `root-tree`; no writable admission or handoff; entire disk unchanged. |

The negative disks are fresh copies and are hashed in full before and after
execution. Their failure is demonstrated by the expected producer stage and
absence of continuation, not merely QEMU exit status. All retained original
fixtures remain unchanged. The earlier VM service/package/persistence tests
are reusable background evidence, not new results of this smaller suite.

## Implementation and retained inputs

The [new source directory](../../workspace/public/src/debian/s22plus_initramfs_h0/README.md)
contains two host scripts, four small boot/build scripts and a child checker.
The runtime adapts one line of the upstream `/init`: its unconditional
devtmpfs mount becomes a sourced tmpfs/mdev setup. A Debian `BOOT=` extension
provides fixed protected VM root admission; an init-bottom script supplies
the `/dev` move normally handled by udev. Debian's phase sequencing and final
`run-init` remain in use.

The C child reuses the existing metadata/content consumers from
[`s22plus_v1/handoff.c`](../../workspace/public/src/debian/s22plus_v1/handoff.c).
It rejects PID1 execution. Linker garbage collection removes the old C PID1
entrypoint and unused mount/boot functions; the linked symbols were inspected.
This is a smaller ownership boundary, not a claim that all target-specific
code has disappeared or that the old runtime was just renamed.

Debian InRelease, the signed-index hash and all six fetched package hashes were
verified. Construction repeats that verification before extraction into a
private mapped-root builder. The actual Debian `mkinitramfs` is executed there;
the host's Ubuntu initramfs generator is not substituted. Udev is deliberately
absent and its early device responsibilities are replaced by the scoped port.
A separately corrupted `.deb` is rejected before extraction or image creation.

The prior Debian root archive, root UUID and exact metadata/content manifests
are reused. The virtual Linux **5.10.226** Image and configuration remain
byte-identical to the prior H0 inputs. DEVTMPFS and FHANDLE remain disabled.
Virtual block/network drivers are built in; module loading, Samsung UFS,
firmware and USB are not exercised by this VM.

Final build-4's two archives are identical to each other and to build-3's two
archives. Each is **6,375,606 bytes**, SHA-256:
`461cc1e65918f7171b4b1364f5afbe60bf275b00cacc2b185a234c627947d6e8`.
Build-4 adds source/input provenance checks without changing the runtime
artifact, so the successful VM-3 execution is reused by exact artifact identity.
No new boot-time, RAM-use or image-size optimization is claimed.

## Validation, corrections and provenance

Python compilation, shell syntax checks, ARM64 cross-compilation/`file`, linked
symbol inspection, A/B archive comparison and the three real VM paths pass.
Independent H0 review returned **PASS**, with no blocking findings. It checked
the actual archive, signed package chain, refusal ordering, raw VM evidence,
source snapshots and host-only boundaries. This is not target activation or
physical recovery qualification.

Two construction corrections are retained: the module-disabled VM kernel has
no `modules.order`, so its empty list is derived only under that checked kernel
configuration; a future construction epoch initially left changing timestamps
unclamped, so it was replaced with the retained past epoch. Failed build logs
and nonidentical outputs remain private.

The first two VM attempts reached installed init and SSH but failed the host
proof assertion. Tracing identified an unnecessary `noresume` kernel argument
being passed to `/init`, while the assertion expected no extra argument.
Removing that redundant argument was sufficient because the initramfs already
declares `RESUME=none`. The exact assertion was retained and the final suite
used new disks. Those earlier attempts retain `FAIL_H0`; their forced VM stops
are not relabelled as clean shutdowns.

Private evidence root:
`workspace/private/outputs/s22plus-debian-initramfs-h0-20261007-1/`.

| Record | Role |
| --- | --- |
| `packages-complete/` | Signed release/index, exact Debian packages and acquisition records. |
| `build-4/build.json`, `source-inputs.json`, `source-snapshot/` | Final construction identity, source bytes, binding header and root-admission input hashes. |
| `build-4/debian-init.patch`, `symbols.txt` | Exact upstream adaptation and discarded old PID1 implementation evidence. |
| `vm-3/result.json`, per-case serial/SSH/fixture logs | Successful normal and negative ARM64 executions. |
| `vm-3/source-snapshot/manifest.json` | Nine unchanged source files retained after VM-3, before provenance-only builder edits, including the reused VM harness. |
| `package-rejection/result.json` | Corrupted package refusal before construction. |
| `independent-review.json`, `final-audit.json` | Independent review binding and exact join between final artifacts and VM evidence. |

Raw boot identifiers, SSH material, filesystems, packages and compiled outputs
stay private. Existing native/F1 source, consumed artifacts, contracts and
concurrent work are not changed by this unit. A90 and S20+ were untouched.

## What follows

The userspace substitution is now demonstrated in a representative ARM64 VM.
The next useful unit is an H0 port of the **complete cold FYG8 platform/UFS
preparation** into this early-boot layout, with an explicit module/firmware
dependency inventory and evidence available before normal USB services. The
eight UFS modules alone are not the full preparation sequence. Device-node
events, driver readiness, thermal/power responsibilities and gadget ownership
remain target work; missing early records must not be treated as non-execution.

The operator has also requested later kernel modification/build/optimization
if needed. This result provides no reason to change the kernel merely to
replace custom PID1. Investigate a concrete target incompatibility or measured
cost before selecting kernel changes, and keep their proof separate from this
userspace result. The current physical native_data state remains P415's dirty
observation; this VM neither repairs it nor grants a writable phone boot.
