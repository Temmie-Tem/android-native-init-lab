# S22+ FYG8 P3.19 Process-v2 Stock-Adapter Registration H0

Status: `IMPLEMENTED_REVIEW_PENDING / NOT READY / NOT ACTIVE`.

This host-only unit registers the existing P3.19 stock-witness adapter in the
shared Process-v2 evidence, source-binding, and live-result paths. It does not
create a candidate-static artifact, ready or run manifest, approval, device
contact, D0, D1, F1, recovery, replay, candidate-success, causal, or live
authority.

## Exact registration

The evidence dispatcher accepts exactly this tuple:

- source contract `s22plus-fyg8-p310-carrier-v2-hsphy-attribution-v1`;
- userspace overlay `s22plus-fyg8-p319-stock-witness-carrier-v1`;
- decoder `s22plus_fyg8_p319_stock_witness_carrier_v1`; and
- profile `E2`.

It validates the P310 Carrier geometry and the P3.19 decoder round trip, then
applies the adapter's strict acceptance key set and identity. The candidate
source override replaces only P310 telemetry-decoder semantics. Execution
receipts bind exactly the adapter source, P310 carrier model, and P308 telemetry
spec through the adapter's three-key `source_bytes()` closure. P319 overlay
metadata is validated directly; no P318 intent, topology, latch, MUX, or
host-silent contract is imported.

The current P3.19 qualification is not a generic Process-v2 candidate-static
artifact. Offline promotion therefore stops explicitly with
`P3.19 Process-v2 offline promotion is not yet registered`; it cannot fall
through to P310 or P318 static semantics.

## Result projection

The retained classifier preserves the complete P3.19 adapter result rather
than treating generic `accepted=true` as candidate proof:

| retained state | proof class | live verdict | outcome class |
|---|---|---|---|
| `COMPLETE` / `0x6724` | `NONCAUSAL_SUCCESS_PATH` | `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK` | `p319_noncausal_success_path_rollback_verified` |
| `INCOMPLETE` / `0x6725` | `NO_PROOF_EXPERIMENT_PRECONDITION` | `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK` | `p319_experiment_precondition_unproved_rollback_verified` |
| `AMBIGUOUS` / `0x6726` | `NO_PROOF_OBSERVER` | `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK` | `p319_observer_no_proof_rollback_verified` |

Malformed, foreign, and multiplicity cases also remain
`NO_PROOF_OBSERVER`. Every path retains `causal_result_allowed=false`,
`candidate_success=false`, `mux_result_claimable=false`, and
`host_silent_claimable=false`. ACM is optional and supplemental; absence or a
negative observation cannot outvote the retained stock classification.

The final two identical raw-first `/proc/last_kmsg` reads remain the evidence
source. The live state stores the exact stock projection and proof class, and
validation compares them directly with the classification reconstructed from
the final raw evidence. A state-only proof-class relabel is rejected.

## Raw-first boundary

Because the shared live runner is an active raw-first source, its new exact
199,860-byte / `ec932139` identity is repinned in the permanent auditor. The
unchanged populations are 1,747 revalidation Python files, 412 subprocess
modules, 128 pre-boundary device sources, 126 closed observer sources, and 47
legacy observer sources; their semantic inventory hashes change only where the
modified evidence/core files are members.

The 76,346-byte / `bcf06725` auditor has normalized self-hash `feabe85c` and
publishes new private receipt `-16`, 15,075 bytes, mode 0400, link count one,
SHA-256
`8fb852498444fa65c79ce2f2ba4332ae21f0b175055eec658a1148f3c1809fac`.
The `-15` 15,075-byte / `a93097d5` predecessor and all earlier receipts remain
unchanged.

## Exact source identities

| source | bytes | SHA-256 |
|---|---:|---|
| typed evidence | 243,987 | `f2176585719ebc616cd37024585cd039af20ecb0563f8823fea6e15d3cea2112` |
| Process-v2 core | 86,025 | `b13d196098d6c1819b25bf3d2727ebc91631831fdea0e694c5335968606995cf` |
| live runner | 199,860 | `ec9321390365b89a453b28fffc6c6989dfe7a3009b0c2d721fb44c372c16959a` |
| registration test | 10,034 | `d2dfde1ac9b6b53e691f227c0dc61902dc1c2a4e55dc05d691479a4c28495481` |

## Validation and remaining boundary

P319 registration plus existing evidence, core, live, and common Process-v2
docs pass 151/151. P319 result-contract arming plus the retained P318 native
fixture pass 13/13, and P318 live integration passes 5/5. Raw-first docs plus
ledger taxonomy pass 60/60; the selected current-tree, frozen-inventory, and
receipt gates pass 4/4 after the exact repin. Touched Python compiles and
`git diff --check` passes.

The independently reviewed Integration V2 `-04` remains immutable evidence,
but these execution-critical shared source changes intentionally make its old
source projection a predecessor. After this registration receives independent
review, a new versioned Integration V2 result must repin the reviewed shared
identities before candidate-static promotion. No ready manifest may consume
`-04` as current authority.
