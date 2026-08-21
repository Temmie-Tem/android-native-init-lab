# A90 F1 candidate-return machine receipt — H0 report

Date: 2026-08-21
Target: Samsung Galaxy A90 5G only
Tier: H0 host-only
Verdict: implemented and statically tested; no live authority

## Result

The checked `native_init_flash.py` path now has one fixed owner-only receipt
mode. It records the stage facts needed to distinguish pre-write failure,
unclassified write/readback failure, exact boot write/readback plus confirmed
TWRP System return, and exact boot write/readback plus uncertain TWRP System
return. The adapter accepts only the complete canonical receipt; missing,
malformed, duplicate, prose, generic-rc, or inconsistent receipts become
`UNCLASSIFIED`.

New PASS and successful rollback terminals require the exact
`BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_CONFIRMED` outcome. A healthy
snapshot cannot upgrade an unclassified or historical effect record. The
producer also requires `systemReturnAttempted=true` and a zero TWRP shell
return before a disappearing recovery endpoint can be treated as confirmed in
owner receipt mode. Legacy helper behavior remains unchanged. Nonzero TWRP
return in owner mode is unclassified and cannot create pending.

Recovery parsing also checks the durable `22-candidate-result.json` crash cut.
An exact uncertain result with no `23` record becomes
`CANDIDATE_RETURN_PENDING_RECORD_MISSING_NO_ROLLBACK`; substituted, malformed,
legacy, or missing-outcome results retain the old rollback-only historical
classification. No rollback record is created by this parser state.
The pending record's `effectReceiptSha256` is joined byte-for-byte to the
durable `22.payload.receiptSha256`; either-side mutation is an invalid
no-rollback park.

The minimal owner publishes `23-candidate-return-pending.json` only for the
exact uncertain outcome. It publishes that record before any rollback intent,
keeps candidate replay false, and retains both guards. Existing H24/H27/H28
journals remain historical and are not upgraded.

The physical/observation continuation is deliberately not implemented in this
unit. Its candidate-neutral token and intent design is recorded separately in
`docs/plans/A90_F1_CANDIDATE_RETURN_CONTINUATION_DESIGN_2026-08-21.md` and
requires a new independent review before any live use.

## Validation

- `python3 -m py_compile` passed for the changed Python modules.
- Focused suite: `93/93` passed, including the exact uncertain park,
  generic/missing/malformed receipt rejection, confirmed-receipt terminal
  gating, and nonzero-TWRP-return rejection tests.
- `git diff --check` passed.

## Boundary

Device, `/dev`, USB, network, `workspace/private`, S22+, and S20+ access were
zero. No image was built, transferred, rebooted, or flashed. No D0, D1, F1,
approval token, ordinal, or live authority was created. The execution closure
changed, so the prior H28 review/qualification is intentionally stale until a
fresh independent review binds the changed closure.
