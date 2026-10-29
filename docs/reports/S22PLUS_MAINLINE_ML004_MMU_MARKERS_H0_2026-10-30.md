# S22+ ML004: pre-MMU and early-C retained markers

Status: **READY_H0_AND_CURRENT_D0_NO_EXPERIMENT**.

This is the historical preparation checkpoint. ML004 was subsequently consumed
and closed healthy on 2026-10-30; the
[run record](S22PLUS_MAINLINE_ML004_RUN_2026-10-30.md) contains the physical
MMU/early-C proof and the still-unproved RAM PID1/USB result.

ML004 moves the two diagnostic slots proved by
[ML003](S22PLUS_MAINLINE_ML003_RUN_2026-10-30.md) to the next useful boot
boundaries: the start of `__primary_switch` before `__enable_mmu`, and
`setup_arch` after `early_ioremap_init` but before `setup_machine_fdt`.
Only S22+ SM-S906N/g0q/S906NKSS7FYG8 is selected. A90 and S20+ are untouched.
This preparation has no candidate transfer, control, grant or consumption.

Independent source/artifact review is **PASS_GO**, with no unresolved findings.
The production artifact and task consumers reopened the exact candidate. The
unchanged ordinary-terminal worker selected backend v13 and completed the
named fixed D0 readiness. Its raw Android health and durable readiness journal
were rederived within the existing freshness bound; process exit alone was not
accepted as proof. This point-in-time health observation must still satisfy
the existing freshness and effect-time checks when the operator approves.

| Preparation receipt | SHA-256 |
| --- | --- |
| Independent review | `cf5813923c1231eae4fa6d2b7a8c406848dfc42fd300444fbbe89463e7feef4a` |
| Mainline capability | `fde27a86dc718825e36b2ab6490b7dbb5cabc0d7a283dfab4f5860f74c538247` |
| Backend v13 | `fb98b85d02836edc6254f1d87cb162838bc2e5ce697e82dbf255903510c0f546` |
| Exact task | `2162d939eba4813a54b5a8cd7ca6c00f6699558239dc75c14b5818cef132c83f` |
| Current preapproval readiness | `495af81d2a07eb67832249fd0da0a70d78e35149fe1991a81d10fe06ace26bb1` |
| Pre-experiment summary | `6178658f6e02bdb5eebb3aaa479af4eac248ca28b3094ce5dc99752b31fb1084` |

No operator-approval record, grant or candidate operation exists at this
checkpoint. Device controls and partition transfers are zero. Prior review
receipts and ML003's consumed task, grant, journal and terminal remain intact.

## Behavior and proof limits

The schema-distinct V2 format replaces the V1 sites in this candidate. It
retains two 128-byte slots in the same fixed Samsung retained-log slice, the
unchanged 16-byte header, prefix-last commit and four-word stability check.
The first site uses the existing MMU-off assembly writer. The second uses the
kernel's early temporary mapping API with non-executable Normal-NC attributes,
then unmaps every successful mapping. It preserves the no-map reservation;
there is no filesystem, watchdog, peripheral or recovery change.

A valid pre-MMU frame proves that recording site, not MMU activation. A valid
early-C frame proves the named MMU-enabled `setup_arch` path and earlier entry
to `start_kernel`. Neither proves subsequent FDT setup, userspace, USB, one
shared boot, the last attempt or reset cause. Missing frames remain unknown.
The unchanged RAM PID1/USB verdict and original-A return remain separate.
V1 records and consumed ML003 artifacts retain their original interpretation.

## Validation

The fresh private source tree differs from the pinned unmarked preparation
only at `head.S`, `setup.c` and the new generated header. Config and g0q DTB
bytes are unchanged. The actual kernel, loader and physical initramfs are
freshly bound; the initramfs has its own new candidate identity and key.

| Check | Result |
| --- | --- |
| Actual linked pre-MMU assembly | 171 cases, including 135 incomplete-store cuts, register preservation, bounds, state rejection and header changes |
| Actual linked early-C instructions | 158 cases, including 135 incomplete-store cuts, mapping failures, page-boundary placement and cleanup; system-register results and mapping calls are explicit fixtures |
| Actual pre-MMU exception levels | EL1/EL2 recording and EL3 refusal |
| Exact kernel through real MMU and early mapping APIs | 11 QEMU cases; real EL1 and EL2 success, cross-page slot, invalid header/index, exhausted first/second mapping and all four header-word mutations; no leaked mapping slots |
| Complete loader | 20 cases and 1,051 direct-copy cases; actual EL1/EL2 entry and EL3 refusal |
| Exact kernel with separately marked VM PID1 | Authenticated RAM PID1 observer passed |
| Repeated boot/AP packaging | Byte-identical copies, only `boot.img.lz4`, retained original-A outer envelope |
| Mainline/marker/collector/terminal suite | 67 tests passed, including V1/V2 decoding and closed-owner recovery boundaries |
| Stable ordinary-terminal connector suite | 78 tests passed; its runtime and dispatch code are unchanged |

The C fixture preserves the compiled stack-protector prologue and initializes
`SP_EL0` to the mapped `init_task`. The QEMU fixture was corrected to omit an
unneeded default NIC ROM, compare virtual addresses as exact 64-bit patterns,
and distinguish actual EL1 from the kernel's VHE EL2 path. Failed fixture logs
remain private. These corrections did not rebuild or alter the candidate.
QEMU does not establish physical cache coherency, retention or boot success.

Applicable past-failure checks: ABI confirms actual ARM64 mapping and canary
behavior; WIRE/SEMANTIC keep positive stage occurrence separate from USB and
recovery; ROUTE/PERSIST exercise real decoder/raw-capture and closed-owner
paths; ARTIFACT joins actual linked frames and boot/AP contents; HOST checks
the ordinary-terminal source and dispatch tests. RETURN retains the original
one-shot A recovery and forbids replay after uncertainty. AUDIT preserves old
evidence. No IO transport or DISPLAY implementation changed.

Private evidence is under
`workspace/private/outputs/s22plus-mainline-ml004-h0-20261030-1/`, including
the source comparison, compiler logs, linked-code tests, QEMU logs and raw
memory fixtures, repeated packages and focused test logs. The
[mainline policy](../operations/S22PLUS_MAINLINE_RAM_V1.md) still requires
source-bound independent review, production admission, current fixed D0
readiness, an exact returned finite approval and actual attended recovery
before the experiment. Review and current readiness are complete; the exact
returned approval and actual attendance remain required.
