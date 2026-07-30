# A90 V3403 F1 Staging Abort Before Candidate

Date: 2026-07-30 KST

Status: `CLOSED_ABORTED_BEFORE_CANDIDATE_V2321_HEALTH_RESTORED`

## Disposition

Run `a90-v3403-debian-f1-20260730-02` consumed one exact fresh approval and
entered the manifest-bound absent-only SD staging step. It did not reach
candidate intent or invoke the checked flash helper.

- Candidate transfer count: `0`
- Rollback transfer count: `0`
- Candidate replay: `false`
- Rollback required: `false`
- Final post-failure health: unverified
- Internal userdata operation: none

The run and approval are closed and must not be reused. A later separately
approved D1 recovery restored command-channel and exact V2321 health; it did
not reopen this F1 transaction.

## Failure

The adapter reserved only its exact run-owned staging directory, then launched
the existing USB-local payload receiver. The host data connection timed out
before transferring the rootfs. Cleanup then timed out waiting for the command
channel end marker because the original receiver command remained blocked.

Read-only host inventory after the abort showed:

- the exact A90 ACM endpoint still enumerated;
- the bridge process and local listener still running;
- the A90 USB NCM link present and up; and
- no expected USB-local IPv4 address or route on that NCM link.

This explains the payload connection timeout without attributing any candidate
boot write. One later exact version read repeated the same command-channel
timeout. Under the same-material-failure-twice rule, no further device command
or experiment retry was attempted.

## Bounded D1 recovery

One fresh D1 approval authorized one control byte, cleanup of only the
run-owned incomplete staging path, and read-only V2321 health checks.

- One control byte released the blocked receiver.
- Exact final and work paths remained absent.
- The exact run-owned staging directory was empty and was removed with
  non-recursive `rmdir`.
- V2321 exact version/build passed.
- Selftest returned `11` pass, `1` warning, and `0` failures.
- Pstore contained zero entries.
- SD ext4 remained mounted read-write.

No flash, reboot, candidate replay, or userdata operation occurred.

## Host NCM repair and prevention

The existing A90 NetworkManager profile retained an old USB path binding and
therefore could not activate on the current verified A90 NCM interface. The
dedicated profile was recreated for the current interface using the existing
repository helper behavior. Direct USB-local route, host CIDR, and three ping
samples then passed.

The selected staging remediation adds a fail-closed host NCM gate before stage
reservation. It derives the host peer from the manifest-bound observer
address, requires a direct route with no gateway, verifies the route interface
as the exact Samsung A90 NCM function, requires the expected host CIDR, and
requires one successful device ping. The changed focused closure passes
`104/104`; independent review remains required before a new final manifest.

## Durable evidence

Private evidence is under:

`workspace/private/runs/server-distro/a90-v3403-debian-f1-20260730-02/`

The F1 journal records `staging-failed` followed by
`aborted-before-candidate`. The structured result records
`candidate_transfer_count=0`, `rollback_transfer_count=0`, and
`rollback_required=false`. Raw transport and bridge logs remain private.

## Next gate

No candidate recovery or rollback is needed because candidate intent was never
recorded. Before any new experiment:

1. independently review the changed staging execution closure;
2. bind its exact accepted source identity in a new run and final manifest;
3. repeat exact V2321, path-absence, and host NCM D0 evidence; and
4. obtain one fresh exact F1 approval.

No flash, reboot, or candidate replay is authorized by this report.
