# S22+ FYG8 P2.42 E2 pipeline preflight host pass

Date: 2026-07-23 KST
Tier: H0
Status: `PASS_P242_E2_PIPELINE_PREFLIGHT_HOST_ONLY`
Device contact: none
Live authority: none

## Result

The profile-driven P2.34 candidate pipeline now accepts the P2.41 E2 source
contract and binds the exact 59-module FYG8 stock closure, profile-3 userspace,
effective rootfs, executable identities, and candidate AP payload. This unit
does not claim an E2 kernel build or candidate: the two clean Full-LTO builds,
two deterministic package runs, and offline Process v2 promotion remain the
next H0 step.

## Execution-Critical Closure

The common boot-only AP verifier now requires one MD5-valid canonical USTAR
archive with one direct regular `boot.img.lz4` member. Candidate metadata must
be deterministic. The proven Magisk rollback remains accepted by exact AP hash
with its historical metadata, while retaining the same one-member, USTAR, MD5,
regular-file, and pathname gates.

The independent LZ4 path validates header, block, and content checksums,
rejects dictionary, dependent-block, concatenated, and trailing frames, and
decodes the actual candidate member before E2 acceptance. The exact extracted
boot image is parsed through boot-v4, its kernel identity is checked, and the
generic ramdisk is decoded and audited from its actual CPIO bytes.

The E2 rootfs audit requires static AArch64 `/init` and child executables with
the expected entrypoints, root ownership, mode `0750`, one link, one derived
run identity, every required runtime/module string, one child token, and no
forbidden shell, block-write, configfs, ACM, or `sec_log_buf` authority. The
effective rootfs composes the candidate generic ramdisk with the pinned stock
`vendor_boot` layers and rejects duplicate, alias, override, module-byte, and
module-order changes.

The common F1 runner version moved to host core 2 because the AP parser and E2
payload closure are execution-critical. Historical core-1 manifests are
therefore intentionally invalid and cannot authorize a later run.

## Validation And Review

- 187 focused and regression tests passed.
- Actual prior candidate and proven Magisk rollback AP members decoded byte
  identically with the pure-Python and pinned external LZ4 decoders.
- Adversarial tests cover USTAR prefix substitution for candidate and rollback,
  checksum corruption, dependent frames, nested JSON numeric/boolean aliases,
  and coherently repinned CPIO metadata and semantic mutations.
- Python compilation and `git diff --check` passed.
- The independent execution-critical delta review returned `GO` after four
  archive, type, parser, and test-coverage findings were fixed.

## Boundary

P2.42 is not complete. No fresh E2 nonce, Full-LTO output, AP, manifest,
connected D0 binding, approval, Odin session, or device action was created.
The next bounded step is two clean reproducible Full-LTO E2 builds followed by
deterministic packaging and offline Process v2 promotion. Device contact
remains outside that step.
