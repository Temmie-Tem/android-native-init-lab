# A90 V3403 F1 Staging Abort Before Candidate

Date: 2026-07-30 KST

Status: `ABORTED_F1_V2_BEFORE_CANDIDATE`

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

The run and approval are closed and must not be reused.

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

1. perform a separately approved, bounded D1 recovery of the blocked receiver;
2. remove only the run-owned incomplete staging path;
3. verify exact V2321 health with D0 reads;
4. repair and statically validate host NCM readiness before staging; and
5. use a new run, final manifest, D0 evidence, and fresh exact approval.

No flash, reboot, or candidate replay is authorized by this report.
