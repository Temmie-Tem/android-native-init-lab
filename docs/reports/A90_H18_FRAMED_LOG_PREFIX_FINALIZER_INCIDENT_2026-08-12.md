# A90 H18 framed-log prefix finalizer incident

Date: 2026-08-12

## Classification

`H18_FRAMED_LOG_PREFIX_ENVELOPE_MISMATCH` is a host observer incident after
the one H18 D1 arm-plus-reboot effect was already consumed.  The device showed
the generic E1 return and the bounded read-only follow-up captured an exact H18
native return.  Its appended log payload contains one ordered failure record at
`firstboot-overlay` with `rc=-1`, `errno=1`, and `root_mounted=1`, followed by
one clean-restoration record with the UFS root unmounted, recovery not required,
and userdata unchanged with zero writes.

## Host defect

The original H18 finalizer compared the complete `logcat` command receipts.
Those receipts include per-command `A90P1` sequence, duration, echo, completion,
and prompt envelopes.  The opening receipt used sequence 10 and the later
receipt used sequence 6 after a host bridge restart, so two valid cumulative
log payloads could never satisfy the complete-receipt prefix check.  The raw
log payload itself is an exact prefix and was not the source of the rejection.

## Disposition

The consumed arm, reboot, and handoff are never replayed.  A distinct host-only
successor binds the exact five-record journal prefix and the already captured
private bridge transcript.  It validates all six outbound command lines, all
six successful framed responses, exact H18 health, `binding=1 enable=1
latch=1`, the same durable intent, unmounted userdata, payload-only log-prefix
continuity, and the unique ordered diagnostic and cleanup facts.  It may append
only `final-health` and `closed`; it performs no device, `/dev`, USB, network,
reboot, handoff, mount, service-control, payload, flash, or userdata action.

The successor retires after the exact journal closes, on any bound source,
capture, or execution-closure drift, or on any new incident.  Its independent
qualification grants no live authority and cannot authorize another D1 or F1
effect.
