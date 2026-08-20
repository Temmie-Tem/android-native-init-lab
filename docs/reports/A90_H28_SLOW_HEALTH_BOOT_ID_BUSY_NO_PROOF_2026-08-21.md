# A90 H28 slow-health boot-ID busy incident

Date: 2026-08-21

## Disposition

`NO_PROOF_OBSERVER / RECOVERY_PARKED`

The attended, read-only `A90_H28_SLOW_HEALTH_RECONCILIATION_V1` session was
executed exactly once after its reviewed preparation token was repeated. It
performed no image transfer, reboot, physical action, partition write, or
other device effect. The session is consumed and must not be rerun.

This result is not an H28 kernel failure. The H28 candidate had already been
replaced by the exact V2321 rollback before any candidate boot opportunity.
The current observation therefore concerns only the returned V2321 resident.

## Observed prefix

The fixed slow-input observer established all of the following in one bounded
session:

- the exact A90 Native USB endpoint was present and the other Samsung endpoint
  was left untouched;
- the repository-managed serial bridge was exact and healthy;
- `version` completed with `rc=0` and proved exact V2321
  `0.9.285 / v2321-usb-clean-identity-rodata`;
- `selftest` completed with `rc=0`, `pass=11`, `warn=1`, and `fail=0`;
- `status` completed with `rc=0`, repeated the exact V2321 identity and
  self-test result, reported native boot health, and reported pstore entries
  equal to zero.

The final fixed command,
`cat /proc/sys/kernel/random/boot_id`, reached the exact A90P1 producer but
returned `rc=-16`, `errno=16`, `status=busy` with the device message
`auto menu active; send hide/q before command`. No boot ID was produced.

## Classification

The failure is an observer-state precondition defect: the reviewed command
sequence did not make the automatic menu quiescent before requesting the boot
ID. It is not a device contradiction and cannot be converted into terminal
resident health by combining older evidence.

The durable slow-health observation intent exists with SHA-256
`63c26238f332a7bc1bad37a3950d5dc05f383c50a4a09ecfe57e2a119a390ac4`.
The original run has no `41-recovery-closed.json`. The active-run guard and
the consumed H28 candidate guard both remain present. Candidate and rollback
replay remain forbidden.

## Next boundary

No second invocation of this capability is allowed. Any future closure must be
a newly designed terminal-only observer with a fresh namespace and review. It
may use only a predeclared, read-only way to quiesce or account for the native
automatic menu before obtaining a fresh boot ID; it must not authorize a boot
image, reboot, physical action, candidate replay, or rollback replay.

No D0, D1, F1, candidate, install, handoff, recovery, or live authority is
granted by this report.
