# S22+ FYG8 P2.80 udev-guard lifecycle and evidence contract

Date: 2026-07-27 KST

## Verdict

`PASS_H0_GUARD_EXPIRY_ASYMMETRIC_EVIDENCE`

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

The second state could preserve an `endpoint-timeout` while reporting a
successful guard release. That was a false attribution path, not merely missing
diagnostics. A first correction then went too far in the opposite direction:
it invalidated an already captured exact banner whenever the guard was found
lost at observation close.

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

The release receipt reader accepts only exact status/shape combinations and the
success-only validator remains strict. Process v2 reopens that exact receipt
and stores its status in durable live state and the `OBSERVED` transition.

Evidence treatment is deliberately asymmetric:

- an exact accepted banner remains proof when the helper reports
  cleanup-confirmed `guard-expired` or `guard-exited-uncommanded`; the live
  state retains that status as `candidate_observer_guard_warning`;
- banner absence under either warning is indeterminate and cannot be attributed
  to the device, so it remains no-proof;
- `release-failed`, malformed, missing, or stale release evidence remains
  fail-closed because cleanup is not established.

The asymmetry is sound because ACM acceptance already requires the current
candidate AP and approval binding, exact current run ID, exact USB identity,
Download departure, pre-open guard/property validation, `TIOCEXCL`, repeated
endpoint and file-descriptor identity, exact byte count, no extra byte, and a
hash-bound raw payload. Guard loss can allow another process to consume those
bytes, but cannot synthesize that exact candidate-bound payload.

With no accepted banner, a completed rollback after exact expiry closes as:

```text
NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK
candidate_observer_guard_expired_rollback_verified
```

Recovery from an interrupted transaction uses the same receipt and outcome
mapping without repeating candidate observation or transfer. With an accepted
banner it re-derives proof and preserves the warning; without one it does not
collapse expiry back to a generic endpoint timeout.

The existing guard schema name and exact successful receipt shape are
unchanged, so completed success evidence remains readable. New failure statuses
are additive. Their effect depends on the already durable exact-banner result.
A future ready bundle still binds the changed observer and embedded-helper
source hashes.

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
- expiry and uncommanded exit racing with a broken control pipe and post-write
  wait;
- final guard-property loss after an exact banner read;
- strict expiry-receipt mutations;
- rejection of contradictory `release-failed` receipts carrying cleanup-
  confirmed exit `0`, `3`, or `4`;
- ordinary release failure compatibility;
- exact ACM acceptance across cleanup-confirmed expiry and uncommanded exit;
- absent ACM plus expiry remaining an explicit no-proof result;
- ACM-only diagnostics surviving expiry;
- cleanup-uncertain release failure remaining fail-closed;
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
isolated-helper test fail with accidental zero exit. That review established
the lifecycle protocol. A later adversarial read identified the over-broad
evidence invalidation described above. Its first independent review returned
`NO-GO` for two remaining exact-banner discard races: helper exit `4` in
broken-pipe/post-wait paths and final guard-property cleanup between health and
property checks. Both were corrected; the same persisted review session's
delta review returned `GO` with no findings after 86 focused tests and the
isolated real-helper fixture passed.

## Limits

Exit `3` proves helper TTL expiry only when cleanup completed; a cleanup
exception exits `1` and remains a generic release failure. This is
fail-closed. Exact ACM acceptance does not prove that the guard remained active
for the whole window; the warning preserves that limitation. Banner absence
under a warning does not prove why the endpoint or bytes were unavailable.

The P2.80 timing receipt and guard-cap calculation remain mandatory. They
prevent a knowingly oversized observation window; the repaired runtime
contract independently detects an actual expiry caused by scheduling,
measurement error, or unexpected overhead.
