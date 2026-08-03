# A90 qualified unattended resident D1 policy

Status: `H0_PASS_GO_POLICY_CLARIFIED_NO_LIVE_AUTHORITY`

Date: 2026-08-03

## Decision

Contract revision 2 permits one permanent attendance exception: exact A90
resident D1 may run unattended only through
`A90_UNATTENDED_RESIDENT_D1_V1`. The currently qualified action is the existing
no-payload `SWITCHROOT_EXPERIMENT` transaction with unchanged reviewed dispatch,
automatic native return, durable intent, and no replay.

The exception is a permanent Revision 2 boundary delegation. Standing
no-per-action autonomy remains part of the operational trial: after trial
retirement, the exception survives but creates no live authority without the
successor procedure and its required live binding.

Every ordinal requires fresh exact-target D0 and starts only from durable
`RESIDENT_HEALTHY`. A late ACM/NCM endpoint enters passive health observation;
it does not cause action replay or immediate recovery failure. Control loss or
recovery-required state parks all new effects until the operator returns. Real
target ambiguity, resident mismatch, or loss of physical recovery remains an
immediate permanent-boundary stop.

Independent `PASS_GO` is capability qualification, not a per-run approval. One
verdict is reused across ordinals, manifests, qualifications, and campaigns
while its exact execution-critical closure and hazard assumptions remain
unchanged. A closure change or new hazard/incident requires the next capability
review.

## Unchanged boundaries

- S22+ D1 remains attended.
- Every F1 remains attended and boot-only.
- Forbidden partitions and raw primitives remain forbidden.
- Exact target isolation, rollback readiness, physical recovery, private
  evidence, one intent/one dispatch, and no-replay remain mandatory.
- Persistent settings, credentials, security state, package/rootfs/recovery
  mutation, payload transfer, and actions expected to need physical entry are
  outside the unattended lane.

## Implementation boundary

The attended v1 runner still requires `--operator-attended` and must not claim
it while the operator is absent or asleep. A separate H0 runner now implements
the named unattended mode, but execution remains blocked until one independent
`PASS_GO` receipt binds its exact execution-critical closure.

## Validation

- focused contract regression: `19/19` PASS;
- related contract, D1 runner, and resident model regression: `59/59` PASS;
- independent safety review: `PASS_GO` for clarification, no unresolved finding;
- device contact, payload transfer, partition write, flash, reboot: none.
