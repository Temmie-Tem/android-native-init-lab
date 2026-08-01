# S22+ Target Contract Refactor v1 H0 Report

Date: `2026-08-02`

Verdict: `PASS_S22PLUS_TARGET_CONTRACT_REFACTOR_V1_H0`

## Scope

This was a host-only policy refactor. No connected read, device command,
reboot, Odin invocation, payload transfer, or flash occurred. It grants no D0,
D1, or F1 authority.

The refactor separates stable repository invariants from changing target state:

- `AGENTS.md` now contains common permanent boundaries, precedence, and a
  binding target registry.
- `docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md` contains the stable
  S22+ H0/D0/D1/F1 and Rule-7 specializations.
- `GOAL.md` remains the current S22+ frontier and authority-state ledger, not a
  source of device authority.
- `docs/operations/DEVICE_ACTION_RISK_TIERS.md` now recognizes the selected
  binding target contract in its precedence statement.

Unrelated pre-existing A90 changes in `tests/test_a90ctl.py` and
`workspace/public/src/scripts/revalidation/a90ctl.py` were not edited or staged.

## Preserved Common Boundaries

The ordinary payload remains boot-only. The complete forbidden-partition list
and forbidden raw-action paragraph were compared byte-for-byte with the
pre-refactor `AGENTS.md` and remained identical. Exact rollback availability,
target isolation, candidate no-replay, durable-journal recovery, private
evidence handling, and post-device-session immediate stop remain binding.

The existing A90 reviewed attended pre-handoff channel exception remains a
narrow common delegation and is bound through the A90 registry row. The S22+
contract does not select that exception.

## S22+ Rule-7 Specialization

Before a connected device command or a positively proven Odin/device session
starts, the first novel material host-only failure:

1. stops and preserves the failed invocation;
2. permits one scoped H0 diagnosis and repair;
3. requires focused validation against the real input or a representative
   fixture; and
4. permits one corrected execution of that bounded unit.

The same material failure a second time stops the line. Renaming or moving the
same causal failure does not make it novel, and the rule never permits
retry-until-pass behavior or device action.

A host rejection or local parser failure is Rule-7 eligible only when it is
positively proven to precede device-session start. Tool-process creation alone
does not imply device contact. Once a device command, Download handoff, or
device session begins, unexplained failure is an immediate stop and only the
already-authorized exact rollback may continue.

## Validation

The host checks proved:

- every newly referenced policy path exists;
- the boot-only forbidden-partition paragraph is byte-identical to the old
  common contract;
- the forbidden raw-action paragraph is byte-identical to the old common
  contract;
- `AGENTS.md` contains no P2.x live posture or campaign checkpoint values;
- the S22+ target contract contains no live approval token;
- `GOAL.md` remains below its 800-line archive-review threshold and
  `GOAL_A90.md` remains at, but not above, that threshold; and
- `git diff --check` passes.

## Independent Safety Review

One independent reviewer examined only the changed policy closure. The first
review found one blocking wording contradiction: the Rule-7 section originally
ended repair authority at transfer-tool invocation while the F1 section treated
a pre-device Odin local-parser failure as repairable.

The wording was corrected to use one boundary everywhere: the positively
proven start or report of a device session, with tool-process creation alone
explicitly excluded. The reviewer rechecked that exact change and returned
`PASS`. No other weakening of boot-only, forbidden-action, rollback, no-replay,
private-evidence, target-isolation, or no-live-authority protections was found.

## Consequence for Existing Requests

Any unconsumed S22+ request that binds the pre-refactor policy commit is stale
after this policy commit. Candidate artifacts and source identity are not
changed by this H0 refactor, but a future request must bind the new policy
commit and exact execution closure before any connected or live action.
