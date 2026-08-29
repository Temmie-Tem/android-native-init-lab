# S22+ FYG8 P3.19 Candidate/Baseline Cross-Binding H0

Status: `NOT_READY_P319_RUNTIME_CLASSIFICATION_PENDING_H0`.

Review: **IMPLEMENTED / REVIEW_PENDING / NOT ACTIVE**.

This host-only unit closes one provenance gap between two already reviewed
P3.19 inputs. The fresh-baseline V3 receipt identified candidate qualification
`-10`, while the current Process-v2 integration consumed requalification
`-11`. Each input was independently valid, but the integration did not prove
that they represented the same candidate bytes.

The repair adds one P3.19-specific result component to the existing Integration
V2 source. It does not add a generic framework, fork the F1 process, create a
ready or run manifest, or contact a device.

## Exact cross-binding

The new `candidate_baseline_cross_binding` component reopens the retained
baseline and current intent, qualification, and phase receipts at their exact
paths, sizes, SHA-256 values, modes, and link counts. It then proves:

- target, run ID, fixed Image, 73-row module plan, E2 profile, candidate window,
  and guard lifetime are equal;
- the only changed `SOURCE_KEYS` member is `target_contract`, from
  14,926 bytes / `e429c80c` to 15,287 bytes / `e220df44`;
- baseline phase 1 `-52` and current phase 1 `-54` are both 382,264 bytes /
  `982f903f` and byte-identical;
- baseline phase 2 `-53` and current phase 2 `-55` are both 392,886 bytes /
  `21beec5d` and byte-identical; and
- the phase-2 A/B candidate and userspace receipts agree exactly.

The resulting artifact identities are:

| artifact | bytes | SHA-256 |
|---|---:|---|
| AP tar.md5 | 27,279,401 | `db5666ac794dfbf6f64192d7ea341ed79ff330f03db74c57da5ef61f659032f6` |
| boot.img | 100,663,296 | `2b492a71808a0483f62896eb804042da38ed9ba7867aea045c5de630c9a86cb1` |
| boot.img.lz4 | 27,267,991 | `0491d50adecf485d10ec5e58ea4f58c2f62a874897564fb7151059348205c7e0` |
| init | 80,080 | `f6e6ea932c6c5297e18a932197e2fe1a131fac93c9caff9416d8fb873b055acb` |
| child | 1,376 | `eb3c072b41ab4d4953fd1d862388d3be5ca5a40e9a07f074cb273f96a28557cf` |

Any missing or forged component, receipt identity drift, source-key delta
outside `target_contract`, phase-byte drift, or candidate artifact drift adds
the explicit blocker `FRESH_BASELINE_CANDIDATE_IDENTITY_DRIFT`. Result
validation independently recomputes the component from retained evidence; it
does not trust the serialized success flag.

## Successor receipt

The preserved predecessor is private Integration V2 `-02`, 118,384 bytes /
`d21bf634a4c5a07dd55bc10b62e40b57d67ce378a7d9a06a996cbdb38931205f`.
The new no-clobber `-03` receipt is 121,247 bytes, mode 0400, link count one,
SHA-256
`56ecefbcc7b051c9efb79e806f83754a0e20df9febc2c84c7c5d2ae4563cba11`.

It reports `candidate_baseline_cross_binding.status=PASS_AUTHORITATIVE`, zero
blockers, and `source_closure_pass=true`. It remains
`NOT_READY_P319_RUNTIME_CLASSIFICATION_PENDING_H0` with
`runtime_classification_gate_pending=true`; `ready`, `runner_ready`, every
ready/run/approval manifest flag, device contact, D0/D1/F1/live authority,
replay, candidate success, and causal result remain false.

## Validation and boundary

The focused Integration V2 suite passes 23/23, including exact retained
cross-binding and hostile missing/forged/source-key/artifact drift cases. The
raw-first documentation suite passes 21/21. Touched Python compiles and
`git diff --check` passes. The retained `-03` bytes are independently
regenerated before commit and must remain byte-identical.

This unit changes no candidate bytes, candidate registry state, target
contract, transfer/recovery machinery, A90 path, or S20+ path. It grants no
device or live authority. Independent changed-closure review remains required
before the cross-binding can be used by the later P3.19 ready-manifest unit.
