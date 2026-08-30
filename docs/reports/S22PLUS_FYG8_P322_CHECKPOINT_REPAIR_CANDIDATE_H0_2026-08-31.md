# S22+ FYG8 P3.22 checkpoint-repair candidate H0 closure

Date: 2026-08-31

Target: `SM-S906N` / `g0q` / `S906NKSS7FYG8`

Verdict: `PASS_P322_STOCK_CANDIDATE_BUILD_H0_CHECKPOINT_REPAIRED`

## Purpose

P3.21 booted normally but retained a CRC-valid, semantically invalid generation-93
slot. Host re-derivation proved that `p319_stock_bypass_to_pair()` entered with
generation 92, required generation 105 immediately, and wrote failure detail
`0x6720` into a position where that detail was not legal.

P3.22 repairs only that checkpoint bridge. It is a new candidate, not a replay of
P3.21.

## Bounded change

The builder reopens the exact P3.21 12-file stock source closure. Only
`s22plus_fyg8_p290_e3_runtime.inc.c` changes, and within it only
`p319_stock_bypass_to_pair()`:

- terminal or generation greater than 105 still fails closed;
- generation below 105 advances through the finite missing positions;
- generation 92 therefore performs exactly 13 progress writes for positions
  92 through 104 before the existing payload positions 105 and 106;
- diagnostic/provider code, the wrapper, checkpoint writer, child, latch module,
  module plan, and all other source members remain unchanged.

The repair follows the already present P3.13 bridge shape. A compiled C fixture
executes the 92-to-105 path and the terminal/overrun failures.

## Fresh identity and build

The fresh run ID is
`c322f1e0a90b5e6d7c8a9b0c1d2e3f4b`. The P3.19 Image is transformed only at
its one raw run-ID string and embedded IKCONFIG line. Its gzip stream remains
40,695 bytes with header `1f8b0800000000000203`; Image size and layout remain
unchanged. No kernel compilation or Full-LTO ran.

Static userspace is recompiled and the boot-only AP is packaged twice. `/init`
is the only changed userspace artifact; the child reproduces its P3.21 bytes.
The A/B outputs are byte-identical and independently unpacked to join the same
P3.22 ID across Image IKCONFIG, Image rodata, and `/init`. P3.19, P3.20, and
P3.21 identities are rejected by the P3.22 adapter.

## Artifact identities

- Result: 39,444 bytes,
  `ed8cc4a3a17d48fe84a8f7da98fe26bcdb74209821c3dcfdff7636d6cb2a4082`.
- Image: 41,490,944 bytes,
  `29606fb42162d629bdfbd752e408b8962121e0a25b17dbee925d6366e762275f`.
- `/init`: 80,504 bytes,
  `d2350352ddbc76ec116f32c83e33b7aaf9e8c229671778341843dd29a94de3e5`.
- boot image: 100,663,296 bytes,
  `941fa81dcc8bc58801cbfe36a4e1d857f92d27bee56e9e50c6218cd8d93ba0df`.
- `boot.img.lz4`: 27,269,441 bytes,
  `c27d71c3c2ee7edaebab871373539ca03dd106f085813e024abc652d2ff52f07`.
- A/B AP: 27,279,401 bytes,
  `ff7f189d02ba7c124ba6bc805f9a8f385bc4995fb235b5c13b4e436ae69cd412`.
- Exact rollback remains 23,367,721 bytes,
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`.

The private output is
`workspace/private/outputs/s22plus_fyg8_p322/stock-candidate-build-v1-20260831-02`.

## Validation and boundary

The final build completed in 13.75 seconds wall time. Builder `--audit-only`,
real AP unpack/join, deterministic A/B comparison, rollback reopening, adapter
fixtures, artifact transform tests, and the executed checkpoint fixture pass.
Independent hostile review returned `PASS_GO_P322_H0` with no material blocker.

The candidate-build unit was H0 evidence only. At that stage it created no D0,
D1, F1, recovery, replay, approval, run manifest, ready manifest, live
authority, USB claim, or candidate-success claim. P3.21 and all earlier
candidates remain consumed and unchanged. The subsequent promotion below binds
these exact bytes and the current common Process-v2 closure.

## Process-v2 H0 promotion

The exact P3.22 candidate is now registered as a distinct Process-v2 stock
observer path. It does not alias P3.21: the common verifier accepts the P3.22
run ID, overlay, schemas, source receipts, and AP while rejecting the P3.19,
P3.20, and P3.21 identities. `COMPLETE` remains the non-causal success path;
the separate no-proof outcomes and rollback requirements remain unchanged.

The thin promotion wrapper exact-loads the reviewed P3.21 publisher source but
supplies every P3.22 path, schema, run, and timeout argument explicitly. It
uses a P3.22-only temporary directory and module-local proxies rather than
mutating shared P3.21 constants. The first H0 rehearsal exposed one inherited
presentation literal, `P321_STOCK_OBSERVER_V4_RETAINED`; before any device
contact, the wrapper was narrowed to rotate only that literal and its dependent
canonical run-manifest hash. The corrected rehearsal and publication pass.

Published identities are:

- candidate-static: 24,398 bytes,
  `650f56785a0c0c165c0a276a56b9bd00e406a8126696e3522530f2a06a01745a`;
- promotion run manifest: 1,021 bytes,
  `ce92c77b3f32d524618e3675924e1276ecc5b60a14090223179d15182821fa5f`;
- promotion static result: 1,835 bytes,
  `054e710fe839a7adaefcfa96d3c0dc0872925b7c305c48b7dfe41744c3d1a2c3`;
- public ready manifest: 2,743 bytes,
  `37b5c94fdc7098f3e078bb309f52177a691c48495aba26c9d1cfc5cfb2ceecb3`.

The common Process-v2 suite passes 120 tests, the P3.22 artifact/static suite
passes 22, the ready/promotion suite passes 3, and the current-tree raw-first
audit passes after membership-only S20+ census drift was re-pinned. `py_compile`
and `git diff --check` also pass. The public status is
`ready-for-f1-approval`, which is only a non-consuming H0 declaration. It does
not grant connected D0, F1 transfer, replay, candidate success, USB causality,
or live authority; those require a fresh exact target preparation and one
fresh attended approval.
