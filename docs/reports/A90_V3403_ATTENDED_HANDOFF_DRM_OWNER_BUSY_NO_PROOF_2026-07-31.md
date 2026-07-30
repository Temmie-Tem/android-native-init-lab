# A90 V3403 Attended Handoff DRM-Owner Busy No-Proof

Date: 2026-07-31

Status: `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`

## Scope and result

Run `a90-v3403-debian-f1-20260731-03` consumed one exact F1 approval and one
exact attended-continuation acknowledgement. The manifest selected
`operator-attended-v1` with exact `900/3/1` limits.

The run completed:

- absent-only rootfs staging and final SHA256 verification;
- one candidate boot transfer and checked readback;
- exact candidate version, selftest, and source preflight;
- one successful attended pre-handoff attempt;
- one durable handoff intent and one handoff command;
- candidate native-init return;
- one exact V2321 rollback transfer and checked readback; and
- exact V2321 final health through rollback-only recovery.

Debian PID1 was not proved. Candidate and rollback transfer counts are `1/1`,
candidate replay is false, internal userdata is untouched, and the canonical
eight-event timeline passed.

## Handoff boundary

The runner fsynced `attended-handoff-started` before sending the exact command.
The private device trace then proved:

1. the source rootfs SHA256 matched;
2. strict display cleanup began;
3. the named display services returned without a retained service error;
4. one DRM owner passed its TERM deadline, received SIGKILL, and still reached
   the one-second per-owner deadline as `-EBUSY`;
5. another owner stopped;
6. the authoritative final scan reported exactly zero remaining
   non-preserved DRM owners;
7. `handoff_display` nevertheless returned the retained `-EBUSY`; and
8. the source rootfs SHA256 remained byte-identical after failure.

No post-display-cleanup source marker, work-copy creation, mount, or actual
`exec_switch_root_now` marker survived. The formal result therefore cannot
claim storage handoff, `switch_root`, Debian init, or Debian SSH proof.

## Root cause selected for H0

`d_handoff_stop_display_owners_mode()` retains any per-owner stop error in
`final_rc`. A later zero-owner rescan prevents a new `-EBUSY`, but does not
clear an earlier per-owner timeout even when that final scan proves the owner
and its DRM file descriptors are gone.

The live ordering is therefore consistent with a resolved per-owner deadline
race whose stale error remains load-bearing. The final zero-owner scan is the
stronger ownership result. A successor must distinguish this exact resolved
timeout from:

- a nonzero final owner count;
- a display-service failure;
- a `/proc` scan failure; or
- any non-timeout signal or process-control error.

It must not broadly turn display cleanup errors into success.

## Rollback recovery

After the no-proof observation, candidate native-init return succeeded and the
exact rollback completed once. The first post-rollback channel settle sent
`hide`, but automatic menu output interleaved it as `hidAe`. Durable state had
already reached `rollback-flashed`.

The approved rollback-only recovery path therefore performed no transfer. It
reopened the exact consumed approval and journal, read final health, and closed
with:

- exact V2321 version and build;
- selftest `fail=0`;
- pstore entries `0`;
- candidate transfer count `1`;
- rollback transfer count `1`; and
- candidate replay false.

## Next gate

No new live authority exists. Before another run, H0 must implement and test a
versioned display-cleanup successor in which a final zero-owner rescan resolves
only the exact earlier per-owner `-EBUSY`, while service, scan, signal, and
nonzero-owner failures remain fail-closed. The changed execution-critical
closure requires cross-compilation, focused fault tests, and one independent
safety review.
