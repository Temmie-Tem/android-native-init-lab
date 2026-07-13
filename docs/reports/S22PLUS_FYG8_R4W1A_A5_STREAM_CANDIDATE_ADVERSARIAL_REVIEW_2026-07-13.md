# S22+ FYG8 R4W1A A5 Stream Candidate Adversarial Review

Date: 2026-07-13 KST  
Scope: HOST-ONLY, READ-ONLY independent review of commit `c889e14f`  
Reviewer: Claude Opus 4.8, high effort, conversation
`290dc782-0f91-41bf-b876-b7aedb9e0903`  
Verdict: `GO_TO_SEPARATE_POLICY_ACTIVATION_REVIEW`

## Boundary

This review evaluated the source-ready successor gate without activating its
draft policy. It performed no device contact, build, image generation, flash,
write, or live execution. The binding candidate policy remains absent from
`AGENTS.md`; the helper therefore remains `DRAFT_INACTIVE` and cannot authorize
a candidate run.

## Evidence Rechecked

- all helper, test, historical-oracle, qualifier, A4-result, policy-draft, and
  boot-only AP pins resolved to the expected bytes on disk;
- the A4 qualifier returned
  `PASS_R4W1A_STREAM_ORACLE_EVIDENCE_QUALIFIED_HOST_ONLY` while retaining
  `candidate_live_authorized=false`;
- the successor `--offline-check` returned
  `PASS_R4W1A_STREAM_CANDIDATE_OFFLINE_CHECK` with `policy.active=false`,
  `policy.state=DRAFT_INACTIVE`, `candidate_consumed=false`, and no device
  contact, write, or flash;
- 25 successor/qualifier tests and 32 parent/oracle tests passed;
- no candidate ACTIVE whole-line sentinel exists in binding `AGENTS.md`;
- the helper invokes Odin only through `--reboot -a <AP> -d <device>`, and the
  candidate, Magisk rollback, and stock fallback APs each contain only
  `boot.img.lz4`;
- no serial leak or non-boot dangerous path was found in the reviewed commit.

## Findings

No CRITICAL, HIGH, or blocking MEDIUM finding was found. No path can produce
the success verdict without a verified Magisk rollback, stable candidate
Android samples, exact 1/1 marker cardinality in both the streamed archive and
its `/proc/last_kmsg` section, unchanged `/bugreports` inventory, and parser to
stream identity. Stock fallback is cleanup-only and cannot produce PASS.

### LOW-1: Timeline Semantics Annotation

The ambiguous-rollback early return in
`s22plus_fyg8_r4w1a_stream_candidate_live_gate.py` appends the canonical
rollback timeline events without the explanatory `timeline_phase_semantics`
annotation used by the nearby rollback-not-verified path. The verdict remains
fail-closed with rc 20. This is telemetry clarity, not a safety defect.

### LOW-2: Negative Test Coverage

The activation bundle should add focused negative tests for:

- ACTIVE sentinel present while one policy pin is absent;
- a missing draft pin in `verify_policy_draft`;
- `stream_bugreport` raising inside `capture_stream_oracle`.

The corresponding implementation paths are fail-closed by inspection; the
missing cases reduce regression evidence rather than creating a current
false-PASS path.

### LOW-3: Private A4 Reproduction Dependency

The pinned A4 result and run evidence are under gitignored
`workspace/private/`. Absence fails closed, but a policy-activation review must
retain those exact private artifacts to reproduce the qualification result.

### LOW-4: Parser Identity Naming

`parser_stream_identity_match` compares values derived from the same local
streamed file. Its useful guarantee is that the parser consumed the host-side
streamed ZIP and that the same file remained stable across parsing. The name
is broader than the actual guarantee, but the check is adequate.

## Residual Live Questions

Only a separately authorized run can prove that the retained PID1-exec marker
lands in the candidate boot's `/proc/last_kmsg` and that real Odin, Download,
Android, and Magisk transitions behave as modeled. Marker absence returns rc
41 rather than PASS.

## Usage Measurement

The same Claude conversation was measured immediately before and after the
review:

| Metric | Before | After |
|---|---:|---:|
| Current-session quota | `75%` | `85%` |
| Weekly all-model quota | `77%` | `79%` |
| Free context | `937.6k` (`93.8%`) | `823.5k` (`82.3%`) |
| Message context | `14.6k` (`1.5%`) | `128.9k` (`12.9%`) |

The CLI directly reported `$4.76`, API time `9m 15s`, wall time `16m 55s`,
`69` input tokens, `32.2k` output tokens, `4.6m` cache-read tokens, and `163.6k`
cache-write tokens for the session. Subscription percentages are rounded and
account-wide; the `+10` and `+2` point deltas are operational measurements, not
token billing.

## Decision

The A5 gate is source-ready and safely inactive. It may advance only to a
separate SHA-pinned policy-activation review. Before any live candidate run,
the exact ACTIVE clause must be independently reviewed and committed into
binding `AGENTS.md`, all pins must be rechecked, and the operator must provide
fresh attended approval. This review itself authorizes none of those actions.
