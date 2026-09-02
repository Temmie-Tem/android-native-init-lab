# S22+ FYG8 P3.30 H0 build-normalization stop

Date: 2026-09-03
Target: `SM-S906N/g0q/S906NKSS7FYG8`
Tier: H0 only

## Outcome

P3.30 is not ready for F1. The bounded runtime and host observer unit exists,
but the candidate builder reached the same result-normalization failure twice
and this build line stopped under S22+ Rule 7. No device, ADB, Download mode,
Odin invocation, transfer, or partition action occurred.

The uncommitted P3.30 runtime adds only two non-authoritative pre-auth
diagnostics around the unchanged S328/HMAC path: `OPEN_PARSED` and `RNG`. Its
`getrandom` loop retries only `-EAGAIN`, at the inherited 100-ms cadence, for at
most 64 retries. The host observer retains actual partial TX/RX and bounded
failure metadata. Focused source tests passed 7/7. Current source identities
at the stop were:

- runtime: 8,818 bytes, SHA-256
  `c281a19568569195640fa73de72ae62fafca8481e17037934e595e8da6a77e6a`;
- observer: 15,035 bytes, SHA-256
  `a00589310609cbab776dd99a23325644406d4d52cc0038ab34ab11ae726b3240`.

## Build evidence

Private output ordinals `01` and `02` were left incomplete when the delegated
packaging task was interrupted. Root then used new no-clobber ordinals `03`
and `04`. Both produced byte-identical A/B boot-only AP files of 28,631,081
bytes, SHA-256
`f458498c1b33961a9a7049a3ad8e74d4ab67ab64e672ba20af21d074f418175b`,
but neither published `result.json`. Therefore none of these AP files is a
qualified candidate or eligible live input.

Ordinal `03` stopped with:

`P330 inherited result normalization failed: P328 inherited result normalization failed: P324 result projection header differs`

The single bounded repair changed the P3.30 wrapper to enter through P3.29's
normalizer and used fresh ordinal `04`. It stopped at the same underlying
`P324 result projection header differs` invariant. No third build was run.

## Diagnosis and next bounded unit

Static source tracing localizes the remaining mismatch to the inherited
delegate globals. P3.29 re-invokes P3.28's `_patch_delegate_modules()` after
rebinding its artifact, adapter, runtime, and observer; the current P3.30
wrapper does not. Consequently the nested P3.24 normalizer sees the fresh P330
result before its expected compatibility predecessor/header globals are
re-established.

The next bounded H0 unit should start from the retained failure evidence, add
that one delegate-rebind call at the same seam, select a new no-clobber output
ordinal, and exercise the normalizer with a captured representative result
before one real build. This is a proposed repair, not a PASS or authority.

Common evidence/core/live P330 registration is also uncommitted work in
progress. It must not be promoted, prepared, approved, or used until the build,
candidate-static, focused regressions, raw-first audit, and independent review
all close.

## Bounded follow-up resolution

The next H0 unit followed the proposed fixture-first path. A representative
P3.29 result carrying the retained partial P3.30 AP identity reproduced the
header failure without creating another candidate. Adding P3.28's existing
recursive delegate rebind then made that fixture pass.

Two distinct post-build audit failures were handled under their own Rule-7
signatures. Ordinal `05` built but its reopen found four diagnostic presentation
fields duplicated into the inherited byte-equal runtime-repair receipt.
Removing only those duplicates preserved the diagnostics in `framed_exec`.
Ordinal `06` built and passed the runtime audit, then exposed a stored-result
idempotence mismatch: its direct P3.29 predecessor had not been temporarily
projected to the P3.29 normalizer's P3.28 entry shape. The retained `06` result
was used as the failing fixture before that one compatibility projection was
added. No failed AP was promoted or transferred.

Corrected ordinal `07` builds and reopens exactly:

- result: 45,820 bytes, SHA-256
  `d2186404aaab0c1472d41d93a241c0ab32119561fe0a07ca231eb0b0ca3bacf1`;
- candidate A/B AP: 28,631,081 bytes, SHA-256
  `f458498c1b33961a9a7049a3ad8e74d4ab67ab64e672ba20af21d074f418175b`;
- Image: 41,490,944 bytes, SHA-256
  `7a730473a60cf454ba5a3df9dd992444196299b0397369531f3e171982ee8456`;
- `/init`: 82,032 bytes, SHA-256
  `4d744d3def07a000d0d31f5abfa323372709d4cac0d6493d8696cb0a0e70a7a7`;
- exact rollback AP: 23,367,721 bytes, SHA-256
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`.

The A/B APs are byte-identical and contain only `boot.img.lz4` at the Odin AP
boundary. Candidate-static was published privately as 26,330 bytes, SHA-256
`a81277fe317d87695b65bc6eb0b8956c8cd35d0e69c86e4eb6eb27d2212cd1a0`,
mode 0400. Its focused tests pass 4/4. The P3.30 prepare wrapper and P3.30
offline verifier pass in audit-only mode; neither promotion nor ready manifest
has been published. Independent review and raw-first audit remain required.

All follow-up work remained H0: no device, ADB, Download mode, Odin, transfer,
approval, or live authority occurred.

## Independent review and H0 publication

Independent read-only review returned `PASS_GO_P330_H0` with no material
blocker. It confirmed the non-authoritative diagnostic boundary, EAGAIN-only
retry, partial raw TX/RX retention, P3.30 key-helper binding, typed parser-error
path, exact ordinal-07 artifacts, and Rule-7 accounting. The proportional
raw-first audit passed across 1,840 Python files and 420 subprocess modules;
its private receipt is 26,327 bytes, SHA-256
`121a5975af2dbdc52b1ebe7efd31a31d3c6bb461ffa8cb66b5dfdd77fc5fb70c`.

After that review, the host-only promotion was published once. Its run manifest
is 1,065 bytes / `336e24fc`, static check is 1,982 bytes / `9fa54048`, and the
tracked ready manifest is 5,840 bytes, SHA-256
`06c83e25a89c73f34ea108eae95a157dbd2ea5b288ec59650833e44bc19dc97c`.
The ready manifest is a preparation input only. It grants no F1 authority;
fresh exact-target preparation, exact approval, and attendance remain required.
