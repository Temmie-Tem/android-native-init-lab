# S22+ compact OBSERVED journal repair

Status: **H0 implementation and independent review PASS_GO; no device effects.**

P381's completed observation was passed in full to a 32 KiB journal writer.
That publication failed before the normal close/rollback segment, delaying
observation of the software Download return. Its existing durable-recovery path
used a compact OBSERVED record and completed one exact rollback with final
Android health. The consumed run remains NO_PROOF/CLOSED; this repair does not
change its records or promote v0.1.2. See the [rc.4 report](S22PLUS_FYG8_OUTPUT_MEMORY_RC4_H0_2026-09-10.md).

## Change and scope

The common `_finish_candidate_window` now computes its unchanged proof from the
full observation, then publishes only proof, bounded/departure state, observer
classification/acceptance, guard release state and the validated observer/guard
receipt hashes. Full evidence stays in the existing private receipts, raw
captures and live state. No truncation, raw deletion, bound increase or fallback
serialization is introduced. OBSERVED still precedes passive-trace sealing,
candidate_boot_ready and rollback. Recovery still derives facts from durable
receipts/state, never from a duplicated qualification body in the journal.

Independent consumer review found no reachable dependency on that full body.
The separately owned exploration/P335/P336 publication paths are unchanged.
The existing 32 KiB journal and 64 KiB eligible state/result limits are unchanged.
No target/device contract, C code, image, candidate or schema is changed.

## Validation

- Python compilation and all 77 common live-runner tests passed. The new test
  uses the real execute/recover, journal and result producers with fixture-backed
  transport/transfer/health. Its oversized nested command evidence is rejected
  by the original bounded writer, while compact normal closure succeeds.
- Four scenarios passed: normal close, cut before OBSERVED, cut after OBSERVED,
  and cut after ROLLBACK_FLASHED. Each closes with one candidate and one rollback,
  no observation restart during recovery, unchanged receipt bytes, exact receipt
  hash references, final health and bounded journal/result files.
- The immutable P381 observer receipt (65,160 bytes, SHA-256
  `1f0443ba8b955d7f1e7a241699cfce263252d44b3ebd81fb1da5ff9dad823fab`)
  also passed those four common-path scenarios as the large observation input.
  Its actual final state (55,309 bytes) and result (61,356 bytes) roundtripped
  through the existing 64 KiB writers. This is a host serialization/common-close
  replay with fixture-backed effects, not a new P381 run or a fresh live
  authentication/Download-timing qualification.
- Another 39 sidecar-lifecycle and goal-research tests passed. A broader 62-test
  core/P300 run had three errors in two historical P300 tests: missing FYG8
  source input and two subcases with an uninitialized private registry. The
  same three errors were reproduced using the unchanged HEAD runner. They occur
  before the modified close path; no safety check was bypassed or weakened.
- Independent review returned PASS_GO for the runner and regression test and
  independently repeated the four oversized normal/cut scenarios.

Private replay script, logs, prior review and the independent-review record are
under `workspace/private/outputs/s22plus_observed_journal_20260910/`. The reviewed
runner SHA-256 is
`a3dffc941d54f968659982b9e817f8fb413f6587f3656f4744c0a9fc5fe0ef53`.

Only the current foreground-goal review's f1_owner source pin is refreshed;
eight actions and eight other source roles are unchanged. No grant is opened
or renewed. Historical attended review, consumed source closures, prepared
records and journals remain unchanged. Any future attended capability must
qualify its actual current closure before use.

## Next bounded design

The [native baseline roundtrip design](../plans/S22PLUS_FYG8_NATIVE_BASELINE_ROUNDTRIP_DESIGN_2026-09-10.md)
is independently reviewed DESIGN_ONLY. It proposes native installation,
Download, restoration of the same exact native artifact, authenticated distinct
boot health, then Android cleanup for the initial qualification. Later adoption
as an ordinary rollback destination needs its own activated native-health
profile and authority. Persistent storage and RAM-file cleanup are separate.

No device was contacted in this unit. No native baseline has been selected,
installed or activated; no standing native lease follows. A90 and S20+ remain
outside scope.
