# S22+ ML016: fresh loader and kernel-entry calibration

Status: **H0 qualified, independently reviewed and fixed preapproval D0 passed;
exact finite attended approval pending**.

The next bounded candidate reuses the existing V1 format: one 128-byte
header-preserving record at loader handoff and one at mainline `primary_entry`,
before `record_mmu_state`. It keeps ML015's exact corrected DTB and kernel
configuration, including GPIO reservations 36..39, 50 and 93. A clean unmarked
source base supplies a fresh candidate/key, initramfs, kernel and boot package.
V2's pre-MMU/early-C sites and V9/V10 hooks are absent.

## Selection and evidence limits

Two-round Claude/Argon discussion produced different recommendations. Claude
favored V1's point outside the mainline kernel; Argon proposed a conditional
`regulator_ignore_unused` variant. Source checks found no specific affected
unused rail or failure mechanism, so this unit selects the existing V1
observation and retains the configuration. Thermal, watchdog, regulator,
storage and driver behavior are unchanged. A dual-kernel live witness remains
an unselected H0 idea with substantial CPU-state, ABI and placement work.

[LA002](S22PLUS_LOADER_LOGM_LA002_RUN_2026-11-03.md) established a positive
write/read control on the healthy vendor path. It did not establish the CPU
or header state of ML015 or retention after its failed mainline attempt.
V1 can add a fresh positive loader or earliest-kernel observation; a zero
remains unresolved. Its information value does not depend on assigning a
cause to missing records.

| Retained V1 result | Bounded interpretation |
| --- | --- |
| Loader and kernel entry | Each point occurred at least once in this candidate's attempts and its frame reached collection. |
| Loader only | Loader occurrence is observed; kernel entry remains unproved. |
| Kernel entry only | Kernel-entry occurrence is observed; loader occurrence remains unproved. |
| Neither | Neither point is proved in this candidate. |

Static frames need not share a boot or invocation. A positive neither proves
a later return nor localizes a stop. Results cannot explain ML015's absence,
prove the GPIO correction's effect, establish general reset retention or
substitute for authenticated RAM-userspace PID1/USB. Earlier physical records
retain their own scope. Another zero would add no basis for an unchanged
repetition; subsequent work should seek distinct evidence.

## Low-cost checks and preparation

The exact final ML004, ML011, ML012 and ML015 DTBs already protect the entire
Samsung log carve-out with active, non-reusable `no-map` coverage. The USB path
already has the single HS PHY and its three supplies. The existing log-content
census and geometry comparison do not provide boot chronology or a missing
reservation/USB3-dependency defect. Those proposed fixes were rejected.

The exact retained ML015 assembly and C writers were exercised with LA002's
observed four-word header. The assembly fixture injects LA002's sampled CPU
values; the C fixture adds a synthetic MMU-on state and mocks mapping APIs.
Both write the expected frame, and the unchanged extracted Samsung C consumer
and production HMAC decoder agree. The retained ML003 V1 loader/kernel writers
also pass the observed-header cases with register preservation. These are
fixture results, not the physical mainline state or a new candidate's
qualification.

Two fixture setup/checker errors were retained: a durable-record helper was
inappropriately used for hard-linked source artifacts, and a stage-name result
was compared to numeric IDs. Source/artifact byte hashes and the real decoder
schema corrected those assumptions. The complete saved first-stage RAM was
revalidated without repeating that producer. Neither error changed device
code or caused device access.

The previous mainline capability admission rejected two stale source pins
following LA002: its loader-only target clause and selected-loader source-file
list. Their diff does not change the mainline effect graph. The new independently
reviewed capability receipt and backend V24 bind current sources and the
new receipt reference; historical reviews and consumed owners remain intact.
The stable worker, complete Android health, physical original-A recovery,
finite attended grant and no-replay rules remain unchanged.
The shared reference change also makes the retained LA002 loader capability
stale for a prospective loader task. Backend V24 does not renew that separate
capability; closed LA002 evidence and its original source snapshot remain valid.

Fresh artifact qualification passes:

- The fresh ARM64 Image uses ML015's exact configuration and DTB. The five
  clean source files match ML015's uninstrumented base; only V1's assembly
  entry hook is added, with no V2 or later C/hook instrumentation.
- Actual linked marker execution passes 342 guarded-write/interruption cases
  and six real-EL cases. EL1/EL2 commit and EL3 skips; argument registers,
  header and out-of-slot bytes are preserved.
- The loader passes 20 instruction cases, 1,051 aligned-copy cases and three
  real-EL entry cases. Two independently packaged boot/AP outputs match.
- Fresh RAM-userspace PID1 VM authentication and an offline raw-evidence
  recheck pass. Sixteen mainline terminal tests and touched-Python compilation
  pass. These are H0 results, with physical boot/cache/retention unproved.

The final review packet freezes 93 source files and 395 artifact/raw-evidence
pins, including the exact producer ELF/Image and complete qualification logs.
Final independent review is **PASS_GO**, with no remaining findings. It confirms
the actual call sites and source parity, exact package/VM joins, 16 representative
writer cases and four writer-to-Samsung-C-consumer joins. Two reviewer-only
historical-schema/package-comparison errors and their corrected checks remain
in the private review evidence; neither changed the candidate or touched a
device. The final receipt SHA-256 is
`df2a755b4d468cf2f713e8a79f2f0d449ba719e69ee77d34d28b5ef82548388e`.

The unmocked production image/task consumer passes. Backend V24 is selected
and the connected stable worker accepts its unchanged worker-source subset.
A preceding status request correctly rejected the then-stale backend source
binding without device access. One fixed preapproval D0 passed: all seven raw
health reads rederive exact healthy original A, current identity/digests and
task readiness, with no unresolved F1 owner. No approval, grant, candidate
control or partition transfer has occurred. The generated exact one-operation
approval, attendance through recovery/final health and usable physical Download
remain required. A later grant must still pass readiness freshness.
Applicable past-failure rows are ABI, ARTIFACT, WIRE, SEMANTIC and RETURN:
actual call-site/register behavior, fresh producer/consumer identity,
positive-only interpretation and independent original-A closure.

Private source/artifact evidence is retained under
`workspace/private/outputs/s22plus-mainline-ml016-h0-20261103-1/`; discussion,
usage accounting and reused-artifact checks are in the sibling
`s22plus-la002-next-discussion-20261103-1/` tree. A90 and S20+ are untouched.
