# S22+ FYG8 R4W1 Retained Init Witness Design

Date: 2026-07-12 KST  
Target: `SM-S906N/g0q/S906NKSS7FYG8`  
Scope: host-only design and source patch; no image, device contact, or flash

## Decision

R4W1 will add one GKI-side marker after `kernel_execve("/init", ...)` returns
success for PID 1. The marker is appended directly to the existing Samsung
`sec_log_buf` reserved-memory ring. No Samsung or Qualcomm security setting is
changed.

This is the narrowest mechanism that resolves the present ambiguity:

- positive marker: the rebuilt kernel accepted `/init` as PID 1;
- absent marker: remains `NO_PROOF`, never evidence that PID 1 did not run;
- invalid ring magic: refuse the RAM write and continue booting;
- witness failure: never panic, reboot, or alter a partition.

## Why This Channel

`CONFIG_PSTORE`, `CONFIG_PSTORE_RAM`, `CONFIG_PSTORE_CONSOLE`, and
`CONFIG_PSTORE_PMSG` are already enabled. V3439 bound a corrected ramoops
backend and still recovered no current-run frame, so merely enabling or
rebuilding ramoops is a retired hypothesis.

The exact FYG8 Samsung source instead shows that `sec_log_buf.ko`:

1. maps the `samsung,kernel_log_buf` reserved-memory region;
2. validates magic `0x4d474f4c` (`LOGM`);
3. snapshots the prior ring into `/proc/last_kmsg` before current logging;
4. appends current printk records through strategy 3 (`vh_logbuf`).

V3428R already proved that a build-bound marker in this ring survives an
attended RDX/Download transition and is recovered unchanged from the first
rollback boot's `/proc/last_kmsg`.

## Exact Memory Contract

All eleven generated FYG8 g0q DTBO revisions, `r01`, `r02`, and `r04` through
`r12`, encode the same node contract:

```text
compatible = "samsung,kernel_log_buf"
status = "okay"
memory-region = sec_debug_region_log@8001FF000
partial reg = <0x08 0x200000 0x00 0x200000>
strategy = 3
```

The witness therefore pins:

```text
physical base = 0x800200000
region size   = 0x00200000
header        = four u32 fields, then circular payload
magic         = 0x4d474f4c
```

The future live gate must additionally require exact stock DTBO SHA256
`97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`
before candidate flash. A different DTBO is a hard stop.

## Marker And Ordering

The R4W1-A marker is:

```text
[[S22R4W1|id=9ed5923b08c5eedbbdb0aaa6f6a5200c|phase=RAMDISK_EXEC_ACCEPTED|pid=1|path=/init]]
```

The marker is written with circular wrap handling. A write barrier precedes
the `idx` update, so a completed index publication cannot precede marker data.
`boot_cnt`, `magic`, and `prev_idx` remain unchanged. The code does not
initialize an invalid ring.

The build ID is unique to this kernel artifact. A live helper must prove it is
absent from the current `/proc/ap_klog` and `/proc/last_kmsg` before flashing.
Repeated copies after a boot loop are acceptable positive evidence for at
least one successful `/init` acceptance; malformed or foreign IDs are not.

## Source Delta

Patch:
`workspace/public/src/patches/s22plus_fyg8_r4w1_retained_init_witness.patch`

Only these exact source files may change:

1. `kernel_platform/common/init/main.c`
2. `kernel_platform/common/init/Kconfig`
3. `kernel_platform/common/arch/arm64/configs/gki_defconfig`

The only config delta is
`CONFIG_S22PLUS_FYG8_RETAINED_WITNESS=y`. RKP, KDP, UH, DEFEX, PROCA, FIVE,
KMI, module-signing, and LTO settings must remain unchanged.

## Host Gates

Before any live preparation:

1. Apply the patch only to a newly reconstructed clean FYG8 source tree whose
   three base files match pinned SHA256 identities.
2. Run the exact Full-LTO build with the R1 v3 provenance controls.
3. Require exact FYG8 banner and release.
4. Require the new marker exactly once in `Image` and `vmlinux`.
5. Require unchanged exported KMI names and CRCs for every stock module
   consumer; no new exported symbol is allowed.
6. Require config delta to contain only the witness option plus the already
   allowlisted absolute whitelist path normalization.
7. Measure the rebuilt `Image` size. If it exceeds the existing boot kernel
   slot by more than the 1,536-byte pre-ramdisk slack, stop and separately
   review a layout-preserving repack. Do not silently move the ramdisk.
8. Reproduce the patched Full-LTO `Image` from a second clean tree and require
   byte-identical SHA256.

## Live Ladder, Not Yet Authorized

R4W1-A, stock-Android positive control:

- one boot-only candidate flash;
- normal Android and Magisk root must return;
- `/proc/last_kmsg` must contain the exact marker;
- exact boot/DTBO/recovery identities must be collected;
- exact Magisk boot rollback is mandatory.

Only after R4W1-A passes may a separately built R4W1-B direct-PID1 candidate
use a different build ID. Its positive marker would prove the kernel accepted
that candidate `/init`; it would not by itself prove any later userspace
checkpoint or USB capability.

Each live rung requires a new SHA-pinned one-shot `AGENTS.md` exception and
fresh attended operator approval. This document and patch authorize no live
action.

## Verdict

`HOST_DESIGN_READY_FOR_STATIC_PATCH_VALIDATION; NO_LIVE_AUTHORIZATION`.
