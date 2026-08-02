# A90 qualified unattended resident D1 policy

Status: `H0_PASS_GO_POLICY_READY_NO_LIVE_AUTHORITY`

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

This is a policy and contract change only. The current v1 runner implements
only `A90_D1_ATTENDED_SESSION_V1` and requires `--operator-attended`. It must not
claim that flag while the operator is absent or asleep. Unattended execution
remains blocked until a separately reviewed runner implements the named mode
and its contract tests.

## Validation

- focused contract regression: `19/19` PASS;
- related contract, D1 runner, and resident model regression: `59/59` PASS;
- independent safety review: `PASS_GO`, no unresolved finding;
- device contact, payload transfer, partition write, flash, reboot: none.
