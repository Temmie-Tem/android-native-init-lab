# S22+ FYG8 R4W1-A A11 Live Policy Bound And Ready For Approval

Date: 2026-07-13 KST

Target: `SM-S906N/g0q/S906NKSS7FYG8`

Binding commit: `72921c06`

Scope: host-only policy binding and validation. No device contact, USB
enumeration, ADB, Odin invocation, reboot, Download transition, consumed-state
creation, candidate transfer, rollback transfer, or flash occurred.

## Binding

The independently reviewed R4W1-A stream-candidate clause is now present in
`AGENTS.md` with exactly one whole-line sentinel:

`S22PLUS_FYG8_R4W1A_STREAM_CANDIDATE_POLICY_STATE=ACTIVE`

The clause binds the reviewed helper, focused test, A4 qualification, candidate
boot/AP, marker oracle, Magisk rollback AP, stock cleanup AP, firmware evidence,
one-shot consumption, exact stream proof, mandatory rollback, canonical
timeline, and absolute exclusions. It explicitly permits only the boot
partition and still requires a fresh attended acknowledgement before any device
contact or live action.

## Exact Identities

- `AGENTS.md` SHA256:
  `79785eb79a456fbb713a2e297784fdd4decd304cd725d5a90f16673df584e7d7`;
- live helper SHA256:
  `9f3055e3c782d058f11bc2482c6cc4270a400e1654fdfdc50be6e681b4e3d7d7`;
- focused test SHA256:
  `402382d88ef853cda70e98614aa6a73ab9ff424cff8d25daf00b4a72962d72b3`;
- retained reviewed draft SHA256:
  `a4d72aaa29807e9f056ef64ce04398246801f115a4667b4837acb9cd4335960c`.

## Active-State Validation

- focused successor tests: `26/26 PASS`;
- R4W1-pattern tests: `107/107 PASS`;
- candidate-builder tests: `8/8 PASS`;
- combined bounded suite: `115/115 PASS`;
- `git diff --check`: PASS;
- offline gate: `PASS_R4W1A_STREAM_CANDIDATE_OFFLINE_CHECK`;
- runtime policy decision: `active=true`;
- candidate consumed: `false`;
- device contact, device write, and flash: all `false`.

The offline result retains `state=DRAFT_INACTIVE` only as metadata from the
unchanged reviewed draft source. The load-bearing runtime decision is
`policy.active=true`, derived from the committed exact `AGENTS.md` sentinel and
all pins.

## Approval Boundary

No further source, build, artifact, or policy work is required before live
preflight. The operator must remain present with the device in completed rooted
Android, USB debugging authorized, and the cable connected. The fresh live
acknowledgement is:

`S22PLUS-FYG8-R4W1A-STREAM-CANDIDATE-LIVE`

After that acknowledgement, the helper first reruns the complete offline gate
and connected read-only preflight. Any mismatch stops before consumption or
candidate flash. If automatic Download entry for mandatory rollback does not
appear after candidate observation, the operator must physically enter Download
mode. Interrupted recovery uses the separately pinned rollback acknowledgement
only after a valid v2 consumed state exists.
