# S22+ FYG8 P3.10 Carrier v2 JSON serialization incident

Date: 2026-08-09 KST  
Target: Samsung Galaxy S22+ FYG8 only  
Classification: `HOST_OBSERVER_SERIALIZATION_FAILURE_AFTER_ROLLBACK`

## Outcome

The P3.10 candidate and exact Magisk rollback each transferred once. The
operator observed one normal candidate boot without a boot loop. The exact ACM
observer timed out. Exact rollback completed and rooted FYG8 Android returned.

The original runner then failed while persisting final host state. Both final
retained reads and final Android health had already been collected. The failure
did not represent a candidate, rollback, USB, or device-health failure.
Candidate replay and a second rollback transfer were prohibited.

A recovery-only host adapter, bound to the frozen runner, prepared receipt,
approval binding, exact `ROLLBACK_FLASHED` journal state, and exactly one
candidate plus one rollback result, reused the two durable retained reads. It
prohibited Download requests and every transfer function, revalidated the
exact S22+ identity and health, and closed the original journal. Final state is
`CLOSED`, exact rollback is verified, and `recovery_required=false`. A90
received zero commands.

## Root cause

Carrier v2 slots contain a bounded `payload: bytes` field. The carrier model's
`decode_record()` intentionally returns raw bytes so request/application model
operations remain lossless. The P3.10 telemetry decoder passed those nested
bytes through its observation `records` list. The live runner then placed that
classification under `final_evidence.observer.classification` and called the
strict JSON state writer.

Python rejected the nested bytes while serializing `live-state.json`. The
failure occurred after the durable `rollback_flashed` transition and after the
two final reads, but before `HEALTH_VERIFIED` could be recorded.

## Recovery evidence

- Durable boundary before repair: `ROLLBACK_FLASHED`.
- Candidate transfer results: exactly one, `odin_transfer_completed`.
- Rollback transfer results: exactly one, `odin_transfer_completed`.
- Final retained reads: two, nonempty, byte-identical, and full length.
- Recovery adapter SHA-256:
  `6af64a7fd62ba139612f4f436b4449648f5ae1f682581f7ee875f6edcaa1d535`.
- Independent review: `PASS_GO` for that exact SHA and durable boundary.
- Final live result SHA-256:
  `85f610fbc6ca009ff9a85d8697c8ccb235f89b32741636d2cfa7b8f51e0bc680`.
- Final verdict: `DIAGNOSTIC_F1_V2_RETAINED_ONLY_ROLLED_BACK`.

Private raw evidence remains under
`workspace/private/runs/device-action-f1-live-v2/` and is not committed.

## P3.10 diagnostic result

The final retained evidence contains one normal adjacent pair with clean
integrity, exact count one, family count one, foreign count zero, and no
degraded or contradiction record.

1. Generation 106, stage `0x92`, item 1, detail `0xD1B`:
   EUD cache value zero; init reached without the EUD CSR message; no DPDM
   callback was seen; and before init a clock call reported
   `clocks_enabled=0,on=1`.
2. Generation 107, stage `0x93`, item 0, detail `0x4005`:
   the 12 init-local clock return callsites were not reached; QSCRATCH was hit
   once with VBUS-valid and software session-select both set.

The pair refutes EUD ownership at both measured samples. It also shows that a
clock-enable request occurred before init and explains the missed init-local
calls: the subsequent init call encountered the already-enabled path. The
wrapper's QSCRATCH VBUS/session programming was present. The earlier clock call
ran outside the 12 return probes, however, so its discarded prepare/enable
return values remain unmeasured. These are negative attributions; they do not
identify why the candidate pull-up failed to become a host-visible enumeration.

## Permanent correction

Only the P3.10 telemetry decoder's classified observation output is normalized
for JSON. Nested bytes become an unambiguous object:

```json
{"encoding": "hex", "value": "<lowercase hex>"}
```

The raw carrier model, `decode_record()` bytes ABI, P3.08 pair semantics, and
shared P3.01 contracts remain unchanged. A regression now requires the actual
P3.10 evidence-adapter result to serialize with strict `json.dumps()`. The
actual retained P3.10 record and all focused carrier/integration tests pass.

No further F1 may reuse the consumed P3.10 candidate.
