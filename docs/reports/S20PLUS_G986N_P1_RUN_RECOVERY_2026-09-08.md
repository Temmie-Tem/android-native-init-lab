# S20+ P1 run and resident recovery

Result: **NO_PROOF_P1_PID1_WITNESS_RETURNED_RESIDENT_HEALTHY**

The exact S20+ P1 candidate was transferred once. Its resident Magisk rollback
was transferred once and final rooted Android health passed. Neither transfer
may be replayed. The shared action guard was released, and the P1 owner and
kmsg reader were returned to dormant. The one-run recovery exception is closed.
No recovery-partition access or other-target command occurred.

## What the run established

The candidate AP was the reviewed single-member boot archive, SHA-256
`2d80698a6cbcf2690cc4ae9a9ee70934df0f671102645e60f040d525b184e70b`.
Its transfer result was `odin_transfer_completed`. Android ADB metadata appeared,
but the inherited public-health predicate rejected before the root read and
before `/dev/kmsg` acquisition. The stored reason digest matches the literal
`Android public health differs`. The rejected field values were not retained,
so a boot-readiness timing issue is a hypothesis, not an established cause.

There is no P1 witness capture. Native PID1 execution, producer handoff and
sufficient log-prefix retention remain unproved. NO_PROOF is not disproof of
those behaviors; successful rollback does not improve the candidate verdict.

## Recovery deviation

The ordinary physical confirmation was consumed, but Download identity
qualification failed and an immutable `physical-observation-miss.json` was
published. The listed endpoint had product `SAMSUNG USB` and a different physical
topology from the prepared S20 `SM8250` endpoint. The operator reported two
Download devices and disconnected the other connection. Later host metadata
matched the prepared S20 profile/topology. This does not retroactively qualify
the first physical observation or establish that both devices were returned by
one host listing.

The existing policy prohibited further transfer after that miss. The operator
explicitly approved the [one-run policy exception](../operations/S20PLUS_P1_ONE_RUN_RECOVERY_EXCEPTION_2026-09-08.md).
A separate independently reviewed authorization allowed one new, distinct
incident identification and only the first bound resident rollback. The original
miss, confirmation, candidate claim, prepared binding and raw evidence were
preserved. No ordinary physical-arrival receipt was fabricated.

The implementation adds a default-deny rollback-provenance hook to the existing
engine and restricts the P1 exception to this run's resume path and rollback kind.
It retains the session lease, global candidate claim, shared guard, exact
artifact/archive checks, intent-before-effect transfer journal, cgroups, bounded
raw capture and final health. An incomplete incident identification cannot be
repeated. An existing rollback intent can continue only its result/quiescence
and health handling. It cannot cause another transfer.

## Timeline and final state

Times below are UTC on 2026-09-07 (2026-09-08 in Korea).

| Event | Time | Outcome |
|---|---|---|
| Candidate transfer result | 20:34:00 | Transfer completed, first and only candidate |
| Candidate observation | 20:34:28 | Android public health unqualified; NO_PROOF |
| Physical observation | 20:38:32 | Identity unproved; original miss preserved |
| Reviewed incident identification intent | 21:44:05 | One-run exception consumed |
| Resident rollback result | 21:44:08 | Transfer completed, first and only rollback |
| Final health and terminal record | 21:44:55 | Rooted resident Android healthy |

Final health established `SM-G986N` / `y2q` / `y2qksx` / `G986NKSS8IYC2`,
boot complete, boot animation stopped, UID/GID 0, Magisk 30.7 / 30700,
enforcing SELinux and stock `/system/bin/init` with `u:r:init:s0`. Final boot
identity was fresh under the existing final-health validator.

## Validation and retained evidence

The incident correction passed 15 focused tests covering preserved history,
wrong product/topology, intent/reporting cuts, pre-transfer failure, post-intent
health-only continuation, expiry, forbidden entrypoints/kinds, endpoint changes,
ctime-only continuity, validated terminal readback and host-only mode. A real
installed-profile host check read the actual prepared recovery closure, claim
and quiescence with zero device commands. Touched Python compilation and scoped
whitespace checks passed. Independent boundary/execution review returned
PASS_GO with zero findings; it did not rerun the earlier 211-test capability suite.

The reviewed incident source closure was
`3cbee9996d4cc7b2e6dd7a93e6fddb7cfcbec9080fe4f967b92316e357e18f91`.
Private evidence remains in
`workspace/private/runs/s20plus-g986n-p1-pid1-witness-f1/run-1788813079911545392/`.
The immutable authorization, close record and executed source snapshot are under
`workspace/private/outputs/s20plus_g986n/p1_recovery_exception_20260908/`.
Its `executed-source-closure/receipts.json` binds the pre-deactivation source
and policy bytes. Earlier source copies and the original activation records
remain retained separately; consumed records were not repinned.

The preparation work repeated too many broad checks after small comment and
fixture changes. Successful unchanged checks should be reused. The next useful
H0 work is the concrete early public-health rejection and recovery-transport
coupling, with bounded failure evidence; this report adds no next-device authority.

After terminal closure, the incident-only runtime hooks were retired during
TWRP baseline qualification to restore the existing retained-T2 source pins.
The pre-exception and executed exception sources remain preserved privately;
this retirement changes no consumed run or recovery result.
