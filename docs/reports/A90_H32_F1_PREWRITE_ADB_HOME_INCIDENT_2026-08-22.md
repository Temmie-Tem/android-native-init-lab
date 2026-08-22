# A90 H32 F1 pre-write ADB-home incident — 2026-08-22

Status: H0 incident record. No candidate or rollback image was written.

H32 entered a durable pre-write park. The candidate owner receipt is
`PRE_WRITE_FAILURE` with `writeStarted=false`, `bootWrittenReadbackExact=false`,
and `systemReturnAttempted=false`. The rollback intent and launch records were
durable, but the rollback helper was never dispatched; candidate and rollback
write counts are both zero. The exact H32 journal/log closure is bound only by
the fixed H32 reconciler and receives no authority from this report.

The observed recovery ADB failure was an owner-observer failure. The operator
private daemon log proves the fatal startup condition
`Cannot mkdir '/nonexistent/.android': No such file or directory` under the
forced HOME. The complete unexpected raw ADB stderr stream is not reproduced
or tracked here and remains unproved as a byte-level claim.

The repair is limited to the fixed A90 owner path: a per-run owner-private
ADB HOME, exact `.android` contents/modes, child `umask=0077`, and no ambient
HOME/keys. The existing default host ADB server port remains unchanged. The
rollback zero-Samsung re-enumeration wait is now a passive bounded 30-second
window; late, wrong, extra, malformed, and timeout states still stop before
helper dispatch.

The current device recovery state is not claimed by this host-only record.
Closure requires a separately reviewed H32 reconciler and one later fresh,
exact healthy V2321 ACM observation. It may publish only the same run's 41
record, release only its active guard, retain the H32 candidate guard, and
never replay or perform candidate/rollback/reboot/recovery/image/partition
effects.
