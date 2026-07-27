# S22+ FYG8 P2.80 udev-guard expiry observation contract

Date: 2026-07-27 KST

## Verdict

`PASS_H0_GUARD_EXPIRY_DISTINGUISHED`

This unit is host-only. It performs no device contact, build, packaging,
manifest generation, approval, transfer, or flash.

## Defect

The privileged transient udev guard removed its rule on either a parent
`release` command or its 300-second TTL, then returned zero in both cases.
`ModemManagerGuard.release()` accepted an already-exited zero-status child as a
successful commanded release.

That merged two materially different states:

- the exclusion rule remained active for the complete candidate observation
  and the parent deliberately released it; and
- the rule expired before observation closure, allowing another process to
  claim `ttyACM0`.

The second state could preserve an `endpoint-timeout` or even a previously read
banner while reporting a successful guard release. It was therefore a false
evidence path, not merely missing diagnostics.

## Correction

The embedded root helper now has one source-bound exit protocol:

- `0`: exact `release\n` command received;
- `3`: the 300-second TTL expired;
- `4`: control EOF or a termination signal occurred before release; and
- `1`: validation, udev, cleanup, or other helper failure.

The parent now samples child state before writing the command. Any prior exit,
including status zero, is uncommanded and cannot produce `released=true`.
The helper rechecks signal state and the monotonic deadline after `select()` and
again after reading the command. A release becomes successful only at that final
check; an already-expired deadline or an earlier signal wins the race. Expiry
racing with the parent pipe is recovered from status `3` and retained as
`guard-expired`.

The release receipt reader accepts only exact status/shape combinations and
keeps cleanup outcome separate from evidence validity. The success-only
validator remains strict. Process v2 reopens the exact failure receipt, stores
the status in durable live state and the `OBSERVED` transition, and refuses
candidate proof. A completed rollback closes this case as:

```text
NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK
candidate_observer_guard_expired_rollback_verified
```

Recovery from an interrupted transaction uses the same receipt and outcome
mapping; it does not collapse expiry back to a generic endpoint timeout.

The existing guard schema name and exact successful receipt shape are
unchanged, so completed success evidence remains readable. New failure statuses
are additive and can only remove proof. A future ready bundle still binds the
changed observer and embedded-helper source hashes.

## Validation

Focused fixtures cover:

- commanded helper release and exact zero exit;
- real helper TTL expiry in an isolated bubblewrap user namespace, including
  rule removal and both udev reloads;
- real isolated-helper schedules where `release\n` is already readable but the
  deadline expires or a termination callback fires after `select()` and,
  separately, after `readline()`; all remain nonzero and perform cleanup;
- expiry before parent release;
- an uncommanded zero exit;
- expiry racing with a broken control pipe;
- strict expiry-receipt mutations;
- ordinary release failure compatibility;
- live Process v2 proof refusal and exact expiry outcome;
- journal recovery after an `OBSERVED` interruption; and
- recovery directly from `CANDIDATE_FLASHED`, reopening the already-durable
  accepted ACM receipt and expiry receipt without observation or candidate
  transfer replay.

The existing observation and live-runner suites remain the historical
regression surface. One persisted independent `gpt-5.6-sol` high-reasoning
review returned `NO-GO` for the missing post-`select()` ordering and direct
`CANDIDATE_FLASHED` recovery fixture, then a second `NO-GO` for missing
post-read fixtures. The final delta review returned `GO` after independently
removing each post-read fence in memory and observing the corresponding real
isolated-helper test fail with accidental zero exit. It also reconfirmed direct
recovery, mandatory rollback, `proof=false`, compatibility, and clean scope.

## Limits

Exit `3` proves helper TTL expiry only when cleanup completed; a cleanup
exception exits `1` and remains a generic release failure. This is
fail-closed. The change does not prove why an ACM endpoint or banner was absent.

The P2.80 timing receipt and guard-cap calculation remain mandatory. They
prevent a knowingly oversized observation window; the repaired runtime
contract independently detects an actual expiry caused by scheduling,
measurement error, or unexpected overhead.
