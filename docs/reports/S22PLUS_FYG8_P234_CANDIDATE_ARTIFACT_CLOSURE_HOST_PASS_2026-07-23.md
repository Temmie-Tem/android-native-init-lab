# S22+ FYG8 P2.34 candidate artifact closure host pass

Date: 2026-07-23 KST
Tier: H0
Status: `PASS_P234_CANDIDATE_ARTIFACT_CLOSURE_HOST_ONLY`
Device contact: none
Live authority: none

## Result

P2.34 produced one candidate-specific E1A kernel and userspace closure, two
byte-identical deterministic boot-only AP packages, and the three immutable
offline evidence payloads required by Device Action Process v2. The generated
candidate remains private and no ready manifest, connected target binding,
approval, Odin session, or device action was created.

The candidate identity derives a non-model run identity and UNSAT tag from a
private nonce plus exact source receipts. The contract binds that identity to
the FYG8 target, E1A profile, decoder policy, base source hashes, generated
patch, compiled config, reachable-record proof, userspace binaries, kernel
image, reconstructed boot image, and AP.

## Clean Build Evidence

Two fresh Full-LTO builds ran sequentially on the FX-8300 builder with all
eight cores. The output tree was deleted between builds and no compiler cache
was used. Each build completed in about 39 minutes.

An initial pair exposed a reproducibility defect: a random private namespace
path entered DWARF and changed the SHA1 build ID. P2.34 now maps the private
repository root to `/private-repo` in both C and assembly debug paths. The
final two clean builds contain no `/tmp/s22-r4w1b-private-*` path and are byte
identical for:

- `Image`;
- `vmlinux`;
- `.config`;
- `System.map`;
- `vmlinux.symvers`; and
- `abi.xml`.

The independent linked audit also passed the required `kernel_init` and E1
writer call order, exact retained flush cardinality, and the `dc civac` plus
`dsb sy` cache-flush implementation.

## Candidate Evidence

- The candidate kernel fits the fixed boot-v4 kernel interval while preserving
  the header and ramdisk outside that interval.
- Two independent package runs produced byte-identical boot images, compressed
  members, AP archives, and artifact-result payloads.
- Each AP contains exactly one deterministic regular member named
  `boot.img.lz4`.
- Independent reconstruction, LZ4 round trip, MagiskBoot unpack, exact
  `/init` and child extraction, and writer exclusion passed.
- The candidate static result was promoted into exactly
  `candidate-static.json`, `run-manifest.json`, and
  `static-check-result.json`.
- The actual three payloads and actual candidate AP passed the common Process
  v2 `verify_offline_contract()` path.

## Review And Validation

The independent source review initially found incomplete cross-payload
identity binding, incomplete candidate-contract shape validation, and JSON
boolean/integer type aliasing. The verifier now requires exact candidate and
contract shapes, source/AP/config/run cross-bindings, all independent proof
flags, and type-strict counters and safety values. Coherently repinned negative
tests cover each case. The final bounded follow-up returned GO with no
actionable finding.

Ninety-nine focused P2.34, P2.33, common Process v2, and historical manifest
tests passed. Historical bundle SHA pins were refreshed only after the
execution-critical source was frozen and independently reviewed.

## Build Efficiency Rule

Full-LTO is a final-candidate qualification step, not an implementation-loop
default. Ordinary source and contract iterations use focused host tests and,
when compilation is needed, should use a separate non-authoritative
thin/no-LTO output with a development-only cache. Final F1 candidates retain
clean, uncached, source-matched Full-LTO builds so cached objects cannot replace
the independent reproducibility proof.

## Boundary

P2.34 is H0 only. F1 remains inactive. The next bounded unit is connected D0:
reconfirm one exact healthy S22+ target, a clean retained baseline, the exact
candidate and rollback AP identities, ordinary regular paths, physical
Download recovery, and a new empty journal. Only after that unit closes may a
fresh exact F1 approval be requested.
