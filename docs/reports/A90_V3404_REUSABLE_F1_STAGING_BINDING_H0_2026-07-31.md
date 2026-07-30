# A90 V3404 Reusable F1 Staging Binding H0

Date: 2026-07-31

Status: `H0_REVIEWED_READY_NO_LIVE_AUTHORITY`

## Scope

This host-only unit binds the reviewed V3404 boot successor to the existing
manifest-driven attended F1 machinery without copying or replacing the live
orchestrator. It changes no approval, candidate-one/no-replay, boot-only
transport, mandatory rollback, observation, final-health, or journal rule.

No device command, staging, flash, reboot, mount, network action,
`switch_root`, or userdata action was performed.

## Versioned run identity

The reusable absent-only staging adapter now accepts exactly two run cycles:

- `a90-v3403-debian-f1-YYYYMMDD-NN`; and
- `a90-v3404-debian-f1-YYYYMMDD-NN`.

The regular expression captures the exact cycle and suffix. The adapter then
selects the matching fixed rootfs filename prefix:

- V3403 selects
  `debian-bookworm-arm64-d3-sysvinit-v3403-keyed-`; and
- V3404 selects
  `debian-bookworm-arm64-d3-sysvinit-v3404-keyed-`.

The final path is re-derived from the run ID and compared both textually and
as a `PurePosixPath`. A V3403 path paired with a V3404 run, or the reverse, is
therefore rejected. The exclusive stage directory continues to include the
full run ID, so the two cycles cannot share a reservation.

## Unchanged execution closure

The existing orchestrator remains byte-identical. It already:

- reads candidate version and build from the immutable manifest;
- binds candidate, rollback, staging adapter, orchestrator, and flash-runner
  hashes into the approval receipt;
- requires one candidate attempt with no replay;
- fsyncs handoff intent before the one handoff command;
- pre-authorizes the exact rollback once candidate execution starts; and
- restores exact V2321 health before closure.

The switch-root command and immutable-rootfs SHA contract are unchanged
between V3403 and V3404. Only the reviewed V3404 display-owner return
semantics differ inside the candidate boot image.

## Validation

- staging focused tests: `41/41`;
- unchanged orchestrator tests: `72/72`;
- combined focused closure: `113/113`;
- Python compilation: pass;
- scoped diff check: pass; and
- independent safety review: `GO`, with no Critical, High, or Medium finding.

Mutation tests reject an added cycle, a forced cycle or suffix, a forced
V3403 prefix, bypass of the manifest final-path validator, and cross-cycle
remote paths.

## Disposition

This closure creates no run, manifest, receipt, continuation, or live
authority. The next H0/D0 preparation must create a fresh V3404 run directory
and new-inode keyed rootfs, bind the exact V3404 boot and V2321 rollback,
collect fresh target/path evidence, and stop at one new exact F1 approval
gate. No V3403 run or consumed approval may be reused.
