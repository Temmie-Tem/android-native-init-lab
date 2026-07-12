# S22+ FYG8 R3C0 Live Gate Source Ready

Date: 2026-07-12 KST

Target: `SM-S906N/g0q/S906NKSS7FYG8`

Verdict: `PASS_SOURCE_READY_PENDING_FRESH_ATTENDED_APPROVAL`

Subsequent status: the attended live run completed with
`PASS_R3C0_NORMALIZED_STOCK_CARRIER_AND_ROLLED_BACK`; this source-ready state is
superseded by
`docs/reports/S22PLUS_FYG8_R3C0_LIVE_RESULT_2026-07-12.md`.

No candidate transfer, Download transition, reboot, or partition write occurred
in this unit. Device contact was limited to a connected read-only baseline
check after the host-only gate passed.

## Implemented Surface

- live helper:
  `workspace/public/src/scripts/revalidation/s22plus_fyg8_r3c0_live_gate.py`
- helper SHA256:
  `921800725fa73b7d37fd8d3c46369d0015ab4a8e366111e079b5f7ce674246e3`
- focused tests: `tests/test_s22plus_fyg8_r3c0_live_gate.py`
- inactive policy draft:
  `docs/operations/S22PLUS_FYG8_R3C0_AGENTS_EXCEPTION_DRAFT_2026-07-12.md`
- binding policy state:
  `S22PLUS_FYG8_R3C0_POLICY_STATE=PENDING_OPERATOR_APPROVAL`

The helper supports four mutually exclusive modes:

1. `--offline-check`: hashes all pinned artifacts, reruns the exact R3 checker,
   verifies the policy draft, and performs no device contact.
2. `--connected-dry-run`: repeats the host gate, reads the exact Android/Magisk
   baseline, and requires no Odin endpoint. It performs no device write.
3. `--live`: requires a whole-line ACTIVE policy sentinel, exact acknowledgement,
   an unconsumed one-shot state, and every preflight gate before requesting
   Download mode.
4. `--rollback-from-download`: remains available to restore the pinned Magisk
   boot after an already-started run, including after one-shot consumption.

## Pinned Artifacts

| Artifact | SHA256 |
| --- | --- |
| R3C0 raw boot | `384efeb0f81534cbfaf3643f42e34fb6e01fe6f0b6bf80139a047a1f9a71f29f` |
| R3C0 boot-only AP | `8f2b16d3ee8932ff927e06fee8956f975ec3f9e5cc0ef16337e00ad5108d3c00` |
| R3C0 manifest | `febffce465ea639d4d4751170bf280ae148ca3431f560aae6ecd8ea08f12ced0` |
| Magisk rollback AP | `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` |
| stock cleanup AP | `2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94` |
| R3 static checker | `917b12f82dc5525b84cf2627379a80e49d921b6c33ca79fe3fc5c6a9ece6a514` |
| Odin 4 | `6754aa54f2abe6e99ece32414cd34c8b23b28dbddde537a33203036813637c3b` |

The AP contains exactly `boot.img.lz4`. The independent static checker returned
`PASS_R3C0_STATIC_CONTRACT`, including full FYG8 stock firmware evidence and
both rollback chains.

## Connected Baseline

The read-only connected dry-run proved:

- model/device/bootloader/incremental exact;
- `sys.boot_completed=1` and `init.svc.bootanim=stopped`;
- verified-boot state `orange`;
- Magisk `uid=0(root)`;
- current boot SHA256
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`;
- DTBO SHA256
  `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`;
- recovery SHA256
  `93fac06ca79bf4b365b25a8d49902bc41aba112ea253c30880c90e314d7895d4`;
- no Odin endpoint;
- one-shot consumed state `false`;
- policy active state `false`.

## Safety Closure

The first external adversarial review returned NO-GO on three substantive
issues:

1. the pending `AGENTS.md` prose contained the ACTIVE sentinel and policy
   activation depended accidentally on line wrapping;
2. rollback-only stock cleanup returned process exit code 0;
3. one-shot retirement was documentary rather than enforced.

The corrected helper now:

- recognizes ACTIVE only as an exact whole-line state and leaves the binding
  policy at a distinct PENDING line;
- propagates stock cleanup as exit code 30;
- durably writes
  `workspace/private/state/s22plus_fyg8_r3c0_live_exception_consumed.json` at
  `candidate_flash_start` and refuses later candidate runs;
- keeps rollback-only recovery available after consumption;
- completes all eight timeline events with explicit no-flash semantics if the
  bounded rollback endpoint wait closes;
- classifies PASS only after a stable candidate Android milestone and exact
  Magisk rollback with no remaining Odin endpoint.

The same Claude Opus session re-reviewed only those fixes and returned GO with
no remaining blocker. Residual attended risk is explicit: an unexpected host
exception after candidate transfer can require the operator to enter Download
mode and invoke the rollback-only path. This does not authorize unattended use.

## Validation

- `py_compile`: PASS
- focused and related unit tests: `35/35` PASS
- `git diff --check`: PASS before final documentation update
- offline helper gate: PASS, device contact `false`
- connected dry-run: PASS, device writes `false`
- external adversarial review round 1: NO-GO, findings fixed
- external adversarial review round 2: GO
- Claude subscription usage: 23% before first review, 46% after first review,
  58% after fix re-review; reset shown as 2026-07-13 01:50 KST

## Closed Gate

The required attended approval was subsequently supplied, the exact helper ran
once, and the one-shot policy was retired after candidate PASS and verified
Magisk rollback. This exception cannot be reactivated or reused. R3C1 requires
a separate host artifact, review, policy, and approval.
