# S22+ FYG8 P3.19 Process-v2 Candidate-Static H0

Status: `INDEPENDENT_PASS_GO / NOT READY / NOT ACTIVE`.

This host-only unit creates the first P3.19-specific Process-v2
candidate-static artifact. It does not register offline promotion, create a
ready/run manifest or approval, contact a device, invoke Odin, or grant D0,
D1, F1, recovery, replay, candidate-success, causal, MUX, host-silent, or live
authority.

## Exact result

The private result is
`process-v2-candidate-static-20260829-01.json`, 34,782 bytes, mode 0400,
link count one, SHA-256
`86cc71e19360281bb3bff9e8565a6f7c77132e3adc4e3400dd7e1285ad742a46`.
It consumes the independently reviewed Integration V2 `-05` result at
125,814 bytes / `16c9901f`, regenerates that complete result from current
sources, and requires exact typed equality before deriving any static claim.

The resulting contract binds:

- the authoritative 73-row plan with EUD index 38 and the single
  `s22plus_dwc3_event_latch.ko` overlay;
- the exact current and baseline intent, qualification, phase, AP, boot,
  LZ4, init, and child identities reopened by Integration V2;
- the authoritative fresh baseline, global consumed-candidate registry,
  prerequisite audit, and 17-case Download-request-cut recovery closure;
- the current P319 adapter, P310 Carrier model, and P308 telemetry source
  bytes; and
- all three terminal representations produced by the real bound C encoder,
  real Carrier, and current host decoder.

The admitted terminal mapping remains exact:

| terminal | proof class | accepted |
|---|---|---:|
| `COMPLETE` | `NONCAUSAL_SUCCESS_PATH` | true |
| `INCOMPLETE` | `NO_PROOF_EXPERIMENT_PRECONDITION` | false |
| `AMBIGUOUS` | `NO_PROOF_OBSERVER` | false |

`accepted=true` for `COMPLETE` is not candidate proof. Every causal,
candidate-success, MUX, and host-silent flag remains false and ACM remains
supplemental.

## Runtime boundary

The four witnesses `module_results`, `vbusdet_irq_tuple`,
`initial_status_classification_probe`, and `retained_carrier` remain required
future F1 outputs with `PENDING_FRESH_CANDIDATE_RUN` and
`accepted_as_preflight_fact=false`. That is the existing post-run
classification boundary, not a claim that those device facts were observed
host-side. Missing or malformed runtime evidence remains
`NO_PROOF_OBSERVER`; a sound precondition-failure terminal remains
`NO_PROOF_EXPERIMENT_PRECONDITION`.

The checker lives under `scripts/analysis/`, not `revalidation/`. Its only
operation is host-side reconstruction of retained evidence, and placing it in
the global raw-first acquisition population would change a full census count
without changing the protected device-acquisition boundary. The reviewed
raw-first `-18` and Integration `-05` therefore remain byte-valid rather than
requiring an unrelated repin loop.

## Validation and remaining gate

The 19,344-byte checker has SHA-256
`97538d60793830ab96b93c477c2e7c28d8ac3b80522f6994a098b3622a677bfe`.
Its 6,859-byte test has SHA-256
`d1cf6bb3cbf93cfaffcf8291e35056753c1d6ae4330b604047ccd3752715299c`.
Ten focused tests pass, including exact result regeneration and hostile
boolean/integer substitution, proof-class relabel, EUD-index, and candidate AP
identity drift.

## Independent review

Independent read-only hostile review returned `PASS_GO`. It verified that
`build_result()` validates and freshly regenerates reviewed Integration V2
`-05` before `_derive()` can construct the artifact, and that `_derive()`
binds the exact plan, reopened candidate artifacts, preflight authorities,
adapter sources, terminal mappings, and future witness contract. The retained
artifact reopened as a direct 34,782-byte mode-0400/link-count-one file at
`86cc71e1`.

The independent fast hostile selection passed 9/9; the implementation's full
10/10 selection additionally performed the 106-second byte-exact regeneration.
The reviewer confirmed the analysis-path source has no device-acquisition
primitive and all ready/run/approval/live/causal flags remain false.

A separate small unit may now register this exact schema in the shared offline
verifier and derive a ready manifest. Until that registration and its own
independent review pass, the existing fail-closed message `P3.19 Process-v2
offline promotion is not yet registered` remains correct and no F1 approval
may bind this artifact.
