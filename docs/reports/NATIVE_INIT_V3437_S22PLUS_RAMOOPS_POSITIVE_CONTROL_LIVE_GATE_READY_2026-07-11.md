# V3437 S22+ Ramoops Positive-Control Live-Gate Source Ready

## Verdict

`HOST_SOURCE_READY_POLICY_INERT_NO_LIVE`.

The resumable V3437 helper and two independent inert policy drafts are present.
`AGENTS.md` was not changed. No device contact, flash, reboot, panic, or other
live action occurred.

## Implemented

- exact V3435/V3436 artifact and contract pins;
- independent DTBO, panic, and restore acknowledgement gates;
- stock and patched Android read-only preflights;
- exact live DT and ramoops backend/parameter checks;
- run-bound kmsg/pmsg marker arm and one-shot panic trigger;
- ADB-loss observation and early-root/manual-recovery resume;
- duplicate pstore collection, byte comparison, hashing, and durable flush;
- standard single-events timeline schema;
- pre-panic automatic Android/Odin stock rollback;
- post-panic evidence-first rule;
- explicit evidence-abandon recovery classification;
- stock rollback and final baseline proof.

## Current Offline Result

```text
artifacts/contracts                      PASS
DTBO inert policy draft                  PASS
panic inert policy draft                 PASS
dtbo_active                              false
panic_active                             false
device_action                            0
V3437 focused tests                      16/16 PASS
V3426-V3437 regression tests           165/165 PASS (61.017 s)
```

## Remaining Gate

This is not yet live-ready. The two policy drafts require review and separate
operator approval before promotion to `AGENTS.md`. After promotion, a read-only
`--dry-run` must pass before `--live-session` may be considered.

## Post-Report Activation

The operator explicitly approved the V3437 live run on 2026-07-11. Both narrow
one-shot clauses were promoted to `AGENTS.md`; offline policy status is now
`dtbo_active=true`, `panic_active=true`. This activation record itself performed
no device action. The read-only dry-run remains the mandatory next gate.
