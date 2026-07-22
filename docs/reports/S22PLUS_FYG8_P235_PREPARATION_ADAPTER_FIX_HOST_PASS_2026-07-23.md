# S22+ FYG8 P2.35 preparation adapter fix host pass

Date: 2026-07-23 KST
Tier: H0
Status: `PASS_P235_PREPARATION_ADAPTER_FIX_HOST_ONLY`
Device contact: none
Live authority: none

## Result

The first P2.35 preparation line stopped after two manifest validations failed
before any connected read, journal allocation, approval, Odin invocation, or
device action. The first manifest used the wrong E1A terminal-stage constant.
The corrected second manifest reached the common bundle verifier and exposed
an adapter boundary defect: the E1A run manifest stores a binary identity as
`size` plus `sha256`, while the common file-pinning core supplies the same
identity with an additional non-authoritative `path` field.

The verifier previously compared those dictionaries directly and rejected the
valid pinned receipt. It now compares only the already pinned binary identity.
The common core still selects the acceptance-contract path, opens a direct
regular file, verifies its expected size and SHA256, reads from that descriptor,
and revalidates the pinned path identity. No path or artifact check was removed.

## Validation

- A regression reproduces the common core's path-bearing receipt shape.
- Wrong size, wrong SHA256, missing identity, and substituted candidate content
  remain rejected before any authority is produced.
- The previously rejected exact private bundle passes `verify_bundle()` with
  offline contract verification true and device contact, Odin invocation, and
  live authorization all false.
- A related host-only superset passed 124 tests.
- All eight affected historical bundle pins were independently recomputed; each
  change is explained solely by the execution-critical evidence source hash.
- Independent bounded safety review returned `GO` with no actionable finding.
- `git diff --check` passed.

## Boundary

The two failed preparation manifests are retained as private evidence and are
not reusable. This H0 repair does not resume the stopped preparation line and
does not grant D0 or F1 authority. P2.35 must begin a fresh connected D0 line
with a new manifest and new empty journal before any fresh exact F1 approval can
be requested.
