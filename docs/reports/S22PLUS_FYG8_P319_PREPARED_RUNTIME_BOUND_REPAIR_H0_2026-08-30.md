# S22+ FYG8 P3.19 prepared/runtime-bound Process-v2 repair

Date: 2026-08-30 KST

Status: `P319_PREPARED_RUNTIME_BOUND_REPAIR_IMPLEMENTED_REVIEW_PENDING`

## Incident

The first approved P3.19 F1 invocation stopped before any transaction or
device effect with:

`P3.19 candidate-static authority rejected the result`

The retained exception cause was `Integration V2 is not byte-reproducible`.
The preceding connected D0 preparation had succeeded and published an exact
`prepared.json`.  The prerequisite then scanned that new pre-effect record,
found the candidate AP digest, and relabeled preparation as prior candidate
consumption.  Candidate-static live verification regenerated that time-varying
prerequisite and rejected the immutable Integration snapshot it had accepted
immediately before preparation.

The failed invocation created no `transaction`, Download-request intent,
global claim intent or claim, transfer attempt, live state, or live result.
The global registry still contains zero records and zero active claims.  No
Download request, Odin invocation, candidate transfer, rollback transfer,
reboot, partition write, or candidate replay occurred.  The old prepared
binding is now stale and is not reusable.

## Bounded repair

The repair separates three states that the previous verifier conflated:

1. The exact `ready-for-f1-approval` public declaration remains
   non-consuming.
2. An exact private `device_action_f1_prepared_v2` record is also
   non-consuming only when its direct child set is exactly the preflight
   directory plus `prepared.json`, `target-private.json`, and the P3.00
   USB-trace binding.  Its typed header, false effect flags, candidate and
   rollback identities, canonical base/live binding digests, exact current
   ready observation and execution-source closure, and mode-0400
   D0/private-target/USB-trace receipts are reopened before exclusion.  The
   already-retained stopped run is separately pinned by the complete
   `prepared.json` identity.  A malformed record, replacement between parse
   and classification, or any unexpected child fails closed.
3. `validate` and `prepare` retain full Integration regeneration.  Once a run
   is prepared, `execute` and `recover` use a runtime-bound validator that
   reopens the exact pinned Integration snapshot and rederives the complete
   candidate-static object without replaying its historical absence probe.
   The runner's global-registry preflight and durable journal remain the live
   no-replay and recovery authorities.

This runtime-bound path is P3.19-specific.  It does not weaken other Process-v2
profiles and does not bypass candidate AP, rollback AP, manifest, source,
promotion, target, or prepared-binding verification.  Recovery can therefore
reopen a consumed run instead of being blocked by the very claim it must
recover.

## New immutable chain

- raw-first receipt `-24`: 15,075 bytes / `54db40b2fc63f98b…`, mode 0400,
  link count one; `-23` `15075B/608799f1…` remains preserved.
- global registry qualification `-02`: 2,964 bytes / `7be7e29cb458457d…`,
  mode 0400, link count one.
- prerequisite `-14`: 13,186 bytes / `4e29a5630c8a7a0d…`, mode 0400,
  link count one.
- Integration V2 `-19`: 126,133 bytes / `dc9380a73e61e6f9…`, zero blockers,
  runtime classification pending, mode 0400, link count one.
- candidate-static `-14`: 35,307 bytes / `37654942055d063a…`, mode 0400,
  link count one.
- promotion `-14`: candidate-static `35307B/37654942…`, run manifest
  `1043B/ba44ec77…`, static check `1842B/45464908…`; all mode 0400 and
  link count one.
- tracked ready manifest: 2,432 bytes / `e84e81837c010e4c…`, direct regular
  link count one, mode 0644 or Git-umask-equivalent 0664.

Candidate AP `27279401B/db5666ac…`, its boot member, and rollback AP
`23367721B/d2373bf8…` are unchanged.

## Validation and authority boundary

The exact main-tree `--validate` passes against the retained failed-prepared
record, the new promotion, the current A90-parallel source population, and the
zero-record global registry.  Focused hostile tests cover exact pre-effect
prepared acceptance, false-to-true authority mutation, every unexpected
direct child, current observation/closure divergence, parse-to-classification
replacement, strict Integration regeneration, and runtime-bound non-replay of
the state probe.  The final focused sets pass 140/140 (53 prerequisite/static/
Integration, 18 promotion/ready, and 69 live-boundary/ledger/docs), and the
actual public manifest reopens with runtime-bound bundle
`58c841e15fb53453…`.  Independent review remains pending.

This H0 repair grants no D0, D1, F1, recovery, replay, or live authority.  It
does not authorize use of the previous approval token.  After independent
review, a fresh connected D0 preparation and a new exact attended F1 approval
are required.

Intermediate Integration `-17/-18`, candidate-static `-12/-13`, and promotion
`-12/-13` are preserved as non-authoritative build-order predecessors.
