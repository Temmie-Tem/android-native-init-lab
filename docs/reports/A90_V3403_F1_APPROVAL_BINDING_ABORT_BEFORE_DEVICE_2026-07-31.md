# A90 V3403 F1 Approval-Binding Abort Before Device

Date: 2026-07-31

Status: `CLOSED_BEFORE_DEVICE_H0_REMEDIATED_REVIEW_GO_NO_LIVE_AUTHORITY`

## Outcome

Run `a90-v3403-debian-f1-20260731-02` consumed one exact F1 approval. The
orchestrator created its private transaction and invoked the manifest-bound
staging child. The child rejected the approval before host NCM enumeration,
bridge selection, or any device command.

The durable journal ends:

`preflight -> approved -> staging-started -> staging-failed -> aborted-before-candidate`

The structured result is `ABORTED_F1_V2_BEFORE_CANDIDATE`. Candidate and
rollback transfer counts are `0/0`, candidate replay is false, rollback is not
required, no rootfs was staged, and no continuation receipt exists. The run
and approval are closed and non-reusable.

## Cause

The attended orchestrator approval binding correctly added:

- `observation_mode`;
- `attended_window_sec`;
- `pre_handoff_attempt_limit`; and
- `handoff_attempt_limit`.

The staging adapter still reconstructed the previous binding shape locally.
Its exact comparison therefore rejected the valid attended receipt with
`parent approval does not match exact staging closure`. This occurred before
the staging live directory and before the adapter's NCM, bridge, baseline, or
remote-path gates.

## H0 Repair

The staging module now owns one `canonical_f1_approval_binding()` builder.
Both the orchestrator and staging receipt validator call that same builder.
It validates the exact run ID and every bound SHA256, rejects non-integer
policy values including booleans, and accepts only:

- attended `operator-attended-v1` with `900/3/1`; or
- unattended `unattended-single-shot-v1` with `0/1/1`.

The existing one-candidate, mandatory-rollback-after-candidate, no-replay, and
boot-only fields remain unchanged. Legacy or missing observation bindings,
stale receipts, and stale source or manifest bindings fail closed.

The exact failed receipt was revalidated host-only against the repaired
canonical builder. It matched, which reproduces and closes the implementation
mismatch without reopening the consumed run.

## Validation

- staging focused tests: `39/39`;
- orchestrator focused tests: `72/72`;
- related regression closure: `157/157`;
- touched Python `py_compile`: pass;
- `git diff --check`: pass; and
- independent execution-critical re-review: `GO`, with no Critical, High, or
  Medium finding.

The independent review performed no device contact and no file modification.
This repair creates no run, manifest, receipt, approval, rollback authority,
or live authority.

## Next Gate

A later attempt requires a new run identity, new rootfs/key pair, fresh exact
connected D0 and path-absence evidence, a final manifest binding the repaired
source hashes, a new host-only approval receipt, and one fresh exact F1
approval. No artifact from this closed run may authorize that attempt.
