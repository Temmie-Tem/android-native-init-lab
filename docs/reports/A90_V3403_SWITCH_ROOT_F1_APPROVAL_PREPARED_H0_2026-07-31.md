# A90 V3403 Switch-Root F1 Approval Prepared

Date: 2026-07-31 KST

Status: `H0_APPROVAL_PREPARED_AWAITING_EXACT_OPERATOR_ACK`

## Scope

This unit prepares a fresh A90 V3403 transaction whose bounded observation is
the first real PID-1 handoff into Debian through `switch_root`. It does not
authorize or execute rootfs staging, a candidate boot transfer, a reboot, or
the mandatory rollback.

The prior V3403 run and its consumed approval remain closed and non-reusable.

## Connected preparation

After explicit operator direction to resume from the reported D0 stop, the
successor used a no-menu-control path. Fresh bounded reads proved:

- exactly one manifest-bound A90 target, separate from the connected S22+;
- healthy V2321 version and build;
- zero selftest failures and zero pstore entries;
- direct topology-bound A90 NCM route, host CIDR, and device reachability; and
- absence of the new run-derived final source, fixed work image, and run-owned
  staging directory.

The old fixed-name source remains present and untouched. It is not an input to
the new transaction. No device file was written during these checks.

## Unique source-path contract

The staging adapter no longer accepts one global fixed final source path. The
only accepted final path is derived from the exact run ID suffix
`YYYYMMDD-NN`. The manifest value must be byte-exactly equal to that derived
path.

The contract rejects:

- the legacy fixed path;
- a path derived from another run;
- redundant separators or traversal;
- a path outside the fixed runtime directory; and
- the fixed V3403 work-image path.

The manifest loader, connected path evidence, and staging scripts therefore
bind the same exact final, work, and staging paths. Absent-only same-filesystem
hard-link publication and no-clobber behavior are unchanged.

Commit `b59c939d89c5e8b40e9e606710c875f0043c62a8` contains the two-file
execution-critical change.

## Validation and review

The focused host-only suite passes `125/125`. Touched Python and its execution
closure pass `py_compile`, and the tracked diff passes `git diff --check`.

Independent safety review returned `GO`. Its focused checks passed `93/93` and
confirmed deterministic run-derived naming, byte-exact manifest binding,
three-path D0 agreement, unchanged no-clobber publication, and no added device
authority. The reviewed diff SHA256 was
`c62ac8e057d4eab00d99b3dbf39bd5d87eeb815afa61db9171bc125788cb9a64`.

## Prepared immutable closure

Run `a90-v3403-debian-f1-20260731-01` has a fresh single-run observer key and
new-inode keyed rootfs copied from the pristine D3 source. The exact candidate,
V2321 rollback, flash runner, staging adapter, orchestrator, connected D0, path
preflight, and host preparation are bound by one final manifest.

The final manifest SHA256 is
`1ac6e5066aef3aae9925766204d44503fdd21beb2e81e50feea9231becc2f68d`.
Both staging-adapter and parent-orchestrator host inspections report zero
contract issues and approval-preparation readiness.

One exclusive private approval receipt was then created with mode `0600`.
Its token remains only in private run evidence and is not recorded here. The
receipt states:

- `device_contact: false`;
- `device_write: false`;
- `f1_authorized: false`; and
- `live_authorized: false`.

Private artifacts are under
`workspace/private/runs/server-distro/a90-v3403-debian-f1-20260731-01/`.

## Next gate

The transaction is prepared but not authorized. The next action is one fresh
exact operator acknowledgement of the privately prepared approval token.

That acknowledgement will bind one candidate boot-only attempt and its
mandatory exact V2321 rollback. Only after it is received may the attended F1
runner revalidate health, stage the unique rootfs source, transfer the V3403
boot candidate once, attempt the bounded Debian PID-1 handoff, observe the
result, and restore V2321. Missing switch-root proof remains a no-proof result,
not a pass.
