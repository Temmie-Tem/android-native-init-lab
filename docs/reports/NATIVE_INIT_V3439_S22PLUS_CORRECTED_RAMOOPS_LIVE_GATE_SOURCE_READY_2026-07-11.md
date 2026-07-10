# V3439 S22+ Corrected Ramoops Live-Gate Source Ready

## Verdict

`HOST_SOURCE_READY_POLICY_INERT_NO_LIVE`.

V3439 preserves the V3437 candidate, classifier, resumable session, durable
timeline, evidence-first recovery, and stock rollback. It changes only the
false-negative backend proof identified by V3438 and binds that correction to
the pinned V3438 postmortem.

No device contact, flash, reboot, marker, or panic occurred in this source unit.

## Exact Helper

```text
path=workspace/public/src/scripts/revalidation/s22plus_v3439_ramoops_positive_control_live_gate.py
sha256=a070b7d826c4698032cc6a3eb903f9c0365db72cf75bc900f5b1482f38432a81
v3438_postmortem_sha256=f5c12e50e01d9b7938a2482f4990a0620f9d7e7cb0fb6837350357af009ec5a4
```

## Corrected Backend Gate

Required:

```text
candidate DTBO readback matches pin
live DT status and all size properties match
ramoops module parameters match the post-register values
pstore mount count is 1
/dev/pmsg0 exists
/sys/module/pstore/parameters/backend == ramoops
exactly one symlink under /sys/bus/platform/drivers/ramoops
bound OF compatible == ramoops
bound OF status == okay
```

The early `Registered ramoops...` and `ramoops: using` strings are collected but
are no longer mandatory because V3438 proved they can be overwritten before
Android userspace.

## Preserved Safety

- exact candidate and stock DTBO-only AP pins;
- exact Magisk boot and target identity checks;
- independent DTBO, panic, and restore acknowledgements;
- pre-panic automatic stock rollback;
- no panic until the corrected backend gate passes;
- exactly one run-bound marker sequence and one panic attempt;
- duplicate pstore reads and durable per-step flush;
- evidence collection before stock rollback;
- standard `events:[{name,timestamp_utc}]` timeline;
- manual recovery resume and explicit evidence-abandon classification;
- one-shot policy consumption regardless of result.

## Current Gate

```text
V3439 focused tests     18/18 PASS
offline-check           PASS
dtbo_active             false
panic_active            false
device_action           0
```

The operator supplied fresh live approval. The exact helper must first be
committed, then separate SHA-pinned clauses may be promoted to `AGENTS.md`.
A connected read-only dry-run remains mandatory before candidate transfer.

## Policy Activation

After commit `7d97807a`, the exact helper SHA and V3438 postmortem SHA were
promoted into separate one-shot `AGENTS.md` clauses under the operator's fresh
approval. Offline policy status passed as `dtbo_active=true` and
`panic_active=true`; activation itself performed no device action. The connected
read-only dry-run is the next mandatory gate.
