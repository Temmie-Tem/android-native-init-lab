# S22+ FYG8 P2.42 E2 candidate H0 pass

Date: 2026-07-23 KST
Tier: H0
Status: `PASS_P242_E2_CANDIDATE_HOST_ONLY`
Device contact: none
Live authority: none

## Result

P2.42 produced one closed E2 host candidate. Two clean Full-LTO kernel builds
completed in about 38 minutes each with about 24.3 GB peak RSS. Their six
execution artifacts were byte-identical. Two independent package runs then
produced byte-identical boot-only APs from the reproducible kernel and the
two-build static userspace result.

The independent artifact checker reconstructed the candidate boot image,
generic ramdisk, and effective rootfs. It verified the source-bound E2 kernel,
static `/init` and child, exact FYG8 59-module stock closure, module order, and
absence of forbidden writers. The exact candidate then passed Process v2
offline evidence promotion. All build products and detailed evidence remain
under `workspace/private/`.

## Integration Finding

The first Process v2 promotion stopped fail-closed because the outer Odin AP
member uses a modern LZ4 frame while the boot-v4 inner ramdisk uses Samsung's
legacy LZ4 stream. The existing independent verifier accepted only modern
frames.

The shared verifier now dispatches only on the two exact magics. Modern Odin
members retain their frame descriptor, checksum, concatenation, and trailing
data checks. The legacy path is bounded to independent 8 MiB blocks and rejects
invalid sizes, truncation, output overflow, match-terminated blocks, short final
literal runs, and matches too close to the block end. The E2 path uses legacy
support only for the inner ramdisk; the outer AP member remains modern-frame
only.

The initial positive test fixture exposed a second fail-closed issue: the local
decoder accepted a match-terminated block that the pinned external decoder
rejected. Canonical LZ4 terminal constraints were added, the positive fixture
was corrected, and the malformed block became a negative parity test.

## Validation

- Two clean Full-LTO builds were byte-identical across all six pinned outputs.
- Two candidate package runs were byte-identical.
- Independent artifact closure and Process v2 offline promotion passed.
- The actual E2 legacy ramdisk decoded byte-identically with the internal and
  pinned external LZ4 decoders.
- `191` related regression tests, Python compilation, and `git diff --check`
  passed.
- Independent remediation review returned `GO_INDEPENDENT_REVIEW` with no
  remaining findings.

## Boundary

This is an H0 candidate result, not an E2 live result. No device was contacted,
no ready manifest or connected binding was created, no approval was issued,
and Odin was not invoked. The next bounded step is one immutable ready manifest
followed by connected read-only D0 preparation. Any F1 candidate attempt still
requires the new binding's fresh exact approval.
