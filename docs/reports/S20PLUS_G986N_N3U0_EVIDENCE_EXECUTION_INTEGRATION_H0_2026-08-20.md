# S20+ G986N N3-U0 evidence-backed execution integration H0

Date: 2026-08-20

Target: Samsung Galaxy S20+ 5G (`SM-G986N` / `device=y2q` /
`product=y2qksx` / `G986NKSS8IYC2`)

Status: **H0 PASS_GO - NOT ACTIVE**

## Scope

This bounded H0 unit connects the exact dormant concrete backend to the exact
atomic evidence owner and derives missing journal results only from complete
durable evidence. It adds no CLI execution surface and does not amend the
binding target contract. `EXECUTION_ACTIVE`, `BACKEND_ACTIVE`, and
`EVIDENCE_ACTIVE` remain false; rendered live authority, backend exposure,
integrated live consumer, physical-entry bridge, device commands, and
partition transfers remain false or empty.

The work also closes a concrete backend gap found by the new end-to-end host
fixture: after the exact ACM banner, the backend now performs a bounded
read-only Android return observation and binds the candidate boot identity.
Without that identity the exact automatic resident rollback source could not
be attributed.

## Frozen review candidate

| Input | Size | SHA-256 |
|---|---:|---|
| `workspace/public/src/scripts/revalidation/s20plus_n3u0_attended_f1_backend_h0.py` | 30,896 | `0d8a752e94ea34f5130a53fe2747c7e949561db54ba661d55c4af2db0a19e27b` |
| `tests/test_s20plus_n3u0_attended_f1_backend_h0.py` | 19,885 | `6514f1040d9d911e248d8a1f6a3b12a6e578aa680a60e94db84d4bf118eb30d2` |
| `workspace/public/src/scripts/revalidation/s20plus_n3u0_attended_f1_evidence_h0.py` | 23,833 | `730e5e78368894ef30e22d9e1f7d8356f6dfc00a536fc36b322ac0424cb84f09` |
| `tests/test_s20plus_n3u0_attended_f1_evidence_h0.py` | 15,605 | `384b1130a866893677c38ccc4c1678681471e8163b1ab649f199ca6e03595e94` |
| `workspace/public/src/scripts/revalidation/s20plus_n3u0_attended_f1_execution_h0.py` | 34,030 | `54d2330b8da43b4d76766155cf65a824f3a09bfa86cca06d8d9a5cb4729960fa` |
| `tests/test_s20plus_n3u0_attended_f1_execution_h0.py` | 17,447 | `2de90fedb9f0b28313f35ba6b113ed89fbc3050e893b2d422b3d028ed839c8a5` |

The backend binding is
`5561aabc35f20752702b8ef12ec6f8d4669bbef8b022ff5557c7925c34b9704b`.
The evidence-owner binding is
`c59992f48361429812475b6535c4ad927ee63cad81f61a1d4e2ac59567402f47`.
The execution-integration binding is
`f58862882da975e48ef15b8264fcaa68f6b4a328679a8eee7d092b888017313c`.
All three source statuses are `PASS_GO_NOT_ACTIVE`.

## Execution and evidence ordering

`ExecutionSession` exact-loads the journal, prior integration model, concrete
backend, and evidence owner. It constructs the exact `FixedBackend` internally;
the caller cannot supply a backend, callback, command, executable, path,
endpoint, source identity, or artifact. The only internal choices are the
finite reviewed operation names.

For each effect transition, the session:

1. publishes the exact journal intent;
2. creates a one-invocation in-memory eligibility marker;
3. consumes that marker before calling the fixed backend;
4. captures every actual subprocess return produced by that backend operation;
5. atomically publishes each command stdout, stderr, and typed result through
   the evidence owner;
6. atomically publishes one operation-return summary containing the full
   endpoint/artifact/classifier or observation receipt; and
7. derives the state-journal result only after re-reading all complete evidence
   and proving that semantic raw receipts equal the actual captured command.

An existing durable intent never recreates the in-memory marker. After process
restart, intent-only, raw-only, producer-error, and summary-publication cuts are
consumed and cannot call the backend again. A complete evidence summary may
publish a missing journal result with zero backend calls. If the journal result
already exists, its classification, outcome, endpoint, or raw receipt must be
exactly equal to the re-derived value.

The evidence owner now accepts the backend's exact 8 MiB Odin output bound and
provides one gated complete-operation read API. It retains the same atomic
no-replace, file-fsync, and directory-fsync publication order and fixed private
namespace.

## Hostile validation

The new focused execution suite passes **14/14**. It covers dormant-before-
backend behavior, complete evidence before journal result, result-only resume
with zero backend calls, raw publication interruption, producer exception,
typed return-code rejection, semantic-versus-command raw mismatch, mismatched
pre-existing journal result, source drift before backend construction,
direct-helper rejection without same-invocation intent creation, intent-only
restart no-replay, candidate-transfer result recovery, and the complete
automatic candidate-to-resident path with one backend call per named operation.

The backend and evidence focused suites add actual reboot/Odin command capture,
dormant capture-helper rejection, exact full-receipt binding, candidate Android
return attribution, complete raw reread, and the 8 MiB Odin bound. The current
five-module journal/integration/backend/evidence/execution aggregate passes
**92/92** after the final assertion correction, and the complete nine-module
N3-U0 aggregate passes **130/130**. `py_compile` passes for all
touched Python. No device-facing command was run by these tests.

The first independent review returned `NO_GO`: module-level
`_fixed_backend_call` and `_publish_captures` helpers still accepted a caller
backend or caller command/semantic receipt and could bypass the session's
fresh marker. The rotated candidate removes both helpers completely. Fixed
backend dispatch and evidence publication are now inlined after
`ExecutionSession._capture_fresh()` consumes the same-invocation marker; direct
invocation without that marker rejects before any backend call. The hostile
suite asserts that both former helper names are absent and that an intent-only
restart cannot populate the marker or publish evidence.

The second independent review returned `NO_GO` because the Odin capture wrapper
called `bounded_command`, whose real bootstrap implementation delegated back
through the wrapper and recursed. The current backend preserves the exact
original streaming callable and invokes it directly inside the capture closure.
The fake bootstrap now mirrors that real delegation and proves one Odin return
is captured without recursion.

Fresh exact-byte independent review returned `PASS_GO` for the complete dormant
rotation. The subsequent status/self-identity rotation changes no execution
logic or activation flag.

## Deliberate non-claims and remaining gates

This is not an active F1 runner. It still has no physical Download-entry
bridge, connected prepare/approval, target-contract N3-U0 authority, or live
CLI. Exact automatic rollback is modeled only when the candidate returns the
observed exact Android identity. If that observation is absent or uncertain,
the candidate effect remains consumed and only a separately reviewed physical
recovery bridge may continue.

Independent review and the authority-neutral status/identity rotation are
complete for this exact H0 closure. Physical-entry integration, full
reporting-cut review, target-contract amendment, mechanical activation, fresh
connected preparation, and fresh attended approval remain later independent
gates.

No device, USB endpoint, ADB, `su`, Odin, reboot, network, private live run, or
partition transfer was contacted by this H0 unit.
