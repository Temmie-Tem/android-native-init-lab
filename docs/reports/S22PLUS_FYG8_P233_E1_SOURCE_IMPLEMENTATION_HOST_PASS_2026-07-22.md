# S22+ FYG8 P2.33 compact E1 source implementation host pass

Date: 2026-07-22 KST
Tier: H0
Status: `PASS_P233_E1_SOURCE_IMPLEMENTATION_HOST_ONLY`
Device contact: none
Live authority: none

## Result

P2.33 implements the P2.32 45-byte compact E1A/E1B design as source and
host-side validation only:

- one default-disabled FYG8 kernel patch derived from the P2.25 target guard
  and cache-flush path;
- one version-2 checkpoint client;
- one profile-selectable runtime wrapper reusing the pinned R4W1-E mount,
  child, module, and park primitives;
- one raw multiboot decoder and opt-in Process v2 evidence kind; and
- one source checker covering clean patch application, linked userspace,
  terminal dominance, and every reachable compact record.

The patch changes only `init/Kconfig` and `init/main.c`. It does not enable the
new option in `gki_defconfig`. Empty, malformed, or zero run identity, invalid
profile, malformed, zero, or family-colliding UNSAT tag, target mismatch,
header change, request mismatch, CRC failure, sequence violation, or
evidence-family collision fails closed. Candidate-specific UNSAT derivation is
not claimed here and remains a P2.34 artifact check.

## Static Evidence

- The patch clean-applies to the source-matched FYG8 tree.
- The long/header/slot/UNSAT/request sizes remain 45/25/10/24/32 bytes.
- The retained update clears and flushes the inactive CRC, writes and flushes
  the six-byte body, rechecks the frozen header and prior slot, writes the CRC
  last, flushes it, and performs exact readback before advancing RAM state.
- E1A links as a 6,608-byte static AArch64 ELF with zero watchdog-module file
  names or module-loader symbol.
- E1B links as a 68,328-byte static AArch64 ELF with each exact watchdog-module
  file name present once and the module-loader symbol retained.
- The pinned child links as a 1,384-byte static AArch64 ELF with its exact token.
- All 90,114 reachable E1A/E1B slot variants have nonzero CRC32 and no related
  evidence-family collision for deterministic non-model source-check IDs. The
  checker constructs the actual adjacent old/new A/B slot combinations rather
  than testing each slot against ENTRY alone.
- Focused implementation and adapter tests pass, including malformed records,
  dirty baseline, mixed valid boot states, active-slot item preservation,
  model-ID refusal, and deliberate source-only Process v2 refusal through the
  complete `verify_bundle()` path.

## Independent Review

The first independent review returned NO-GO after finding that E1B did not
preserve the active watchdog slot's nonzero item index. That would have made
the next request fail `-ESTALE`. The fix stores and reconstructs the exact item
index, renames a local identifier that could collide with the kernel `current`
macro, and adds a mutation regression. The same review also caused adjacent
A/B record validation, non-model source-check identities, sanitized compiler
environment, and full runner refusal coverage to be added. A follow-up review
of this corrected closure found no remaining issue and returned GO for this H0
source-only commit. Candidate-specific build and physical persistence risks
remain explicitly deferred to P2.34.

## Process v2 Boundary

`retained_e1_latest_stage_multiboot_after_rollback` is allowlisted only as a
typed source implementation. Its decoder and clean-baseline path are usable in
H0 tests, but `verify_offline_contract()` deliberately rejects it because no
candidate-bound run manifest, static AP closure, kernel build, boot image, or
candidate AP exists. This prevents P2.33 from becoming live-ready accidentally.

No kernel was built, no image or manifest was created, no device was contacted,
and no prior live verdict changed.

## Next Boundary

P2.34 may create one candidate-specific host build and offline artifact closure:
derive a non-model run ID and UNSAT tag, bind the same profile into kernel and
userspace, perform one clean Full-LTO kernel build, link the exact runtime and
child, package one boot-only AP, and add the candidate-bound offline verifier.
It remains H0 until a later connected D0 and fresh F1 approval.
