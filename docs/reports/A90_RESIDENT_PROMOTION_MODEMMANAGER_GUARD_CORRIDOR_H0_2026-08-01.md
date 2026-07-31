# A90 resident promotion ModemManager guard corridor H0 closure

## Decision

The host-only change closes the first candidate-return framing gap exposed by
run `a90-v3406-debian-display-f1-20260801-03`. The candidate transfer is not
replayed. No live-device authority was used by this unit.

The observed PC disconnect and later ACM re-enumeration remain the expected
USB reboot boundary. The candidate exposed a native prompt, so the retained
evidence is consistent with a successful candidate boot. The strict health
frame was corrupted by host AT probe bytes before `candidate-boot-ready`, so
the run correctly remains conservative rather than promoting that observation
to formal candidate qualification.

## Implemented boundary

- The existing exact A90-only transient ModemManager guard is armed and its
  exact receipt is durably journaled before candidate-transfer intent.
- The same live guard covers first candidate health, resident reboot, returned
  health, and the corresponding from-native rollback source checks.
- Success and recovery release the guard before terminal close. Exact release
  failure remains recoverable through two bounded, journal-derived recovery
  leases; active children and stale or dangling runtime rules fail closed.
- Loss of an observer guard cannot revoke the already-authorized exact
  rollback. An exact adb-recovery rollback may complete without the guard, but
  no unguarded resident framed command or final-health promotion is allowed.
- A durable `ROLLBACK_FLASHED` state is health-checked only; rollback is never
  retransmitted because a reporting or observer step failed.
- Guard lifetime covers the actual flash, remote-command, six fixed bridge
  preflight, two NCM rebind, reboot/return, and inline-recovery call graphs.
  The default remains 360 seconds; the reviewed ceiling is 7200 seconds.

The guard still uses the exact A90 USB identity, a transient rule under
`/run`, and parent-death cleanup. It does not stop ModemManager globally and
does not install a persistent udev rule.

## Validation

- Related A90 regression: `332/332` PASS.
- Orchestrator focused regression: `118/118` PASS.
- Resident-promotion regression: `20/20` PASS.
- CDC ACM observer regression: `41/41` PASS.
- Phase 2C contract packet: PASS.
- Python compilation and `git diff --check`: PASS.
- Independent safety review: GO, unresolved blocking findings `0`.

Reviewed execution identities:

- orchestrator: `aa0677077ddf82ed559a2b703e599ee05c3fa77f7023260d193c01c462b25b20`
- resident promotion: `0e18d50ee059419b273f7af9d3735e8ac8c5ee49c825973f3c36f1adcc7a13c8`
- CDC ACM guard: `6c8a6d2151928d2e098ca41b3c9dc24cdbbfabe9be10df19969be274744ef9a9`
- Phase 2C contract: `38bf85a2abb38c199d73cc448d68f7cfcf4155d8fa3cec14c6126cab15adcf5b`

## Authority after closure

Exact V2321 remains resident and the prior transaction remains closed healthy.
No A90 F1, D1, or attended authority exists. Because execution-critical hashes
changed, the next live attempt requires a fresh immutable manifest, fresh run
directory, passing preflight, and one new exact F1 approval. The consumed
`-03` approval and candidate must not be reused.

The separately connected S22+ received no command during the prior live run
and was not contacted by this H0 unit.
