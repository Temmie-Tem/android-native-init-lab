# S22+ FYG8 P3.19 Candidate/Baseline Cross-Binding H0

Status: `NOT_READY_P319_RUNTIME_CLASSIFICATION_PENDING_H0`.

Review: **INDEPENDENT PASS_GO / NOT ACTIVE**.

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
The first no-clobber `-03` receipt is preserved at 121,247 bytes, mode 0400,
link count one, SHA-256
`56ecefbcc7b051c9efb79e806f83754a0e20df9febc2c84c7c5d2ae4563cba11`.

It reported `candidate_baseline_cross_binding.status=PASS_AUTHORITATIVE`, zero
blockers, and `source_closure_pass=true`. It remained
`NOT_READY_P319_RUNTIME_CLASSIFICATION_PENDING_H0` with
`runtime_classification_gate_pending=true`; `ready`, `runner_ready`, every
ready/run/approval manifest flag, device contact, D0/D1/F1/live authority,
replay, candidate success, and causal result false.

## Hostile-review artifact-reopen repair

Independent review rejected `-03` because the phase receipts were byte-pinned
but their nested A/B artifact identities were only compared with each other.
If both sides were replaced by the same forged size/SHA objects, the serialized
comparison still passed without reopening the named AP, boot, LZ4, init, or
child files.

The repair pins the five expected identities as constants and reopens all A/B
files in both the baseline `-53` and current `-55` phase roots. Each file must
be a direct mode-0400, link-count-one regular file of the exact size; SHA-256 is
streamed while device, inode, mode, link count, size, and mtime remain stable.
The result records all 20 file receipts. A new hostile test replaces both
phase receipts and both A/B sides with equal forged identities and confirms
`FRESH_BASELINE_CANDIDATE_IDENTITY_DRIFT`.

The repaired source is 68,331 bytes / `91034271`, and its 34,208-byte /
`ffc1d1dd` focused test suite passes 24/24. The new no-clobber `-04` receipt
preserves `-03` as its direct predecessor and is 125,735 bytes, mode 0400,
link count one, SHA-256
`77416056429e60d65564b0e2db55e88128fa03ff7042373ff820f3f8678b8ca3`.
It has the same zero-blocker, source-closure-pass, runtime-pending and all-false
authority/action result as `-03`, now backed by exact retained artifact bytes.

## Validation and boundary

The focused Integration V2 suite passes 24/24, including exact retained
cross-binding and hostile missing/forged/source-key/paired-artifact drift. The
raw-first documentation suite passes 21/21. Touched Python compiles and
`git diff --check` passes. The retained `-04` bytes are independently
regenerated before commit and must remain byte-identical.

This unit changes no candidate bytes, candidate registry state, target
contract, transfer/recovery machinery, A90 path, or S20+ path. It grants no
device or live authority.

Independent read-only re-review returned
`PASS_GO_P319_PROCESS_V2_CANDIDATE_BASELINE_CROSSBIND_H0_CAPABILITY_V1`.
It ran the paired-forgery hostile case, independently reopened all 20 artifact
files, and confirmed exact `-04` regeneration, predecessor preservation,
`70/53/17` full-tail review accounting, and every authority/action/causal flag
false. This qualifies only the exact H0 cross-binding; it does not qualify the
future P3.19 Process-v2 registration or ready manifest.
