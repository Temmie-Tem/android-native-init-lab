# S22+ FYG8 R4W1-A A8 Adversarial MUST-FIX Closure

Date: 2026-07-13 KST

Target: `SM-S906N/g0q/S906NKSS7FYG8`

Scope: host-only source, test, artifact, and policy-draft review. No device
contact, USB enumeration, ADB, Odin invocation, reboot, Download transition,
consumed-state creation in the repository, or flash occurred.

## Independent Review Result

Two independent read-only reviewers examined commit `74562c6d` and both returned
`GO_WITH_MUST_FIX` before policy binding. Their load-bearing findings were:

1. the CLI allowed one candidate sample even though the proposed policy requires
   exactly three, and PASS did not directly require transfer success plus three
   samples;
2. `TimeoutExpired` or `OSError` during candidate transfer could escape after
   one-shot consumption without entering mandatory rollback;
3. rollback consumed-state validation did not reopen its timestamp, run
   directory, or target run result;
4. several failure exits could leave a partial timeline instead of all eight
   canonical events;
5. the real-repository activation test derived its expected value from
   `policy_active()` itself;
6. candidate observation accepted a bound above the proposed 300-second limit.

No reviewer authorized activation or device work.

## Closure

The successor helper now:

- requires exactly three samples and directly requires candidate transfer,
  three samples, and the exact stream marker proof for PASS;
- limits candidate observation to at most 300 seconds;
- catches `GateError`, `OSError`, and `subprocess.SubprocessError` around the
  consumed candidate transfer and continues into the mandatory rollback state
  machine;
- suppresses candidate transfer if consumed-state creation does not complete
  cleanly, while treating an already-created state as consumed for recovery;
- validates strict UTC consumption time, a non-symlink relative run directory
  beneath `workspace/private/runs`, and the bound live result schema, mode, and
  target before rollback-from-download;
- completes the canonical eight-event timeline for pre-consumption failures,
  ambiguous or absent rollback targets, rollback transfer failures, and rollback
  health failures; and
- preserves result-side semantics for phases in which no transfer occurred.

Focused tests independently derive the exact ACTIVE whole-line condition and
every required pin from `AGENTS.md`. New negative/integration cases cover bad
consumption timestamps and paths, mismatched target results, CLI weakening,
pre-consumption timeline completion, candidate-transfer `OSError` followed by
actual mandatory rollback, and rollback-target failure timeline completion.

## Exact Pins

- successor helper SHA256:
  `1cdd18ad1cbd3f75ecdd017cdb25b9e053e9f475e38812be446a0b18845e9ad5`;
- focused test SHA256:
  `e07447e570c843d92d4d75823340580939354477376cce13e328b1fc348654d0`;
- inactive policy draft SHA256:
  `13110c68bd9874fb5385246d2bd3e4c544a34c89ef25baefee66184104f9a42e`.

The A4 qualification and all candidate, marker-oracle, Magisk rollback, stock
cleanup, checker, transport, builder, manifest, Odin, and firmware-evidence pins
remain unchanged.

## Validation

- focused successor tests: `22/22 PASS`;
- complete R4W1-family tests: `111/111 PASS`;
- Python compile check: PASS;
- `git diff --check`: PASS;
- offline gate: `PASS_R4W1A_STREAM_CANDIDATE_OFFLINE_CHECK`;
- offline policy state: `DRAFT_INACTIVE`, `active=false`;
- candidate consumed: `false`;
- offline device contact, device write, and flash: all `false`.

`ruff` was not available on this host and was not installed as part of this
bounded unit.

## Decision

The first adversarial review's MUST-FIX set is closed in source and tests, but
this report is not a binding verdict. `AGENTS.md` remains unchanged and contains
no R4W1-A stream-candidate ACTIVE sentinel. The next gate is delta re-review of
this exact checkpoint by both independent reviewers. Only a clean binding
verdict may permit a separate exact policy commit; any eventual live run still
requires fresh attended operator approval.
