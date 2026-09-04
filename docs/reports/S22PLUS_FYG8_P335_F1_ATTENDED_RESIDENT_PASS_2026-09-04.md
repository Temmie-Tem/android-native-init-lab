# S22+ FYG8 P3.35 attended resident F1 result

Date: 2026-09-04 KST

Target: `SM-S906N / g0q / S906NKSS7FYG8`

Formal verdict: `PASS_F1_V2_P335_AUTHENTICATED_ATTENDED_RESIDENT_AND_ROLLED_BACK`

Outcome: `p335_authenticated_attended_resident_rollback_verified`

## Result

The exact P3.35 boot-only candidate and the exact Magisk rollback each
transferred once. There was no attempt 2. The candidate observer accepted
three authenticated native-PID1 sessions: two on one continuously open tty
descriptor and one after the single planned host close/reopen. All three used
distinct challenge nonces and one unchanged per-boot identity.

The accepted sessions executed the fixed BusyBox tuple three times, for nine
successful commands in total: `id`, `uname -a`, and the fixed P3.35 nonce echo.
HMAC authentication, READY, boot-ID authentication, command framing, zero
exits, clean DONE, child cleanup and zero trailing bytes passed. The canonical
candidate receipt is `18882B/1b4aa474`.

The candidate remained enumerated on the same CDC-ACM and Type-C lane after
the initial observer released it. Interactive host sampling observed the same
endpoint identity twenty times over about five minutes. This sampling is
supporting operational evidence; the canonical three-session receipt remains
the proof source.

## Later-action incident

One later named `identity` action was armed after the initial proof. Its
durable intent is `299B/716a9a87`; the conservative result is
`uncertain` at `507B/7c856b07`, binding failure receipt
`259B/46a13cb2`. It consumed action ordinal 1 and terminated the lease. It was
not replayed, and no other later action was attempted.

The retained failure type is `AuthObserverError`. Its stored error digest
`a0afa674...` exactly matches the canonical message
`P335 exchange stopped at open-diagnostic-read`. In the runner's fixed order,
that point follows banner receipt, host OPEN and the entry diagnostic, but
precedes AUTH and every EXEC. The later action therefore executed no fixed
command. This does not invalidate the earlier three accepted sessions.

The device listener writes a banner and entry diagnostic before waiting for
OPEN, then repeats after an expected no-peer timeout. The host action reopened
the tty after a long idle without first discarding or synchronizing possible
queued preambles. That is a strong resynchronization hypothesis for the second
diagnostic mismatch, but it is not promoted to proved cause because this
failure path retained the stage digest rather than partial TX/RX bytes.

The proportional successor should make only two changes before another F1:

1. retain partial TX/RX and the nested exception digest on every action cut;
2. establish one fresh preamble boundary before OPEN, then test repeated
   idle/reopen sessions.

Reboot and Download-mode commands were not in the P3.35 catalog. They should
not be added until ordinary session resynchronization is demonstrated.

## Recovery and final health

The uncertain later action set the resident lease to `ROLLBACK_REQUIRED`.
Recovery resumed only the retained Process-v2 journal. After attended physical
Download entry, the exact Magisk rollback transferred once and the S22+
returned to rooted FYG8 Android with boot completion, stopped boot animation,
expected boot/supporting-partition identities and no Download endpoint.

The ordinary journal is `CLOSED` at 19 records, `recovery_required=false`,
canonical state is `26952B/17877f36`, and canonical result is
`30474B/c8005dee`. P3.35 is consumed and never replayable.

The supplemental Carrier read remains `AMBIGUOUS_INTEGRITY_FAILURE` because
its two generations differ. It is not the primary P3.35 arrival proof and
creates no Max77705 causal claim. The accepted authenticated CDC-ACM proof does
not grant interactive PTY, caller-selected shell, file transfer, persistence,
reboot, Download control or standing authority.
