# S22+ FYG8 P3.23 ACM-primary observer repair H0

Date: 2026-08-31

Target: `SM-S906N` / `g0q` / `S906NKSS7FYG8`

Status: `PASS_GO_P323_ACM_PRIMARY_H0`

## Finding

P3.22 did not retain a torn Carrier slot. Independent byte-level reanalysis of
both identical post-rollback reads shows valid CRCs for the header and both
slots. The actual transition is generation 92 stage `0x8f`/item 4 progress to
generation 93 stage `0x90`/item 0 failure `0x6726`. The older host semantic
model called the second slot `bad-body` because it did not admit this P3.13
intermediate contradiction route.

The runtime reached `p319_stock_publish()` with an open raw gadget TTY, but the
publisher discarded `tty_fd`. Its stock witness encoder then rejected before
the repaired Carrier bridge. The exact rejected encoder predicate was not
retained. This is two separate defects: the candidate had no direct host
arrival signal, and the retained host decoder mislabeled a valid producer
failure as integrity damage.

The consumed P3.22 formal verdict remains
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`; it is not replayable. The correction is
post-live H0 interpretation, not retroactive F1 success.

## Minimal P3.23 repair

P3.23 changes one publisher-entry line. It attempts the existing exact
49-byte, run-bound CDC ACM banner once before witness copy and stock encoding.
The Carrier path always continues unchanged afterward.

The two evidence axes are now explicit:

- Exact ACM receipt: proves native PID-1 reached the post-bind publisher and
  the candidate-bound USB ACM path reached the host.
- Retained Carrier: supplemental Max77705 experiment result or producer-failure
  diagnostic; it cannot erase ACM arrival and ACM cannot promote its missing
  scientific result.

The host terminal class for a complete candidate transfer, exact ACM receipt,
Download departure, topology continuity, guard release, exact rollback, and
healthy final return is
`PASS_F1_V2_ACM_PRIMARY_NATIVE_PID1_USB_ARRIVAL_AND_ROLLED_BACK`. Missing,
partial, extra-byte, wrong-endpoint, topology-drift, guard-failure, or
failed-transfer cases remain no-proof. Existing manifests retain their prior
ACM/Carrier precedence unless they explicitly bind the new versioned role.

## Host build

Private output:
`workspace/private/outputs/s22plus_fyg8_p323/stock-candidate-build-v1-20260831-03`

- Run ID: `c323f1e0a90b5e6d7c8a9b0c1d2e3f4b`
- Result: 39,365 bytes,
  SHA-256 `94075654a8bc4356b1bcda9a5abd822b13a2fe558647d1eaf2810d684e45e3ea`
- Candidate AP A/B: 27,279,401 bytes,
  SHA-256 `5f34e26cb2a0554a6f082ea18848f9a25f1149a38078ef3a5db94552b4040293`
- Image: 41,490,944 bytes,
  SHA-256 `0684c512f77dd4c3659a07fb16eb40fe2b32609483aa9823d7dae450e08925bf`
- Static `/init`: 80,552 bytes,
  SHA-256 `374b4a843e938a87b09754f49b55c2d85bf62f098f656235815932ad148e8bfd`
- Rollback: unchanged exact boot-only AP,
  SHA-256 `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`

The A/B artifacts are byte-identical and contain only `boot.img.lz4`; P319
through P322 identities are rejected. The build and audit-only reopen both
pass. The failed first presentation output and one `/tmp`-exhausted partial
attempt are preserved privately and are not readiness inputs.

## Validation and boundary

The P323 runtime/artifact/adapter/builder/reanalysis suites pass 19 tests. The
common evidence, Process-v2, and live suites pass 127 tests, including the
ACM-primary hostile cases and unchanged legacy behavior. Python compilation,
actual AArch64 static compilation, deterministic A/B packaging, and diff
checks pass. Independent review returned `PASS_GO_P323_ACM_PRIMARY_H0` with no
blocker in this H0 repair or its host artifacts.

The global raw-first current-tree smoke is not counted as a P3.23 failure. It
currently stops on the separately added S20+ host builder
`build_s20plus_g986n_recovery_adb_canary_h0.py`; none of the P3.23 sources is
the reported boundary bypass. That cross-target census coupling is left to the
S20+/auditor owner and is not carried forward as another P3.23 gate.

This work made no device contact, issued no ADB or Odin command, transferred no
payload, created no approval, and grants no D0, D1, F1, recovery, replay, or
live authority. P3.23 still requires exact common registration, candidate
static/promotion/ready generation, and validation that a supplemental Carrier
parser exception cannot discard an accepted ACM receipt. That added execution
closure then requires its normal independent review, fresh connected
preparation, and a fresh attended approval before any live action.
