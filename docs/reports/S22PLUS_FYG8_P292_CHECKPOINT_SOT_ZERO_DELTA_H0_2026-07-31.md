# S22+ FYG8 P2.92 checkpoint SoT zero-delta H0

Date: 2026-07-31 KST

Tier: H0

Status: `PASS_CHECKPOINT_SOT_ZERO_DELTA`

## Result

The phase-1 checkpoint source-of-truth generator reproduced the complete
retained P2.90 materialized scope byte-for-byte. The frozen baseline contains
`candidate.patch` and all twelve materialized sources. No artifact was
excluded.

The comparison order was load-bearing:

1. verify the retained P2.90 intent and all thirteen retained artifacts;
2. generate A in a clean temporary tree and require exact baseline equality;
3. only after A passes, generate B in a separate clean tree; and
4. require B to match both the retained baseline and A.

All three comparisons passed. File inventory, regular-file type, mode, size,
and SHA256 were exact. The gate reports:

```text
baseline artifacts:     13/13
run A baseline fidelity: PASS
run B baseline fidelity: PASS
run A/B determinism:     PASS
comparison weakened:     false
repair present:          false
```

This proves both fidelity to the bytes actually materialized for P2.90 and
deterministic regeneration. A↔B equality alone cannot pass the gate.

## Authority

The retained authority is:

```text
run ID:       2ec2bbaeed33025c92a0831c5e82dd3b
profile:      E2
intent SHA256:
  1e33bed20a46d646610e7e0e0bab7bd55c807451ec0b1cc7d4b3f3a1a48fc2dd
candidate.patch SHA256:
  f64f93f7e750187bb69e2f8dabca68b0c52ef31bf181bd1b0c06b5d6935853f1
```

The frozen public baseline manifest has SHA256:

```text
b3cc6d08101bb18bd688c0fb458623e9b8a9d6b7c3cd7f4ef7cb6e43c651bdcd
```

The private durable qualification result is mode `0400` and has SHA256:

```text
93fe9535d37b092ef5a9ec34364fd1fe8b62b186e1f39562e15ac7f688eace79
```

## Fault validation

The focused suite passes six tests. It proves:

- an authority-receipt mismatch prevents any generation;
- an A mismatch prevents B from starting;
- a B-only mismatch fails after the valid A comparison;
- a missing or extra generated artifact fails closed;
- the 107-position phase-1 descriptor matches the inherited P2.90 contract;
  and
- the real retained baseline passes without scope reduction.

## Scope boundary

This is only phase 1 of the two-phase introduction. The SoT deliberately
describes the existing P2.90 state defect and errno-discard behavior:

```text
active state: p290-field-subset-without-outcome-detail
errno policy: publication-error-discarded-before-quiet-park
```

It does not repair either property. No successor intent was derived, no kernel
or image was built, no device was contacted, and no live authority exists.
The next H0 unit may now apply only the predeclared exact-active-slot and errno
repairs on top of this byte-exact baseline and prove their delta attribution.

The SoT and byte-affecting generator are prospective Tier 1 identity inputs.
The frozen baseline, zero-delta gate, focused tests, and this report are
evidence-only Tier 2 inputs. This is the first implemented rung of the P2.64
Stage C identity split; Stage C remains open until the three-tier descriptor,
mutation matrix, approval binding, and independent review pass.

## Hygiene

Two earlier H0 reports contained a 65-character transcription of the P2.90
candidate-patch SHA. They were corrected to the 64-character intent-bound
value above. No retained private artifact or candidate source was changed.
Unrelated untracked A90 work was left untouched.
