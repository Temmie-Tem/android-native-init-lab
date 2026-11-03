# LA003 physical prefix witness — consumed and closed healthy

Result: **PASS_LOADER_FYG8_ANDROID / ANDROID_CLOSED_HEALTHY**.
The current candidate boot proves execution of the fixed mainline
Image-header/`primary_entry` prefix and its return to the resident loader,
followed by exact vendor Android. It does not prove a complete mainline boot.

The operator returned the exact one-operation, 1800-second attended approval
and confirmed physical Download availability. Fresh fixed preapproval health
passed. The [qualified candidate](S22PLUS_LOADER_PREFIX_LA003_H0_2026-11-03.md),
loader-prefix capability, backend V25 and stable worker remained unchanged.
The candidate and original A each transferred exactly once. Both normal
Android-to-Download controls completed; no physical recovery command or
transfer retry was needed.

## Current-boot observations

The sealed 256-byte FDT report is `RETURNED`. Its returned entry PC matches the
actual mainline Image's `primary_entry`, the return cookie matches, and the
before/returned CPU samples agree: EL1, little-endian, with MMU, data cache and
instruction cache off. This bounded prefix returns before `record_mmu_state`;
it does not execute later kernel initialization or PID 1.

The external before/after LOGM header samples at both sites are equal. The
post-call comparisons at the loader and kernel slots both have zero mismatched
bytes. These are static candidate-frame comparisons. The unchanged V1 writer
returns no status, and a frame could predate the current attempt; this result
does not prove a current-attempt store/commit, absence of intervening writes,
reset retention or a reason for the missing ML012–ML016 records.

The first complete candidate Android proof, post-report proof and fresh
pre-Download proof share one observed boot ID and validated USB generation.
The exact candidate boot digest, original supporting partition digests,
root, vendor kernel release and loader-created marker all pass. These three
brackets do not establish continuity before the earliest complete observation.
This two-Image carrier and live vendor-FDT argument are distinct from the
historical full-mainline boot path.

## Original-A return and health

The normal candidate Download command and original-A transfer completed.
The first final-health attempt then failed while acquiring properties:
`02-health.capture.json` returned `error: closed`, with empty stdout. Its raw
failure remains preserved and supplies no return boot identity or health.

The original owner's single health-only continuation passed all final checks
and closed the task. No transfer or control was repeated. The final original-A
boot ID differs from the observed candidate boot; continuity across the failed
empty properties read is unknown. ADB failure cause, earlier unseen boots and
automatic failure recovery remain unproved.

| Canonical event | Seconds from original grant |
| --- | ---: |
| live_session_start | 0.000 |
| candidate_flash_start | 43.494 |
| candidate_flash_done | 45.393 |
| candidate_boot_ready | 166.984 |
| rollback_flash_start | 182.095 |
| rollback_flash_done | 183.666 |
| rollback_boot_ready | 332.694 |
| live_session_end | 332.694 |

## Offline verification and closure

An offline audit rederived the production observation and terminal with device
acquisition blocked, independently reconstructed both V1 frames and decoded
the report bytes, and checked all 936 raw captures. The one failed capture is
the preserved initial final-health read. All 65 frozen execution sources and
29 protected proof/journal files retain their identities.

The task and grant are consumed, final original-A health is proved, and no F1
owner remains. The separate mainline capability was not renewed by the
loader-prefix review. No successor or new grant is armed. A90, S20+ and
unrelated work remain untouched. Mainline RAM PID1/USB is still the next
functional objective; this result supplies only the stated early-prefix proof.
