# S22+ FYG8 R3C1 Live Gate Source Ready

Date: 2026-07-12 KST

Target: `SM-S906N/g0q/S906NKSS7FYG8`

Verdict: `PASS_R3C1_SOURCE_READY_PENDING_FRESH_ATTENDED_APPROVAL`

Subsequent status: the attended run completed with
`PASS_R3C1_UNPATCHED_REBUILT_KERNEL_VIABLE_AND_ROLLED_BACK`; this source-ready
state is superseded by
`docs/reports/S22PLUS_FYG8_R3C1_LIVE_RESULT_2026-07-12.md`.

No reboot, Download transition, candidate transfer, or partition write occurred
in this unit. Device contact was limited to one connected read-only baseline
after the full host-only gate passed. The approval supplied before these gates
is intentionally not retained or consumed.

## Implemented Surface

- live helper:
  `workspace/public/src/scripts/revalidation/s22plus_fyg8_r3c1_live_gate.py`
- helper SHA256:
  `2e6bf83733685288d0289d175c9639858ae0d3c5f2fe06f83737bceb186a6eb1`
- focused test SHA256:
  `14b3d038c6e5484eca28ef8fbf4fe0e8e6a7176b2ebbce659f6ef142382d23cd`
- policy draft:
  `docs/operations/S22PLUS_FYG8_R3C1_AGENTS_EXCEPTION_DRAFT_2026-07-12.md`
- binding state:
  `S22PLUS_FYG8_R3C1_POLICY_STATE=PENDING_OPERATOR_APPROVAL`
- live acknowledgement, not yet valid:
  `S22PLUS-FYG8-R3C1-UNPATCHED-KERNEL-LIVE`
- emergency acknowledgement for an already-started run:
  `S22PLUS-FYG8-R3C1-MAGISK-ROLLBACK-FROM-DOWNLOAD`

The helper imports the reviewed R3C0 transport and final-observation primitives
but has distinct R3C1 artifact verification, policy state, acknowledgement
tokens, result classes, run names, and consumed-state path.

## Exact Pins

| Item | SHA256 |
| --- | --- |
| R3C1 raw boot | `e1f0be9933e9c76d881a2cc39c0431bf54930ee0f216f55de4d7a166a60d120c` |
| R3C1 boot-only AP | `023d7780e11363bd152900e28279233a0fd66ce8dd8902417d23eb781f613fb4` |
| R3C1 manifest | `2596b5f1c6a8fa88d8ee75224c8a039764c67453875789744a7087db2fb97bb0` |
| R3C1 builder | `11f6e270ba5c63b498b2072573bb8a870f6dd031b5fb407268b6d39c55577596` |
| R3 static checker | `917b12f82dc5525b84cf2627379a80e49d921b6c33ca79fe3fc5c6a9ece6a514` |
| Magisk rollback AP | `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` |
| stock cleanup AP | `2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94` |
| Odin | `6754aa54f2abe6e99ece32414cd34c8b23b28dbddde537a33203036813637c3b` |

The live preflight reruns `PASS_R3C1_STATIC_CONTRACT`, including full FYG8
firmware evidence, exact R3C0/R2 inputs, intentional stale AVB, kernel-only
delta, AP/LZ4 roundtrip, and both rollback chains.

## Safety Properties

- ACTIVE requires an exact whole-line sentinel; descriptive prose and the
  PENDING line cannot activate it.
- live and rollback modes fail before device contact while policy is inactive.
- candidate AP must contain exactly `boot.img.lz4`.
- candidate flash start durably consumes the R3C1-specific one-shot state before
  Odin runs.
- candidate PASS requires exact FYG8 identity, boot complete, stopped boot
  animation, exact `uname -r` and `/proc/version`, orange verified-boot state,
  and three stable samples.
- candidate root is not required.
- Magisk rollback is mandatory after candidate PASS or failure.
- stock cleanup remains non-PASS with nonzero exit code.
- final PASS requires exact Magisk boot, root, stock DTBO/recovery, and no Odin
  endpoint.
- timeline uses only the standard eight `events:[{name,timestamp_utc}]` phases.
- R3C1 state and acknowledgement tokens are distinct from retired R3C0.

## Validation

- `py_compile`: PASS
- focused and related tests: `54/54` PASS
- offline gate: `PASS_R3C1_STATIC_CONTRACT`, device contact false
- connected dry-run: exact Magisk baseline, policy inactive, one-shot unconsumed,
  no Odin endpoint, device writes false
- `git diff --check`: PASS

## Independent Review

Claude Opus current-session usage was `76% -> 92%`, reset 2026-07-13 01:50
KST. Review verdict: **GO**, no blocking finding. It independently verified all
on-disk SHA pins, exact whole-line policy gating, candidate predicate
achievability against the timestamp-correct R2 Image, separate one-shot state,
mandatory rollback, non-PASS stock cleanup, and complete timeline paths.

Accepted LOW residuals:

- emergency `--rollback-from-download` still performs full candidate/static
  artifact verification first; missing/corrupt candidate files would require
  attended manual Odin/TWRP use of the already pinned Magisk AP;
- post-run editing of the draft state would break later offline checks;
- several negative manifest/static-check and no-rollback-endpoint paths are
  covered by source review rather than dedicated unit tests;
- wrapper source scanning does not independently re-audit the imported R3C0/M3
  flash primitives, which were already reviewed and live-proven.

All pinned candidate, checker, rollback, and policy files currently exist, so
the emergency-verification dependency is bounded and accepted for this attended
one-shot design.

## Closed Gate

The required fresh approval was subsequently supplied, the exact helper ran
once, and the one-shot policy was retired after candidate PASS and verified
Magisk rollback. This exception cannot be reactivated or reused.
