# S22+ FYG8 pre-F1 autonomous coordinator H0 report

Date: 2026-08-29

Status: **IMPLEMENTED / REVIEW PENDING / NOT ACTIVE**

## Cause

The independently reviewed pre-F1 policy defines one finite four-class
campaign, but policy text alone cannot enforce aggregate debit, effect
serialization, expiry, or uncertain-consumed no-replay behavior. The first
implementation slice should establish those semantics without creating a
device runner or repeating the large per-action machinery that the policy was
written to remove.

## Change

`workspace/public/src/device-action/coordinators/s22plus_fyg8_pref1_autonomous_coordinator_h0.py`
is a pure host-side state core. It parses and hashes the single JSON declaration
in the reviewed policy, binds the exact `SM-S906N/g0q/S906NKSS7FYG8` target,
and accepts only canonical typed activation-model bytes with the current
policy, coordinator, and catalog identities. The model enforces one 12-hour
campaign, the shared aggregate limits of eight D1 effects and 256 D0 command
groups, one open effect, fresh healthy identity before intent, and class-bound
boot continuity.

Host failure before intent returns the unchanged state. Effect intent debits
the applicable aggregate counter and consumes one ordinal. A healthy result
reopens the campaign; an uncertain post-intent cut parks the campaign with the
ordinal consumed and no modeled transition back to an effect. Android Recovery
is rejected because it is outside the four-class catalog.

The code lives under `workspace/public/src/device-action/coordinators/`, not
the observer-source directory. Adding a non-acquiring state model therefore
does not change the raw-first observer population or its unrelated cardinality
receipts.

## Independent-review repair

The first independent review passed every dormant, identity, accounting,
no-replay, Recovery, population, and proportionality check but found one
semantic mismatch. The policy permits the privileged USB-role/UDC transient to
prove restoration either in the same boot or by reboot, while the predecessor
`22,856B/1cdb721f` core accepted only same-boot completion.

The repair binds a closed `proof_mode` into every intent. D0 accepts only
`same_boot_observation`; normal reboot and the payload-free Download roundtrip
accept only `new_boot_health`; the privileged USB transient accepts either
`same_boot_restore` or `reboot_restore_health`. Healthy return enforces the
selected boot relation, both USB paths have positive and negative tests, and
unknown or cross-class modes fail closed. A future live integration must derive
this mode from its immutable fixed descriptor rather than caller input.

## Boundary

The core is deliberately not a live runner. `COORDINATOR_ACTIVE`,
`LIVE_AUTHORITY`, `DEVICE_ACTION_INTEGRATION`, and
`DURABLE_JOURNAL_INTEGRATION` are all false. The CLI exposes only
`--render-plan`; its plan contains empty device-command, effect, and partition
transfer arrays. The source imports no process-spawn facility and writes no
file. Its activation parser is a structural H0 model, not proof that an
activation manifest, independent review receipt, or live-session approval
exists.

No descriptor executor, target enumerator, raw observer, durable journal, or
recovery owner is connected. Those remain one later integration unit and must
bind fixed descriptors rather than caller-supplied commands, paths, or values.
The policy remains `DEFINED_NOT_ACTIVE`; F1 remains freshly attended and
ordinary Process-v2 is unchanged.

## Validation

The repaired coordinator is 23,764 bytes with SHA-256
`c0d56417c070c5958a356110f4b1996f9c903af993d118e0f812cccdd8aea65e`.
Its deterministic render-plan output is SHA-256
`1cb8dfeec01e00ff59b13869741d8b7f54b9399474c0ca856604e6b79552dac6`.
Fourteen focused tests cover dormant rendering, exact policy/catalog binding,
canonical activation rejection, aggregate D0 and D1 ceilings, pre-intent
non-consumption, class-specific boot identity, uncertain park/no-replay,
expiry, unknown/Recovery rejection, tampered intent, absence of execution
surface, render-only CLI behavior, and the documented inactive boundary. They
pass `14/14`; touched Python
compiles and `git diff --check` passes.

Independent review is required before the H0 core is qualified. Even after
that review, the catalog cannot activate until the separate fixed-descriptor
runner and durable journal integration are implemented, tested, reviewed, and
bound by one fresh attended campaign activation.
